import csv
import os
from datetime import datetime


class PaperTrader:

    def __init__(self):
        self.balance = 100000
        self.position = None

    def buy(self, symbol, price, qty):

        cost = price * qty

        print("Balance =", self.balance)
        print("Cost =", cost)
        print("Qty =", qty)
        print("Price =", price)

        if cost > self.balance:
            print("❌ Insufficient Balance")
            return False

        self.balance -= cost

        # Position Save
        self.position = {
            "symbol": symbol,
            "entry": price,
            "qty": qty,
            "entry_time": datetime.now(),
            "stoploss": price - 20,
            "target": price + 40
        }

        print("BUY SAVED :", self.position)

        self.save_trade(
            "BUY",
            symbol,
            price,
            qty,
            0
        )

        print("Balance =", self.balance)

        return True

    
    def sell(self, price):

        if self.position is None:
            return False

        entry = self.position["entry"]
        qty = self.position["qty"]

        pnl = round((price - entry) * qty, 2)

        self.balance += price * qty

        self.save_trade(
            "SELL",
            self.position["symbol"],
            price,
            qty,
            pnl
        )

        print("=" * 50)
        print("SELL EXECUTED")
        print("Entry :", entry)
        print("Exit  :", price)
        print("Qty   :", qty)
        print("PNL   :", pnl)
        print("Balance :", self.balance)
        print("=" * 50)

        self.position = None

        return True

    def save_trade(self, side, symbol, price, qty, pnl=0):

        file_exists = os.path.exists("trade_history.csv")

        with open(
            "trade_history.csv",
            "a",
            newline="",
            encoding="utf-8"
        ) as f:

            writer = csv.writer(f)

            if (not file_exists) or os.path.getsize("trade_history.csv") == 0:

                writer.writerow([
                    "Date",
                    "Action",
                    "Symbol",
                    "Price",
                    "Qty",
                    "PNL"
                ])

            writer.writerow([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
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
