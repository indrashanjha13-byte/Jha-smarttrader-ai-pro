import pandas as pd

def backtest(data):

    balance = 100000

    trades = []

    return balance, trades


def performance(trades):

    if len(trades) == 0:

        return {
            "total": 0,
            "wins": 0,
            "losses": 0,
            "net_profit": 0,
            "win_rate": 0,
            "profit_factor": 0
        }

    df = pd.DataFrame(trades)

    total = len(df)

    wins = len(df[df["PnL"] > 0])

    losses = len(df[df["PnL"] <= 0])

    net_profit = round(df["PnL"].sum(), 2)

    gross_profit = df[df["PnL"] > 0]["PnL"].sum()

    gross_loss = abs(df[df["PnL"] < 0]["PnL"].sum())

    profit_factor = round(
        gross_profit / gross_loss,
        2
    ) if gross_loss > 0 else 999

    win_rate = round(
        wins / total * 100,
        2
    )

    return {
        "total": total,
        "wins": wins,
        "losses": losses,
        "net_profit": net_profit,
        "win_rate": win_rate,
        "profit_factor": profit_factor
    }