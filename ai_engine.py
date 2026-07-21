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

def market_regime(
    ema9,
    ema21,
    supertrend
):

    if ema9 > ema21 and supertrend > 0:
        return "BULLISH"

    elif ema9 < ema21 and supertrend < 0:
        return "BEARISH"

    return "SIDEWAYS"

def risk_check(
    balance,
    risk_percent,
    trade_amount
):

    max_risk = balance * (risk_percent / 100)

    if trade_amount <= max_risk:
        return True

    return False

def trade_decision(
    signal,
    regime,
    risk_ok
):

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

    score = rank_signal(
        rsi,
        volume,
        trend
    )

    regime = market_regime(
        ema9,
        ema21,
        supertrend
    )

    risk_ok = risk_check(
        balance,
        risk_percent,
        trade_amount
    )

    decision = trade_decision(
        signal,
        regime,
        risk_ok
    )

    return {
        "filter": filter_ok,
        "score": score,
        "regime": regime,
        "risk": risk_ok,
        "decision": decision
    }

def confidence_score(
    score,
    regime,
    filter_ok
):

    confidence = score

    if regime == "BULLISH":
        confidence += 10

    elif regime == "BEARISH":
        confidence += 10

    if filter_ok:
        confidence += 10

    if confidence > 100:
        confidence = 100

    return confidence
def stop_target(entry, atr=20):

    stoploss = entry - atr
    target = entry + (atr * 2)

    return stoploss, target


def position_size(
    balance,
    risk_percent,
    stoploss_points
):

    risk_amount = balance * (risk_percent / 100)

    qty = int(risk_amount / stoploss_points)

    if qty < 1:
        qty = 1

    return qty


def trailing_stop(
    entry,
    current_price,
    stoploss
):

    if current_price >= entry + 20:
        stoploss = entry

    if current_price >= entry + 40:
        stoploss = entry + 20

    if current_price >= entry + 60:
        stoploss = entry + 40

    if current_price >= entry + 80:
        stoploss = entry + 60

    return stoploss

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
