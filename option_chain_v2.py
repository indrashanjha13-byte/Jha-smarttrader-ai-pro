import yfinance as yf
import pandas as pd
import logging


def get_option_chain_summary(symbol="^NSEI"):
    """
    Fetches latest price data safely using yfinance and calculates ATM strike based on symbol type.
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
            logging.warning(f"⚠️ No price data found for symbol: {symbol}")
            return {"error": "No Data Available"}

        # Robust MultiIndex columns flattening
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0] for col in df.columns]

        # Check if 'Close' column exists
        if "Close" not in df.columns:
            return {"error": "'Close' price column missing from downloaded data"}

        # Drop NaN values in Close series
        close_series = df["Close"].dropna()
        if close_series.empty:
            return {"error": "Empty Close price series"}

        spot = float(close_series.iloc[-1])

        # Dynamic ATM Strike Rounding based on Symbol Type
        s_upper = str(symbol).upper()
        if "NSEBANK" in s_upper:
            strike_diff = 100  # Bank Nifty strikes are multiples of 100
        elif "BSESN" in s_upper or "SENSEX" in s_upper:
            strike_diff = 100  # Sensex strikes
        elif "NSEI" in s_upper or "NIFTY" in s_upper:
            strike_diff = 50   # Nifty strikes are multiples of 50
        else:
            strike_diff = 5    # Standard equities default rounding

        atm = round(spot / strike_diff) * strike_diff

        return {
            "Spot": round(spot, 2),
            "ATM": int(atm),
            "Signal": "Ready",
            "PCR": 0.0,
            "MaxPain": 0.0
        }

    except Exception as e:
        logging.error(f"❌ Error in get_option_chain_summary for {symbol}: {e}")
        return {
            "error": str(e)
        }