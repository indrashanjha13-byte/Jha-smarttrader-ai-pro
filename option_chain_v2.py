import yfinance as yf
import pandas as pd

def get_option_chain_summary(symbol="^NSEI"):

    try:
        df = yf.download(
            symbol,
            period="5d",
            interval="15m",
            progress=False,
            auto_adjust=False
        )

        if df.empty:
            return {"error": "No Data"}

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        spot = float(df["Close"].iloc[-1])

        atm = round(spot / 50) * 50

        return {
            "Spot": round(spot, 2),
            "ATM": atm,
            "Signal": "Loading...",
            "PCR": 0,
            "MaxPain": 0
        }

    except Exception as e:
        return {
            "error": str(e)
        }