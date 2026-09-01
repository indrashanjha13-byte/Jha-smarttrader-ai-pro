import logging
import math


def _safe_float(value, default=0.0):
    """Safely convert value to float."""
    try:
        if value is None:
            return default

        value = float(value)

        if math.isnan(value) or math.isinf(value):
            return default

        return value

    except (TypeError, ValueError):
        return default


def market_regime(
    ema9,
    ema21,
    supertrend_direction
):
    """
    Determines current market regime.

    Returns:
        BULLISH
        BEARISH
        SIDEWAYS
    """

    ema9 = _safe_float(ema9)
    ema21 = _safe_float(ema21)

    # Normalize SuperTrend direction
    st = str(supertrend_direction).upper().strip()

    bullish_st = st in (
        "UP",
        "BULLISH",
        "BUY",
        "1",
        "1.0"
    )

    bearish_st = st in (
        "DOWN",
        "BEARISH",
        "SELL",
        "-1",
        "-1.0"
    )

    # Bullish market
    if ema9 > ema21 and bullish_st:
        return "BULLISH"

    # Bearish market
    if ema9 < ema21 and bearish_st:
        return "BEARISH"

    # No clear trend
    return "SIDEWAYS"


def get_market_regime(
    ema9,
    ema21,
    supertrend_direction
):
    """
    Alias for market_regime().
    Keeps compatibility with modules that use get_market_regime().
    """
    return market_regime(
        ema9,
        ema21,
        supertrend_direction
    )


if __name__ == "__main__":

    print("===== MARKET REGIME TEST =====")

    print(
        "Bullish:",
        market_regime(
            ema9=52000,
            ema21=51800,
            supertrend_direction="UP"
        )
    )

    print(
        "Bearish:",
        market_regime(
            ema9=51800,
            ema21=52000,
            supertrend_direction="DOWN"
        )
    )

    print(
        "Sideways:",
        market_regime(
            ema9=52000,
            ema21=51800,
            supertrend_direction="DOWN"
        )
    )
