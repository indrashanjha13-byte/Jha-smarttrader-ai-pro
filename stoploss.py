def stoploss(
    entry,
    atr
):

    return entry - (2 * atr)
def target(
    entry,
    atr
):

    return entry + (4 * atr)


def check_exit(
    entry,
    current_price,
    atr
):

    sl = stoploss(
        entry,
        atr
    )

    tgt = target(
        entry,
        atr
    )

    if current_price <= sl:
        return "STOPLOSS"

    if current_price >= tgt:
        return "TARGET"

    return None
