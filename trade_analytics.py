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

        win_rate = 0

        if total_trades > 0:
            win_rate = round(
                (sell_trades / total_trades) * 100,
                2
            )

        return {
            "total": total_trades,
            "buy": buy_trades,
            "sell": sell_trades,
            "win_rate": win_rate
        }

    except:
        return {
            "total": 0,
            "buy": 0,
            "sell": 0,
            "win_rate": 0
        }
