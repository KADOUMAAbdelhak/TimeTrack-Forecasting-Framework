"""Bundle builder end to end on generated fits, evaluations and historical tables."""

from dataclasses import replace
from functools import lru_cache
import json
from pathlib import Path
import tempfile
from types import MappingProxyType
import unittest

import numpy as np
import pandas as pd

from fgcs_strengthening_v03.analyse_study import _records, _sources
from fgcs_strengthening_v03.src.data_adapters import PreparedPartition, Windows, frozen_contexts
from fgcs_strengthening_v03.src.evaluation import OuterEvaluator, _digest
from fgcs_strengthening_v03.src.historical import MANIFEST, HistoricalReader, PartitionMetadata
from fgcs_strengthening_v03.src.identity import CONFIG, HOME, ROOT, RESOURCES, read_config
from fgcs_strengthening_v03.src.manifest_builder import (
    BundleBuilder, ScheduleNotClosed, required_coordinates,
)
from fgcs_strengthening_v03.src.provenance import Fingerprints, sha256_file
from fgcs_strengthening_v03.src.statistics.design import BLOCKS
from fgcs_strengthening_v03.src.statistics.endpoints import Cell
from fgcs_strengthening_v03.src.statistics.schema import Provenance
from fgcs_strengthening_v03.src.statistics.synthesis import DiagnosticCell, ResultTable
from fgcs_strengthening_v03.src.systems import systems_fingerprints
from fgcs_strengthening_v03.tests.training_fixtures import close_evaluation, close_fits, digest, identity, scratch_engine

SETTINGS = read_config()
BLOCK, ENTITY, FOLD = "fastStorage", "697", 1
L = frozen_contexts(BLOCK)[ENTITY, FOLD]
HORIZONS = SETTINGS["blocks"][BLOCK]["horizons"]
IDS = list(range(100, 106))


@lru_cache(maxsize=1)
def seal():
    return systems_fingerprints()


def framed(unit, *, broken=False):
    """Generated windows at the frozen common context; outer test only through origin 2."""
    gen = np.random.default_rng(5)
    train = Windows(gen.normal(size=(9, L, 4)).astype("float32"),
                    gen.normal(size=(9, 4, len(HORIZONS))).astype("float32"), None, np.arange(9))
    valid = Windows(gen.normal(size=(3, L, 4)).astype("float32"),
                    gen.normal(size=(3, 4, len(HORIZONS))).astype("float32"), None, np.arange(9, 12))
    targets = gen.normal(size=(len(IDS), 4, len(HORIZONS))).astype("float32")
    native = targets.astype(np.float64) * 2 + 1
    if broken:
        native[0, 0, 0] = np.nan
    test = Windows(gen.normal(size=(len(IDS), L, 4)).astype("float32"), targets, native, np.asarray(IDS))

    class Adapter:
        def _windows(self, frame, entity, length, origins, scaler):
            return {0: train, 1: valid, 2: test}[int(origins[0])]

        def _inverse(self, scaler, values, resource):
            values = np.asarray(values, dtype=np.float64) * 2 + 1
            return values, 0., values

    hashes = MappingProxyType({name: digest(name) for name in
                               ("inner_train", "inner_validation", "outer_train", "outer_test")})
    return PreparedPartition(BLOCK, ENTITY, FOLD, unit.phase, L, digest(unit.phase + "support"), hashes,
                             digest(unit.phase + "scaler"), Adapter(), None, np.array([0]),
                             np.array([1 if unit.phase == "inner" else 2]), None)


def metadata(block, entity, fold):
    final = framed(replace(identity("M1"), phase="final"))
    scalers = {length: digest(f"scaler-{length}") for length in SETTINGS["blocks"][block]["contexts"]}
    scalers[L] = final.scaler_sha256
    return PartitionMetadata(block, entity, fold, L, final.support_sha256, final.split_hashes["outer_test"],
                             len(IDS), _digest(IDS), scalers)


