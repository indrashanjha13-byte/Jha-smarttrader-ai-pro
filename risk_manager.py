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
    lot_size,
    direction="LONG"
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

    direction = str(direction).upper().strip()

    if direction not in ("LONG", "SHORT"):
        raise ValueError("Direction must be LONG or SHORT.")

    if direction == "LONG" and stoploss_price >= entry_price:
        raise ValueError("For a LONG trade, stop-loss must be below entry price.")

    if direction == "SHORT" and stoploss_price <= entry_price:
        raise ValueError("For a SHORT trade, stop-loss must be above entry price.")

    if lot_size <= 0:
        raise ValueError("Lot size must be greater than 0.")

    risk_amount = calculate_risk_amount(capital)

    direction = str(direction).upper().strip()

    if direction not in ("LONG", "SHORT"):
        raise ValueError("Direction must be LONG or SHORT.")

    if direction == "LONG":
        risk_per_unit = entry_price - stoploss_price
    else:
        risk_per_unit = stoploss_price - entry_price

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
    reward_ratio=2.0,
    direction="LONG"
):
    """Return complete risk, lot and target information."""

    lots = calculate_lots(
        capital,
        entry_price,
        stoploss_price,
        lot_size,
        direction
    )

    risk_amount = calculate_risk_amount(capital)

    direction = str(direction).upper().strip()

    if direction not in ("LONG", "SHORT"):
        raise ValueError("Direction must be LONG or SHORT.")

    if direction == "LONG":
        risk_per_unit = entry_price - stoploss_price
    else:
        risk_per_unit = stoploss_price - entry_price

    risk_per_lot = risk_per_unit * lot_size

    total_quantity = lots * lot_size

    actual_risk = risk_per_lot * lots

    target_distance = risk_per_unit * reward_ratio

    if direction == "LONG":
        target_price = entry_price + target_distance
    else:
        target_price = entry_price - target_distance

    potential_profit = actual_risk * reward_ratio

    # Keep high precision for low-priced Futures.
    # Keep normal 2 decimals for regular instruments.
    precision = 8 if entry_price < 1 else 2

    return {
        "risk_percent": MAX_RISK_PER_TRADE,
        "risk_amount": round(risk_amount, 2),
        "risk_per_unit": round(risk_per_unit, precision),
        "risk_per_lot": round(risk_per_lot, precision),
        "lots": lots,
        "lot_size": lot_size,
        "quantity": total_quantity,
        "actual_risk": round(actual_risk, 2),
        "target_price": round(target_price, precision),
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
def calculate_delta_trade_details(
    capital,
    entry_price,
    stoploss_price,
    contract_value=1.0,
    reward_ratio=2.0,
    direction="LONG",
    tick_size=None,
    max_contracts=None,
    max_notional=None,
):
    """Calculate risk, contracts, stop-loss and target for Delta Futures."""

    if capital <= 0:
        raise ValueError("Capital must be greater than 0.")

    if entry_price <= 0:
        raise ValueError("Entry price must be greater than 0.")

    if stoploss_price <= 0:
        raise ValueError("Stop-loss price must be greater than 0.")

    if contract_value <= 0:
        raise ValueError("Contract value must be greater than 0.")

    direction = str(direction).upper().strip()

    if direction not in ("LONG", "SHORT"):
        raise ValueError("Direction must be LONG or SHORT.")

    if direction == "LONG" and stoploss_price >= entry_price:
        raise ValueError(
            "For a LONG trade, stop-loss must be below entry price."
        )

    if direction == "SHORT" and stoploss_price <= entry_price:
        raise ValueError(
            "For a SHORT trade, stop-loss must be above entry price."
        )

    risk_amount = calculate_risk_amount(capital)

    # Normalize execution prices before calculating quantity.
    # This guarantees that risk and notional use the same
    # prices that will actually be returned for execution.
    if tick_size and tick_size > 0:
        entry_price = round(
            round(entry_price / tick_size) * tick_size,
            12
        )
        stoploss_price = round(
            round(stoploss_price / tick_size) * tick_size,
            12
        )

    risk_per_contract = (
        abs(entry_price - stoploss_price)
        * contract_value
    )

    if risk_per_contract <= 0:
        raise ValueError("Risk per contract must be greater than 0.")

    contracts = int(risk_amount // risk_per_contract)

    if max_contracts is not None:
        contracts = min(
            contracts,
            max(int(max_contracts), 0)
        )

    if max_notional is not None and entry_price > 0:
        notional_per_contract = (
            entry_price * contract_value
        )

        if notional_per_contract > 0:
            notional_contracts = int(
                max_notional // notional_per_contract
            )
            contracts = min(
                contracts,
                max(notional_contracts, 0)
            )

            # Final hard safety check against floating-point
            # rounding and the exact execution entry price.
            while (
                contracts > 0
                and (
                    entry_price
                    * contract_value
                    * contracts
                ) > max_notional
            ):
                contracts -= 1

    actual_risk = (
        risk_per_contract * contracts
    )

    target_distance = (
        abs(entry_price - stoploss_price)
        * reward_ratio
    )

    if direction == "LONG":
        target_price = entry_price + target_distance
    else:
        target_price = entry_price - target_distance

    potential_profit = (
        actual_risk * reward_ratio
    )

    if tick_size and tick_size > 0:
        stoploss_price = round(
            round(stoploss_price / tick_size) * tick_size,
            12
        )
        target_price = round(
            round(target_price / tick_size) * tick_size,
            12
        )

    precision = 8 if entry_price < 1 else 2

    return {
        "risk_percent": MAX_RISK_PER_TRADE,
        "risk_amount": round(risk_amount, 2),
        "risk_per_contract": round(
            risk_per_contract,
            precision
        ),
        "contracts": contracts,
        "contract_value": contract_value,
        "actual_risk": round(actual_risk, 2),
        "entry_price": round(entry_price, precision),
        "stoploss_price": round(stoploss_price, precision),
        "target_price": round(target_price, precision),
        "reward_ratio": reward_ratio,
        "potential_profit": round(
            potential_profit,
            2
        ),
        "tick_size": tick_size,
    }
