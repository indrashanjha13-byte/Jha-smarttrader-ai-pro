def option_ai_signal(pcr):
    """
    Evaluates Put-Call Ratio (PCR) to determine Options AI Signal and Confidence Score.
    """
    try:
        # Ensure PCR is a valid float number
        pcr_val = float(pcr)

        if pcr_val >= 1.20:
            return {
                "Signal": "🟢 BUY",
                "Confidence": 90
            }

        elif pcr_val <= 0.80:
            return {
                "Signal": "🔴 SELL",
                "Confidence": 90
            }

        else:
            return {
                "Signal": "🟡 HOLD",
                "Confidence": 60
            }

    except (ValueError, TypeError):
        # Fallback safeguard if invalid/non-numeric data is passed
        return {
            "Signal": "🟡 HOLD",
            "Confidence": 50
        }