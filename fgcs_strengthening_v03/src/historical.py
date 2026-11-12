"""Read-only normalisers for reused v1 and Stage-18 results. Nothing runs on import.

Historical tables store per-cell counts (and, for external blocks, the outer-test hash) but not
ordered origin IDs. Every row is therefore bound to its frozen final partition: its outer-test
count and, where recorded, its outer-test hash must equal the frozen support. Support and
ordered-test-ID fingerprints then come from that partition, exactly as for new evaluations.
"""

from collections import defaultdict
from dataclasses import dataclass
from hashlib import sha256
import json
import math
from pathlib import Path

from .identity import HOME, RESOURCES, ROOT, canonical_json, read_config
from .provenance import ProvenanceError, repository_path, sha256_file
from .statistics.endpoints import Cell

_CONFIG = read_config()
MANIFEST = HOME / "configs/historical_results_v03.json"
_SOURCES = (Path(__file__).resolve().relative_to(ROOT).as_posix(), MANIFEST.relative_to(ROOT).as_posix())
FROZEN_CONTEXT_MODELS = frozenset({"M1-H64-v1", "S2-common-v1", "Ridge-AR", "Ridge-ARX"})


def _digest(value):
    return sha256(canonical_json(value)).hexdigest()


@dataclass(frozen=True, slots=True)
class PartitionMetadata:
    """Frozen final-partition fingerprints, independent of any model or result."""

    block: str
    entity: str
    fold: int
    frozen_context: int
    support_sha256: str
    outer_test_hash: str
    test_origins: int
    ordered_test_ids_sha256: str
    scaler_sha256_by_context: dict

    def scaler_sha256(self, context):
        try:
            return self.scaler_sha256_by_context[context]
        except KeyError:
            raise ProvenanceError(f"No frozen training scaler at L={context}") from None


def frozen_partition_metadata(block, entity, fold):
    """Production provider: prepares the frozen final partition (training scaler only, no test windows)."""
    from .data_adapters import adapter_for

    adapter = adapter_for(block)
    partition = adapter.prepare(entity, fold, "final")
    ids = list(partition.benchmark_origin_ids())
    scalers = {int(length): _digest(group["outer_scaler"])
               for length, group in adapter._reference_groups[entity, fold].items()}
    if scalers.get(partition.context) != partition.scaler_sha256:
        raise ProvenanceError("Frozen scaler reference differs from the prepared final scaler")
    return PartitionMetadata(block, entity, fold, partition.context, partition.support_sha256,
                             partition.split_hashes["outer_test"], len(ids), _digest(ids), scalers)


def load_manifest(path=MANIFEST):
    manifest = json.loads(Path(path).read_text())
    for table in manifest["tables"]:
        if table["kind"] not in manifest["models"]:
            raise ProvenanceError("Unknown historical table kind")
    return manifest


def _rows(table):
    import pandas as pd

    path = repository_path(table["path"])
    if sha256_file(path) != table["sha256"]:
        raise ProvenanceError(f"Historical result table differs from its frozen hash: {table['path']}")
    return pd.read_parquet(path)


def _entity(row, block):
    if "entity" in row:
        return str(row["entity"])
    return str(row["machine"] if block == "TimeTrack" else row["vm_id"])


def _status(mae):
    if mae is None or type(mae) is bool or not math.isfinite(mae):
        return None, "nonfinite_prediction"
    return float(mae), "ok"


