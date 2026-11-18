"""Read-only v1 data preparation. No scientific model or runner is imported."""

from dataclasses import dataclass
from functools import cached_property, lru_cache
from hashlib import sha256
import importlib
import io
import json
import sys
from threading import Lock
from types import MappingProxyType
import zipfile

import numpy as np
import pandas as pd

from .identity import RESOURCES, canonical_json, read_config
from .provenance import ProvenanceError, repository_path, verified_reference, verify_file

_CONFIG = read_config()
TT = "multiresource.04_lstm_factorial.src"
EXTERNAL = "independent_validation.05_bitbrains_factorial.src"
PARTITIONS = {
    "inner": ("inner_train", "inner_validation"),
    "final": ("outer_train", "outer_test"),
}
_IMPORT_LOCK = Lock()


def _require(condition, detail):
    if not condition:
        raise ProvenanceError(detail)


@lru_cache(maxsize=None)
def _frozen_module(name):
    # Reuse pure historical definitions without generating bytecode in their trees.
    with _IMPORT_LOCK:
        for path, digest in _CONFIG["historical_source_hashes"].items():
            verify_file(repository_path(path), digest)
        previous = sys.dont_write_bytecode
        try:
            sys.dont_write_bytecode = True
            return importlib.import_module(name)
        finally:
            sys.dont_write_bytecode = previous


@lru_cache(maxsize=None)
def _verified_reference(path, digest):
    return verified_reference({"path": path, "sha256": digest})


def _reference(ref):
    return _verified_reference(ref["path"], ref["sha256"])


def frozen_contexts(block):
    """Read exact v1 H64 M1 selections without loading a panel or a model."""
    spec = _CONFIG["blocks"][block]
    entity_column = "machine" if block == "TimeTrack" else "vm_id"
    frame = pd.read_csv(verified_reference(spec["common_context_source"]), dtype={entity_column: str})
    m1 = frame.loc[frame.formulation.eq(_CONFIG["common_context"]["formulation"])]
    if block != "TimeTrack":
        _require(m1.environment.eq(spec["environment"]).all(), f"{block}: wrong context environment")
        _require(m1.selection_source.eq("inner_validation_only").all(), f"{block}: wrong selection source")
    contexts = {}
    for entity, fold, length in m1[[entity_column, "fold", "selected_L"]].itertuples(index=False, name=None):
        _require((entity, fold) not in contexts and length in spec["contexts"], f"{block}: invalid or duplicate context")
        contexts[entity, fold] = int(length)
    expected = {(entity, fold) for entity in spec["entities"] for fold in _CONFIG["folds"]}
    _require(contexts.keys() == expected, f"{block}: incomplete or unexpected M1 context grid")
    return MappingProxyType(contexts)


@dataclass(frozen=True, slots=True)
class Windows:
    inputs: np.ndarray
    targets: np.ndarray
    native_targets: np.ndarray
    origin_ids: np.ndarray


@dataclass(frozen=True, slots=True)
class PreparedPartition:
    """Bound to one verified phase and its training-only scaler."""

    block: str
    entity: str
    fold: int
    phase: str
    context: int
    support_sha256: str
    split_hashes: MappingProxyType
    scaler_sha256: str
    _adapter: "FrozenAdapter"
    _frame: pd.DataFrame
    _train_origins: np.ndarray
    _evaluation_origins: np.ndarray
    _scaler: object

    def training(self):
        return self._adapter._windows(self._frame, self.entity, self.context, self._train_origins, self._scaler)

    def validation(self):
        if self.phase != "inner":
            raise ValueError("Only an inner partition exposes validation windows")
        return self._adapter._windows(self._frame, self.entity, self.context, self._evaluation_origins, self._scaler)

    def outer_test(self):
        if self.phase != "final":
            raise ValueError("An inner partition cannot expose outer test windows")
        # The future training engine calls this only after the final trajectory finishes.
        return self._adapter._windows(self._frame, self.entity, self.context, self._evaluation_origins, self._scaler)

    def benchmark_origin_ids(self):
        if self.phase != "final":
            raise ValueError("Benchmark origins require the legal outer-test partition")
        return self._adapter._benchmark_ids(self._frame, self.entity, self._evaluation_origins)

    def benchmark_histories(self, positions):
        if self.phase != "final":
            raise ValueError("Benchmark histories require a final partition")
        positions = tuple(positions)
        if (not positions or len(set(positions)) != len(positions)
                or any(type(pos) is not int or not 0 <= pos < len(self._evaluation_origins) for pos in positions)):
            raise ValueError("Invalid benchmark positions in the frozen test support")
        # Historical window builders expect ordered origins. Restore the sampled order.
        ordered = sorted(positions)
        raw = self._adapter._benchmark_histories(
            self._frame, self.entity, self.context, self._evaluation_origins[ordered])
        return raw[np.argsort(np.argsort(positions))]

    def scale_benchmark_histories(self, histories):
        return self._scaler.transform(histories)

    def inverse_target(self, scaled, resource):
        """Return projected values, projected fraction and unprojected values."""
        return self._adapter._inverse(self._scaler, scaled, resource)


