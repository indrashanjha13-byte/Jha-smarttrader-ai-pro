import pandas as pd
import os
import logging


def get_trade_stats(csv_path="trade_history.csv"):
    """
    Reads trade history CSV and computes core trading statistics 
    like total trades, buy/sell breakdown, and win rate.
    """
    default_stats = {
        "total": 0,
        "buy": 0,
        "sell": 0,
        "win_rate": 0.0
    }

    try:
        # Check if CSV file exists
        if not os.path.exists(csv_path):
            logging.info(f"ℹ️ Trade history file '{csv_path}' not found. Returning default stats.")
            return default_stats

        df = pd.read_csv(csv_path)

        if df is None or df.empty:
            return default_stats

        # Standardize column names to uppercase/proper keys if needed
        # Ensuring required columns exist
        required_cols = ["Action", "PNL"]
        for col in required_cols:
            if col not in df.columns:
                logging.warning(f"⚠️ Required column '{col}' missing from trade history CSV.")
                return default_stats

        total_trades = len(df)
        
        # Count BUY and SELL actions safely
        buy_trades = int((df["Action"].astype(str).str.upper() == "BUY").sum())
        sell_trades = int((df["Action"].astype(str).str.upper() == "SELL").sum())

        # Count Winning trades (PNL > 0)
        df["PNL"] = pd.to_numeric(df["PNL"], errors="coerce").fillna(0.0)
        wins = int((df["PNL"] > 0).sum())

        win_rate = round((wins / total_trades) * 100.0, 2) if total_trades > 0 else 0.0

        return {
            "total": total_trades,
            "buy": buy_trades,
            "sell": sell_trades,
            "win_rate": win_rate
        }

    except Exception as e:
        logging.error(f"❌ Error reading trade stats from CSV: {e}")
        return default_stats