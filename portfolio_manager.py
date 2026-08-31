import logging

MAX_OPEN_TRADES = 5


def trade_allowed(open_positions):
    """
    Checks if new trades are permitted based on active open positions limit.
    """
    try:
        # Ensure open_positions is safely parsed as an integer
        positions_count = int(open_positions)

        if positions_count < 0:
            logging.warning("⚠️ Negative open positions count detected. Defaulting to 0.")
            positions_count = 0

        is_allowed = positions_count < MAX_OPEN_TRADES

        if not is_allowed:
            logging.info(f"🛑 Max open trades limit reached ({positions_count}/{MAX_OPEN_TRADES}). New trade blocked.")

        return is_allowed

    except (ValueError, TypeError) as e:
        logging.error(f"❌ Invalid open_positions data type passed to trade_allowed: {e}")
        return False