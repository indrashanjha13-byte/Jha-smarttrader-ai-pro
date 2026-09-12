import logging
import json
import os
import pyotp
from decouple import config

try:
    from neo_api_client import NeoAPI
except ImportError:
    NeoAPI = None


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SETTINGS_FILE = os.path.join(BASE_DIR, "settings.json")


class KotakBroker:

    def __init__(self):
        self.connected = False
        self.client = None

        # ==========================================================
        # KOTAK NEO CREDENTIALS
        # .env first
        # ==========================================================
        self.consumer_key = config(
            "KOTAK_CONSUMER_KEY",
            default=""
        )

        self.mobile_number = config(
            "KOTAK_MOBILE_NUMBER",
            default=""
        )

        self.ucc = config(
            "KOTAK_UCC",
            default=""
        )

        self.totp_secret = config(
            "KOTAK_TOTP_SECRET",
            default=""
        )

        self.mpin = config(
            "KOTAK_MPIN",
            default=""
        )

        self._load_from_settings()

    # ==============================================================
    # LOAD SETTINGS
    # ==============================================================

    def _load_from_settings(self):

        if not os.path.exists(SETTINGS_FILE):
            return

        try:
            with open(
                SETTINGS_FILE,
                "r",
                encoding="utf-8"
            ) as f:
                settings = json.load(f)

            if settings.get("broker") in (
                "Kotak Neo",
                "Kotak"
            ):
                self.consumer_key = settings.get(
                    "api_key",
                    self.consumer_key
                )

                self.ucc = settings.get(
                    "client_id",
                    self.ucc
                )

        except Exception as e:

            logging.error(
                "Error loading Kotak settings: %s",
                e
            )

    # ==============================================================
    # CONNECT / LOGIN
    # ==============================================================

    def connect(self):

        if NeoAPI is None:

            logging.error(
                "'neo_api_client' is not installed."
            )

            return False

        if self.connected and self.client:

            return True

        required_credentials = [
            self.consumer_key,
            self.mobile_number,
            self.ucc,
            self.totp_secret,
            self.mpin,
        ]

        if not all(required_credentials):

            logging.warning(
                "Kotak Neo credentials missing in .env/settings."
            )

            return False

        try:

            self.client = NeoAPI(
                consumer_key=self.consumer_key,
                environment="prod"
            )

            # Generate current TOTP
            totp = pyotp.TOTP(
                self.totp_secret
            ).now()

            # TOTP login
            login_response = self.client.totp_login(
                mobile_number=self.mobile_number,
                ucc=self.ucc,
                totp=totp
            )

            logging.info(
                "Kotak TOTP login completed."
            )

            # MPIN validation
            validate_response = self.client.totp_validate(
                mpin=self.mpin
            )

            logging.info(
                "Kotak TOTP validation completed."
            )

            self.connected = True

            logging.info(
                "Kotak Neo login successful."
            )

            return True

        except Exception as e:

            self.connected = False
            self.client = None

            logging.error(
                "Kotak Neo connection error: %s",
                e
            )

            return False

    # ==============================================================
    # SEARCH SYMBOL
    # ==============================================================

    def resolve_symbol(self, symbol):

        if not self.connected:

            if not self.connect():
                return None

        try:

            clean_symbol = str(
                symbol
            ).strip().upper()

            if clean_symbol.endswith(".NS"):

                clean_symbol = clean_symbol[:-3]

            elif clean_symbol.endswith(".NSE"):

                clean_symbol = clean_symbol[:-4]

            result = self.client.search_scrip(
                exchange_segment="nse_cm",
                symbol=clean_symbol
            )

            if not result:

                logging.warning(
                    "Kotak symbol not found: %s",
                    clean_symbol
                )

                return None

            # SDK normally returns a list
            if isinstance(result, dict):

                records = result.get(
                    "data",
                    result.get("scrips", [])
                )

            else:

                records = result

            if not isinstance(records, list) or not records:

                logging.warning(
                    "No Kotak scrip records for: %s",
                    clean_symbol
                )

                return None

            first = records[0]

            trading_symbol = first.get(
                "pTrdSymbol"
            )

            if not trading_symbol:

                return None

            try:
                lot_size = int(
                    first.get(
                        "lLotSize",
                        1
                    )
                )
            except Exception:
                lot_size = 1

            return {
                "symbol": clean_symbol,
                "trading_symbol": trading_symbol,
                "token": first.get("pSymbol"),
                "exchange_segment": first.get(
                    "pExchSeg",
                    "nse_cm"
                ),
                "lot_size": lot_size
            }

        except Exception as e:

            logging.error(
                "Kotak symbol resolution error: %s",
                e
            )

            return None

    # ==============================================================
    # READ-ONLY QUOTES
    # ==============================================================

    def quotes(
        self,
        instrument_tokens,
        quote_type=None
    ):
        """
        READ-ONLY Kotak market quote request.

        Example:

        [
            {
                "exchange_segment": "nse_fo",
                "instrument_token": "47293"
            }
        ]

        This method DOES NOT place any order.
        """

        if not self.connected:

            if not self.connect():

                return {
                    "success": False,
                    "error": "Kotak Neo is not connected."
                }

        if not instrument_tokens:

            return {
                "success": False,
                "error": "instrument_tokens is empty."
            }

        try:

            result = self.client.quotes(
                instrument_tokens=instrument_tokens,
                quote_type=quote_type
            )

            return {
                "success": True,
                "data": result
            }

        except Exception as e:

            logging.error(
                "Kotak quotes error: %s",
                e
            )

            return {
                "success": False,
                "error": str(e)
            }

    # ==============================================================
    # SINGLE OPTION LTP
    # ==============================================================

    def get_option_ltp(
        self,
        token,
        exchange_segment="nse_fo"
    ):
        """
        Read-only single option quote.

        No BUY.
        No SELL.
        No place_order().
        """

        if not token:

            return {
                "success": False,
                "error": "Option token is missing."
            }

        return self.quotes(
            instrument_tokens=[
                {
                    "exchange_segment": str(
                        exchange_segment
                    ),
                    "instrument_token": str(
                        token
                    )
                }
            ]
        )

    # ==============================================================
    # OPTION QUOTES - CE + PE TOGETHER
    # ==============================================================

    def get_option_quotes(
        self,
        ce_token=None,
        pe_token=None,
        exchange_segment="nse_fo"
    ):
        """
        Read-only CE + PE quote request.
        """

        tokens = []

        if ce_token:

            tokens.append(
                {
                    "exchange_segment": str(
                        exchange_segment
                    ),
                    "instrument_token": str(
                        ce_token
                    )
                }
            )

        if pe_token:

            tokens.append(
                {
                    "exchange_segment": str(
                        exchange_segment
                    ),
                    "instrument_token": str(
                        pe_token
                    )
                }
            )

        if not tokens:

            return {
                "success": False,
                "error": "No CE/PE token supplied."
            }

        return self.quotes(
            instrument_tokens=tokens
        )

    # ==============================================================
    # BALANCE
    # ==============================================================

    def get_balance(self):

        if not self.connected:

            if not self.connect():
                return 0.0

        try:

            res = self.client.limits()

            if isinstance(res, dict):

                return float(
                    res.get(
                        "Net",
                        res.get(
                            "availableLimit",
                            0.0
                        )
                    )
                )

            return 0.0

        except Exception as e:

            logging.error(
                "Kotak balance error: %s",
                e
            )

            return 0.0

    # ==============================================================
    # POSITIONS
    # ==============================================================

    def get_positions(self):

        if not self.connected:

            if not self.connect():
                return []

        try:

            res = self.client.positions()

            if isinstance(res, dict):

                return res.get(
                    "stat",
                    []
                )

            return res

        except Exception as e:

            logging.error(
                "Kotak positions error: %s",
                e
            )

            return []

    # ==============================================================
    # HOLDINGS
    # ==============================================================

    def get_holdings(self):

        if not self.connected:

            if not self.connect():
                return []

        try:

            return self.client.holdings()

        except Exception as e:

            logging.error(
                "Kotak holdings error: %s",
                e
            )

            return []

    # ==============================================================
    # ORDER BOOK
    # ==============================================================

    def order_book(self):

        if not self.connected:

            if not self.connect():
                return []

        try:

            return self.client.order_report()

        except Exception as e:

            logging.error(
                "Kotak order book error: %s",
                e
            )

            return []

    # ==============================================================
    # BUY
    # ==============================================================

    def buy(
        self,
        symbol,
        qty,
        price=0.0,
        **kwargs
    ):

        if not self.connected:

            if not self.connect():

                return {
                    "status": "error",
                    "message": "Not connected"
                }

        try:

            resolved = self.resolve_symbol(
                symbol
            )

            if not resolved:

                return {
                    "status": "error",
                    "message": "Symbol resolution failed"
                }

            trading_symbol = resolved[
                "trading_symbol"
            ]

            exchange_segment = resolved[
                "exchange_segment"
            ]

            quantity = int(qty)

            order_type = (
                "MKT"
                if price == 0
                else "L"
            )

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

            success = self._order_success(
                result
            )

            return {
                "status": (
                    "success"
                    if success
                    else "error"
                ),
                "response": result
            }

        except Exception as e:

            logging.error(
                "Kotak BUY error: %s",
                e
            )

            return {
                "status": "error",
                "message": str(e)
            }

    # ==============================================================
    # SELL
    # ==============================================================

    def sell(
        self,
        symbol,
        qty,
        price=0.0,
        **kwargs
    ):

        if not self.connected:

            if not self.connect():

                return {
                    "status": "error",
                    "message": "Not connected"
                }

        try:

            resolved = self.resolve_symbol(
                symbol
            )

            if not resolved:

                return {
                    "status": "error",
                    "message": "Symbol resolution failed"
                }

            trading_symbol = resolved[
                "trading_symbol"
            ]

            exchange_segment = resolved[
                "exchange_segment"
            ]

            quantity = int(qty)

            order_type = (
                "MKT"
                if price == 0
                else "L"
            )

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

            success = self._order_success(
                result
            )

            return {
                "status": (
                    "success"
                    if success
                    else "error"
                ),
                "response": result
            }

        except Exception as e:

            logging.error(
                "Kotak SELL error: %s",
                e
            )

            return {
                "status": "error",
                "message": str(e)
            }

    # ==============================================================
    # ORDER SUCCESS CHECK
    # ==============================================================

    def _order_success(self, result):

        if not result:
            return False

        if not isinstance(result, dict):
            return False

        if "error" in result:
            return False

        stat = str(
            result.get(
                "stat",
                ""
            )
        ).lower()

        if stat in (
            "ok",
            "success"
        ):
            return True

        if result.get("nOrdNo"):
            return True

        if result.get("order_id"):
            return True

        return False
