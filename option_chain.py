# ============================================================
# JHA SMARTTRADER AI PRO
# UNIFIED OPTION CHAIN MODULE
#
# PRIMARY LIVE PRICE SOURCE:
#     Kotak Neo Quotes
#
# FALLBACK SOURCE:
#     NSE Option Chain
#
# IMPORTANT:
#     This module is READ-ONLY for market/option prices.
#     It does NOT place BUY/SELL orders.
# ============================================================

import logging
import re
import time
from datetime import datetime, date
from typing import Any, Optional

import requests


# ============================================================
# LOGGING
# ============================================================

logger = logging.getLogger(__name__)

if not logger.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )


# ============================================================
# OPTIONAL KOTAK IMPORTS
# ============================================================

try:
    from broker.kotak_api import KotakBroker
except Exception as exc:
    KotakBroker = None
    logger.warning(
        "KotakBroker import failed: %s",
        exc,
    )


try:
    from kotak_option_resolver import resolve_atm_option
except Exception as exc:
    resolve_atm_option = None
    logger.warning(
        "Kotak option resolver import failed: %s",
        exc,
    )


# ============================================================
# KOTAK CONNECTION CACHE
# ============================================================

_kotak_broker = None


def _get_kotak_broker():
    """
    Return a reusable KotakBroker connection.

    IMPORTANT:
        This is used only for READ-ONLY quotes.
        No order is placed here.
    """

    global _kotak_broker

    if KotakBroker is None:
        return None

    try:

        if _kotak_broker is None:
            _kotak_broker = KotakBroker()

        if not getattr(
            _kotak_broker,
            "connected",
            False,
        ):

            connected = _kotak_broker.connect()

            if not connected:
                logger.warning(
                    "Kotak Neo connection failed."
                )
                return None

        return _kotak_broker

    except Exception as exc:

        logger.exception(
            "Kotak broker initialization error: %s",
            exc,
        )

        return None


# ============================================================
# NSE CONFIG
# ============================================================

NSE_HOME = "https://www.nseindia.com"

NSE_OPTION_CHAIN_INDEX_URL = (
    "https://www.nseindia.com/api/option-chain-indices?symbol={}"
)

NSE_OPTION_CHAIN_EQUITY_URL = (
    "https://www.nseindia.com/api/option-chain-equities?symbol={}"
)


# ============================================================
# SUPPORTED INDEX CONFIG
# ============================================================

NSE_INDEX_SYMBOLS = {
    "NIFTY",
    "BANKNIFTY",
    "FINNIFTY",
    "MIDCPNIFTY",
}

BSE_INDEX_SYMBOLS = {
    "SENSEX",
}


# ============================================================
# NSE HEADERS
# ============================================================

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/142.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "application/json,text/plain,*/*"
    ),
    "Accept-Language": (
        "en-US,en;q=0.9"
    ),
    "Referer": (
        "https://www.nseindia.com/"
    ),
    "Origin": (
        "https://www.nseindia.com"
    ),
    "Connection": "keep-alive",
}


# ============================================================
# NSE SESSION
# ============================================================

session = requests.Session()
session.headers.update(HEADERS)

_last_cookie_refresh = 0.0

COOKIE_REFRESH_INTERVAL = 30.0


# ============================================================
# SYMBOL NORMALIZATION
# ============================================================

def normalize_symbol(
    symbol: Any,
) -> Optional[str]:

    if symbol is None:
        return None

    value = str(
        symbol
    ).strip().upper()

    if not value:
        return None

    symbol_map = {

        "^NSEI": "NIFTY",
        "NIFTY": "NIFTY",
        "NIFTY 50": "NIFTY",
        "NIFTY50": "NIFTY",

        "^NSEBANK": "BANKNIFTY",
        "BANKNIFTY": "BANKNIFTY",
        "NIFTY BANK": "BANKNIFTY",
        "NIFTYBANK": "BANKNIFTY",

        "^CNXFINANCE": "FINNIFTY",
        "FINNIFTY": "FINNIFTY",
        "NIFTY FIN SERVICE": "FINNIFTY",
        "NIFTY FINANCIAL SERVICES": "FINNIFTY",

        "^NSEMDCP50": "MIDCPNIFTY",
        "MIDCPNIFTY": "MIDCPNIFTY",
        "NIFTY MID SELECT": "MIDCPNIFTY",
        "NIFTY MIDCAP SELECT": "MIDCPNIFTY",

        "^BSESN": "SENSEX",
        "BSESN": "SENSEX",
        "SENSEX": "SENSEX",
    }

    return symbol_map.get(
        value,
        value,
    )


# ============================================================
# SAFE FLOAT
# ============================================================

def _safe_float(
    value: Any,
) -> Optional[float]:

    try:

        if value is None:
            return None

        if isinstance(
            value,
            str,
        ):

            value = (
                value
                .replace(",", "")
                .replace("₹", "")
                .strip()
            )

            if value.upper() in (
                "",
                "-",
                "NA",
                "N/A",
                "NULL",
                "NONE",
                "NAN",
            ):
                return None

        result = float(value)

        if result != result:
            return None

        return result

    except (
        TypeError,
        ValueError,
    ):

        return None


# ============================================================
# SAFE DATE PARSER
# ============================================================

def _parse_expiry_date(
    value: Any,
) -> Optional[date]:

    if value is None:
        return None

    text = str(
        value
    ).strip()

    if not text:
        return None

    text = re.sub(
        r"\s+",
        "",
        text,
    )

    formats = (
        "%d-%b-%Y",
        "%d-%B-%Y",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y-%m-%d",
        "%d.%m.%Y",
        "%d%b%Y",
        "%d%B%Y",
        "%d%b%y",
        "%d-%b-%y",
    )

    for fmt in formats:

        try:

            return datetime.strptime(
                text.upper(),
                fmt,
            ).date()

        except ValueError:
            continue

    return None


# ============================================================
# EXPIRY NORMALIZATION
# ============================================================

