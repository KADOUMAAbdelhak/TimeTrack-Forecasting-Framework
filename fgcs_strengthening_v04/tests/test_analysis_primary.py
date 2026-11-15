"""P4 analysis on generated rows: grid rules, classes, bootstrap and the end-to-end tables."""

from functools import lru_cache
import json
import math
import unittest

import numpy as np

from fgcs_strengthening_v04.analyse_study import analyse, dry_plan
from fgcs_strengthening_v04.src.analysis.bootstrap import Draws, gain_interval, mean_interval, spearman
from fgcs_strengthening_v04.src.analysis.grid import COHORT, CELLS, Grid, MAERow, macro, seed_average
from fgcs_strengthening_v04.src.analysis.primary import (classify, consistency_counts, cross_backbone_rows,
                                                         parameter_counts, persistence_skill)
from fgcs_strengthening_v04.src.identity import RESOURCES, read_config
from fgcs_strengthening_v04.tests.analysis_fixtures import persistence, synthetic_rows

CONFIG = read_config()
# LSTM: sharing hurts (M cells 10 % worse), context helps (S2/M1 5 % better than S1/M0).
FACTORS = {("LSTM", "S1"): 1.0, ("LSTM", "S2"): 0.95, ("LSTM", "M0"): 1.1, ("LSTM", "M1"): 1.045,
           ("iTransformer", "S2"): 0.9, ("iTransformer", "M1"): 0.9}
FAILED = (("DLinear", "M1", "Rnd", "99", "CPU", 2, 1),)


@lru_cache(maxsize=1)
def rows():
    return tuple(synthetic_rows(FACTORS, failed=FAILED))


@lru_cache(maxsize=1)
def draws():
    return Draws(replicates=500)


def _inputs():
    d1 = {(block, entity, fold): np.full((4, 4), 0.5) for block in COHORT for entity in COHORT[block]
          for fold in CONFIG["folds"]}
    ridge = {block: {"AR": persistence(1.)[block], "ARX": persistence(0.9)[block]} for block in COHORT}
    return dict(persistence=persistence(), ridge=ridge, d1=d1, d4={}, d7={})


@lru_cache(maxsize=1)
def results():
    return analyse(rows=rows(), draws=draws(), **_inputs())


class ClassTests(unittest.TestCase):
    def test_thresholds_are_conjunctive_fractions_of_available_units(self):
        full = {"horizons": [5, 5], "vms": [10, 10], "folds": [5, 5], "seeds": [3, 3]}
        self.assertEqual(classify(1.0, full), "Broad Positive")
        self.assertEqual(classify(0.99, full), "Conditionally Positive")
        self.assertEqual(classify(1.0, {**full, "vms": [7, 10]}), "Conditionally Positive")
        self.assertEqual(classify(1.0, {**full, "vms": [7, 9]}), "Conditionally Positive")  # 7/9 < 0.8
        self.assertEqual(classify(1.0, {**full, "vms": [8, 9]}), "Broad Positive")
        self.assertEqual(classify(0.5, {**full, "vms": [4, 10]}), "Neutral or Mixed")
        self.assertEqual(classify(0.5, {**full, "seeds": [1, 3]}), "Neutral or Mixed")
        none = {"horizons": [1, 5], "vms": [2, 10], "folds": [1, 5], "seeds": [1, 3]}
        self.assertEqual(classify(-1.0, none), "Broad Negative")
        self.assertEqual(classify(-0.99, none), "Neutral or Mixed")
        self.assertEqual(classify(-1.0, {**none, "vms": [3, 10]}), "Neutral or Mixed")
        self.assertEqual(classify(0.0, full), "Neutral or Mixed")  # exact zero is not positive
        self.assertEqual(classify(None, full), "Undefined")


