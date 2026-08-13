def predict_trade(signal, rsi, macd):

    confidence = 50

    if signal == "BUY":
        confidence += 20

    elif signal == "SELL":
        confidence += 20

    if rsi > 60 or rsi < 40:
        confidence += 15

    if macd > 0 or macd < 0:
        confidence += 15

    confidence = min(confidence, 100)

    return signal, confidence