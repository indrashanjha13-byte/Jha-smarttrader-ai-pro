import logging

MAX_RISK_PER_TRADE = 2  # Max 2% risk per trade


def calculate_qty(capital, entry_price, stoploss_price):
    """
    Calculates safe position quantity based on capital and maximum allowed risk percentage.
    """
    try:
        # Convert inputs to standard float/int values
        cap = float(capital)
        entry = float(entry_price)
        sl = float(stoploss_price)

        if cap <= 0 or entry <= 0:
            logging.warning("⚠️ Invalid capital or entry price provided for quantity calculation.")
            return 0

        # Risk amount in currency (e.g., INR)
        risk_amount = (cap * MAX_RISK_PER_TRADE) / 100.0

        # Risk per share (absolute difference between entry and stoploss)
        risk_per_share = abs(entry - sl)

        # Division by zero safeguard
        if risk_per_share <= 0:
            logging.warning("⚠️ Risk per share is zero or negative. Stoploss cannot equal entry price.")
            return 0

        # Calculate final share quantity
        qty = int(risk_amount / risk_per_share)

        # Ensure quantity is at least 0
        return max(0, qty)

    except (ValueError, TypeError) as e:
        logging.error(f"❌ Invalid data type passed to calculate_qty: {e}")
        return 0