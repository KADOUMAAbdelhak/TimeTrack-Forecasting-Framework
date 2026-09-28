from __future__ import annotations

import numpy as np
import pytest
import torch

from src import RESOURCE_ORDER
from src.models import MultiTargetLSTM
from src.selection import SelectionRow, select_context
from src.training import build_model, encoder_parameter_count, fit_final_fixed_epochs, fit_inner, head_parameter_count, parameter_count, resource_losses, set_seed
from src.transforms import ResourceScaler


def test_s1_shape():
    assert build_model("S1", 1)(torch.zeros(3, 9, 1)).shape == (3, 5)


def test_s2_shape():
    assert build_model("S2", 4)(torch.zeros(3, 9, 4)).shape == (3, 5)


def test_m1_shape_shared_encoder_independent_heads():
    model = build_model("M1", 4)
    assert model(torch.zeros(3, 9, 4)).shape == (3, 4, 5)
    assert isinstance(model, MultiTargetLSTM)
    assert len(model.heads) == 4
    assert len({id(head) for head in model.heads}) == 4


def test_parameter_accounting():
    s1, s2, m1 = build_model("S1", 1), build_model("S2", 4), build_model("M1", 4)
    assert parameter_count(s1) == 50_757
    assert 4 * parameter_count(s1) == 203_028
    assert parameter_count(s2) == 51_525
    assert 4 * parameter_count(s2) == 206_100
    assert encoder_parameter_count(m1) == 51_200
    assert head_parameter_count(m1) == 1_300
    assert parameter_count(m1) == 52_500


def test_equal_m1_task_loss():
    prediction = torch.zeros(2, 4, 5)
    target = torch.stack([torch.full((2, 5), float(value)) for value in (1, 2, 3, 4)], dim=1)
    joint, losses = resource_losses(prediction, target, "M1", None)
    assert torch.isclose(joint, torch.stack(list(losses.values())).mean())


def test_seed_behavior_is_reproducible():
    set_seed(7); first = torch.rand(4)
    set_seed(7); second = torch.rand(4)
    assert torch.equal(first, second)


def test_context_selection_smaller_tie():
    rows = [
        SelectionRow("S1", context, seed, np.ones(5), seed + 1)
        for context in (4, 9, 18) for seed in (0, 1, 2)
    ]
    result = select_context(rows, "S1")
    assert result.context_length == 4
    assert result.best_epoch_by_seed == {0: 1, 1: 2, 2: 3}


def test_m1_selection_objective_shape():
    rows = [
        SelectionRow("M1", context, seed, np.full((4, 5), context), 2)
        for context in (4, 9, 18) for seed in (0, 1, 2)
    ]
    assert select_context(rows, "M1").context_length == 4


def test_iqr_zero_stop():
    with pytest.raises(ValueError, match="IQR_ZERO_STOP"):
        ResourceScaler.fit(np.ones((10, 4)))


def test_physical_inverse_and_projection():
    values = np.column_stack([
        np.arange(1, 101), np.arange(1, 101), np.arange(101, 201), np.arange(2, 102)
    ])
    scaler = ResourceScaler.fit(values)
    scaled = np.full((4, 5), -100.0)
    projected, fraction, unclipped = scaler.inverse_one(scaled, "THROUGHPUT")
    assert np.all(projected >= 0)
    assert fraction == 1.0
    assert np.all(unclipped < 0)


def test_fixed_five_epoch_inner_lifecycle():
    rng = np.random.default_rng(0)
    X = rng.normal(size=(32, 4, 1)).astype(np.float32)
    y = rng.normal(size=(32, 5)).astype(np.float32)
    result = fit_inner("S1", "CPU", 0, X, y, X[:8], y[:8], fixed_epochs=5, batch_size=16)
    assert result.epochs_trained == 5
    assert len(result.epoch_logs) == 5


def test_final_refit_has_no_validation_prediction():
    rng = np.random.default_rng(1)
    X = rng.normal(size=(16, 4, 1)).astype(np.float32)
    y = rng.normal(size=(16, 5)).astype(np.float32)
    result = fit_final_fixed_epochs("S1", "CPU", 0, X, y, 1)
    assert result.epochs_trained == 1
    assert result.validation_prediction is None
    assert result.epoch_validation_seconds == []

