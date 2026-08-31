import logging
from trade_exit import exit_manager
from ai_learning import auto_strategy
from risk_manager import calculate_trade_details
from config import LOT_SIZE


def place_trade(action, symbol, qty, price):
    """
    Executes a trade order (BUY/SELL) locally within trade_manager.
    """
    try:
        logging.info(f"🚀 Placing Trade -> Action: {action} | Symbol: {symbol} | Qty: {qty} | Price: {price}")
        print(f"🚀 Order Executed: {action} {symbol} (Qty: {qty}) at ₹{price}")
        return True
    except Exception as e:
        logging.error(f"❌ Error in place_trade: {e}")
        return False


class TradeManager:
    """
    Manages trade signals, risk calculations, strategy selection, 
    and orchestrates order execution and position lifecycle.
    """

    def __init__(self):
        self.last_signal = None

    def process(
        self,
        symbol,
        signal,
        current_price,
        capital=100000
    ):
        try:
            signal = str(signal).strip().upper()
            symbol = str(symbol).strip().upper()
            current_price = float(current_price)

            # ==========================
            # HOLD
            # ==========================
            if signal == "HOLD":
                return

            # ==========================
            # Same Signal Filtering
            # ==========================
            if signal == self.last_signal:
                return

            # ==========================
            # BUY SIGNAL
            # ==========================
            if signal == "BUY":
                # Check if trade is already running
                if exit_manager.trade_open:
                    logging.warning("⚠️ Trade Already Running. Skipping BUY signal.")
                    return

                # AI selects the strategy
                selected_strategy = auto_strategy()

                # Stop Loss = 1% | Reward : Risk = 1 : 2
                stoploss_price = round(current_price * 0.99, 2)

                # Risk + Lot Calculation
                trade = calculate_trade_details(
                    capital=capital,
                    entry_price=current_price,
                    stoploss_price=stoploss_price,
                    lot_size=LOT_SIZE,
                    reward_ratio=2.0
                )

                lots = trade.get("lots", 0)
                qty = trade.get("quantity", 0)
                target_price = trade.get("target_price", 0)

                # Safety Check
                if lots <= 0 or qty <= 0:
                    logging.warning("⚠️ Trade skipped: Risk limit does not allow even 1 lot.")
                    return

                # Execute BUY order via Broker/Paper API
                place_trade("BUY", symbol, qty, current_price)

                # Initialize Trade Tracking
                exit_manager.open_trade(
                    symbol=symbol,
                    qty=qty,
                    entry=current_price,
                    target=target_price,
                    stoploss=stoploss_price,
                    strategy=selected_strategy
                )

                self.last_signal = "BUY"

                # Display Trade Information Logs
                print("==========================================")
                print("🟢 BUY TRADE EXECUTED")
                print(f"Symbol          : {symbol}")
                print(f"Entry           : ₹{current_price}")
                print(f"Stop Loss       : ₹{stoploss_price}")
                print(f"Target          : ₹{target_price}")
                print(f"Lot Size        : {LOT_SIZE}")
                print(f"Lots            : {lots}")
                print(f"Quantity        : {qty}")
                print(f"Risk %          : {trade.get('risk_percent', 0)}%")
                print(f"Maximum Risk    : ₹{trade.get('actual_risk', 0)}")
                print(f"Potential Profit: ₹{trade.get('potential_profit', 0)}")
                print(f"AI Strategy     : {selected_strategy}")
                print("==========================================")

            # ==========================
            # SELL SIGNAL
            # ==========================
            elif signal == "SELL":
                if not exit_manager.trade_open:
                    return

                qty = exit_manager.qty

                place_trade("SELL", symbol, qty, current_price)
                self.last_signal = "SELL"

                logging.info(f"🔴 SELL Executed: {symbol} Qty={qty}")
                print(f"🔴 SELL Executed: {symbol} Qty={qty}")

        except Exception as e:
            logging.error(f"❌ Error in TradeManager process loop: {e}")