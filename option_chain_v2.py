import yfinance as yf
import pandas as pd
import logging


def get_option_chain_summary(symbol="^NSEI"):
    """
    Get underlying Spot and ATM strike.

    Actual CE/PE option premium will be supplied
    separately from the option-chain/broker data source.
    """

    try:

        df = yf.download(
            symbol,
            period="5d",
            interval="15m",
            progress=False,
            auto_adjust=False
        )

        if df is None or df.empty:
            logging.warning(
                f"⚠️ No price data found for symbol: {symbol}"
            )
            return {
                "error": "No Data Available"
            }

        # -------------------------------------------------
        # Flatten MultiIndex
        # -------------------------------------------------

        if isinstance(df.columns, pd.MultiIndex):

            df.columns = [
                col[0]
                for col in df.columns
            ]

        # -------------------------------------------------
        # Close Check
        # -------------------------------------------------

        if "Close" not in df.columns:

            return {
                "error": (
                    "'Close' price column missing "
                    "from downloaded data"
                )
            }

        close_series = (
            df["Close"]
            .dropna()
        )

        if close_series.empty:

            return {
                "error": "Empty Close price series"
            }

        # -------------------------------------------------
        # Spot
        # -------------------------------------------------

        spot = float(
            close_series.iloc[-1]
        )

        # -------------------------------------------------
        # Index Name
        # -------------------------------------------------

        s_upper = str(
            symbol
        ).upper()

        # -------------------------------------------------
        # Strike Step
        # -------------------------------------------------

        if "NSEBANK" in s_upper:

            strike_diff = 100

        elif (
            "BSESN" in s_upper
            or "SENSEX" in s_upper
        ):

            strike_diff = 100

        elif (
            "NSEI" in s_upper
            or "NIFTY" in s_upper
        ):

            strike_diff = 50

        elif "CNXFINANCE" in s_upper:

            strike_diff = 50

        elif "NSEMDCP50" in s_upper:

            strike_diff = 25

        else:

            strike_diff = 5

        # -------------------------------------------------
        # ATM
        # -------------------------------------------------

        atm = round(
            spot / strike_diff
        ) * strike_diff

        # -------------------------------------------------
        # Result
        # -------------------------------------------------

        return {

            "Symbol": symbol,

            "Spot": round(
                spot,
                2
            ),

            "ATM": int(
                atm
            ),

            # Actual premiums will be
            # connected next.
            "CE_Premium": None,

            "PE_Premium": None,

            "CE_Contract": None,

            "PE_Contract": None,

            "Signal": "Ready",

            "PCR": 0.0,

            "MaxPain": 0.0
        }

    except Exception as e:

        logging.exception(
            "❌ Error in get_option_chain_summary"
        )

        return {
            "error": str(e)
        }