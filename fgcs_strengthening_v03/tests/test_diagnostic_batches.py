from dataclasses import replace
from hashlib import sha256
import unittest

import numpy as np

from fgcs_strengthening_v03.src.diagnostics.batches import build_batch_pairs, json_sha256
from fgcs_strengthening_v03.tests.training_fixtures import identity


def diagnostic_identity(slot="final", formulation="M1"):
    return replace(identity(formulation, phase="final"), arm="diagnostic", variant=slot)


class DiagnosticBatchTests(unittest.TestCase):
    def test_exact_key_and_independently_keyed_pcg64_indices(self):
        unit = diagnostic_identity()
        ids = np.arange(10000, 10029) * 300
        pairs = build_batch_pairs(unit, ids)
        self.assertEqual(len(pairs), 8)
        for index, pair in enumerate(pairs):
            self.assertEqual(pair.index, index)
            for side in ("A", "B"):
                draw = getattr(pair, side)
                key = f"fgcs-v03|fastStorage|697|1|0|final|{index}|{side}"
                seed = int.from_bytes(sha256(key.encode()).digest()[:8], "little")
                expected = np.random.Generator(np.random.PCG64(seed)).integers(0, len(ids), size=128)
                self.assertEqual(draw.key, key)
                self.assertEqual(draw.indices, tuple(expected.tolist()))
                self.assertEqual(draw.origin_ids, tuple(ids[expected].tolist()))
                self.assertLess(len(set(draw.origin_ids)), 128)
                self.assertEqual(draw.payload()["origin_ids_sha256"], json_sha256(list(draw.origin_ids)))
            self.assertNotEqual(pair.A.indices, pair.B.indices)

    def test_repeatability_preserves_exact_order_and_string_ids(self):
        unit = diagnostic_identity("mid")
        ids = ["machine01:004", "machine01:008", "machine01:017"]
        first = [pair.payload() for pair in build_batch_pairs(unit, ids)]
        second = [pair.payload() for pair in build_batch_pairs(unit, ids)]
        self.assertEqual(first, second)
        self.assertEqual(json_sha256(first), json_sha256(second))
        self.assertTrue(set(first[0]["A"]["origin_ids"]) <= set(ids))
        final = build_batch_pairs(diagnostic_identity(), ids)
        self.assertNotEqual(first[0]["A"]["indices"], final[0].A.payload()["indices"])
        with self.assertRaises(ValueError):
            build_batch_pairs(unit, ["same", "same"])
