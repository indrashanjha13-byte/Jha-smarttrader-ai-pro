"""
Jha SmartTrader AI Pro
3000+ Stock AI Scanner Engine

BUY / SELL / HOLD scanner
No live orders are placed by this module.
"""

from __future__ import annotations
from pathlib import Path

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Iterable

import pandas as pd

from signals import download_data, calculate_indicators
from ai_signal_ranker import signal_score


logger = logging.getLogger(__name__)


# =========================================================
# CONFIGURATION
# =========================================================

DEFAULT_INTERVAL = "5m"
DEFAULT_PERIOD = "5d"

DEFAULT_MAX_WORKERS = 8

BUY_THRESHOLD = 65.0
SELL_THRESHOLD = 35.0


# =========================================================
# STOCK UNIVERSE
# =========================================================

# NSE official Equity master file.
NSE_MASTER_FILE = Path(__file__).resolve().parent / "data" / "EQUITY_L.csv"


# Safe fallback universe.
# Used only when the NSE master file is unavailable or invalid.
NSE_FALLBACK_STOCKS = [
    "RELIANCE.NS",
    "TCS.NS",
    "INFY.NS",
    "HDFCBANK.NS",
    "ICICIBANK.NS",
    "SBIN.NS",
    "AXISBANK.NS",
    "KOTAKBANK.NS",
    "LT.NS",
    "ITC.NS",
    "HINDUNILVR.NS",
    "BHARTIARTL.NS",
    "MARUTI.NS",
    "M&M.NS",
    "SUNPHARMA.NS",
    "TATAMOTORS.NS",
    "TATASTEEL.NS",
    "NTPC.NS",
    "POWERGRID.NS",
    "ONGC.NS",
    "ADANIENT.NS",
    "ADANIPORTS.NS",
    "COALINDIA.NS",
    "BEL.NS",
    "HAL.NS",
    "TRENT.NS",
    "ZOMATO.NS",
    "IRCTC.NS",
    "INDUSINDBK.NS",
    "BAJFINANCE.NS",
    "BAJAJFINSV.NS",
    "HCLTECH.NS",
    "WIPRO.NS",
    "TECHM.NS",
    "MARICO.NS",
    "DABUR.NS",
    "CIPLA.NS",
    "DRREDDY.NS",
    "EICHERMOT.NS",
    "HEROMOTOCO.NS",
    "TVSMOTOR.NS",
    "GRASIM.NS",
    "JSWSTEEL.NS",
    "JINDALSTEL.NS",
    "TITAN.NS",
    "ASIANPAINT.NS",
    "ULTRACEMCO.NS",
    "SHREECEM.NS",
]


def load_nse_equity_universe():
    """
    Load the current NSE Equity universe from EQUITY_L.csv.

    Only Series=EQ securities are included.
    Symbols are normalized to Yahoo Finance .NS format.

    Returns the fallback universe if the master file cannot
    be loaded safely.
    """
    try:
        if not NSE_MASTER_FILE.exists():
            logger.warning(
                "NSE master file not found: %s. Using fallback universe.",
                NSE_MASTER_FILE,
            )
            return list(NSE_FALLBACK_STOCKS)

        df = pd.read_csv(
            NSE_MASTER_FILE,
            dtype=str,
            engine="python",
        )

        # Normalize column names because NSE CSV headers contain spaces.
        df.columns = [
            str(column).strip().upper()
            for column in df.columns
        ]

        required_columns = {"SYMBOL", "SERIES"}

        if not required_columns.issubset(df.columns):
            logger.warning(
                "NSE master file is missing required columns: %s. "
                "Using fallback universe.",
                required_columns - set(df.columns),
            )
            return list(NSE_FALLBACK_STOCKS)

        # Only normal Equity series.
        eq = df[
            df["SERIES"]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.upper()
            .eq("EQ")
        ].copy()

        symbols = (
            eq["SYMBOL"]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.upper()
        )

        # Remove blank symbols and duplicates.
        symbols = symbols[
            symbols.ne("")
        ].drop_duplicates()

        # Convert NSE symbols to Yahoo Finance format.
        nse_stocks = [
            symbol if symbol.endswith(".NS") else f"{symbol}.NS"
            for symbol in symbols.tolist()
        ]

        if not nse_stocks:
            logger.warning(
                "NSE master file produced no valid EQ symbols. "
                "Using fallback universe."
            )
            return list(NSE_FALLBACK_STOCKS)

        logger.info(
            "Loaded %d NSE EQ stocks from %s",
            len(nse_stocks),
            NSE_MASTER_FILE,
        )

        return nse_stocks

    except Exception as exc:
        logger.warning(
            "Could not load NSE equity universe: %s. "
            "Using fallback universe.",
            exc,
        )
        return list(NSE_FALLBACK_STOCKS)


