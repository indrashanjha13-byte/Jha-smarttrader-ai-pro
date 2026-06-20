import yfinance as yf
import pandas as pd
import pandas_ta as ta


def get_signals(symbol):

    df = yf.download(
        symbol,
        period="30d",
        interval="15m",
        auto_adjust=False
    )
    print("Symbol:", symbol)
    print(df.tail())

    if df.empty:
        return {"error": "No data"}

    # Fix yfinance MultiIndex
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)


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

    if macd is not None:
        df["MACD"] = macd.iloc[:,0]
        df["MACD_SIGNAL"] = macd.iloc[:,1]
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


    if st is not None:
        df["SUPERTREND"] = st.iloc[:,0]
        df["ST_DIRECTION"] = st.iloc[:,1]
    else:
        df["SUPERTREND"] = 0
        df["ST_DIRECTION"] = 0



    # Volume
    df["AVG_VOLUME"] = volume.rolling(20).mean()


    latest = df.iloc[-1]


    return {

        "EMA9": float(latest["EMA9"]),
        "EMA21": float(latest["EMA21"]),
        "RSI": float(latest["RSI"]),

        "MACD": float(latest["MACD"]),
        "MACD_SIGNAL": float(latest["MACD_SIGNAL"]),

        "SUPERTREND": float(latest["ST_DIRECTION"]),

        "Volume": float(latest["Volume"]),
        "AVG_VOLUME": float(latest["AVG_VOLUME"])
        "Close": float(latest["Close"])
}