class FrozenAdapter:
    def __init__(self, block):
        self.block = block
        self._spec = _CONFIG["blocks"][block]
        self.entities = tuple(self._spec["entities"])
        self.horizons = tuple(self._spec["horizons"])
        self.contexts = frozen_contexts(block)
        self._raw = _reference(self._spec["raw_input"])
        self._entity_column = "machine" if block == "TimeTrack" else "vm_id"
        self._length_column = "context_length" if block == "TimeTrack" else "L"
        self._verify_cohort()
        self._frame_cache = None

    def _verify_cohort(self):
        path = verified_reference(self._spec["cohort_source"])
        if self.block == "TimeTrack":
            entities = json.loads(path.read_text())["machines"]
        else:
            rows = pd.read_csv(path, dtype={"entity_id": str})
            if not self.block.startswith("Materna-"):
                rows = rows.loc[rows.environment.eq(self._spec["environment"])]
            rows = rows.sort_values("rank")
            _require(list(rows["rank"]) == list(range(1, len(self.entities) + 1)), "Invalid frozen cohort ranks")
            entities = list(rows.entity_id)
        _require(tuple(entities) == self.entities, f"{self.block}: frozen cohort mismatch")

    @cached_property
    def _support(self):
        path = verified_reference(self._spec["support_manifest"])
        filters = [(self._entity_column, "in", list(self.entities))]
        if self.block != "TimeTrack":
            filters.append(("environment", "=", self._spec["environment"]))
        manifest = pd.read_parquet(path, filters=filters)
        manifest = manifest.set_index([self._entity_column, "fold", self._length_column])
        expected = {(entity, fold, length) for entity in self.entities
                    for fold in _CONFIG["folds"] for length in self._spec["contexts"]}
        _require(manifest.index.is_unique and set(manifest.index) == expected, f"{self.block}: incomplete v1 support grid")
        return manifest

    @cached_property
    def _reference_groups(self):
        ref = json.loads(verified_reference(self._spec["frozen_scaler_reference"]).read_text())
        _require(ref["block"] == self.block and tuple(ref["entities"]) == self.entities, "Invalid scaler reference cohort")
        groups = {(group["entity"], group["fold"]): group["contexts"] for group in ref["groups"]}
        _require(len(groups) == len(ref["groups"]) and groups.keys() == self.contexts.keys(), "Invalid scaler reference grid")
        return groups

    def prepare(self, entity, fold, phase):
        """Verify frozen metadata and prepare only the requested phase's scaler."""
        if type(fold) is not int or (entity, fold) not in self.contexts or phase not in PARTITIONS:
            raise ValueError(f"Unplanned partition: {self.block}/{entity}/{fold}/{phase}")
        context = self.contexts[entity, fold]
        frame, folds = self._data(entity)
        split = folds[fold - 1]
        expected = self._reference_groups[entity, fold][str(context)]
        _require(split.fold == fold and split.hashes == expected["split_hashes"], "Frozen split hash mismatch")
        self._verify_support(frame, entity, split)
        train_name, evaluation_name = PARTITIONS[phase]
        train, evaluation = getattr(split, train_name), getattr(split, evaluation_name)
        scaler, metadata = self._fit_scaler(frame, entity, train, context)
        _require(metadata == expected["inner_scaler" if phase == "inner" else "outer_scaler"],
                 f"{self.block}/{entity}/{fold}/{phase}: training scaler differs from v1")
        _require(all(np.isfinite(array).all() for array in (
            scaler.transformed_median, scaler.transformed_iqr, scaler.native_iqr)), "Nonfinite training scaler")
        _require((scaler.transformed_iqr > 0).all() and (scaler.native_iqr > 0).all(), "Nonpositive training IQR")
        for array in (scaler.transformed_median, scaler.transformed_iqr, scaler.native_iqr):
            array.setflags(write=False)
        keys = (("train", "validation" if phase == "inner" else "test")
                if self.block == "TimeTrack" else (train_name, evaluation_name))
        support_sha = sha256(canonical_json(dict(zip(keys, (split.hashes[train_name], split.hashes[evaluation_name]))))).hexdigest()
        _require(support_sha == expected["inner_support" if phase == "inner" else "outer_support"], "Phase support hash differs")
        return PreparedPartition(
            self.block, entity, fold, phase, context, support_sha, MappingProxyType(dict(split.hashes)),
            sha256(canonical_json(metadata)).hexdigest(), self, frame, train, evaluation, scaler,
        )

    def _verify_support(self, frame, entity, split):
        times = self._timestamps(frame)
        for names in PARTITIONS.values():
            train, holdout = (getattr(split, name) for name in names)
            _require(len(train) and len(holdout) and np.all(times[train + max(self.horizons)] < times[holdout[0]]),
                     "Target-time purge failed")
        for length in self._spec["contexts"]:
            row = self._support.loc[(entity, split.fold, length)]
            for name, digest in split.hashes.items():
                origins = getattr(split, name)
                _require(len(origins) and np.all(np.diff(origins) > 0), "Unsorted or empty frozen origins")
                _require(digest == row[f"{name}_hash"], "Frozen manifest support differs across contexts")
                count = f"{name}_{'n' if self.block == 'TimeTrack' else 'count'}"
                _require(len(origins) == row[count], "Frozen manifest origin count differs")
                if self.block != "TimeTrack":
                    _require(np.array_equal(times[origins], row[f"{name}_origin_ids"]), "Exact v1 origin IDs differ")

    def _data(self, entity):
        cached = self._frame_cache
        if cached is None or cached[0] != entity:
            frame, folds = self._load_entity(entity)
            _require(tuple(item.fold for item in folds) == tuple(_CONFIG["folds"]), "Unexpected v1 fold sequence")
            for fold in folds:
                for name in fold.hashes:
                    getattr(fold, name).setflags(write=False)
            self._frame_cache = entity, frame, folds
            return frame, folds
        return cached[1:]


