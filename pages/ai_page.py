import streamlit as st
from signals import get_signals
from ai_decision import ai_decision

def ai_page(symbol):
    st.title("🤖 AI Trading Assistant")

    # Metrics Row (Fixed duplication)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🤖 AI", "ONLINE")
    c2.metric("Version", "2.0")
    c3.metric("Mode", "LIVE")
    c4.metric("Learning", "ACTIVE")

    st.divider()

    # Fetch Trading Signals
    signal = get_signals(symbol)

    # Safe Error & Null Check
    if not signal or "error" in signal:
        st.error(signal.get("error", "Failed to retrieve signal data."))
        return

    # Extract indicators safely with fallbacks
    rsi = signal.get("RSI", 0)
    macd = signal.get("MACD", 0)
    macd_signal = signal.get("MACD_SIGNAL", 0)
    ema9 = signal.get("EMA9", 0)
    ema21 = signal.get("EMA21", 0)
    supertrend = signal.get("SUPERTREND", "NEUTRAL")
    volume = signal.get("Volume", signal.get("volume", 0))
    avg_volume = signal.get("AVG_VOLUME", signal.get("avg_volume", 0))

    # Get AI Decision
    ai = ai_decision(
        rsi=rsi,
        macd=macd,
        macd_signal=macd_signal,
        ema9=ema9,
        ema21=ema21,
        supertrend=supertrend,
        volume=volume,
        avg_volume=avg_volume
    )

    prediction = ai.get("decision", "HOLD")
    confidence = ai.get("confidence", 0)
    score = ai.get("score", 0)
    risk = max(0, 100 - confidence)

    st.subheader("📈 AI Market Prediction")

    if prediction == "BUY":
        st.success("🟢 BUY")
    elif prediction == "SELL":
        st.error("🔴 SELL")
    else:
        st.warning("🟡 HOLD")

    # Metrics Section
    m1, m2, m3 = st.columns(3)
    m1.metric("🎯 Confidence", f"{confidence}%")
    m2.metric("⚠ Risk Level", f"{risk}%")
    m3.metric("📊 AI Score", score)

    st.subheader("📊 Signal Strength")
    st.progress(confidence / 100)

    if confidence >= 80:
        st.success("🔥 Strong Signal")
    elif confidence >= 60:
        st.warning("⚡ Medium Signal")
    else:
        st.error("⚠ Weak Signal")

    st.divider()

    st.subheader("💡 AI Recommendation")
    if prediction == "BUY":
        st.success("Recommended Action: Buy")
    elif prediction == "SELL":
        st.error("Recommended Action: Sell")
    else:
        st.warning("Recommended Action: Wait / Hold")

    st.divider()

    st.subheader("📡 Scanner & AI Analysis")
    st.info(f"**Prediction:** {prediction} | **Confidence:** {confidence}% | **AI Score:** {score}")

    # Safe float formatting to prevent crash if data is None
    st.write(f"**RSI:** {rsi:.2f}" if isinstance(rsi, (int, float)) else f"**RSI:** {rsi}")
    st.write(f"**MACD:** {macd:.2f}" if isinstance(macd, (int, float)) else f"**MACD:** {macd}")
    st.write(f"**MACD Signal:** {macd_signal:.2f}" if isinstance(macd_signal, (int, float)) else f"**MACD Signal:** {macd_signal}")
    st.write(f"**EMA 9:** {ema9:.2f}" if isinstance(ema9, (int, float)) else f"**EMA 9:** {ema9}")
    st.write(f"**EMA 21:** {ema21:.2f}" if isinstance(ema21, (int, float)) else f"**EMA 21:** {ema21}")
    st.write(f"**SuperTrend:** {supertrend}")
    st.write(f"**Volume:** {volume}")
    st.write(f"**Average Volume:** {avg_volume}")

    st.divider()

    st.subheader("📅 Next Candle Prediction")
    if prediction == "BUY":
        st.success("📈 Expected Bullish Continuation")
    elif prediction == "SELL":
        st.error("📉 Expected Bearish Continuation")
    else:
        st.warning("⏳ Sideways Market Expected")