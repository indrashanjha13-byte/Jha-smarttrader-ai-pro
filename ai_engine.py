import logging
import math


def ai_filter(rsi, volume):
    if rsi is None or volume is None:
        return False
    # Filter allows both strong uptrend (RSI > 60) and downtrend/oversold setup (RSI < 40) with volume confirmation
    if (rsi > 60 or rsi < 40) and volume > 100000:
        return True
    return False


def rank_signal(rsi, volume, trend):
    score = 0
    if rsi is not None:
        if rsi > 60 or rsi < 40:
            score += 30
    if volume is not None and volume > 100000:
        score += 30
    if trend in ("UP", "BULLISH", 1):
        score += 40
    elif trend in ("DOWN", "BEARISH", -1):
        score += 40
    return score


def market_regime(ema9, ema21, supertrend):
    if any(v is None for v in [ema9, ema21, supertrend]):
        return "SIDEWAYS"

    if ema9 > ema21 and supertrend > 0:
        return "BULLISH"
    elif ema9 < ema21 and supertrend < 0:
        return "BEARISH"

    return "SIDEWAYS"


def risk_check(balance, risk_percent, trade_amount):
    if balance <= 0 or risk_percent <= 0:
        return False
    max_risk = balance * (risk_percent / 100.0)
    return trade_amount <= max_risk


def trade_decision(signal, regime, risk_ok):
    if not risk_ok:
        return "NO TRADE"

    if signal == "BUY" and regime == "BULLISH":
        return "BUY"
    elif signal == "SELL" and regime == "BEARISH":
        return "SELL"

    return "HOLD"


def ai_brain(
    signal,
    rsi,
    volume,
    trend,
    ema9,
    ema21,
    supertrend,
    balance,
    risk_percent,
    trade_amount
):
    filter_ok = ai_filter(rsi, volume)
    score = rank_signal(rsi, volume, trend)
    regime = market_regime(ema9, ema21, supertrend)
    risk_ok = risk_check(balance, risk_percent, trade_amount)
    decision = trade_decision(signal, regime, risk_ok)

    return {
        "filter": filter_ok,
        "score": score,
        "regime": regime,
        "risk": risk_ok,
        "decision": decision
    }


def confidence_score(score, regime, filter_ok):
    confidence = float(score)

    if regime in ("BULLISH", "BEARISH"):
        confidence += 10.0

    if filter_ok:
        confidence += 10.0

    return min(max(confidence, 0.0), 100.0)


def stop_target(entry, atr=20, action="BUY"):
    entry = float(entry)
    atr = float(atr) if atr > 0 else 20.0

    if action == "SELL":
        stoploss = round(entry + atr, 2)
        target = round(entry - (atr * 2), 2)
    else:
        stoploss = round(entry - atr, 2)
        target = round(entry + (atr * 2), 2)

    return stoploss, target


def position_size(balance, risk_percent, stoploss_points):
    stoploss_points = abs(float(stoploss_points))
    if stoploss_points <= 0 or balance <= 0:
        return 1

    risk_amount = balance * (risk_percent / 100.0)
    qty = int(risk_amount / stoploss_points)

    return max(qty, 1)


def trailing_stop(entry, current_price, stoploss, action="BUY"):
    entry = float(entry)
    current_price = float(current_price)
    stoploss = float(stoploss)

    if action == "BUY":
        profit_points = current_price - entry
        if profit_points >= 80:
            stoploss = max(stoploss, entry + 60)
        elif profit_points >= 60:
            stoploss = max(stoploss, entry + 40)
        elif profit_points >= 40:
            stoploss = max(stoploss, entry + 20)
        elif profit_points >= 20:
            stoploss = max(stoploss, entry)
    else:
        profit_points = entry - current_price
        if profit_points >= 80:
            stoploss = min(stoploss, entry - 60)
        elif profit_points >= 60:
            stoploss = min(stoploss, entry - 40)
        elif profit_points >= 40:
            stoploss = min(stoploss, entry - 20)
        elif profit_points >= 20:
            stoploss = min(stoploss, entry)

    return round(stoploss, 2)


def daily_risk_manager(
    trades_today,
    losses_today,
    daily_loss,
    max_trades=5,
    max_losses=3,
    max_daily_loss=2000
):
    if trades_today >= max_trades:
        return False, "Max Trades Reached"

    if losses_today >= max_losses:
        return False, "Max Losses Reached"

    if daily_loss >= max_daily_loss:
        return False, "Daily Loss Limit Hit"

    return True, "Trading Allowed"