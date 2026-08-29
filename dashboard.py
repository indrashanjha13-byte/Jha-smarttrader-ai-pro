from pathlib import Path
from datetime import datetime
import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from PIL import Image

from streamlit_autorefresh import st_autorefresh

# ------------------------
# Project Imports
# ------------------------

from signals import get_signals

from strategy import (
    generate_signal,
    ema_signal,
    rsi_signal,
    supertrend_signal
)

from ai_engine import (
    ai_brain,
    confidence_score,
    stop_target,
    position_size,
    trailing_stop,
    daily_risk_manager
)

from ai_signal_ranker import signal_score

from paper_trading import PaperTrader

from ai_learning import (
    load_learning,
    update_learning,
    best_strategy,
    auto_strategy
)

from market_memory import best_market_strategy
from auto_mode import (
    enable_auto,
    disable_auto,
    is_enabled,
    get_scan_interval
)
from option_chain import scan_all_option_chain
from fo_symbols import INDICES, FO_STOCKS
import plotly.express as px
from broker.broker_manager import BrokerManager
from backtest_engine import BacktestEngine
from settings_manager import load_settings, save_settings
from paper_trading import PaperTrader
from pages.dashboard_page import dashboard_page
from pages.market_page import market_page
from pages.portfolio_page import portfolio_page
from pages.reports_page import reports_page
from pages.settings_page import settings_page
from pages.trading_page import trading_page
print(PaperTrader)
print(PaperTrader.__module__)
print(dir(PaperTrader))


# ------------------------
# Streamlit Config
# ------------------------

st.set_page_config(
    page_title="Jha SmartTrader AI Pro",
    page_icon="📈",
    layout="wide"
)

st.markdown("""
<style>

.block-container{
    padding-top:1rem;
}

div[data-testid="stMetric"]{
    background:#1b1f2a;
    border-radius:15px;
    padding:15px;
    border:1px solid #2f3545;
    box-shadow:0px 0px 10px rgba(0,0,0,0.3);
}

div[data-testid="stMetric"]:hover{
    border:1px solid #00ff88;
    transform:scale(1.02);
}

</style>
""", unsafe_allow_html=True)

# ------------------------
# Auto Refresh
# ------------------------

st_autorefresh(
    interval=15000,
    key="market_refresh"
)

# ------------------------
# Session
# ------------------------

if "trader" not in st.session_state:
    st.session_state.trader = PaperTrader()

trader = st.session_state.trader

if "backtester" not in st.session_state:
    st.session_state.backtester = BacktestEngine()

backtester = st.session_state.backtester


# ==========================
# Load Saved Settings
# ==========================
settings = load_settings()

# ------------------------
# Logo
# ------------------------

BASE_DIR = Path(__file__).resolve().parent

logo = BASE_DIR / "logo.png"

if logo.exists():

    try:

        st.image(
            Image.open(logo),
            width=150
        )

    except:
        pass

# ------------------------
# Sidebar
# ------------------------

st.sidebar.markdown("## 📈 Jha SmartTrader AI Pro")
st.sidebar.caption("AI Powered Trading Terminal")

st.sidebar.divider()

st.sidebar.success("🟢 Market : OPEN")
st.sidebar.info("💰 Balance : ₹100000")
st.sidebar.write("🤖 AI : ACTIVE")
st.sidebar.write("🏦 Broker : Kotak Neo")

st.sidebar.divider()

page = st.sidebar.radio(

    "📂 Navigation",

    [
        "🏠 Dashboard",
        "📈 Market",
        "🤖 AI",
        "💰 Trading",
        "📦 Portfolio",
        "📊 Reports",
        "⚙ Settings",
        "👤 Broker"
    ]

)

st.sidebar.title("⚙ Settings")

symbols = [
    "^NSEI",
    "^NSEBANK",
    "^BSESN",
    "RELIANCE.NS",
    "TCS.NS",
    "INFY.NS",
    "HDFCBANK.NS",
    "ICICIBANK.NS",
    "SBIN.NS",
    "LT.NS",
    "AXISBANK.NS"
]

symbol = st.sidebar.selectbox(
    "Select Symbol",
    symbols,
    index=symbols.index(settings["symbol"])
)

strategies = [
    "EMA Crossover",
    "RSI",
    "SuperTrend",
    "MACD + Volume",
    "AI Combo"
]

strategy_name = st.sidebar.selectbox(
    "Strategy",
    strategies,
    index=strategies.index(settings["strategy"])
)

if strategy_name == "AI Combo":

    strategy_name = auto_strategy()

    st.sidebar.success(
        f"🤖 AI Selected Strategy : {strategy_name}"
    )

options = ["CE", "PE"]

option_side = st.sidebar.selectbox(
    "Option",
    options,
    index=options.index(settings["option"])
)

strikes = ["ITM", "ATM", "OTM"]

strike_mode = st.sidebar.selectbox(
    "Strike",
    strikes,
    index=strikes.index(settings["strike"])
)

# =====================================
# DASHBOARD PAGE
# =====================================

if page == "🏠 Dashboard":

    signal = get_signals(symbol)
    current_price = signal["Close"]

    dashboard_page(

    trader=trader,

    current_price=current_price,

    symbol=symbol

)



# ------------------------
# Scanner Button
# ------------------------

run_scan = st.button("🚀 Run Scanner")


AUTO_SCAN = False

if is_enabled():
    AUTO_SCAN = True

if AUTO_SCAN:
    run_scan = True

if is_enabled():

    st.success("🤖 AUTO TRADING RUNNING")

    #time.sleep(get_scan_interval())

    run_scan = True


# =====================================
# MARKET PAGE
# =====================================

if page == "📈 Market":

    market_page(
        symbol,
        trader,
        INDICES,
        FO_STOCKS,
        scan_all_option_chain
    )
# =====================================
# TRADING PAGE
# =====================================

if page == "💰 Trading":

    trading_page(
        trader=trader,
        symbol=symbol
    )
# ==========================================================

st.divider()

st.success("✅ Jha SmartTrader AI Pro Loaded Successfully")

st.caption(

    f"Last Refresh : {datetime.now()}"

)