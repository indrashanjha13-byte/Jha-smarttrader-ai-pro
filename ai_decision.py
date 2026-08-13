def ai_decision(
    rsi,
    macd,
    macd_signal,
    ema9,
    ema21,
    supertrend,
    volume,
    avg_volume
):

    score = 0

    # RSI
    if rsi < 30:
        score += 3
    elif rsi < 40:
        score += 1
    elif rsi > 75:
        score -= 3
    elif rsi > 65:
        score -= 1

    # MACD
    if macd > macd_signal:
        score += 2
    else:
        score -= 2

    # EMA
    if ema9 > ema21:
        score += 2
    else:
        score -= 2

    # SuperTrend
    if supertrend > 0:
        score += 2
    else:
        score -= 2

    # Volume
    if volume > avg_volume:
        score += 1

    # Final Decision
    if score >= 5:
        decision = "BUY"
    elif score <= -5:
        decision = "SELL"
    else:
        decision = "HOLD"

    confidence = min(50 + abs(score) * 8, 95)

    return {
        "decision": decision,
        "score": score,
        "confidence": confidence
    }