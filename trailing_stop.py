import logging


class TrailingStop:
    """
    Manages dynamic trailing stop-loss for open trades based on price milestones.
    """

    def __init__(self):
        self.active = False
        self.stoploss = 0.0
        self.entry = 0.0

    def start(self, entry, stoploss):
        """Initializes trailing stop tracking with entry and initial stoploss."""
        self.active = True
        self.entry = float(entry)
        self.stoploss = float(stoploss)
        logging.info(f"🛡️ Trailing stop started | Entry: {self.entry} | Initial SL: {self.stoploss}")

    def update(self, current_price):
        """
        Updates the trailing stoploss if current price makes a favorable profit move.
        Triggers when price moves 1% above entry.
        """
        if not self.active:
            return self.stoploss

        try:
            curr_price = float(current_price)
            profit = curr_price - self.entry

            # When price goes 1% up from entry
            if profit >= (self.entry * 0.01):
                # Trail stoploss at 0.5% below current price
                new_sl = curr_price * 0.995

                # Move stoploss only upwards
                if new_sl > self.stoploss:
                    self.stoploss = round(new_sl, 2)
                    logging.info(f"📈 Trailing Stop updated to: {self.stoploss} at price {curr_price}")

        except Exception as e:
            logging.error(f"❌ Error in TrailingStop update: {e}")

        return self.stoploss


# Global TrailingStop instance
trailing_stop = TrailingStop()