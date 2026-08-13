import pandas as pd

def performance_summary(trades):

    if len(trades) == 0:
        return {
            "Total Trades": 0,
            "Winning Trades": 0,
            "Losing Trades": 0,
            "Net Profit": 0,
            "Win Rate": 0,
            "Profit Factor": 0,
            "Max Drawdown": 0
        }

    df = pd.DataFrame(trades)

    wins = len(df[df["PnL"] > 0])
    losses = len(df[df["PnL"] <= 0])

    gross_profit = df[df["PnL"] > 0]["PnL"].sum()
    gross_loss = abs(df[df["PnL"] < 0]["PnL"].sum())

    profit_factor = (
        round(gross_profit / gross_loss, 2)
        if gross_loss > 0 else 999
    )

    win_rate = round(
        (wins / len(df)) * 100,
        2
    )

    equity = df["PnL"].cumsum()
    drawdown = equity - equity.cummax()
    max_drawdown = round(abs(drawdown.min()), 2)

    return {
        "Total Trades": len(df),
        "Winning Trades": wins,
        "Losing Trades": losses,
        "Net Profit": round(df["PnL"].sum(), 2),
        "Win Rate": win_rate,
        "Profit Factor": profit_factor,
        "Max Drawdown": max_drawdown
    }