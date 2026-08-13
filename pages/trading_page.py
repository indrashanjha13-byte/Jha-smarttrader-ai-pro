import streamlit as st

from signals import get_signals

from strategy import (
    generate_signal,
    ema_signal,
    rsi_signal,
    supertrend_signal
)

from ai_learning import auto_strategy

from ai_engine import (
    ai_brain,
    confidence_score,
    stop_target,
    position_size
)


def trading_page(trader, symbol):

    st.title("💹 Trading")

    # =========================
    # MARKET SIGNAL
    # =========================

    signal = get_signals(symbol)

    if "error" in signal:
        st.error(signal["error"])
        return

    current_price = signal["Close"]

    # =========================
    # 🤖 AI STRATEGY
    # =========================

    selected_strategy = auto_strategy()

    if not selected_strategy or selected_strategy == "None":
        selected_strategy = "AI Combo"

    st.info(
        f"🤖 AI Selected Strategy : {selected_strategy}"
    )

    # =========================
    # AI SIGNAL
    # =========================

    if selected_strategy == "EMA Crossover":

        ai_signal = ema_signal(
            signal["EMA9"],
            signal["EMA21"]
        )

    elif selected_strategy == "RSI":

        ai_signal = rsi_signal(
            signal["RSI"]
        )

    elif selected_strategy == "SuperTrend":

        ai_signal = supertrend_signal(
            signal["SUPERTREND"]
        )

    else:

        ai_signal = generate_signal(
            signal["SUPERTREND"],
            signal["MACD"],
            signal["MACD_SIGNAL"],
            signal["Volume"],
            signal["AVG_VOLUME"]
        )

    st.write(
        "🧠 AI Signal :",
        ai_signal
    )

    # =========================
    # 🤖 AI ANALYSIS
    # =========================

    trend = (
        "UP"
        if signal["SUPERTREND"] > 0
        else "DOWN"
    )

    ai = ai_brain(
        signal=ai_signal,
        rsi=signal["RSI"],
        volume=signal["Volume"],
        trend=trend,
        ema9=signal["EMA9"],
        ema21=signal["EMA21"],
        supertrend=signal["SUPERTREND"],
        balance=trader.balance,
        risk_percent=2,
        trade_amount=current_price
    )

    confidence = confidence_score(
        ai["score"],
        ai["regime"],
        ai["filter"]
    )

    st.subheader("🤖 AI Analysis")

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "AI Score",
        ai["score"]
    )

    c2.metric(
        "Confidence",
        f"{confidence}%"
    )

    c3.metric(
        "Market Regime",
        ai["regime"]
    )

    st.write(
        "AI Decision :",
        ai["decision"]
    )

    # =========================
    # 📈 LIVE TRADING PANEL
    # =========================

    st.header("📈 Live Trading Panel")

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "Price",
        f"₹ {signal['Close']:.2f}"
    )

    c2.metric(
        "RSI",
        round(signal["RSI"], 2)
    )

    c3.metric(
        "SuperTrend",
        signal["SUPERTREND"]
    )

    st.divider()

    # =========================
    # 💰 BALANCE
    # =========================

    st.metric(
        "💰 Account Balance",
        f"₹ {trader.balance:.2f}"
    )

    # =========================
    # TRADE STATUS
    # =========================

    if trader.position:

        st.success("🟢 Trade Running")

    else:

        st.warning("🔴 No Active Trade")

    st.divider()

    # =========================
    # 🛒 ORDER PANEL
    # =========================

    st.subheader("🛒 Place Order")

    qty = st.number_input(
        "Quantity",
        min_value=1,
        value=1
    )

    target = st.number_input(
        "Target",
        value=float(signal["Close"] + 40)
    )

    stoploss = st.number_input(
        "Stoploss",
        value=float(signal["Close"] - 20)
    )

    col1, col2 = st.columns(2)

    # =========================
    # 🟢 BUY
    # =========================

    with col1:

        if st.button("🟢 BUY"):

            ok, msg = trader.buy(
                symbol,
                signal["Close"],
                qty,
                target,
                stoploss,
                strategy=selected_strategy
            )

            if ok:

                st.success(msg)

                st.info(
                    f"🤖 Strategy Used : {selected_strategy}"
                )

            else:

                st.error(msg)

    # =========================
    # 🔴 SELL
    # =========================

    with col2:

        if st.button("🔴 SELL"):

            ok, pnl = trader.sell(
                signal["Close"]
            )

            if ok:

                st.success(
                    f"Trade Closed | P&L ₹{pnl:.2f}"
                )

            else:

                st.error(pnl)

    # =========================
    # 📦 CURRENT POSITION
    # =========================

    st.divider()

    st.subheader("📦 Current Position")

    if trader.position:

        st.write(
            "**Symbol:**",
            trader.position["symbol"]
        )

        st.write(
            "**Quantity:**",
            trader.position["qty"]
        )

        st.write(
            "**Entry Price:**",
            trader.position["entry"]
        )

        st.write(
            "**Target:**",
            trader.position["target"]
        )

        st.write(
            "**Stoploss:**",
            trader.position["stoploss"]
        )

        # Strategy display
        st.write(
            "**AI Strategy:**",
            trader.position.get(
                "strategy",
                "AI Combo"
            )
        )

        # =========================
        # ❌ CLOSE POSITION
        # =========================

        if st.button("❌ Close Position"):

            ok, pnl = trader.sell(
                signal["Close"]
            )

            if ok:

                st.success(
                    f"Position Closed | P&L ₹{pnl:.2f}"
                )

            else:

                st.error(pnl)

    else:

        st.info("No Active Position")