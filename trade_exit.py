import logging
from live_trading import execute_sell
from trailing_stop import trailing_stop
from ai_learning import update_learning


class ExitManager:
    """
    Manages active trade lifecycle, trailing stoploss updates, 
    target/stoploss exit triggers, and AI learning feedback loops.
    """

    def __init__(self):
        self.reset_state()

    def reset_state(self):
        """Resets all internal trade parameters to default state."""
        self.trade_open = False
        self.symbol = None
        self.qty = 0
        self.entry = 0.0
        self.target = 0.0
        self.stoploss = 0.0
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
        """Initializes tracking for a newly executed trade."""
        self.trade_open = True
        self.symbol = str(symbol).strip().upper()
        self.qty = int(qty)
        self.entry = float(entry)
        self.target = float(target)
        self.stoploss = float(stoploss)
        self.strategy = strategy

        try:
            trailing_stop.start(self.entry, self.stoploss)
            logging.info(f"🎯 Tracking trade opened for {self.symbol} | Qty: {self.qty} | Entry: {self.entry}")
        except Exception as e:
            logging.error(f"❌ Error starting trailing stop for {self.symbol}: {e}")

    def _close_trade_and_log(self, current_price, outcome):
        """Helper method to execute sell, update learning, and reset state."""
        try:
            # Execute broker sell order
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

            # Update AI Learning feedback
            update_learning(strategy, market, outcome)
            logging.info(f"🏁 Trade closed for {market} with outcome: {outcome} at price {current_price}")

        except Exception as e:
            logging.error(f"❌ Error during trade exit execution for {self.symbol}: {e}")
        finally:
            # Always reset state securely
            self.reset_state()

    def check(self, current_price):
        """
        Monitors current price against target and trailing stoploss 
        to trigger exits.
        """
        if not self.trade_open:
            return None

        try:
            curr_price = float(current_price)

            # Update trailing stoploss dynamically
            self.stoploss = trailing_stop.update(curr_price)

            # Target Hit Check
            if curr_price >= self.target:
                self._close_trade_and_log(curr_price, "WIN")
                return "TARGET"

            # Stop Loss Hit Check
            if curr_price <= self.stoploss:
                self._close_trade_and_log(curr_price, "LOSS")
                return "STOPLOSS"

        except Exception as e:
            logging.error(f"❌ Error in ExitManager check loop: {e}")

        return None


# ==========================
# Global Exit Manager Object
# ==========================

exit_manager = ExitManager()