class TimeTrackAdapter(FrozenAdapter):
    def __init__(self):
        super().__init__("TimeTrack")

    @cached_property
    def _panel(self):
        return _frozen_module(f"{TT}.data").load_panel()

    def _load_entity(self, entity):
        folds = _frozen_module(f"{TT}.splits")
        # The original splitter constructs support at maximum L for every context.
        return self._panel, folds.build_factorial_folds(self._panel, entity, max(self._spec["contexts"]))

    @staticmethod
    def _timestamps(frame):
        return frame.timestamp.to_numpy()

    @staticmethod
    def _fit_scaler(frame, entity, train, context):
        scaler = _frozen_module(f"{TT}.transforms").fit_partition_scaler(frame, entity, train, context)
        return scaler, scaler.metadata()

    @staticmethod
    def _windows(frame, entity, context, origins, scaler):
        raw = _frozen_module(f"{TT}.data").build_raw_windows(frame, entity, context, origins)
        inputs, targets = _frozen_module(f"{TT}.transforms").scale_windows(raw.X, raw.y, scaler)
        return Windows(inputs, targets, raw.y, raw.sample_ids)

    @staticmethod
    def _benchmark_ids(frame, entity, origins):
        return tuple(f"{entity}:{origin}" for origin in origins)

    @staticmethod
    def _benchmark_histories(frame, entity, context, origins):
        return _frozen_module(f"{TT}.data").build_raw_windows(frame, entity, context, origins).X

    @staticmethod
    def _inverse(scaler, scaled, resource):
        index = RESOURCES.index(resource)
        values = np.zeros((*np.shape(scaled), len(RESOURCES)), dtype=np.float64)
        values[..., index] = scaled
        native, fractions = scaler.inverse(values)
        unprojected, _ = scaler.inverse(values, physical_projection=False)
        return native[..., index], float(fractions[index]), unprojected[..., index]


