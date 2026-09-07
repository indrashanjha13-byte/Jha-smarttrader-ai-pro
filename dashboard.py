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

from index_config import INDIAN_OPTION_INDICES
from option_contracts import (
    resolve_option_contract,
    get_lot_size,
    get_strike_modes,
)
from multi_index_scanner import (
    scan_indices,
    get_best_signal,
    signal_summary,
)


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


# =========================
# Supported Symbols
# =========================

symbols = [
    "^NSEI",          # NIFTY
    "^NSEBANK",       # BANKNIFTY
    "^CNXFINANCE",    # FINNIFTY
    "^NSEMDCP50",     # MIDCAP NIFTY
    "^BSESN",         # SENSEX

    "RELIANCE.NS",
    "TCS.NS",
    "INFY.NS",
    "HDFCBANK.NS",
    "ICICIBANK.NS",
    "SBIN.NS",
    "LT.NS",
    "AXISBANK.NS",
]


# =========================
# Symbol
# =========================

default_symbol = settings.get(
    "symbol",
    "^NSEI"
)

if default_symbol not in symbols:
    default_symbol = "^NSEI"


symbol = st.sidebar.selectbox(
    "Select Symbol",
    symbols,
    index=symbols.index(
        default_symbol
    )
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
    index=strategies.index(
        default_strategy
    )
)


# =========================
# AI Strategy
# =========================

selected_strategy = strategy_name


if strategy_name == "AI Combo":

    try:

        ai_result = auto_strategy()

        if ai_result:

            selected_strategy = ai_result

            st.sidebar.success(
                f"🤖 AI Strategy : {selected_strategy}"
            )

        else:

            st.sidebar.caption(
                "AI Strategy : Default"
            )

    except Exception:

        st.sidebar.caption(
            "AI Strategy : Default"
        )


# =========================================================
# OPTION CONFIGURATION
# =========================================================

OPTION_SYMBOL_MAP = {

    "^NSEI": "NIFTY",

    "^NSEBANK": "BANKNIFTY",

    "^CNXFINANCE": "FINNIFTY",

    "^NSEMDCP50": "MIDCPNIFTY",

    "^BSESN": "SENSEX",
}


is_option_index = (
    symbol in OPTION_SYMBOL_MAP
)


# =========================================================
# Market Type
# =========================================================

if is_option_index:

    market_type = st.sidebar.selectbox(
        "Market",
        [
            "OPTIONS",
            "FUTURES",
            "INDEX"
        ],
        index=0,
        key="index_market_type"
    )

else:

    market_type = st.sidebar.selectbox(
        "Market",
        [
            "STOCK",
            "FUTURES"
        ],
        index=0,
        key="stock_market_type"
    )


# =========================================================
# OPTION PARAMETERS
# =========================================================

option_mode = "N/A"
strike_mode = "ATM"
selected_lots = 1
LOT_SIZE = 1
quantity = 1
option_contract = None


if market_type == "OPTIONS" and is_option_index:

    index_name = OPTION_SYMBOL_MAP[
        symbol
    ]

    LOT_SIZE = get_lot_size(
        index_name
    )
    quantity = (
        int(selected_lots)
        * int(LOT_SIZE)
    )


    # -----------------------------------------------------
    # CE / PE / ALL
    # -----------------------------------------------------

    option_mode = st.sidebar.selectbox(
        "Option Mode",
        [
            "CE",
            "PE",
            "ALL"
        ],
        index=2
    )


    # -----------------------------------------------------
    # Strike
    # -----------------------------------------------------

    strike_mode = st.sidebar.selectbox(
        "Strike",
        get_strike_modes(),
        index=1
    )


    # -----------------------------------------------------
    # Lot Size
    # -----------------------------------------------------

    LOT_SIZE = get_lot_size(
        index_name
    )


    st.sidebar.caption(
        f"📦 Lot Size : {LOT_SIZE}"
    )


    # -----------------------------------------------------
    # Number of Lots
    # -----------------------------------------------------

    selected_lots = st.sidebar.number_input(
        "Number of Lots",
        min_value=1,
        max_value=100,
        value=1,
        step=1
    )


    # -----------------------------------------------------
    # Quantity
    # -----------------------------------------------------

    quantity = (
        int(selected_lots)
        * int(LOT_SIZE)
    )


    st.sidebar.info(
        f"🔢 Order Quantity : {quantity}"
    )

# -----------------------------------------------------
# Current Underlying Price
# -----------------------------------------------------

try:
    underlying_price = float(
        st.session_state.get(
            "current_price",
            0.0
        )
    )
except (TypeError, ValueError):
    underlying_price = 0.0


