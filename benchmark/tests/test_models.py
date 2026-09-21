from __future__ import annotations

import numpy as np
import torch

from benchmark.src.models import (
    DLinearForecaster,
    LightGBMForecaster,
    PersistenceForecaster,
    RidgeForecaster,
    TCNForecaster,
)
from benchmark.src.models.tcn import TCNNetwork
from benchmark.src.windows import (
    build_windows,
    finite_feature_origins,
    joint_eligible_origins,
)


def synthetic_data():
    rng = np.random.default_rng(7)
    X = rng.normal(size=(32, 32, 3)).astype(np.float32)
    y = np.column_stack(
        [X[:, -1, 0] + 0.1 * lead for lead in range(8)]
    ).astype(np.float32)
    return X, y


def test_all_model_output_shapes():
    X, y = synthetic_data()
    models = [
        PersistenceForecaster(),
        RidgeForecaster(alpha=1.0),
        LightGBMForecaster(num_leaves=15, learning_rate=0.05, n_estimators=5),
        DLinearForecaster(
            context_length=32,
            input_channels=3,
            seed=0,
            max_epochs=1,
            patience=1,
            batch_size=16,
            device="cpu",
        ),
        TCNForecaster(
            input_channels=3,
            seed=0,
            channels=(8, 8),
            max_epochs=1,
            patience=1,
            batch_size=16,
            device="cpu",
        ),
    ]
    for model in models:
        model.fit(X[:24], y[:24], X[24:], y[24:])
        assert model.predict(X[24:]).shape == (8, 8)


def test_tcn_is_causal():
    torch.manual_seed(0)
    network = TCNNetwork(
        input_channels=2, channels=(4, 4), kernel_size=3, dropout=0.0
    )
    network.eval()
    original = torch.randn(1, 32, 2)
    changed = original.clone()
    changed[:, 20:, :] += 1000
    with torch.no_grad():
        original_features = network.forward_features(original)
        changed_features = network.forward_features(changed)
    assert torch.allclose(
        original_features[:, :, :20],
        changed_features[:, :, :20],
        atol=1e-6,
    )


def test_feature_parity_same_origins_and_targets(panel):
    origins = finite_feature_origins(
        panel,
        "machine01",
        "F5_THROUGHPUT_LOMO_MEDIAN",
        32,
        joint_eligible_origins(panel, "machine01"),
    )[:16]
    local = build_windows(panel, "machine01", "F0_LOCAL", 32, origins)
    context = build_windows(
        panel, "machine01", "F5_THROUGHPUT_LOMO_MEDIAN", 32, origins
    )
    assert np.array_equal(local.origin_indices, context.origin_indices)
    assert np.array_equal(local.y, context.y)
    assert local.X.shape[:2] == context.X.shape[:2]
    assert local.X.shape[-1] == 1
    assert context.X.shape[-1] == 3


def test_target_is_not_scaled_by_ridge():
    X, y = synthetic_data()
    y_native = y * 20 + 50
    model = RidgeForecaster(alpha=1.0).fit(X, y_native)
    prediction = model.predict(X)
    assert prediction.shape == y_native.shape
    assert prediction.mean() > 10
