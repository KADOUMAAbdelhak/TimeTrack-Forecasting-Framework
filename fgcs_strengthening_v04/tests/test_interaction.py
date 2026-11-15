from dataclasses import replace
import math
import unittest

from fgcs_strengthening_v04.src.statistics.design import TRACES
from fgcs_strengthening_v04.src.statistics.endpoints import contrast, interaction, materna_effect
from fgcs_strengthening_v04.tests.statistics_fixtures import aggregate


class InteractionTests(unittest.TestCase):
    def test_interaction_analytical_example_and_common_support(self):
        terms = {model: aggregate(model, mae) for model, mae in (("M1", 8), ("S2", 2), ("M0", 4), ("S1", 2))}
        measured = interaction("fastStorage", terms)
        self.assertAlmostEqual(measured.value, math.log(2))
        self.assertAlmostEqual(measured.ratio, 2.)
        mismatched = terms | {"M0": aggregate("M0", 4, support="other"), "S1": aggregate("S1", 2, support="other")}
        self.assertEqual(interaction("fastStorage", mismatched).issues, {"support_mismatch": 1})
        zeros = interaction("fastStorage", terms | {"M1": aggregate("M1", 0.)})
        self.assertFalse(zeros.available)
        self.assertEqual(zeros.zeros["all/candidate_only_zero"], 1)
        self.assertEqual(zeros.native["fastStorage", "M1"], 0.)

    def test_materna_within_vm_average_and_no_native_trace_pooling(self):
        effects = {}
        for trace, ratio in zip(TRACES, (2., 4., 8.), strict=True):
            args = dict(block=trace, entity="74")
            effects[trace] = contrast(trace, "M1", "S2", aggregate("M1", ratio, **args), aggregate("S2", 1., **args))
        result = materna_effect(effects)
        self.assertAlmostEqual(result.value, math.log(4))
        self.assertEqual(len(result.native), 6)
        with self.assertRaisesRegex(ValueError, "same exact VM"):
            materna_effect(effects | {TRACES[1]: replace(effects[TRACES[1]], subject=("134", "CPU"))})
        self.assertFalse(materna_effect({TRACES[0]: effects[TRACES[0]]}).available)
