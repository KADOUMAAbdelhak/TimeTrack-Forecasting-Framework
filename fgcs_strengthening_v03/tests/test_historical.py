"""Historical reader on generated tables in every reused format; the real manifest is hash-checked only."""

from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest

import pandas as pd

from fgcs_strengthening_v03.src.evaluation import _digest as evaluation_digest
from fgcs_strengthening_v03.src.historical import (
    MANIFEST, HistoricalReader, PartitionMetadata, _digest, load_manifest,
)
from fgcs_strengthening_v03.src.identity import HOME, ROOT, read_config
from fgcs_strengthening_v03.src.provenance import ProvenanceError, sha256_file

CONFIG = read_config()
TT, FS = "TimeTrack", "fastStorage"
MACHINE, VM = CONFIG["blocks"][TT]["entities"][0], CONFIG["blocks"][FS]["entities"][0]
FROZEN = {TT: 64, FS: 9}


def metadata(block, entity, fold):
    ids = [f"{entity}:{i}" for i in range(6 + fold)]
    contexts = CONFIG["blocks"][block]["contexts"]
    return PartitionMetadata(block, entity, fold, FROZEN[block], _digest(["support", block, entity, fold]),
                             _digest(["test", block, entity, fold]), len(ids), _digest(ids),
                             {L: _digest(["scaler", block, entity, fold, L]) for L in contexts})


def rows_for(block, entity, *, persistence=False, posthoc=None, **fields):
    horizons = CONFIG["blocks"][block]["horizons"][:2]
    out = []
    for fold in (1, 2):
        for resource in ("CPU", "MEMORY"):
            for lead in horizons:
                base = {"fold": fold, "resource": resource, "lead": lead, "n": 6 + fold,
                        "mae": 0.5 + fold + lead / 100}
                if block != TT and posthoc is None:
                    base["outer_test_hash"] = _digest(["test", block, entity, fold])
                if posthoc is None:
                    base["machine" if block == TT else "vm_id"] = entity
                else:
                    base.update(block=block, entity=entity)
                out.append({**base, **fields})
    return out


