"""Neural forecasting models (PyTorch)."""

from __future__ import annotations

from typing import Any

import numpy as np

from models.base import BaseForecaster
from models.registry import register


def _torch():
    import torch
    import torch.nn as nn
    return torch, nn


def _prepare_seq(X: np.ndarray) -> np.ndarray:
    X = np.asarray(X, dtype=np.float32)
    if X.ndim == 2:
        # (n, context) -> (n, context, 1)
        X = X[:, :, None]
    return X


class _TorchSeqForecaster(BaseForecaster):
    def __init__(
        self,
        hidden_size: int = 64,
        num_layers: int = 1,
        dropout: float = 0.0,
        epochs: int = 20,
        batch_size: int = 256,
        lr: float = 1e-3,
        patience: int = 5,
        **kwargs: Any,
    ):
        super().__init__(**kwargs)
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.dropout = dropout
        self.epochs = epochs
        self.batch_size = batch_size
        self.lr = lr
        self.patience = patience
        self.device = "cpu"

    def _build_net(self, n_features: int):
        raise NotImplementedError

    def save(self, path):
        """Persist via state_dict to avoid pickling nested nn.Module classes."""
        import json
        from pathlib import Path
        import torch

        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        torch.save(
            {
                "class": self.__class__.__name__,
                "name": self.name,
                "horizon": self.horizon,
                "context_length": self.context_length,
                "seed": self.seed,
                "n_features": getattr(self, "n_features_", None),
                "metadata": self.metadata.to_dict(),
                "state_dict": self.net_.state_dict(),
                "hyper": {
                    k: getattr(self, k)
                    for k in (
                        "hidden_size",
                        "num_layers",
                        "dropout",
                        "epochs",
                        "batch_size",
                        "lr",
                        "patience",
                        "kernel_size",
                    )
                    if hasattr(self, k)
                },
            },
            path / "model.pt",
        )
        (path / "metadata.json").write_text(json.dumps(self.metadata.to_dict(), indent=2))

    def fit(self, X, y, X_val=None, y_val=None):
        torch, nn = _torch()
        torch.manual_seed(self.seed)
        np.random.seed(self.seed)

        X_arr = _prepare_seq(X)
        y_arr = np.asarray(y, dtype=np.float32)
        if y_arr.ndim == 1:
            y_arr = y_arr[:, None]
        Xv = _prepare_seq(X_val) if X_val is not None else None
        yv = np.asarray(y_val, dtype=np.float32) if y_val is not None else None
        if yv is not None and yv.ndim == 1:
            yv = yv[:, None]
        n_features = X_arr.shape[-1]
        self.n_features_ = n_features

        def _fit():
            self.net_ = self._build_net(n_features).to(self.device)
            opt = torch.optim.Adam(self.net_.parameters(), lr=self.lr)
            loss_fn = nn.MSELoss()

            def batches(Xa, ya):
                idx = np.arange(len(Xa))
                np.random.shuffle(idx)
                for i in range(0, len(idx), self.batch_size):
                    sl = idx[i : i + self.batch_size]
                    yield (
                        torch.tensor(Xa[sl], device=self.device),
                        torch.tensor(ya[sl], device=self.device),
                    )

            best_state = None
            best_val = float("inf")
            stale = 0

            for _epoch in range(self.epochs):
                self.net_.train()
                for xb, yb in batches(X_arr, y_arr):
                    opt.zero_grad()
                    pred = self.net_(xb)
                    loss = loss_fn(pred, yb)
                    loss.backward()
                    opt.step()
                if Xv is not None:
                    self.net_.eval()
                    with torch.no_grad():
                        pv = self.net_(torch.tensor(Xv, device=self.device)).cpu().numpy()
                        vloss = float(np.mean((pv - yv) ** 2))
                    if vloss < best_val - 1e-8:
                        best_val = vloss
                        best_state = {k: v.detach().cpu().clone() for k, v in self.net_.state_dict().items()}
                        stale = 0
                    else:
                        stale += 1
                        if stale >= self.patience:
                            break
            if best_state is not None:
                self.net_.load_state_dict(best_state)
            self.metadata.n_parameters = int(sum(p.numel() for p in self.net_.parameters()))
            return self

        return self._timed_fit(_fit)

    def predict(self, X):
        torch, _ = _torch()
        X_arr = _prepare_seq(X)

        def _predict(_X):
            self.net_.eval()
            with torch.no_grad():
                pred = self.net_(torch.tensor(X_arr, device=self.device)).cpu().numpy()
            if self.horizon == 1:
                return pred.reshape(-1)
            return pred

        return self._timed_predict(_predict, X_arr)


