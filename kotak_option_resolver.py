import os
from datetime import datetime

from decouple import config
from neo_api_client import NeoAPI


# ============================================================
# KOTAK NEO CONFIG
# ============================================================

CONSUMER_KEY = config("KOTAK_CONSUMER_KEY", default="")

if not CONSUMER_KEY:
    raise RuntimeError(
        "KOTAK_CONSUMER_KEY is not configured in .env"
    )


neo = NeoAPI(
    consumer_key=CONSUMER_KEY,
    environment="prod",
)


# ============================================================
# INDEX CONFIG
# ============================================================

INDEX_CONFIG = {
    "NIFTY": {
        "strike_step": 50,
        "lot_size": 65,
    },
    "BANKNIFTY": {
        "strike_step": 100,
        "lot_size": 30,
    },
    "FINNIFTY": {
        "strike_step": 50,
        "lot_size": 60,
    },
    "MIDCPNIFTY": {
        "strike_step": 25,
        "lot_size": 120,
    },
    "SENSEX": {
        "strike_step": 100,
        "lot_size": 20,
    },
}


# ============================================================
# STRIKE NORMALIZER
# ============================================================

def normalize_strike(value):
    """
    Kotak returns dStrikePrice; like:

        2375000.0 -> 23750.0
    """

    try:
        value = float(value)

        if value > 100000:
            return value / 100

        return value

    except Exception:
        return None


# ============================================================
# EXPIRY PARSER
# ============================================================

def parse_expiry(value):

    try:
        return datetime.strptime(
            str(value),
            "%d%b%Y"
        )

    except Exception:
        return None


# ============================================================
# ATM CALCULATOR
# ============================================================

def calculate_atm(price, strike_step):

    price = float(price)

    return round(
        price / strike_step
    ) * strike_step


# ============================================================
# LOAD KOTAK OPTION MASTER
# ============================================================

def get_option_master(index_name):

    index_name = index_name.upper().strip()

    records = neo.search_scrip(
        exchange_segment="nse_fo",
        symbol=index_name,
        ignore_50multiple=False,
    )

    if not isinstance(records, list):

        raise RuntimeError(
            f"Kotak search_scrip returned unexpected data: {records}"
        )

    options = []

    for item in records:

        # Exact underlying only.
        # This prevents NIFTYFPI etc.
        if item.get("pSymbolName") != index_name:
            continue

        # Only index options.
        if item.get("pInstType") != "OPTIDX":
            continue

        option_type = item.get("pOptionType")

        if option_type not in ("CE", "PE"):
            continue

        expiry_raw = item.get("pExpiryDate")

        expiry_date = parse_expiry(
            expiry_raw
        )

        if expiry_date is None:
            continue

        strike = normalize_strike(
            item.get("dStrikePrice;")
        )

        if strike is None:
            continue

        item["_expiry_date"] = expiry_date
        item["_strike"] = strike

        options.append(item)

    return options


# ============================================================
# RESOLVE ATM OPTION
# ============================================================

