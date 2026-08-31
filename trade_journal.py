import os
import logging
from datetime import datetime
import pandas as pd

FILE_NAME = "trade_journal.csv"


def save_trade(
    symbol,
    action,
    entry,
    exit_price,
    stoploss,
    target,
    qty,
    confidence,
    score,
    regime,
    strategy,
    pnl,
    reason,
    result="OPEN"
):
    """
    Appends a new trade record with complete AI parameters and status 
    into the trade journal CSV.
    """
    try:
        trade = {
            "Date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Symbol": str(symbol).strip().upper(),
            "Action": str(action).strip().upper(),
            "Entry": float(entry or 0.0),
            "Exit": float(exit_price or 0.0),
            "StopLoss": float(stoploss or 0.0),
            "Target": float(target or 0.0),
            "Quantity": int(qty or 0),
            "PNL": float(pnl or 0.0),
            "Strategy": str(strategy),
            "Confidence": float(confidence or 0.0),
            "AI Score": float(score or 0.0),
            "Market Regime": str(regime),
            "Reason": str(reason),
            "Result": str(result).strip().upper()
        }

        # Load existing journal or create new dataframe
        if os.path.exists(FILE_NAME):
            try:
                df = pd.read_csv(FILE_NAME)
            except Exception:
                df = pd.DataFrame()
        else:
            df = pd.DataFrame()

        new_row_df = pd.DataFrame([trade])
        df = pd.concat([df, new_row_df], ignore_index=True)

        # Save back to CSV securely
        df.to_csv(FILE_NAME, index=False)
        logging.info(f"📝 Trade successfully saved to journal for {symbol} ({action})")

    except Exception as e:
        logging.error(f"❌ Error saving trade to journal: {e}")


def update_last_trade(result):
    """
    Updates the result status (e.g. WIN, LOSS, CLOSED) of the most recent trade in the journal.
    """
    try:
        if not os.path.exists(FILE_NAME):
            logging.warning(f"⚠️ Journal file '{FILE_NAME}' not found for updating.")
            return

        df = pd.read_csv(FILE_NAME)

        if df is None or df.empty:
            return

        # Update result of the last record
        df.loc[df.index[-1], "Result"] = str(result).strip().upper()

        df.to_csv(FILE_NAME, index=False)
        logging.info(f"🔄 Last trade result updated to: {result}")

    except Exception as e:
        logging.error(f"❌ Error updating last trade result: {e}")