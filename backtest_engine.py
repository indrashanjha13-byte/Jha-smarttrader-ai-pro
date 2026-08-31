import pandas as pd
import logging
import math


class BacktestEngine:

    def __init__(self, initial_balance=100000.0):
        self.start_balance = float(initial_balance)
        self.balance = float(initial_balance)
        self.trades = []

    def add_trade(self, symbol, action, entry, exit_price, qty):
        """
        Calculates PnL safely and updates backtest balance.
        """
        # 1. Inputs Safety & Validation Check
        if not symbol or not isinstance(qty, (int, float)) or qty <= 0:
            logging.warning(f"⚠️ Invalid quantity ({qty}) for trade {symbol}. Trade skipped.")
            return False

        if any(v is None or not isinstance(v, (int, float)) or math.isnan(v) or v <= 0 for v in [entry, exit_price]):
            logging.warning(f"⚠️ Invalid entry/exit price for trade {symbol}. Trade skipped.")
            return False

        act = str(action).upper().strip()

        # 2. PnL Calculation
        if act == "BUY":
            pnl = (exit_price - entry) * qty
        elif act == "SELL":
            pnl = (entry - exit_price) * qty
        else:
            logging.warning(f"⚠️ Unknown trade action '{action}'. Trade skipped.")
            return False

        pnl = round(pnl, 2)
        self.balance += pnl

        self.trades.append({
            "Symbol": symbol,
            "Action": act,
            "Entry": float(entry),
            "Exit": float(exit_price),
            "Qty": float(qty),
            "PnL": pnl,
            "Balance": round(self.balance, 2)
        })
        return True

    def summary(self):
        """
        Generates comprehensive backtest performance summary.
        """
        if not self.trades:
            return {
                "Total Trades": 0,
                "Wins": 0,
                "Losses": 0,
                "Breakeven": 0,
                "Win Rate (%)": 0.0,
                "Net Profit": 0.0,
                "ROI (%)": 0.0,
                "Ending Balance": self.balance
            }

        df = pd.DataFrame(self.trades)

        wins = len(df[df["PnL"] > 0])
        losses = len(df[df["PnL"] < 0])
        breakeven = len(df[df["PnL"] == 0])
        total = len(df)

        win_rate = round((wins / total) * 100, 2) if total > 0 else 0.0
        net_profit = round(float(df["PnL"].sum()), 2)
        roi = round((net_profit / self.start_balance) * 100, 2)

        return {
            "Total Trades": total,
            "Wins": wins,
            "Losses": losses,
            "Breakeven": breakeven,
            "Win Rate (%)": win_rate,
            "Net Profit": net_profit,
            "ROI (%)": roi,
            "Ending Balance": round(self.balance, 2)
        }

    def dataframe(self):
        """Returns trade history as a Pandas DataFrame."""
        return pd.DataFrame(self.trades)