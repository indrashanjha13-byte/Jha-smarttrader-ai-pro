class DemoBroker:

    def __init__(self):
        self.connected = False
        self.balance = 100000
        self.positions = []
        self.holdings = []
        self.orders = []

    def connect(self):
        self.connected = True
        return True

    def get_balance(self):
        return self.balance

    def get_positions(self):
        return self.positions

    def get_holdings(self):
        return self.holdings

    def order_book(self):
        return self.orders

    def buy(self, symbol, qty):

        self.orders.append({
            "Action": "BUY",
            "Symbol": symbol,
            "Qty": qty
        })

        print(f"DEMO BUY -> {symbol} Qty={qty}")
        return True

    def sell(self, symbol, qty):

        self.orders.append({
            "Action": "SELL",
            "Symbol": symbol,
            "Qty": qty
        })

        print(f"DEMO SELL -> {symbol} Qty={qty}")
        return True