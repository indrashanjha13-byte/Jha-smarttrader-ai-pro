# live_trading.py

from config import MODE, BROKER
from broker.broker_manager import BrokerManager


# ==============================
# Broker Manager
# ==============================

broker_manager = BrokerManager(BROKER)


# ==============================
# BUY
# ==============================

def execute_buy(
    symbol,
    qty,
    entry,
    target,
    stoploss
):

    try:

        print("=" * 60)
        print("🟢 BUY REQUEST")
        print(f"Broker      : {BROKER}")
        print(f"Mode        : {MODE}")
        print(f"Symbol      : {symbol}")
        print(f"Quantity    : {qty}")
        print(f"Entry       : ₹{entry}")
        print(f"Target      : ₹{target}")
        print(f"Stop Loss   : ₹{stoploss}")
        print("=" * 60)

        # ------------------------------
        # PAPER MODE
        # ------------------------------

        if MODE.upper() == "PAPER":

            print("🟡 PAPER MODE")
            print("✅ BUY simulated successfully")

            return True

        # ------------------------------
        # LIVE MODE
        # ------------------------------

        if MODE.upper() == "LIVE":

            connected = broker_manager.connect()

            if not connected:
                print("❌ Broker connection failed")
                return False

            result = broker_manager.buy(
                symbol,
                qty
            )

            print("Broker BUY response:", result)

            return result

        print(f"❌ Unknown MODE: {MODE}")

        return False

    except Exception as e:

        print(f"❌ BUY ERROR: {e}")

        return False


# ==============================
# SELL
# ==============================

def execute_sell(
    symbol,
    qty,
    entry,
    exit_price,
    target,
    stoploss
):

    try:

        pnl = round(
            (exit_price - entry) * qty,
            2
        )

        print("=" * 60)
        print("🔴 SELL REQUEST")
        print(f"Broker      : {BROKER}")
        print(f"Mode        : {MODE}")
        print(f"Symbol      : {symbol}")
        print(f"Quantity    : {qty}")
        print(f"Entry       : ₹{entry}")
        print(f"Exit        : ₹{exit_price}")
        print(f"Target      : ₹{target}")
        print(f"Stop Loss   : ₹{stoploss}")
        print(f"P&L         : ₹{pnl}")
        print("=" * 60)

        # ------------------------------
        # PAPER MODE
        # ------------------------------

        if MODE.upper() == "PAPER":

            print("🟡 PAPER MODE")
            print("✅ SELL simulated successfully")
            print(f"📊 Paper P&L: ₹{pnl}")

            return True

        # ------------------------------
        # LIVE MODE
        # ------------------------------

        if MODE.upper() == "LIVE":

            connected = broker_manager.connect()

            if not connected:
                print("❌ Broker connection failed")
                return False

            result = broker_manager.sell(
                symbol,
                qty
            )

            print("Broker SELL response:", result)

            return result

        print(f"❌ Unknown MODE: {MODE}")

        return False

    except Exception as e:

        print(f"❌ SELL ERROR: {e}")

        return False