class GridTests(unittest.TestCase):
    def test_every_coordinate_must_be_explicit_and_unique(self):
        complete = list(rows())
        with self.assertRaisesRegex(ValueError, "Incomplete grid"):
            Grid(complete[:-1])
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            Grid(complete + complete[:1])
        with self.assertRaises(ValueError):
            MAERow("iTransformer", "S1", "Rnd", "99", "CPU", 1, 1, 0, 1.)
        with self.assertRaises(ValueError):
            MAERow("LSTM", "M1/CPU+MEMORY", "Rnd", "99", "DISK_WRITE", 1, 1, 0, 1.)
        with self.assertRaises(ValueError):
            MAERow("LSTM", "S1", "Rnd", "1", "CPU", 1, 1, 0, 1.)  # outside the 20-VM cohort
        with self.assertRaises(ValueError):
            MAERow("LSTM", "S1", "Rnd", "99", "CPU", 1, 1, 0, math.nan)

    def test_a_failed_fit_is_missing_for_every_cell_of_its_backbone_only(self):
        grid = Grid(rows())
        mask = grid.mask("DLinear", "Rnd")
        unit = (COHORT["Rnd"].index("99"), 0, 1, 1)
        self.assertEqual(int(mask.sum()), 1)
        self.assertTrue(mask[unit])
        for cell in CELLS:
            values = grid.masked("DLinear", cell, "Rnd", mask)
            self.assertTrue(np.isnan(values[unit[0], unit[1], unit[2], :, unit[3]]).all())
        self.assertFalse(grid.mask("LSTM", "Rnd").any())
        self.assertEqual(grid.missing_units(), [{"backbone": "DLinear", "block": "Rnd", "entity": "99",
                                                 "resource": "CPU", "fold": 2, "seed": 1,
                                                 "failed_cells": ["M1"]}])

    def test_macro_weights_cells_then_horizons_and_seeds_use_the_remaining_ones(self):
        values = np.array([[[1., 4.], [3., 8.]], [[np.nan, np.nan], [5., 6.]]])  # [entity, fold, horizon]
        self.assertAlmostEqual(macro(values), ((1 + 3 + 5) / 3 + (4 + 8 + 6) / 3) / 2)
        seeds = np.array([[1., np.nan, 3.], [np.nan] * 3])
        np.testing.assert_array_equal(seed_average(seeds), [2., np.nan])

    def test_consistency_counts_on_a_uniform_improvement(self):
        reference = np.ones((10, 5, 5, 3))
        candidate = reference * 0.9
        candidate[0] = 1.2  # one VM worse
        counts = consistency_counts(candidate, reference)
        self.assertEqual(counts, {"horizons": [5, 5], "vms": [9, 10], "folds": [5, 5], "seeds": [3, 3]})

    def test_persistence_skill_counts_zero_denominators(self):
        model = np.ones((2, 1, 2))
        pers = np.array([[[2., 0.]], [[4., 2.]]])
        result = persistence_skill(model, pers)
        self.assertEqual(result["undefined_zero_denominator"], 1)
        self.assertAlmostEqual(result["skill"], ((0.5 + 0.75) / 2 + 0.5) / 2)


class BootstrapTests(unittest.TestCase):
    def test_draws_are_fixed_per_block_and_read_only(self):
        first, second = Draws(replicates=50), Draws(replicates=50)
        for block in COHORT:
            np.testing.assert_array_equal(first.indices(block), second.indices(block))
            self.assertEqual(first.indices(block).shape, (50, 10))
            with self.assertRaises(ValueError):
                first.indices(block)[0, 0] = 1
        self.assertFalse(np.array_equal(first.indices("fastStorage"), first.indices("Rnd")))

    def test_gain_interval_replicates_match_a_direct_resample(self):
        generator = np.random.default_rng(1)
        c, b = generator.uniform(1, 2, (10, 5, 5)), generator.uniform(1, 2, (10, 5, 5))
        c[3, 2] = b[3, 2] = np.nan
        local = Draws(replicates=40)
        interval, undefined = gain_interval(local, "Rnd", c, b)
        direct = [100 * (macro(b[row]) - macro(c[row])) / macro(b[row]) for row in local.indices("Rnd")]
        np.testing.assert_allclose(interval, np.percentile(direct, [2.5, 97.5]))
        self.assertEqual(undefined, 0)
        same, _ = gain_interval(local, "Rnd", b, b)
        self.assertEqual(same, [0., 0.])
        means, _ = mean_interval(local, "Rnd", np.arange(10.))
        self.assertTrue(0 <= means[0] <= 4.5 <= means[1] <= 9)

    def test_spearman_with_ties(self):
        from scipy.stats import spearmanr

        x, y = np.array([1, 2, 2, 3, 5, 4.]), np.array([2, 1, 3, 3, 6, 5.])
        self.assertAlmostEqual(float(spearman(x, y)), spearmanr(x, y).statistic)
        self.assertTrue(np.isnan(spearman(np.ones(5), np.arange(5.))))


