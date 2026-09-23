from __future__ import annotations

import torch

from benchmark.neural_v2.src.models import (
    DLinear,
    FullReceptiveFieldTCN,
    LSTMForecaster,
    PatchTST,
    receptive_field,
)


def test_all_models_return_eight_outputs_for_f0_and_f1():
    for channels in (1, 2):
        values = torch.randn(3, 64, channels)
        models = [
            DLinear(64, channels),
            LSTMForecaster(channels),
            FullReceptiveFieldTCN(channels),
            PatchTST(64, channels),
        ]
        for model in models:
            model.eval()
            with torch.no_grad():
                assert model(values).shape == (3, 8)


def test_dlinear_channel_handling_is_explicit():
    f0 = DLinear(32, 1)
    f1 = DLinear(32, 2)
    assert f0.channel_projection.in_features == 1
    assert f1.channel_projection.in_features == 2


def test_lstm_is_unidirectional_and_has_frozen_shape():
    model = LSTMForecaster(2)
    assert model.lstm.hidden_size == 64
    assert model.lstm.num_layers == 2
    assert model.lstm.dropout == 0.1
    assert not model.lstm.bidirectional


def test_tcn_receptive_field_is_exact_and_covers_maximum_context():
    assert receptive_field() == 253
    assert receptive_field() >= 128


def test_tcn_perturbation_causality():
    torch.manual_seed(0)
    model = FullReceptiveFieldTCN(2, dropout=0.0)
    model.eval()
    original = torch.randn(1, 128, 2)
    changed = original.clone()
    changed[:, 80:, :] += 1000
    with torch.no_grad():
        original_features = model.forward_features(original)
        changed_features = model.forward_features(changed)
    assert torch.allclose(
        original_features[:, :, :80], changed_features[:, :, :80], atol=1e-6
    )


def test_patchtst_patch_construction():
    model = PatchTST(64, 2)
    values = torch.arange(128, dtype=torch.float32).reshape(1, 64, 2)
    patches = model.construct_patches(values)
    assert model.patch_count == 15
    assert patches.shape == (1, 2, 15, 8)
    assert torch.equal(patches[0, 0, 0], values[0, :8, 0])
    assert torch.equal(patches[0, 0, 1], values[0, 4:12, 0])


def test_patchtst_rejects_nonhistory_shape():
    model = PatchTST(64, 1)
    try:
        model(torch.randn(2, 65, 1))
    except ValueError as error:
        assert "[batch, L, channels]" in str(error)
    else:
        raise AssertionError("PatchTST accepted an input outside its history")