def _expiry_key(
    value: Any,
) -> str:

    if value is None:
        return ""

    parsed = _parse_expiry_date(
        value
    )

    if parsed:

        return parsed.isoformat()

    text = str(
        value
    ).strip().upper()

    text = re.sub(
        r"\s+",
        "",
        text,
    )

    return (
        text
        .replace("-", "")
        .replace("/", "")
        .replace(".", "")
    )


# ============================================================
# SELECT EXPIRY
# ============================================================

def _select_expiry(
    expiry_dates: list,
    requested_expiry: Any = None,
) -> Optional[Any]:

    if not expiry_dates:
        return None

    # Requested expiry
    if requested_expiry is not None:

        requested_key = _expiry_key(
            requested_expiry
        )

        for available in expiry_dates:

            if (
                _expiry_key(available)
                == requested_key
            ):
                return available

        requested_date = _parse_expiry_date(
            requested_expiry
        )

        if requested_date:

            for available in expiry_dates:

                available_date = (
                    _parse_expiry_date(
                        available
                    )
                )

                if (
                    available_date
                    == requested_date
                ):
                    return available

        return None

    # Nearest future expiry
    today = datetime.now().date()

    parsed_expiries = []

    for item in expiry_dates:

        expiry_date = _parse_expiry_date(
            item
        )

        if expiry_date is None:
            continue

        if expiry_date >= today:

            parsed_expiries.append(
                (
                    expiry_date,
                    item,
                )
            )

    if parsed_expiries:

        parsed_expiries.sort(
            key=lambda x: x[0]
        )

        return parsed_expiries[0][1]

    return expiry_dates[0]


# ============================================================
# REFRESH NSE SESSION
# ============================================================

def refresh_cookie(
    force: bool = False,
) -> bool:

    global _last_cookie_refresh

    now = time.time()

    if (
        not force
        and _last_cookie_refresh > 0
        and (
            now - _last_cookie_refresh
        ) < COOKIE_REFRESH_INTERVAL
    ):

        return True

    try:

        response = session.get(
            NSE_HOME,
            headers=HEADERS,
            timeout=10,
        )

        if response.status_code != 200:

            logger.warning(
                "NSE homepage status: %s",
                response.status_code,
            )

        _last_cookie_refresh = now

        return True

    except requests.RequestException as exc:

        logger.warning(
            "NSE cookie refresh failed: %s",
            exc,
        )

        return False


# ============================================================
# BUILD NSE API URL
# ============================================================

def _build_option_chain_url(
    nse_symbol: str,
) -> Optional[str]:

    if nse_symbol in BSE_INDEX_SYMBOLS:
        return None

    if nse_symbol in NSE_INDEX_SYMBOLS:

        return NSE_OPTION_CHAIN_INDEX_URL.format(
            nse_symbol
        )

    return NSE_OPTION_CHAIN_EQUITY_URL.format(
        nse_symbol
    )


# ============================================================
# GET NSE OPTION CHAIN
# ============================================================

def get_option_chain(
    symbol: str,
) -> dict:

    nse_symbol = normalize_symbol(
        symbol
    )

    if not nse_symbol:

        return {
            "error": "Invalid symbol"
        }

    if nse_symbol == "SENSEX":

        return {
            "error": (
                "SENSEX is a BSE index. "
                "Use Kotak Neo for SENSEX options."
            )
        }

    url = _build_option_chain_url(
        nse_symbol
    )

    if not url:

        return {
            "error": (
                f"No NSE option-chain endpoint "
                f"available for {nse_symbol}"
            )
        }

    try:

        refresh_cookie()

        response = None

        for attempt in range(3):

            try:

                response = session.get(
                    url,
                    headers=HEADERS,
                    timeout=15,
                )

                status = response.status_code

                if status == 200:
                    break

                logger.warning(
                    "NSE option API status %s "
                    "for %s "
                    "(attempt %s/3)",
                    status,
                    nse_symbol,
                    attempt + 1,
                )

                if status in (
                    401,
                    403,
                    429,
                ):

                    if attempt < 2:

                        refresh_cookie(
                            force=True
                        )

                        time.sleep(
                            1.5
                            * (
                                attempt + 1
                            )
                        )

                        continue

                if attempt < 2:

                    time.sleep(
                        1.0
                        * (
                            attempt + 1
                        )
                    )

                    continue

                break

            except requests.RequestException as exc:

                logger.warning(
                    "NSE request exception "
                    "for %s "
                    "(attempt %s/3): %s",
                    nse_symbol,
                    attempt + 1,
                    exc,
                )

                if attempt >= 2:
                    raise

                time.sleep(
                    1.0
                    * (
                        attempt + 1
                    )
                )

        if response is None:

            return {
                "error": (
                    "NSE response unavailable"
                )
            }

        if response.status_code != 200:

            return {
                "error": (
                    "NSE API returned HTTP "
                    f"{response.status_code}"
                )
            }

        try:

            data = response.json()

        except ValueError:

            return {
                "error": (
                    "NSE returned invalid JSON"
                )
            }

        if not isinstance(
            data,
            dict,
        ):

            return {
                "error": (
                    "Invalid NSE JSON response"
                )
            }

        if "records" not in data:

            return {
                "error": (
                    "NSE response missing records"
                )
            }

        if not isinstance(
            data.get("records"),
            dict,
        ):

            return {
                "error": (
                    "Invalid NSE records structure"
                )
            }

        return data

    except requests.Timeout:

        logger.warning(
            "NSE option-chain timeout "
            "for %s",
            nse_symbol,
        )

        return {
            "error": (
                "NSE request timeout"
            )
        }

    except requests.RequestException as exc:

        logger.warning(
            "NSE request error "
            "for %s: %s",
            nse_symbol,
            exc,
        )

        return {
            "error": str(exc)
        }

    except Exception as exc:

        logger.exception(
            "Unexpected option-chain error "
            "for %s",
            nse_symbol,
        )

        return {
            "error": str(exc)
        }