class ExternalAdapter(FrozenAdapter):
    def _load_entity(self, entity):
        raw = self._read_vm(entity)
        _require(raw.archive_path == self._raw and raw.archive_sha256 == self._spec["raw_input"]["sha256"],
                 "External raw archive identity mismatch")
        frame = _frozen_module(f"{EXTERNAL}.cleaning").clean_and_segment(raw).frame
        origins = _frozen_module(f"{EXTERNAL}.support").legal_origins(frame)
        folds = _frozen_module(f"{EXTERNAL}.splits").build_folds(frame, self._spec["environment"], entity, origins)
        return frame, folds

    @staticmethod
    def _timestamps(frame):
        return frame.timestamp_seconds.to_numpy(dtype=np.int64)

    @staticmethod
    def _fit_scaler(frame, entity, train, context):
        scaler = _frozen_module(f"{EXTERNAL}.transforms").fit_partition_scaler(frame, train, context)
        return scaler, {field: getattr(scaler, field).tolist()
                        for field in ("transformed_median", "transformed_iqr", "native_iqr")}

    @staticmethod
    def _windows(frame, entity, context, origins, scaler):
        X, y, _ = _frozen_module(f"{EXTERNAL}.panel").build_windows(frame, origins, context)
        inputs, targets = _frozen_module(f"{EXTERNAL}.transforms").scale_windows(X, y, scaler)
        ids = _frozen_module(f"{EXTERNAL}.support").origin_ids(frame, origins)
        return Windows(inputs, targets, y, ids)

    @staticmethod
    def _benchmark_ids(frame, entity, origins):
        return tuple(_frozen_module(f"{EXTERNAL}.support").origin_ids(frame, origins).tolist())

    @staticmethod
    def _benchmark_histories(frame, entity, context, origins):
        X, _, _ = _frozen_module(f"{EXTERNAL}.panel").build_windows(frame, origins, context)
        return X

    @staticmethod
    def _inverse(scaler, scaled, resource):
        return scaler.inverse_one(scaled, resource)


class BitbrainsAdapter(ExternalAdapter):
    def __init__(self, block):
        if block not in _CONFIG["secondary"]["blocks"]:
            raise ValueError("Expected a Bitbrains block")
        super().__init__(block)
        verified_reference(_CONFIG["historical_reader_config"])

    def _read_vm(self, entity):
        return _frozen_module(f"{EXTERNAL}.ingestion").read_vm(self._spec["environment"], entity)


class MaternaAdapter(ExternalAdapter):
    def __init__(self, block):
        if block not in ("Materna-T1", "Materna-T2", "Materna-T3"):
            raise ValueError("Expected a Materna trace")
        super().__init__(block)

    def _read_vm(self, entity):
        """The frozen Materna ZIP member and UTC timestamp conventions."""
        ingestion = _frozen_module(f"{EXTERNAL}.ingestion")
        folder = f"materna-trace-{self.block[-1]}"
        with zipfile.ZipFile(self._raw) as bundle:
            names = [name for name in bundle.namelist()
                     if name.lower().endswith(".csv") and folder in name.lower()
                     and name.rsplit("/", 1)[-1][:-4] == entity]
            _require(len(names) == 1, f"Expected one Materna ZIP member for {self.block}/{entity}")
            member = names[0]
            payload = bundle.read(member)
        source = pd.read_csv(io.BytesIO(payload), sep=";", engine="c")
        source.columns = [column.strip() for column in source.columns]
        columns = ingestion.required_columns(list(source.columns))
        times = pd.to_datetime(source[columns["timestamp"]], format="%d.%m.%Y %H:%M:%S", utc=True, errors="raise")
        frame = pd.DataFrame({
            "timestamp_seconds": times.to_numpy(dtype="datetime64[ns]").astype("int64") // 1_000_000_000,
            "raw_member": member,
        })
        for field, key in (("CPU", "cpu"), ("MEMORY", "memory"), ("DISK_WRITE", "disk_write"),
                           ("network_received", "network_received"), ("network_transmitted", "network_transmitted")):
            frame[field] = ingestion.numeric(source[columns[key]])
        members = [{"environment": self.block, "vm_id": entity, "archive_filename": self._raw.name,
                    "member_path": member, "member_byte_size": len(payload), "member_sha256": sha256(payload).hexdigest()}]
        return ingestion.RawVM(self.block, entity, frame, members, self._raw, self._spec["raw_input"]["sha256"])


def adapter_for(block):
    if block == "TimeTrack":
        return TimeTrackAdapter()
    if block.startswith("Materna-"):
        return MaternaAdapter(block)
    return BitbrainsAdapter(block)
