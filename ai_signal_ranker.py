def signal_score(
    rsi,
    volume_ratio,
    trend
):

    score = 0

    if rsi > 60:
        score += 30

    if volume_ratio > 1.5:
        score += 30

    if trend == "UP":
        score += 40

    return score
