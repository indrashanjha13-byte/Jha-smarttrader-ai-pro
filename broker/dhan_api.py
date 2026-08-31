import logging
import json
import os

SETTINGS_FILE = "settings.json"


class DhanBroker:

    def __init__(self):
        self.connected = False
        self.dhan = None
        self.client_id = ""
        self.access_token = ""
        self._load_credentials()

    def _load_credentials(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r") as f:
                    settings = json.load(f)
                    if settings.get("broker") == "Dhan":
                        self.client_id = settings.get("client_id", "")
                        self.access_token = settings.get("api_key", "")
            except Exception as e:
                logging.error(f"Error loading Dhan credentials: {e}")

    def connect(self):
        if not self.client_id or not self.access_token:
            logging.warning("⚠️ Dhan Credentials missing in settings.json. Operating in Mock mode.")
            self.connected = False
            return False

        try:
            from dhanhq import dhanhq
            self.dhan = dhanhq(self.client_id, self.access_token)
            self.connected = True
            logging.info("✅ Connected to Dhan HQ API successfully.")
            return True
        except ImportError:
            logging.error("❌ 'dhanhq' package not installed. Run: pip install dhanhq")
            self.connected = False
            return False
        except Exception as e:
            logging.error(f"❌ Failed to connect to Dhan: {e}")
            self.connected = False
            return False

    def get_balance(self):
        if self.connected and self.dhan:
            try:
                fund_limits = self.dhan.get_fund_limits()
                if fund_limits.get("status") == "success":
                    return float(fund_limits.get("data", {}).get("availabelBalance", 0.0))
            except Exception as e:
                logging.error(f"Error fetching Dhan balance: {e}")
        return 100000.0  # Fallback balance

    def get_positions(self):
        if self.connected and self.dhan:
            try:
                res = self.dhan.get_positions()
                if res.get("status") == "success":
                    positions = []
                    for pos in res.get("data", []):
                        positions.append({
                            "symbol": pos.get("tradingSymbol"),
                            "qty": pos.get("netQty"),
                            "entry": pos.get("buyAvg"),
                            "pnl": pos.get("realizedProfit", 0) + pos.get("unrealizedProfit", 0)
                        })
                    return positions
            except Exception as e:
                logging.error(f"Error fetching Dhan positions: {e}")
        return []

    def get_holdings(self):
        if self.connected and self.dhan:
            try:
                res = self.dhan.get_holdings()
                if res.get("status") == "success":
                    return res.get("data", [])
            except Exception as e:
                logging.error(f"Error fetching Dhan holdings: {e}")
        return []

    def buy(self, symbol, qty, price=0.0, **kwargs):
        qty = int(qty)
        if self.connected and self.dhan:
            try:
                order_res = self.dhan.place_order(
                    security_id=symbol,
                    exchange_segment=self.dhan.NSE,
                    transaction_type=self.dhan.BUY,
                    quantity=qty,
                    order_type=self.dhan.MARKET if price == 0 else self.dhan.LIMIT,
                    product_type=self.dhan.INTRA,
                    price=price
                )
                logging.info(f"DHAN BUY ORDER -> {symbol} Qty={qty} Response={order_res}")
                return {"status": "success", "response": order_res}
            except Exception as e:
                logging.error(f"DHAN BUY FAILED -> {e}")
                return {"status": "error", "message": str(e)}

        logging.info(f"MOCK DHAN BUY -> {symbol} Qty={qty}")
        return {"status": "success", "mock": True}

    def sell(self, symbol, qty, price=0.0, **kwargs):
        qty = int(qty)
        if self.connected and self.dhan:
            try:
                order_res = self.dhan.place_order(
                    security_id=symbol,
                    exchange_segment=self.dhan.NSE,
                    transaction_type=self.dhan.SELL,
                    quantity=qty,
                    order_type=self.dhan.MARKET if price == 0 else self.dhan.LIMIT,
                    product_type=self.dhan.INTRA,
                    price=price
                )
                logging.info(f"DHAN SELL ORDER -> {symbol} Qty={qty} Response={order_res}")
                return {"status": "success", "response": order_res}
            except Exception as e:
                logging.error(f"DHAN SELL FAILED -> {e}")
                return {"status": "error", "message": str(e)}

        logging.info(f"MOCK DHAN SELL -> {symbol} Qty={qty}")
        return {"status": "success", "mock": True}

    def order_book(self):
        if self.connected and self.dhan:
            try:
                res = self.dhan.get_order_list()
                if res.get("status") == "success":
                    return res.get("data", [])
            except Exception as e:
                logging.error(f"Error fetching Dhan order book: {e}")
        return []