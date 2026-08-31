import logging
import math


def signal_score(rsi, volume_ratio, trend, macd, macd_signal, supertrend):
    """
    Calculates a balanced trade signal score (0 to 100).
    Accounts for Bullish, Bearish, and Sideways market conditions safely.
    """
    # 1. Safety Check for None or NaN values
    indicators = [rsi, volume_ratio, macd, macd_signal, supertrend]
    if any(val is None or (isinstance(val, float) and math.isnan(val)) for val in indicators):
        logging.warning("⚠️ Invalid or missing indicator values in signal_score. Returning default neutral score (50).")
        return 50.0

    score = 50.0

    # 2. RSI (Momentum Analysis)
    if 50 <= rsi < 70:
        score += 10.0   # Healthy Uptrend Momentum
    elif rsi >= 70:
        score += 5.0    # Strong Momentum but Overbought Risk
    elif 30 < rsi <= 50:
        score -= 10.0   # Downtrend Momentum
    elif rsi <= 30:
        score -= 5.0    # Oversold Zone (Potential Reversal)

    # 3. Volume Confirmation
    if volume_ratio >= 2.0:
        score += 15.0   # Strong Institutional Activity
    elif volume_ratio >= 1.5:
        score += 8.0    # Good Volume Confirmation

    # 4. MACD Momentum Crossover
    macd_hist = macd - macd_signal
    if macd_hist > 0:
        score += 12.0   # Bullish Crossover
    elif macd_hist < 0:
        score -= 12.0   # Bearish Crossover

    # 5. SuperTrend Alignment
    if supertrend > 0:
        score += 10.0   # Bullish Trend Line
    elif supertrend < 0:
        score -= 10.0   # Bearish Trend Line

    # 6. Overall Market Trend Check
    trend_upper = str(trend).upper() if trend else "NEUTRAL"
    if trend_upper == "UP":
        score += 10.0
    elif trend_upper == "DOWN":
        score -= 10.0
    # Sideways/Neutral keeps score unchanged (No harsh penalty)

    # Clamp final score strictly between 0 and 100
    return round(min(max(score, 0.0), 100.0), 2)