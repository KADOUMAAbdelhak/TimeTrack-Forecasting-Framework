from dataclasses import replace
from functools import lru_cache
import io
import json
import random
import unittest
from unittest.mock import patch

import numpy as np
import torch

from fgcs_strengthening_v03.src.checkpoints import diagnostic_slots
from fgcs_strengthening_v03.src.diagnostics.batches import json_sha256
from fgcs_strengthening_v03.src.diagnostics.engine import DiagnosticEngine, diagnostic_fingerprints
from fgcs_strengthening_v03.src.diagnostics.gradients import StateContamination, live_state_hashes
from fgcs_strengthening_v03.src.identity import RESOURCES
from fgcs_strengthening_v03.src.models.lstm import LSTM
from fgcs_strengthening_v03.src.provenance import DuplicateIdentity, ProvenanceError, sha256_file
from fgcs_strengthening_v03.src.training import cpu_seed_scope
from fgcs_strengthening_v03.tests.training_fixtures import identity, partition, scratch_engine


@lru_cache(maxsize=1)
def seal():
    return diagnostic_fingerprints()


def fit(engine, *, extended, formulation="M1"):
    inner = identity(formulation)
    final = replace(inner, phase="final")
    validation = [[2., 2., 2., 2.]] * 8
    if extended:
        validation[1] = [1., 1., 4., 4.]
        validation[2] = [1., 1., 1., 8.]
    with patch("fgcs_strengthening_v03.src.training._evaluate", side_effect=validation):
        engine.fit_inner(inner, partition(inner)[0])
    prepared, accesses = partition(final)
    fit_result = engine.fit_final(final, prepared)
    state = torch.load(io.BytesIO(fit_result.resume_state), weights_only=True)
    live = LSTM(formulation=formulation, block=final.block, tasks=final.tasks, hidden_size=final.hidden_size)
    live.load_state_dict(state["model"])
    live.register_buffer("guard_fixture", torch.ones(2), persistent=False)
    for p in live.parameters():
        p.grad = torch.ones_like(p)
    optimizer = torch.optim.Adam(live.parameters(), lr=0.001)
    optimizer.load_state_dict(state["optimizer"])
    generator = torch.Generator()
    generator.set_state(state["rng"]["shuffle"])
    return final, prepared, accesses, live, optimizer, generator, fit_result.evidence


