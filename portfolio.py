import logging


# =========================================================
# GLOBAL PORTFOLIO STATE
# =========================================================

portfolio = {}


# =========================================================
# UPDATE POSITION
# =========================================================

def update_position(symbol, qty):
    """
    Add, update, or remove a position.
    """

    try:
        clean_symbol = str(symbol).strip().upper()
        quantity = int(qty)

        if not clean_symbol:
            return False

        if quantity <= 0:

            if clean_symbol in portfolio:
                del portfolio[clean_symbol]

                logging.info(
                    f"🗑️ Position closed: {clean_symbol}"
                )

        else:

            portfolio[clean_symbol] = quantity

            logging.info(
                f"📊 Position Updated: "
                f"{clean_symbol} = {quantity}"
            )

        return True

    except (ValueError, TypeError) as e:

        logging.error(
            f"❌ Position update error: {e}"
        )

        return False


# =========================================================
# GET POSITION
# =========================================================

def get_position(symbol):
    """
    Returns current quantity for a symbol.
    """

    try:

        clean_symbol = str(
            symbol
        ).strip().upper()

        return portfolio.get(
            clean_symbol,
            0
        )

    except Exception as e:

        logging.error(
            f"❌ Get position error: {e}"
        )

        return 0


# =========================================================
# CHECK POSITION
# =========================================================

def has_position(symbol):
    """
    Returns True if an active position exists.
    """

    return get_position(symbol) > 0


# =========================================================
# CLOSE POSITION
# =========================================================

def close_position(symbol):
    """
    Completely removes a symbol from portfolio.
    """

    try:

        clean_symbol = str(
            symbol
        ).strip().upper()

        if clean_symbol in portfolio:

            del portfolio[clean_symbol]

            logging.info(
                f"🔴 Position closed: {clean_symbol}"
            )

            return True

        return False

    except Exception as e:

        logging.error(
            f"❌ Close position error: {e}"
        )

        return False


# =========================================================
# GET ALL POSITIONS
# =========================================================

def get_all_positions():
    """
    Returns a copy of all active positions.
    """

    return portfolio.copy()


# =========================================================
# TOTAL QUANTITY
# =========================================================

def total_quantity():
    """
    Returns total quantity across all positions.
    """

    try:

        return sum(
            portfolio.values()
        )

    except Exception:

        return 0


# =========================================================
# CLEAR PORTFOLIO
# =========================================================

def clear_portfolio():
    """
    Clears all portfolio positions.
    """

    portfolio.clear()

    logging.info(
        "🧹 Portfolio cleared"
    )

    return True


# =========================================================
# PORTFOLIO SUMMARY
# =========================================================

def portfolio_summary():
    """
    Returns a simple portfolio summary.
    """

    return {
        "positions": get_all_positions(),
        "number_of_positions": len(portfolio),
        "total_quantity": total_quantity()
    }


# =========================================================
# TEST
# =========================================================

if __name__ == "__main__":

    print("===== PORTFOLIO TEST =====")

    update_position(
        "^NSEI",
        1
    )

    update_position(
        "RELIANCE.NS",
        10
    )

    print(
        "Portfolio:",
        get_all_positions()
    )

    print(
        "NIFTY Position:",
        get_position("^NSEI")
    )

    print(
        "Has NIFTY:",
        has_position("^NSEI")
    )

    print(
        "Summary:",
        portfolio_summary()
    )

    close_position("^NSEI")

    print(
        "After Close:",
        get_all_positions()
    )