class ManifestBuilderTests(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory(dir=HOME)
        self.addCleanup(self.scratch.cleanup)
        self.root = Path(self.scratch.name)

    def historical(self):
        rows = []
        for lead in HORIZONS:
            base = {"block": BLOCK, "entity": ENTITY, "fold": FOLD, "resource": "CPU", "lead": lead, "n": len(IDS),
                    "mae": 1. + lead / 10}
            rows.append({**base, "formulation": "AR", "L": L})
        path = self.root / "ridge.parquet"
        pd.DataFrame(rows).to_parquet(path, index=False)
        persistence = [{"vm_id": ENTITY, "fold": FOLD, "resource": "CPU", "lead": lead, "n": len(IDS),
                        "mae": 2. + lead, "outer_test_hash": digest("outer_test"), "formulation": f, "seed": s}
                       for lead in HORIZONS for f in ("S1", "M1") for s in (0, 1)]
        ppath = self.root / "persistence.parquet"
        pd.DataFrame(persistence).to_parquet(ppath, index=False)
        manifest = json.loads(MANIFEST.read_text())
        manifest["tables"] = [
            {"kind": "ridge", "block": None, "path": path.relative_to(ROOT).as_posix(), "sha256": sha256_file(path)},
            {"kind": "v1_persistence", "block": BLOCK, "path": ppath.relative_to(ROOT).as_posix(),
             "sha256": sha256_file(ppath)}]
        mpath = self.root / "historical.json"
        mpath.write_text(json.dumps(manifest))
        return HistoricalReader(metadata, manifest=mpath)

    def test_bundle_validates_under_the_scientific_record_checks(self):
        s2, m1, m0 = (replace(identity(f), tasks=("CPU",)) if f == "S2" else identity(f)
                      for f in ("S2", "M1", "M0"))
        coordinates = [(model, BLOCK, ENTITY, "CPU", FOLD, h, seed)
                       for model, seed in (("S2", 0), ("M1", 0), ("M0", 0), ("S1", 0), ("persistence", None),
                                           ("Ridge-AR", None), ("Ridge-ARX", None))
                       for h in HORIZONS]
        s1 = replace(identity("S1"), phase="final", tasks=("CPU",))
        diagnostic = DiagnosticCell(BLOCK, ENTITY, FOLD, 0, None).identity()
        with scratch_engine(seal()) as engine:
            for unit in (s2, m1, m0):
                engine.fit_inner(unit, framed(unit))
                engine.fit_final(replace(unit, phase="final"), framed(replace(unit, phase="final")))
            builder = BundleBuilder(engine.journal, self.historical())
            with self.assertRaisesRegex(ScheduleNotClosed, "fits closure"):
                list(builder.cells(coordinates))
            close_fits(engine.journal, abandoned={diagnostic.digest})  # S1 is not listed: still open
            evaluator = OuterEvaluator(engine.journal)
            for unit in (s2, m1, m0):
                final = replace(unit, phase="final")
                if unit is m0:
                    with self.assertRaises(ValueError):
                        evaluator.evaluate(final, framed(final, broken=True))
                else:
                    evaluator.evaluate(final, framed(final))
            with self.assertRaisesRegex(ScheduleNotClosed, "evaluation closure"):
                list(BundleBuilder(engine.journal, self.historical()).cells(coordinates))
            close_evaluation(engine.journal, abandoned={s1.digest})
            builder = BundleBuilder(engine.journal, self.historical())
            with self.assertRaisesRegex(ScheduleNotClosed, "no terminal record"):
                list(builder.cells(coordinates))  # S1 abandoned for evaluation only, not as a fit
            engine.journal._path("orchestrator", "gates", "fits.json").unlink()  # scratch-only rewrite
            close_fits(engine.journal, abandoned={s1.digest, diagnostic.digest})
            builder = BundleBuilder(engine.journal, self.historical())
            path = builder.build(self.root / "bundle", coordinates=coordinates,
                                 diagnostic_keys=[(BLOCK, ENTITY, FOLD, 0)])
            with self.assertRaises(FileExistsError):
                builder.build(self.root / "bundle", coordinates=coordinates)

            manifest = json.loads(path.read_text())
            raw = Provenance(**manifest["provenance"])
            sealed = Fingerprints((CONFIG.relative_to(ROOT).as_posix(), raw.config_sha256),
                                  tuple(raw.input_hashes.items()), tuple(raw.source_hashes.items()))
            sealed.require_protocol(additional_sources=_sources())
            sealed.verify()
            frozen = {block: frozen_contexts(block) for block in BLOCKS}
            verified = set(raw.input_hashes.values())
            cells = list(_records(path.parent, manifest["artifacts"]["cells"], Cell, True, verified, frozen))
            diagnostics = list(_records(path.parent, manifest["artifacts"]["diagnostics"], DiagnosticCell, True,
                                        verified, frozen))
            ResultTable(cells, diagnostics).validate_domains(complete=False)

        status = {}
        for cell in cells:
            status.setdefault(cell.model, set()).add(cell.status)
        self.assertEqual(status, {"S2": {"ok"}, "M1": {"ok"}, "M0": {"failed"}, "S1": {"missing"},
                                  "persistence": {"ok"}, "Ridge-AR": {"ok"}, "Ridge-ARX": {"missing"}})
        by_model = {cell.model: cell for cell in cells if cell.horizon == 1}
        self.assertEqual(by_model["M1"].metadata[:2], by_model["persistence"].metadata[:2])
        self.assertEqual(by_model["M1"].metadata, by_model["Ridge-AR"].metadata)
        self.assertEqual(by_model["M1"].context, L)
        self.assertIsNotNone(by_model["M0"].evidence_sha256)
        self.assertIsNone(by_model["S1"].evidence_sha256)
        self.assertEqual(diagnostics, [DiagnosticCell(BLOCK, ENTITY, FOLD, 0, None)])

    def test_catalogue_matches_the_registered_budget(self):
        from fgcs_strengthening_v03.src.manifest_builder import HISTORICAL_MODELS, _blank
        from fgcs_strengthening_v03.src.statistics.design import expected_identity

        seen, identities = 0, set()
        for coordinate in required_coordinates():
            seen += 1
            if coordinate[0] not in HISTORICAL_MODELS:
                identities.add(expected_identity(_blank(coordinate)).digest)
        self.assertEqual(seen, 1_085_800)
        budget = 45_500 + 4_550 + 12_600 + 8_400 + 1_050 + 1_050 + 2_800 + 1_500 + 4_200
        self.assertEqual(len(identities), budget)
        self.assertEqual(RESOURCES, tuple(SETTINGS["resources"]))


if __name__ == "__main__":
    unittest.main()
