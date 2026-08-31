import csv
import os
import logging
from datetime import datetime

try:
    from ai_learning import update_learning
except ImportError:
    # Fallback if ai_learning module is missing or structured differently
    def update_learning(strategy, symbol, result):
        pass


class PaperTrader:
    """
    Simulates real-world paper trading, ledger management, and trade history persistence.
    """

    def __init__(self, initial_balance=100000.0):
        self.balance = float(initial_balance)
        self.position = None

    # ==========================================
    # BUY
    # ==========================================

    def buy(self, symbol, price, qty, target, stoploss):
        """Executes a simulated Buy order."""
        try:
            price = float(price)
            qty = int(qty)
            target = float(target)
            stoploss = float(stoploss)
            
            cost = price * qty

            logging.info(f"Balance: ₹{self.balance} | Cost: ₹{cost} | Qty: {qty} | Price: ₹{price}")

            if cost > self.balance:
                return False, "❌ Insufficient Paper Trading Balance"

            # Deduct total capital spent on trade
            self.balance -= cost

            # Save Active Position
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
                pnl=0.0
            )

            return True, "✅ BUY Order Executed Successfully"

        except Exception as e:
            logging.error(f"❌ Paper Buy Error: {e}")
            return False, f"Error: {e}"

    # ==========================================
    # SELL
    # ==========================================

    def sell(self, current_price):
        """Executes a simulated Sell order, clears position, and updates ledger balance."""
        if self.position is None:
            return False, "❌ No Active Position Found"

        try:
            current_price = float(current_price)
            symbol = self.position["symbol"]
            entry = self.position["entry"]
            qty = self.position["qty"]
            target = self.position["target"]
            stoploss = self.position["stoploss"]

            # Calculate Profit and Loss
            pnl = round((current_price - entry) * qty, 2)

            # CORRECT LEDGER UPDATE: Return original invested margin + PnL
            invested_capital = entry * qty
            self.balance += invested_capital + pnl

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

        except Exception as e:
            logging.error(f"❌ Paper Sell Error: {e}")
            return False, str(e)

    # ==========================================
    # AUTO EXIT
    # ==========================================

    def auto_exit(self, current_price):
        """Monitors active position against Target and Stoploss bounds."""
        if self.position is None:
            return None

        try:
            current_price = float(current_price)
            symbol = self.position["symbol"]

            if current_price >= self.position["target"]:
                self.sell(current_price)
                update_learning("AI Combo", symbol, "WIN")
                return "🎯 Target Hit"

            if current_price <= self.position["stoploss"]:
                self.sell(current_price)
                update_learning("AI Combo", symbol, "LOSS")
                return "🛑 Stoploss Hit"

        except Exception as e:
            logging.error(f"❌ Auto Exit Error: {e}")

        return None

    # ==========================================
    # SAVE TRADE
    # ==========================================

    def save_trade(self, action, symbol, entry, exit_price, qty, target, stoploss, pnl):
        """Persists completed or opened trade logs safely to trade_history.csv."""
        try:
            file_path = "trade_history.csv"
            file_exists = os.path.exists(file_path)
            is_empty = not file_exists or os.path.getsize(file_path) == 0

            with open(file_path, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)

                if is_empty:
                    writer.writerow([
                        "Date", "Action", "Symbol", "Entry", "Exit", 
                        "Qty", "Target", "Stoploss", "PNL"
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
        except Exception as e:
            logging.error(f"❌ Failed to save trade history: {e}")


# ==========================================
# CHECK EXIT (Helper Utility)
# ==========================================

def check_exit(entry, current):
    """Simple boundary check for target/stoploss testing."""
    try:
        entry = float(entry)
        current = float(current)

        if current <= entry - 20:
            return "STOPLOSS"
        if current >= entry + 40:
            return "TARGET"
    except Exception:
        pass

    return None