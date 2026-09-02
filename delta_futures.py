import requests
import logging


# =========================================================
# Delta Exchange India
# Futures Market Data
# =========================================================

BASE_URL = "https://api.india.delta.exchange"


class DeltaFutures:

    def __init__(self):
        self.base_url = BASE_URL

    # =====================================================
    # Test Connection
    # =====================================================

    def test_connection(self):
        try:

            url = f"{self.base_url}/v2/products"

            response = requests.get(
                url,
                params={
                    "contract_types": "futures,perpetual_futures",
                    "states": "live",
                    "page_size": 100
                },
                headers={
                    "Accept": "application/json"
                },
                timeout=10
            )

            response.raise_for_status()

            data = response.json()

            if data.get("success"):

                products = data.get(
                    "result",
                    []
                )

                return True, products

            return False, data

        except Exception as e:

            logging.exception(
                "Delta Futures connection error"
            )

            return False, str(e)

    # =====================================================
    # Get Futures Contracts
    # =====================================================

    def get_futures(self):

        success, result = self.test_connection()

        if not success:
            return []

        return result
    
# =====================================================
# Get Ticker
# =====================================================

    def get_ticker(self, symbol):

        try:

            symbol = str(symbol).strip().upper()

            if not symbol:
                return {}

            url = (
                f"{self.base_url}"
                f"/v2/tickers/{symbol}"
            )

            response = requests.get(
                url,
                headers={
                    "Accept": "application/json"
                },
                timeout=10
            )

            response.raise_for_status()

            data = response.json()

            if not data.get("success"):
                logging.error(
                    f"Delta ticker failed | "
                    f"Symbol={symbol} | "
                    f"Response={data}"
                )
                return {}

            result = data.get("result", {})

            if not result:
                logging.warning(
                    f"Empty ticker result | Symbol={symbol}"
                )
                return {}

            return result

        except requests.RequestException as e:

            logging.error(
                f"Delta API request error | "
                f"Symbol={symbol} | Error={e}"
            )

            return {}

        except Exception as e:

            logging.exception(
                f"Delta ticker error | Symbol={symbol}"
            )

            return {}
        
# =========================================================
# Quick Test
# =========================================================

if __name__ == "__main__":

    delta = DeltaFutures()

    success, futures = (
        delta.test_connection()
    )

    if success:

        print(
            "✅ Delta Futures connection OK"
        )

        print(
            f"Futures found: {len(futures)}"
        )

        for product in futures[:10]:

            print(
                product.get("symbol"),
                "|",
                product.get("contract_type"),
                "| ID:",
                product.get("id")
            )

    else:

        print(
            "❌ Delta connection failed"
        )

        print(futures)