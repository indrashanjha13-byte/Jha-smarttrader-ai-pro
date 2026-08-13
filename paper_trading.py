import csv
import os
from datetime import datetime

from ai_learning import update_learning


class PaperTrader:

    def __init__(self):
        self.balance = 100000
        self.position = None

    # ==========================================
    # BUY
    # ==========================================

    def buy(self, symbol, price, qty, target, stoploss):

        cost = price * qty

        print("Balance =", self.balance)
        print("Cost =", cost)
        print("Qty =", qty)
        print("Price =", price)

        if cost > self.balance:
            return False, "❌ Insufficient Balance"

        self.balance -= cost

        # Position Save
        self.position = {
            "symbol": symbol,
            "entry": price,
            "qty": qty,
            "target": target,
            "stoploss": stoploss,
            "entry_time": datetime.now()
        }

        self.save_trade(
            action="BUY",
            symbol=symbol,
            entry=price,
            exit_price="",
            qty=qty,
            target=target,
            stoploss=stoploss,
            pnl=0
        )

        return True, "✅ BUY Order Executed"

    # ==========================================
    # SELL
    # ==========================================

    def sell(self, current_price):

        if self.position is None:
            return False, "❌ No Active Position"

        symbol = self.position["symbol"]
        entry = self.position["entry"]
        qty = self.position["qty"]
        target = self.position["target"]
        stoploss = self.position["stoploss"]

        pnl = round((current_price - entry) * qty, 2)

        self.balance += current_price * qty

        self.save_trade(
            action="SELL",
            symbol=symbol,
            entry=entry,
            exit_price=current_price,
            qty=qty,
            target=target,
            stoploss=stoploss,
            pnl=pnl
        )

        self.position = None

        return True, pnl

    # ==========================================
    # AUTO EXIT
    # ==========================================

    def auto_exit(self, current_price):

        if self.position is None:
            return None

        if current_price >= self.position["target"]:

            symbol = self.position["symbol"]

            self.sell(current_price)

            update_learning(
                "AI Combo",
                symbol,
                "WIN"
            )

            return "🎯 Target Hit"

        if current_price <= self.position["stoploss"]:

            symbol = self.position["symbol"]

            self.sell(current_price)

            update_learning(
                "AI Combo",
                symbol,
                "LOSS"
            )

            return "🛑 Stoploss Hit"
        
        return None

    # ==========================================
    # SAVE TRADE
    # ==========================================

    def save_trade(
        self,
        action,
        symbol,
        entry,
        exit_price,
        qty,
        target,
        stoploss,
        pnl
    ):

        file_exists = os.path.exists("trade_history.csv")

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
                    "Entry",
                    "Exit",
                    "Qty",
                    "Target",
                    "Stoploss",
                    "PNL"
                ])

            writer.writerow([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                action,
                symbol,
                entry,
                exit_price,
                qty,
                target,
                stoploss,
                pnl
            ])


# ==========================================
# CHECK EXIT
# ==========================================

def check_exit(entry, current):

    if current <= entry - 20:
        return "STOPLOSS"

    if current >= entry + 40:
        return "TARGET"

    return None