import yfinance as yf
import pandas as pd
import pandas_ta as ta


def get_signals(symbol):

    df = yf.download(
        symbol,
        period="30d",
        interval="5m",
        auto_adjust=False,
        progress=False
    )

    # Fix MultiIndex FIRST
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    if df.empty:
        return {"error": "No data"}

    print("Symbol:", symbol)
    print("Rows =", len(df))
    print(df.tail())

    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    volume = df["Volume"]

    # EMA
    df["EMA9"] = ta.ema(close, length=9)
    df["EMA21"] = ta.ema(close, length=21)

    # RSI
    df["RSI"] = ta.rsi(close, length=14)

    # MACD
    macd = ta.macd(close)

    if macd is not None and not macd.empty:
        df["MACD"] = macd.iloc[:, 0]
        df["MACD_SIGNAL"] = macd.iloc[:, 1]
    else:
        df["MACD"] = 0
        df["MACD_SIGNAL"] = 0

    # SuperTrend
    st = ta.supertrend(
        high,
        low,
        close,
        length=10,
        multiplier=3
    )

    if st is not None and not st.empty:
        df["SUPERTREND"] = st.iloc[:, 0]
        df["ST_DIRECTION"] = st.iloc[:, 1]
    else:
        df["SUPERTREND"] = 0
        df["ST_DIRECTION"] = 0

    # Volume
    df["AVG_VOLUME"] = volume.rolling(20).mean()

    latest = df.iloc[-1]

    return {

        "EMA9": float(latest["EMA9"]) if pd.notna(latest["EMA9"]) else 0,
        "EMA21": float(latest["EMA21"]) if pd.notna(latest["EMA21"]) else 0,
        "RSI": float(latest["RSI"]) if pd.notna(latest["RSI"]) else 0,
        "MACD": float(latest["MACD"]) if pd.notna(latest["MACD"]) else 0,
        

        "MACD_SIGNAL": float(latest["MACD_SIGNAL"]) if pd.notna(latest["MACD_SIGNAL"]) else 0,
        "SUPERTREND": int(latest["ST_DIRECTION"]) if pd.notna(latest["ST_DIRECTION"]) else 0,
        "Volume": float(latest["Volume"]) if pd.notna(latest["Volume"]) else 0,
        "AVG_VOLUME": float(latest["AVG_VOLUME"]) if pd.notna(latest["AVG_VOLUME"]) else 0,


        "Close": float(latest["Close"]) if pd.notna(latest["Close"]) else 0,
        "Open": float(latest["Open"]) if pd.notna(latest["Open"]) else 0,
        "High": float(latest["High"]) if pd.notna(latest["High"]) else 0,
        "Low": float(latest["Low"]) if pd.notna(latest["Low"]) else 0
    }