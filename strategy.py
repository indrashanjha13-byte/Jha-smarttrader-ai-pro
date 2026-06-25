def generate_signal(
    supertrend,
    macd,
    macd_signal,
    volume,
    avg_volume
):

    # BUY
    if (
        supertrend > 0
        and macd > macd_signal
        and volume > avg_volume
    ):
        return "BUY"

    # SELL
    elif (
        supertrend < 0
        and macd < macd_signal
        and volume > avg_volume
    ):
        return "SELL"

    return "NO TRADE"


def ema_signal(ema9, ema21):

    if ema9 > ema21:
        return "BUY"

    elif ema9 < ema21:
        return "SELL"

    return "NO TRADE"


def rsi_signal(rsi):

    if rsi < 30:
        return "BUY"

    elif rsi > 70:
        return "SELL"

    return "NO TRADE"


def supertrend_signal(supertrend):

    if supertrend > 0:
        return "BUY"

    elif supertrend < 0:
        return "SELL"

    return "NO TRADE"

def option_selection(signal, strike_mode):

    if signal == "BUY":
        if strike_mode == "ITM":
            return "Buy ITM Option"
        elif strike_mode == "ATM":
            return "Buy ATM Option"
        else:
            return "Buy OTM Option"

    return "No Trade"

import pandas as pd


def scalper_signal(df):

    df = df.copy()

    # EMA
    df["ema9"] = df["close"].ewm(span=9).mean()
    df["ema21"] = df["close"].ewm(span=21).mean()

    # RSI
    delta = df["close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()

    rs = avg_gain / avg_loss
    df["rsi"] = 100 - (100 / (1 + rs))


    last = df.iloc[-1]
    prev = df.iloc[-2]


    signal = "WAIT"
    entry = None
    sl = None
    target = None


    # Bullish candle + trend

    if (
        last["ema9"] > last["ema21"]
        and last["rsi"] > 50
        and last["close"] > last["open"]
        and prev["close"] < prev["open"]
    ):

        signal = "BUY"

        entry = last["close"]
        sl = last["low"]

        risk = entry - sl
        target = entry + (risk * 1.5)



    # Bearish candle + trend

    elif (
        last["ema9"] < last["ema21"]
        and last["rsi"] < 50
        and last["close"] < last["open"]
        and prev["close"] > prev["open"]
    ):

        signal = "SELL"

        entry = last["close"]
        sl = last["high"]

        risk = sl - entry
        target = entry - (risk * 1.5)


    return {
        "signal": signal,
        "entry": round(entry,2) if entry else None,
        "stop_loss": round(sl,2) if sl else None,
        "target": round(target,2) if target else None
    }
