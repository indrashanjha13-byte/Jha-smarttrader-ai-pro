from auto_trader import place_trade
from trade_exit import exit_manager
from ai_learning import auto_strategy


class TradeManager:

    def __init__(self):
        self.last_signal = None

    def process(self, symbol, signal, current_price, qty=1):

        # ==========================
        # HOLD
        # ==========================
        if signal == "HOLD":
            return

        # ==========================
        # Trade already running
        # ==========================
        if exit_manager.trade_open:
            print("⚠ Trade Already Running")
            return

        # ==========================
        # Same Signal
        # ==========================
        if signal == self.last_signal:
            print(f"⏸ Same Signal ({signal}) -> Skip")
            return

        # ==========================
        # BUY
        # ==========================
        if signal == "BUY":

            # AI selects the strategy
            selected_strategy = auto_strategy()

            target_price = round(
                current_price * 1.02,
                2
            )

            stoploss_price = round(
                current_price * 0.99,
                2
            )

            place_trade(
                "BUY",
                symbol,
                qty,
                current_price
            )

            exit_manager.open_trade(
                symbol=symbol,
                qty=qty,
                entry=current_price,
                target=target_price,
                stoploss=stoploss_price,
                strategy=selected_strategy
            )

            self.last_signal = "BUY"

            print(
                f"✅ BUY Executed : {symbol}"
            )

            print(
                f"🤖 AI Strategy : {selected_strategy}"
            )

        # ==========================
        # SELL
        # ==========================
        elif signal == "SELL":

            place_trade(
                "SELL",
                symbol,
                qty,
                current_price
            )

            self.last_signal = "SELL"

            print(
                f"🔴 SELL Executed : {symbol}"
            )