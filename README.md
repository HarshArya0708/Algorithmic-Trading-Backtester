# 📈 Algorithmic Trading Backtester

A complete backtesting engine with a Streamlit UI. Import historical & near real-time
market data, test trading strategies, and evaluate performance with Sharpe ratio,
maximum drawdown, and equity curves.

## Features

- ✅ Fetches historical and near real-time market data (via [yfinance](https://github.com/ranaroussi/yfinance))
- ✅ Interactive UI — pick a ticker, date range, strategy, and parameters, no code required
- ✅ **Indian market support** — NSE and BSE, with automatic `.NS`/`.BO` suffixing and ₹ currency display
- ✅ Three built-in strategies: **Moving Average Crossover**, **Momentum**, **Mean Reversion**
- ✅ Computes Sharpe Ratio, CAGR, annualized volatility, win rate
- ✅ Measures Maximum Drawdown
- ✅ Generates equity curves (strategy vs. buy & hold)
- ✅ Trade log with entry/exit prices, exportable as CSV
- ✅ Configurable commission costs and starting capital

## Screenshots

*(Add your own screenshots here after running the app)*

## Project structure

```
algo-backtester/
├── app.py              # Streamlit UI (entry point)
├── data_fetcher.py      # Historical & live data fetching (yfinance)
├── strategies.py        # Strategy signal generators + registry
├── backtester.py         # Core backtesting engine & performance metrics
├── requirements.txt
└── README.md
```

## Getting started

### 1. Clone the repo

```bash
git clone https://github.com/<your-username>/algo-backtester.git
cd algo-backtester
```

### 2. Create a virtual environment (recommended)

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the app

```bash
streamlit run app.py
```

Then open the local URL Streamlit prints (usually `http://localhost:8501`).

## How to use

1. Choose a **Market** in the sidebar: `Global / US`, `India (NSE)`, or `India (BSE)`.
2. Enter a ticker symbol (e.g. `AAPL`, `MSFT`, `BTC-USD`, `EURUSD=X` for Global; `RELIANCE`, `TCS`,
   `INFY` for India — no need to type `.NS`/`.BO`, it's added automatically). A dropdown of
   popular NSE stocks is available as a shortcut when India (NSE) is selected.
3. Pick a date range and data interval.
4. Choose a strategy and tune its parameters with the sliders.
5. Set your starting capital and commission assumptions (prices/metrics display in ₹ for Indian tickers, $ otherwise).
6. Click **Run Backtest** to see the equity curve, metrics, and trade log.

### Indian market notes

- Yahoo Finance covers NSE (`.NS`) and BSE (`.BO`) listed stocks and indices (e.g. `^NSEI` for Nifty 50, `^BSESN` for Sensex).
- If you type a symbol that already includes a suffix (or a `.` of any kind), it's used as-is and not double-suffixed.
- Data delay and availability for Indian tickers follow the same Yahoo Finance limitations as other markets (see Notes & disclaimers below).

## Adding your own strategy

Add a new function to `strategies.py` that takes a DataFrame with a `Close`
column and returns it with an added `signal` column (`1` = long, `0` = flat).
Then register it in `STRATEGY_REGISTRY` with its display name and tunable
parameters — it will automatically appear in the UI.

```python
def my_strategy(df, some_param=10):
    out = df.copy()
    out["signal"] = 0
    # ... your logic here
    return out

STRATEGY_REGISTRY["My Strategy"] = {
    "func": my_strategy,
    "params": {
        "some_param": {"label": "Some Param", "type": "int", "default": 10, "min": 1, "max": 100},
    },
}
```

## Notes & disclaimers

- Data is sourced from Yahoo Finance via `yfinance` and may be delayed (~15 min) — not suitable for live trading execution.
- This tool is for educational and research purposes only. It is **not financial advice**, and past
  backtested performance does not guarantee future results.
- Intraday intervals (`1h`, `30m`, `15m`, `5m`) are limited by Yahoo Finance to roughly the last 60 days of history.

## License

MIT — feel free to use, modify, and share.
