from decouple import config
from neo_api_client import NeoAPI
from datetime import datetime


# ============================================================
# KOTAK NEO CONFIG
# ============================================================

consumer_key = config("KOTAK_CONSUMER_KEY", default="")

if not consumer_key:
    raise RuntimeError(
        "KOTAK_CONSUMER_KEY is not configured in .env"
    )

neo = NeoAPI(
    consumer_key=consumer_key,
    environment="prod",
)


# ============================================================
# SETTINGS
# ============================================================

UNDERLYING = "NIFTY"

OPTION_TYPE = "CE"

# Temporary test price.
# Later SmartTrader will get this automatically from market data.
CURRENT_PRICE = 23769.80


# NIFTY strike interval
STRIKE_STEP = 50


# ============================================================
# GET KOTAK CONTRACT MASTER
# ============================================================

print("=" * 70)
print("KOTAK NEO - NIFTY ATM OPTION RESOLVER")
print("=" * 70)

try:

    contracts = neo.search_scrip(
        exchange_segment="nse_fo",
        symbol="NIFTY",
        ignore_50multiple=False,
    )

    print("\nTotal records:", len(contracts))


    # ========================================================
    # ONLY REAL NIFTY OPTIONS
    # ========================================================

    options = [
        x for x in contracts
        if x.get("pSymbolName") == UNDERLYING
        and x.get("pInstType") == "OPTIDX"
        and x.get("pOptionType") in ("CE", "PE")
    ]

    print("Actual NIFTY options:", len(options))


    if not options:
        raise RuntimeError("No NIFTY option contracts found.")


    # ========================================================
    # EXPIRY PARSER
    # ========================================================

    def parse_expiry(value):

        return datetime.strptime(
            value,
            "%d%b%Y"
        )


    # ========================================================
    # FIND NEAREST VALID EXPIRY
    # ========================================================

    today = datetime.now()

    future_expiries = sorted(
        {
            parse_expiry(x["pExpiryDate"])
            for x in options
            if x.get("pExpiryDate")
            and parse_expiry(x["pExpiryDate"]) >= today
        }
    )


    if not future_expiries:
        raise RuntimeError("No future NIFTY expiry found.")


    nearest_expiry = future_expiries[0]

    expiry_text = nearest_expiry.strftime(
        "%d%b%Y"
    )


    print("\nCurrent Price :", CURRENT_PRICE)

    print(
        "Selected Expiry:",
        nearest_expiry.strftime("%d-%b-%Y")
    )


    # ========================================================
    # CALCULATE ATM STRIKE
    # ========================================================

    atm_strike = round(
        CURRENT_PRICE / STRIKE_STEP
    ) * STRIKE_STEP


    print("ATM Strike    :", atm_strike)


    # ========================================================
    # FIND CE + PE ATM CONTRACTS
    # ========================================================

    selected = {}

    for option_type in ("CE", "PE"):

        matches = []

        for x in options:

            if x.get("pOptionType") != option_type:
                continue

            if x.get("pExpiryDate") != expiry_text:
                continue

            raw_strike = x.get("dStrikePrice;")

            if raw_strike is None:
                continue

            # Kotak stores strike scaled by 100
            actual_strike = float(raw_strike) / 100

            if actual_strike == atm_strike:

                matches.append(x)


        if matches:

            selected[option_type] = matches[0]


    # ========================================================
    # DISPLAY RESULT
    # ========================================================

    print("\n" + "=" * 70)
    print("SELECTED ATM CONTRACTS")
    print("=" * 70)


    for option_type in ("CE", "PE"):

        contract = selected.get(option_type)

        if not contract:

            print(
                f"\n{option_type}: NOT FOUND"
            )

            continue


        raw_strike = float(
            contract.get("dStrikePrice;")
        )

        actual_strike = raw_strike / 100


        print(f"\n{option_type}")

        print(
            "Trading Symbol :",
            contract.get("pTrdSymbol")
        )

        print(
            "Token          :",
            contract.get("pSymbol")
        )

        print(
            "Strike         :",
            actual_strike
        )

        print(
            "Expiry         :",
            contract.get("pExpiryDate")
        )

        print(
            "Lot Size       :",
            contract.get("lLotSize")
        )

        print(
            "Exchange       :",
            contract.get("pExchSeg")
        )

        print(
            "Instrument     :",
            contract.get("pInstType")
        )


except Exception as e:

    print("\nERROR:")
    print(type(e).__name__)
    print(str(e))


print("\n" + "=" * 70)
print("ATM OPTION RESOLVER TEST COMPLETE")
print("=" * 70)
