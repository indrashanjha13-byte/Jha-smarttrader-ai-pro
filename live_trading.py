from broker_api import BrokerAPI

broker = BrokerAPI()

def execute_buy(
    symbol,
    qty
):

    broker.place_buy_order(
        symbol,
        qty
    )

def execute_sell(
    symbol,
    qty
):

    broker.place_sell_order(
        symbol,
        qty
    )
