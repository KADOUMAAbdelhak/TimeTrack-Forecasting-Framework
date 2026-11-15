"""Measurement provenance, fail-closed host guards and an isolated end-to-end systems pass.

Everything here uses generated windows, tiny generated fits and a scratch journal.
"""

from dataclasses import asdict, replace
from importlib import import_module
import json
from pathlib import Path
import subprocess
import tempfile
from types import MappingProxyType, SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np

from fgcs_strengthening_v04.src.data_adapters import PreparedPartition, Windows
from fgcs_strengthening_v04.src.identity import HOME, RESOURCES, ScientificIdentity, canonical_json, read_config
from fgcs_strengthening_v04.src.provenance import DuplicateIdentity, Journal, ProvenanceError
from fgcs_strengthening_v04.src.systems import (
    CheckpointRef, SystemsRunner, _SOURCES, run_isolated, systems_fingerprints,
)
from fgcs_strengthening_v04.src.systems_environment import (
    MachineManifest, REGISTERED, observe_environment, require_environment,
)
from fgcs_strengthening_v04.src.systems_records import COST_LABELS, digest
from fgcs_strengthening_v04.tests.systems_fixtures import complement, manifest, plan_for
from fgcs_strengthening_v04.tests.training_fixtures import _seal, close_fits, digest as text_digest, identity

_FORBIDDEN = ("energy", "carbon", "joule", "co2", "watt", "kwh")


def _check(condition, message):
    if not condition:
        raise AssertionError(message)


def benchmark_partition(unit, *, evaluation_count=130):
    """A generated partition exposing training windows and a legal benchmark support."""
    config = read_config()
    block = config["blocks"][unit.block]
    context, horizons = block["contexts"][0], len(block["horizons"])
    gen = np.random.default_rng(982)
    train = Windows(gen.normal(size=(7, context, 4)).astype("float32"),
                    gen.normal(size=(7, 4, horizons)).astype("float32"), None, np.arange(7))
    validation = Windows(gen.normal(size=(3, context, 4)).astype("float32"),
                         gen.normal(size=(3, 4, horizons)).astype("float32"), None, np.arange(7, 10))
    histories = gen.uniform(0, 5, size=(evaluation_count, context, 4))

    class Scaler:
        @staticmethod
        def transform(values):
            return ((np.asarray(values, dtype=np.float64) - 1.0) / 2.0).astype(np.float32)

    class Adapter:
        @staticmethod
        def _windows(frame, entity, length, origins, scaler):
            if origins[0] == 0:
                return train
            if origins[0] == 1:
                return validation
            raise AssertionError("Outer test windows materialised during systems work")

        @staticmethod
        def _benchmark_ids(frame, entity, origins):
            return tuple(f"{entity}:{origin}" for origin in origins)

        @staticmethod
        def _benchmark_histories(frame, entity, length, origins):
            _check(list(origins) == sorted(origins), "Historical builders require ordered origins")
            return histories[np.asarray(origins) - 1000]

        @staticmethod
        def _inverse(scaler, scaled, resource):
            values = np.asarray(scaled, dtype=np.float64) * 2 + 1
            return values, 0.0, values

    split_hashes = MappingProxyType({name: text_digest(name) for name in
                                    ("inner_train", "inner_validation", "outer_train", "outer_test")})
    evaluation = np.array([1]) if unit.phase == "inner" else np.arange(1000, 1000 + evaluation_count)
    return PreparedPartition(unit.block, unit.entity, unit.fold, unit.phase, context,
                             text_digest(unit.phase + "support"), split_hashes, text_digest(unit.phase + "scaler"),
                             Adapter(), None, np.array([0]), evaluation, Scaler()), histories