# ============================================================
# EXTRACT NSE LTP
# ============================================================

def _extract_ltp(
    option_data: dict,
) -> Optional[float]:

    if not isinstance(
        option_data,
        dict,
    ):
        return None

    ltp = _safe_float(
        option_data.get(
            "lastPrice"
        )
    )

    if (
        ltp is not None
        and ltp > 0
    ):
        return ltp

    bid = _safe_float(
        option_data.get(
            "bidprice"
        )
    )

    if (
        bid is not None
        and bid > 0
    ):
        return bid

    ask = _safe_float(
        option_data.get(
            "askPrice"
        )
    )

    if (
        ask is not None
        and ask > 0
    ):
        return ask

    close = _safe_float(
        option_data.get(
            "closePrice"
        )
    )

    if (
        close is not None
        and close > 0
    ):
        return close

    return None


# ============================================================
# BUILD NSE CONTRACT
# ============================================================

def _build_contract(
    index_name: str,
    option_type: str,
    strike: float,
    expiry: Any,
    underlying: Optional[float],
    option_data: dict,
) -> dict:

    if not isinstance(
        option_data,
        dict,
    ):
        option_data = {}

    identifier = option_data.get(
        "identifier"
    )

    last_price = _safe_float(
        option_data.get(
            "lastPrice"
        )
    )

    bid = _safe_float(
        option_data.get(
            "bidprice"
        )
    )

    ask = _safe_float(
        option_data.get(
            "askPrice"
        )
    )

    close_price = _safe_float(
        option_data.get(
            "closePrice"
        )
    )

    effective_ltp = _extract_ltp(
        option_data
    )

    return {

        "index": index_name,

        "option_type": option_type,

        "strike": strike,

        "expiry": expiry,

        "underlying": underlying,

        "last_price": last_price,

        "ltp": effective_ltp,

        "bid": bid,

        "ask": ask,

        "close_price": close_price,

        "change": _safe_float(
            option_data.get(
                "change"
            )
        ),

        "change_percent": _safe_float(
            option_data.get(
                "pChange"
            )
        ),

        "open_interest": _safe_float(
            option_data.get(
                "openInterest"
            )
        ),

        "volume": _safe_float(
            option_data.get(
                "totalTradedVolume"
            )
        ),

        "identifier": identifier,

        "exchange": "NSE",

        "price_source": (
            "lastPrice"
            if (
                last_price is not None
                and last_price > 0
            )
            else (
                "bidprice"
                if (
                    bid is not None
                    and bid > 0
                )
                else (
                    "askPrice"
                    if (
                        ask is not None
                        and ask > 0
                    )
                    else (
                        "closePrice"
                        if (
                            close_price
                            is not None
                            and close_price > 0
                        )
                        else "UNAVAILABLE"
                    )
                )
            )
        ),
    }


# ============================================================
# EXTRACT NSE CE / PE
# ============================================================

def extract_option_prices(
    option_chain_data: dict,
    strike: Any = None,
    expiry: Any = None,
) -> dict:

    if not isinstance(
        option_chain_data,
        dict,
    ):

        return {
            "error": (
                "Invalid option chain data"
            )
        }

    records = option_chain_data.get(
        "records"
    )

    if not isinstance(
        records,
        dict,
    ):

        return {
            "error": (
                "Invalid records data"
            )
        }

    underlying = _safe_float(
        records.get(
            "underlyingValue"
        )
    )

    if underlying is None:

        return {
            "error": (
                "Underlying value unavailable"
            )
        }

    expiry_dates = records.get(
        "expiryDates",
        [],
    )

    if (
        not isinstance(
            expiry_dates,
            list,
        )
        or not expiry_dates
    ):

        return {
            "error": (
                "No expiry dates available"
            )
        }

    selected_expiry = _select_expiry(
        expiry_dates,
        expiry,
    )

    if selected_expiry is None:

        return {
            "error": (
                f"Expiry {expiry} not found. "
                f"Available: "
                f"{expiry_dates[:5]}"
            )
        }

    data_rows = records.get(
        "data",
        [],
    )

    if not isinstance(
        data_rows,
        list,
    ):

        return {
            "error": (
                "Option-chain data rows "
                "unavailable"
            )
        }

    valid_rows = []

    selected_key = _expiry_key(
        selected_expiry
    )

    for row in data_rows:

        if not isinstance(
            row,
            dict,
        ):
            continue

        row_strike = _safe_float(
            row.get(
                "strikePrice"
            )
        )

        if row_strike is None:
            continue

        row_expiry = row.get(
            "expiryDate"
        )

        row_key = _expiry_key(
            row_expiry
        )

        if row_key != selected_key:

            row_date = (
                _parse_expiry_date(
                    row_expiry
                )
            )

            selected_date = (
                _parse_expiry_date(
                    selected_expiry
                )
            )

            if (
                row_date is None
                or selected_date is None
                or row_date != selected_date
            ):
                continue

        valid_rows.append(
            (
                row_strike,
                row,
            )
        )

    if not valid_rows:

        return {
            "error": (
                "No option data found "
                f"for expiry "
                f"{selected_expiry}"
            )
        }

    selected_strike = None
    selected_row = None

    # ATM
    if strike is None:

        selected_strike, selected_row = min(
            valid_rows,
            key=lambda item: abs(
                item[0]
                - underlying
            ),
        )

    else:

        requested_strike = _safe_float(
            strike
        )

        if requested_strike is None:

            return {
                "error": (
                    "Invalid strike"
                )
            }

        for (
            row_strike,
            row,
        ) in valid_rows:

            if abs(
                row_strike
                - requested_strike
            ) < 0.01:

                selected_strike = (
                    row_strike
                )

                selected_row = row

                break

        if selected_row is None:

            available_strikes = sorted(
                {
                    item[0]
                    for item in valid_rows
                }
            )

            return {
                "error": (
                    f"Strike "
                    f"{requested_strike} "
                    f"not found for expiry "
                    f"{selected_expiry}. "
                    f"Nearest available "
                    f"strikes: "
                    f"{available_strikes[:10]}"
                )
            }

    ce_data = selected_row.get(
        "CE"
    )

    if not isinstance(
        ce_data,
        dict,
    ):
        ce_data = {}

    ce_contract = _build_contract(
        index_name="",
        option_type="CE",
        strike=selected_strike,
        expiry=selected_expiry,
        underlying=underlying,
        option_data=ce_data,
    )

    pe_data = selected_row.get(
        "PE"
    )

    if not isinstance(
        pe_data,
        dict,
    ):
        pe_data = {}

    pe_contract = _build_contract(
        index_name="",
        option_type="PE",
        strike=selected_strike,
        expiry=selected_expiry,
        underlying=underlying,
        option_data=pe_data,
    )

    ce_price = _safe_float(
        ce_contract.get(
            "ltp"
        )
    )

    pe_price = _safe_float(
        pe_contract.get(
            "ltp"
        )
    )

    return {

        "success": True,

        "CE": ce_price,

        "PE": pe_price,

        "CE_LTP": ce_price,

        "PE_LTP": pe_price,

        "strike": selected_strike,

        "expiry": selected_expiry,

        "underlying": underlying,

        "CE_CONTRACT": ce_contract,

        "PE_CONTRACT": pe_contract,

        "available_expiries": (
            expiry_dates
        ),

        "CE_PRICE_SOURCE": (
            ce_contract.get(
                "price_source"
            )
        ),

        "PE_PRICE_SOURCE": (
            pe_contract.get(
                "price_source"
            )
        ),
    }


