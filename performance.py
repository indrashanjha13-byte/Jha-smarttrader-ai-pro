import pandas as pd
import logging


def performance_summary(trades):
    """
    Computes professional trading performance metrics (Win Rate, Profit Factor, Drawdown) 
    safely from a list of trades or a pandas DataFrame.
    """
    try:
        # Check if trades is empty or None
        if not trades or len(trades) == 0:
            return {
                "Total Trades": 0,
                "Winning Trades": 0,
                "Losing Trades": 0,
                "Net Profit": 0.0,
                "Win Rate": 0.0,
                "Profit Factor": 0.0,
                "Max Drawdown": 0.0
            }

        # Convert to DataFrame if list/dict is passed
        df = pd.DataFrame(trades) if not isinstance(trades, pd.DataFrame) else trades.copy()

        # Validate required columns
        if "PnL" not in df.columns:
            logging.error("❌ 'PnL' column missing from trades data for performance summary.")
            return {"error": "'PnL' column missing"}

        # Ensure PnL is numeric
        df["PnL"] = pd.to_numeric(df["PnL"], errors="coerce").fillna(0.0)

        total_trades = len(df)
        if total_trades == 0:
            return {
                "Total Trades": 0, "Winning Trades": 0, "Losing Trades": 0,
                "Net Profit": 0.0, "Win Rate": 0.0, "Profit Factor": 0.0, "Max Drawdown": 0.0
            }

        # Accurate Win/Loss Classification (Strictly < 0 for loss, > 0 for win)
        wins = int((df["PnL"] > 0).sum())
        losses = int((df["PnL"] < 0).sum())
        breakeven = int((df["PnL"] == 0).sum())

        gross_profit = float(df[df["PnL"] > 0]["PnL"].sum())
        gross_loss = float(abs(df[df["PnL"] < 0]["PnL"].sum()))

        # Profit Factor Calculation with Zero Division Safeguard
        if gross_loss > 0:
            profit_factor = round(gross_profit / gross_loss, 2)
        else:
            profit_factor = 999.0 if gross_profit > 0 else 0.0

        # Win Rate Calculation
        win_rate = round((wins / total_trades) * 100.0, 2)

        # Net Profit
        net_profit = round(float(df["PnL"].sum()), 2)

        # Max Drawdown Calculation using Cumulative Equity Curve
        equity = df["PnL"].cumsum()
        peak = equity.cummax()
        drawdown = equity - peak
        max_drawdown = round(abs(float(drawdown.min())), 2) if not drawdown.empty else 0.0

        return {
            "Total Trades": total_trades,
            "Winning Trades": wins,
            "Losing Trades": losses,
            "Breakeven Trades": breakeven,
            "Net Profit": net_profit,
            "Win Rate": win_rate,
            "Profit Factor": profit_factor,
            "Max Drawdown": max_drawdown
        }

    except Exception as e:
        logging.error(f"❌ Error in performance_summary: {e}")
        return {
            "error": str(e)
        }