# Public scanner universe.
# With the current NSE master this contains 2,319 EQ stocks.
NSE_STOCKS = load_nse_equity_universe()


# =========================================================
# HELPERS
# =========================================================

def safe_float(value, default=0.0):
    """Safely convert a value to float."""
    try:
        if value is None:
            return default

        if pd.isna(value):
            return default

        return float(value)

    except (TypeError, ValueError):
        return default


def normalize_symbol(symbol: str) -> str:
    """Normalize stock symbol for Yahoo/NSE usage."""
    symbol = str(symbol).strip().upper()

    if not symbol:
        return ""

    if symbol.endswith(".NS"):
        return symbol

    if symbol.endswith(".BO"):
        return symbol

    return f"{symbol}.NS"


def get_column(df: pd.DataFrame, names: Iterable[str]):
    """Find the first available column from a list."""
    for name in names:
        if name in df.columns:
            return name

    return None


# =========================================================
# SIGNAL CLASSIFICATION
# =========================================================

def classify_signal(score: float) -> str:
    """
    Convert AI score into BUY / SELL / HOLD.

    65+  = BUY
    35-  = SELL
    else = HOLD
    """

    score = safe_float(score)

    if score >= BUY_THRESHOLD:
        return "BUY"

    if score <= SELL_THRESHOLD:
        return "SELL"

    return "HOLD"


def confidence_from_score(score: float) -> float:
    """
    Convert score into a confidence value.

    Distance from neutral 50 becomes confidence.
    """

    score = max(0.0, min(100.0, safe_float(score)))

    distance = abs(score - 50.0)

    confidence = 50.0 + (distance * 2.0)

    return round(min(confidence, 100.0), 2)


# =========================================================
# SINGLE STOCK SCAN
# =========================================================

def scan_stock(
    symbol: str,
    interval: str = DEFAULT_INTERVAL,
    period: str = DEFAULT_PERIOD,
) -> dict:
    """
    Scan one stock.

    Returns a normalized dictionary suitable for
    Streamlit tables, ranking and filtering.
    """

    symbol = normalize_symbol(symbol)

    if not symbol:
        return {
            "symbol": "",
            "signal": "ERROR",
            "confidence": 0.0,
            "score": 0.0,
            "error": "Empty symbol",
        }

    try:
        df = download_data(
            symbol=symbol,
            interval=interval,
            period=period,
        )

        if df is None or df.empty:
            return {
                "symbol": symbol,
                "signal": "NO DATA",
                "confidence": 0.0,
                "score": 0.0,
                "error": "No market data",
            }

        df = calculate_indicators(df)

        if df is None or df.empty:
            return {
                "symbol": symbol,
                "signal": "NO DATA",
                "confidence": 0.0,
                "score": 0.0,
                "error": "Indicator calculation failed",
            }

        row = df.iloc[-1]

        close_col = get_column(
            df,
            ["Close", "close", "Adj Close"],
        )

        rsi_col = get_column(
            df,
            ["RSI", "rsi", "RSI14"],
        )

        volume_ratio_col = get_column(
            df,
            [
                "Volume_Ratio",
                "volume_ratio",
                "VolumeRatio",
            ],
        )

        trend_col = get_column(
            df,
            [
                "Trend",
                "trend",
                "Market_Trend",
            ],
        )

        macd_col = get_column(
            df,
            ["MACD", "macd"],
        )

        macd_signal_col = get_column(
            df,
            [
                "MACD_Signal",
                "macd_signal",
                "MACDSignal",
            ],
        )

        supertrend_col = get_column(
            df,
            [
                "SuperTrend",
                "supertrend",
                "Supertrend",
            ],
        )

        close = safe_float(
            row[close_col]
        ) if close_col else 0.0

        rsi = safe_float(
            row[rsi_col]
        ) if rsi_col else 50.0

        volume_ratio = safe_float(
            row[volume_ratio_col]
        ) if volume_ratio_col else 1.0

        trend = (
            str(row[trend_col])
            if trend_col
            else "NEUTRAL"
        )

        macd = safe_float(
            row[macd_col]
        ) if macd_col else 0.0

        macd_signal = safe_float(
            row[macd_signal_col]
        ) if macd_signal_col else 0.0

        supertrend = (
            safe_float(row[supertrend_col])
            if supertrend_col
            else close
        )
        # -------------------------------------------------
        # EXISTING AI RANKER
        # -------------------------------------------------

        score = signal_score(
            rsi=rsi,
            volume_ratio=volume_ratio,
            trend=trend,
            macd=macd,
            macd_signal=macd_signal,
            supertrend=supertrend,
        )

        score = safe_float(score)

        score = max(
            0.0,
            min(100.0, score),
        )

        signal = classify_signal(score)

        confidence = confidence_from_score(
            score
        )

        # -------------------------------------------------
        # ENTRY / SL / TARGET
        # -------------------------------------------------

        if signal == "BUY":

            entry = close

            stop_loss = close * 0.99

            target = close * 1.02

        elif signal == "SELL":

            entry = close

            stop_loss = close * 1.01

            target = close * 0.98

        else:

            entry = close

            stop_loss = close

            target = close

        return {
            "symbol": symbol,
            "signal": signal,
            "confidence": confidence,
            "score": round(score, 2),
            "price": round(close, 2),
            "entry": round(entry, 2),
            "stop_loss": round(stop_loss, 2),
            "target": round(target, 2),
            "rsi": round(rsi, 2),
            "volume_ratio": round(
                volume_ratio,
                2,
            ),
            "trend": trend,
            "macd": round(macd, 4),
            "macd_signal": round(
                macd_signal,
                4,
            ),
            "supertrend": round(
                supertrend,
                2,
            ),
            "error": "",
        }

    except Exception as exc:

        logger.warning(
            "Stock scan failed for %s: %s",
            symbol,
            exc,
        )

        return {
            "symbol": symbol,
            "signal": "ERROR",
            "confidence": 0.0,
            "score": 0.0,
            "error": str(exc),
        }


