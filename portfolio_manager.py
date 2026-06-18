MAX_OPEN_TRADES = 5

def can_trade(
    open_positions
):

    return (
        open_positions
        < MAX_OPEN_TRADES
    )
