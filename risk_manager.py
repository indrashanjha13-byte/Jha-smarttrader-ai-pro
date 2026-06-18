MAX_RISK_PER_TRADE = 2

def calculate_qty(
    capital,
    entry_price,
    stoploss_price
):

    risk_amount = (
        capital * MAX_RISK_PER_TRADE
    ) / 100

    risk_per_share = (
        entry_price - stoploss_price
    )

    qty = int(
        risk_amount /
        risk_per_share
    )

    return qty

def trailing_sl(
    current_price,
    stoploss,
    trail=20
):

    new_sl = max(
        stoploss,
        current_price - trail
    )

    return new_sl
