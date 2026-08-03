"""Feature engineering for lag-based models."""

from __future__ import annotations

import numpy as np
import pandas as pd


def add_calendar_features(df: pd.DataFrame, ts_col: str = "timestamp") -> pd.DataFrame:
    out = df.copy()
    ts = pd.to_datetime(out[ts_col])
    hour = ts.dt.hour + ts.dt.minute / 60.0
    dow = ts.dt.dayofweek.astype(float)
    out["hour_sin"] = np.sin(2 * np.pi * hour / 24.0)
    out["hour_cos"] = np.cos(2 * np.pi * hour / 24.0)
    out["dow_sin"] = np.sin(2 * np.pi * dow / 7.0)
    out["dow_cos"] = np.cos(2 * np.pi * dow / 7.0)
    out["is_weekend"] = (ts.dt.dayofweek >= 5).astype(float)
    out["is_workhours"] = ts.dt.hour.between(9, 17).astype(float)
    return out


def rolling_stats(series: pd.Series, windows: list[int]) -> pd.DataFrame:
    s = series.astype(float)
    frames = {}
    for w in windows:
        r = s.rolling(w, min_periods=max(1, w // 2))
        frames[f"roll_mean_{w}"] = r.mean()
        frames[f"roll_std_{w}"] = r.std()
        frames[f"roll_min_{w}"] = r.min()
        frames[f"roll_max_{w}"] = r.max()
        frames[f"roll_median_{w}"] = r.median()
    return pd.DataFrame(frames, index=series.index)


def ewm_stats(series: pd.Series, spans: list[int]) -> pd.DataFrame:
    s = series.astype(float)
    frames = {}
    for span in spans:
        e = s.ewm(span=span, adjust=False)
        frames[f"ewm_mean_{span}"] = e.mean()
        frames[f"ewm_std_{span}"] = e.std()
    return pd.DataFrame(frames, index=series.index)


def lag_matrix(series: pd.Series, lags: list[int]) -> pd.DataFrame:
    s = series.astype(float)
    return pd.DataFrame({f"lag_{lag}": s.shift(lag) for lag in lags}, index=series.index)


def difference_features(series: pd.Series, lags: list[int] | None = None) -> pd.DataFrame:
    lags = lags or [1]
    s = series.astype(float)
    frames = {"diff_1": s.diff(1)}
    for lag in lags:
        if lag != 1:
            frames[f"diff_{lag}"] = s.diff(lag)
    frames["pct_change_1"] = s.pct_change(1).replace([np.inf, -np.inf], np.nan)
    return pd.DataFrame(frames, index=series.index)


def build_lag_feature_table(
    panel: pd.DataFrame,
    target: str,
    exog: list[str] | None = None,
    context: int = 32,
    rolling_windows: list[int] | None = None,
    ewm_spans: list[int] | None = None,
    use_calendar: bool = True,
    use_diffs: bool = True,
) -> tuple[pd.DataFrame, list[str]]:
    """
    Row t uses only information <= t (lags shift positive).
    Caller must still align targets at t+h and drop rows crossing splits.
    """
    exog = exog or []
    rolling_windows = rolling_windows or [4, 8, 16]
    ewm_spans = ewm_spans or [4, 16]
    lags = list(range(1, context + 1))

    parts = [lag_matrix(panel[target], lags)]
    parts[0].columns = [f"{target}_{c}" for c in parts[0].columns]

    if use_diffs:
        d = difference_features(panel[target])
        d.columns = [f"{target}_{c}" for c in d.columns]
        parts.append(d)

    r = rolling_stats(panel[target], rolling_windows)
    r.columns = [f"{target}_{c}" for c in r.columns]
    parts.append(r)

    e = ewm_stats(panel[target], ewm_spans)
    e.columns = [f"{target}_{c}" for c in e.columns]
    parts.append(e)

    for col in exog:
        if col not in panel.columns:
            raise KeyError(col)
        # limited cross-metric lags to control dimensionality
        xlags = [1, 2, 4, 8]
        xm = lag_matrix(panel[col], xlags)
        xm.columns = [f"{col}_{c}" for c in xm.columns]
        parts.append(xm)

    feat = pd.concat(parts, axis=1)
    if use_calendar:
        cal = add_calendar_features(panel[["timestamp"]].copy())
        feat = pd.concat([feat, cal.drop(columns=["timestamp"], errors="ignore")], axis=1)

    feature_names = list(feat.columns)
    return feat, feature_names