@register("mlp")
class MLPForecaster(_TorchSeqForecaster):
    name = "mlp"

    def _build_net(self, n_features: int):
        torch, nn = _torch()
        context = self.context_length
        in_dim = context * n_features
        hidden = self.hidden_size

        class Net(nn.Module):
            def __init__(self_inner):
                super().__init__()
                self_inner.net = nn.Sequential(
                    nn.Flatten(),
                    nn.Linear(in_dim, hidden),
                    nn.ReLU(),
                    nn.Dropout(self.dropout),
                    nn.Linear(hidden, hidden),
                    nn.ReLU(),
                    nn.Linear(hidden, self.horizon),
                )

            def forward(self_inner, x):
                return self_inner.net(x)

        return Net()


@register("lstm")
class LSTMForecaster(_TorchSeqForecaster):
    name = "lstm"

    def _build_net(self, n_features: int):
        torch, nn = _torch()

        class Net(nn.Module):
            def __init__(self_inner):
                super().__init__()
                self_inner.rnn = nn.LSTM(
                    input_size=n_features,
                    hidden_size=self.hidden_size,
                    num_layers=self.num_layers,
                    batch_first=True,
                    dropout=self.dropout if self.num_layers > 1 else 0.0,
                )
                self_inner.head = nn.Linear(self.hidden_size, self.horizon)

            def forward(self_inner, x):
                out, _ = self_inner.rnn(x)
                return self_inner.head(out[:, -1, :])

        return Net()


@register("gru")
class GRUForecaster(_TorchSeqForecaster):
    name = "gru"

    def _build_net(self, n_features: int):
        torch, nn = _torch()

        class Net(nn.Module):
            def __init__(self_inner):
                super().__init__()
                self_inner.rnn = nn.GRU(
                    input_size=n_features,
                    hidden_size=self.hidden_size,
                    num_layers=self.num_layers,
                    batch_first=True,
                    dropout=self.dropout if self.num_layers > 1 else 0.0,
                )
                self_inner.head = nn.Linear(self.hidden_size, self.horizon)

            def forward(self_inner, x):
                out, _ = self_inner.rnn(x)
                return self_inner.head(out[:, -1, :])

        return Net()


@register("tcn")
class TCNForecaster(_TorchSeqForecaster):
    """Simple dilated causal TCN-style 1D CNN."""

    name = "tcn"

    def _build_net(self, n_features: int):
        torch, nn = _torch()

        class CausalConv(nn.Module):
            def __init__(self_inner, in_ch, out_ch, dilation):
                super().__init__()
                self_inner.pad = dilation
                self_inner.conv = nn.Conv1d(in_ch, out_ch, kernel_size=2, dilation=dilation)

            def forward(self_inner, x):
                # x: (b, c, t)
                x = nn.functional.pad(x, (self_inner.pad, 0))
                return self_inner.conv(x)

        class Net(nn.Module):
            def __init__(self_inner):
                super().__init__()
                channels = self.hidden_size
                self_inner.blocks = nn.Sequential(
                    CausalConv(n_features, channels, 1),
                    nn.ReLU(),
                    CausalConv(channels, channels, 2),
                    nn.ReLU(),
                    CausalConv(channels, channels, 4),
                    nn.ReLU(),
                )
                self_inner.head = nn.Linear(channels, self.horizon)

            def forward(self_inner, x):
                # (b, t, f) -> (b, f, t)
                h = x.transpose(1, 2)
                h = self_inner.blocks(h)
                return self_inner.head(h[:, :, -1])

        return Net()


