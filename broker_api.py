import csv
import os
import logging
from datetime import datetime

# Absolute path resolution for safe execution
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_FILE_PATH = os.path.join(BASE_DIR, "trade_history.csv")


class BrokerAPI:

    def __init__(self, file_path=CSV_FILE_PATH):
        self.file_path = file_path
        self._init_csv()

    def _init_csv(self):
        """Initializes trade history CSV with headers if it does not exist."""
        if not os.path.exists(self.file_path):
            try:
                with open(self.file_path, "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        "Time", "Action", "Symbol", "Entry",
                        "Exit", "Quantity", "Target", "StopLoss",
                        "PnL", "Status", "Mode"
                    ])
            except Exception as e:
                logging.error(f"❌ Failed to initialize trade history CSV: {e}")

    def save_trade(
        self,
        action,
        symbol,
        qty,
        entry=0.0,
        exit_price=0.0,
        target=0.0,
        stoploss=0.0,
        pnl=0.0,
        status="OPEN",
        mode="Paper"
    ) -> bool:
        """Saves trade log into CSV safely."""
        try:
            with open(self.file_path, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    action,
                    symbol,
                    round(float(entry), 2),
                    round(float(exit_price), 2),
                    qty,
                    round(float(target), 2),
                    round(float(stoploss), 2),
                    round(float(pnl), 2),
                    status,
                    mode
                ])
            return True
        except PermissionError:
            logging.error(f"❌ Cannot save trade. {self.file_path} is open in another program.")
            return False
        except Exception as e:
            logging.error(f"❌ Error saving trade to CSV: {e}")
            return False

    def place_buy_order(self, symbol, qty, entry, target, stoploss) -> bool:
        """Executes simulated paper BUY order."""
        try:
            logging.info("=" * 50)
            logging.info(f"🟢 BUY ORDER EXECUTED | Symbol: {symbol} | Qty: {qty} | Entry: ₹{entry}")
            logging.info("=" * 50)

            saved = self.save_trade(
                action="BUY",
                symbol=symbol,
                qty=qty,
                entry=entry,
                target=target,
                stoploss=stoploss,
                pnl=0.0,
                status="OPEN",
                mode="Paper"
            )
            return saved
        except Exception as e:
            logging.error(f"❌ BUY Order Execution Error: {e}")
            return False

    def place_sell_order(self, symbol, qty, entry, exit_price, target, stoploss, pnl) -> bool:
        """Executes simulated paper SELL order."""
        try:
            logging.info("=" * 50)
            logging.info(f"🔴 SELL ORDER EXECUTED | Symbol: {symbol} | Qty: {qty} | PnL: ₹{pnl}")
            logging.info("=" * 50)

            saved = self.save_trade(
                action="SELL",
                symbol=symbol,
                qty=qty,
                entry=entry,
                exit_price=exit_price,
                target=target,
                stoploss=stoploss,
                pnl=pnl,
                status="CLOSED",
                mode="Paper"
            )
            return saved
        except Exception as e:
            logging.error(f"❌ SELL Order Execution Error: {e}")
            return False