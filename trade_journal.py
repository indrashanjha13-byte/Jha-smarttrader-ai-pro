import pandas as pd
import os
from datetime import datetime

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

    trade = {
        "Date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Symbol": symbol,
        "Action": action,
        "Entry": entry,
        "Exit": exit_price,
        "StopLoss": stoploss,
        "Target": target,
        "Quantity": qty,
        "PNL": pnl,
        "Strategy": strategy,
        "Confidence": confidence,
        "AI Score": score,
        "Market Regime": regime,
        "Reason": reason,
        "Result": result
    }

    if os.path.exists(FILE_NAME):
        df = pd.read_csv(FILE_NAME)
    else:
        df = pd.DataFrame()

    df = pd.concat([df, pd.DataFrame([trade])], ignore_index=True)

    df.to_csv(FILE_NAME, index=False)

def update_last_trade(result):

    if not os.path.exists(FILE_NAME):
        return

    df = pd.read_csv(FILE_NAME)

    if len(df) == 0:
        return

    df.loc[df.index[-1], "Result"] = result

    df.to_csv(FILE_NAME, index=False)
