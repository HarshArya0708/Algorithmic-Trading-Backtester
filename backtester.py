"""
backtester.py
--------------
Core backtesting engine. Takes a DataFrame that already contains a 'signal'
column (1 = long, 0 = flat) and simulates trading it with a starting cash
balance, producing an equity curve and standard performance metrics.
"""

import numpy as np
import pandas as pd


class Backtester:
    def __init__(self, data: pd.DataFrame, initial_capital: float = 10_000.0,
                 commission_pct: float = 0.0):
        """
        Parameters
        ----------
        data : pd.DataFrame
            Must contain 'Close' and 'signal' columns, indexed by date.
        initial_capital : float
            Starting cash balance.
        commission_pct : float
            Per-trade commission as a fraction (e.g. 0.001 = 0.1%) applied
            whenever the position changes.
        """
        self.data = data.copy()
        self.initial_capital = initial_capital
        self.commission_pct = commission_pct
        self.results = None
        self.trades = None

    def run(self) -> pd.DataFrame:
        df = self.data.copy()
        df["position"] = df["signal"].shift(1).fillna(0)  # trade on next bar's open/close to avoid lookahead
        df["daily_return"] = df["Close"].pct_change().fillna(0)
        df["strategy_return"] = df["position"] * df["daily_return"]

        # Apply commission whenever position changes
        df["position_change"] = df["position"].diff().abs().fillna(0)
        df["commission_cost"] = df["position_change"] * self.commission_pct
        df["strategy_return_net"] = df["strategy_return"] - df["commission_cost"]

        df["equity_curve"] = self.initial_capital * (1 + df["strategy_return_net"]).cumprod()
        df["buy_hold_equity"] = self.initial_capital * (1 + df["daily_return"]).cumprod()

        # Running peak & drawdown series (useful for plotting)
        df["running_max"] = df["equity_curve"].cummax()
        df["drawdown"] = (df["equity_curve"] - df["running_max"]) / df["running_max"]

        self.results = df
        self._extract_trades(df)
        return df

    def _extract_trades(self, df: pd.DataFrame):
        """Build a simple trade log from position changes."""
        trades = []
        entry_date, entry_price = None, None

        for date, row in df.iterrows():
            if row["position_change"] > 0:
                if row["position"] == 1:  # entering long
                    entry_date, entry_price = date, row["Close"]
                elif row["position"] == 0 and entry_date is not None:  # exiting
                    exit_price = row["Close"]
                    pnl_pct = (exit_price - entry_price) / entry_price * 100
                    trades.append({
                        "Entry Date": entry_date,
                        "Exit Date": date,
                        "Entry Price": round(entry_price, 2),
                        "Exit Price": round(exit_price, 2),
                        "Return %": round(pnl_pct, 2),
                    })
                    entry_date, entry_price = None, None

        self.trades = pd.DataFrame(trades)

    def performance_metrics(self, risk_free_rate: float = 0.0) -> dict:
        """
        Compute standard performance metrics from the equity curve.
        Assumes daily data (252 trading days/year) unless overridden.
        """
        if self.results is None:
            raise RuntimeError("Call .run() before requesting performance metrics.")

        df = self.results
        returns = df["strategy_return_net"]

        total_return_pct = (df["equity_curve"].iloc[-1] / self.initial_capital - 1) * 100

        n_days = len(df)
        years = max(n_days / 252, 1e-9)
        cagr = (df["equity_curve"].iloc[-1] / self.initial_capital) ** (1 / years) - 1

        annual_vol = returns.std() * np.sqrt(252)
        excess_return = returns.mean() * 252 - risk_free_rate
        sharpe_ratio = excess_return / annual_vol if annual_vol > 0 else 0.0

        max_drawdown_pct = df["drawdown"].min() * 100

        win_rate = None
        if self.trades is not None and len(self.trades) > 0:
            win_rate = (self.trades["Return %"] > 0).mean() * 100

        buy_hold_return_pct = (df["buy_hold_equity"].iloc[-1] / self.initial_capital - 1) * 100

        return {
            "Total Return (%)": round(float(total_return_pct), 2),
            "Buy & Hold Return (%)": round(float(buy_hold_return_pct), 2),
            "CAGR (%)": round(float(cagr) * 100, 2),
            "Annualized Volatility (%)": round(float(annual_vol) * 100, 2),
            "Sharpe Ratio": round(float(sharpe_ratio), 2),
            "Max Drawdown (%)": round(float(max_drawdown_pct), 2),
            "Number of Trades": len(self.trades) if self.trades is not None else 0,
            "Win Rate (%)": round(float(win_rate), 2) if win_rate is not None else "N/A",
            "Final Equity ($)": round(float(df["equity_curve"].iloc[-1]), 2),
        }
