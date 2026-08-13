def confidence_engine(

    rsi,
    macd,
    macd_signal,
    ema9,
    ema21,
    volume,
    avg_volume,
    supertrend

):

    score = 0
    reasons = []

    # EMA
    if ema9 > ema21:
        score += 20
        reasons.append("EMA Bullish")

    else:
        reasons.append("EMA Bearish")

    # MACD
    if macd > macd_signal:
        score += 20
        reasons.append("MACD Bullish")

    else:
        reasons.append("MACD Bearish")

    # RSI
    if 40 <= rsi <= 65:
        score += 20
        reasons.append("Healthy RSI")

    elif rsi < 30:
        score += 10
        reasons.append("Oversold")

    elif rsi > 70:
        reasons.append("Overbought")

    # Volume
    if volume > avg_volume:
        score += 20
        reasons.append("High Volume")

    # SuperTrend
    if supertrend > 0:
        score += 20
        reasons.append("SuperTrend Bullish")

    confidence = min(score, 100)

    return {

        "confidence": confidence,

        "reasons": reasons

    }