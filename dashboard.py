from pathlib import Path
from datetime import datetime

import streamlit as st
from PIL import Image

from streamlit_autorefresh import st_autorefresh

# =========================
# Project Imports
# =========================

from signals import get_signals

from paper_trading import PaperTrader
from trade_manager import TradeManager
from backtest_engine import BacktestEngine

from ai_decision import ai_decision

from ai_learning import auto_strategy
from market_memory import best_market_strategy

from auto_mode import (
    is_enabled,
    enable_auto,
    disable_auto
)

from option_chain import scan_all_option_chain
from fo_symbols import INDICES, FO_STOCKS

from settings_manager import load_settings

# =========================
# Pages
# =========================

from pages.dashboard_page import dashboard_page
from pages.market_page import market_page
from pages.portfolio_page import portfolio_page
from pages.reports_page import reports_page
from pages.settings_page import settings_page
from delta_futures import DeltaFutures

from pages.trading_page import trading_page


# =========================
# Streamlit Configuration
# =========================

st.set_page_config(
    page_title="Jha SmartTrader AI Pro",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)


# =========================
# Custom CSS
# =========================

st.markdown(
    """
    <style>

    .block-container {
        padding-top: 1rem;
    }

    div[data-testid="stMetric"] {
        background: #1b1f2a;
        border-radius: 15px;
        padding: 15px;
        border: 1px solid #2f3545;
    }

    div[data-testid="stMetric"]:hover {
        border: 1px solid #00ff88;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# =========================
# Auto Refresh
# =========================

try:
    st_autorefresh(
        interval=15000,
        key="market_refresh"
    )
except Exception:
    pass

# ============================================
# Session State
# ============================================

# Paper Trader
if "trader" not in st.session_state:
    st.session_state.trader = PaperTrader(
        initial_balance=100000
    )

trader = st.session_state.trader


# Trade Manager
if "trade_manager" not in st.session_state:
    st.session_state.trade_manager = TradeManager(
        paper_trader=trader
    )

trade_manager = st.session_state.trade_manager

# Ensure PaperTrader is connected
try:
    trade_manager.set_paper_trader(trader)
except Exception:
    pass


# Backtester
if "backtester" not in st.session_state:
    st.session_state.backtester = BacktestEngine()

backtester = st.session_state.backtester
# =========================
# Settings
# =========================

try:
    settings = load_settings()

    if not isinstance(settings, dict):
        settings = {}

except Exception:
    settings = {}
    
# =========================
# Trailing Stoploss Settings
# =========================

trailing_enabled = settings.get(
    "trailing_enabled",
    False
)

trailing_start = float(
    settings.get(
        "trailing_start",
        10
    )
)

trailing_distance = float(
    settings.get(
        "trailing_distance",
        5
    )
)

trade_manager.set_trailing_settings(
    enabled=trailing_enabled,
    start=trailing_start,
    distance=trailing_distance
)


# =========================
# Sidebar Logo
# =========================

BASE_DIR = Path(__file__).resolve().parent
logo_path = BASE_DIR / "logo.png"

if logo_path.exists():

    try:
        logo_image = Image.open(logo_path)

        st.sidebar.image(
            logo_image,
            width=150
        )

    except Exception:
        pass


# =========================
# Sidebar Header
# =========================

st.sidebar.markdown(
    "## 📈 Jha SmartTrader AI Pro"
)

st.sidebar.caption(
    "AI Powered Trading Terminal"
)

st.sidebar.divider()


# =========================
# Trading Status
# =========================

st.sidebar.success(
    "🟢 Market System : ONLINE"
)

st.sidebar.info(
    f"💰 Paper Balance : ₹{getattr(trader, 'balance', 100000):,.2f}"
)

st.sidebar.write(
    "🤖 AI Engine : ACTIVE"
)

st.sidebar.write(
    "🏦 Broker : "
    + str(settings.get("broker", "Kotak Neo"))
)

st.sidebar.divider()


# =========================
# Navigation
# =========================

page = st.sidebar.radio(
    "📂 Navigation",
    [
        "🏠 Dashboard",
        "📈 Market",
        "💰 Trading",
        "📦 Portfolio",
        "📊 Reports",
        "⚙ Settings"
    ]
)


# =========================
# Parameters
# =========================

st.sidebar.title("⚙ Parameters")


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


default_symbol = settings.get(
    "symbol",
    "^NSEI"
)

if default_symbol not in symbols:
    default_symbol = "^NSEI"


symbol = st.sidebar.selectbox(
    "Select Symbol",
    symbols,
    index=symbols.index(default_symbol)
)


# =========================
# Strategy
# =========================

strategies = [
    "EMA Crossover",
    "RSI",
    "SuperTrend",
    "MACD + Volume",
    "AI Combo"
]


default_strategy = settings.get(
    "strategy",
    "AI Combo"
)


if default_strategy not in strategies:
    default_strategy = "AI Combo"


strategy_name = st.sidebar.selectbox(
    "Strategy",
    strategies,
    index=strategies.index(default_strategy)
)


if strategy_name == "AI Combo":

    try:

        selected_strategy = auto_strategy()

        if selected_strategy:
            st.sidebar.success(
                f"🤖 AI Strategy : {selected_strategy}"
            )

    except Exception:

        st.sidebar.caption(
            "AI Strategy : Default"
        )


# =========================
# Market Settings
# =========================

market_types = [
    "OPTIONS",
    "FUTURES"
]

default_market = settings.get(
    "market_type",
    "OPTIONS"
)

if default_market not in market_types:
    default_market = "OPTIONS"


market_type = st.sidebar.selectbox(
    "Market",
    market_types,
    index=market_types.index(default_market)
)


# =========================
# Option Settings
# =========================

if market_type == "OPTIONS":

    options = [
        "CE",
        "PE",
        "ALL"
    ]

    default_option = settings.get(
        "option",
        "CE"
    )

    if default_option not in options:
        default_option = "CE"


    option_side = st.sidebar.selectbox(
        "Option",
        options,
        index=options.index(default_option)
    )


    strikes = [
        "ITM",
        "ATM",
        "OTM"
    ]

    default_strike = settings.get(
        "strike",
        "ATM"
    )

    if default_strike not in strikes:
        default_strike = "ATM"


    strike_mode = st.sidebar.selectbox(
        "Strike",
        strikes,
        index=strikes.index(default_strike)
    )


# =========================
# Delta Futures Settings
# =========================

else:

    try:

        delta = DeltaFutures()

        futures_data = delta.get_futures()

        futures_symbols = []

        for product in futures_data:

            symbol = product.get("symbol")

            contract_type = str(
                product.get(
                    "contract_type",
                    ""
                )
            ).lower()

            if (
                symbol
                and contract_type in (
                    "futures",
                    "perpetual_futures"
                )
            ):
                futures_symbols.append(
                    str(symbol).strip().upper()
                )

        # Remove duplicates
        futures_symbols = sorted(
            list(set(futures_symbols))
        )

        if not futures_symbols:

            st.sidebar.warning(
                "⚠️ No Delta Futures contracts found."
            )

    except Exception as e:

        futures_symbols = []

        st.sidebar.error(
            f"Delta Futures Error: {e}"
        )

    # =========================
    # Fallback
    # =========================

    if not futures_symbols:

        futures_symbols = [
            "BTCUSD",
            "ETHUSD"
        ]


    # =========================
    # Default Futures
    # =========================

    default_futures = settings.get(
        "futures_symbol",
        futures_symbols[0]
    )

    if default_futures not in futures_symbols:

        default_futures = (
            futures_symbols[0]
        )


    # =========================
    # Futures Selector
    # =========================

    futures_symbol = st.sidebar.selectbox(
        "Delta Futures",
        futures_symbols,
        index=futures_symbols.index(
            default_futures
        )
    )


    # Options are not used
    option_side = "N/A"
    strike_mode = "N/A"

# =========================
# Futures Live Price
# =========================

if market_type == "FUTURES":

    try:

        delta = DeltaFutures()

        # Make sure the selected symbol is clean
        futures_symbol = str(
            futures_symbol
        ).strip().upper()

        ticker = delta.get_ticker(
            futures_symbol
        )

        if ticker:

            current_price = float(
                ticker.get(
                    "mark_price",
                    ticker.get(
                        "close",
                        ticker.get(
                            "last_price",
                            0
                        )
                    )
                ) or 0
            )

            if current_price > 0:

                st.sidebar.success(
                    f"💰 {futures_symbol} "
                    f"Price: {current_price:,.2f}"
                )

            else:

                st.sidebar.warning(
                    f"⚠️ {futures_symbol} "
                    "ticker received but price is 0"
                )

        else:

            current_price = 0.0

            st.sidebar.warning(
                f"⚠️ No market data available "
                f"for {futures_symbol}"
            )

    except Exception as e:

        current_price = 0.0

        st.sidebar.error(
            f"Delta Price Error: {e}"
        )

# =========================
# Trading Mode
# =========================

st.sidebar.divider()
st.sidebar.subheader("🤖 Trading Mode")


# -------------------------
# Paper Trading
# -------------------------

paper_trading = st.sidebar.toggle(
    "🟢 Paper Trading",
    value=not is_enabled(),
    key="paper_trading_switch"
)


# -------------------------
# Live Auto Trading
# -------------------------

live_auto_trading = st.sidebar.toggle(
    "🔴 Live Auto Trading",
    value=is_enabled(),
    key="live_auto_trading_switch"
)


# =========================
# Mode Control
# =========================

if live_auto_trading:

    enable_auto()

    st.sidebar.warning(
        "⚠️ LIVE AUTO TRADING : ON"
    )

    live_confirm = st.sidebar.checkbox(
        "I confirm real orders can be placed",
        key="live_trade_confirmation"
    )

    if not live_confirm:

        disable_auto()

        st.sidebar.error(
            "🔒 Live trading locked — confirmation required"
        )


elif paper_trading:

    disable_auto()

    st.sidebar.success(
        "🟢 PAPER TRADING : ON"
    )


else:

    disable_auto()

    st.sidebar.info(
        "⚪ Trading : OFF"
    )

# =========================================================
# DASHBOARD
# =========================================================

if page == "🏠 Dashboard":

    try:

        signal_data = get_signals(symbol)

    except Exception as e:

        signal_data = {
            "error": str(e)
        }


    if not isinstance(signal_data, dict):

        signal_data = {
            "error": "Invalid signal response"
        }


    if "error" in signal_data:

        current_price = 0.0

        st.warning(
            f"⚠️ Market data unavailable: "
            f"{signal_data.get('error')}"
        )

    else:

        current_price = float(
            signal_data.get(
                "Close",
                0.0
            ) or 0.0
        )


    try:

        dashboard_page(
            trader=trader,
            current_price=current_price,
            symbol=symbol
        )

    except Exception as e:

        st.error(
            f"❌ Dashboard Error: {e}"
        )


# =========================================================
# MARKET
# =========================================================

elif page == "📈 Market":

    try:

        market_page(
            symbol=symbol,
            trader=trader,
            INDICES=INDICES,
            FO_STOCKS=FO_STOCKS,
            scan_all_option_chain=scan_all_option_chain
        )

    except Exception as e:

        st.error(
            f"❌ Market Page Error: {e}"
        )


# =========================================================
# TRADING
# =========================================================

elif page == "💰 Trading":

    if trading_page is None:

        st.error(
            "❌ pages/trading_page.py में "
            "`trading_page()` function नहीं मिला।"
        )

    else:

        try:

            trading_page(
                trader=trader,
                symbol=symbol
            )

        except Exception as e:

            st.error(
                f"❌ Trading Page Error: {e}"
            )


# =========================================================
# PORTFOLIO
# =========================================================

elif page == "📦 Portfolio":

    try:

        portfolio_page(
            trader=trader,
            symbol=symbol
        )

    except TypeError:

        # Compatibility fallback
        try:

            portfolio_page(
                trader=trader
            )

        except Exception as e:

            st.error(
                f"❌ Portfolio Error: {e}"
            )

    except Exception as e:

        st.error(
            f"❌ Portfolio Error: {e}"
        )


# =========================================================
# REPORTS
# =========================================================

elif page == "📊 Reports":

    try:

        reports_page(
            backtester=backtester
        )

    except TypeError:

        try:

            reports_page()

        except Exception as e:

            st.error(
                f"❌ Reports Error: {e}"
            )

    except Exception as e:

        st.error(
            f"❌ Reports Error: {e}"
        )


# =========================================================
# SETTINGS
# =========================================================

elif page == "⚙ Settings":

    try:

        settings_page()

    except Exception as e:

        st.error(
            f"❌ Settings Error: {e}"
        )


# =========================
# Footer
# =========================

st.divider()

st.caption(
    "Jha SmartTrader AI Pro • "
    "AI Trading Terminal"
)

st.caption(
    f"Last Refresh : "
    f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
)