# ============================================================
# KOTAK CONTRACT NORMALIZER
# ============================================================

def _normalize_kotak_contract(
    resolved: dict,
    option_type: str,
) -> Optional[dict]:
    """
    Extract CE/PE contract from resolver response.

    Resolver structure:

        {
            "index": ...,
            "underlying_price": ...,
            "atm_strike": ...,
            "expiry": ...,
            "exchange_segment": ...,
            "contracts": {
                "CE": {...},
                "PE": {...}
            }
        }
    """

    if not isinstance(
        resolved,
        dict,
    ):
        return None

    contracts = resolved.get(
        "contracts",
        {}
    )

    if not isinstance(
        contracts,
        dict,
    ):
        return None

    contract = contracts.get(
        option_type
    )

    if not isinstance(
        contract,
        dict,
    ):
        return None

    # Copy so original resolver result
    # is never modified.
    normalized = dict(
        contract
    )

    if not normalized.get(
        "exchange_segment"
    ):

        normalized["exchange_segment"] = (
            resolved.get(
                "exchange_segment"
            )
            or "nse_fo"
        )

    if not normalized.get(
        "expiry"
    ):

        normalized["expiry"] = (
            resolved.get(
                "expiry"
            )
        )

    if not normalized.get(
        "strike"
    ):

        normalized["strike"] = (
            resolved.get(
                "atm_strike"
            )
        )

    if not normalized.get(
        "option_type"
    ):

        normalized["option_type"] = (
            option_type
        )

    if not normalized.get(
        "underlying"
    ):

        normalized["underlying"] = (
            resolved.get(
                "underlying_price"
            )
        )

    return normalized


# ============================================================
# KOTAK QUOTE FETCH
# ============================================================

def _get_kotak_option_quotes(
    ce_contract: Optional[dict],
    pe_contract: Optional[dict],
) -> dict:
    """
    Fetch exact CE/PE LTP from Kotak Neo.

    READ-ONLY.
    No BUY/SELL order is placed.
    """

    result = {

        "success": False,

        "CE_LTP": None,

        "PE_LTP": None,

        "CE_QUOTE": None,

        "PE_QUOTE": None,

        "error": None,
    }

    try:

        broker = _get_kotak_broker()

        if broker is None:

            result["error"] = (
                "Kotak Neo unavailable"
            )

            return result

        ce_token = None
        pe_token = None

        exchange_segment = "nse_fo"

        if isinstance(
            ce_contract,
            dict,
        ):

            ce_token = ce_contract.get(
                "token"
            )

            exchange_segment = (
                ce_contract.get(
                    "exchange_segment"
                )
                or exchange_segment
            )

        if isinstance(
            pe_contract,
            dict,
        ):

            pe_token = pe_contract.get(
                "token"
            )

            if not ce_token:

                exchange_segment = (
                    pe_contract.get(
                        "exchange_segment"
                    )
                    or exchange_segment
                )

        if ce_token is not None:
            ce_token = str(
                ce_token
            ).strip()

        if pe_token is not None:
            pe_token = str(
                pe_token
            ).strip()

        if (
            not ce_token
            and not pe_token
        ):

            result["error"] = (
                "Kotak CE/PE token "
                "unavailable"
            )

            return result

        quote_result = (
            broker.get_option_quotes(
                ce_token=ce_token,
                pe_token=pe_token,
                exchange_segment=(
                    exchange_segment
                ),
            )
        )

        if not isinstance(
            quote_result,
            dict,
        ):

            result["error"] = (
                "Invalid Kotak quote response"
            )

            return result

        if not quote_result.get(
            "success"
        ):

            result["error"] = (
                quote_result.get(
                    "error",
                    "Kotak quote request failed",
                )
            )

            return result

        quote_data = quote_result.get(
            "data",
            [],
        )

        if not isinstance(
            quote_data,
            list,
        ):

            result["error"] = (
                "Invalid Kotak quote data"
            )

            return result

        ce_token_str = (
            str(ce_token)
            if ce_token
            else None
        )

        pe_token_str = (
            str(pe_token)
            if pe_token
            else None
        )

        for quote in quote_data:

            if not isinstance(
                quote,
                dict,
            ):
                continue

            quote_token = str(
                quote.get(
                    "exchange_token",
                    "",
                )
            ).strip()

            ltp = _safe_float(
                quote.get(
                    "ltp"
                )
            )

            if (
                ltp is None
                or ltp <= 0
            ):
                continue

            if (
                ce_token_str
                and quote_token
                == ce_token_str
            ):

                result["CE_LTP"] = ltp

                result["CE_QUOTE"] = quote

            if (
                pe_token_str
                and quote_token
                == pe_token_str
            ):

                result["PE_LTP"] = ltp

                result["PE_QUOTE"] = quote

        if (
            result["CE_LTP"] is not None
            or result["PE_LTP"] is not None
        ):

            result["success"] = True

        else:

            result["error"] = (
                "Kotak returned no valid "
                "CE/PE LTP"
            )

        return result

    except Exception as exc:

        logger.exception(
            "Kotak option quote error: %s",
            exc,
        )

        result["error"] = str(
            exc
        )

        return result


