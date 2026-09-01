import logging
import math
from typing import Dict, Tuple, Optional


# =========================================================
# CONFIG
# =========================================================

DEFAULT_ATR_MULTIPLIER = 1.0
DEFAULT_TARGET_RR = 2.0

DEFAULT_MAX_TRADES = 5
DEFAULT_MAX_LOSSES = 3
DEFAULT_MAX_DAILY_LOSS = 2000.0


# =========================================================
# SAFE NUMBER
# =========================================================

def _safe_float(value, default=0.0):
    try:
        if value is None:
            return default

        value = float(value)

        if math.isnan(value) or math.isinf(value):
            return default

        return value

    except (TypeError, ValueError):
        return default


def _safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


# =========================================================
# AI FILTER
# =========================================================

def ai_filter(
    rsi,
    volume,
    avg_volume=None,
    min_rsi=60,
    max_rsi=40
):
    rsi = _safe_float(rsi, None)
    volume = _safe_float(volume, None)

    if rsi is None or volume is None:
        return False

    # Relative volume
    if avg_volume is not None:
        avg_volume = _safe_float(avg_volume, 0.0)

        if avg_volume > 0:
            volume_ok = volume >= avg_volume * 1.20
        else:
            volume_ok = volume > 100000
    else:
        volume_ok = volume > 100000

    momentum_ok = (
        rsi >= min_rsi or
        rsi <= max_rsi
    )

    return momentum_ok and volume_ok


# =========================================================
# SIGNAL RANKING
# =========================================================

def rank_signal(
    rsi,
    volume,
    trend,
    macd=None,
    ema9=None,
    ema21=None,
    supertrend_direction=None,
    avg_volume=None
):
    score = 0

    rsi = _safe_float(rsi, 50)
    volume = _safe_float(volume, 0)

    # -----------------------------------------------------
    # RSI
    # -----------------------------------------------------

    if rsi >= 60 or rsi <= 40:
        score += 20

    # -----------------------------------------------------
    # VOLUME
    # -----------------------------------------------------

    if avg_volume is not None:
        avg_volume = _safe_float(avg_volume)

        if avg_volume > 0 and volume >= avg_volume * 1.20:
            score += 20
    elif volume > 100000:
        score += 20

    # -----------------------------------------------------
    # TREND
    # -----------------------------------------------------

    trend = str(trend).upper()

    if trend in ("UP", "BULLISH", "BUY", "1"):
        score += 20

    elif trend in ("DOWN", "BEARISH", "SELL", "-1"):
        score += 20

    # -----------------------------------------------------
    # MACD
    # -----------------------------------------------------

    if macd is not None:

        macd_value = _safe_float(macd)

        if macd_value > 0 or macd_value < 0:
            score += 10

    # -----------------------------------------------------
    # EMA
    # -----------------------------------------------------

    if ema9 is not None and ema21 is not None:

        ema9 = _safe_float(ema9)
        ema21 = _safe_float(ema21)

        if ema9 > ema21 or ema9 < ema21:
            score += 10

    # -----------------------------------------------------
    # SUPERTREND
    # -----------------------------------------------------

    if supertrend_direction is not None:

        direction = str(
            supertrend_direction
        ).upper()

        if direction in (
            "UP",
            "BULLISH",
            "BUY",
            "DOWN",
            "BEARISH",
            "SELL"
        ):
            score += 20

    return min(score, 100)


# =========================================================
# MARKET REGIME
# =========================================================

def market_regime(
    ema9,
    ema21,
    supertrend_direction
):
    ema9 = _safe_float(ema9)
    ema21 = _safe_float(ema21)

    direction = str(
        supertrend_direction
    ).upper()

    bullish_st = direction in (
        "UP",
        "BULLISH",
        "BUY",
        "1"
    )

    bearish_st = direction in (
        "DOWN",
        "BEARISH",
        "SELL",
        "-1"
    )

    if ema9 > ema21 and bullish_st:
        return "BULLISH"

    if ema9 < ema21 and bearish_st:
        return "BEARISH"

    return "SIDEWAYS"


# =========================================================
# RISK CHECK
# =========================================================

def risk_check(
    balance,
    risk_percent,
    stoploss_points,
    quantity=1
):
    balance = _safe_float(balance)
    risk_percent = _safe_float(risk_percent)
    stoploss_points = abs(
        _safe_float(stoploss_points)
    )
    quantity = max(
        _safe_int(quantity, 1),
        1
    )

    if balance <= 0:
        return False

    if risk_percent <= 0:
        return False

    if stoploss_points <= 0:
        return False

    max_risk = (
        balance *
        risk_percent /
        100.0
    )

    actual_risk = (
        stoploss_points *
        quantity
    )

    return actual_risk <= max_risk


# =========================================================
# TRADE DECISION
# =========================================================

