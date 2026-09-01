import logging
import math


def _safe_float(value, default=0.0):
    """Safely convert value to float and handle NaN/Inf."""
    try:
        if value is None:
            return default

        value = float(value)

        if math.isnan(value) or math.isinf(value):
            return default

        return value

    except (TypeError, ValueError):
        return default


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
    Main AI decision layer.

    Compatible with:
        signals.py
        dashboard.py
        ai_engine.py

    Returns:
        decision
        score
        confidence
    """

    # =====================================================
    # SAFE VALUES
    # =====================================================

    rsi = _safe_float(rsi, 50.0)
    macd = _safe_float(macd, 0.0)
    macd_signal = _safe_float(macd_signal, 0.0)
    ema9 = _safe_float(ema9, 0.0)
    ema21 = _safe_float(ema21, 0.0)
    volume = _safe_float(volume, 0.0)
    avg_volume = _safe_float(avg_volume, 0.0)
    supertrend = _safe_float(supertrend, 0.0)

    score = 0

    # =====================================================
    # 1. RSI
    # =====================================================

    if rsi <= 30:
        score += 2

    elif rsi <= 40:
        score += 1

    elif rsi >= 70:
        score -= 2

    elif rsi >= 60:
        score -= 1

    # =====================================================
    # 2. MACD
    # =====================================================

    if macd > macd_signal:
        score += 2

    elif macd < macd_signal:
        score -= 2

    # =====================================================
    # 3. EMA TREND
    # =====================================================

    if ema9 > ema21:
        score += 2

    elif ema9 < ema21:
        score -= 2

    # =====================================================
    # 4. SUPERTREND DIRECTION
    #
    # signals.py returns ST_DIRECTION as:
    # +1 = Bullish
    # -1 = Bearish
    # =====================================================

    if supertrend > 0:
        score += 2

    elif supertrend < 0:
        score -= 2

    # =====================================================
    # 5. VOLUME CONFIRMATION
    # =====================================================

    volume_confirmed = False

    if avg_volume > 0:
        volume_ratio = volume / avg_volume

        if volume_ratio >= 1.20:
            volume_confirmed = True

            if score > 0:
                score += 1

            elif score < 0:
                score -= 1

    # =====================================================
    # 6. FINAL DECISION
    # =====================================================

    if score >= 5:
        decision = "BUY"

    elif score <= -5:
        decision = "SELL"

    else:
        decision = "HOLD"

    # =====================================================
    # 7. CONFIDENCE
    # =====================================================

    # Maximum theoretical score = 9
    confidence = 50 + (abs(score) * 5)

    if volume_confirmed:
        confidence += 5

    confidence = min(
        max(confidence, 50),
        95
    )

    # =====================================================
    # RETURN
    # =====================================================

    return {
        "decision": decision,
        "score": score,
        "confidence": round(confidence, 2),
        "volume_confirmed": volume_confirmed
    }


# =========================================================
# TEST
# =========================================================

if __name__ == "__main__":

    result = ai_decision(
        rsi=65,
        macd=100,
        macd_signal=80,
        ema9=52000,
        ema21=51800,
        supertrend=1,
        volume=250000,
        avg_volume=150000
    )

    print("===== AI DECISION TEST =====")

    for key, value in result.items():
        print(f"{key}: {value}")