# ============================================================
# KOTAK PRICE USING RESOLVER
# ============================================================

def _get_kotak_resolved_prices(
    index_name: str,
    underlying_price: Any,
    option_type: Optional[str] = None,
) -> dict:
    """
    Resolve actual Kotak option contracts dynamically
    and fetch their live LTP.

    underlying_price MUST come from the current market
    price already known by the dashboard/application.

    READ-ONLY.
    """

    try:

        if resolve_atm_option is None:

            return {
                "success": False,
                "error": (
                    "Kotak option resolver "
                    "unavailable"
                ),
            }

        symbol = normalize_symbol(
            index_name
        )

        if not symbol:

            return {
                "success": False,
                "error": "Invalid index",
            }

        underlying = _safe_float(
            underlying_price
        )

        if (
            underlying is None
            or underlying <= 0
        ):

            return {
                "success": False,
                "error": (
                    "Invalid underlying price"
                ),
            }

        # ----------------------------------------------------
        # Resolver
        # ----------------------------------------------------

        resolved = resolve_atm_option(
            symbol,
            underlying,
            "CE",
        )

        if not isinstance(
            resolved,
            dict,
        ):

            return {
                "success": False,
                "error": (
                    "Kotak resolver returned "
                    "invalid result"
                ),
            }

        ce_contract = (
            _normalize_kotak_contract(
                resolved,
                "CE",
            )
        )

        pe_contract = (
            _normalize_kotak_contract(
                resolved,
                "PE",
            )
        )

        # ----------------------------------------------------
        # If PE wasn't included, resolve PE separately
        # ----------------------------------------------------

        if pe_contract is None:

            pe_resolved = (
                resolve_atm_option(
                    symbol,
                    underlying,
                    "PE",
                )
            )

            pe_contract = (
                _normalize_kotak_contract(
                    pe_resolved,
                    "PE",
                )
            )

        # ----------------------------------------------------
        # CE missing
        # ----------------------------------------------------

        if ce_contract is None:

            ce_resolved = (
                resolve_atm_option(
                    symbol,
                    underlying,
                    "CE",
                )
            )

            ce_contract = (
                _normalize_kotak_contract(
                    ce_resolved,
                    "CE",
                )
            )

        if (
            ce_contract is None
            and pe_contract is None
        ):

            return {
                "success": False,
                "error": (
                    "Kotak CE/PE contracts "
                    "could not be resolved"
                ),
            }

        # ----------------------------------------------------
        # Quotes
        # ----------------------------------------------------

        quote_result = (
            _get_kotak_option_quotes(
                ce_contract,
                pe_contract,
            )
        )

        if not quote_result.get(
            "success"
        ):

            return {
                "success": False,
                "error": quote_result.get(
                    "error",
                    "Kotak quote failed",
                ),
                "resolved": resolved,
                "CE_CONTRACT": ce_contract,
                "PE_CONTRACT": pe_contract,
            }

        ce_ltp = quote_result.get(
            "CE_LTP"
        )

        pe_ltp = quote_result.get(
            "PE_LTP"
        )

        selected_contract = None
        selected_ltp = None

        if option_type:

            requested_type = str(
                option_type
            ).upper().strip()

            if requested_type == "CE":

                selected_contract = (
                    ce_contract
                )

                selected_ltp = ce_ltp

            elif requested_type == "PE":

                selected_contract = (
                    pe_contract
                )

                selected_ltp = pe_ltp

        return {

            "success": True,

            "index": symbol,

            "underlying": underlying,

            "strike": (
                resolved.get(
                    "atm_strike"
                )
            ),

            "expiry": (
                resolved.get(
                    "expiry"
                )
            ),

            "CE": ce_ltp,

            "PE": pe_ltp,

            "CE_LTP": ce_ltp,

            "PE_LTP": pe_ltp,

            "CE_CONTRACT": ce_contract,

            "PE_CONTRACT": pe_contract,

            "CE_QUOTE": quote_result.get(
                "CE_QUOTE"
            ),

            "PE_QUOTE": quote_result.get(
                "PE_QUOTE"
            ),

            "CE_PRICE_SOURCE": (
                "KOTAK_NEO"
                if ce_ltp is not None
                else "UNAVAILABLE"
            ),

            "PE_PRICE_SOURCE": (
                "KOTAK_NEO"
                if pe_ltp is not None
                else "UNAVAILABLE"
            ),

            "option_type": (
                option_type
            ),

            "ltp": selected_ltp,

            "LTP": selected_ltp,

            "contract": (
                selected_contract
            ),
        }

    except Exception as exc:

        logger.exception(
            "Kotak resolved option price "
            "error: %s",
            exc,
        )

        return {
            "success": False,
            "error": str(exc),
        }


# ============================================================
# EXACT SELECTED OPTION LTP
# ============================================================