def resolve_atm_option(
    index_name,
    current_price,
    option_mode="CE",
):

    index_name = index_name.upper().strip()
    option_mode = option_mode.upper().strip()

    if index_name not in INDEX_CONFIG:

        raise ValueError(
            f"Unsupported index: {index_name}"
        )

    if option_mode not in ("CE", "PE", "ALL"):

        raise ValueError(
            "option_mode must be CE, PE or ALL"
        )

    index_config = INDEX_CONFIG[index_name]

    strike_step = index_config["strike_step"]

    # --------------------------------------------------------
    # ATM STRIKE
    # --------------------------------------------------------

    atm_strike = calculate_atm(
        current_price,
        strike_step,
    )

    # --------------------------------------------------------
    # OPTION MASTER
    # --------------------------------------------------------

    options = get_option_master(
        index_name
    )

    if not options:

        raise RuntimeError(
            f"No {index_name} option contracts found."
        )

    # --------------------------------------------------------
    # FUTURE EXPIRIES
    # --------------------------------------------------------

    today = datetime.now().date()

    expiries = sorted(
        {
            item["_expiry_date"]
            for item in options
            if item["_expiry_date"].date() >= today
        }
    )

    if not expiries:

        raise RuntimeError(
            f"No future expiry found for {index_name}."
        )

    selected_expiry = expiries[0]

    # --------------------------------------------------------
    # RESULT
    # --------------------------------------------------------

    result = {

        "index": index_name,

        "underlying_price": float(
            current_price
        ),

        "atm_strike": float(
            atm_strike
        ),

        "expiry": selected_expiry.strftime(
            "%d%b%Y"
        ),

        "exchange_segment": "nse_fo",

        "contracts": {},
    }

    # --------------------------------------------------------
    # FIND ATM CE / PE
    # --------------------------------------------------------

    for item in options:

        if item["_expiry_date"] != selected_expiry:
            continue

        if abs(
            item["_strike"] - atm_strike
        ) > 0.001:
            continue

        item_option_type = item.get(
            "pOptionType"
        )

        if option_mode != "ALL":

            if item_option_type != option_mode:
                continue

        # IMPORTANT:
        # Kotak token field is pSymbol.
        token = item.get("pSymbol")

        if token is None:

            raise RuntimeError(
                f"Kotak token missing for "
                f"{item.get('pTrdSymbol')}"
            )

        contract = {

            "trading_symbol": item.get(
                "pTrdSymbol"
            ),

            "token": int(token),

            "strike": float(
                item["_strike"]
            ),

            "expiry": item.get(
                "pExpiryDate"
            ),

            "lot_size": int(
                item.get("lLotSize")
                or item.get("iLotSize")
                or index_config["lot_size"]
            ),

            "exchange_segment": item.get(
                "pExchSeg",
                "nse_fo",
            ),

            "instrument": item.get(
                "pInstType",
                "OPTIDX",
            ),

            "option_type": item_option_type,
        }

        result["contracts"][
            item_option_type
        ] = contract

    # --------------------------------------------------------
    # VALIDATION
    # --------------------------------------------------------

    if option_mode == "CE":

        if "CE" not in result["contracts"]:

            raise RuntimeError(
                f"ATM CE contract not found for "
                f"{index_name}"
            )

    elif option_mode == "PE":

        if "PE" not in result["contracts"]:

            raise RuntimeError(
                f"ATM PE contract not found for "
                f"{index_name}"
            )

    elif option_mode == "ALL":

        if not result["contracts"]:

            raise RuntimeError(
                f"ATM CE/PE contracts not found for "
                f"{index_name}"
            )

    return result


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    print("=" * 70)
    print("KOTAK NEO - SMARTTRADER OPTION RESOLVER")
    print("=" * 70)

    test_price = 23769.80

    result = resolve_atm_option(
        index_name="NIFTY",
        current_price=test_price,
        option_mode="ALL",
    )

    print()

    print(
        "Index          :",
        result["index"]
    )

    print(
        "Current Price  :",
        result["underlying_price"]
    )

    print(
        "ATM Strike     :",
        result["atm_strike"]
    )

    print(
        "Expiry         :",
        result["expiry"]
    )

    print()

    for option_type, contract in result[
        "contracts"
    ].items():

        print("-" * 70)

        print(option_type)

        print(
            "Trading Symbol :",
            contract["trading_symbol"]
        )

        print(
            "Token          :",
            contract["token"]
        )

        print(
            "Strike         :",
            contract["strike"]
        )

        print(
            "Expiry         :",
            contract["expiry"]
        )

        print(
            "Lot Size       :",
            contract["lot_size"]
        )

        print(
            "Exchange       :",
            contract["exchange_segment"]
        )

        print(
            "Instrument     :",
            contract["instrument"]
        )

    print()

    print("=" * 70)
    print("SMARTTRADER OPTION RESOLVER TEST COMPLETE")
    print("=" * 70)