class HistoricalReaderTests(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory(dir=HOME)
        self.root = Path(self.scratch.name)
        self.addCleanup(self.scratch.cleanup)

    def write(self, name, rows):
        path = self.root / f"{name}.parquet"
        pd.DataFrame(rows).to_parquet(path, index=False)
        return {"path": path.relative_to(ROOT).as_posix(), "sha256": sha256_file(path)}

    def reader(self, tables):
        manifest = json.loads(MANIFEST.read_text())
        manifest["tables"] = tables
        path = self.root / "manifest.json"
        path.write_text(json.dumps(manifest))
        return HistoricalReader(metadata, manifest=path)

    def tables(self):
        metrics = [row for formulation in ("S1", "S2", "M1") for seed in (0, 1, 2) for row in
                   rows_for(TT, MACHINE, formulation=formulation, seed=seed,
                            selected_L=FROZEN[TT] if formulation == "M1" else 32)]
        fs_metrics = [row for formulation in ("S2", "M1") for seed in (0, 1, 2) for row in
                      rows_for(FS, VM, formulation=formulation, seed=seed, selected_L=FROZEN[FS])]
        persistence = [row for formulation in ("S1", "S2", "M1") for seed in (0, 1, 2)
                       for row in rows_for(FS, VM, formulation=formulation, seed=seed)]
        tt_persistence = [row for formulation in ("S1", "S2", "M1")
                          for row in rows_for(TT, MACHINE, formulation=formulation)]
        common = [row for seed in (0, 1, 2) for row in rows_for(FS, VM, posthoc=True, seed=seed, forced_L=9)]
        h129 = [row for seed in (0, 1, 2) for row in rows_for(TT, MACHINE, posthoc=True, seed=seed, L=128)]
        ridge = [row for formulation in ("AR", "ARX") for row in rows_for(FS, VM, posthoc=True,
                                                                         formulation=formulation, L=9)]
        return [{"kind": "v1_metrics", "block": TT, **self.write("tt_metrics", metrics)},
                {"kind": "v1_metrics", "block": FS, **self.write("fs_metrics", fs_metrics)},
                {"kind": "v1_persistence", "block": FS, **self.write("fs_persistence", persistence)},
                {"kind": "v1_persistence", "block": TT, **self.write("tt_persistence", tt_persistence)},
                {"kind": "s2_common", "block": None, **self.write("common", common)},
                {"kind": "h129", "block": None, **self.write("h129", h129)},
                {"kind": "ridge", "block": None, **self.write("ridge", ridge)}]

    def test_every_reused_format_maps_to_bound_cells(self):
        tables = self.tables()
        cells = self.reader(tables).cells()
        counts = {}
        for cell in cells:
            counts[cell.model] = counts.get(cell.model, 0) + 1
        self.assertEqual(counts, {"S2-v1": 48, "M1-H64-v1": 48, "persistence": 16, "S2-common-v1": 24,
                                  "M1-H129-v1": 24, "Ridge-AR": 8, "Ridge-ARX": 8})
        for cell in cells:
            meta = metadata(cell.block, cell.entity, cell.fold)
            self.assertEqual((cell.support_sha256, cell.ordered_test_ids_sha256),
                             (meta.support_sha256, meta.ordered_test_ids_sha256))
            self.assertIn(cell.evidence_sha256, {table["sha256"] for table in tables})
            self.assertIsNone(cell.identity_sha256)
            if cell.model == "persistence":
                self.assertEqual((cell.seed, cell.context, cell.scaler_sha256), (None, None, None))
            else:
                self.assertEqual(cell.scaler_sha256, meta.scaler_sha256(cell.context))
        tt_s2 = next(c for c in cells if c.model == "S2-v1" and c.block == TT)
        self.assertEqual(tt_s2.context, 32)
        self.assertTrue(all(c.context == 128 for c in cells if c.model == "M1-H129-v1"))
        self.assertTrue(all(c.seed is None for c in cells if c.model.startswith("Ridge")))
        self.assertEqual(len({(c.block, c.fold) for c in cells if c.model == "persistence"}), 4)

    def test_binding_failures_fail_closed(self):
        tables = self.tables()
        cases = {
            "count": lambda rows: rows[0].update(n=99),
            "test hash": lambda rows: rows[0].update(outer_test_hash=_digest("other")),
            "frozen context": lambda rows: rows[-1].update(selected_L=18),
            "entity": lambda rows: rows[0].update(vm_id="not-in-cohort"),
        }
        for label, change in cases.items():
            with self.subTest(label=label), self.assertRaises(ProvenanceError):
                rows = pd.read_parquet(ROOT / tables[1]["path"]).to_dict("records")
                change(rows)
                self.reader([{"kind": "v1_metrics", "block": FS, **self.write("bad", rows)}]).cells()
        rows = pd.read_parquet(ROOT / tables[2]["path"]).to_dict("records")
        rows[0]["mae"] += 1
        with self.assertRaisesRegex(ProvenanceError, "persistence differs"):
            self.reader([{"kind": "v1_persistence", "block": FS, **self.write("bad_p", rows)}]).cells()
        with self.assertRaisesRegex(ProvenanceError, "frozen hash"):
            self.reader([{**tables[0], "sha256": "0" * 64}]).cells()
        with self.assertRaisesRegex(ProvenanceError, "Duplicate"):
            self.reader([tables[0], {**tables[0], "kind": "v1_metrics"}]).cells()

    def test_nonfinite_historical_mae_is_explicit(self):
        rows = rows_for(FS, VM, posthoc=True, formulation="AR", L=9)
        rows[0]["mae"] = float("nan")
        cells = self.reader([{"kind": "ridge", "block": None, **self.write("nan", rows)}]).cells()
        self.assertEqual((cells[0].status, cells[0].mae), ("nonfinite_prediction", None))
        self.assertTrue(all(c.status == "ok" for c in cells[1:]))

    def test_registered_manifest_lists_exact_tracked_tables(self):
        manifest = load_manifest()
        self.assertEqual(len(manifest["tables"]), 15)
        self.assertEqual({t["kind"] for t in manifest["tables"]},
                         {"v1_metrics", "v1_persistence", "s2_common", "h129", "ridge"})
        for table in manifest["tables"]:
            with self.subTest(path=table["path"]):
                self.assertEqual(sha256_file(ROOT / table["path"]), table["sha256"])
        ids = ["machine01:5", 7, "a"]
        self.assertEqual(_digest(ids), evaluation_digest(ids))
        self.assertEqual(_digest(ids), sha256(json.dumps(ids, separators=(",", ":")).encode()).hexdigest())


if __name__ == "__main__":
    unittest.main()
