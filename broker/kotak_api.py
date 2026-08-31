import logging
import json
import os
import pyotp
from decouple import config

try:
    from neo_api_client import NeoAPI
except ImportError:
    NeoAPI = None

SETTINGS_FILE = "settings.json"


class KotakBroker:

    def __init__(self):
        self.connected = False
        self.client = None

        # Load from .env first, fallback to settings.json
        self.consumer_key = config("KOTAK_CONSUMER_KEY", default="")
        self.mobile_number = config("KOTAK_MOBILE_NUMBER", default="")
        self.ucc = config("KOTAK_UCC", default="")
        self.totp_secret = config("KOTAK_TOTP_SECRET", default="")
        self.mpin = config("KOTAK_MPIN", default="")

        self._load_from_settings()

    def _load_from_settings(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r") as f:
                    settings = json.load(f)
                    if settings.get("broker") in ("Kotak Neo", "Kotak"):
                        self.consumer_key = settings.get("api_key", self.consumer_key)
                        self.ucc = settings.get("client_id", self.ucc)
            except Exception as e:
                logging.error(f"Error loading Kotak settings: {e}")

    def connect(self):
        if not NeoAPI:
            logging.error("❌ 'neo_api_client' not installed. Run: pip install neo-api-client")
            return False

        if self.connected and self.client:
            return True

        if not all([self.consumer_key, self.mobile_number, self.ucc, self.totp_secret, self.mpin]):
            logging.warning("⚠️ Kotak Neo credentials missing in settings/.env.")
            return False

        try:
            self.client = NeoAPI(
                consumer_key=self.consumer_key,
                environment="prod"
            )

            totp = pyotp.TOTP(self.totp_secret).now()

            self.client.totp_login(
                mobile_number=self.mobile_number,
                ucc=self.ucc,
                totp=totp
            )

            self.client.totp_validate(mpin=self.mpin)

            self.connected = True
            logging.info("✅ Kotak Neo login and MPIN validation successful.")
            return True

        except Exception as e:
            self.connected = False
            self.client = None
            logging.error(f"❌ Kotak Neo connection error: {e}")
            return False

    def resolve_symbol(self, symbol):
        if not self.connected:
            if not self.connect():
                return None

        try:
            clean_symbol = str(symbol).strip().upper()
            if clean_symbol.endswith(".NS"):
                clean_symbol = clean_symbol[:-3]
            elif clean_symbol.endswith(".NSE"):
                clean_symbol = clean_symbol[:-4]

            result = self.client.search_scrip(
                exchange_segment="nse_cm",
                symbol=clean_symbol
            )

            if not result or not isinstance(result, list):
                logging.warning(f"❌ Kotak symbol not found: {clean_symbol}")
                return None

            first = result[0]
            trading_symbol = first.get("pTrdSymbol")

            if not trading_symbol:
                return None

            return {
                "symbol": clean_symbol,
                "trading_symbol": trading_symbol,
                "token": first.get("pSymbol"),
                "exchange_segment": first.get("pExchSeg", "nse_cm"),
                "lot_size": int(first.get("lLotSize", 1))
            }

        except Exception as e:
            logging.error(f"❌ Kotak symbol resolution error: {e}")
            return None

    def get_balance(self):
        if not self.connected and not self.connect():
            return 0.0
        try:
            res = self.client.limits()
            if isinstance(res, dict):
                return float(res.get("Net", res.get("availableLimit", 0.0)))
            return 0.0
        except Exception as e:
            logging.error(f"❌ Kotak balance error: {e}")
            return 0.0

    def get_positions(self):
        if not self.connected and not self.connect():
            return []
        try:
            res = self.client.positions()
            return res.get("stat", []) if isinstance(res, dict) else res
        except Exception as e:
            logging.error(f"❌ Kotak positions error: {e}")
            return []

    def get_holdings(self):
        if not self.connected and not self.connect():
            return []
        try:
            return self.client.holdings()
        except Exception as e:
            logging.error(f"❌ Kotak holdings error: {e}")
            return []

    def order_book(self):
        if not self.connected and not self.connect():
            return []
        try:
            return self.client.order_report()
        except Exception as e:
            logging.error(f"❌ Kotak order book error: {e}")
            return []

    def buy(self, symbol, qty, price=0.0, **kwargs):
        if not self.connected and not self.connect():
            return {"status": "error", "message": "Not connected"}

        try:
            resolved = self.resolve_symbol(symbol)
            if not resolved:
                return {"status": "error", "message": "Symbol resolution failed"}

            trading_symbol = resolved["trading_symbol"]
            exchange_segment = resolved["exchange_segment"]
            quantity = int(qty)

            order_type = "MKT" if price == 0 else "L"

            result = self.client.place_order(
                exchange_segment=exchange_segment,
                product="MIS",
                price=str(price),
                order_type=order_type,
                quantity=str(quantity),
                validity="DAY",
                trading_symbol=trading_symbol,
                transaction_type="B",
                amo="NO"
            )

            success = self._order_success(result)
            return {"status": "success" if success else "error", "response": result}

        except Exception as e:
            logging.error(f"❌ Kotak BUY error: {e}")
            return {"status": "error", "message": str(e)}

    def sell(self, symbol, qty, price=0.0, **kwargs):
        if not self.connected and not self.connect():
            return {"status": "error", "message": "Not connected"}

        try:
            resolved = self.resolve_symbol(symbol)
            if not resolved:
                return {"status": "error", "message": "Symbol resolution failed"}

            trading_symbol = resolved["trading_symbol"]
            exchange_segment = resolved["exchange_segment"]
            quantity = int(qty)

            order_type = "MKT" if price == 0 else "L"

            result = self.client.place_order(
                exchange_segment=exchange_segment,
                product="MIS",
                price=str(price),
                order_type=order_type,
                quantity=str(quantity),
                validity="DAY",
                trading_symbol=trading_symbol,
                transaction_type="S",
                amo="NO"
            )

            success = self._order_success(result)
            return {"status": "success" if success else "error", "response": result}

        except Exception as e:
            logging.error(f"❌ Kotak SELL error: {e}")
            return {"status": "error", "message": str(e)}

    def _order_success(self, result):
        if not result or not isinstance(result, dict):
            return False
        if "error" in result:
            return False
        stat = str(result.get("stat", "")).lower()
        if stat in ("ok", "success") or result.get("nOrdNo") or result.get("order_id"):
            return True
        return False