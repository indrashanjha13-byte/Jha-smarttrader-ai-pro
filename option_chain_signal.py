def option_ai_signal(pcr):

    if pcr > 1.20:
        return {
            "Signal": "🟢 BUY",
            "Confidence": 90
        }

    elif pcr < 0.80:
        return {
            "Signal": "🔴 SELL",
            "Confidence": 90
        }

    else:
        return {
            "Signal": "🟡 HOLD",
            "Confidence": 60
        }