class EndToEndTests(unittest.TestCase):
    def test_table_sizes_match_the_dry_plan(self):
        plan, output = dry_plan(), results()
        self.assertEqual(len(output["P4"]["contrasts"]), plan["P4"]["contrast_rows"])
        self.assertEqual(len(output["P4"]["interaction"]), plan["P4"]["interaction_rows"])
        self.assertEqual(len(output["P4"]["cross_backbone"]), plan["P4"]["cross_backbone_rows"])
        self.assertEqual(len(output["P4"]["baseline_accuracy"]), plan["P4"]["baseline_rows"])
        self.assertEqual(len(output["P4"]["parameter_counts"]), plan["P4"]["parameter_count_rows"])
        self.assertEqual(len(output["P5"]["D-1"]), plan["P5"]["D-1_entity_fold_rows"])
        self.assertEqual(len(output["P5"]["D-3"]), plan["P5"]["D-3_associations"])
        self.assertEqual(len(output["P5"]["D-6"]), plan["P5"]["D-6_entries"])
        self.assertEqual(len(output["P5"]["D-7"]), plan["P5"]["D-7_rows"])
        json.dumps(output, allow_nan=False)

    def test_generated_effects_are_recovered_and_classified(self):
        contrasts = {(r["backbone"], r["block"], r["resource"], r["contrast"]): r for r in results()["P4"]["contrasts"]}
        sharing = contrasts["LSTM", "Rnd", "CPU", "M1:S2"]
        self.assertAlmostEqual(sharing["gain_percent"], -10, delta=0.3)
        self.assertEqual(sharing["class"], "Broad Negative")
        self.assertLess(sharing["interval"][1], 0)
        self.assertEqual(sharing["win_rate"], 0.)
        self.assertAlmostEqual(sharing["median_ratio"], 1.1, delta=0.01)
        context = contrasts["LSTM", "fastStorage", "MEMORY", "S2:S1"]
        self.assertAlmostEqual(context["gain_percent"], 5, delta=0.3)
        self.assertEqual(context["class"], "Broad Positive")
        self.assertAlmostEqual(context["persistence_skill"]["S2"]["skill"], 1 - 0.95 * 1.68 / 2, delta=0.01)
        self.assertEqual(contrasts["DLinear", "Rnd", "CPU", "M1:S2"]["class"], "Neutral or Mixed")  # noise only
        self.assertNotIn(("iTransformer", "Rnd", "CPU", "S2:S1"), contrasts)
        self.assertTrue(all(r["undefined_replicates"] == 0 for r in contrasts.values()))

    def test_interaction_is_the_difference_of_sharing_log_effects(self):
        rows = {(r["backbone"], r["block"], r["resource"]): r for r in results()["P4"]["interaction"]}
        self.assertEqual({b for b, _, _ in rows}, {"LSTM", "DLinear", "PatchTST"})
        lstm = rows["LSTM", "Rnd", "DISK_WRITE"]
        self.assertAlmostEqual(lstm["interaction_log_ratio"], math.log(1.045 / 0.95) - math.log(1.1), delta=0.01)
        self.assertEqual(lstm["entities"], 10)
        self.assertLessEqual(lstm["interval"][0], lstm["interaction_log_ratio"])

    def test_cross_backbone_rule(self):
        def row(backbone, value):
            return {"backbone": backbone, "block": "Rnd", "contrast": "M1:S2", "resource": "CPU", "class": value}

        def verdict(*classes):
            contrasts = [row(b, c) for b, c in zip(("LSTM", "DLinear", "PatchTST", "iTransformer"), classes)]
            out = [r for r in cross_backbone_rows(contrasts) if (r["block"], r["contrast"], r["resource"])
                   == ("Rnd", "M1:S2", "CPU")][0]
            return out["summary"], out["direction"]

        self.assertEqual(verdict("Broad Negative", "Broad Negative", "Broad Negative", "Broad Negative"),
                         ("generalises across backbones", "negative"))
        self.assertEqual(verdict("Broad Positive", "Conditionally Positive", "Broad Positive", "Broad Positive"),
                         ("generalises across backbones", "positive"))
        self.assertEqual(verdict("Broad Negative", "Neutral or Mixed", "Broad Negative", "Broad Negative"),
                         ("backbone-dependent", None))
        self.assertEqual(verdict("Broad Negative", "Broad Positive", "Broad Negative", "Broad Negative"),
                         ("backbone-dependent", None))

    def test_baseline_table_ratio_and_undefined_cells(self):
        rows = {(r["block"], r["cell"], r["resource"]): r for r in results()["P4"]["baseline_accuracy"]}
        s2 = rows["Rnd", "S2", "CPU"]
        self.assertEqual(s2["most_accurate"], "iTransformer")
        self.assertAlmostEqual(s2["lstm_ratio_to_most_accurate"], 0.95 / 0.9, delta=0.01)
        self.assertEqual(rows["Rnd", "S1", "CPU"]["undefined_backbones"], ["iTransformer"])

    def test_parameter_counts_match_the_frozen_and_declared_shapes(self):
        counts = {(r["backbone"], r["cell"], r["context"]): r for r in parameter_counts()}
        self.assertEqual(counts["LSTM", "S1", 9]["complement_parameters"], CONFIG["lstm"]["s1_complement_parameters"][1])
        self.assertEqual(counts["LSTM", "M0", 9]["complement_parameters"], CONFIG["lstm"]["m0_parameter_counts"]["64"][1])
        for context in (4, 9, 18):
            self.assertEqual(counts["DLinear", "S2", context]["complement_parameters"], 4 * (8 * context * 5 + 5))
            self.assertEqual(counts["DLinear", "M1", context]["models"], 1)
        self.assertNotIn(("iTransformer", "S1", 9), counts)


if __name__ == "__main__":
    unittest.main()