# =========================================================
# MULTI STOCK SCANNER
# =========================================================

def scan_stocks(
    symbols=None,
    interval: str = DEFAULT_INTERVAL,
    period: str = DEFAULT_PERIOD,
    max_workers: int = DEFAULT_MAX_WORKERS,
) -> pd.DataFrame:
    """
    Scan multiple stocks concurrently.

    Designed for large stock universes.
    """

    if symbols is None:
        symbols = NSE_STOCKS

    symbols = [
        normalize_symbol(symbol)
        for symbol in symbols
    ]

    symbols = [
        symbol
        for symbol in symbols
        if symbol
    ]

    results = []

    workers = max(
        1,
        min(
            int(max_workers),
            16,
        ),
    )

    with ThreadPoolExecutor(
        max_workers=workers
    ) as executor:

        futures = {
            executor.submit(
                scan_stock,
                symbol,
                interval,
                period,
            ): symbol
            for symbol in symbols
        }

        for future in as_completed(futures):

            symbol = futures[future]

            try:
                result = future.result()

            except Exception as exc:

                result = {
                    "symbol": symbol,
                    "signal": "ERROR",
                    "confidence": 0.0,
                    "score": 0.0,
                    "error": str(exc),
                }

            results.append(result)

    if not results:
        return pd.DataFrame()

    result_df = pd.DataFrame(results)

    if "confidence" in result_df.columns:

        result_df = result_df.sort_values(
            by="confidence",
            ascending=False,
        )

    result_df = result_df.reset_index(
        drop=True
    )

    result_df.insert(
        0,
        "rank",
        range(
            1,
            len(result_df) + 1,
        ),
    )

    return result_df


# =========================================================
# FILTER FUNCTIONS
# =========================================================

def filter_signals(
    df: pd.DataFrame,
    signal: str = "ALL",
    min_confidence: float = 0.0,
) -> pd.DataFrame:

    if df is None or df.empty:
        return pd.DataFrame()

    result = df.copy()

    if signal and signal.upper() != "ALL":

        result = result[
            result["signal"]
            .astype(str)
            .str.upper()
            == signal.upper()
        ]

    if "confidence" in result.columns:

        result = result[
            pd.to_numeric(
                result["confidence"],
                errors="coerce",
            ).fillna(0)
            >= float(min_confidence)
        ]

    return result.reset_index(
        drop=True
    )


# =========================================================
# TOP BUY / SELL
# =========================================================

def get_top_signals(
    df: pd.DataFrame,
    limit: int = 20,
):
    """Return strongest BUY and SELL candidates."""

    if df is None or df.empty:
        return {
            "BUY": pd.DataFrame(),
            "SELL": pd.DataFrame(),
        }

    buy = df[
        df["signal"] == "BUY"
    ].head(limit)

    sell = df[
        df["signal"] == "SELL"
    ].head(limit)

    return {
        "BUY": buy.reset_index(drop=True),
        "SELL": sell.reset_index(drop=True),
    }


# =========================================================
# SIMPLE TEST
# =========================================================

if __name__ == "__main__":

    logging.basicConfig(
        level=logging.INFO
    )

    print(
        "=" * 70
    )

    print(
        "JHA SMARTTRADER AI PRO"
    )

    print(
        "STOCK AI SCANNER TEST"
    )

    print(
        "=" * 70
    )

    test_symbols = [
        "RELIANCE.NS",
        "TCS.NS",
        "INFY.NS",
        "HDFCBANK.NS",
        "ICICIBANK.NS",
    ]

    result = scan_stocks(
        symbols=test_symbols,
        interval="5m",
        period="5d",
        max_workers=5,
    )

    print()

    print(result.to_string(
        index=False
    ))