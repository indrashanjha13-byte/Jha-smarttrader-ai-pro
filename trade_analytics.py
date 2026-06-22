import pandas as pd

df = pd.read_csv(
    "trade_history.csv"
)

total_trades = len(df)

winning_trades = len(
    df[df["PnL"] > 0]
)

win_rate = (
    winning_trades /
    total_trades
) * 100
df["Equity"] = (
    df["PnL"].cumsum()
)
