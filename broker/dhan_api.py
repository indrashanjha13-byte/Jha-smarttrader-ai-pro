class DhanBroker:

    def connect(self):
        return True

    def get_balance(self):
        return 100000

    def get_positions(self):
        return []

    def get_holdings(self):
        return []

    def buy(self, symbol, qty):
        print(f"DHAN BUY -> {symbol} Qty={qty}")
        return True

    def sell(self, symbol, qty):
        print(f"DHAN SELL -> {symbol} Qty={qty}")
        return True

    def order_book(self):
        return []