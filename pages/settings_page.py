import streamlit as st
import json
import os

SETTINGS_FILE = "settings.json"


def load_settings():

    if os.path.exists(SETTINGS_FILE):

        with open(SETTINGS_FILE, "r") as f:
            return json.load(f)

    return {}


def save_settings(settings):

    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=4)


def settings_page():

    settings = load_settings()
    
    st.title("⚙ Settings")

    st.subheader("🎨 Appearance")

    theme = st.selectbox(
        "Theme",
        ["Dark", "Light"],
        index=0 if settings.get("theme", "Dark") == "Dark" else 1
    )

    st.divider()

    st.subheader("🤖 AI Settings")

    ai_mode = st.selectbox(
        "AI Mode",
        [
            "Conservative",
            "Balanced",
            "Aggressive"
        ]
    )

    confidence = st.slider(
        "Minimum AI Confidence %",
        50,
        100,
        70
    )

    st.divider()

    st.subheader("🔔 Notifications")

    telegram = st.checkbox("Telegram Alerts")

    sound = st.checkbox("Sound Alerts")

    email = st.checkbox("Email Alerts")

    st.divider()

    st.subheader("💾 Backup")

    if st.button("Create Backup"):
        st.success("Backup Created Successfully")

    if st.button("Restore Backup"):
        st.info("Backup Restored")

    st.divider()

    if st.button("💾 Save Settings"):

        save_settings({

            "theme": theme,
            "ai_mode": ai_mode,
            "confidence": confidence,
            "telegram": telegram

        })  

        st.success("✅ Settings Saved Successfully")


# ===================================
# AI Settings
# ===================================

    st.header("🤖 AI Settings")

    ai_mode = st.selectbox(
        "AI Trading Mode",
        [
            "Conservative",
            "Balanced",
            "Aggressive"
        ]
    )

    confidence = st.slider(
        "Minimum AI Confidence %",
        50,
        100,
        70
    )

    paper_trade = st.toggle(
        "Paper Trading Mode",
        value=True
    )

    auto_trade = st.toggle(
        "Enable Auto Trading",
        value=False
    )

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
        2
    )

    max_trades = st.number_input(
        "Max Trades Per Day",
        min_value=1,
        max_value=100,
        value=5
    )

    default_target = st.number_input(
        "Default Target (Points)",
        min_value=5,
        value=40
    )

    default_stoploss = st.number_input(
        "Default Stoploss (Points)",
        min_value=5,
        value=20
    )

    st.success(
        f"""
Risk Per Trade : {risk_per_trade}%

Max Trades : {max_trades}

Default Target : {default_target}

Default Stoploss : {default_stoploss}
"""
    )

    st.divider()

# ===================================
# Broker Settings
# ===================================

    st.header("🏦 Broker Settings")

    broker = st.selectbox(
        "Select Broker",
        [
            "Kotak Neo",
            "Dhan",
            "Zerodha",
            "Upstox",
            "Angel One"
        ]
    )

    client_id = st.text_input(
        "Client ID"
    )

    api_key = st.text_input(
        "API Key",
        type="password"
    )

    api_secret = st.text_input(
        "API Secret",
        type="password"
    )

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🔗 Connect Broker"):
            st.success(f"✅ {broker} Connected Successfully")

    with col2:
        if st.button("❌ Disconnect Broker"):
            st.warning("Broker Disconnected")

    st.info(f"""
    Selected Broker : **{broker}**
    """)

    st.divider()

# ===================================
# Chart Settings
# ===================================

    st.header("📈 Chart Settings")

    show_ema = st.checkbox("Show EMA", value=True)

    show_supertrend = st.checkbox("Show SuperTrend", value=True)

    show_rsi = st.checkbox("Show RSI", value=True)

    show_macd = st.checkbox("Show MACD", value=True)

    show_volume = st.checkbox("Show Volume", value=True)

    show_bollinger = st.checkbox("Show Bollinger Bands")

    timeframe = st.selectbox(
        "Default Timeframe",
        [
            "1m",
            "3m",
            "5m",
            "15m",
            "30m",
            "1h",
            "1d"
        ],
        index=2
    )

    st.success(f"""
EMA : {'ON' if show_ema else 'OFF'}

SuperTrend : {'ON' if show_supertrend else 'OFF'}

RSI : {'ON' if show_rsi else 'OFF'}

MACD : {'ON' if show_macd else 'OFF'}

Volume : {'ON' if show_volume else 'OFF'}

Bollinger Bands : {'ON' if show_bollinger else 'OFF'}

Default Timeframe : {timeframe}
""")

    st.divider()

# ===================================
# User Profile
# ===================================

    st.header("👤 User Profile")

    name = st.text_input(
        "Full Name",
        value="Pratham Jha"
    )

    email = st.text_input(
        "Email"
    )

    mobile = st.text_input(
        "Mobile Number"
    )

    experience = st.selectbox(
        "Trading Experience",
        [
            "Beginner",
            "Intermediate",
            "Advanced"
        ]
    )

    if st.button("💾 Save Profile"):
        st.success("Profile Updated Successfully")

    st.divider()

# ===================================
# Telegram Settings
# ===================================

    st.header("📱 Telegram Settings")

    telegram_token = st.text_input(
        "Bot Token",
        type="password"
    )

    chat_id = st.text_input(
        "Chat ID"
    )

    telegram_alert = st.checkbox(
        "Enable Telegram Alerts",
        value=True
    )

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🔗 Connect Telegram"):
            st.success("Telegram Connected Successfully")

    with col2:
        if st.button("📤 Test Message"):
            st.info("Test Message Sent")

    st.success(f"""
Telegram Alerts : {'ON' if telegram_alert else 'OFF'}
""")

    st.divider()

# ===================================
# API Key Manager
# ===================================

    st.header("🔑 API Key Manager")

    openai_key = st.text_input(
        "OpenAI API Key",
        type="password"
    )

    gemini_key = st.text_input(
        "Gemini API Key",
        type="password"
    )

    news_key = st.text_input(
        "News API Key",
        type="password"
    )

    if st.button("💾 Save API Keys"):
        st.success("API Keys Saved Successfully")

    st.info("""
    🔒 Your API keys remain hidden.
    """)

    st.divider()

# ===================================
# About
# ===================================

    st.header("ℹ About SmartTrader AI Pro")

    st.markdown("""
    ### 🚀 SmartTrader AI Pro

    Version : **1.0**

    Developer : **Indrashan Jha**

    Features

    ✅ AI Trading

    ✅ Paper Trading

    ✅ Live Trading

    ✅ Portfolio

    ✅ Reports

    ✅ Risk Management

    ✅ AI Scanner

    ✅ Telegram Alerts

    © 2026 SmartTrader AI Pro
    """)

    st.divider()

# ===================================
# Reset Settings
# ===================================

    st.header("🗑 Reset Settings")

    if st.button("⚠ Reset All Settings"):

        st.warning("All Settings Reset Successfully")