def trade_decision(
    signal,
    regime,
    risk_ok,
    confidence=0,
    minimum_confidence=65
):
    signal = str(signal).upper()

    confidence = _safe_float(
        confidence
    )

    if not risk_ok:
        return "NO TRADE"

    if confidence < minimum_confidence:
        return "NO TRADE"

    if signal == "BUY" and regime == "BULLISH":
        return "BUY"

    if signal == "SELL" and regime == "BEARISH":
        return "SELL"

    return "HOLD"


# =========================================================
# CONFIDENCE SCORE
# =========================================================

def confidence_score(
    score,
    regime,
    filter_ok,
    signal=None
):
    score = _safe_float(score)

    confidence = 40.0

    # Score
    confidence += score * 0.45

    # Regime
    if regime in (
        "BULLISH",
        "BEARISH"
    ):
        confidence += 5

    # AI filter
    if filter_ok:
        confidence += 10

    # Signal validation
    if signal is not None:
        signal = str(signal).upper()

        if (
            signal == "BUY"
            and regime == "BULLISH"
        ):
            confidence += 5

        elif (
            signal == "SELL"
            and regime == "BEARISH"
        ):
            confidence += 5

    return round(
        min(
            max(confidence, 0),
            95
        ),
        2
    )


# =========================================================
# STOP LOSS + TARGET
# =========================================================

def stop_target(
    entry,
    atr=20,
    action="BUY",
    atr_multiplier=DEFAULT_ATR_MULTIPLIER,
    target_rr=DEFAULT_TARGET_RR
):
    entry = _safe_float(entry)
    atr = abs(
        _safe_float(atr, 20)
    )

    atr_multiplier = abs(
        _safe_float(
            atr_multiplier,
            1.0
        )
    )

    target_rr = abs(
        _safe_float(
            target_rr,
            2.0
        )
    )

    if entry <= 0:
        return 0.0, 0.0

    if atr <= 0:
        atr = 20.0

    if atr_multiplier <= 0:
        atr_multiplier = 1.0

    if target_rr <= 0:
        target_rr = 2.0

    risk_distance = (
        atr *
        atr_multiplier
    )

    action = str(action).upper()

    if action == "SELL":

        stoploss = (
            entry +
            risk_distance
        )

        target = (
            entry -
            risk_distance *
            target_rr
        )

    else:

        stoploss = (
            entry -
            risk_distance
        )

        target = (
            entry +
            risk_distance *
            target_rr
        )

    return (
        round(stoploss, 2),
        round(target, 2)
    )


# =========================================================
# POSITION SIZE
# =========================================================

def position_size(
    balance,
    risk_percent,
    stoploss_points,
    lot_size=1
):
    balance = _safe_float(balance)
    risk_percent = _safe_float(
        risk_percent
    )

    stoploss_points = abs(
        _safe_float(stoploss_points)
    )

    lot_size = max(
        _safe_int(lot_size, 1),
        1
    )

    if balance <= 0:
        return lot_size

    if risk_percent <= 0:
        return lot_size

    if stoploss_points <= 0:
        return lot_size

    risk_amount = (
        balance *
        risk_percent /
        100.0
    )

    raw_qty = (
        risk_amount /
        stoploss_points
    )

    lots = int(
        raw_qty /
        lot_size
    )

    return max(
        lots * lot_size,
        lot_size
    )


# =========================================================
# ATR TRAILING STOP
# =========================================================

def trailing_stop(
    entry,
    current_price,
    stoploss,
    atr=20,
    action="BUY",
    trail_multiplier=1.0
):
    entry = _safe_float(entry)
    current_price = _safe_float(
        current_price
    )

    stoploss = _safe_float(
        stoploss
    )

    atr = abs(
        _safe_float(atr, 20)
    )

    trail_multiplier = abs(
        _safe_float(
            trail_multiplier,
            1.0
        )
    )

    action = str(action).upper()

    if (
        entry <= 0 or
        current_price <= 0
    ):
        return round(
            stoploss,
            2
        )

    if atr <= 0:
        atr = 20

    if trail_multiplier <= 0:
        trail_multiplier = 1.0

    trail_distance = (
        atr *
        trail_multiplier
    )

    # -----------------------------------------------------
    # BUY
    # -----------------------------------------------------

    if action == "BUY":

        profit = (
            current_price -
            entry
        )

        # Start trailing only after
        # minimum 1 ATR profit

        if profit >= atr:

            new_stop = (
                current_price -
                trail_distance
            )

            stoploss = max(
                stoploss,
                new_stop
            )

    # -----------------------------------------------------
    # SELL
    # -----------------------------------------------------

    elif action == "SELL":

        profit = (
            entry -
            current_price
        )

        if profit >= atr:

            new_stop = (
                current_price +
                trail_distance
            )

            stoploss = min(
                stoploss,
                new_stop
            )

    return round(
        stoploss,
        2
    )


# =========================================================
# DAILY RISK MANAGER
# =========================================================

