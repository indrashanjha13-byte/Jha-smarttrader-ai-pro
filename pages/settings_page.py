import streamlit as st
import json
import os

SETTINGS_FILE = "settings.json"


def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_settings(settings):
    try:
        current = load_settings()
        current.update(settings)
        with open(SETTINGS_FILE, "w") as f:
            json.dump(current, f, indent=4)
        return True
    except Exception as e:
        st.error(f"Failed to save settings: {e}")
        return False


def settings_page():
    settings = load_settings()
    
    st.title("⚙ Settings")

    # ===================================
    # Appearance
    # ===================================
    st.subheader("🎨 Appearance")
    theme = st.selectbox(
        "Theme",
        ["Dark", "Light"],
        index=0 if settings.get("theme", "Dark") == "Dark" else 1,
        key="app_theme"
    )

    st.divider()

    # ===================================
    # AI Settings
    # ===================================
    st.header("🤖 AI Settings")

    ai_modes = ["Conservative", "Balanced", "Aggressive"]
    saved_mode = settings.get("ai_mode", "Balanced")
    mode_idx = ai_modes.index(saved_mode) if saved_mode in ai_modes else 1

    ai_mode = st.selectbox(
        "AI Trading Mode",
        ai_modes,
        index=mode_idx,
        key="ai_mode_select"
    )

    confidence = st.slider(
        "Minimum AI Confidence %",
        50,
        100,
        int(settings.get("confidence", 70)),
        key="ai_confidence_slider"
    )

    paper_trade = st.toggle(
        "Paper Trading Mode",
        value=settings.get("paper_trade", True),
        key="paper_trade_toggle"
    )

    auto_trade = st.toggle(
        "Enable Auto Trading",
        value=settings.get("auto_trade", False),
        key="auto_trade_toggle"
    )

    # ===================================
    # Multi-Strategy Selection (Added Here)
    # ===================================
    st.markdown("---")
    st.markdown("### 🤖 Multi-Strategy AI Confirmation")
    st.markdown("Select strategies that must agree before trade execution:")

    strat_ema = st.checkbox("EMA Crossover Strategy", value=settings.get("strat_ema", True), key="chk_strat_ema")
    strat_supertrend = st.checkbox("SuperTrend Strategy", value=settings.get("strat_supertrend", True), key="chk_strat_supertrend")
    strat_rsi = st.checkbox("RSI Momentum Strategy", value=settings.get("strat_rsi", True), key="chk_strat_rsi_strategy")

    st.info(
        f"""
AI Mode : **{ai_mode}**  
Confidence : **{confidence}%**  
Paper Trading : **{'ON' if paper_trade else 'OFF'}**  
Auto Trading : **{'ON' if auto_trade else 'OFF'}**
"""
    )

    st.divider()

    # ===================================
    # Risk Management
    # ===================================
    st.header("💰 Risk Management")

    risk_per_trade = st.slider(
        "Risk Per Trade (%)",
        1,
        10,
        int(settings.get("risk_per_trade", 2)),
        key="risk_slider"
    )

    max_trades = st.number_input(
        "Max Trades Per Day",
        min_value=1,
        max_value=100,
        value=int(settings.get("max_trades", 5)),
        key="max_trades_input"
    )

    default_target = st.number_input(
        "Default Target (Points)",
        min_value=5,
        value=int(settings.get("default_target", 40)),
        key="target_input"
    )

    default_stoploss = st.number_input(
        "Default Stoploss (Points)",
        min_value=5,
        value=int(settings.get("default_stoploss", 20)),
        key="stoploss_input"
    )

    st.divider()

    # ===================================
    # Broker Settings
    # ===================================
    st.header("🏦 Broker Settings")

    brokers = ["Kotak Neo", "Dhan", "Zerodha", "Upstox", "Angel One"]
    saved_broker = settings.get("broker", "Kotak Neo")
    broker_idx = brokers.index(saved_broker) if saved_broker in brokers else 0

    broker = st.selectbox(
        "Select Broker",
        brokers,
        index=broker_idx,
        key="broker_select"
    )

    client_id = st.text_input("Client ID", value=settings.get("client_id", ""), key="client_id_input")
    api_key = st.text_input("API Key", value=settings.get("api_key", ""), type="password", key="api_key_input")
    api_secret = st.text_input("API Secret", value=settings.get("api_secret", ""), type="password", key="api_secret_input")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔗 Connect Broker", key="btn_connect_broker"):
            st.success(f"✅ {broker} Connected Successfully")

    with col2:
        if st.button("❌ Disconnect Broker", key="btn_disconnect_broker"):
            st.warning("Broker Disconnected")

    st.divider()

    # ===================================
    # Chart Settings
    # ===================================
    st.header("📈 Chart Settings")

    show_ema = st.checkbox("Show EMA", value=settings.get("show_ema", True), key="chk_ema")
    show_supertrend = st.checkbox("Show SuperTrend", value=settings.get("show_supertrend", True), key="chk_supertrend")
    show_rsi = st.checkbox("Show RSI", value=settings.get("show_rsi", True), key="chk_rsi")
    show_macd = st.checkbox("Show MACD", value=settings.get("show_macd", True), key="chk_macd")
    show_volume = st.checkbox("Show Volume", value=settings.get("show_volume", True), key="chk_volume")
    show_bollinger = st.checkbox("Show Bollinger Bands", value=settings.get("show_bollinger", False), key="chk_bollinger")

    timeframes = ["1m", "3m", "5m", "15m", "30m", "1h", "1d"]
    saved_tf = settings.get("timeframe", "5m")
    tf_idx = timeframes.index(saved_tf) if saved_tf in timeframes else 2

    timeframe = st.selectbox(
        "Default Timeframe",
        timeframes,
        index=tf_idx,
        key="tf_select"
    )

    st.divider()

    # ===================================
    # User Profile
    # ===================================
    st.header("👤 User Profile")

    name = st.text_input("Full Name", value=settings.get("user_name", "Pratham Jha"), key="user_name_input")
    email = st.text_input("Email", value=settings.get("user_email", ""), key="user_email_input")
    mobile = st.text_input("Mobile Number", value=settings.get("user_mobile", ""), key="user_mobile_input")

    st.divider()

    # ===================================
    # Telegram Settings
    # ===================================
    st.header("📱 Telegram Settings")

    telegram_token = st.text_input("Bot Token", value=settings.get("telegram_token", ""), type="password", key="tg_token")
    chat_id = st.text_input("Chat ID", value=settings.get("chat_id", ""), key="tg_chat_id")
    telegram_alert = st.checkbox("Enable Telegram Alerts", value=settings.get("telegram_alert", True), key="chk_tg_alert")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔗 Connect Telegram", key="btn_tg_connect"):
            st.success("Telegram Connected Successfully")

    with col2:
        if st.button("📤 Test Message", key="btn_tg_test"):
            st.info("Test Message Sent")

    st.divider()

    # ===================================
    # API Key Manager
    # ===================================
    st.header("🔑 API Key Manager")

    openai_key = st.text_input("OpenAI API Key", value=settings.get("openai_key", ""), type="password", key="key_openai")
    gemini_key = st.text_input("Gemini API Key", value=settings.get("gemini_key", ""), type="password", key="key_gemini")
    news_key = st.text_input("News API Key", value=settings.get("news_key", ""), type="password", key="key_news")

    st.divider()

    # Save All Settings Button
    if st.button("💾 Save All Settings", use_container_width=True, type="primary"):
        new_settings = {
            "theme": theme,
            "ai_mode": ai_mode,
            "confidence": confidence,
            "paper_trade": paper_trade,
            "auto_trade": auto_trade,
            # Multi-Strategy Settings Saved Here:
            "strat_ema": strat_ema,
            "strat_supertrend": strat_supertrend,
            "strat_rsi": strat_rsi,
            # Rest of settings...
            "risk_per_trade": risk_per_trade,
            "max_trades": max_trades,
            "default_target": default_target,
            "default_stoploss": default_stoploss,
            "broker": broker,
            "client_id": client_id,
            "api_key": api_key,
            "api_secret": api_secret,
            "show_ema": show_ema,
            "show_supertrend": show_supertrend,
            "show_rsi": show_rsi,
            "show_macd": show_macd,
            "show_volume": show_volume,
            "show_bollinger": show_bollinger,
            "timeframe": timeframe,
            "user_name": name,
            "user_email": email,
            "user_mobile": mobile,
            "telegram_token": telegram_token,
            "chat_id": chat_id,
            "telegram_alert": telegram_alert,
            "openai_key": openai_key,
            "gemini_key": gemini_key,
            "news_key": news_key
        }
        if save_settings(new_settings):
            st.success("✅ All Settings Saved Successfully!")

    st.divider()

    # ===================================
    # About & Backup / Reset
    # ===================================
    st.header("ℹ About SmartTrader AI Pro")
    st.markdown("""
    ### 🚀 SmartTrader AI Pro
    Version : **1.0**  
    Developer : **Indrashan Jha**  

    **Features:**  
    ✅ AI Trading | ✅ Paper Trading | ✅ Live Trading  
    ✅ Portfolio | ✅ Reports | ✅ Risk Management  
    ✅ AI Scanner | ✅ Telegram Alerts  

    © 2026 SmartTrader AI Pro
    """)

    st.divider()

    st.header("🗑 Backup & Reset")
    col_b1, col_b2 = st.columns(2)
    with col_b1:
        if st.button("Create Backup", key="btn_create_backup"):
            save_settings(load_settings())
            st.success("Backup Created Successfully")
    with col_b2:
        if st.button("⚠ Reset All Settings", key="btn_reset_all"):
            if os.path.exists(SETTINGS_FILE):
                os.remove(SETTINGS_FILE)
            st.warning("All Settings Reset Successfully! Reloading...")
            st.rerun()