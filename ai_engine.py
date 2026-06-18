def ai_filter(
    rsi,
    volume
):

    if rsi > 60 and volume > 100000:

        return True

    return False

def rank_signal(
    rsi,
    volume,
    trend
):

    score = 0

    if rsi > 60:
        score += 30

    if volume > 100000:
        score += 30

    if trend == "UP":
        score += 40

    return score
