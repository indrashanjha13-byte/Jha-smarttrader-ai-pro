def signal_score(
    rsi,
    volume_ratio,
    trend
):

    score = 0

    # RSI
    if rsi >= 70:
        score += 40
    elif rsi >= 60:
        score += 30
    elif rsi >= 50:
        score += 20
    else:
        score += 10

    # Volume
    if volume_ratio >= 2:
        score += 30
    elif volume_ratio >= 1.5:
        score += 20
    elif volume_ratio >= 1:
        score += 10

    # Trend
    if trend == "UP":
        score += 30

    return score
