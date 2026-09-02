import streamlit as st
import json
import os
from pathlib import Path
from datetime import datetime


# =========================================================
# FILE PATHS
# =========================================================

BASE_DIR = Path(__file__).resolve().parent.parent

SETTINGS_FILE = BASE_DIR / "settings.json"
BACKUP_DIR = BASE_DIR / "backups"


# =========================================================
# DEFAULT SETTINGS
# =========================================================

DEFAULT_SETTINGS = {
    "theme": "Dark",

    # AI
    "ai_mode": "Balanced",
    "confidence": 70,

    # Trading
    "paper_trade": True,
    "auto_trade": False,

    # Multi Strategy
    "strat_ema": True,
    "strat_supertrend": True,
    "strat_rsi": True,

    # Risk
    "risk_per_trade": 2,
    "max_trades": 5,
    "default_target": 40,
    "default_stoploss": 20,

    # Trailing Stoploss
    "trailing_enabled": True,
    "trailing_points": 10,

    # Broker
    "broker": "Kotak Neo",
    "client_id": "",
    "api_key": "",
    "api_secret": "",

    # Chart
    "show_ema": True,
    "show_supertrend": True,
    "show_rsi": True,
    "show_macd": True,
    "show_volume": True,
    "show_bollinger": False,
    "timeframe": "5m",

    # User
    "user_name": "Pratham Jha",
    "user_email": "",
    "user_mobile": "",

    # Telegram
    "telegram_token": "",
    "chat_id": "",
    "telegram_alert": True,

    # AI API
    "openai_key": "",
    "gemini_key": "",
    "news_key": "",
}


# =========================================================
# LOAD SETTINGS
# =========================================================

def load_settings():

    try:

        if SETTINGS_FILE.exists():

            with open(
                SETTINGS_FILE,
                "r",
                encoding="utf-8"
            ) as f:

                data = json.load(f)

            if isinstance(data, dict):

                # Missing settings automatically get defaults
                settings = DEFAULT_SETTINGS.copy()
                settings.update(data)

                return settings

    except Exception as e:

        st.warning(
            f"⚠️ Settings load error: {e}"
        )

    return DEFAULT_SETTINGS.copy()


# =========================================================
# SAVE SETTINGS
# =========================================================

def save_settings(settings):

    try:

        SETTINGS_FILE.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        current = load_settings()

        if not isinstance(current, dict):
            current = {}

        current.update(settings)

        with open(
            SETTINGS_FILE,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                current,
                f,
                indent=4,
                ensure_ascii=False
            )

        return True

    except Exception as e:

        st.error(
            f"❌ Failed to save settings: {e}"
        )

        return False


# =========================================================
# CREATE BACKUP
# =========================================================

def create_backup():

    try:

        BACKUP_DIR.mkdir(
            parents=True,
            exist_ok=True
        )

        settings = load_settings()

        timestamp = datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )

        backup_file = (
            BACKUP_DIR /
            f"settings_backup_{timestamp}.json"
        )

        with open(
            backup_file,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                settings,
                f,
                indent=4,
                ensure_ascii=False
            )

        return backup_file

    except Exception as e:

        st.error(
            f"❌ Backup failed: {e}"
        )

        return None


# =========================================================
# SETTINGS PAGE
# =========================================================

