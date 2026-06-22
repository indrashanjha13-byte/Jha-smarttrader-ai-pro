import pandas as pd

def get_trade_stats():

    try:
        df = pd.read_csv("trade_history.csv")

        total_trades = len(df)

        buy_trades = len(
            df[df["Side"] == "BUY"]
        )

        sell_trades = len(
            df[df["Side"] == "SELL"]
        )

        return {
            "total": total_trades,
            "buy": buy_trades,
            "sell": sell_trades
        }

    except:
        return {
            "total": 0,
            "buy": 0,
            "sell": 0
        }