def end_to_end_probe():
    """Fresh-process run: fit, select, sample, time, cost, publish. Returns compact evidence."""
    import torch

    torch.set_num_interop_threads(1)
    torch.set_num_threads(1)
    from fgcs_strengthening_v04.src.systems import _memory_condition, deployment_rows, inference_condition
    from fgcs_strengthening_v04.src.training import TrainingEngine

    out = {}
    with tempfile.TemporaryDirectory(dir=HOME) as scratch, patch(
            "fgcs_strengthening_v04.src.provenance.HOME", Path(scratch)):
        seal = systems_fingerprints()
        engine = TrainingEngine(Journal(seal))
        inner_id = identity("M1")
        final_id = replace(inner_id, phase="final")
        losses = [[3.] * 4, [2.] * 4, [2.5, 2.5, 1.0, 2.5]] + [[2.] * 4] * 20
        with patch("fgcs_strengthening_v04.src.training._evaluate", side_effect=losses):
            engine.fit_inner(inner_id, benchmark_partition(inner_id)[0])
        final, histories = benchmark_partition(final_id)
        engine.fit_final(final_id, final)

        host = observe_environment()
        runner = SystemsRunner(engine.journal, host)
        try:
            runner.prepare((final_id,), final)
        except ProvenanceError as error:
            _check("C6" in str(error), "systems preparation refused before fit closure")
        else:
            _check(False, "systems preparation refused before fit closure")
        _check(not engine.journal._path("systems", "origins").exists(), "nothing published before fit closure")
        close_fits(engine.journal)
        plan = runner.prepare((final_id,), final)
        again = runner.prepare((final_id,), final)
        _check(again.binding == plan.binding and again.origins == plan.origins, "Origin sampling is not stable")
        positions = list(plan.origins.positions)
        _check(len(positions) == 128 == len(set(positions)), "Expected 128 distinct sampled origins")
        _check(np.array_equal(plan.raw_histories, histories[positions]), "Sampled order is not preserved")
        _check(plan.scaled_histories.dtype == np.float32, "Prepared histories must be float32")
        origin_file = engine.journal.runtime / "systems" / "origins" / f"{plan.origins.sha256}.json"
        _check(digest(json.loads(origin_file.read_text())) == plan.binding.origins_sha256, "Origin manifest hash")
        published = json.loads((engine.journal.runtime / "systems" / "manifest.json").read_text())
        _check(published == host.payload(), "Published host manifest differs")

        rows = runner.measure_complement(plan)
        latencies = [row for row in rows if type(row).__name__ == "InferenceLatency"]
        _check(len(latencies) == 20 == len(rows) / 2, "Expected 5 subjects x 2 modes x 2 batches")
        _check(all(row.available and len(row.durations_ns) == 100 and row.median_ms > 0 and row.p95_ms >= row.median_ms
                   for row in latencies), "Incomplete timed condition")
        footprints, deployment = deployment_rows(plan.complement, plan.binding)
        costs = runner.costs(plan)
        _check(tuple(row.label for row in costs) == COST_LABELS, "Missing registered cost label")
        cost = {row.label: row for row in costs}
        outcome, _ = engine.journal.completed_evidence(final_id)
        inner, _ = engine.journal.completed_evidence(inner_id)
        _check(cost["selection_cost"].worker_seconds == inner["timing_seconds"]["elapsed"], "Selection elapsed")
        _check(cost["final_fit_cost"].optimisation_seconds == outcome["timing_seconds"]["primary_optimisation"],
               "Final-fit optimisation excludes the tail")
        _check(cost["checkpoint_tail_cost"].tail_epochs == 1 and cost["checkpoint_tail_cost"].worker_seconds > 0,
               "Checkpoint tail is charged separately")
        _check(cost["diagnostic_cost"].checkpoint_serialization_seconds > 0, "Diagnostic captures charged separately")

        task_ids = tuple(ScientificIdentity(final_id.block, final_id.entity, final_id.fold, final_id.seed, "final",
                                            "checkpoint_request", "M1", (task,), "all", 64, "task_selected")
                         for task in RESOURCES)
        task_plan = runner.prepare(task_ids, final)
        task_footprints, task_deployment = deployment_rows(task_plan.complement, task_plan.binding)
        _check(task_plan.origins == plan.origins, "C1: every model on a partition shares its benchmark origins")
        task_rows = runner.measure(task_plan, 1, "end_to_end_in_memory")

        short = benchmark_partition(final_id, evaluation_count=20)[0]
        short_plan = runner.prepare((final_id,), short)
        short_latency, _ = runner.measure(short_plan, 128, "forward_only")
        _check(not short_latency.available and runner.memory(short_plan, 128, "forward_only") is None,
               "Short support must mark batch 128 unavailable")
        _check(runner.measure(short_plan, 1, "forward_only")[0].available, "Batch 1 remains available")

        requests = []

        def replay(module, function, arguments, *, manifest):
            requests.append((module, function, manifest == host))
            arguments = json.loads(canonical_json(arguments))
            adapter = SimpleNamespace(prepare=lambda entity, fold, phase: final)
            with patch("fgcs_strengthening_v04.src.data_adapters.adapter_for", return_value=adapter):
                result = getattr(import_module(module), function)(**arguments)
            return {"baseline_rss_bytes": 10, "peak_rss_bytes": 30, "peak_increment_bytes": 20,
                    "platform_interpretation": "Darwin ru_maxrss bytes", "worker_pid": 1, "result": result}

        with patch("fgcs_strengthening_v04.src.systems.run_isolated", replay):
            memory = runner.memory(plan, 128, "end_to_end_in_memory")
        _check(requests == [("fgcs_strengthening_v04.src.systems", "_memory_condition", True)], "RSS request")
        _check(memory.peak_increment_bytes == 20 and memory.provenance == plan.binding, "RSS provenance")
        with patch("fgcs_strengthening_v04.src.systems.run_isolated",
                   lambda *args, **kwargs: {**replay(*args, **kwargs), "result": {"binding_sha256": "0" * 64}}):
            try:
                runner.memory(plan, 1, "forward_only")
                raise AssertionError("RSS worker mismatch accepted")
            except ProvenanceError:
                pass
        adapter = SimpleNamespace(prepare=lambda entity, fold, phase: final)
        with patch("fgcs_strengthening_v04.src.data_adapters.adapter_for", return_value=adapter):
            try:
                _memory_condition(seal.payload(), host.payload(), [final_id.payload()], "0" * 64, 1,
                                  "forward_only", "complement")
                raise AssertionError("Replay accepted a different binding")
            except ProvenanceError:
                pass

        paths = [runner.publish(row) for row in (*footprints, deployment, *costs, *rows, memory,
                                                 *task_footprints, task_deployment, *task_rows)]
        _check(len(set(paths)) == len(paths), "Measurement keys collide")
        try:
            runner.publish(rows[0])
            raise AssertionError("Measurement was overwritten")
        except DuplicateIdentity:
            pass
        tampered = replace(rows[0], provenance=replace(plan.binding, hardware_sha256=digest("other host")))
        for operation in (lambda: runner.publish(tampered),
                          lambda: runner.measure(replace(plan, origins=short_plan.origins), 1, "forward_only"),
                          lambda: runner.measure(replace(plan, complement=task_plan.complement), 1, "forward_only")):
            try:
                operation()
                raise AssertionError("Tampered provenance accepted")
            except ProvenanceError:
                pass
        records = [json.loads(path.read_text()) for path in paths]
        text = json.dumps(records).lower()
        _check(not any(word in text for word in _FORBIDDEN), "Energy/carbon field in systems output")
        _check(all(record["provenance"]["hardware_sha256"] == host.hardware_sha256
                   and len(record["observed_background_load"]) == 3 for record in records), "Host binding")

        out.update(
            records=len(records), record_types=sorted({record["record_type"] for record in records}),
            parameters=footprints[0].trainable_parameters, raw_bytes=footprints[0].raw_tensor_bytes,
            deployed_bytes=deployment.total_deployed_bytes, optimizer=deployment.optimizer_state_bytes_by_fit,
            expected_optimizer=outcome["optimizer_state_bytes"], deployment=(deployment.physical_checkpoint_count,
                                                                           deployment.logical_target_models),
            task_deployment=(task_deployment.physical_checkpoint_count, task_deployment.logical_target_models),
            task_epochs=sorted(ref.epoch for ref in task_plan.binding.checkpoints),
            routing=dict(task_plan.binding.target_checkpoint_sha256s),
            checkpoint_sha=footprints[0].artifact.checkpoint_sha256,
            artifact_sha=outcome["checkpoints"]["2"]["sha256"], formulation=plan.binding.formulation,
            task_formulation=task_plan.binding.formulation,
            origins_reused=all(record["provenance"]["origins_sha256"] == plan.binding.origins_sha256
                               for record in records[:len(footprints) + 1 + len(costs) + len(rows)]),
            systems_sources=sorted(_SOURCES), sealed=sorted(dict(seal.sources)),
        )
    return out


