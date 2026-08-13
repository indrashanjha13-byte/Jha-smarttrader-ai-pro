class KotakBroker:

    def __init__(self):
        self.connected = False

    def connect(self):
        print("Kotak API credentials required.")
        return False

    def get_balance(self):
        return 0

    def get_positions(self):
        return []

    def get_holdings(self):
        return []

    def order_book(self):
        return []

    def buy(self, symbol, qty):
        print("Kotak Broker not connected.")
        return False

    def sell(self, symbol, qty):
        print("Kotak Broker not connected.")
        return False