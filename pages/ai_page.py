import streamlit as st
from signals import get_signals
from ai_decision import ai_decision


def ai_page(symbol):

    st.title("🤖 AI Trading Assistant")

    st.columns(4)

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("🤖 AI", "ONLINE")

    c2.metric("Version", "2.0")

    c3.metric("Mode", "LIVE")

    c4.metric("Learning", "ACTIVE")

    st.divider()

    signal = get_signals(symbol)

    if "error" in signal:
        st.error(signal["error"])
        return

    ai = ai_decision(
        rsi=signal["RSI"],
        macd=signal["MACD"],
        macd_signal=signal["MACD_SIGNAL"],
        ema9=signal["EMA9"],
        ema21=signal["EMA21"],
        supertrend=signal["SUPERTREND"],
        volume=signal["Volume"],
        avg_volume=signal["AVG_VOLUME"]
    )

    prediction = ai["decision"]
    confidence = ai["confidence"]
    score = ai["score"]

    risk = 100 - confidence

    st.subheader("📈 AI Market Prediction")

    if prediction == "BUY":
        st.success("🟢 BUY")

    elif prediction == "SELL":
        st.error("🔴 SELL")

    else:
        st.warning("🟡 HOLD")

    st.divider()

    c1, c2, c3 = st.columns(3)

    with c1:
        st.metric("🎯 Confidence", f"{confidence}%")

    with c2:
        st.metric("⚠ Risk", f"{risk}%")

    with c3:
        st.metric("📊 AI Score", score)

    st.progress(confidence / 100)

    st.subheader("📊 AI Decision Meter")

    if confidence >= 80:
        st.success("🔥 Strong Signal")

    elif confidence >= 60:
        st.warning("⚡ Medium Signal")

    else:
        st.error("⚠ Weak Signal")

    st.divider()

    st.subheader("💡 AI Recommendation")

    if prediction == "BUY":

        st.success("Recommended Action : Buy")

    elif prediction == "SELL":

        st.error("Recommended Action : Sell")

    else:

        st.warning("Recommended Action : Wait")

    st.divider()

    st.subheader("⚠ Risk Meter")

    st.progress(risk / 100)

    st.metric(
        "Risk Level",
        f"{risk}%"
    )
    st.divider()
    st.divider()

    st.subheader("📡 Scanner Summary")

    st.info(
        f"""
    Prediction : {prediction}

    Confidence : {confidence}%

    AI Score : {score}
    """
    )

    st.divider()

    st.subheader("🧠 AI Analysis")

    st.write(f"**Decision:** {prediction}")
    st.write(f"**RSI:** {signal['RSI']:.2f}")
    st.write(f"**MACD:** {signal['MACD']:.2f}")
    st.write(f"**MACD Signal:** {signal['MACD_SIGNAL']:.2f}")
    st.write(f"**EMA 9:** {signal['EMA9']:.2f}")
    st.write(f"**EMA 21:** {signal['EMA21']:.2f}")
    st.write(f"**SuperTrend:** {signal['SUPERTREND']}")
    st.write(f"**Volume:** {signal['Volume']}")
    st.write(f"**Average Volume:** {signal['AVG_VOLUME']}")

    st.divider()

    st.subheader("📅 Next Candle Prediction")

    if prediction == "BUY":
        st.success("📈 Expected Bullish Continuation")

    elif prediction == "SELL":
        st.error("📉 Expected Bearish Continuation")

    else:
        st.warning("⏳ Sideways Market Expected")