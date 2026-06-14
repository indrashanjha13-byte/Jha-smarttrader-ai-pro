def generate_signal(ema9, ema21, rsi, macd, macd_signal, volume, avg_volume):

    print("EMA9 =", ema9, type(ema9))
    print("EMA21 =", ema21, type(ema21))
    print("RSI =", rsi, type(rsi))
    print("MACD =", macd, type(macd))
    print("MACD_SIGNAL =", macd_signal, type(macd_signal))

    if (
        ema9 > ema21
        and rsi > 55
        and macd > macd_signal
        and volume > avg_volume
    ):
        return "BUY"

    elif (
        ema9 < ema21
        and rsi < 45
        and macd < macd_signal
        and volume > avg_volume
    ):
        return "SELL"

    return "NO TRADE"

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