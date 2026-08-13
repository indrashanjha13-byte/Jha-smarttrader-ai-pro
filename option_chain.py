import requests
import time
import random

from fo_symbols import INDICES, FO_STOCKS

BASE_URL = "https://www.nseindia.com"

INDEX_API = "https://www.nseindia.com/api/option-chain-indices?symbol={}"
EQUITY_API = "https://www.nseindia.com/api/option-chain-equities?symbol={}"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/138.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/option-chain",
    "Connection": "keep-alive",
}

session = requests.Session()
session.headers.update(HEADERS)


def refresh_cookie():
    try:
        session.get(BASE_URL, timeout=10)
        time.sleep(random.uniform(1, 2))
    except Exception as e:
        print("Cookie Error:", e)


def get_option_chain(symbol):

    refresh_cookie()

    if symbol in INDICES:
        url = INDEX_API.format(symbol)
    else:
        url = EQUITY_API.format(symbol)
        print("URL =", url)

    try:

        response = session.get(url, timeout=15)

        print("URL =", url)
        print("Status =", response.status_code)
        print("Text =", response.text[:500])

        if response.status_code != 200:
            return {
                "error": f"HTTP {response.status_code}"
            }

        try:

            data = response.json()

        except Exception:

            return {
                "error": "JSON Decode Failed",
                "response": response.text[:500]
            }

        if "records" not in data:

            return {
                "error": "records key not found",
                "keys": list(data.keys()),
                "response": data
            }

        return data

    except Exception as e:

        return {
            "error": str(e)
        }


def scan_all_option_chain():

    result = {}

    symbols = INDICES + FO_STOCKS

    for symbol in symbols:

        print(f"Scanning {symbol}")

        result[symbol] = get_option_chain(symbol)

        time.sleep(0.5)

    return result


if __name__ == "__main__":

    data = get_option_chain("NIFTY")

    print(data)