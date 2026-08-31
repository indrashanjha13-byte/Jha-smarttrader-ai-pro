import yfinance as yf
import pandas as pd
import pandas_ta as ta
import logging


def get_signals(symbol):
    """
    Downloads intraday price data and calculates core technical indicators 
    (EMA, RSI, MACD, SuperTrend) and multi-strategy individual signals using pandas_ta.
    """
    try:
        df = yf.download(
            symbol,
            period="30d",
            interval="5m",
            auto_adjust=False,
            progress=False
        )

        if df is None or df.empty:
            logging.warning(f"⚠️ No data downloaded for symbol: {symbol}")
            return {"error": "No data available"}

        # Fix MultiIndex FIRST
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0] for col in df.columns]

        required_cols = ["Close", "High", "Low", "Volume"]
        for col in required_cols:
            if col not in df.columns:
                return {"error": f"Required column '{col}' missing from downloaded data"}

        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        volume = df["Volume"]

        # Technical Indicators calculation using pandas_ta
        df["EMA9"] = ta.ema(close, length=9)
        df["EMA21"] = ta.ema(close, length=21)
        df["RSI"] = ta.rsi(close, length=14)

        # MACD
        macd = ta.macd(close)
        if macd is not None and not macd.empty and macd.shape[1] >= 2:
            df["MACD"] = macd.iloc[:, 0]
            df["MACD_SIGNAL"] = macd.iloc[:, 1]
        else:
            df["MACD"] = 0.0
            df["MACD_SIGNAL"] = 0.0

        # SuperTrend
        st = ta.supertrend(high, low, close, length=10, multiplier=3)
        if st is not None and not st.empty and st.shape[1] >= 2:
            df["SUPERTREND"] = st.iloc[:, 0]
            df["ST_DIRECTION"] = st.iloc[:, 1]
        else:
            df["SUPERTREND"] = 0.0
            df["ST_DIRECTION"] = 0

        # Volume Moving Average
        df["AVG_VOLUME"] = volume.rolling(20, min_periods=1).mean()

        latest = df.iloc[-1]

        def safe_val(val, default=0.0, cast_type=float):
            try:
                return cast_type(val) if pd.notna(val) else default
            except Exception:
                return default

        # ---------------------------------------------------------
        # Multi-Strategy Individual Signals
        # ---------------------------------------------------------
        ema9_val = safe_val(latest.get("EMA9"))
        ema21_val = safe_val(latest.get("EMA21"))
        ema_signal = "BUY" if ema9_val > ema21_val else ("SELL" if ema9_val < ema21_val else "HOLD")

        st_dir = safe_val(latest.get("ST_DIRECTION"), default=0, cast_type=int)
        supertrend_signal = "BUY" if st_dir == 1 else ("SELL" if st_dir == -1 else "HOLD")

        rsi_val = safe_val(latest.get("RSI"))
        rsi_signal = "BUY" if rsi_val > 55 else ("SELL" if rsi_val < 45 else "HOLD")

        return {
            "EMA9": ema9_val,
            "EMA21": ema21_val,
            "RSI": rsi_val,
            "MACD": safe_val(latest.get("MACD")),
            "MACD_SIGNAL": safe_val(latest.get("MACD_SIGNAL")),
            "SUPERTREND": st_dir,
            "Volume": safe_val(latest.get("Volume")),
            "AVG_VOLUME": safe_val(latest.get("AVG_VOLUME")),
            "Close": safe_val(latest.get("Close")),
            "Open": safe_val(latest.get("Open")),
            "High": safe_val(latest.get("High")),
            "Low": safe_val(latest.get("Low")),
            # Multi-Strategy Signals Added Here Safely:
            "EMA_SIGNAL": ema_signal,
            "SUPERTREND_SIGNAL": supertrend_signal,
            "RSI_SIGNAL": rsi_signal
        }

    except Exception as e:
        logging.error(f"❌ Error generating signals for {symbol}: {e}")
        return {"error": str(e)}