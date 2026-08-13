import csv
import os
from datetime import datetime


class BrokerAPI:

    FILE_NAME = "trade_history.csv"

    def __init__(self):

        if not os.path.exists(self.FILE_NAME):

            with open(self.FILE_NAME, "w", newline="") as f:

                writer = csv.writer(f)

                writer.writerow([
                    "Time",
                    "Action",
                    "Symbol",
                    "Entry",
                    "Exit",
                    "Quantity",
                    "Target",
                    "StopLoss",
                    "PnL",
                    "Status",
                    "Mode"
                ])

    def save_trade(
        self,
        action,
        symbol,
        qty,
        entry=0,
        exit_price=0,
        target=0,
        stoploss=0,
        pnl=0,
        status="OPEN",
        mode="Paper"
    ):

        with open(self.FILE_NAME, "a", newline="") as f:

            writer = csv.writer(f)

            writer.writerow([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                action,
                symbol,
                entry,
                exit_price,
                qty,
                target,
                stoploss,
                pnl,
                status,
                mode
            ])

    def place_buy_order(
        self,
        symbol,
        qty,
        entry,
        target,
        stoploss
    ):

        print("=" * 60)
        print("🟢 BUY ORDER EXECUTED")
        print(f"Symbol     : {symbol}")
        print(f"Entry      : ₹{entry}")
        print(f"Target     : ₹{target}")
        print(f"Stop Loss  : ₹{stoploss}")
        print(f"Quantity   : {qty}")
        print("=" * 60)

        self.save_trade(
            action="BUY",
            symbol=symbol,
            qty=qty,
            entry=entry,
            target=target,
            stoploss=stoploss,
            pnl=0,
            status="OPEN",
            mode="Paper"
        )

    def place_sell_order(
        self,
        symbol,
        qty,
        entry,
        exit_price,
        target,
        stoploss,
        pnl
    ):

        print("=" * 60)
        print("🔴 SELL ORDER EXECUTED")
        print(f"Symbol     : {symbol}")
        print(f"Entry      : ₹{entry}")
        print(f"Exit       : ₹{exit_price}")
        print(f"PnL        : ₹{pnl}")
        print("=" * 60)

        self.save_trade(
            action="SELL",
            symbol=symbol,
            qty=qty,
            entry=entry,
            exit_price=exit_price,
            target=target,
            stoploss=stoploss,
            pnl=pnl,
            status="CLOSED",
            mode="Paper"
        )