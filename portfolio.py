import logging

# Global in-memory portfolio state
portfolio = {}


def update_position(symbol, qty):
    """
    Updates or adds position quantity for a given symbol. 
    Removes the symbol from portfolio if quantity becomes zero or less.
    """
    try:
        clean_symbol = str(symbol).strip().upper()
        quantity = int(qty)

        if quantity <= 0:
            if clean_symbol in portfolio:
                del portfolio[clean_symbol]
                logging.info(f"🗑️ Position closed/removed for {clean_symbol}")
        else:
            portfolio[clean_symbol] = quantity
            logging.info(f"📊 Portfolio Updated -> {clean_symbol}: {quantity}")

    except (ValueError, TypeError) as e:
        logging.error(f"❌ Invalid data passed to update_position: {e}")