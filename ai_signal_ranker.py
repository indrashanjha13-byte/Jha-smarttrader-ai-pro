def signal_score(
    rsi,
    volume_ratio,
    trend,
    macd,
    macd_signal,
    supertrend
):

    score = 50

    # RSI
    if rsi >= 70:
        score += 15
    elif rsi >= 60:
        score += 10
    elif rsi <= 30:
        score -= 15
    elif rsi <= 40:
        score -= 10

    # Volume
    if volume_ratio >= 2:
        score += 10
    elif volume_ratio >= 1.5:
        score += 5

    # MACD
    if macd > macd_signal:
        score += 15
    else:
        score -= 15

    # SuperTrend
    if supertrend > 0:
        score += 10
    else:
        score -= 10

    # Trend
    if trend == "UP":
        score += 10
    else:
        score -= 10

    score = max(0, min(100, score))

    return score
