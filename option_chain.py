import requests
import time
import random
import logging

from fo_symbols import INDICES, FO_STOCKS


# ============================================================
# NSE OPTION CHAIN CONFIGURATION
# ============================================================

BASE_URL = "https://www.nseindia.com"

INDEX_API = (
    "https://www.nseindia.com/api/option-chain-indices?symbol={}"
)

EQUITY_API = (
    "https://www.nseindia.com/api/option-chain-equities?symbol={}"
)


# ============================================================
# NSE HEADERS
# ============================================================

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/142.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/option-chain",
    "Connection": "keep-alive",
}


# ============================================================
# SESSION
# ============================================================

session = requests.Session()
session.headers.update(HEADERS)


# ============================================================
# REFRESH NSE COOKIE
# ============================================================

def refresh_cookie():
    """
    Initialize NSE session cookies before requesting option chain.
    """

    try:
        # Open NSE homepage first
        session.get(
            "https://www.nseindia.com/",
            timeout=10
        )

        time.sleep(1)

        # Then open Option Chain page
        session.get(
            "https://www.nseindia.com/option-chain",
            timeout=10
        )

        time.sleep(1)

    except Exception as e:
        logging.warning(
            f"NSE Cookie Refresh Warning: {e}"
        )
# ============================================================
# SYMBOL NORMALIZATION
# ============================================================

def normalize_symbol(symbol):
    """
    Convert internal/index symbols to NSE option-chain symbols.
    """

    clean_sym = str(symbol).strip().upper()

    symbol_map = {
        "^NSEI": "NIFTY",
        "^NSEBANK": "BANKNIFTY",
        "^CNXFINANCE": "FINNIFTY",
        "^NSEMDCP50": "MIDCPNIFTY",
        "^BSESN": "SENSEX",

        "NSEI": "NIFTY",
        "NSEBANK": "BANKNIFTY",
        "CNXFINANCE": "FINNIFTY",
        "NSEMDCP50": "MIDCPNIFTY",
        "BSESN": "SENSEX",
    }

    return symbol_map.get(clean_sym, clean_sym)


# ============================================================
# GET OPTION CHAIN
# ============================================================

def get_option_chain(symbol):
    """
    Fetch live option-chain JSON data from NSE.

    Returns:
        NSE option-chain dictionary
        OR
        {"error": "..."}
    """

    clean_sym = str(symbol).strip().upper()

    api_sym = normalize_symbol(clean_sym)

    # --------------------------------------------------------
    # IMPORTANT:
    # SENSEX is not available through NSE option-chain API.
    # --------------------------------------------------------

    if api_sym == "SENSEX":
        return {
            "error": (
                "SENSEX option chain is not available "
                "through NSE API. Use BSE/Broker API."
            )
        }

    # --------------------------------------------------------
    # Determine index/equity endpoint
    # --------------------------------------------------------

    index_symbols = {
        "NIFTY",
        "BANKNIFTY",
        "FINNIFTY",
        "MIDCPNIFTY",
    }

    if api_sym in index_symbols:
        url = INDEX_API.format(api_sym)

    elif clean_sym in INDICES:
        url = INDEX_API.format(api_sym)

    elif "^" in clean_sym:
        url = INDEX_API.format(api_sym)

    else:
        # Equity F&O symbol
        api_sym = api_sym.replace(".NS", "")
        api_sym = api_sym.replace("-", "%20")

        url = EQUITY_API.format(api_sym)

    # --------------------------------------------------------
    # Refresh NSE session
    # --------------------------------------------------------

    refresh_cookie()

    # --------------------------------------------------------
    # Request
    # --------------------------------------------------------

    try:

        response = session.get(
            url,
            timeout=15
        )

        logging.debug(
            f"Fetching Option Chain -> "
            f"URL: {url} | "
            f"Status: {response.status_code}"
        )

        # ----------------------------------------------------
        # HTTP error
        # ----------------------------------------------------

        if response.status_code != 200:

            return {
                "error": (
                    f"HTTP Status "
                    f"{response.status_code}"
                )
            }

        # ----------------------------------------------------
        # JSON decode
        # ----------------------------------------------------

        try:

            data = response.json()

        except Exception:

            return {
                "error": "JSON Decode Failed",
                "response": response.text[:300]
            }

        # ----------------------------------------------------
        # Validate records
        # ----------------------------------------------------

        if "records" not in data:

            return {
                "error": "records key not found in response",
                "keys": list(data.keys()),
                "response": data
            }

        return data

    # --------------------------------------------------------
    # Timeout
    # --------------------------------------------------------

    except requests.exceptions.Timeout:

        return {
            "error": (
                "Request Timeout while "
                "connecting to NSE"
            )
        }

    # --------------------------------------------------------
    # Connection error
    # --------------------------------------------------------

    except requests.exceptions.ConnectionError as e:

        return {
            "error": f"NSE Connection Error: {e}"
        }

    # --------------------------------------------------------
    # General error
    # --------------------------------------------------------

    except Exception as e:

        return {
            "error": str(e)
        }


# ============================================================
# EXTRACT CE / PE OPTION PRICES
# ============================================================

