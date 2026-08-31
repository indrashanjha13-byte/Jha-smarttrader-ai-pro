import pandas as pd
import logging


def backtest(data, initial_balance=100000.0):
    """
    Executes backtesting loop over historical market data.
    """
    if data is None or (isinstance(data, pd.DataFrame) and data.empty):
        logging.warning("⚠️ Empty market data passed to backtest module.")
        return float(initial_balance), []

    balance = float(initial_balance)
    trades = []

    # Safe Iteration placeholder for strategy signals execution
    # If using indicators/signals in dataframe:
    if isinstance(data, pd.DataFrame) and "Signal" in data.columns:
        for idx, row in data.iterrows():
            # Example Signal Handling (Can be extended based on your strategy)
            pass

    return round(balance, 2), trades


def performance(trades):
    """
    Calculates detailed backtest performance metrics safely.
    """
    # 1. Empty/Invalid Trades Safety Check
    if not trades or not isinstance(trades, (list, pd.DataFrame)):
        return {
            "total": 0,
            "wins": 0,
            "losses": 0,
            "breakeven": 0,
            "net_profit": 0.0,
            "win_rate": 0.0,
            "profit_factor": 0.0
        }

    df = pd.DataFrame(trades) if isinstance(trades, list) else trades

    if df.empty or "PnL" not in df.columns:
        return {
            "total": 0,
            "wins": 0,
            "losses": 0,
            "breakeven": 0,
            "net_profit": 0.0,
            "win_rate": 0.0,
            "profit_factor": 0.0
        }

    # 2. Performance Metrics Calculation
    total = len(df)
    wins = len(df[df["PnL"] > 0])
    losses = len(df[df["PnL"] < 0])
    breakeven = len(df[df["PnL"] == 0])

    net_profit = round(float(df["PnL"].sum()), 2)
    gross_profit = float(df[df["PnL"] > 0]["PnL"].sum())
    gross_loss = abs(float(df[df["PnL"] < 0]["PnL"].sum()))

    # Zero Division Safety for Profit Factor
    if gross_loss > 0:
        profit_factor = round(gross_profit / gross_loss, 2)
    elif gross_profit > 0:
        profit_factor = 99.0  # Infinite Profit Factor representation
    else:
        profit_factor = 0.0

    win_rate = round((wins / total) * 100, 2) if total > 0 else 0.0

    return {
        "total": total,
        "wins": wins,
        "losses": losses,
        "breakeven": breakeven,
        "net_profit": net_profit,
        "win_rate": win_rate,
        "profit_factor": profit_factor
    }