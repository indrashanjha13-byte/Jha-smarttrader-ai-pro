import logging


def stoploss(entry, atr, multiplier=2.0, trade_type="BUY"):
    """
    Calculates dynamic stoploss price based on Entry and ATR.
    """
    try:
        entry_val = float(entry)
        atr_val = float(atr)

        if trade_type.upper() == "BUY":
            return round(entry_val - (multiplier * atr_val), 2)
        else:  # For SELL / Short trade
            return round(entry_val + (multiplier * atr_val), 2)
    except Exception as e:
        logging.error(f"❌ Error calculating stoploss: {e}")
        return entry


def target(entry, atr, multiplier=4.0, trade_type="BUY"):
    """
    Calculates dynamic target price based on Entry and ATR (Default Risk:Reward 1:2).
    """
    try:
        entry_val = float(entry)
        atr_val = float(atr)

        if trade_type.upper() == "BUY":
            return round(entry_val + (multiplier * atr_val), 2)
        else:  # For SELL / Short trade
            return round(entry_val - (multiplier * atr_val), 2)
    except Exception as e:
        logging.error(f"❌ Error calculating target: {e}")
        return entry


def check_exit(entry, current_price, atr, trade_type="BUY"):
    """
    Evaluates current price against ATR bounds to check if Target or Stoploss is hit.
    """
    try:
        curr = float(current_price)
        sl = stoploss(entry, atr, multiplier=2.0, trade_type=trade_type)
        tgt = target(entry, atr, multiplier=4.0, trade_type=trade_type)

        if trade_type.upper() == "BUY":
            if curr <= sl:
                return "STOPLOSS"
            if curr >= tgt:
                return "TARGET"
        else:  # For SELL / Short trade
            if curr >= sl:
                return "STOPLOSS"
            if curr <= tgt:
                return "TARGET"

    except Exception as e:
        logging.error(f"❌ Error in check_exit evaluation: {e}")

    return None