class SystemsProvenanceTests(unittest.TestCase):
    def test_registered_conditions_fail_closed(self):
        REGISTERED.require_registered()
        for change in ({"device": "mps"}, {"workers": 2}, {"torch_intraop_threads": 2},
                       {"torch_interop_threads": 8}, {"OMP_NUM_THREADS": ""}, {"MKL_NUM_THREADS": "2"},
                       {"OPENBLAS_NUM_THREADS": "4"}, {"lightgbm_jobs": True}):
            with self.subTest(change=change), self.assertRaises(ProvenanceError):
                replace(REGISTERED, **change).require_registered()
        with self.assertRaises(ProvenanceError):
            require_environment(None)
        expected = manifest()
        with self.assertRaises(ProvenanceError):
            require_environment(replace(expected, conditions=replace(REGISTERED, workers=2)))
        live = replace(expected, conditions=replace(REGISTERED, torch_interop_threads=8))
        with patch("fgcs_strengthening_v04.src.systems_environment.observe_environment", return_value=live), \
                self.assertRaises(ProvenanceError):
            require_environment(expected)
        other = replace(expected, hardware=replace(expected.hardware, hostname="other-host"))
        with patch("fgcs_strengthening_v04.src.systems_environment.observe_environment", return_value=other), \
                self.assertRaises(ProvenanceError):
            require_environment(expected)
        with patch("fgcs_strengthening_v04.src.systems_environment.observe_environment", side_effect=OSError), \
                self.assertRaises(ProvenanceError):
            require_environment(expected)
        with patch("fgcs_strengthening_v04.src.systems_environment.observe_environment", return_value=expected):
            require_environment(expected)

    def test_manifest_is_complete_and_hash_separates_hardware_and_software(self):
        expected = manifest()
        self.assertEqual(MachineManifest.from_payload(json.loads(canonical_json(expected.payload()))), expected)
        for field in ("cpu_model", "power_mode", "os"):
            with self.subTest(field=field), self.assertRaises(ValueError):
                replace(expected.hardware, **{field: " "})
        with self.assertRaises(ValueError):
            replace(expected.hardware, physical_cores=8, logical_cores=4)
        with self.assertRaises(ValueError):
            replace(expected.software, pytorch="")
        changed = replace(expected, software=replace(expected.software, numpy="other"))
        self.assertEqual(changed.hardware_sha256, expected.hardware_sha256)
        self.assertNotEqual(changed.software_sha256, expected.software_sha256)
        live = observe_environment()
        self.assertEqual(live.conditions.device, "cpu")
        self.assertEqual((live.conditions.workers, live.conditions.lightgbm_jobs), (1, 1))
        self.assertTrue(all(asdict(live.hardware).values()) and all(asdict(live.software).values()))

    def test_binding_and_checkpoint_references_are_exact(self):
        plan = plan_for(complement("S1", []))
        binding = plan.binding
        for change in ({"hardware_sha256": "x"}, {"origins_sha256": "0" * 63}, {"warmups": 19},
                       {"repetitions": 99}, {"tasks": ("MEMORY", "CPU")}, {"context": 0},
                       {"run_identities": (identity("S1"),)},
                       {"target_checkpoint_sha256s": binding.target_checkpoint_sha256s[:3]},
                       {"target_checkpoint_sha256s": (("CPU", ("0" * 64,)), *binding.target_checkpoint_sha256s[1:])}):
            with self.subTest(change=tuple(change)), self.assertRaises(ValueError):
                replace(binding, **change)
        ref = binding.checkpoints[0]
        with self.assertRaises(ValueError):
            replace(ref, identity=identity("S1"))
        with self.assertRaises(ValueError):
            replace(ref, epoch=None)
        tree = ScientificIdentity("fastStorage", "697", 1, 0, "final", "lightgbm", "LightGBM", ("CPU",), "own",
                                  None, "selected")
        with self.assertRaises(ValueError):
            CheckpointRef(tree, ref.checkpoint_sha256, ref.outcome_sha256, None, 3)
        CheckpointRef(tree, ref.checkpoint_sha256, ref.outcome_sha256, None, 18)

    def test_runner_requires_systems_sources_in_the_journal_seal(self):
        seal = systems_fingerprints()
        sealed = dict(seal.sources)
        self.assertTrue(set(_SOURCES) <= set(sealed))
        self.assertTrue(set(dict(_seal().sources)) <= set(sealed))
        with tempfile.TemporaryDirectory(dir=HOME) as scratch, patch(
                "fgcs_strengthening_v04.src.provenance.HOME", Path(scratch)):
            with self.assertRaises(ProvenanceError):
                SystemsRunner(Journal(_seal()), manifest())
        with tempfile.TemporaryDirectory(dir=HOME) as scratch, patch(
                "fgcs_strengthening_v04.src.provenance.HOME", Path(scratch)):
            journal = Journal(seal)
            with self.assertRaises(ProvenanceError):
                SystemsRunner(journal, replace(manifest(), conditions=replace(REGISTERED, device="mps")))
            with self.assertRaises(ProvenanceError):
                SystemsRunner(journal, None)
            SystemsRunner(journal, manifest())

    def test_end_to_end_isolated_measurement_provenance(self):
        try:
            module = "fgcs_strengthening_v04.tests.test_systems_provenance"
            result = run_isolated(module, "end_to_end_probe", {})["result"]
        except subprocess.CalledProcessError as error:
            self.fail(error.stderr.decode()[-4000:])
        self.assertEqual(result["parameters"], 52500)
        self.assertEqual(result["raw_bytes"], 52500 * 4)
        self.assertGreater(result["deployed_bytes"], result["raw_bytes"])
        self.assertEqual(list(result["optimizer"].values()), [result["expected_optimizer"]])
        self.assertEqual(result["deployment"], [1, 1])
        self.assertEqual(result["task_deployment"], [2, 4])
        self.assertEqual(result["task_epochs"], [2, 3])
        routing = result["routing"]
        self.assertEqual(routing["CPU"], routing["THROUGHPUT"])
        self.assertNotEqual(routing["MEMORY"], routing["CPU"])
        self.assertEqual(result["checkpoint_sha"], result["artifact_sha"])
        self.assertEqual((result["formulation"], result["task_formulation"]), ("M1", "M1-task-checkpoints"))
        self.assertEqual(result["record_types"], ["Deployment", "Footprint", "InferenceLatency",
                                                  "InferenceThroughput", "PeakMemory", "TrainingCost"])
        self.assertEqual(result["records"], 1 + 1 + 6 + 40 + 1 + 2 + 1 + 2)
        self.assertTrue(result["origins_reused"])
        self.assertTrue(set(result["systems_sources"]) <= set(result["sealed"]))


if __name__ == "__main__":
    unittest.main()