# -----------------------------------------------------
# Contract Preview
# -----------------------------------------------------

if underlying_price > 0:

    if option_mode in ["CE", "PE"]:

        option_contract = resolve_option_contract(
            index_name=index_name,
            underlying_price=underlying_price,
            option_type=option_mode,
            strike_mode=strike_mode
        )

        if option_contract:

            st.sidebar.success(
                "📋 Option Contract Ready"
            )

            st.sidebar.caption(
                f"Index : {index_name}"
            )

            st.sidebar.caption(
                f"Underlying : ₹{underlying_price:,.2f}"
            )

            st.sidebar.caption(
                f"Type : {option_contract['option_type']}"
            )

            st.sidebar.caption(
                f"Strike : {option_contract['strike']}"
            )

            st.sidebar.caption(
                f"Mode : {option_contract['strike_mode']}"
            )

            st.sidebar.caption(
                f"Lot Size : {option_contract['lot_size']}"
            )

            st.sidebar.caption(
                f"Lots : {selected_lots}"
            )

            st.sidebar.caption(
                f"Quantity : {quantity}"
            )

    else:

        st.sidebar.caption(
            "📋 ALL = CE + PE signals"
        )

else:

    st.sidebar.info(
        "⏳ Waiting for market price..."
    )




# =========================================================
# NON-OPTION MARKET
# =========================================================

if market_type != "OPTIONS":
    option_mode = "N/A"
    strike_mode = "N/A"

    selected_lots = 1
    LOT_SIZE = 1
    quantity = 1
    

# =========================
# Option / Futures Settings
# =========================

# Safe defaults so variables always exist
option_mode = "N/A"
selected_lots = 1
LOT_SIZE = 1
quantity = 1
option_side = "N/A"
strike_mode = "ATM"

if market_type == "OPTIONS":

    # =========================
    # Option Selector
    # =========================

    options = [
        "CE",
        "PE",
        "ALL",
    ]

    default_option = settings.get(
        "option",
        "CE"
    )

    if default_option not in options:
        default_option = "CE"

    option_mode = st.sidebar.selectbox(
        "Option Mode",
        options,
        index=options.index(default_option),
        key="dashboard_option_mode"
    )

    # =========================
    # Strike Selector
    # =========================

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
        index=strikes.index(default_strike),
        key="dashboard_strike_mode"
    )

    
# =========================
# Delta Futures Settings
# =========================

else:

    futures_symbols = []

    try:

        delta = DeltaFutures()

        futures_data = delta.get_futures()

        if futures_data:

            for product in futures_data:

                futures_contract_symbol = product.get(
                    "symbol"
                )

                if futures_contract_symbol:

                    futures_symbols.append(
                        str(
                            futures_contract_symbol
                        ).strip().upper()
                    )

        # Remove duplicates
        futures_symbols = sorted(
            list(
                set(futures_symbols)
            )
        )

    except Exception as e:

        st.sidebar.error(
            f"Delta Futures Error: {e}"
        )

        futures_symbols = []


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

    # Futures do not use CE/PE lots
    option_mode = "N/A"
    selected_lots = 1
    LOT_SIZE = 1
    quantity = 1
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
                    "price",
                    0
                ) or 0
            )

            if current_price > 0:

                st.sidebar.success(
                    f"💰 {futures_symbol} "
                    f"Price: {current_price:,.8f}"
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
    value=True,
    key="paper_trading_switch"
)
# -------------------------
# Auto Paper Trading
# -------------------------

auto_paper_trading = st.sidebar.toggle(
    "🟢 Auto Paper Trading",
    value=False,
    key="auto_paper_trading_switch"
)

# -------------------------
# Live Auto Trading
# -------------------------

live_auto_trading = st.sidebar.toggle(
    "🔴 Live Auto Trading",
    value=False,
    key="live_auto_trading_switch"
)


# =========================
# Mode Control
# =========================

