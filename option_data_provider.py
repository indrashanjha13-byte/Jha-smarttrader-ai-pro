"""
Option Data Provider
--------------------
Single source of truth for Indian index option data.

IMPORTANT:
- Never invent an option symbol.
- Never use underlying spot as option premium.
- Never return an option contract with LTP <= 0.
- Never allow expiry=None for a tradable contract.
- This module is PAPER-TRADING safe.
- Live broker mapping is intentionally NOT implemented here.
"""

from __future__ import annotations

import logging
from datetime import datetime, date
from typing import Any, Optional

from option_chain import get_exact_option_prices


logger = logging.getLogger(__name__)


SUPPORTED_INDICES = {
    "NIFTY",
    "BANKNIFTY",
    "FINNIFTY",
    "MIDCPNIFTY",
    "SENSEX",
}


def _safe_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None

        if isinstance(value, bool):
            return None

        value = float(value)

        if value != value:  # NaN
            return None

        return value
    except (TypeError, ValueError):
        return None


def _normalize_index(index_name: str) -> str:
    value = str(index_name or "").strip().upper()

    mapping = {
        "^NSEI": "NIFTY",
        "NSEI": "NIFTY",
        "NIFTY 50": "NIFTY",
        "NIFTY50": "NIFTY",

        "^NSEBANK": "BANKNIFTY",
        "NSEBANK": "BANKNIFTY",
        "BANK NIFTY": "BANKNIFTY",

        "^CNXFINANCE": "FINNIFTY",
        "CNXFINANCE": "FINNIFTY",
        "FINNIFTY": "FINNIFTY",

        "^NSEMDCP50": "MIDCPNIFTY",
        "NSEMDCP50": "MIDCPNIFTY",
        "MIDCAP NIFTY": "MIDCPNIFTY",
        "MIDCPNIFTY": "MIDCPNIFTY",

        "^BSESN": "SENSEX",
        "BSESN": "SENSEX",
        "SENSEX": "SENSEX",
    }

    return mapping.get(value, value)


def _normalize_option_type(option_type: str) -> str:
    value = str(option_type or "").strip().upper()

    if value in {"CALL", "C"}:
        return "CE"

    if value in {"PUT", "P"}:
        return "PE"

    return value


def _expiry_is_valid(expiry: Any) -> bool:
    if expiry is None:
        return False

    text = str(expiry).strip()

    if not text:
        return False

    invalid_values = {
        "NONE",
        "NULL",
        "N/A",
        "NA",
        "EXPIRY",
        "UNKNOWN",
        "WAITING",
    }

    return text.upper() not in invalid_values


def _normalize_contract(
    raw_contract: Any,
    index_name: str,
    option_type: str,
    requested_strike: Optional[float] = None,
) -> Optional[dict]:
    if not isinstance(raw_contract, dict):
        return None

    index_name = _normalize_index(index_name)
    option_type = _normalize_option_type(option_type)

    strike = _safe_float(
        raw_contract.get("strike")
        or raw_contract.get("strikePrice")
    )

    ltp = _safe_float(
        raw_contract.get("ltp")
        or raw_contract.get("lastPrice")
        or raw_contract.get("last_price")
    )

    expiry = raw_contract.get("expiry")

    if strike is None and requested_strike is not None:
        strike = _safe_float(requested_strike)

    # NEVER accept an invalid contract.
    if strike is None:
        logger.warning(
            "Option rejected: missing strike | %s %s",
            index_name,
            option_type,
        )
        return None

    if ltp is None or ltp <= 0:
        logger.warning(
            "Option rejected: invalid LTP | %s %s %.2f",
            index_name,
            option_type,
            strike,
        )
        return None

    if not _expiry_is_valid(expiry):
        logger.warning(
            "Option rejected: invalid expiry | %s %s %.2f",
            index_name,
            option_type,
            strike,
        )
        return None

    symbol = raw_contract.get("symbol")

    # Do not accept the old fake symbols such as:
    # NIFTYEXPIRY23400CE
    if symbol:
        symbol_text = str(symbol).strip()

        if "EXPIRY" in symbol_text.upper():
            symbol = None
        else:
            symbol = symbol_text

    result = {
        "index": index_name,
        "option_type": option_type,
        "strike": int(strike) if float(strike).is_integer() else strike,
        "expiry": expiry,
        "ltp": ltp,

        "bid": _safe_float(
            raw_contract.get("bid")
            or raw_contract.get("bidPrice")
        ),

        "ask": _safe_float(
            raw_contract.get("ask")
            or raw_contract.get("askPrice")
        ),

        "change": _safe_float(
            raw_contract.get("change")
        ),

        "change_percent": _safe_float(
            raw_contract.get("change_percent")
            or raw_contract.get("changePercent")
        ),

        "open_interest": _safe_float(
            raw_contract.get("open_interest")
            or raw_contract.get("openInterest")
        ),

        "volume": _safe_float(
            raw_contract.get("volume")
        ),

        "symbol": symbol,

        # Keep broker mapping fields separate.
        # They must never be guessed.
        "token": raw_contract.get("token"),
        "exchange": raw_contract.get("exchange"),
        "exchange_segment": raw_contract.get("exchange_segment"),

        "identifier": raw_contract.get("identifier"),

        "data_source": raw_contract.get(
            "data_source",
            "option_chain",
        ),

        "retrieved_at": datetime.now().isoformat(),
    }

    return result


