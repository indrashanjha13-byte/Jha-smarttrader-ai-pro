import logging
import math
import os
import sys

# Set root project path dynamically
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Dynamic Machine Learning Engine Import
ml_engine = None
try:
    import ml_model
    ml_engine = ml_model.TradeMLModel()
except ImportError:
    try:
        from trading import ml_model
        ml_engine = ml_model.TradeMLModel()
    except Exception as e:
        logging.warning(f"⚠️ ML Model optional loading skipped: {e}")


def predict_trade(signal, rsi, macd, macd_signal=0, **kwargs):
    """
    Calculates trade prediction and confidence dynamically.
    Combines Technical Indicator Rules with ML Model (if available).
    """
    # 1. Safe fallback for invalid signals
    if signal is None or signal not in ["BUY", "SELL"]:
        return "HOLD", 50.0

    # 2. Safe fallback for missing/corrupted technical values
    if any(val is None or (isinstance(val, float) and math.isnan(val)) for val in [rsi, macd]):
        logging.warning("⚠️ Invalid RSI or MACD values in predict_trade. Returning standard signal.")
        return signal, 50.0

    # Base Confidence Score
    confidence = 50.0

    # 3. Base Signal Weight
    if signal in ["BUY", "SELL"]:
        confidence += 15.0

    # 4. RSI Momentum Validation
    if signal == "BUY" and rsi < 40:
        confidence += 15.0  # Buying in oversold region
    elif signal == "SELL" and rsi > 60:
        confidence += 15.0  # Selling in overbought region
    elif 40 <= rsi <= 60:
        confidence += 5.0   # Neutral momentum range

    # 5. MACD Trend Direction Validation
    if signal == "BUY" and macd > macd_signal:
        confidence += 15.0  # Bullish Crossover
    elif signal == "SELL" and macd < macd_signal:
        confidence += 15.0  # Bearish Crossover

    # 6. ML Model Reinforcement Alignment
    if ml_engine and getattr(ml_engine, "is_fitted", False):
        try:
            macd_hist = macd - macd_signal
            ml_pred, ml_conf = ml_engine.predict([rsi, macd, macd_hist])
            
            # If ML prediction confirms indicator signal
            if (signal == "BUY" and ml_pred == 1) or (signal == "SELL" and ml_pred == 0):
                confidence = (confidence + ml_conf) / 2.0
        except Exception as e:
            logging.error(f"❌ ML Prediction Error: {e}")

    # Clamp confidence score safely between 0% and 95%
    final_confidence = min(max(round(confidence, 2), 0.0), 95.0)

    return signal, final_confidence