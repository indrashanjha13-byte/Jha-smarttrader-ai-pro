import requests
import time
import random
import logging

from fo_symbols import INDICES, FO_STOCKS

BASE_URL = "https://www.nseindia.com"

INDEX_API = "https://www.nseindia.com/api/option-chain-indices?symbol={}"
EQUITY_API = "https://www.nseindia.com/api/option-chain-equities?symbol={}"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://www.nseindia.com/option-chain",
    "Connection": "keep-alive",
}

# Initialize Session
session = requests.Session()
session.headers.update(HEADERS)


def refresh_cookie():
    """Refreshes session cookies by hitting NSE homepage to bypass basic bot shields."""
    try:
        session.get(BASE_URL, timeout=10)
        time.sleep(random.uniform(1.5, 3.0))
    except Exception as e:
        logging.warning(f"⚠️ Cookie Refresh Warning: {e}")


def get_option_chain(symbol):
    """
    Fetches live option chain JSON data for a given index or equity symbol from NSE.
    """
    refresh_cookie()

    # Normalize symbol for URL mapping
    clean_sym = str(symbol).strip().upper()

    # Check if symbol belongs to indices
    if clean_sym in INDICES or "^" in clean_sym or clean_sym in ["NIFTY", "BANKNIFTY", "SENSEX"]:
        # Format index symbol for NSE API (e.g., ^NSEI -> NIFTY)
        api_sym = clean_sym.replace("^NSEI", "NIFTY").replace("^NSEBANK", "BANKNIFTY").replace("^BSESN", "SENSEX")
        url = INDEX_API.format(api_sym)
    else:
        # Clean equity symbol (remove .NS if present for NSE website)
        api_sym = clean_sym.replace(".NS", "").replace("-", "%20")
        url = EQUITY_API.format(api_sym)

    try:
        response = session.get(url, timeout=15)
        
        logging.debug(f"Fetching Option Chain -> URL: {url} | Status: {response.status_code}")

        if response.status_code != 200:
            return {
                "error": f"HTTP Status {response.status_code}"
            }

        try:
            data = response.json()
        except Exception:
            return {
                "error": "JSON Decode Failed",
                "response": response.text[:300]
            }

        if "records" not in data:
            return {
                "error": "records key not found in response",
                "keys": list(data.keys()),
                "response": data
            }

        return data

    except requests.exceptions.Timeout:
        return {"error": "Request Timeout while connecting to NSE"}
    except Exception as e:
        return {"error": str(e)}


def scan_all_option_chain():
    """Scans option chains for all configured indices and F&O stocks safely with delays."""
    result = {}
    symbols = list(dict.fromkeys(INDICES + FO_STOCKS))

    for symbol in symbols:
        logging.info(f"Scanning Option Chain for: {symbol}")
        result[symbol] = get_option_chain(symbol)
        # Safe delay to prevent IP rate-limiting / blocking by NSE
        time.sleep(random.uniform(1.5, 2.5))

    return result


if __name__ == "__main__":
    # Test script execution
    test_symbol = "NIFTY"
    print(f"Testing Option Chain fetch for {test_symbol}...")
    data = get_option_chain(test_symbol)
    print("Result Keys:", list(data.keys()) if isinstance(data, dict) else data)