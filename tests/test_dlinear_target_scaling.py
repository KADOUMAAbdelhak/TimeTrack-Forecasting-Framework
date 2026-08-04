"""Regression: DLinear must inverse-transform large-scale targets correctly."""

from __future__ import annotations

import numpy as np

from models import forecasting as F


def test_dlinear_large_scale_target_roundtrip():
    rng = np.random.default_rng(0)
    n, ctx, h = 400, 32, 1
    # Synthetic large-magnitude AR(1)-like series (~1e11)
    level = 1.2e11
    noise = rng.normal(0, 1e9, size=n + ctx + h)
    series = level + np.cumsum(noise) * 0.01
    X, y = [], []
    for o in range(ctx - 1, n + ctx - 1):
        X.append(series[o - ctx + 1 : o + 1])
        y.append(series[o + h])
    X = np.asarray(X, dtype=float)[:, :, None]
    y = np.asarray(y, dtype=float)
    n_tr = int(0.7 * len(X))
    n_va = int(0.85 * len(X))
    m = F.build_model(
        "dlinear",
        horizon=1,
        context_length=ctx,
        seed=0,
        epochs=40,
        patience=8,
        num_threads=1,
        max_batches_per_epoch=50,
    )
    m.fit(X[:n_tr], y[:n_tr], X[n_tr:n_va], y[n_tr:n_va])
    pred = np.asarray(m.predict(X[n_va:]), dtype=float).reshape(-1)
    yt = y[n_va : n_va + len(pred)]
    assert np.all(np.isfinite(pred))
    # Predictions must be in the same magnitude ballpark as targets
    med_y = float(np.median(np.abs(yt)))
    med_p = float(np.median(np.abs(pred)))
    assert 0.1 * med_y < med_p < 10 * med_y, (med_y, med_p)
    mae = float(np.mean(np.abs(yt - pred)))
    pers = float(np.mean(np.abs(yt - X[n_va : n_va + len(pred), -1, 0])))
    # Should not be pathologically worse than persistence after scaling fix
    assert mae < 5.0 * pers, (mae, pers)
    assert hasattr(m, "y_mean_") and hasattr(m, "y_std_")
    assert m.y_std_ > 0