def extract_option_prices(
    option_chain_data,
    strike=None,
    expiry=None
):
    """
    Extract CE and PE LTP from NSE option-chain response.

    If strike is None:
        Automatically finds ATM strike.

    If expiry is None:
        Uses nearest available expiry.

    Returns:

        {
            "CE": float,
            "PE": float,
            "strike": float,
            "expiry": str,
            "underlying": float
        }
    """

    # --------------------------------------------------------
    # Validate input
    # --------------------------------------------------------

    if not isinstance(option_chain_data, dict):

        return {
            "error": "Invalid option chain data"
        }

    # --------------------------------------------------------
    # Existing API error
    # --------------------------------------------------------

    if "error" in option_chain_data:

        return option_chain_data

    # --------------------------------------------------------
    # Get records
    # --------------------------------------------------------

    records = option_chain_data.get(
        "records",
        {}
    )

    data = records.get(
        "data",
        []
    )

    if not data:

        return {
            "error": "Option chain data is empty"
        }

    # --------------------------------------------------------
    # Underlying value
    # --------------------------------------------------------

    underlying_value = records.get(
        "underlyingValue"
    )

    if underlying_value is None:

        return {
            "error": "Underlying value not available"
        }

    try:

        underlying_value = float(
            underlying_value
        )

    except Exception:

        return {
            "error": "Invalid underlying value"
        }

    # --------------------------------------------------------
    # Expiry
    # --------------------------------------------------------

    expiry_dates = records.get(
        "expiryDates",
        []
    )

    if expiry is None:

        if expiry_dates:

            expiry = expiry_dates[0]

        else:

            expiry = None

    # --------------------------------------------------------
    # Find ATM strike
    # --------------------------------------------------------

    if strike is None:

        valid_strikes = []

        for row in data:

            try:

                row_strike = float(
                    row.get("strikePrice")
                )

                valid_strikes.append(
                    row_strike
                )

            except (
                TypeError,
                ValueError
            ):

                continue

        if not valid_strikes:

            return {
                "error": "No valid strikes found"
            }

        strike = min(
            valid_strikes,
            key=lambda x:
            abs(x - underlying_value)
        )

    # --------------------------------------------------------
    # Normalize strike
    # --------------------------------------------------------

    try:

        strike = float(strike)

    except Exception:

        return {
            "error": "Invalid strike value"
        }

    # --------------------------------------------------------
    # CE / PE prices
    # --------------------------------------------------------

    ce_price = None
    pe_price = None

    # --------------------------------------------------------
    # Search option-chain row
    # --------------------------------------------------------

    for row in data:

        try:

            row_strike = float(
                row.get("strikePrice")
            )

        except (
            TypeError,
            ValueError
        ):

            continue

        # Strike match
        if row_strike != strike:
            continue

        # ----------------------------------------------------
        # Expiry match
        # ----------------------------------------------------

        row_expiry = row.get(
            "expiryDate"
        )

        if (
            expiry
            and row_expiry
            and row_expiry != expiry
        ):
            continue

        # ----------------------------------------------------
        # CE
        # ----------------------------------------------------

        ce = row.get("CE")

        if isinstance(ce, dict):

            ce_price = ce.get(
                "lastPrice"
            )

        # ----------------------------------------------------
        # PE
        # ----------------------------------------------------

        pe = row.get("PE")

        if isinstance(pe, dict):

            pe_price = pe.get(
                "lastPrice"
            )

        break

    # --------------------------------------------------------
    # Convert prices
    # --------------------------------------------------------

    try:

        ce_price = (
            float(ce_price)
            if ce_price is not None
            else None
        )

    except (
        TypeError,
        ValueError
    ):

        ce_price = None

    try:

        pe_price = (
            float(pe_price)
            if pe_price is not None
            else None
        )

    except (
        TypeError,
        ValueError
    ):

        pe_price = None

    # --------------------------------------------------------
    # Return result
    # --------------------------------------------------------

    return {
        "CE": ce_price,
        "PE": pe_price,
        "strike": strike,
        "expiry": expiry,
        "underlying": underlying_value,
    }


# ============================================================
# SCAN ALL OPTION CHAINS
# ============================================================

def scan_all_option_chain():
    """
    Scan all configured indices and F&O stocks.

    Uses delays to reduce NSE rate-limit risk.
    """

    result = {}

    symbols = list(
        dict.fromkeys(
            INDICES + FO_STOCKS
        )
    )

    for symbol in symbols:

        logging.info(
            f"Scanning Option Chain for: {symbol}"
        )

        result[symbol] = get_option_chain(
            symbol
        )

        # Safe delay
        time.sleep(
            random.uniform(
                1.5,
                2.5
            )
        )

    return result


# ============================================================
# NSE CONNECTION TEST
# ============================================================

def test_nse_connection():

    urls = [
        "https://www.nseindia.com/",
        "https://www.nseindia.com/option-chain",
        "https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY",
    ]

    for url in urls:

        try:

            r = session.get(
                url,
                timeout=15
            )

            print("\nURL:", url)
            print("STATUS:", r.status_code)
            print("FINAL URL:", r.url)
            print(
                "CONTENT TYPE:",
                r.headers.get("Content-Type")
            )
            print(
                "RESPONSE:",
                r.text[:200]
            )

        except Exception as e:

            print(
                "\nERROR:",
                url,
                e
            )
# ============================================================
# MAIN TEST
# ============================================================

if __name__ == "__main__":
    test_nse_connection()