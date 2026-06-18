from live_trading import (
    execute_buy,
    execute_sell
)

def place_trade(
    signal,
    symbol,
    qty
):

    if signal == "BUY":

        execute_buy(
            symbol,
            qty
        )

    elif signal == "SELL":

        execute_sell(
            symbol,
            qty
        )
