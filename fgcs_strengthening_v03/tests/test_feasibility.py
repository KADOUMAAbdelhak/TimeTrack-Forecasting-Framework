"""Feasibility inputs are metadata-complete and the projection arithmetic is exact on fixed timings."""

import unittest

from fgcs_strengthening_v03 import feasibility
from fgcs_strengthening_v03.plan_execution import fit_identities
from fgcs_strengthening_v03.src.identity import read_config
from fgcs_strengthening_v03.src.tree.design import GRID

CONFIG = read_config()


class FeasibilityTests(unittest.TestCase):
    def test_metadata_covers_every_partition_without_metric_columns(self):
        shapes = feasibility.partition_shapes()
        self.assertEqual(len(shapes), 910)
        self.assertTrue(all(shape["outer_train"] > 0 and shape["outer_test"] > 0 for shape in shapes.values()))
        epochs, finals = feasibility.v1_operations()
        self.assertEqual(set(epochs), set(CONFIG["blocks"]))
        self.assertTrue(all(set(value) == {"S1", "S2", "M1"} for value in epochs.values()))
        self.assertFalse(any(key.endswith(("mae", "nmae", "mse")) for row in finals[:5] for key in row))

    def test_projection_scales_with_registered_units_and_speedup(self):
        shapes = feasibility.partition_shapes()
        epochs = {block: {f: {"inner": 2.0, "final": 1.0} for f in ("S1", "S2", "M1")} for block in CONFIG["blocks"]}
        kinds = ("S1", "S2", "M0", "M1", "H128", "pcgrad", "gradnorm",
                 *(f"{family}/{variant}" for family in CONFIG["modern"]["families"]
                   for variant in ("independent", "shared")))
        timing = {(kind, block, L): (1e-6, 0.)
                  for kind in kinds for block in CONFIG["blocks"] for L in CONFIG["blocks"][block]["contexts"]}
        lightgbm = {(L, scope): {config.variant: 0. for config in GRID} for L in (4, 9, 18) for scope in ("own", "all")}
        extraction = {(block, L): 0. for block in CONFIG["blocks"] for L in CONFIG["blocks"][block]["contexts"]}
        result = feasibility.project(shapes, epochs, timing, lightgbm, extraction,
                                     {1: {"speedup": 1.}, 4: {"speedup": 2.}})
        expected = 0.
        for identity in fit_identities():
            if identity.arm == "lightgbm":
                continue
            shape = shapes[identity.block, identity.entity, identity.fold]
            expected += 1e-6 * (2 * shape["inner_train"] if identity.phase == "inner" else shape["outer_train"])
        self.assertAlmostEqual(result["single_worker_seconds"], expected, places=6)
        self.assertAlmostEqual(result["projected_wall_days"][4], result["projected_wall_days"][1] / 2)


if __name__ == "__main__":
    unittest.main()