def daily_risk_manager(
    trades_today,
    losses_today,
    daily_loss,
    max_trades=DEFAULT_MAX_TRADES,
    max_losses=DEFAULT_MAX_LOSSES,
    max_daily_loss=DEFAULT_MAX_DAILY_LOSS
):
    try:

        trades_today = _safe_int(
            trades_today
        )

        losses_today = _safe_int(
            losses_today
        )

        daily_loss = _safe_float(
            daily_loss
        )

        max_trades = _safe_int(
            max_trades
        )

        max_losses = _safe_int(
            max_losses
        )

        max_daily_loss = _safe_float(
            max_daily_loss
        )

    except Exception as e:

        logging.error(
            f"Risk Manager Error: {e}"
        )

        return (
            False,
            "Invalid Risk Parameters"
        )

    if max_trades <= 0:
        return (
            False,
            "Invalid Max Trades"
        )

    if max_losses < 0:
        return (
            False,
            "Invalid Max Losses"
        )

    if max_daily_loss <= 0:
        return (
            False,
            "Invalid Daily Loss Limit"
        )

    if trades_today >= max_trades:
        return (
            False,
            "Max Trades Reached"
        )

    if losses_today >= max_losses:
        return (
            False,
            "Max Losses Reached"
        )

    if daily_loss >= max_daily_loss:
        return (
            False,
            "Daily Loss Limit Hit"
        )

    return (
        True,
        "Trading Allowed"
    )


# =========================================================
# COMPLETE AI BRAIN
# =========================================================

def ai_brain(
    signal,
    rsi,
    volume,
    trend,
    ema9,
    ema21,
    supertrend_direction,
    balance,
    risk_percent,
    entry,
    atr=20,
    lot_size=1,
    macd=None,
    avg_volume=None,
    minimum_confidence=65
):
    signal = str(signal).upper()

    # -----------------------------------------------------
    # AI FILTER
    # -----------------------------------------------------

    filter_ok = ai_filter(
        rsi,
        volume,
        avg_volume
    )

    # -----------------------------------------------------
    # MARKET REGIME
    # -----------------------------------------------------

    regime = market_regime(
        ema9,
        ema21,
        supertrend_direction
    )

    # -----------------------------------------------------
    # SCORE
    # -----------------------------------------------------

    score = rank_signal(
        rsi=rsi,
        volume=volume,
        trend=trend,
        macd=macd,
        ema9=ema9,
        ema21=ema21,
        supertrend_direction=supertrend_direction,
        avg_volume=avg_volume
    )

    # -----------------------------------------------------
    # CONFIDENCE
    # -----------------------------------------------------

    confidence = confidence_score(
        score,
        regime,
        filter_ok,
        signal
    )

    # -----------------------------------------------------
    # SL + TARGET
    # -----------------------------------------------------

    stoploss, target = stop_target(
        entry=entry,
        atr=atr,
        action=signal
    )

    # -----------------------------------------------------
    # STOP DISTANCE
    # -----------------------------------------------------

    stoploss_points = abs(
        _safe_float(entry) -
        stoploss
    )

    # -----------------------------------------------------
    # POSITION SIZE
    # -----------------------------------------------------

    quantity = position_size(
        balance=balance,
        risk_percent=risk_percent,
        stoploss_points=stoploss_points,
        lot_size=lot_size
    )

    # -----------------------------------------------------
    # RISK CHECK
    # -----------------------------------------------------

    risk_ok = risk_check(
        balance=balance,
        risk_percent=risk_percent,
        stoploss_points=stoploss_points,
        quantity=quantity
    )

    # -----------------------------------------------------
    # FINAL DECISION
    # -----------------------------------------------------

    decision = trade_decision(
        signal=signal,
        regime=regime,
        risk_ok=risk_ok,
        confidence=confidence,
        minimum_confidence=minimum_confidence
    )

    return {
        "filter": filter_ok,
        "score": score,
        "confidence": confidence,
        "regime": regime,
        "risk": risk_ok,
        "decision": decision,
        "entry": round(
            _safe_float(entry),
            2
        ),
        "stoploss": stoploss,
        "target": target,
        "stoploss_points": round(
            stoploss_points,
            2
        ),
        "quantity": quantity,
        "risk_reward": round(
            abs(target - _safe_float(entry)) /
            stoploss_points
            if stoploss_points > 0
            else 0,
            2
        )
    }


# =========================================================
# MODULE TEST
# =========================================================

if __name__ == "__main__":

    result = ai_brain(
        signal="BUY",
        rsi=65,
        volume=250000,
        trend="UP",
        ema9=52000,
        ema21=51800,
        supertrend_direction="UP",
        balance=100000,
        risk_percent=1,
        entry=52000,
        atr=100,
        lot_size=1,
        macd=50,
        avg_volume=150000
    )

    print("\n===== AI BRAIN TEST =====")

    for key, value in result.items():
        print(
            f"{key}: {value}"
        )