def get_exact_option_ltp(
    index_name: str,
    strike: Any,
    option_type: str,
    expiry: Any = None,
    underlying_price: Any = None,
) -> dict:

    try:

        requested_type = str(
            option_type
        ).upper().strip()

        if requested_type not in (
            "CE",
            "PE",
        ):

            return {
                "success": False,
                "error": (
                    "Option type must be "
                    "CE or PE"
                ),
            }

        symbol = normalize_symbol(
            index_name
        )

        if not symbol:

            return {
                "success": False,
                "error": "Invalid index",
            }

        # ----------------------------------------------------
        # Kotak path
        #
        # If underlying price is supplied,
        # resolver + live Kotak quote is primary.
        # ----------------------------------------------------

        if underlying_price is not None:

            kotak_result = (
                _get_kotak_resolved_prices(
                    symbol,
                    underlying_price,
                    requested_type,
                )
            )

            if kotak_result.get(
                "success"
            ):

                resolved_strike = (
                    _safe_float(
                        kotak_result.get(
                            "strike"
                        )
                    )
                )

                requested_strike = _safe_float(
                    strike
                )

                # If caller specifically requested
                # a strike and resolver ATM is different,
                # do not silently return the wrong strike.
                if (
                    requested_strike is not None
                    and resolved_strike is not None
                    and abs(
                        requested_strike
                        - resolved_strike
                    ) > 0.01
                ):

                    # Continue to NSE fallback below.
                    pass

                else:

                    ltp = _safe_float(
                        kotak_result.get(
                            "ltp"
                        )
                    )

                    if (
                        ltp is not None
                        and ltp > 0
                    ):

                        contract = (
                            kotak_result.get(
                                "contract"
                            )
                        )

                        return {

                            "success": True,

                            "index": symbol,

                            "option_type": (
                                requested_type
                            ),

                            "strike": (
                                kotak_result.get(
                                    "strike"
                                )
                            ),

                            "expiry": (
                                kotak_result.get(
                                    "expiry"
                                )
                            ),

                            "underlying": (
                                kotak_result.get(
                                    "underlying"
                                )
                            ),

                            "ltp": ltp,

                            "LTP": ltp,

                            "contract": contract,

                            "price_source": (
                                "KOTAK_NEO"
                            ),
                        }

        # ----------------------------------------------------
        # NSE fallback
        # ----------------------------------------------------

        if symbol == "SENSEX":

            return {
                "success": False,
                "error": (
                    "SENSEX exact option LTP "
                    "requires Kotak underlying "
                    "price or broker data."
                ),
            }

        chain_data = get_option_chain(
            symbol
        )

        if not chain_data:

            return {
                "success": False,
                "error": (
                    "Option-chain data unavailable"
                ),
            }

        if "error" in chain_data:

            return {
                "success": False,
                "error": chain_data[
                    "error"
                ],
            }

        result = extract_option_prices(
            chain_data,
            strike=strike,
            expiry=expiry,
        )

        if "error" in result:

            return {
                "success": False,
                "error": result[
                    "error"
                ],
            }

        contract_key = (
            "CE_CONTRACT"
            if requested_type == "CE"
            else "PE_CONTRACT"
        )

        contract = result.get(
            contract_key
        )

        if not isinstance(
            contract,
            dict,
        ):

            return {
                "success": False,
                "error": (
                    f"{requested_type} "
                    "contract unavailable"
                ),
            }

        ltp = _safe_float(
            contract.get(
                "ltp"
            )
        )

        if (
            ltp is None
            or ltp <= 0
        ):

            return {
                "success": False,
                "error": (
                    f"{requested_type} LTP "
                    f"unavailable for strike "
                    f"{strike}. "
                    f"Price source: "
                    f"{contract.get('price_source')}"
                ),
            }

        return {

            "success": True,

            "index": symbol,

            "option_type": requested_type,

            "strike": result.get(
                "strike"
            ),

            "expiry": result.get(
                "expiry"
            ),

            "underlying": result.get(
                "underlying"
            ),

            "ltp": ltp,

            "LTP": ltp,

            "contract": contract,

            "price_source": contract.get(
                "price_source"
            ),
        }

    except Exception as exc:

        logger.exception(
            "Exact option LTP error"
        )

        return {
            "success": False,
            "error": str(exc),
        }


# ============================================================
# GET BOTH CE / PE FOR EXACT STRIKE
# ============================================================

