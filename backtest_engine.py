import pandas as pd


class BacktestEngine:

    def __init__(self):

        self.trades = []

        self.balance = 100000

        self.start_balance = 100000

    def add_trade(

        self,

        symbol,

        action,

        entry,

        exit_price,

        qty

    ):

        if action == "BUY":

            pnl = (exit_price - entry) * qty

        else:

            pnl = (entry - exit_price) * qty

        self.balance += pnl

        self.trades.append({

            "Symbol": symbol,

            "Action": action,

            "Entry": entry,

            "Exit": exit_price,

            "Qty": qty,

            "PnL": pnl

        })
    def summary(self):

        if len(self.trades) == 0:

            return {

                "Total Trades": 0,
                "Wins": 0,
                "Losses": 0,
                "Win Rate": 0,
                "Net Profit": 0,
                "Ending Balance": self.balance

            }

        df = pd.DataFrame(self.trades)

        wins = len(df[df["PnL"] > 0])

        losses = len(df[df["PnL"] <= 0])

        total = len(df)

        win_rate = round((wins / total) * 100, 2)

        net_profit = round(df["PnL"].sum(), 2)

        return {

            "Total Trades": total,
            "Wins": wins,
            "Losses": losses,
            "Win Rate": win_rate,
            "Net Profit": net_profit,
            "Ending Balance": round(self.balance, 2)

        }

    def dataframe(self):

        return pd.DataFrame(self.trades)
