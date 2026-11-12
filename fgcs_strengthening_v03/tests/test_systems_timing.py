from dataclasses import replace
from hashlib import sha256
import unittest

import numpy as np

from fgcs_strengthening_v03.src.identity import RESOURCES
from fgcs_strengthening_v03.src.systems import (
    FitTiming, inference_condition, measure_calls, sample_origins, summarise_durations, training_costs,
)
from fgcs_strengthening_v03.tests.systems_fixtures import complement, plan_for
from fgcs_strengthening_v03.tests.training_fixtures import digest, identity


class SystemsTimingTests(unittest.TestCase):
    def test_fixed_warmup_count_and_reference_summary(self):
        calls = []
        ticks = iter(tick for i in range(1, 101) for tick in (0, i * 1_000_000))
        samples = measure_calls(lambda: calls.append(None), clock=lambda: next(ticks))
        self.assertEqual(len(calls), 120)
        median, p95, mean, throughput = summarise_durations(samples, 128)
        self.assertEqual((median, p95, mean), (50.5, 95.05, 50.5))
        self.assertAlmostEqual(throughput, 128 / 0.0505)

    def test_modes_and_short_support(self):
        work, transformations = [], []
        plan = plan_for(complement("M1", work), origin_count=15, history_calls=transformations)
        latency, throughput = inference_condition(plan, 128, "forward_only")
        self.assertFalse(latency.available)
        self.assertIsNone(throughput.forecasts_per_second)
        self.assertEqual(work, [])
        inference_condition(plan, 1, "forward_only")
        self.assertEqual(transformations, [])
        inference_condition(plan, 1, "end_to_end_in_memory")
        self.assertEqual(transformations, ["transform", *RESOURCES] * 120)
        self.assertEqual(len(work), 240)

    def test_origins_match_independent_key_reference(self):
        key, ids = digest("run"), tuple(range(200, 350))
        seed = int.from_bytes(sha256(f"fgcs-v03|systems-origins|{key}".encode()).digest()[:8], "little")
        positions = tuple(np.random.Generator(np.random.PCG64(seed)).choice(150, 128, replace=False).tolist())
        sampled = sample_origins(key, ids)
        self.assertEqual(sampled.positions, positions)
        self.assertEqual(sampled.origin_ids, tuple(ids[i] for i in positions))
        self.assertEqual(sampled.sha256, sample_origins(key, ids).sha256)
        self.assertEqual(len(set(sampled.origin_ids)), 128)
        self.assertIsNone(sample_origins(key, ()).count_for(1))

    def test_fit_costs_separate_failure_tail_diagnostics_and_elapsed(self):
        inner = identity()
        final = replace(inner, phase="final")
        diagnostic = replace(final, arm="diagnostic", variant="final")
        items = (
            FitTiming(inner, digest("inner"), "complete", {"elapsed": 11, "primary_optimisation": 5, "validation": 3}),
            FitTiming(replace(inner, seed=1), digest("failed"), "failed", {"elapsed": 2}),
            FitTiming(final, digest("final"), "complete", {"elapsed": 100, "primary_optimisation": 7, "validation": 0,
                      "checkpoint_serialization": 1, "checkpoint_io": 2, "checkpoint_tail_optimisation": 20,
                      "task_checkpoint_serialization": 1, "diagnostic_checkpoint_serialization": 3}, 2),
            FitTiming(diagnostic, digest("diagnostic"), "complete", {"diagnostic_seconds": 12}),
        )
        binding = plan_for(complement("M1", [])).binding
        rows = {row.label: row for row in training_costs(binding, items, scheduler_elapsed={"selection_cost": 8})}
        self.assertEqual((rows["selection_cost"].worker_seconds, rows["selection_cost"].failed_attempt_worker_seconds,
                          rows["selection_cost"].scheduler_elapsed_seconds), (11, 2, 8))
        self.assertEqual(rows["final_fit_cost"].worker_seconds, 10)
        self.assertEqual(rows["checkpoint_tail_cost"].worker_seconds, 21)
        self.assertEqual(rows["checkpoint_tail_cost"].tail_epochs, 2)
        self.assertEqual(rows["diagnostic_cost"].worker_seconds, 15)
        self.assertTrue(rows["gradnorm_overhead"].included_in_optimisation)
        with self.assertRaises(ValueError):
            FitTiming(inner, digest("mixed"), "complete", {"elapsed": 10, "diagnostic_seconds": 1})