def get_exact_option_prices(
    index_name: str,
    strike: Any,
    expiry: Any = None,
    underlying_price: Any = None,
) -> dict:

    try:

        symbol = normalize_symbol(
            index_name
        )

        if not symbol:

            return {
                "success": False,
                "error": "Invalid index",
            }

        # ====================================================
        # KOTAK PRIMARY PATH
        # ====================================================

        if underlying_price is not None:

            kotak_result = (
                _get_kotak_resolved_prices(
                    symbol,
                    underlying_price,
                    None,
                )
            )

            if kotak_result.get(
                "success"
            ):

                kotak_strike = _safe_float(
                    kotak_result.get(
                        "strike"
                    )
                )

                requested_strike = _safe_float(
                    strike
                )

                # --------------------------------------------
                # Use Kotak only when strike matches requested
                # strike. This prevents an ATM result from
                # silently replacing a manually selected strike.
                # --------------------------------------------

                strike_matches = (
                    requested_strike is None
                    or kotak_strike is None
                    or abs(
                        requested_strike
                        - kotak_strike
                    ) < 0.01
                )

                # Expiry check
                expiry_matches = True

                if expiry is not None:

                    resolved_expiry = (
                        kotak_result.get(
                            "expiry"
                        )
                    )

                    if resolved_expiry:

                        expiry_matches = (
                            _expiry_key(
                                expiry
                            )
                            == _expiry_key(
                                resolved_expiry
                            )
                        )

                if (
                    strike_matches
                    and expiry_matches
                ):

                    return {

                        "success": True,

                        "index": symbol,

                        "strike": (
                            kotak_result.get(
                                "strike"
                            )
                        ),

                        "expiry": (
                            kotak_result.get(
                                "expiry"
                            )
                        ),

                        "underlying": (
                            kotak_result.get(
                                "underlying"
                            )
                        ),

                        "CE": (
                            kotak_result.get(
                                "CE_LTP"
                            )
                        ),

                        "PE": (
                            kotak_result.get(
                                "PE_LTP"
                            )
                        ),

                        "CE_LTP": (
                            kotak_result.get(
                                "CE_LTP"
                            )
                        ),

                        "PE_LTP": (
                            kotak_result.get(
                                "PE_LTP"
                            )
                        ),

                        "CE_CONTRACT": (
                            kotak_result.get(
                                "CE_CONTRACT"
                            )
                        ),

                        "PE_CONTRACT": (
                            kotak_result.get(
                                "PE_CONTRACT"
                            )
                        ),

                        "CE_QUOTE": (
                            kotak_result.get(
                                "CE_QUOTE"
                            )
                        ),

                        "PE_QUOTE": (
                            kotak_result.get(
                                "PE_QUOTE"
                            )
                        ),

                        "CE_PRICE_SOURCE": (
                            kotak_result.get(
                                "CE_PRICE_SOURCE"
                            )
                        ),

                        "PE_PRICE_SOURCE": (
                            kotak_result.get(
                                "PE_PRICE_SOURCE"
                            )
                        ),

                        "available_expiries": [],

                    }

        # ====================================================
        # NSE FALLBACK
        # ====================================================

        if symbol == "SENSEX":

            return {
                "success": False,
                "error": (
                    "SENSEX requires Kotak "
                    "broker data with a valid "
                    "underlying price."
                ),
            }

        chain_data = get_option_chain(
            symbol
        )

        if not chain_data:

            return {
                "success": False,
                "error": (
                    "Option-chain data unavailable"
                ),
            }

        if "error" in chain_data:

            return {
                "success": False,
                "error": chain_data[
                    "error"
                ],
            }

        result = extract_option_prices(
            chain_data,
            strike=strike,
            expiry=expiry,
        )

        if not result:

            return {
                "success": False,
                "error": (
                    "Could not extract "
                    "option prices"
                ),
            }

        if "error" in result:

            return {
                "success": False,
                "error": result[
                    "error"
                ],
            }

        ce_contract = result.get(
            "CE_CONTRACT"
        )

        pe_contract = result.get(
            "PE_CONTRACT"
        )

        ce_price = _safe_float(
            result.get(
                "CE"
            )
        )

        pe_price = _safe_float(
            result.get(
                "PE"
            )
        )

        if (
            ce_price is None
            and pe_price is None
        ):

            return {

                "success": False,

                "error": (
                    "CE and PE LTP "
                    "unavailable for strike "
                    f"{result.get('strike')} "
                    f"expiry "
                    f"{result.get('expiry')}. "
                    f"CE source="
                    f"{result.get('CE_PRICE_SOURCE')}, "
                    f"PE source="
                    f"{result.get('PE_PRICE_SOURCE')}"
                ),

                "index": symbol,

                "strike": result.get(
                    "strike"
                ),

                "expiry": result.get(
                    "expiry"
                ),

                "underlying": result.get(
                    "underlying"
                ),
            }

        return {

            "success": True,

            "index": symbol,

            "strike": result.get(
                "strike"
            ),

            "expiry": result.get(
                "expiry"
            ),

            "underlying": result.get(
                "underlying"
            ),

            "CE": ce_price,

            "PE": pe_price,

            "CE_LTP": ce_price,

            "PE_LTP": pe_price,

            "CE_CONTRACT": ce_contract,

            "PE_CONTRACT": pe_contract,

            "CE_PRICE_SOURCE": result.get(
                "CE_PRICE_SOURCE"
            ),

            "PE_PRICE_SOURCE": result.get(
                "PE_PRICE_SOURCE"
            ),

            "available_expiries": (
                result.get(
                    "available_expiries",
                    [],
                )
            ),
        }

    except Exception as exc:

        logger.exception(
            "Exact CE/PE price error"
        )

        return {
            "success": False,
            "error": str(exc),
        }


# ============================================================
# GET ATM OPTION PRICES
# ============================================================

def get_atm_option_prices(
    index_name: str,
    expiry: Any = None,
    underlying_price: Any = None,
) -> dict:

    try:

        # ----------------------------------------------------
        # If dashboard provides underlying price,
        # Kotak becomes primary.
        # ----------------------------------------------------

        if underlying_price is not None:

            result = (
                _get_kotak_resolved_prices(
                    index_name,
                    underlying_price,
                    None,
                )
            )

            if result.get(
                "success"
            ):

                return result

        # ----------------------------------------------------
        # NSE fallback
        # ----------------------------------------------------

        return get_exact_option_prices(
            index_name=index_name,
            strike=None,
            expiry=expiry,
            underlying_price=(
                underlying_price
            ),
        )

    except Exception as exc:

        logger.exception(
            "ATM option price error"
        )

        return {
            "success": False,
            "error": str(exc),
        }


# ============================================================
# KOTAK DIRECT ATM TEST HELPER
# ============================================================

def get_kotak_atm_option_prices(
    index_name: str,
    underlying_price: Any,
) -> dict:
    """
    Direct helper for dashboard.

    Example:

        get_kotak_atm_option_prices(
            "NIFTY",
            23398.10
        )
    """

    return _get_kotak_resolved_prices(
        index_name=index_name,
        underlying_price=underlying_price,
        option_type=None,
    )


# ============================================================
# SCAN ALL OPTION CHAINS
# ============================================================

