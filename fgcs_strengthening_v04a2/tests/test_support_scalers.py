import csv
from hashlib import sha256
import json
import unittest

import numpy as np

from fgcs_strengthening_v04a2.src.data_adapters import PARTITIONS, adapter_for
from fgcs_strengthening_v04a2.src.identity import RESOURCES, canonical_json, read_config
from fgcs_strengthening_v04a2.src.provenance import verified_reference


class FrozenSupportTests(unittest.TestCase):
    def test_all_910_entity_folds_against_v1_completion_records(self):
        config = read_config()
        checks = 0
        for block, spec in config["blocks"].items():
            adapter = adapter_for(block)
            entity_key = "machine" if block == "TimeTrack" else "vm_id"
            scaler_key = "scaler_metadata" if block == "TimeTrack" else "scaler"
            support_key = "support_sha256" if block.startswith("Materna-") else "support_hash"
            paths = {}
            for phase, reference in spec["v1_registries"].items():
                registry = verified_reference(reference)
                with registry.open(newline="") as stream:
                    for row in csv.DictReader(stream):
                        if row["formulation"] != "M1" or row["seed"] != "0":
                            continue
                        entity, fold = row[entity_key], int(row["fold"])
                        if int(row["L"]) != adapter.contexts[entity, fold]:
                            continue
                        key = (entity, fold, phase)
                        self.assertNotIn(key, paths)
                        paths[key] = registry.parent / "runtime" / "completions" / phase / f"{row['run_id']}.json"
            self.assertEqual(len(paths), len(adapter.entities) * 5 * 2)
            for entity in adapter.entities:
                for fold in config["folds"]:
                    for phase in PARTITIONS:
                        with self.subTest(block=block, entity=entity, fold=fold, phase=phase):
                            actual = adapter.prepare(entity, fold, phase)
                            original = json.loads(paths[entity, fold, phase].read_text())
                            identity = original["identity"]
                            self.assertEqual(original["status"], "complete")
                            self.assertEqual((identity[entity_key], identity["fold"], identity["phase"]), (entity, fold, phase))
                            self.assertEqual((identity["formulation"], identity["seed"]), ("M1", 0))
                            self.assertEqual(actual.context, identity["L"])
                            self.assertEqual(actual.support_sha256, identity[support_key])
                            self.assertEqual(actual.scaler_sha256, sha256(canonical_json(original[scaler_key])).hexdigest())
                            for name in PARTITIONS[phase]:
                                self.assertEqual(actual.split_hashes[name], original[f"{name}_hash"])
                            checks += 1
        self.assertEqual(checks, 1820)

    def test_phase_bound_windows_and_canary_contexts(self):
        config = read_config()
        # The v0.4 canary entities' frozen fold-1 contexts (r3 recorded them as its modern pilots).
        for block, entity, context in (("fastStorage", "697", 18), ("Rnd", "99", 4)):
            self.assertEqual(adapter_for(block).contexts[entity, 1], context)
        for block in config["blocks"]:
            with self.subTest(block=block):
                adapter = adapter_for(block)
                inner = adapter.prepare(adapter.entities[0], 1, "inner")
                with self.assertRaises(ValueError):
                    inner.outer_test()
                validation = inner.validation()
                self.assertEqual(validation.inputs.shape[1:], (inner.context, len(RESOURCES)))
                self.assertEqual(validation.targets.shape[1:], (len(RESOURCES), len(adapter.horizons)))
                self.assertEqual(validation.targets.shape, validation.native_targets.shape)
                self.assertEqual(validation.inputs.dtype, np.float32)
                self.assertEqual(validation.targets.dtype, np.float32)
                self.assertTrue(np.isfinite(validation.inputs).all())
                self.assertTrue(np.isfinite(validation.targets).all())
                self.assertEqual(len(set(validation.origin_ids)), len(validation.inputs))
                values, fraction, raw = inner.inverse_target(np.array([-1e6]), "DISK_WRITE")
                self.assertEqual((values[0], fraction, raw[0]), (0, 1, -1))
                final = adapter.prepare(adapter.entities[0], 1, "final")
                with self.assertRaises(ValueError):
                    final.validation()
