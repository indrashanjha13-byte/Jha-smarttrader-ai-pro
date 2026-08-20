from live_trading import execute_buy, execute_sell
from trade_exit import exit_manager

last_signal = None


def place_trade(signal, symbol, qty, current_price):

    global last_signal

    # ==========================
    # BUY
    # ==========================
    if signal == "BUY":

        if exit_manager.trade_open:
            print("⚠ Trade Already Open")
            return False

        if last_signal == "BUY":
            print("⏸ Same Signal (BUY) -> Skip")
            return False

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
            symbol=symbol,
            qty=qty,
            entry=entry_price,
            target=target_price,
            stoploss=stoploss_price
        )

        last_signal = "BUY"

        print(f"✅ BUY : {symbol} Qty={qty}")

        return True

    # ==========================
    # SELL
    # ==========================
    elif signal == "SELL":

        if not exit_manager.trade_open:
            print("⚠ No Open Trade")
            return False

        entry_price = exit_manager.entry
        target_price = exit_manager.target
        stoploss_price = exit_manager.stoploss
        trade_qty = exit_manager.qty

        execute_sell(
            symbol,
            trade_qty,
            entry_price,
            current_price,
            target_price,
            stoploss_price
        )

        # Close local trade state
        exit_manager.trade_open = False
        exit_manager.symbol = None
        exit_manager.qty = 0
        exit_manager.entry = 0
        exit_manager.target = 0
        exit_manager.stoploss = 0
        exit_manager.strategy = "AI Combo"

        last_signal = "SELL"

        print(
            f"🔴 SELL : {symbol} Qty={trade_qty}"
        )

        return True

    # ==========================
    # HOLD
    # ==========================
    else:

        print("🟡 HOLD")
        return False