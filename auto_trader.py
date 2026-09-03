import logging

from auto_mode import is_enabled
from broker.broker_manager import BrokerManager

def place_trade(action, symbol, qty, price=0.0):
    """
    Execute a LIVE broker trade only when Live Auto Trading is enabled.

    Paper trading should continue to be handled by PaperTrader/TradeManager.
    """

    try:
        # =====================================================
        # LIVE TRADING SAFETY CHECK
        # =====================================================

        if not is_enabled():
            logging.info(
                "🛑 Live Auto Trading is OFF. "
                "Real order blocked."
            )

            return {
                "status": "blocked",
                "message": "Live Auto Trading is OFF"
            }

        # =====================================================
        # Validate Order
        # =====================================================

        action = str(action).strip().upper()
        symbol = str(symbol).strip().upper()

        quantity = int(qty)

        if action not in ("BUY", "SELL"):
            return {
                "status": "error",
                "message": f"Invalid action: {action}"
            }

        if not symbol:
            return {
                "status": "error",
                "message": "Symbol is required"
            }

        if quantity <= 0:
            return {
                "status": "error",
                "message": "Quantity must be greater than 0"
            }

        price = float(price or 0.0)

        # =====================================================
        # Broker Manager
        # =====================================================

        broker = BrokerManager(
            broker_name="Kotak Neo"
        )

        # =====================================================
        # Connect Broker
        # =====================================================

        if not broker.connect():

            logging.error(
                "❌ Kotak Neo broker connection failed."
            )

            return {
                "status": "error",
                "message": "Broker connection failed"
            }

        # =====================================================
        # Place LIVE Order
        # =====================================================

        logging.warning(
            f"🔴 LIVE ORDER -> "
            f"{action} | {symbol} | "
            f"Qty: {quantity} | Price: {price}"
        )

        if action == "BUY":

            result = broker.buy(
                symbol,
                quantity,
                price=price
            )

        else:

            result = broker.sell(
                symbol,
                quantity,
                price=price
            )

        # =====================================================
        # Result
        # =====================================================

        if isinstance(result, dict):

            if result.get("status") == "success":

                logging.info(
                    f"✅ LIVE ORDER SUCCESS -> "
                    f"{action} {symbol} "
                    f"Qty={quantity}"
                )

            else:

                logging.error(
                    f"❌ LIVE ORDER FAILED -> "
                    f"{result}"
                )

            return result

        return {
            "status": "error",
            "message": "Unexpected broker response",
            "response": result
        }

    except Exception as e:

        logging.exception(
            f"❌ Error in live place_trade: {e}"
        )

        return {
            "status": "error",
            "message": str(e)
        }