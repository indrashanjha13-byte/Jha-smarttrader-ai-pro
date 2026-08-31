import logging
import json
import os

SETTINGS_FILE = "settings.json"


class ZerodhaBroker:

    def __init__(self):
        self.connected = False
        self.kite = None
        self.api_key = ""
        self.access_token = ""
        self._load_credentials()

    def _load_credentials(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r") as f:
                    settings = json.load(f)
                    if settings.get("broker") in ("Zerodha", "Kite"):
                        self.api_key = settings.get("api_key", "")
                        self.access_token = settings.get("access_token", settings.get("api_secret", ""))
            except Exception as e:
                logging.error(f"Error loading Zerodha credentials: {e}")

    def connect(self):
        if not self.api_key or not self.access_token:
            logging.warning("⚠️ Zerodha API Key / Access Token missing in settings.json. Operating in Mock mode.")
            self.connected = False
            return False

        try:
            from kiteconnect import KiteConnect
            self.kite = KiteConnect(api_key=self.api_key)
            self.kite.set_access_token(self.access_token)
            self.connected = True
            logging.info("✅ Connected to Zerodha Kite API successfully.")
            return True
        except ImportError:
            logging.error("❌ 'kiteconnect' package not installed. Run: pip install kiteconnect")
            self.connected = False
            return False
        except Exception as e:
            logging.error(f"❌ Failed to connect to Zerodha: {e}")
            self.connected = False
            return False

    def get_balance(self):
        if self.connected and self.kite:
            try:
                margins = self.kite.margins()
                if margins and "equity" in margins:
                    return float(margins["equity"].get("available", {}).get("live_balance", 0.0))
            except Exception as e:
                logging.error(f"Error fetching Zerodha balance: {e}")
        return 100000.0  # Fallback mock balance

    def get_positions(self):
        if self.connected and self.kite:
            try:
                res = self.kite.positions()
                net_positions = res.get("net", [])
                positions = []
                for pos in net_positions:
                    positions.append({
                        "symbol": pos.get("tradingsymbol"),
                        "qty": pos.get("quantity"),
                        "entry": pos.get("average_price"),
                        "pnl": pos.get("pnl", 0.0)
                    })
                return positions
            except Exception as e:
                logging.error(f"Error fetching Zerodha positions: {e}")
        return []

    def get_holdings(self):
        if self.connected and self.kite:
            try:
                return self.kite.holdings()
            except Exception as e:
                logging.error(f"Error fetching Zerodha holdings: {e}")
        return []

    def buy(self, symbol, qty, price=0.0, product="MIS", **kwargs):
        qty = int(qty)
        if self.connected and self.kite:
            try:
                order_type = self.kite.ORDER_TYPE_MARKET if price == 0 else self.kite.ORDER_TYPE_LIMIT
                prod_type = self.kite.PRODUCT_MIS if product == "MIS" else self.kite.PRODUCT_CNC

                order_id = self.kite.place_order(
                    variety=self.kite.VARIETY_REGULAR,
                    exchange=self.kite.EXCHANGE_NSE,
                    tradingsymbol=symbol,
                    transaction_type=self.kite.TRANSACTION_TYPE_BUY,
                    quantity=qty,
                    product=prod_type,
                    order_type=order_type,
                    price=price if price > 0 else None
                )
                logging.info(f"ZERODHA BUY ORDER -> {symbol} Qty={qty} OrderID={order_id}")
                return {"status": "success", "order_id": order_id}
            except Exception as e:
                logging.error(f"ZERODHA BUY FAILED -> {e}")
                return {"status": "error", "message": str(e)}

        logging.info(f"MOCK ZERODHA BUY -> {symbol} Qty={qty}")
        return {"status": "success", "mock": True}

    def sell(self, symbol, qty, price=0.0, product="MIS", **kwargs):
        qty = int(qty)
        if self.connected and self.kite:
            try:
                order_type = self.kite.ORDER_TYPE_MARKET if price == 0 else self.kite.ORDER_TYPE_LIMIT
                prod_type = self.kite.PRODUCT_MIS if product == "MIS" else self.kite.PRODUCT_CNC

                order_id = self.kite.place_order(
                    variety=self.kite.VARIETY_REGULAR,
                    exchange=self.kite.EXCHANGE_NSE,
                    tradingsymbol=symbol,
                    transaction_type=self.kite.TRANSACTION_TYPE_SELL,
                    quantity=qty,
                    product=prod_type,
                    order_type=order_type,
                    price=price if price > 0 else None
                )
                logging.info(f"ZERODHA SELL ORDER -> {symbol} Qty={qty} OrderID={order_id}")
                return {"status": "success", "order_id": order_id}
            except Exception as e:
                logging.error(f"ZERODHA SELL FAILED -> {e}")
                return {"status": "error", "message": str(e)}

        logging.info(f"MOCK ZERODHA SELL -> {symbol} Qty={qty}")
        return {"status": "success", "mock": True}

    def order_book(self):
        if self.connected and self.kite:
            try:
                return self.kite.orders()
            except Exception as e:
                logging.error(f"Error fetching Zerodha order book: {e}")
        return []