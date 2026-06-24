import csv
from datetime import datetime

class PaperTrader:

    def __init__(self):
        self.balance = 100000
        self.position = None

    def buy(self, symbol, price, qty):

        cost = price * qty

        if cost > self.balance:
            print("Insufficient Balance")
            return

        self.balance -= cost

        self.position = {
            "symbol": symbol,
            "entry": price,
            "qty": qty
        }

        self.save_trade("BUY", symbol, price, qty, 0)

        print(f"BUY {symbol} @ {price}")

    def sell(self, price):
        print("SELL PRICE RECEIVED =", price)

        if not self.position:
            return

        pnl = (
            (price - self.position["entry"])
            * self.position["qty"]
        )

        self.balance += (
            price * self.position["qty"]
        )

        self.save_trade(
            "SELL",
            self.position["symbol"],
            price,
            self.position["qty"],
            pnl
        )

        print(f"PNL = {pnl}")

        self.position = None

    def save_trade(self, side, symbol, price, qty, pnl=0):

        with open(
            "trade_history.csv",
            "a",
            newline=""
        ) as f:

            writer = csv.writer(f)

            writer.writerow([
                datetime.now(),
                side,
                symbol,
                price,
                qty,
                pnl
            ])
def check_exit(entry, current):

    if current <= entry - 20:
        return "STOPLOSS"

    if current >= entry + 40:
        return "TARGET"

    return None
