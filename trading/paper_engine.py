from datetime import datetime
import pandas as pd
import os

from ai_learning import update_learning


class PaperTrading:

    def __init__(self):
        self.balance = 100000
        self.position = None
        self.trade_history = []

    # ==========================
    # BUY
    # ==========================
    def buy(
        self,
        symbol,
        price,
        qty,
        target=None,
        stoploss=None,
        strategy="AI Combo"
    ):

        if target is None:
            target = price + 40

        if stoploss is None:
            stoploss = price - 20

        cost = price * qty

        if cost > self.balance:
            return False, "Insufficient Balance"

        self.balance -= cost

        self.position = {
            "symbol": symbol,
            "entry": price,
            "qty": qty,
            "target": target,
            "stoploss": stoploss,
            "strategy": strategy,
            "time": datetime.now()
        }

        trade = {
            "Date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Action": "BUY",
            "Symbol": symbol,
            "Entry": price,
            "Exit": "",
            "Qty": qty,
            "Target": target,
            "Stoploss": stoploss,
            "PNL": 0
        }

        self._save_trade(trade)

        return True, "BUY Executed"

    # ==========================
    # SELL
    # ==========================
    def sell(self, price):

        if self.position is None:
            return False, "No Position"

        pnl = round(
            (price - self.position["entry"])
            * self.position["qty"],
            2
        )

        self.balance += price * self.position["qty"]

        # ==========================
        # AI LEARNING
        # ==========================
        if pnl > 0:
            result = "WIN"
        else:
            result = "LOSS"

        strategy = self.position.get(
            "strategy",
            "AI Combo"
        )

        market = self.position["symbol"]

        update_learning(
            strategy,
            market,
            result
        )

        trade = {
            "Date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Action": "SELL",
            "Symbol": market,
            "Entry": self.position["entry"],
            "Exit": price,
            "Qty": self.position["qty"],
            "Target": self.position["target"],
            "Stoploss": self.position["stoploss"],
            "PNL": pnl
        }

        self._save_trade(trade)

        self.position = None

        return True, pnl

    # ==========================
    # AUTO EXIT
    # ==========================
    def auto_exit(self, current_price):

        if self.position is None:
            return None

        if current_price >= self.position["target"]:
            self.sell(current_price)
            return "TARGET HIT"

        if current_price <= self.position["stoploss"]:
            self.sell(current_price)
            return "STOPLOSS HIT"

        return None

    # ==========================
    # SAVE TRADE
    # ==========================
    def _save_trade(self, trade):

        file = "trade_history.csv"

        if os.path.exists(file):
            df = pd.read_csv(file)
        else:
            df = pd.DataFrame(columns=[
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

        df = pd.concat(
            [df, pd.DataFrame([trade])],
            ignore_index=True
        )

        df.to_csv(file, index=False)

        self.trade_history.append(trade)