class IsolationTests(unittest.TestCase):
    def test_all_three_slots_and_extension_preserve_primary_endpoint_and_live_state(self):
        self.assertEqual(diagnostic_slots(1), {"epoch0": 0, "mid": 1, "final": 1})
        self.assertEqual(diagnostic_slots(5), {"epoch0": 0, "mid": 3, "final": 5})
        scores = []
        for extended in (False, True):
            with scratch_engine(seal()) as trainer:
                final, prepared, reads, live, optimizer, generator, fit_evidence = fit(trainer, extended=extended)
                before = live_state_hashes(live, optimizer, generator)
                diag = DiagnosticEngine(trainer.journal)
                records = {}
                for slot in ("epoch0", "mid", "final"):
                    unit = replace(final, arm="diagnostic", variant=slot)
                    record = records[slot] = diag.run(unit, prepared, live, optimizer, generator)
                    self.assertEqual(record["live_before"], before)
                    self.assertEqual(record["live_after"], before)
                    self.assertEqual(record["changed_live_state"], [])
                    self.assertEqual(record["batch_manifest_sha256"], json_sha256(record["batch_manifest"]))
                    self.assertEqual(record["summary"]["complete_pairs"], 8)
                    self.assertEqual(record["final_identity"], final.payload())
                    self.assertEqual(record["final_outcome_sha256"], sha256_file(
                        trainer.journal.runtime / "outcomes" / f"{final.digest}.json"))
                    outcome = trainer.journal.runtime / "outcomes" / f"{unit.digest}.json"
                    self.assertEqual(json.loads(outcome.read_text())["fingerprint_sha256"], seal().digest)
                    old = sha256_file(outcome)
                    with self.assertRaises(DuplicateIdentity):
                        diag.run(unit, prepared, live, optimizer, generator)
                    self.assertEqual(sha256_file(outcome), old)
                self.assertEqual(reads, [0] * 4)
                self.assertEqual(fit_evidence["checkpoint_tail_epochs"], 2 if extended else 0)
                self.assertEqual(records["mid"]["checkpoint"], records["final"]["checkpoint"])
                self.assertNotEqual(records["mid"]["batch_manifest_sha256"], records["final"]["batch_manifest_sha256"])
                self.assertEqual(records["final"]["slots_at_same_epoch"], ["mid", "final"])
                self.assertIsNone(records["mid"]["primary_K"])
                self.assertIsNotNone(records["final"]["primary_K"])
                scores.append((records["final"]["checkpoint"]["model_sha256"], records["final"]["primary_K"]))
        self.assertEqual(scores[0], scores[1])

    def test_contamination_records_terminal_failure(self):
        with scratch_engine(seal()) as trainer:
            final, prepared, _, live, optimizer, generator, _ = fit(trainer, extended=False)
            unit = replace(final, arm="diagnostic", variant="final")
            diag = DiagnosticEngine(trainer.journal)
            with patch.object(diag, "_compute", side_effect=lambda *args: torch.randperm(8, generator=generator)):
                with self.assertRaises(StateContamination):
                    diag.run(unit, prepared, live, optimizer, generator)
            outcome = trainer.journal.runtime / "outcomes" / f"{unit.digest}.json"
            record = json.loads(outcome.read_text())
            self.assertEqual(record["status"], "failed")
            self.assertEqual(record["evidence"]["changed_live_state"], ["training_shuffle_rng"])
            self.assertNotIn("primary_K", record["evidence"])
            with self.assertRaises(DuplicateIdentity):
                diag.run(unit, prepared, live, optimizer, generator)

    def test_m0_slot_is_descriptive_and_tampered_checkpoint_fails(self):
        with scratch_engine(seal()) as trainer:
            final, prepared, _, live, optimizer, generator, evidence = fit(trainer, extended=False, formulation="M0")
            diag = DiagnosticEngine(trainer.journal)
            unit = replace(final, arm="diagnostic", variant="final")
            observed = diag.run(unit, prepared, live, optimizer, generator)
            self.assertIsNotNone(observed["summary"]["K"])
            self.assertIsNone(observed["primary_K"])
            path = trainer.journal.runtime / evidence["diagnostic_checkpoints"]["0"]["path"]
            path.write_bytes(b"tampered synthetic checkpoint")
            with self.assertRaises(ProvenanceError):
                diag.run(replace(unit, variant="epoch0"), prepared, live, optimizer, generator)


    def test_guard_hashes_every_state_category(self):
        with scratch_engine(seal()) as trainer:
            _, _, _, live, optimizer, generator, _ = fit(trainer, extended=False)
            with cpu_seed_scope(57), torch.no_grad():
                before = live_state_hashes(live, optimizer, generator)
                parameter = next(live.parameters())
                parameter.add_(1)
                parameter.grad.add_(1)
                live.guard_fixture.add_(1)
                live.eval()
                optimizer.param_groups[0]["lr"] *= 2
                random.random()
                np.random.random()
                torch.rand(2)
                torch.rand(2, generator=generator)
                after = live_state_hashes(live, optimizer, generator)
            expected = {"model", "buffers", "model_mode", "optimizer", "gradients", "python_rng",
                        "numpy_rng", "torch_cpu_rng", "training_shuffle_rng"}
            self.assertEqual(set(before), expected)
            self.assertEqual({key for key in before if before[key] != after[key]}, expected)

    def test_zero_gradient_is_journalled_with_exact_pair_side_and_task(self):
        with scratch_engine(seal()) as trainer:
            final, prepared, _, live, optimizer, generator, _ = fit(trainer, extended=False)
            unit = replace(final, arm="diagnostic", variant="final")
            aligned = {task: torch.ones(2) for task in RESOURCES}
            zero = aligned | {"MEMORY": torch.zeros(2)}
            with patch("fgcs_strengthening_v03.src.diagnostics.engine.DiagnosticClone.extract",
                       side_effect=[aligned] * 15 + [zero]):
                evidence = DiagnosticEngine(trainer.journal).run(unit, prepared, live, optimizer, generator)
            self.assertEqual(evidence["slot"], "final")
            self.assertEqual(evidence["availability"], "unavailable_zero_gradient")
            self.assertEqual(evidence["summary"]["complete_pairs"], 7)
            self.assertIsNone(evidence["primary_K"])
            self.assertEqual(evidence["pairs"][7]["pair_index"], 7)
            self.assertEqual(evidence["pairs"][7]["zero_gradients"], [{"side": "B", "task": "MEMORY"}])
            persisted, _ = trainer.journal.completed_evidence(unit)
            self.assertEqual(persisted, evidence)
