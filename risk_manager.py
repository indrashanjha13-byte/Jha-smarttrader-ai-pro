MAX_RISK_PER_TRADE = 2.0


def calculate_risk_amount(capital):
    """Maximum money allowed to be lost on one trade."""
    return round(
        capital * MAX_RISK_PER_TRADE / 100,
        2
    )


def calculate_lots(
    capital,
    entry_price,
    stoploss_price,
    lot_size
):
    """
    Calculate maximum number of lots based on 2% capital risk.

    Risk per unit = Entry - Stop Loss
    Risk per lot = Risk per unit × Lot Size
    """

    if capital <= 0:
        raise ValueError("Capital must be greater than 0.")

    if entry_price <= 0:
        raise ValueError("Entry price must be greater than 0.")

    if stoploss_price <= 0:
        raise ValueError("Stop-loss price must be greater than 0.")

    if stoploss_price >= entry_price:
        raise ValueError(
            "For a BUY trade, stop-loss must be below entry price."
        )

    if lot_size <= 0:
        raise ValueError("Lot size must be greater than 0.")

    risk_amount = calculate_risk_amount(capital)

    risk_per_unit = entry_price - stoploss_price

    risk_per_lot = risk_per_unit * lot_size

    if risk_per_lot <= 0:
        return 0

    lots = int(risk_amount // risk_per_lot)

    return max(lots, 0)


def calculate_trade_details(
    capital,
    entry_price,
    stoploss_price,
    lot_size,
    reward_ratio=2.0
):
    """Return complete risk, lot and target information."""

    lots = calculate_lots(
        capital,
        entry_price,
        stoploss_price,
        lot_size
    )

    risk_amount = calculate_risk_amount(capital)

    risk_per_unit = entry_price - stoploss_price

    risk_per_lot = risk_per_unit * lot_size

    total_quantity = lots * lot_size

    actual_risk = risk_per_lot * lots

    target_distance = risk_per_unit * reward_ratio

    target_price = entry_price + target_distance

    potential_profit = actual_risk * reward_ratio

    return {
        "risk_percent": MAX_RISK_PER_TRADE,
        "risk_amount": round(risk_amount, 2),
        "risk_per_unit": round(risk_per_unit, 2),
        "risk_per_lot": round(risk_per_lot, 2),
        "lots": lots,
        "lot_size": lot_size,
        "quantity": total_quantity,
        "actual_risk": round(actual_risk, 2),
        "target_price": round(target_price, 2),
        "reward_ratio": reward_ratio,
        "potential_profit": round(potential_profit, 2),
    }


def trailing_sl(
    current_price,
    stoploss,
    trail=20
):
    """Move stop-loss upward only."""

    return max(
        stoploss,
        current_price - trail
    )