import logging
import math


def trade_allowed(score, min_threshold=65.0, max_threshold=95.0):
    """
    Validates if a trade score meets safety thresholds for execution.
    Handles invalid data types and out-of-bounds scores gracefully.
    """
    # 1. Type & Safety Check for None or NaN
    if score is None or not isinstance(score, (int, float)) or math.isnan(score):
        logging.warning("⚠️ Invalid trade score received in trade_allowed. Trade Rejected.")
        return False

    # 2. Score Range Cap Check
    safe_score = float(score)

    # Reject unrealistically high/corrupted scores or scores below minimum threshold
    if safe_score < min_threshold or safe_score > max_threshold:
        return False

    return True