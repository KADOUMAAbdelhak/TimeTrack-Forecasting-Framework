from __future__ import annotations

import inspect

import numpy as np
import torch

from src.data import RESOURCE_ORDER
from src.models import MultiTargetLSTM, SingleTargetLSTM
from src.training import build_model, encoder_parameter_count, fit_final_fixed_epochs, fit_inner, head_parameter_count, parameter_count, resource_losses, set_seed


def test_s1_output_shape(): assert SingleTargetLSTM(1)(torch.zeros(3, 32, 1)).shape == (3, 8)
def test_s2_output_shape(): assert SingleTargetLSTM(4)(torch.zeros(3, 32, 4)).shape == (3, 8)
def test_m1_output_shape(): assert MultiTargetLSTM()(torch.zeros(3, 32, 4)).shape == (3, 4, 8)
def test_s1_only_one_channel(): assert build_model("S1", 1).input_channels == 1
def test_s2_all_channels(): assert build_model("S2", 4).input_channels == 4
def test_m1_all_channels(): assert build_model("M1", 4).input_channels == 4
def test_m1_shared_encoder_single_instance(): assert isinstance(MultiTargetLSTM().encoder, torch.nn.LSTM)
def test_m1_heads_are_separate():
    model = MultiTargetLSTM(); assert len(model.heads) == 4 and len({id(head) for head in model.heads}) == 4
def test_plain_architecture_has_no_attention_or_adapters():
    names = " ".join(name.lower() for name, _ in MultiTargetLSTM().named_modules())
    assert "attention" not in names and "adapter" not in names and "gate" not in names


def test_equal_four_resource_loss():
    pred = torch.zeros(2, 4, 8); target = torch.stack([torch.full((2, 8), x) for x in (1., 2., 3., 4.)], dim=1)
    joint, parts = resource_losses(pred, target, "M1", None)
    assert set(parts) == set(RESOURCE_ORDER)
    assert torch.isclose(joint, torch.tensor((1 + 4 + 9 + 16) / 4))


def test_parameter_accounting_exact():
    s1, s2, m1 = SingleTargetLSTM(1), SingleTargetLSTM(4), MultiTargetLSTM()
    assert parameter_count(s1) == 50952
    assert parameter_count(s2) == 51720
    assert encoder_parameter_count(m1) == 51200
    assert head_parameter_count(m1) == 2080
    assert parameter_count(m1) == 53280


def test_seed_determinism():
    set_seed(7); first = SingleTargetLSTM(1).state_dict()
    set_seed(7); second = SingleTargetLSTM(1).state_dict()
    assert all(torch.equal(first[key], second[key]) for key in first)


def test_resource_loss_logging_and_five_fixed_epochs():
    rng = np.random.default_rng(1); X = rng.normal(size=(8, 8, 4)).astype("float32"); y = rng.normal(size=(8, 4, 8)).astype("float32")
    result = fit_inner("M1", None, 0, X, y, X, y, fixed_epochs=5, batch_size=8)
    assert result.epochs_trained == 5 and len(result.epoch_logs) == 5
    assert set(result.epoch_logs[0]["train_resource_mse"]) == set(RESOURCE_ORDER)
    assert np.isclose(sum(result.epoch_logs[0]["train_loss_share"].values()), 1)


def test_final_refit_has_no_test_or_validation_api():
    parameters = inspect.signature(fit_final_fixed_epochs).parameters
    assert not any("test" in name or "validation" in name for name in parameters)


def test_fixed_epoch_refit_lifecycle():
    rng = np.random.default_rng(2); X = rng.normal(size=(8, 8, 1)).astype("float32"); y = rng.normal(size=(8, 8)).astype("float32")
    result = fit_final_fixed_epochs("S1", "CPU", 0, X, y, 1, batch_size=8)
    assert result.epochs_trained == result.best_epoch == 1 and result.validation_prediction is None
