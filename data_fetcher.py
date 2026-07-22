"""
data_fetcher.py
----------------
Handles fetching historical and near real-time market data using yfinance.
"""

import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta


def fetch_historical_data(ticker: str, start: str, end: str, interval: str = "1d") -> pd.DataFrame:
    """
    Fetch historical OHLCV data for a given ticker between start and end dates.

    Parameters
    ----------
    ticker : str
        Stock/crypto/forex ticker symbol (e.g. 'AAPL', 'BTC-USD').
    start : str
        Start date in 'YYYY-MM-DD' format.
    end : str
        End date in 'YYYY-MM-DD' format.
    interval : str
        Data interval - '1d', '1h', '15m', '5m', '1m' etc.
        Note: intraday intervals (< 1d) are only available for the last ~60 days on yfinance.

    Returns
    -------
    pd.DataFrame with columns: Open, High, Low, Close, Adj Close, Volume
    """
    df = yf.download(ticker, start=start, end=end, interval=interval, progress=False, auto_adjust=False)

    if df.empty:
        raise ValueError(f"No data returned for ticker '{ticker}'. Check the symbol or date range.")

    # yfinance sometimes returns MultiIndex columns when a single ticker is passed as a list
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df.index.name = "Date"
    return df


def fetch_latest_price(ticker: str) -> dict:
    """
    Fetch the latest available (near real-time, ~15-min delayed for most feeds) price snapshot for a ticker.

    Returns
    -------
    dict with keys: symbol, price, previous_close, change, change_pct, timestamp
    """
    tk = yf.Ticker(ticker)

    # fast_info is lightweight and avoids full .info() overhead
    try:
        fast = tk.fast_info
        price = fast.get("lastPrice") or fast.get("last_price")
        prev_close = fast.get("previousClose") or fast.get("previous_close")
    except Exception:
        price, prev_close = None, None

    # Fallback: pull the most recent 1-minute bar if fast_info is unavailable
    if price is None:
        intraday = tk.history(period="1d", interval="1m")
        if intraday.empty:
            raise ValueError(f"Could not fetch a live price for '{ticker}'.")
        price = float(intraday["Close"].iloc[-1])
        prev_close = float(intraday["Close"].iloc[0])

    change = price - prev_close if prev_close else 0.0
    change_pct = (change / prev_close * 100) if prev_close else 0.0

    return {
        "symbol": ticker.upper(),
        "price": round(float(price), 2),
        "previous_close": round(float(prev_close), 2) if prev_close else None,
        "change": round(float(change), 2),
        "change_pct": round(float(change_pct), 2),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def get_default_date_range(days_back: int = 730) -> tuple:
    """Return (start_str, end_str) covering the last `days_back` days up to today."""
    end = datetime.now()
    start = end - timedelta(days=days_back)
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# Indian market support
# ---------------------------------------------------------------------------
# Yahoo Finance uses these suffixes for Indian exchanges:
#   .NS  -> NSE (National Stock Exchange)
#   .BO  -> BSE (Bombay Stock Exchange)
MARKET_SUFFIXES = {
    "Global / US": "",
    "India (NSE)": ".NS",
    "India (BSE)": ".BO",
}

# A handful of popular NSE symbols to make the dropdown convenient.
# (Users can still type any valid NSE/BSE symbol manually.)
POPULAR_NSE_TICKERS = [
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "HINDUNILVR",
    "SBIN", "BHARTIARTL", "ITC", "KOTAKBANK", "LT", "AXISBANK",
    "BAJFINANCE", "MARUTI", "ASIANPAINT", "SUNPHARMA", "TITAN",
    "WIPRO", "TATAMOTORS", "ADANIENT",
]


def format_ticker(raw_ticker: str, market: str) -> str:
    """
    Normalize a user-entered ticker for the selected market by appending
    the correct Yahoo Finance exchange suffix if it's missing.

    Examples
    --------
    format_ticker("RELIANCE", "India (NSE)") -> "RELIANCE.NS"
    format_ticker("RELIANCE.NS", "India (NSE)") -> "RELIANCE.NS"  (already suffixed)
    format_ticker("AAPL", "Global / US") -> "AAPL"
    """
    raw_ticker = raw_ticker.strip().upper()
    suffix = MARKET_SUFFIXES.get(market, "")

    if not suffix:
        return raw_ticker

    # Don't double-append if the user already typed .NS/.BO (or any suffix)
    if "." in raw_ticker:
        return raw_ticker

    return f"{raw_ticker}{suffix}"


def currency_symbol_for_ticker(ticker: str) -> str:
    """Return the display currency symbol based on the ticker's exchange suffix."""
    t = ticker.upper()
    if t.endswith(".NS") or t.endswith(".BO"):
        return "₹"
    return "$"
