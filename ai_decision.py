import logging
import math


def ai_decision(
    rsi,
    macd,
    macd_signal,
    ema9,
    ema21,
    supertrend,
    volume,
    avg_volume,
    **kwargs
):
    """
    Evaluates technical indicators and generates AI Trading Decision (BUY/SELL/HOLD).
    Handles None/NaN values safely to prevent engine crashes.
    """
    # Defensive Check: Handle None/NaN inputs safely
    inputs = [rsi, macd, macd_signal, ema9, ema21, supertrend, volume, avg_volume]
    if any(val is None or (isinstance(val, float) and math.isnan(val)) for val in inputs):
        logging.warning("⚠️ Invalid or missing indicator values received in ai_decision. Returning HOLD.")
        return {"decision": "HOLD", "score": 0, "confidence": 50}

    score = 0

    # 1. RSI Rules
    if rsi < 30:
        score += 3  # Strongly Oversold -> Strong Buy signal
    elif rsi < 40:
        score += 1  # Moderately Oversold
    elif rsi > 70:
        score -= 3  # Strongly Overbought -> Strong Sell signal
    elif rsi > 60:
        score -= 1  # Moderately Overbought

    # 2. MACD Crossover Rules
    if macd > macd_signal:
        score += 2  # Bullish Momentum
    elif macd < macd_signal:
        score -= 2  # Bearish Momentum

    # 3. EMA Trend Alignment Rules
    if ema9 > ema21:
        score += 2  # Short term Uptrend
    elif ema9 < ema21:
        score -= 2  # Short term Downtrend

    # 4. SuperTrend Rules
    if supertrend > 0 or supertrend == 1:
        score += 2  # Bullish Supertrend
    elif supertrend < 0 or supertrend == -1:
        score -= 2  # Bearish Supertrend

    # 5. Volume Surge Confirmation
    if avg_volume > 0 and volume > (avg_volume * 1.2):
        # Confirm trend strength only if volume is 20%+ higher than average
        if score > 0:
            score += 1
        elif score < 0:
            score -= 1

    # 6. Final Trade Decision Thresholds
    if score >= 5:
        decision = "BUY"
    elif score <= -5:
        decision = "SELL"
    else:
        decision = "HOLD"

    # Dynamic Confidence Calculation (Scaled between 50% and 95%)
    confidence = min(50 + abs(score) * 7.5, 95.0)

    return {
        "decision": decision,
        "score": score,
        "confidence": round(confidence, 2)
    }