import pandas as pd
import logging


def generate_signal(supertrend, macd, macd_signal, volume, avg_volume):
    """Combines SuperTrend, MACD and Volume confirmation for primary signal."""
    try:
        st = int(supertrend or 0)
        m_val = float(macd or 0)
        m_sig = float(macd_signal or 0)
        vol = float(volume or 0)
        avg_vol = float(avg_volume or 0)

        if st > 0 and m_val > m_sig and vol > avg_vol:
            return "BUY"
        elif st < 0 and m_val < m_sig and vol > avg_vol:
            return "SELL"
    except Exception as e:
        logging.error(f"❌ Error in generate_signal: {e}")
    
    return "NO TRADE"


def ema_signal(ema9, ema21):
    """Determines trend direction using EMA crossover/position."""
    try:
        e9 = float(ema9 or 0)
        e21 = float(ema21 or 0)
        if e9 > e21:
            return "BUY"
        elif e9 < e21:
            return "SELL"
    except Exception as e:
        logging.error(f"❌ Error in ema_signal: {e}")
    
    return "NO TRADE"


def rsi_signal(rsi):
    """Checks overbought/oversold levels using RSI."""
    try:
        r = float(rsi or 0)
        if r < 30:
            return "BUY"
        elif r > 70:
            return "SELL"
    except Exception as e:
        logging.error(f"❌ Error in rsi_signal: {e}")
    
    return "NO TRADE"


def supertrend_signal(supertrend):
    """Returns signal based on SuperTrend direction."""
    try:
        st = int(supertrend or 0)
        if st > 0:
            return "BUY"
        elif st < 0:
            return "SELL"
    except Exception as e:
        logging.error(f"❌ Error in supertrend_signal: {e}")
    
    return "NO TRADE"


def option_selection(signal, strike_mode):
    """Maps trade signal and strike preference (ITM/ATM/OTM) to option strategy."""
    if signal == "BUY":
        mode = str(strike_mode).upper()
        if mode == "ITM":
            return "Buy ITM Option"
        elif mode == "ATM":
            return "Buy ATM Option"
        else:
            return "Buy OTM Option"
    return "No Trade"


def scalper_signal(df):
    """
    Advanced price-action and indicator scalper strategy 
    using EMA trends, RSI filter and candle confirmation.
    """
    try:
        if df is None or len(df) < 20:
            return {"signal": "WAIT", "entry": None, "stop_loss": None, "target": None}

        df = df.copy()
        
        # Standardize column names to lowercase to prevent KeyErrors
        df.columns = [str(c).lower() for c in df.columns]

        if "close" not in df.columns or "open" not in df.columns or "low" not in df.columns or "high" not in df.columns:
            return {"signal": "WAIT", "entry": None, "stop_loss": None, "target": None}

        # Calculate EMA safely
        df["ema9"] = df["close"].ewm(span=9, adjust=False).mean()
        df["ema21"] = df["close"].ewm(span=21, adjust=False).mean()

        # Calculate RSI manually if not present
        delta = df["close"].diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.rolling(14).mean()
        avg_loss = loss.rolling(14).mean()
        
        rs = avg_gain / avg_loss.replace(0, 0.001)  # Division by zero safeguard
        df["rsi"] = 100 - (100 / (1 + rs))

        last = df.iloc[-1]
        prev = df.iloc[-2]

        signal = "WAIT"
        entry = None
        sl = None
        target = None

        # Bullish setup
        if (
            last["ema9"] > last["ema21"]
            and last["rsi"] > 50
            and last["close"] > last["open"]
            and prev["close"] < prev["open"]
        ):
            signal = "BUY"
            entry = float(last["close"])
            sl = float(last["low"])
            risk = entry - sl
            if risk > 0:
                target = entry + (risk * 1.5)
            else:
                target = entry * 1.01

        # Bearish setup
        elif (
            last["ema9"] < last["ema21"]
            and last["rsi"] < 50
            and last["close"] < last["open"]
            and prev["close"] > prev["open"]
        ):
            signal = "SELL"
            entry = float(last["close"])
            sl = float(last["high"])
            risk = sl - entry
            if risk > 0:
                target = entry - (risk * 1.5)
            else:
                target = entry * 0.99

        return {
            "signal": signal,
            "entry": round(entry, 2) if entry else None,
            "stop_loss": round(sl, 2) if sl else None,
            "target": round(target, 2) if target else None
        }

    except Exception as e:
        logging.error(f"❌ Error in scalper_signal: {e}")
        return {"signal": "WAIT", "entry": None, "stop_loss": None, "target": None}
    