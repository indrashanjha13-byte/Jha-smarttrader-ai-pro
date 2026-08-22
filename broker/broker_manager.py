from broker.demo_api import DemoBroker
from broker.kotak_api import KotakBroker
from broker.dhan_api import DhanBroker
from broker.zerodha_api import ZerodhaBroker
from broker.upstox_api import UpstoxBroker


class BrokerManager:

    def __init__(self, broker_name):

        name = str(broker_name).strip().upper()

        if name in ("KOTAK NEO", "KOTAK", "KOTAKNEO"):
            self.broker = KotakBroker()

        elif name == "DHAN":
            self.broker = DhanBroker()

        elif name == "ZERODHA":
            self.broker = ZerodhaBroker()

        elif name == "UPSTOX":
            self.broker = UpstoxBroker()

        else:
            print(f"⚠️ Unknown broker: {broker_name}")
            print("⚠️ Using DemoBroker")
            self.broker = DemoBroker()

    def connect(self):
        return self.broker.connect()

    def get_balance(self):
        return self.broker.get_balance()

    def get_positions(self):
        return self.broker.get_positions()

    def get_holdings(self):
        return self.broker.get_holdings()

    def buy(self, symbol, qty):
        return self.broker.buy(symbol, qty)

    def sell(self, symbol, qty):
        return self.broker.sell(symbol, qty)

    def order_book(self):
        return self.broker.order_book()