class HistoricalReader:
    """Normalise every registered reused table into analysis cells, failing closed on any binding error."""

    def __init__(self, metadata_for=frozen_partition_metadata, *, manifest=MANIFEST):
        self.manifest = load_manifest(manifest)
        self._metadata_for = metadata_for
        self._metadata = {}

    def metadata(self, block, entity, fold):
        key = block, entity, fold
        if key not in self._metadata:
            meta = self._metadata_for(block, entity, fold)
            if (meta.block, meta.entity, meta.fold) != key:
                raise ProvenanceError("Partition metadata provider returned a different partition")
            self._metadata[key] = meta
        return self._metadata[key]

    def input_hashes(self):
        return {table["path"]: table["sha256"] for table in self.manifest["tables"]}

    def cells(self):
        cells = []
        for table in self.manifest["tables"]:
            cells.extend(self._table(table))
        keys = [(c.model, c.block, c.entity, c.resource, c.fold, c.horizon, c.seed) for c in cells]
        if len(keys) != len(set(keys)):
            raise ProvenanceError("Duplicate historical cell across reused tables")
        return cells

    def _cell(self, table, model, block, entity, fold, resource, lead, seed, mae, n, context, test_hash=None):
        spec = _CONFIG["blocks"][block]
        if (entity not in spec["entities"] or fold not in _CONFIG["folds"] or resource not in RESOURCES
                or lead not in spec["horizons"]):
            raise ProvenanceError(f"Historical row outside the frozen grid: {table['path']}")
        meta = self.metadata(block, entity, fold)
        if n != meta.test_origins or (test_hash is not None and test_hash != meta.outer_test_hash):
            raise ProvenanceError(f"Historical row is not on the frozen outer-test support: {block}/{entity}/{fold}")
        if model != "persistence":
            if context not in spec["contexts"]:
                raise ProvenanceError("Historical context is outside the registered context set")
            if model in FROZEN_CONTEXT_MODELS and context != meta.frozen_context:
                raise ProvenanceError(f"{model} row differs from the frozen common context")
        value, status = _status(mae)
        return Cell(model, block, entity, resource, fold, lead, seed, value,
                    None if model == "persistence" else context, meta.support_sha256,
                    None if model == "persistence" else meta.scaler_sha256(context),
                    meta.ordered_test_ids_sha256, status, table["sha256"], None)

    def _table(self, table):
        kind, frame = table["kind"], _rows(table)
        models = self.manifest["models"][kind]
        if kind == "v1_metrics":
            return [self._cell(table, models[row["formulation"]], table["block"], _entity(row, table["block"]),
                               int(row["fold"]), row["resource"], int(row["lead"]), int(row["seed"]), row["mae"],
                               int(row["n"]), int(row["selected_L"]), row.get("outer_test_hash"))
                    for row in frame.to_dict("records") if row["formulation"] in models]
        if kind == "v1_persistence":
            return self._persistence(table, frame)
        if kind == "ridge":
            return [self._cell(table, models[row["formulation"]], row["block"], str(row["entity"]), int(row["fold"]),
                               row["resource"], int(row["lead"]), None, row["mae"], int(row["n"]), int(row["L"]))
                    for row in frame.to_dict("records")]
        context = "forced_L" if kind == "s2_common" else "L"
        return [self._cell(table, models, row["block"], str(row["entity"]), int(row["fold"]), row["resource"],
                           int(row["lead"]), int(row["seed"]), row["mae"], int(row["n"]), int(row[context]))
                for row in frame.to_dict("records")]

    def _persistence(self, table, frame):
        """v1 repeats identical persistence per formulation/seed; require exact agreement, keep one."""
        block = table["block"]
        groups = defaultdict(set)
        for row in frame.to_dict("records"):
            key = _entity(row, block), int(row["fold"]), row["resource"], int(row["lead"])
            mae = row["mae"]
            groups[key].add((None if not math.isfinite(mae) else float(mae), int(row["n"]),
                             row.get("outer_test_hash")))
        cells = []
        for (entity, fold, resource, lead), values in sorted(groups.items()):
            if len(values) != 1:
                raise ProvenanceError("v1 persistence differs across repeated formulation/seed rows")
            mae, n, test_hash = values.pop()
            cells.append(self._cell(table, "persistence", block, entity, fold, resource, lead, None,
                                    math.nan if mae is None else mae, n, None, test_hash))
        return cells
