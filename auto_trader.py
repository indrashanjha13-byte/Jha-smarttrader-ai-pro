from live_trading import execute_buy, execute_sell
from trade_exit import exit_manager

last_signal = None

entry_price = 0
target_price = 0
stoploss_price = 0


def place_trade(signal, symbol, qty, current_price):

    global last_signal
    global entry_price
    global target_price
    global stoploss_price

    # ==========================
    # Trade Already Open
    # ==========================
    if exit_manager.trade_open and signal == "BUY":
        print("⚠ Trade Already Open")
        return

    # ==========================
    # Same Signal
    # ==========================
    if signal == last_signal:
        print(f"⏸ Same Signal ({signal}) -> Skip")
        return

    # ==========================
    # BUY
    # ==========================
    if signal == "BUY":

        entry_price = current_price
        target_price = round(current_price * 1.02, 2)
        stoploss_price = round(current_price * 0.99, 2)

        execute_buy(
            symbol,
            qty,
            entry_price,
            target_price,
            stoploss_price
        )

        exit_manager.open_trade(
            symbol,
            qty,
            entry_price,
            target_price,
            stoploss_price
        )


        last_signal = "BUY"

        print(f"✅ BUY : {symbol}")

    # ==========================
    # SELL
    # ==========================
    elif signal == "SELL":

        if not exit_manager.trade_open:
            print("⚠ No Open Trade")
            return

        pnl = round(
            (current_price - entry_price) * qty,
            2
        )

        execute_sell(
            symbol,
            qty,
            entry_price,
            current_price,
            target_price,
            stoploss_price,
            pnl
        )

        last_signal = "SELL"

        print(f"🔴 SELL : {symbol}")

    else:

        print("🟡 HOLD")