if live_auto_trading:

    enable_auto()

    st.sidebar.warning(
        "🔴 LIVE AUTO TRADING : ON"
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

    # Never enable broker live auto mode
    disable_auto()

    st.sidebar.success(
        "🟢 PAPER TRADING : ON"
    )
    if auto_paper_trading:

        st.sidebar.success(
            "🟢 AUTO PAPER TRADING : ON"
        )


    else:
         st.sidebar.info(
            "⚪ AUTO PAPER TRADING : OFF"
        )
# =========================================================
# DASHBOARD
# =========================================================

if page == "🏠 Dashboard":

    # =====================================================
    # DASHBOARD SIGNAL DATA
    # =====================================================

    try:
        if market_type == "FUTURES":
            signal_data = get_signals(futures_symbol)
        else:
            signal_data = get_signals(symbol)

    except Exception as e:
        signal_data = {"error": str(e)}

    if not isinstance(signal_data, dict):
        signal_data = {"error": "Invalid signal response"}


    # =====================================================
    # CURRENT PRICE
    # =====================================================

    current_price = 0.0

    if "error" in signal_data:

        st.warning(
            f"⚠️ Market data unavailable: "
            f"{signal_data.get('error')}"
        )

    else:

        if market_type == "FUTURES":

            try:
                current_price = float(
                    signal_data.get("Close", 0.0) or 0.0
                )
            except (TypeError, ValueError):
                current_price = 0.0

        else:

            try:
                current_price = float(
                    signal_data.get("Close", 0.0) or 0.0
                )
            except (TypeError, ValueError):
                current_price = 0.0


    # SAVE CURRENT PRICE
    st.session_state["current_price"] = current_price

    # =====================================================
    # SIGNAL
    # =====================================================

    raw_signal = signal_data.get(
        "signal",
        signal_data.get(
            "Signal",
            signal_data.get(
                "action",
                signal_data.get(
                    "Action",
                    ""
                )
            )
        )
    )

    signal = str(raw_signal).upper().strip()

    if "BUY" in signal and "SELL" not in signal:
        signal = "BUY"

    elif "SELL" in signal and "BUY" not in signal:
        signal = "SELL"

    else:
        signal = "HOLD"

    # =====================================================
    # TRADE SYMBOL
    # =====================================================

    try:

        trade_symbol = (
            futures_symbol
            if market_type == "FUTURES" and futures_symbol
            else symbol
        )

    except Exception:

        trade_symbol = symbol

    # =====================================================
    # AUTO PAPER EXIT
    # =====================================================

    if (
        paper_trading
        and auto_paper_trading
        and not live_auto_trading
        and current_price > 0
    ):

        try:

            exit_ok, exit_result = trade_manager.check_position(
                current_price=current_price,
                symbol=trade_symbol,
                option_mode=option_mode
            )

            if (
                exit_ok
                and isinstance(exit_result, dict)
                and exit_result.get("status") == "EXIT"
            ):

                st.success(
                    f"🎯 AUTO PAPER EXIT: "
                    f"{exit_result.get('message', exit_result)}"
                )

        except Exception as e:

            st.error(
                f"❌ Auto Exit Error: {e}"
            )

    # =====================================================
    # MARKET CLOSE - 15:30
    # =====================================================

    try:

        market_close_time = datetime.strptime(
            "15:30",
            "%H:%M"
        ).time()

        current_time = datetime.now().time()

        if (
            paper_trading
            and auto_paper_trading
            and not live_auto_trading
            and current_time >= market_close_time
        ):

            position_key = (
                f"{trade_symbol}_{option_mode}"
            )

            price_map = {
                position_key: current_price
            }

            close_result = trader.market_close_auto_exit(
                price_map=price_map
            )

            if (
                isinstance(close_result, dict)
                and close_result.get("count", 0) > 0
            ):

                st.success(
                    f"🔔 MARKET CLOSE 15:30 | "
                    f"{close_result.get('count', 0)} "
                    f"position(s) auto closed."
                )

    except Exception as e:

        st.error(
            f"❌ Market Close Auto Exit Error: {e}"
        )

    # =====================================================
    # AUTO PAPER ENTRY
    # =====================================================

    if (
        paper_trading
        and auto_paper_trading
        and not live_auto_trading
        and current_price > 0
        and signal in ["BUY", "SELL"]
    ):

        try:

            success, result = trade_manager.process(
                symbol=trade_symbol,
                signal=signal,
                current_price=current_price,
                capital=trader.balance,
                option_mode=option_mode,
                lots=selected_lots,
                lot_size=LOT_SIZE
            )

            if success:

                st.success(
                    f"🤖 AUTO PAPER TRADE: {result}"
                )

            else:

                st.info(
                    f"ℹ️ Trade: {result}"
                )

        except Exception as e:

            st.error(
                f"❌ Auto Trade Error: {e}"
            )

    # =====================================================
    # DASHBOARD PAGE
    # =====================================================

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
            scan_all_option_chain=scan_all_option_chain,
            market_type=market_type,
            futures_symbol=(
                futures_symbol
                if market_type == "FUTURES"
                else None
            ),
            futures_price=(
                current_price
                if market_type == "FUTURES"
                else 0.0
            )
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


# =========================================================
# FOOTER
# =========================================================

st.divider()

st.caption(
    "Jha SmartTrader AI Pro • "
    "AI Trading Terminal"
)

st.caption(
    f"Last Refresh: "
    f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
)