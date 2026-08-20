
from auto_trader import place_trade
from trade_exit import exit_manager
from ai_learning import auto_strategy
from risk_manager import calculate_trade_details
from config import LOT_SIZE


class TradeManager:

    def __init__(self):
        self.last_signal = None

    def process(
        self,
        symbol,
        signal,
        current_price,
        capital=100000
    ):

        # ==========================
        # HOLD
        # ==========================
        if signal == "HOLD":
            print("🟡 HOLD")
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

            # --------------------------------
            # Stop Loss = 1%
            # Reward : Risk = 1 : 2
            # --------------------------------
            stoploss_price = round(
                current_price * 0.99,
                2
            )

            # --------------------------------
            # Risk + Lot Calculation
            # --------------------------------
            trade = calculate_trade_details(
                capital=capital,
                entry_price=current_price,
                stoploss_price=stoploss_price,
                lot_size=LOT_SIZE,
                reward_ratio=2.0
            )

            lots = trade["lots"]
            qty = trade["quantity"]
            target_price = trade["target_price"]

            # --------------------------------
            # Safety Check
            # --------------------------------
            if lots <= 0 or qty <= 0:

                print(
                    "⚠ Trade skipped: "
                    "Risk limit does not allow even 1 lot."
                )

                return

            # --------------------------------
            # Execute BUY
            # --------------------------------
            place_trade(
                "BUY",
                symbol,
                qty,
                current_price
            )

            # --------------------------------
            # Open Trade
            # --------------------------------
            exit_manager.open_trade(
                symbol=symbol,
                qty=qty,
                entry=current_price,
                target=target_price,
                stoploss=stoploss_price,
                strategy=selected_strategy
            )

            self.last_signal = "BUY"

            # --------------------------------
            # Display Trade Information
            # --------------------------------
            print("==========================================")
            print("🟢 BUY TRADE")
            print(f"Symbol          : {symbol}")
            print(f"Entry           : ₹{current_price}")
            print(f"Stop Loss       : ₹{stoploss_price}")
            print(f"Target          : ₹{target_price}")
            print(f"Lot Size        : {LOT_SIZE}")
            print(f"Lots            : {lots}")
            print(f"Quantity        : {qty}")
            print(f"Risk %          : {trade['risk_percent']}%")
            print(f"Maximum Risk    : ₹{trade['actual_risk']}")
            print(f"Potential Profit: ₹{trade['potential_profit']}")
            print(f"AI Strategy     : {selected_strategy}")
            print("==========================================")

        # ==========================
        # SELL
        # ==========================
        elif signal == "SELL":

            print(
                "🔴 SELL signal received."
            )

            # A SELL signal should normally
            # close an existing BUY position.
            if not exit_manager.trade_open:

                print(
                    "⚠ No open BUY trade to close."
                )

                return

            qty = exit_manager.qty

            place_trade(
                "SELL",
                symbol,
                qty,
                current_price
            )

            self.last_signal = "SELL"

            print(
                f"🔴 SELL Executed: "
                f"{symbol} Qty={qty}"
            )
