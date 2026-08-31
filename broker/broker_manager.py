import logging
from broker.demo_api import DemoBroker

# Safe imports for external broker APIs
try:
    from broker.kotak_api import KotakBroker
except ImportError:
    KotakBroker = None

try:
    from broker.dhan_api import DhanBroker
except ImportError:
    DhanBroker = None

try:
    from broker.zerodha_api import ZerodhaBroker
except ImportError:
    ZerodhaBroker = None

try:
    from broker.upstox_api import UpstoxBroker
except ImportError:
    UpstoxBroker = None


class BrokerManager:

    def __init__(self, broker_name="DEMO"):
        # Normalize broker name string (remove spaces, underscores, etc.)
        name = str(broker_name).strip().upper().replace(" ", "").replace("_", "")

        if name in ("KOTAK", "KOTAKNEO") and KotakBroker:
            self.broker = KotakBroker()
        elif name == "DHAN" and DhanBroker:
            self.broker = DhanBroker()
        elif name == "ZERODHA" and ZerodhaBroker:
            self.broker = ZerodhaBroker()
        elif name == "UPSTOX" and UpstoxBroker:
            self.broker = UpstoxBroker()
        else:
            if broker_name and name != "DEMO":
                logging.warning(f"⚠️ Broker '{broker_name}' unavailable or class missing. Falling back to DemoBroker.")
            self.broker = DemoBroker()

    def connect(self):
        try:
            return getattr(self.broker, "connect", lambda: True)()
        except Exception as e:
            logging.error(f"Error connecting broker: {e}")
            return False

    def get_balance(self):
        try:
            return getattr(self.broker, "get_balance", lambda: 0.0)()
        except Exception as e:
            logging.error(f"Error fetching balance: {e}")
            return 0.0

    def get_positions(self):
        try:
            return getattr(self.broker, "get_positions", lambda: [])()
        except Exception as e:
            logging.error(f"Error fetching positions: {e}")
            return []

    def get_holdings(self):
        try:
            return getattr(self.broker, "get_holdings", lambda: [])()
        except Exception as e:
            logging.error(f"Error fetching holdings: {e}")
            return []

    def buy(self, symbol, qty, **kwargs):
        try:
            return self.broker.buy(symbol, qty, **kwargs)
        except Exception as e:
            logging.error(f"Error executing buy order for {symbol}: {e}")
            return {"status": "error", "message": str(e)}

    def sell(self, symbol, qty, **kwargs):
        try:
            return self.broker.sell(symbol, qty, **kwargs)
        except Exception as e:
            logging.error(f"Error executing sell order for {symbol}: {e}")
            return {"status": "error", "message": str(e)}

    def order_book(self):
        try:
            return getattr(self.broker, "order_book", lambda: [])()
        except Exception as e:
            logging.error(f"Error fetching order book: {e}")
            return []