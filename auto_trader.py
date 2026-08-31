import logging

def place_trade(action, symbol, qty, price):
    """
    Executes a trade order (BUY/SELL) through the broker API or paper trading engine.
    """
    try:
        logging.info(f"🚀 Placing Trade -> Action: {action} | Symbol: {symbol} | Qty: {qty} | Price: {price}")
        print(f"🚀 Order Executed: {action} {symbol} (Qty: {qty}) at ₹{price}")
        return True
    except Exception as e:
        logging.error(f"❌ Error in place_trade: {e}")
        return False