# trade_exit.py

from live_trading import execute_sell
from trailing_stop import trailing_stop
from ai_learning import update_learning


class ExitManager:

    def __init__(self):
        self.trade_open = False
        self.symbol = None
        self.qty = 0
        self.entry = 0
        self.target = 0
        self.stoploss = 0
        self.strategy = "AI Combo"

    def open_trade(
        self,
        symbol,
        qty,
        entry,
        target,
        stoploss,
        strategy="AI Combo"
    ):

        self.trade_open = True
        self.symbol = symbol
        self.qty = qty
        self.entry = entry
        self.target = target
        self.stoploss = stoploss
        self.strategy = strategy

        trailing_stop.start(
            entry,
            stoploss
        )

    def check(self, current_price):

        if not self.trade_open:
            return None

        self.stoploss = trailing_stop.update(current_price)

        # Target Hit
        if current_price >= self.target:

            pnl = round(
                (current_price - self.entry) * self.qty,
                2
            )

            execute_sell(
                self.symbol,
                self.qty,
                self.entry,
                current_price,
                self.target,
                self.stoploss
            )

            market = self.symbol
            strategy = self.strategy

            self.trade_open = False
            self.symbol = None
            self.qty = 0
            self.entry = 0
            self.target = 0
            self.stoploss = 0
            self.strategy = "AI Combo"

            update_learning(
                strategy,
                market,
                "WIN"
            )

            return "TARGET"

        # Stop Loss Hit
        if current_price <= self.stoploss:

            pnl = round(
                (current_price - self.entry) * self.qty,
                2
            )

            execute_sell(
                self.symbol,
                self.qty,
                self.entry,
                current_price,
                self.target,
                self.stoploss
            )

            market = self.symbol
            strategy = self.strategy

            self.trade_open = False
            self.symbol = None
            self.qty = 0
            self.entry = 0
            self.target = 0
            self.stoploss = 0
            self.strategy = "AI Combo"

            update_learning(
                strategy,
                market,
                "LOSS"
            )

            return "STOPLOSS"

        return None


# ==========================
# Global Exit Manager Object
# ==========================

exit_manager = ExitManager()