def settings_page():

    settings = load_settings()

    st.title("⚙️ Settings")

    st.caption(
        "SmartTrader AI Pro Configuration"
    )

    # =====================================================
    # APPEARANCE
    # =====================================================

    st.header("🎨 Appearance")

    theme = st.selectbox(
        "Theme",
        [
            "Dark",
            "Light"
        ],
        index=(
            0
            if settings.get(
                "theme",
                "Dark"
            ) == "Dark"
            else 1
        ),
        key="app_theme"
    )

    st.divider()
    # =====================================================
    # AI SETTINGS
    # =====================================================

    st.header("🤖 AI Settings")

    ai_modes = [
        "Conservative",
        "Balanced",
        "Aggressive"
    ]

    saved_mode = settings.get(
        "ai_mode",
        "Balanced"
    )

    mode_idx = (
        ai_modes.index(saved_mode)
        if saved_mode in ai_modes
        else 1
    )

    ai_mode = st.selectbox(
        "AI Trading Mode",
        ai_modes,
        index=mode_idx,
        key="ai_mode_select"
    )

    confidence = st.slider(
        "Minimum AI Confidence (%)",
        min_value=50,
        max_value=100,
        value=int(
            settings.get(
                "confidence",
                70
            )
        ),
        step=1,
        key="ai_confidence_slider"
    )

    paper_trade = st.toggle(
        "🧪 Paper Trading Mode",
        value=bool(
            settings.get(
                "paper_trade",
                True
            )
        ),
        key="paper_trade_toggle"
    )

    # =====================================================
    # AUTO TRADING
    # =====================================================

    auto_trade = st.toggle(
        "🤖 Enable Auto Trading",
        value=bool(
            settings.get(
                "auto_trade",
                True
            )
        ),
        key="auto_trade_toggle"
    )
   
    # =====================================================
    # STATUS
    # =====================================================

    if paper_trade:

        st.success(
            "🟢 Paper Trading is ON"
        )

        if auto_trade:
            st.success(
                "🤖 Auto Paper Trading is ON"
            )
        else:
            st.info(
                "🔵 Auto Paper Trading is OFF"
            )

    else:

        st.warning(
            "⚠️ Paper Trading is OFF"
        )

        if auto_trade:
            st.warning(
                "⚠️ Auto Trading is ON, but Paper Trading is OFF."
            )
        else:
            st.info(
                "🔵 Auto Trading is OFF"
            )

    st.info(
        f"""
    **AI Mode:** {ai_mode}

    **Minimum Confidence:** {confidence}%

    **Paper Trading:** {"ON" if paper_trade else "OFF"}

    **Auto Trading:** {"ON" if auto_trade else "OFF"}
    """
    )

    st.divider()

    # =====================================================
    # MULTI STRATEGY
    # =====================================================

    st.header(
        "🤖 Multi-Strategy AI Confirmation"
    )

    st.caption(
        "Select strategies used for trade confirmation."
    )

    strat_ema = st.checkbox(
        "EMA Crossover Strategy",
        value=bool(
            settings.get(
                "strat_ema",
                True
            )
        ),
        key="chk_strat_ema"
    )

    strat_supertrend = st.checkbox(
        "SuperTrend Strategy",
        value=bool(
            settings.get(
                "strat_supertrend",
                True
            )
        ),
        key="chk_strat_supertrend"
    )

    strat_rsi = st.checkbox(
        "RSI Momentum Strategy",
        value=bool(
            settings.get(
                "strat_rsi",
                True
            )
        ),
        key="chk_strat_rsi"
    )

    selected_count = sum([
        strat_ema,
        strat_supertrend,
        strat_rsi
    ])

    st.info(
        f"📊 Selected Strategies: "
        f"**{selected_count}/3**"
    )

    if selected_count == 0:

        st.error(
            "❌ At least one strategy should be enabled."
        )

    st.divider()

    # =====================================================
    # RISK MANAGEMENT
    # =====================================================

    st.header("💰 Risk Management")

    risk_per_trade = st.slider(
        "Risk Per Trade (%)",
        min_value=1,
        max_value=10,
        value=int(
            settings.get(
                "risk_per_trade",
                2
            )
        ),
        step=1,
        key="risk_slider"
    )

    max_trades = st.number_input(
        "Max Trades Per Day",
        min_value=1,
        max_value=100,
        value=int(
            settings.get(
                "max_trades",
                5
            )
        ),
        step=1,
        key="max_trades_input"
    )

    default_target = st.number_input(
        "Default Target (Points)",
        min_value=5,
        max_value=10000,
        value=int(
            settings.get(
                "default_target",
                40
            )
        ),
        step=5,
        key="target_input"
    )

    default_stoploss = st.number_input(
        "Default Stoploss (Points)",
        min_value=5,
        max_value=10000,
        value=int(
            settings.get(
                "default_stoploss",
                20
            )
        ),
        step=5,
        key="stoploss_input"
    )

    st.divider()

    # =====================================================
    # TRAILING STOPLOSS
    # =====================================================

    st.header("📈 Trailing Stoploss")

    trailing_enabled = st.toggle(
        "Enable Trailing Stoploss",
        value=bool(
            settings.get(
                "trailing_enabled",
                True
            )
        ),
        key="trailing_enabled_toggle"
    )

    trailing_points = st.number_input(
        "Trailing Stoploss (Points)",
        min_value=1,
        max_value=10000,
        value=int(
            settings.get(
                "trailing_points",
                10
            )
        ),
        step=1,
        key="trailing_points_input"
    )

    if trailing_enabled:

        st.success(
            f"🟢 Trailing Stoploss ON — "
            f"{trailing_points} points"
        )

        st.info(
            """
Price आपके पक्ष में जाने पर Stoploss
automatically आगे move होगा।

Example BUY:
Entry 100 → Initial SL 80
Price 110 → Trailing SL 100
Price 120 → Trailing SL 110
"""
        )

    else:

        st.warning(
            "Trailing Stoploss OFF"
        )

    st.divider()

    # =====================================================
    # BROKER SETTINGS
    # =====================================================

    st.header("🏦 Broker Settings")

    brokers = [
        "Kotak Neo",
        "Dhan",
        "Zerodha",
        "Upstox",
        "Angel One"
    ]

    saved_broker = settings.get(
        "broker",
        "Kotak Neo"
    )

    broker_idx = (
        brokers.index(saved_broker)
        if saved_broker in brokers
        else 0
    )

    broker = st.selectbox(
        "Select Broker",
        brokers,
        index=broker_idx,
        key="broker_select"
    )

    client_id = st.text_input(
        "Client ID",
        value=settings.get(
            "client_id",
            ""
        ),
        key="client_id_input"
    )

    api_key = st.text_input(
        "API Key",
        value=settings.get(
            "api_key",
            ""
        ),
        type="password",
        key="api_key_input"
    )

    api_secret = st.text_input(
        "API Secret",
        value=settings.get(
            "api_secret",
            ""
        ),
        type="password",
        key="api_secret_input"
    )

    col1, col2 = st.columns(2)

    with col1:

        if st.button(
            "🔗 Test Broker",
            key="btn_connect_broker",
            use_container_width=True
        ):

            if not client_id:

                st.warning(
                    "Client ID required."
                )

            elif not api_key:

                st.warning(
                    "API Key required."
                )

            else:

                st.info(
                    f"Broker credentials entered "
                    f"for {broker}. "
                    f"Actual API connection is not "
                    f"performed by Settings page."
                )

    with col2:

        if st.button(
            "❌ Disconnect",
            key="btn_disconnect_broker",
            use_container_width=True
        ):

            st.info(
                "Broker session disconnected."
            )

    st.divider()

    # =====================================================
    # CHART SETTINGS
    # =====================================================

    st.header("📊 Chart Settings")

    show_ema = st.checkbox(
        "Show EMA",
        value=bool(
            settings.get(
                "show_ema",
                True
            )
        ),
        key="chk_ema"
    )

    show_supertrend = st.checkbox(
        "Show SuperTrend",
        value=bool(
            settings.get(
                "show_supertrend",
                True
            )
        ),
        key="chk_supertrend"
    )

    show_rsi = st.checkbox(
        "Show RSI",
        value=bool(
            settings.get(
                "show_rsi",
                True
            )
        ),
        key="chk_rsi"
    )

    show_macd = st.checkbox(
        "Show MACD",
        value=bool(
            settings.get(
                "show_macd",
                True
            )
        ),
        key="chk_macd"
    )

    show_volume = st.checkbox(
        "Show Volume",
        value=bool(
            settings.get(
                "show_volume",
                True
            )
        ),
        key="chk_volume"
    )

    show_bollinger = st.checkbox(
        "Show Bollinger Bands",
        value=bool(
            settings.get(
                "show_bollinger",
                False
            )
        ),
        key="chk_bollinger"
    )

    timeframes = [
        "1m",
        "3m",
        "5m",
        "15m",
        "30m",
        "1h",
        "1d"
    ]

    saved_tf = settings.get(
        "timeframe",
        "5m"
    )

    tf_idx = (
        timeframes.index(saved_tf)
        if saved_tf in timeframes
        else 2
    )

    timeframe = st.selectbox(
        "Default Timeframe",
        timeframes,
        index=tf_idx,
        key="tf_select"
    )

    st.divider()

    # =====================================================
    # USER PROFILE
    # =====================================================

    st.header("👤 User Profile")

    name = st.text_input(
        "Full Name",
        value=settings.get(
            "user_name",
            "Pratham Jha"
        ),
        key="user_name_input"
    )

    email = st.text_input(
        "Email",
        value=settings.get(
            "user_email",
            ""
        ),
        key="user_email_input"
    )

    mobile = st.text_input(
        "Mobile Number",
        value=settings.get(
            "user_mobile",
            ""
        ),
        key="user_mobile_input"
    )

    st.divider()

    # =====================================================
    # TELEGRAM
    # =====================================================

    st.header("📱 Telegram Settings")

    telegram_token = st.text_input(
        "Bot Token",
        value=settings.get(
            "telegram_token",
            ""
        ),
        type="password",
        key="tg_token"
    )

    chat_id = st.text_input(
        "Chat ID",
        value=settings.get(
            "chat_id",
            ""
        ),
        key="tg_chat_id"
    )

    telegram_alert = st.checkbox(
        "Enable Telegram Alerts",
        value=bool(
            settings.get(
                "telegram_alert",
                True
            )
        ),
        key="chk_tg_alert"
    )

    col1, col2 = st.columns(2)

    with col1:

        if st.button(
            "🔗 Test Telegram",
            key="btn_tg_connect",
            use_container_width=True
        ):

            if not telegram_token:

                st.warning(
                    "Telegram Bot Token required."
                )

            elif not chat_id:

                st.warning(
                    "Telegram Chat ID required."
                )

            else:

                st.info(
                    "Telegram credentials entered. "
                    "Actual message sending requires "
                    "Telegram API integration."
                )

    with col2:

        if st.button(
            "📤 Test Message",
            key="btn_tg_test",
            use_container_width=True
        ):

            st.info(
                "Telegram API integration is not "
                "enabled in this Settings module yet."
            )

    st.divider()

    # =====================================================
    # API KEY MANAGER
    # =====================================================

    st.header("🔑 API Key Manager")

    openai_key = st.text_input(
        "OpenAI API Key",
        value=settings.get(
            "openai_key",
            ""
        ),
        type="password",
        key="key_openai"
    )

    gemini_key = st.text_input(
        "Gemini API Key",
        value=settings.get(
            "gemini_key",
            ""
        ),
        type="password",
        key="key_gemini"
    )

    news_key = st.text_input(
        "News API Key",
        value=settings.get(
            "news_key",
            ""
        ),
        type="password",
        key="key_news"
    )

    st.divider()

    # =====================================================
    # SAVE ALL SETTINGS
    # =====================================================

    if st.button(
        "💾 Save All Settings",
        use_container_width=True,
        type="primary",
        key="save_all_settings"
    ):

        # Safety
        if selected_count == 0:

            st.error(
                "❌ Enable at least one strategy."
            )

        elif trailing_enabled and trailing_points <= 0:

            st.error(
                "❌ Trailing points must be greater than 0."
            )

        else:

            new_settings = {

                # Appearance
                "theme": theme,

                # AI
                "ai_mode": ai_mode,
                "confidence": confidence,

                # Trading
                "paper_trade": paper_trade,
                "auto_trade": auto_trade,

                # Strategies
                "strat_ema": strat_ema,
                "strat_supertrend": strat_supertrend,
                "strat_rsi": strat_rsi,

                # Risk
                "risk_per_trade": risk_per_trade,
                "max_trades": max_trades,
                "default_target": default_target,
                "default_stoploss": default_stoploss,

                # Trailing
                "trailing_enabled": trailing_enabled,
                "trailing_points": trailing_points,

                # Broker
                "broker": broker,
                "client_id": client_id,
                "api_key": api_key,
                "api_secret": api_secret,

                # Chart
                "show_ema": show_ema,
                "show_supertrend": show_supertrend,
                "show_rsi": show_rsi,
                "show_macd": show_macd,
                "show_volume": show_volume,
                "show_bollinger": show_bollinger,
                "timeframe": timeframe,

                # User
                "user_name": name,
                "user_email": email,
                "user_mobile": mobile,

                # Telegram
                "telegram_token": telegram_token,
                "chat_id": chat_id,
                "telegram_alert": telegram_alert,

                # APIs
                "openai_key": openai_key,
                "gemini_key": gemini_key,
                "news_key": news_key,
            }

            if save_settings(new_settings):

                st.success(
                    "✅ All Settings Saved Successfully!"
                )

                st.rerun()

    st.divider()

    # =====================================================
    # ABOUT
    # =====================================================

    st.header(
        "ℹ️ About SmartTrader AI Pro"
    )

    st.markdown(
        """
### 🚀 SmartTrader AI Pro

**Version:** 1.0  
**Developer:** Indrashan Jha  

**Features:**

✅ AI Trading  
✅ Paper Trading  
✅ Live Trading Module  
✅ Portfolio  
✅ Reports  
✅ Risk Management  
✅ AI Scanner  
✅ Multi-Strategy Confirmation  
✅ Trailing Stoploss  
✅ Telegram Alerts  

© 2026 SmartTrader AI Pro
"""
    )

    st.divider()

    # =====================================================
    # BACKUP & RESET
    # =====================================================

    st.header(
        "💾 Backup & Reset"
    )

    col_b1, col_b2 = st.columns(2)

    with col_b1:

        if st.button(
            "💾 Create Backup",
            key="btn_create_backup",
            use_container_width=True
        ):

            backup_file = create_backup()

            if backup_file:

                st.success(
                    "✅ Backup Created Successfully!"
                )

                st.caption(
                    f"Backup: {backup_file.name}"
                )

    with col_b2:

        if st.button(
            "⚠️ Reset All Settings",
            key="btn_reset_all",
            use_container_width=True
        ):

            st.session_state[
                "confirm_reset"
            ] = True

    # =====================================================
    # RESET CONFIRMATION
    # =====================================================

    if st.session_state.get(
        "confirm_reset",
        False
    ):

        st.error(
            "⚠️ Are you sure you want to reset "
            "all settings?"
        )

        col_r1, col_r2 = st.columns(2)

        with col_r1:

            if st.button(
                "✅ Yes, Reset",
                key="confirm_reset_yes",
                use_container_width=True
            ):

                try:

                    if SETTINGS_FILE.exists():

                        SETTINGS_FILE.unlink()

                    st.session_state[
                        "confirm_reset"
                    ] = False

                    st.success(
                        "✅ All Settings Reset Successfully!"
                    )

                    st.rerun()

                except Exception as e:

                    st.error(
                        f"❌ Reset failed: {e}"
                    )

        with col_r2:

            if st.button(
                "❌ Cancel",
                key="confirm_reset_no",
                use_container_width=True
            ):

                st.session_state[
                    "confirm_reset"
                ] = False

                st.rerun()