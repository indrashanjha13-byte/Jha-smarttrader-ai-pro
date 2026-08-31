from datetime import datetime
import pandas as pd
import logging
import os

try:
    from ai_learning import update_learning
except ImportError:
    def update_learning(strategy, market, result):
        pass

HISTORY_FILE = "trade_history.csv"


class PaperTrading:

    def __init__(self, initial_balance=100000.0):
        self.balance = float(initial_balance)
        self.positions = {}  # Symbol-wise multiple positions support
        self.trade_history = []
        self._load_trade_history()

    def _load_trade_history(self):
        if os.path.exists(HISTORY_FILE):
            try:
                df = pd.read_csv(HISTORY_FILE)
                self.trade_history = df.to_dict("records")
            except Exception as e:
                logging.error(f"Failed to load paper trade history: {e}")

    # ==========================
    # BUY ORDER
    # ==========================
    def buy(self, symbol, price, qty, target=None, stoploss=None, strategy="AI Combo", **kwargs):
        symbol = str(symbol).upper()
        price = float(price)
        qty = int(qty)

        if qty <= 0 or price <= 0:
            return False, "Invalid Quantity or Price"

        # Percentage-based fallback target & stoploss if not provided
        if target is None or target == 0:
            target = round(price * 1.015, 2)  # 1.5% Target default
        if stoploss is None or stoploss == 0:
            stoploss = round(price * 0.992, 2)  # 0.8% Stoploss default

        cost = price * qty

        if cost > self.balance:
            return False, f"Insufficient Balance. Required: ₹{cost:.2f}, Avail: ₹{self.balance:.2f}"

        self.balance -= cost

        # Store position by Symbol
        self.positions[symbol] = {
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
            "PNL": 0.0
        }

        self._save_trade(trade)
        logging.info(f"🟢 PAPER BUY -> {symbol} | Price: ₹{price} | Qty: {qty}")

        return True, f"BUY Executed for {symbol}"

    # ==========================
    # SELL ORDER
    # ==========================
    def sell(self, symbol, price):
        symbol = str(symbol).upper()

        if symbol not in self.positions:
            return False, f"No Open Position for {symbol}"

        pos = self.positions[symbol]
        price = float(price)
        pnl = round((price - pos["entry"]) * pos["qty"], 2)

        self.balance += price * pos["qty"]

        # AI Learning Trigger
        result = "WIN" if pnl > 0 else "LOSS"
        strategy = pos.get("strategy", "AI Combo")

        try:
            update_learning(strategy, symbol, result)
        except Exception as e:
            logging.error(f"AI Learning Update error: {e}")

        trade = {
            "Date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Action": "SELL",
            "Symbol": symbol,
            "Entry": pos["entry"],
            "Exit": price,
            "Qty": pos["qty"],
            "Target": pos["target"],
            "Stoploss": pos["stoploss"],
            "PNL": pnl
        }

        self._save_trade(trade)
        del self.positions[symbol]

        logging.info(f"🔴 PAPER SELL -> {symbol} | Exit: ₹{price} | PNL: ₹{pnl}")
        return True, pnl

    # ==========================
    # AUTO EXIT CHECK
    # ==========================
    def auto_exit(self, symbol, current_price):
        symbol = str(symbol).upper()
        if symbol not in self.positions:
            return None

        pos = self.positions[symbol]
        if current_price >= pos["target"]:
            self.sell(symbol, current_price)
            return "TARGET HIT"

        if current_price <= pos["stoploss"]:
            self.sell(symbol, current_price)
            return "STOPLOSS HIT"

        return None

    # ==========================
    # SAVE TRADE HISTORY
    # ==========================
    def _save_trade(self, trade):
        self.trade_history.append(trade)
        try:
            df = pd.DataFrame(self.trade_history)
            df.to_csv(HISTORY_FILE, index=False)
        except Exception as e:
            logging.error(f"Error saving trade history CSV: {e}")