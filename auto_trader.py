from live_trading import (
    execute_buy,
    execute_sell
)

last_signal = None


def place_trade(signal, symbol, qty):
    global last_signal

    if signal == last_signal:
        print(f"No new trade. Signal already {signal}")
        return

    if signal == "BUY":
        execute_buy(symbol, qty)
        print(f"BUY Executed: {symbol} Qty={qty}")
        last_signal = "BUY"

    elif signal == "SELL":
        execute_sell(symbol, qty)
        print(f"SELL Executed: {symbol} Qty={qty}")
        last_signal = "SELL"

    else:
        print("No Trade")
