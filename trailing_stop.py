# trailing_stop.py

class TrailingStop:

    def __init__(self):
        self.active = False
        self.stoploss = 0
        self.entry = 0

    def start(
        self,
        entry,
        stoploss
    ):

        self.active = True
        self.entry = entry
        self.stoploss = stoploss

    def update(
        self,
        current_price
    ):

        if not self.active:
            return self.stoploss

        profit = current_price - self.entry

        # Price 1% upar gaya
        if profit >= self.entry * 0.01:

            new_sl = current_price * 0.995

            if new_sl > self.stoploss:

                self.stoploss = round(
                    new_sl,
                    2
                )

        return self.stoploss


trailing_stop = TrailingStop()