def scan_all_option_chain(
    underlying_prices: Optional[dict] = None,
) -> dict:
    """
    Scan supported indices.

    If underlying_prices is supplied:

        {
            "NIFTY": 23398.10,
            "BANKNIFTY": 50000.00,
            ...
        }

    then Kotak is used as primary source.

    No order is placed.
    """

    results = {}

    supported_indices = [
        "NIFTY",
        "BANKNIFTY",
        "FINNIFTY",
        "MIDCPNIFTY",
        "SENSEX",
    ]

    if not isinstance(
        underlying_prices,
        dict,
    ):
        underlying_prices = {}

    for index_name in supported_indices:

        try:

            underlying = (
                underlying_prices.get(
                    index_name
                )
            )

            # ------------------------------------------------
            # Kotak primary
            # ------------------------------------------------

            if underlying is not None:

                result = (
                    get_atm_option_prices(
                        index_name,
                        underlying_price=(
                            underlying
                        ),
                    )
                )

            else:

                result = (
                    get_atm_option_prices(
                        index_name
                    )
                )

            if result.get(
                "success"
            ):

                results[index_name] = {

                    "success": True,

                    "CE": result.get(
                        "CE"
                    ),

                    "PE": result.get(
                        "PE"
                    ),

                    "CE_LTP": result.get(
                        "CE_LTP"
                    ),

                    "PE_LTP": result.get(
                        "PE_LTP"
                    ),

                    "strike": result.get(
                        "strike"
                    ),

                    "expiry": result.get(
                        "expiry"
                    ),

                    "underlying": result.get(
                        "underlying"
                    ),

                    "CE_CONTRACT": result.get(
                        "CE_CONTRACT"
                    ),

                    "PE_CONTRACT": result.get(
                        "PE_CONTRACT"
                    ),

                    "CE_QUOTE": result.get(
                        "CE_QUOTE"
                    ),

                    "PE_QUOTE": result.get(
                        "PE_QUOTE"
                    ),

                    "CE_PRICE_SOURCE": (
                        result.get(
                            "CE_PRICE_SOURCE"
                        )
                    ),

                    "PE_PRICE_SOURCE": (
                        result.get(
                            "PE_PRICE_SOURCE"
                        )
                    ),
                }

            else:

                results[index_name] = {

                    "success": False,

                    "error": result.get(
                        "error",
                        "Unknown "
                        "option-chain error",
                    ),
                }

            time.sleep(
                0.25
            )

        except Exception as exc:

            logger.exception(
                "Option scan failed "
                "for %s",
                index_name,
            )

            results[index_name] = {

                "success": False,

                "error": str(
                    exc
                ),
            }

    return results


# ============================================================
# SIMPLE CONTRACT VALIDATION
# ============================================================

def validate_option_result(
    result: dict,
    option_type: str,
) -> tuple[bool, str]:

    if not isinstance(
        result,
        dict,
    ):

        return (
            False,
            "Invalid option result",
        )

    if not result.get(
        "success"
    ):

        return (
            False,
            result.get(
                "error",
                "Option result "
                "unsuccessful",
            ),
        )

    option_type = str(
        option_type
    ).upper().strip()

    if option_type not in (
        "CE",
        "PE",
    ):

        return (
            False,
            "Invalid option type",
        )

    ltp = _safe_float(
        result.get(
            "ltp"
        )
    )

    if (
        ltp is None
        or ltp <= 0
    ):

        return (
            False,
            "Invalid option LTP",
        )

    strike = _safe_float(
        result.get(
            "strike"
        )
    )

    if (
        strike is None
        or strike <= 0
    ):

        return (
            False,
            "Invalid strike",
        )

    expiry = result.get(
        "expiry"
    )

    if not expiry:

        return (
            False,
            "Expiry unavailable",
        )

    return (
        True,
        "",
    )


# ============================================================
# DIRECT TEST
# ============================================================

if __name__ == "__main__":

    print()
    print("=" * 70)
    print(
        "JHA SMARTTRADER AI PRO"
    )
    print(
        "KOTAK + NSE OPTION CHAIN TEST"
    )
    print("=" * 70)
    print()

    # --------------------------------------------------------
    # IMPORTANT:
    # This underlying price is only for direct testing.
    #
    # It does NOT place an order.
    # --------------------------------------------------------

    test_underlying = 23398.10

    print(
        "Testing NIFTY ATM..."
    )

    print(
        "Underlying :",
        test_underlying,
    )

    print()

    test = get_atm_option_prices(
        "NIFTY",
        underlying_price=test_underlying,
    )

    print(
        "RESULT:"
    )

    print(test)

    print()

    if test.get(
        "success"
    ):

        print(
            "=" * 50
        )

        print(
            "OPTION PRICE RESULT"
        )

        print(
            "=" * 50
        )

        print(
            "Index      :",
            test.get(
                "index"
            ),
        )

        print(
            "Underlying :",
            test.get(
                "underlying"
            ),
        )

        print(
            "Strike     :",
            test.get(
                "strike"
            ),
        )

        print(
            "Expiry     :",
            test.get(
                "expiry"
            ),
        )

        print(
            "CE LTP     :",
            test.get(
                "CE_LTP"
            ),
        )

        print(
            "PE LTP     :",
            test.get(
                "PE_LTP"
            ),
        )

        print(
            "CE Source  :",
            test.get(
                "CE_PRICE_SOURCE"
            ),
        )

        print(
            "PE Source  :",
            test.get(
                "PE_PRICE_SOURCE"
            ),
        )

        ce_contract = test.get(
            "CE_CONTRACT"
        )

        pe_contract = test.get(
            "PE_CONTRACT"
        )

        print()

        print(
            "CE Symbol  :",
            (
                ce_contract.get(
                    "trading_symbol"
                )
                if isinstance(
                    ce_contract,
                    dict,
                )
                else None
            ),
        )

        print(
            "CE Token   :",
            (
                ce_contract.get(
                    "token"
                )
                if isinstance(
                    ce_contract,
                    dict,
                )
                else None
            ),
        )

        print(
            "PE Symbol  :",
            (
                pe_contract.get(
                    "trading_symbol"
                )
                if isinstance(
                    pe_contract,
                    dict,
                )
                else None
            ),
        )

        print(
            "PE Token   :",
            (
                pe_contract.get(
                    "token"
                )
                if isinstance(
                    pe_contract,
                    dict,
                )
                else None
            ),
        )

        print(
            "=" * 50
        )

    else:

        print(
            "❌ OPTION PRICE ERROR"
        )

        print(
            test.get(
                "error",
                "Unknown error",
            )
        )

    print()

    print(
        "=" * 70
    )