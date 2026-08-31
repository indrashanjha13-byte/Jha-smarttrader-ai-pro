import logging
import json
import os

SETTINGS_FILE = "settings.json"


class UpstoxBroker:

    def __init__(self):
        self.connected = False
        self.api_instance = None
        self.access_token = ""
        self._load_credentials()

    def _load_credentials(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r") as f:
                    settings = json.load(f)
                    if settings.get("broker") == "Upstox":
                        self.access_token = settings.get("api_key", "")
            except Exception as e:
                logging.error(f"Error loading Upstox credentials: {e}")

    def connect(self):
        if not self.access_token:
            logging.warning("⚠️ Upstox Access Token missing in settings.json. Operating in Mock mode.")
            self.connected = False
            return False

        try:
            import upstox_client
            configuration = upstox_client.Configuration()
            configuration.access_token = self.access_token
            self.api_instance = upstox_client.OrderApi(upstox_client.ApiClient(configuration))
            self.user_api = upstox_client.UserApi(upstox_client.ApiClient(configuration))
            self.connected = True
            logging.info("✅ Connected to Upstox API successfully.")
            return True
        except ImportError:
            logging.error("❌ 'upstox-python-sdk' package not installed. Run: pip install upstox-python-sdk")
            self.connected = False
            return False
        except Exception as e:
            logging.error(f"❌ Failed to connect to Upstox: {e}")
            self.connected = False
            return False

    def get_balance(self):
        if self.connected and hasattr(self, "user_api"):
            try:
                res = self.user_api.get_user_fund_and_margin()
                if res and res.data and res.data.equity:
                    return float(res.data.equity.available_margin)
            except Exception as e:
                logging.error(f"Error fetching Upstox balance: {e}")
        return 100000.0

    def get_positions(self):
        if self.connected and hasattr(self, "portfolio_api"):
            try:
                import upstox_client
                portfolio_api = upstox_client.PortfolioApi(upstox_client.ApiClient())
                res = portfolio_api.get_positions()
                if res and res.data:
                    return [
                        {
                            "symbol": pos.trading_symbol,
                            "qty": pos.quantity,
                            "entry": pos.average_price,
                            "pnl": pos.pnl
                        }
                        for pos in res.data
                    ]
            except Exception as e:
                logging.error(f"Error fetching Upstox positions: {e}")
        return []

    def get_holdings(self):
        if self.connected:
            try:
                import upstox_client
                portfolio_api = upstox_client.PortfolioApi(upstox_client.ApiClient())
                res = portfolio_api.get_holdings()
                if res and res.data:
                    return res.data
            except Exception as e:
                logging.error(f"Error fetching Upstox holdings: {e}")
        return []

    def buy(self, symbol, qty, price=0.0, **kwargs):
        qty = int(qty)
        if self.connected and self.api_instance:
            try:
                import upstox_client
                body = upstox_client.PlaceOrderRequest(
                    quantity=qty,
                    product="I",
                    validity="DAY",
                    price=float(price),
                    tag="SmartTrader",
                    instrument_token=symbol,
                    order_type="MARKET" if price == 0 else "LIMIT",
                    transaction_type="BUY",
                    disclosed_quantity=0,
                    trigger_price=0.0,
                    is_amo=False
                )
                res = self.api_instance.place_order(body)
                logging.info(f"UPSTOX BUY ORDER -> {symbol} Qty={qty} Response={res}")
                return {"status": "success", "response": res}
            except Exception as e:
                logging.error(f"UPSTOX BUY FAILED -> {e}")
                return {"status": "error", "message": str(e)}

        logging.info(f"MOCK UPSTOX BUY -> {symbol} Qty={qty}")
        return {"status": "success", "mock": True}

    def sell(self, symbol, qty, price=0.0, **kwargs):
        qty = int(qty)
        if self.connected and self.api_instance:
            try:
                import upstox_client
                body = upstox_client.PlaceOrderRequest(
                    quantity=qty,
                    product="I",
                    validity="DAY",
                    price=float(price),
                    tag="SmartTrader",
                    instrument_token=symbol,
                    order_type="MARKET" if price == 0 else "LIMIT",
                    transaction_type="SELL",
                    disclosed_quantity=0,
                    trigger_price=0.0,
                    is_amo=False
                )
                res = self.api_instance.place_order(body)
                logging.info(f"UPSTOX SELL ORDER -> {symbol} Qty={qty} Response={res}")
                return {"status": "success", "response": res}
            except Exception as e:
                logging.error(f"UPSTOX SELL FAILED -> {e}")
                return {"status": "error", "message": str(e)}

        logging.info(f"MOCK UPSTOX SELL -> {symbol} Qty={qty}")
        return {"status": "success", "mock": True}

    def order_book(self):
        if self.connected and self.api_instance:
            try:
                res = self.api_instance.get_order_book()
                if res and res.data:
                    return res.data
            except Exception as e:
                logging.error(f"Error fetching Upstox order book: {e}")
        return []