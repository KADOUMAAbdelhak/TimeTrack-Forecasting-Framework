import unittest

from fgcs_strengthening_v03.src.models.lstm import LSTM
from fgcs_strengthening_v03.src.systems import deployment_rows
from fgcs_strengthening_v03.tests.systems_fixtures import complement, physical, plan_for
from fgcs_strengthening_v03.tests.training_fixtures import identity
from dataclasses import replace


class SystemsFootprintTests(unittest.TestCase):
    def test_model_parameter_and_tensor_bytes(self):
        counts = {"S1": 50757, "S2": 51525, "M0": 51732, "M1": 52500}
        for formulation, count in counts.items():
            unit = identity(formulation, phase="final")
            model = LSTM(formulation=formulation, block=unit.block, tasks=unit.tasks, hidden_size=64)
            state = physical(unit, model)
            self.assertEqual(state.trainable_parameters, count)
            self.assertEqual(state.raw_tensor_bytes, count * 4)
            self.assertGreater(state.encoded_bytes, state.raw_tensor_bytes)
        unit = replace(identity("M0", phase="final"), arm="capacity", hidden_size=128)
        model = LSTM(formulation="M0", block=unit.block, tasks=unit.tasks, hidden_size=128)
        self.assertEqual(physical(unit, model).trainable_parameters, 201748)

    def test_independent_shared_and_task_checkpoint_costs(self):
        for formulation, task_control, expected in (("S1", False, (4, 4)), ("M1", False, (1, 1)),
                                                     ("M1", True, (2, 4))):
            deployment = complement(formulation, [], task_control=task_control)
            states, row = deployment_rows(deployment, plan_for(deployment).binding)
            self.assertEqual((row.physical_checkpoint_count, row.logical_target_models), expected)
            self.assertEqual(row.total_trainable_parameters, expected[0])
            self.assertEqual(row.total_deployed_bytes, sum(state.uncompressed_model_bytes for state in states))
            self.assertEqual(sum(row.optimizer_state_bytes_by_fit.values()), 123 * (4 if formulation == "S1" else 1))
            self.assertTrue(all(state.raw_tensor_bytes == 8 for state in states))


import io as _io
import zipfile as _zipfile
from hashlib import sha256 as _sha256

from fgcs_strengthening_v03.src.provenance import ProvenanceError
from fgcs_strengthening_v03.src.systems import CheckpointRef, torch_footprint
from fgcs_strengthening_v03.src.training import _encode
from fgcs_strengthening_v03.tests.systems_fixtures import TinyModel
from fgcs_strengthening_v03.tests.training_fixtures import digest


class SystemsFootprintIntegrityTests(unittest.TestCase):
    def test_checkpoint_bytes_must_match_and_remain_uncompressed(self):
        unit = identity("M1", phase="final")
        model = TinyModel(unit.tasks, [])
        encoded = _encode(model.state_dict())
        ref = CheckpointRef(unit, _sha256(encoded).hexdigest(), digest("outcome"), 1)
        state = torch_footprint(ref, model, encoded, optimizer_state_bytes=None)
        self.assertEqual((state.trainable_parameters, state.raw_tensor_bytes, state.encoded_bytes),
                         (1, 8, len(encoded)))
        self.assertIsNone(state.optimizer_state_bytes)
        with self.assertRaises(ProvenanceError):
            torch_footprint(ref, model, encoded + b"x")
        buffer = _io.BytesIO()
        with _zipfile.ZipFile(buffer, "w", compression=_zipfile.ZIP_DEFLATED) as stream:
            stream.writestr("archive/data.pkl", b"0" * 64)
        compressed = buffer.getvalue()
        with self.assertRaises(ProvenanceError):
            torch_footprint(replace(ref, checkpoint_sha256=_sha256(compressed).hexdigest()), model, compressed)

    def test_optimizer_state_is_reported_but_never_deployed(self):
        deployment = complement("M1", [])
        plan = plan_for(deployment)
        states, row = deployment_rows(deployment, plan.binding)
        self.assertEqual(row.total_deployed_bytes, states[0].uncompressed_model_bytes)
        self.assertEqual(states[0].optimizer_state_bytes, 123)
        self.assertEqual(row.optimizer_state_bytes_by_fit, {deployment.refs[0].identity.digest: 123})
        other = complement("M0", [])
        with self.assertRaises(ProvenanceError):
            deployment_rows(other, plan.binding)
