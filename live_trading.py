# live_trading.py

from broker_api import BrokerAPI

broker = BrokerAPI()


def execute_buy(
    symbol,
    qty,
    entry,
    target,
    stoploss
):
    try:

        print(f"🟢 Placing BUY Order: {symbol}")

        broker.place_buy_order(
            symbol=symbol,
            qty=qty,
            entry=entry,
            target=target,
            stoploss=stoploss
        )

        print("✅ BUY Order Executed Successfully")

    except Exception as e:

        print(f"❌ BUY Failed: {e}")


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

        print(f"🔴 Placing SELL Order: {symbol}")

        broker.place_sell_order(
            symbol=symbol,
            qty=qty,
            entry=entry,
            exit_price=exit_price,
            target=target,
            stoploss=stoploss,
            pnl=pnl
        )

        print("✅ SELL Order Executed Successfully")

    except Exception as e:

        print(f"❌ SELL Failed: {e}")