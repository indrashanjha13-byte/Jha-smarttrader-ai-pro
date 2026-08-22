from decouple import config
from neo_api_client import NeoAPI
import pyotp


class KotakBroker:

    def __init__(self):

        self.connected = False
        self.client = None

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

    def connect(self):

        try:

            if not self.consumer_key:
                print("KOTAK_CONSUMER_KEY missing.")
                return False

            if not self.mobile_number:
                print("KOTAK_MOBILE_NUMBER missing.")
                return False

            if not self.ucc:
                print("KOTAK_UCC missing.")
                return False

            if not self.totp_secret:
                print("KOTAK_TOTP_SECRET missing.")
                return False

            if not self.mpin:
                print("KOTAK_MPIN missing.")
                return False

            self.client = NeoAPI(
                consumer_key=self.consumer_key,
                environment="prod"
            )

            print("Kotak Neo client created.")

            totp = pyotp.TOTP(
                self.totp_secret
            ).now()

            self.client.totp_login(
                mobile_number=self.mobile_number,
                ucc=self.ucc,
                totp=totp
            )

            print("Kotak TOTP login successful.")

            self.client.totp_validate(
                mpin=self.mpin
            )

            print("Kotak MPIN validation successful.")

            self.connected = True

            return True

        except Exception as e:

            self.connected = False

            print(
                f"Kotak Neo connection error: {e}"
            )

            return False

    def get_balance(self):

        if not self.connected:
            return 0

        try:
            return self.client.limits()

        except Exception as e:
            print(
                f"Kotak balance error: {e}"
            )
            return 0

    def get_positions(self):

        if not self.connected:
            return []

        try:
            return self.client.positions()

        except Exception as e:
            print(
                f"Kotak positions error: {e}"
            )
            return []

    def get_holdings(self):

        if not self.connected:
            return []

        try:
            return self.client.holdings()

        except Exception as e:
            print(
                f"Kotak holdings error: {e}"
            )
            return []

    def order_book(self):

        if not self.connected:
            return []

        try:
            return self.client.order_report()

        except Exception as e:
            print(
                f"Kotak order book error: {e}"
            )
            return []

    def buy(self, symbol, qty):

        print(
            "LIVE BUY disabled during integration test."
        )

        return False

    def sell(self, symbol, qty):

        print(
            "LIVE SELL disabled during integration test."
        )

        return False