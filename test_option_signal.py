import logging
from option_chain_signal import option_ai_signal


def test_option_ai_signals():
    """Test script to evaluate option AI signals against various PCR thresholds."""
    print("==========================================")
    print("Testing Option AI Signals (PCR Values)...")
    print("==========================================")

    test_values = [
        (1.35, "Expected Bullish / CE setup (High PCR)"),
        (0.65, "Expected Bearish / PE setup (Low PCR)"),
        (1.00, "Expected Neutral setup (Balanced PCR)")
    ]

    for pcr_val, description in test_values:
        try:
            signal = option_ai_signal(pcr_val)
            print(f"PCR: {pcr_val:<5} | Desc: {description}")
            print(f"Result Signal -> {signal}")
            print("-" * 42)
        except Exception as e:
            logging.error(f"❌ Error testing PCR {pcr_val}: {e}")
            print(f"PCR: {pcr_val:<5} | Status: ❌ Failed with error: {e}")
            print("-" * 42)

    print("==========================================")


if __name__ == "__main__":
    test_option_ai_signals()