def get_option_prices(
    index_name: str,
    strike: float,
    expiry: Optional[str] = None,
) -> dict:
    """
    Fetch exact CE + PE option prices.

    Returns:

    {
        "success": True/False,
        "index": "...",
        "strike": ...,
        "expiry": "...",
        "underlying": ...,
        "CE": {...},
        "PE": {...},
        "error": "..."
    }

    IMPORTANT:
    No fake contract is returned when source data is unavailable.
    """

    index_name = _normalize_index(index_name)

    if index_name not in SUPPORTED_INDICES:
        return {
            "success": False,
            "error": f"Unsupported option index: {index_name}",
        }

    strike_value = _safe_float(strike)

    if strike_value is None or strike_value <= 0:
        return {
            "success": False,
            "error": "Invalid option strike.",
        }

    try:
        raw = get_exact_option_prices(
            index_name=index_name,
            strike=int(strike_value),
            expiry=expiry,
        )
    except Exception as exc:
        logger.exception(
            "Option data provider error for %s",
            index_name,
        )

        return {
            "success": False,
            "error": f"Option data source error: {exc}",
        }

    if not isinstance(raw, dict):
        return {
            "success": False,
            "error": "Invalid option data response.",
        }

    if not raw.get("success"):
        return {
            "success": False,
            "index": index_name,
            "strike": int(strike_value),
            "error": raw.get(
                "error",
                "Option data unavailable.",
            ),
        }

    underlying = _safe_float(
        raw.get("underlying")
        or raw.get("underlyingValue")
    )

    actual_expiry = raw.get("expiry")

    if not _expiry_is_valid(actual_expiry):
        return {
            "success": False,
            "index": index_name,
            "strike": int(strike_value),
            "error": "Valid option expiry was not returned.",
        }

    ce_raw = raw.get("CE_CONTRACT")
    pe_raw = raw.get("PE_CONTRACT")

    ce = _normalize_contract(
        ce_raw,
        index_name,
        "CE",
        strike_value,
    )

    pe = _normalize_contract(
        pe_raw,
        index_name,
        "PE",
        strike_value,
    )

    if ce is None and pe is None:
        return {
            "success": False,
            "index": index_name,
            "strike": int(strike_value),
            "expiry": actual_expiry,
            "underlying": underlying,
            "error": "Neither CE nor PE has a valid LTP.",
        }

    result = {
        "success": True,
        "index": index_name,
        "strike": int(strike_value),
        "expiry": actual_expiry,
        "underlying": underlying,
        "CE": ce,
        "PE": pe,
        "retrieved_at": datetime.now().isoformat(),
    }

    return result


def get_single_option(
    index_name: str,
    strike: float,
    option_type: str,
    expiry: Optional[str] = None,
) -> dict:
    """
    Return one exact CE or PE contract.
    """

    option_type = _normalize_option_type(option_type)

    if option_type not in {"CE", "PE"}:
        return {
            "success": False,
            "error": "option_type must be CE or PE.",
        }

    result = get_option_prices(
        index_name=index_name,
        strike=strike,
        expiry=expiry,
    )

    if not result.get("success"):
        return result

    contract = result.get(option_type)

    if not contract:
        return {
            "success": False,
            "index": result.get("index"),
            "strike": result.get("strike"),
            "expiry": result.get("expiry"),
            "error": f"{option_type} contract unavailable.",
        }

    return {
        "success": True,
        "index": result.get("index"),
        "option_type": option_type,
        "strike": result.get("strike"),
        "expiry": result.get("expiry"),
        "underlying": result.get("underlying"),
        "contract": contract,
    }


def validate_option_contract(contract: Any) -> tuple[bool, str]:
    """
    Final safety validation before PaperTrader receives an option.
    """

    if not isinstance(contract, dict):
        return False, "Invalid contract."

    index_name = _normalize_index(
        contract.get("index")
    )

    if index_name not in SUPPORTED_INDICES:
        return False, "Unsupported index."

    option_type = _normalize_option_type(
        contract.get("option_type")
    )

    if option_type not in {"CE", "PE"}:
        return False, "Invalid option type."

    strike = _safe_float(contract.get("strike"))

    if strike is None or strike <= 0:
        return False, "Invalid strike."

    ltp = _safe_float(contract.get("ltp"))

    if ltp is None or ltp <= 0:
        return False, "Invalid option LTP."

    if not _expiry_is_valid(contract.get("expiry")):
        return False, "Valid expiry required."

    return True, "OK"


def get_provider_status() -> dict:
    """
    Diagnostic status for dashboard/debugging.
    """

    return {
        "provider": "option_data_provider",
        "supported_indices": sorted(SUPPORTED_INDICES),
        "live_broker_mapping": False,
        "fake_symbols_allowed": False,
        "zero_ltp_allowed": False,
        "expiry_required": True,
        "timestamp": datetime.now().isoformat(),
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    print(
        get_provider_status()
    )

    # Safe diagnostic test.
    # It will report unavailable if the underlying data source
    # is unavailable. It will NOT invent an LTP.
    result = get_option_prices(
        index_name="NIFTY",
        strike=23400,
    )

    print(result)