def _make_dlinear_net(context: int, horizon: int, kernel_size: int):
    torch, nn = _torch()
    k = kernel_size if kernel_size % 2 == 1 else kernel_size + 1

    class DLinearNet(nn.Module):
        def __init__(self):
            super().__init__()
            self.linear_seasonal = nn.Linear(context, horizon)
            self.linear_trend = nn.Linear(context, horizon)
            self.avg = nn.AvgPool1d(kernel_size=k, stride=1, padding=k // 2, count_include_pad=False)

        def forward(self, x):
            trend = self.avg(x.unsqueeze(1)).squeeze(1)
            if trend.shape[1] > x.shape[1]:
                trend = trend[:, : x.shape[1]]
            elif trend.shape[1] < x.shape[1]:
                pad = x.shape[1] - trend.shape[1]
                trend = nn.functional.pad(trend, (0, pad))
            seasonal = x - trend
            return self.linear_seasonal(seasonal) + self.linear_trend(trend)

    return DLinearNet()


@register("dlinear")
class DLinearForecaster(BaseForecaster):
    """DLinear-style: seasonal/trend decomposition via moving avg + linear.

    Train-only standardization of the univariate series and targets is required
    for large-magnitude telemetry (e.g. cluster_UM ~1e11). Without it, float32
    MSE training collapses to large negative predictions.
    """

    name = "dlinear"

    def __init__(
        self,
        kernel_size: int = 25,
        epochs: int = 30,
        batch_size: int = 256,
        lr: float = 1e-3,
        patience: int = 5,
        timeout_sec: float | None = 180.0,
        max_batches_per_epoch: int | None = None,
        num_threads: int = 1,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.kernel_size = kernel_size
        self.epochs = epochs
        self.batch_size = batch_size
        self.lr = lr
        self.patience = patience
        self.timeout_sec = timeout_sec
        self.max_batches_per_epoch = max_batches_per_epoch
        self.num_threads = num_threads
        self.runtime_meta_: dict[str, Any] = {}

    def _fit_scaler(self, series: np.ndarray, y: np.ndarray) -> None:
        s = series.reshape(-1)
        s = s[np.isfinite(s)]
        yf = y.reshape(-1)
        yf = yf[np.isfinite(yf)]
        self.x_mean_ = float(np.mean(s)) if len(s) else 0.0
        self.x_std_ = float(np.std(s)) if len(s) else 1.0
        if not np.isfinite(self.x_std_) or self.x_std_ < 1e-12:
            self.x_std_ = 1.0
        self.y_mean_ = float(np.mean(yf)) if len(yf) else 0.0
        self.y_std_ = float(np.std(yf)) if len(yf) else 1.0
        if not np.isfinite(self.y_std_) or self.y_std_ < 1e-12:
            self.y_std_ = 1.0

    def _scale_x(self, series: np.ndarray) -> np.ndarray:
        return ((series - self.x_mean_) / self.x_std_).astype(np.float32)

    def _scale_y(self, y: np.ndarray) -> np.ndarray:
        return ((y - self.y_mean_) / self.y_std_).astype(np.float32)

    def _inverse_y(self, y_s: np.ndarray) -> np.ndarray:
        return y_s.astype(np.float64) * self.y_std_ + self.y_mean_

    def fit(self, X, y, X_val=None, y_val=None):
        import time as _time

        torch, nn = _torch()
        try:
            torch.set_num_threads(max(1, int(self.num_threads)))
        except Exception:
            pass
        torch.manual_seed(self.seed)

        t_prep0 = _time.perf_counter()
        X_arr = np.ascontiguousarray(_prepare_seq(X))
        y_arr = np.ascontiguousarray(np.asarray(y, dtype=np.float64))
        if y_arr.ndim == 1:
            y_arr = y_arr[:, None]
        series = np.ascontiguousarray(X_arr[:, :, 0], dtype=np.float64)
        self._fit_scaler(series, y_arr)
        series_s = self._scale_x(series)
        y_s = self._scale_y(y_arr)
        context = series_s.shape[1]
        prep_s = _time.perf_counter() - t_prep0

        Xv = None
        yv = None
        if X_val is not None and y_val is not None and len(X_val):
            Xv = self._scale_x(np.ascontiguousarray(_prepare_seq(X_val)[:, :, 0], dtype=np.float64))
            yv_raw = np.ascontiguousarray(np.asarray(y_val, dtype=np.float64))
            if yv_raw.ndim == 1:
                yv_raw = yv_raw[:, None]
            yv = self._scale_y(yv_raw)

        def _fit():
            t0 = _time.perf_counter()
            self.net_ = _make_dlinear_net(context, self.horizon, self.kernel_size)
            init_s = _time.perf_counter() - t0
            opt = torch.optim.Adam(self.net_.parameters(), lr=self.lr)
            loss_fn = nn.MSELoss()
            Xt = torch.tensor(series_s, dtype=torch.float32)
            yt = torch.tensor(y_s, dtype=torch.float32)
            best_state = None
            best_val = float("inf")
            bad = 0
            epochs_ran = 0
            timed_out = False
            epoch_times = []
            for ep in range(self.epochs):
                if self.timeout_sec is not None and (_time.perf_counter() - t0) > self.timeout_sec:
                    timed_out = True
                    break
                ep0 = _time.perf_counter()
                self.net_.train()
                perm = torch.randperm(len(Xt))
                n_batches = 0
                for i in range(0, len(Xt), self.batch_size):
                    if self.max_batches_per_epoch is not None and n_batches >= self.max_batches_per_epoch:
                        break
                    if self.timeout_sec is not None and (_time.perf_counter() - t0) > self.timeout_sec:
                        timed_out = True
                        break
                    sl = perm[i : i + self.batch_size]
                    opt.zero_grad()
                    pred = self.net_(Xt[sl])
                    loss = loss_fn(pred, yt[sl])
                    loss.backward()
                    opt.step()
                    n_batches += 1
                epochs_ran += 1
                epoch_times.append(_time.perf_counter() - ep0)
                if timed_out:
                    break
                if Xv is not None:
                    self.net_.eval()
                    with torch.no_grad():
                        pv = self.net_(torch.tensor(Xv, dtype=torch.float32))
                        vloss = float(loss_fn(pv, torch.tensor(yv, dtype=torch.float32)).item())
                    if vloss < best_val - 1e-9:
                        best_val = vloss
                        best_state = {k: v.detach().cpu().clone() for k, v in self.net_.state_dict().items()}
                        bad = 0
                    else:
                        bad += 1
                        if bad >= self.patience:
                            break
            if best_state is not None:
                self.net_.load_state_dict(best_state)
            self.metadata.n_parameters = int(sum(p.numel() for p in self.net_.parameters()))
            self.runtime_meta_ = {
                "prep_sec": prep_s,
                "init_sec": init_s,
                "epochs_ran": epochs_ran,
                "epoch_sec_mean": float(np.mean(epoch_times)) if epoch_times else float("nan"),
                "timed_out": timed_out,
                "early_stopped": best_state is not None and epochs_ran < self.epochs and not timed_out,
                "n_train": int(len(Xt)),
                "timeout_sec": self.timeout_sec,
                "num_threads": self.num_threads,
                "x_mean": self.x_mean_,
                "x_std": self.x_std_,
                "y_mean": self.y_mean_,
                "y_std": self.y_std_,
                "scaling": "train_only_standardize",
            }
            self.metadata.config["runtime"] = dict(self.runtime_meta_)
            return self

        return self._timed_fit(_fit)

    def predict(self, X):
        torch, _ = _torch()
        X_raw = np.ascontiguousarray(_prepare_seq(X)[:, :, 0], dtype=np.float64)
        X_arr = self._scale_x(X_raw)

        def _predict(_X):
            self.net_.eval()
            with torch.no_grad():
                outs = []
                bs = max(256, int(self.batch_size))
                for i in range(0, len(X_arr), bs):
                    outs.append(self.net_(torch.tensor(X_arr[i : i + bs], dtype=torch.float32)).cpu().numpy())
                pred_s = np.concatenate(outs, axis=0)
            pred = self._inverse_y(pred_s)
            if self.horizon == 1:
                return pred.reshape(-1)
            return pred

        return self._timed_predict(_predict, X_arr)


    def save(self, path):
        """Save state_dict instead of pickling dynamic modules when needed."""
        import json
        from pathlib import Path
        import torch

        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        torch.save(
            {
                "state_dict": self.net_.state_dict(),
                "horizon": self.horizon,
                "context_length": self.context_length,
                "kernel_size": self.kernel_size,
                "seed": self.seed,
                "metadata": self.metadata.to_dict(),
                "x_mean": getattr(self, "x_mean_", 0.0),
                "x_std": getattr(self, "x_std_", 1.0),
                "y_mean": getattr(self, "y_mean_", 0.0),
                "y_std": getattr(self, "y_std_", 1.0),
            },
            path / "dlinear.pt",
        )
        (path / "metadata.json").write_text(json.dumps(self.metadata.to_dict(), indent=2))

