import requests
import time
import random

from fo_symbols import INDICES, FO_STOCKS


BASE_URL = "https://www.nseindia.com"

INDEX_API = (
    "https://www.nseindia.com/api/option-chain-indices?symbol={}"
)

EQUITY_API = (
    "https://www.nseindia.com/api/option-chain-equities?symbol={}"
)


HEADERS = {

    "User-Agent":
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/138.0 Safari/537.36"
    ),

    "Accept": "application/json",

    "Accept-Language": "en-US,en;q=0.9",

    "Referer": "https://www.nseindia.com/option-chain",

    "Connection": "keep-alive"

}


session = requests.Session()

session.headers.update(HEADERS)


def refresh_cookie():

    session.get(
        BASE_URL,
        timeout=10
    )

    time.sleep(
        random.uniform(
            1,
            2
        )
    )


    # =====================================
# DOWNLOAD OPTION CHAIN
# =====================================

def get_option_chain(symbol):

    refresh_cookie()

    if symbol in INDICES:

        url = INDEX_API.format(symbol)

    else:

        url = EQUITY_API.format(symbol)

    response = session.get(
        url,
        timeout=15
    )

    response.raise_for_status()

    return response.json()

# =====================================
# TEST SCANNER
# =====================================

def scan_all_option_chain():

    result = {}

    symbols = INDICES + FO_STOCKS

    for symbol in symbols:

        try:

            data = get_option_chain(symbol)

            result[symbol] = data

        except Exception as e:

            result[symbol] = {
                "error": str(e)
            }

    return result
