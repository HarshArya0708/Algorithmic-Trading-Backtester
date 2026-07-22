"""
app.py
-------
Streamlit UI for the Algorithmic Trading Backtester.
Lets the user pick a ticker, date range, strategy + parameters, and run a
full backtest with live equity curve, performance metrics, and trade log.
Also shows a near real-time price snapshot for the chosen ticker.

Run with:
    streamlit run app.py
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from data_fetcher import fetch_historical_data, fetch_latest_price, get_default_date_range
from strategies import STRATEGY_REGISTRY
from backtester import Backtester

st.set_page_config(page_title="Algo Trading Backtester", layout="wide", page_icon="📈")


# ---------------------------------------------------------------------------
# Sidebar: user preferences / inputs
# ---------------------------------------------------------------------------
st.sidebar.title("⚙️ Backtest Settings")

ticker = st.sidebar.text_input("Ticker symbol", value="AAPL",
                                help="Any Yahoo Finance symbol, e.g. AAPL, MSFT, BTC-USD, EURUSD=X").upper().strip()

default_start, default_end = get_default_date_range(days_back=730)
col1, col2 = st.sidebar.columns(2)
start_date = col1.date_input("Start date", pd.to_datetime(default_start))
end_date = col2.date_input("End date", pd.to_datetime(default_end))

interval = st.sidebar.selectbox("Data interval", ["1d", "1h", "30m", "15m", "5m"], index=0,
                                 help="Intraday intervals only cover roughly the last 60 days on Yahoo Finance.")

st.sidebar.markdown("---")
strategy_name = st.sidebar.selectbox("Strategy", list(STRATEGY_REGISTRY.keys()))
strategy_config = STRATEGY_REGISTRY[strategy_name]

st.sidebar.markdown(f"**{strategy_name} parameters**")
strategy_params = {}
for param_key, meta in strategy_config["params"].items():
    if meta["type"] == "int":
        strategy_params[param_key] = st.sidebar.slider(
            meta["label"], min_value=meta["min"], max_value=meta["max"], value=meta["default"]
        )
    else:
        strategy_params[param_key] = st.sidebar.slider(
            meta["label"], min_value=float(meta["min"]), max_value=float(meta["max"]),
            value=float(meta["default"]), step=0.01
        )

st.sidebar.markdown("---")
initial_capital = st.sidebar.number_input("Initial capital ($)", min_value=100.0, value=10_000.0, step=500.0)
commission_pct = st.sidebar.slider("Commission per trade (%)", min_value=0.0, max_value=1.0, value=0.05, step=0.01) / 100
risk_free_rate = st.sidebar.slider("Risk-free rate (annual, %)", min_value=0.0, max_value=10.0, value=2.0, step=0.25) / 100

run_button = st.sidebar.button("🚀 Run Backtest", use_container_width=True, type="primary")


# ---------------------------------------------------------------------------
# Header + live price ticker
# ---------------------------------------------------------------------------
st.title("📈 Algorithmic Trading Backtester")
st.caption("Fetches live & historical market data, simulates strategies, and reports Sharpe ratio, "
           "max drawdown, and equity curves.")

if ticker:
    try:
        live = fetch_latest_price(ticker)
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Symbol", live["symbol"])
        m2.metric("Last Price", f"${live['price']}")
        m3.metric("Change", f"${live['change']}", f"{live['change_pct']}%")
        m4.metric("As of", live["timestamp"])
    except Exception as e:
        st.warning(f"Couldn't fetch a live price for '{ticker}': {e}")

st.markdown("---")


# ---------------------------------------------------------------------------
# Run backtest
# ---------------------------------------------------------------------------
if run_button:
    if not ticker:
        st.error("Please enter a ticker symbol.")
        st.stop()

    with st.spinner(f"Fetching data for {ticker}..."):
        try:
            raw_data = fetch_historical_data(
                ticker,
                start=start_date.strftime("%Y-%m-%d"),
                end=end_date.strftime("%Y-%m-%d"),
                interval=interval,
            )
        except Exception as e:
            st.error(f"Data fetch failed: {e}")
            st.stop()

    with st.spinner("Generating signals and running backtest..."):
        signal_df = strategy_config["func"](raw_data, **strategy_params)

        bt = Backtester(signal_df, initial_capital=initial_capital, commission_pct=commission_pct)
        results = bt.run()
        metrics = bt.performance_metrics(risk_free_rate=risk_free_rate)

    st.success(f"Backtest complete: {strategy_name} on {ticker} "
               f"({start_date} → {end_date}, interval={interval})")

    # --- Metrics row ---
    st.subheader("📊 Performance Metrics")
    metric_cols = st.columns(len(metrics))
    for col, (k, v) in zip(metric_cols, metrics.items()):
        col.metric(k, v)

    # --- Equity curve chart ---
    st.subheader("💰 Equity Curve")
    fig = make_subplots(specs=[[{"secondary_y": False}]])
    fig.add_trace(go.Scatter(x=results.index, y=results["equity_curve"],
                              name=f"{strategy_name} Strategy", line=dict(width=2)))
    fig.add_trace(go.Scatter(x=results.index, y=results["buy_hold_equity"],
                              name="Buy & Hold", line=dict(width=2, dash="dot")))
    fig.update_layout(height=450, xaxis_title="Date", yaxis_title="Portfolio Value ($)",
                       legend=dict(orientation="h", yanchor="bottom", y=1.02))
    st.plotly_chart(fig, use_container_width=True)

    # --- Price chart with signal overlay ---
    st.subheader("📉 Price & Signals")
    price_fig = go.Figure()
    price_fig.add_trace(go.Scatter(x=results.index, y=results["Close"], name="Close Price", line=dict(width=1.5)))

    if "fast_ma" in results.columns:
        price_fig.add_trace(go.Scatter(x=results.index, y=results["fast_ma"], name="Fast MA", line=dict(width=1)))
        price_fig.add_trace(go.Scatter(x=results.index, y=results["slow_ma"], name="Slow MA", line=dict(width=1)))
    if "upper_band" in results.columns:
        price_fig.add_trace(go.Scatter(x=results.index, y=results["upper_band"], name="Upper Band",
                                        line=dict(width=1, dash="dash")))
        price_fig.add_trace(go.Scatter(x=results.index, y=results["lower_band"], name="Lower Band",
                                        line=dict(width=1, dash="dash")))

    long_entries = results[results["position"].diff() == 1]
    long_exits = results[results["position"].diff() == -1]
    price_fig.add_trace(go.Scatter(x=long_entries.index, y=long_entries["Close"], mode="markers",
                                    name="Buy", marker=dict(symbol="triangle-up", size=10, color="green")))
    price_fig.add_trace(go.Scatter(x=long_exits.index, y=long_exits["Close"], mode="markers",
                                    name="Sell", marker=dict(symbol="triangle-down", size=10, color="red")))
    price_fig.update_layout(height=450, xaxis_title="Date", yaxis_title="Price ($)",
                             legend=dict(orientation="h", yanchor="bottom", y=1.02))
    st.plotly_chart(price_fig, use_container_width=True)

    # --- Drawdown chart ---
    st.subheader("📉 Drawdown")
    dd_fig = go.Figure()
    dd_fig.add_trace(go.Scatter(x=results.index, y=results["drawdown"] * 100, fill="tozeroy",
                                 name="Drawdown (%)", line=dict(color="crimson")))
    dd_fig.update_layout(height=300, xaxis_title="Date", yaxis_title="Drawdown (%)")
    st.plotly_chart(dd_fig, use_container_width=True)

    # --- Trade log ---
    st.subheader("📋 Trade Log")
    if bt.trades is not None and len(bt.trades) > 0:
        st.dataframe(bt.trades, use_container_width=True)
        csv = bt.trades.to_csv(index=False).encode("utf-8")
        st.download_button("Download trade log (CSV)", csv, file_name=f"{ticker}_trades.csv")
    else:
        st.info("No completed trades in this period/strategy combination.")

    # --- Raw data (expandable) ---
    with st.expander("Show raw backtest data"):
        st.dataframe(results, use_container_width=True)

else:
    st.info("👈 Configure your ticker, date range, and strategy in the sidebar, then click **Run Backtest**.")
    st.markdown("""
    ### Available strategies
    - **Moving Average Crossover** — long when a fast moving average is above a slow moving average.
    - **Momentum** — long when trailing returns exceed a threshold.
    - **Mean Reversion** — long when price dips below a lower Bollinger Band, exits at the mean.
    """)
