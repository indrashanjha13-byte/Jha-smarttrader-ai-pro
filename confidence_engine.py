import logging
import math


def confidence_engine(
    rsi,
    macd,
    macd_signal,
    ema9,
    ema21,
    volume,
    avg_volume,
    supertrend,
    signal="BUY"
):
    """
    Calculates dynamic confidence score (0-100%) and detailed reasoning for BUY/SELL signals safely.
    """
    # 1. Inputs Type Safety & NaN Validation
    indicators = [rsi, macd, macd_signal, ema9, ema21, volume, avg_volume, supertrend]
    if any(val is None or (isinstance(val, float) and math.isnan(val)) for val in indicators):
        logging.warning("⚠️ Invalid or missing indicator values in confidence_engine. Returning default confidence.")
        return {"confidence": 50.0, "reasons": ["Insufficient/Invalid Market Data"]}

    score = 0.0
    reasons = []
    sig = str(signal).upper().strip()

    # ==========================
    # 1. EMA Trend Alignment (20 Points)
    # ==========================
    if sig == "BUY" and ema9 > ema21:
        score += 20.0
        reasons.append("EMA Bullish Alignment")
    elif sig == "SELL" and ema9 < ema21:
        score += 20.0
        reasons.append("EMA Bearish Alignment")
    else:
        reasons.append("EMA Trend Divergence")

    # ==========================
    # 2. MACD Momentum (20 Points)
    # ==========================
    macd_hist = macd - macd_signal
    if sig == "BUY" and macd_hist > 0:
        score += 20.0
        reasons.append("MACD Bullish Crossover")
    elif sig == "SELL" and macd_hist < 0:
        score += 20.0
        reasons.append("MACD Bearish Crossover")
    else:
        reasons.append("MACD Signal Misaligned")

    # ==========================
    # 3. RSI Zone Validation (20 Points)
    # ==========================
    if sig == "BUY":
        if 45 <= rsi <= 65:
            score += 20.0
            reasons.append("RSI Healthy Momentum")
        elif rsi < 35:
            score += 15.0
            reasons.append("RSI Oversold Reversal Zone")
        elif rsi > 70:
            reasons.append("RSI Overbought Risk")
    elif sig == "SELL":
        if 35 <= rsi <= 55:
            score += 20.0
            reasons.append("RSI Healthy Downtrend Momentum")
        elif rsi > 65:
            score += 15.0
            reasons.append("RSI Overbought Reversal Zone")
        elif rsi < 30:
            reasons.append("RSI Oversold Risk")

    # ==========================
    # 4. Volume Confirmation (20 Points)
    # ==========================
    if avg_volume > 0:
        vol_ratio = volume / avg_volume
        if vol_ratio >= 1.5:
            score += 20.0
            reasons.append("Strong Volume Surge (>1.5x)")
        elif vol_ratio >= 1.0:
            score += 10.0
            reasons.append("Above Average Volume")
        else:
            reasons.append("Low Volume Confirmation")

    # ==========================
    # 5. SuperTrend Alignment (20 Points)
    # ==========================
    if sig == "BUY" and supertrend > 0:
        score += 20.0
        reasons.append("SuperTrend Bullish")
    elif sig == "SELL" and supertrend < 0:
        score += 20.0
        reasons.append("SuperTrend Bearish")
    else:
        reasons.append("SuperTrend Against Trade Signal")

    # Final Confidence Score Clamp (0.0% to 100.0%)
    final_confidence = round(min(max(score, 0.0), 100.0), 2)

    return {
        "confidence": final_confidence,
        "reasons": reasons
    }