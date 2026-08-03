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
    """DLinear-style: seasonal/trend decomposition via moving avg + linear."""

    name = "dlinear"

    def __init__(self, kernel_size: int = 25, epochs: int = 30, batch_size: int = 256, lr: float = 1e-3, **kwargs):
        super().__init__(**kwargs)
        self.kernel_size = kernel_size
        self.epochs = epochs
        self.batch_size = batch_size
        self.lr = lr

    def fit(self, X, y, X_val=None, y_val=None):
        torch, nn = _torch()
        torch.manual_seed(self.seed)

        X_arr = _prepare_seq(X)
        y_arr = np.asarray(y, dtype=np.float32)
        if y_arr.ndim == 1:
            y_arr = y_arr[:, None]
        series = X_arr[:, :, 0]
        context = series.shape[1]

        def _fit():
            self.net_ = _make_dlinear_net(context, self.horizon, self.kernel_size)
            opt = torch.optim.Adam(self.net_.parameters(), lr=self.lr)
            loss_fn = nn.MSELoss()
            Xt = torch.tensor(series)
            yt = torch.tensor(y_arr)
            for _ in range(self.epochs):
                self.net_.train()
                perm = torch.randperm(len(Xt))
                for i in range(0, len(Xt), self.batch_size):
                    sl = perm[i : i + self.batch_size]
                    opt.zero_grad()
                    pred = self.net_(Xt[sl])
                    loss = loss_fn(pred, yt[sl])
                    loss.backward()
                    opt.step()
            self.metadata.n_parameters = int(sum(p.numel() for p in self.net_.parameters()))
            return self

        return self._timed_fit(_fit)

    def predict(self, X):
        torch, _ = _torch()
        X_arr = _prepare_seq(X)[:, :, 0]

        def _predict(_X):
            self.net_.eval()
            with torch.no_grad():
                pred = self.net_(torch.tensor(X_arr)).cpu().numpy()
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
            },
            path / "dlinear.pt",
        )
        (path / "metadata.json").write_text(json.dumps(self.metadata.to_dict(), indent=2))

