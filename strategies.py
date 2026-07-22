"""
strategies.py
--------------
Trading strategy signal generators. Each function takes a price DataFrame
(with a 'Close' column) plus strategy-specific parameters, and returns the
same DataFrame with an added 'signal' column:
    1  -> go long / hold long
    0  -> flat / no position
   -1  -> short (only used if short_allowed=True is passed by the caller downstream)
"""

import pandas as pd
import numpy as np


def moving_average_crossover(df: pd.DataFrame, fast_window: int = 20, slow_window: int = 50) -> pd.DataFrame:
    """
    Classic dual moving average crossover.
    Long when fast MA > slow MA, flat otherwise.
    """
    out = df.copy()
    out["fast_ma"] = out["Close"].rolling(window=fast_window, min_periods=fast_window).mean()
    out["slow_ma"] = out["Close"].rolling(window=slow_window, min_periods=slow_window).mean()

    out["signal"] = 0
    out.loc[out["fast_ma"] > out["slow_ma"], "signal"] = 1
    out["signal"] = out["signal"].fillna(0)
    return out


def momentum(df: pd.DataFrame, lookback: int = 20, threshold: float = 0.0) -> pd.DataFrame:
    """
    Momentum / trend-following strategy.
    Goes long when the trailing `lookback`-period return exceeds `threshold`.
    """
    out = df.copy()
    out["momentum"] = out["Close"].pct_change(periods=lookback)

    out["signal"] = 0
    out.loc[out["momentum"] > threshold, "signal"] = 1
    out["signal"] = out["signal"].fillna(0)
    return out


def mean_reversion(df: pd.DataFrame, window: int = 20, num_std: float = 2.0) -> pd.DataFrame:
    """
    Bollinger-Band style mean reversion.
    Goes long when price closes below the lower band (oversold),
    exits (flat) when price closes back above the rolling mean.
    """
    out = df.copy()
    out["rolling_mean"] = out["Close"].rolling(window=window, min_periods=window).mean()
    out["rolling_std"] = out["Close"].rolling(window=window, min_periods=window).std()
    out["upper_band"] = out["rolling_mean"] + num_std * out["rolling_std"]
    out["lower_band"] = out["rolling_mean"] - num_std * out["rolling_std"]

    signal = np.zeros(len(out))
    position = 0
    close = out["Close"].values
    lower = out["lower_band"].values
    mean = out["rolling_mean"].values

    for i in range(len(out)):
        if np.isnan(lower[i]) or np.isnan(mean[i]):
            signal[i] = 0
            continue
        if position == 0 and close[i] < lower[i]:
            position = 1
        elif position == 1 and close[i] >= mean[i]:
            position = 0
        signal[i] = position

    out["signal"] = signal
    return out


STRATEGY_REGISTRY = {
    "Moving Average Crossover": {
        "func": moving_average_crossover,
        "params": {
            "fast_window": {"label": "Fast MA window", "type": "int", "default": 20, "min": 2, "max": 100},
            "slow_window": {"label": "Slow MA window", "type": "int", "default": 50, "min": 5, "max": 300},
        },
    },
    "Momentum": {
        "func": momentum,
        "params": {
            "lookback": {"label": "Lookback period (days)", "type": "int", "default": 20, "min": 2, "max": 250},
            "threshold": {"label": "Return threshold", "type": "float", "default": 0.0, "min": -0.5, "max": 0.5},
        },
    },
    "Mean Reversion": {
        "func": mean_reversion,
        "params": {
            "window": {"label": "Rolling window", "type": "int", "default": 20, "min": 2, "max": 200},
            "num_std": {"label": "Std-dev band width", "type": "float", "default": 2.0, "min": 0.5, "max": 4.0},
        },
    },
}
