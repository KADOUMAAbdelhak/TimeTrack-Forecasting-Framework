"""Read-only v1 persistence and Ridge AR/ARX rows for the 20 cohort VMs. Nothing runs on import.

Both are reused, already-observed results (P7; D-2 is tier 2 post hoc). Each table must match its
frozen SHA-256, and each row is bound to its frozen final partition: its outer-test count, and its
outer-test hash where recorded, must equal the frozen support. Ridge rows must use the frozen
H64-M1 context of their entity and fold.
"""

from collections import defaultdict
from dataclasses import dataclass
import json
import math
from pathlib import Path

import numpy as np

from ..identity import HOME, RESOURCES
from ..provenance import ProvenanceError, repository_path, sha256_file
from .grid import BLOCKS, COHORT, FOLDS, HORIZONS

MANIFEST = HOME / "configs/historical_results_v03.json"


@dataclass(frozen=True, slots=True)
class PartitionMetadata:
    block: str
    entity: str
    fold: int
    frozen_context: int
    outer_test_hash: str
    test_origins: int


def frozen_partition_metadata(block, entity, fold):
    """Prepare the frozen final partition (training scaler only; no test windows are built)."""
    from ..data_adapters import adapter_for

    partition = adapter_for(block).prepare(entity, fold, "final")
    return PartitionMetadata(block, entity, fold, partition.context, partition.split_hashes["outer_test"],
                             len(partition.benchmark_origin_ids()))


def _frame(table):
    import pandas as pd

    path = repository_path(table["path"])
    if sha256_file(path) != table["sha256"]:
        raise ProvenanceError(f"Historical result table differs from its frozen hash: {table['path']}")
    return pd.read_parquet(path)


class HistoricalReader:
    def __init__(self, metadata_for=frozen_partition_metadata, *, manifest=MANIFEST):
        self.manifest = json.loads(Path(manifest).read_text())
        self._metadata_for = metadata_for
        self._metadata = {}

    def tables(self, kind):
        return [t for t in self.manifest["tables"] if t["kind"] == kind and t.get("block") in (None, *BLOCKS)]

    def input_hashes(self):
        return {t["path"]: t["sha256"] for kind in ("v1_persistence", "ridge") for t in self.tables(kind)}

    def metadata(self, block, entity, fold):
        key = block, entity, fold
        if key not in self._metadata:
            meta = self._metadata_for(block, entity, fold)
            if (meta.block, meta.entity, meta.fold) != key:
                raise ProvenanceError("Partition metadata provider returned a different partition")
            self._metadata[key] = meta
        return self._metadata[key]

    def _bind(self, block, entity, fold, n, test_hash=None):
        meta = self.metadata(block, entity, fold)
        if n != meta.test_origins or (test_hash is not None and test_hash != meta.outer_test_hash):
            raise ProvenanceError(f"Historical row is not on the frozen outer-test support: {block}/{entity}/{fold}")
        return meta

    @staticmethod
    def _index(block, entity, resource, fold, lead):
        return (COHORT[block].index(entity), RESOURCES.index(resource), FOLDS.index(fold),
                HORIZONS[block].index(lead))

    def persistence(self):
        """{block: [entity, resource, fold, horizon]} native persistence MAE (NaN if nonfinite)."""
        output = {}
        for table in self.tables("v1_persistence"):
            block = table["block"]
            frame = _frame(table)
            frame = frame[frame["vm_id"].astype(str).isin(COHORT[block])]
            groups = defaultdict(set)
            for row in frame.to_dict("records"):
                mae = float(row["mae"])
                groups[str(row["vm_id"]), int(row["fold"]), row["resource"], int(row["lead"])].add(
                    (mae if math.isfinite(mae) else None, int(row["n"]), row.get("outer_test_hash")))
            values = np.full((len(COHORT[block]), len(RESOURCES), len(FOLDS), len(HORIZONS[block])), np.nan)
            for (entity, fold, resource, lead), found in groups.items():
                if len(found) != 1:
                    raise ProvenanceError("v1 persistence differs across repeated formulation/seed rows")
                mae, n, test_hash = found.pop()
                self._bind(block, entity, fold, n, test_hash)
                values[self._index(block, entity, resource, fold, lead)] = np.nan if mae is None else mae
            if len(groups) != values.size:
                raise ProvenanceError(f"{block}: incomplete v1 persistence grid for the cohort")
            output[block] = values
        if set(output) != set(BLOCKS):
            raise ProvenanceError("Persistence tables do not cover both Bitbrains blocks")
        return output

    def ridge(self):
        """{block: {"AR"|"ARX": [entity, resource, fold, horizon]}} at the frozen context."""
        (table,) = self.tables("ridge")
        frame = _frame(table)
        output = {block: {name: np.full((len(COHORT[block]), len(RESOURCES), len(FOLDS), len(HORIZONS[block])),
                                        np.nan) for name in ("AR", "ARX")} for block in BLOCKS}
        seen = set()
        for row in frame.to_dict("records"):
            block, entity = row["block"], str(row["entity"])
            if block not in BLOCKS or entity not in COHORT[block]:
                continue
            fold, lead, name = int(row["fold"]), int(row["lead"]), row["formulation"]
            key = (block, entity, fold, row["resource"], lead, name)
            if key in seen:
                raise ProvenanceError("Duplicate Ridge row")
            seen.add(key)
            meta = self._bind(block, entity, fold, int(row["n"]))
            if int(row["L"]) != meta.frozen_context:
                raise ProvenanceError("Ridge row differs from the frozen H64-M1 context")
            mae = float(row["mae"])
            output[block][name][self._index(block, entity, row["resource"], fold, lead)] = \
                mae if math.isfinite(mae) else np.nan
        expected = sum(2 * len(COHORT[b]) * len(RESOURCES) * len(FOLDS) * len(HORIZONS[b]) for b in BLOCKS)
        if len(seen) != expected:
            raise ProvenanceError(f"Ridge rows cover {len(seen)} of {expected} cohort cells")
        return output
