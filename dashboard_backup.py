# ============================================================
# Jha SmartTrader AI Pro
# dashboard.py
# ============================================================

from pathlib import Path
from datetime import datetime, time
from zoneinfo import ZoneInfo
import logging

import streamlit as st
from PIL import Image
from streamlit_autorefresh import st_autorefresh


# ============================================================
# PROJECT IMPORTS
# ============================================================

from signals import get_signals

from paper_trading import PaperTrader
from trade_manager import TradeManager
from backtest_engine import BacktestEngine

from ai_learning import auto_strategy

from auto_mode import (
    enable_auto,
    disable_auto,
)

from option_chain import scan_all_option_chain

from fo_symbols import (
    INDICES,
    FO_STOCKS,
)

from settings_manager import load_settings


# ============================================================
# PAGES
# ============================================================

from pages.dashboard_page import dashboard_page
from pages.market_page import market_page
from pages.portfolio_page import portfolio_page
from pages.reports_page import reports_page
from pages.settings_page import settings_page
from pages.trading_page import trading_page


# ============================================================
# DELTA FUTURES
# ============================================================

from delta_futures import DeltaFutures


# ============================================================
# OPTIONS
# ============================================================

from option_contracts import (
    resolve_option_contract,
    get_lot_size,
    get_strike_modes,
)


# ============================================================
# STREAMLIT CONFIG
# ============================================================

st.set_page_config(
    page_title="Jha SmartTrader AI Pro",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)


# ============================================================
# CSS
# ============================================================

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
    unsafe_allow_html=True,
)


# ============================================================
# CACHED OPTION CHAIN
# ============================================================

@st.cache_data(
    ttl=10,
    show_spinner=False,
)
def get_cached_option_chain():

    try:

        return scan_all_option_chain()

    except Exception as e:

        logging.warning(
            f"Option chain error: {e}"
        )

        return None


# ============================================================
# SAFE FLOAT
# ============================================================

def safe_float(
    value,
    default=0.0,
):

    try:

        if value is None:

            return default

        if isinstance(
            value,
            str,
        ):

            value = value.strip()

            if not value:

                return default

            value = value.replace(
                ",",
                "",
            )

        result = float(value)

        if result != result:

            return default

        if result in (
            float("inf"),
            float("-inf"),
        ):

            return default

        return result

    except Exception:

        return default


# ============================================================
# NORMALIZE SIGNAL
# ============================================================

def normalize_signal(value):

    value = str(
        value or ""
    ).upper().strip()

    if (
        "BUY" in value
        and "SELL" not in value
    ):

        return "BUY"

    if (
        "SELL" in value
        and "BUY" not in value
    ):

        return "SELL"

    return "HOLD"


# ============================================================
# POSITION SIDE
# ============================================================

def normalize_position_side(position):

    """
    Normalize BUY/SELL and LONG/SHORT into LONG/SHORT.

    Indian Options:
        BUY -> LONG

    Delta Futures:
        BUY -> LONG
        SELL -> SHORT
    """

    if not isinstance(
        position,
        dict,
    ):

        return "LONG"

    raw_position_side = str(
        position.get(
            "position_side",
            "",
        )
    ).upper().strip()

    if raw_position_side in {
        "LONG",
        "SHORT",
    }:

        return raw_position_side

    raw_side = str(
        position.get(
            "side",
            position.get(
                "action",
                "BUY",
            ),
        )
    ).upper().strip()

    if raw_side in {
        "SELL",
        "SHORT",
    }:

        return "SHORT"

    return "LONG"


# ============================================================
# DELTA MARKET DETECTION
# ============================================================

def is_delta_symbol(symbol):

    try:

        s = str(
            symbol or ""
        ).strip().upper()

        if not s:

            return False

        delta_symbols = {
            "BTCUSD",
            "ETHUSD",
            "SOLUSD",
            "XRPUSD",
            "DOGEUSD",
            "ADAUSD",
            "BNBUSD",
            "AVAXUSD",
            "DOTUSD",
            "LINKUSD",
            "MATICUSD",
            "1000BONKUSD",
            "1000PEPEUSD",
            "BTCUSDT",
            "ETHUSDT",
        }

        if s in delta_symbols:

            return True

        if s.endswith("USD"):

            return True

        if s.endswith("USDT"):

            return True

        return False

    except Exception:

        return False


# ============================================================
# MARKET TIMING
# ============================================================

def get_market_status(symbol):

    # --------------------------------------------------------
    # DELTA EXCHANGE — OPEN 24x7
    # --------------------------------------------------------

    if is_delta_symbol(symbol):

        return {
            "market": "DELTA",
            "status": "DELTA_24X7",
            "market_open": True,
            "entry_allowed": True,
            "manage_positions": True,
            "message": (
                "🟢 Delta Exchange market is OPEN 24/7."
            ),
        }

    # --------------------------------------------------------
    # INDIAN MARKET — IST
    # --------------------------------------------------------

    ist = ZoneInfo(
        "Asia/Kolkata"
    )

    now = datetime.now(
        ist
    ).time()

    pre_market_start = time(
        9,
        0,
    )

    market_open = time(
        9,
        15,
    )

    market_close = time(
        15,
        30,
    )

    # --------------------------------------------------------
    # PRE-MARKET
    # --------------------------------------------------------

    if (
        pre_market_start
        <= now
        < market_open
    ):

        return {
            "market": "INDIA",
            "status": "PRE_MARKET",
            "market_open": False,
            "entry_allowed": False,
            "manage_positions": True,
            "message": (
                "🟡 Indian Market PRE-MARKET • "
                "Opens 09:15 IST."
            ),
        }

    # --------------------------------------------------------
    # MARKET OPEN
    # --------------------------------------------------------

    if (
        market_open
        <= now
        < market_close
    ):

        return {
            "market": "INDIA",
            "status": "ENTRY_OPEN",
            "market_open": True,
            "entry_allowed": True,
            "manage_positions": True,
            "message": (
                "🟢 Indian Market OPEN • "
                "09:15–15:30 IST."
            ),
        }

    # --------------------------------------------------------
    # MARKET CLOSED
    # --------------------------------------------------------

    return {
        "market": "INDIA",
        "status": "MARKET_CLOSED",
        "market_open": False,
        "entry_allowed": False,
        "manage_positions": True,
        "message": (
            "🔴 Indian Market CLOSED • "
            "Session 09:15–15:30 IST."
        ),
    }


# ============================================================
# OPTION SYMBOL MAP
# ============================================================

OPTION_SYMBOL_MAP = {

    "^NSEI": "NIFTY",

    "^NSEBANK": "BANKNIFTY",

    "^CNXFINANCE": "FINNIFTY",

    "^NSEMDCP50": "MIDCPNIFTY",

    "^BSESN": "SENSEX",
}


# ============================================================
# SUPPORTED SYMBOLS
# ============================================================

symbols = [

    "^NSEI",
    "^NSEBANK",
    "^CNXFINANCE",
    "^NSEMDCP50",
    "^BSESN",

    "RELIANCE.NS",
    "TCS.NS",
    "INFY.NS",
    "HDFCBANK.NS",
    "ICICIBANK.NS",
    "SBIN.NS",
    "LT.NS",
    "AXISBANK.NS",
]


# ============================================================
# BASE DIRECTORY
# ============================================================

BASE_DIR = Path(
    __file__
).resolve().parent


# ============================================================
# LOGO
# ============================================================

logo_path = (
    BASE_DIR
    / "logo.png"
)

if logo_path.exists():

    try:

        logo_image = Image.open(
            logo_path
        )

        st.sidebar.image(
            logo_image,
            width=150,
        )

    except Exception as e:

        logging.warning(
            f"Logo error: {e}"
        )


# ============================================================
# SIDEBAR HEADER
# ============================================================

st.sidebar.markdown(
    "## 📈 Jha SmartTrader AI Pro"
)

st.sidebar.caption(
    "AI Powered Trading Terminal"
)

st.sidebar.divider()


# ============================================================
# SESSION STATE
# ============================================================

if "trader" not in st.session_state:

    st.session_state.trader = PaperTrader(
        initial_balance=100000
    )

trader = st.session_state.trader


if "trade_manager" not in st.session_state:

    st.session_state.trade_manager = TradeManager(
        paper_trader=trader
    )

trade_manager = st.session_state.trade_manager


try:

    trade_manager.set_paper_trader(
        trader
    )

except Exception:

    pass


if "backtester" not in st.session_state:

    st.session_state.backtester = BacktestEngine()

backtester = st.session_state.backtester


# ============================================================
# SETTINGS
# ============================================================

try:

    settings = load_settings()

    if not isinstance(
        settings,
        dict,
    ):

        settings = {}

except Exception:

    settings = {}


# ============================================================
# SYSTEM STATUS
# ============================================================

st.sidebar.success(
    "🟢 Market System : ONLINE"
)

st.sidebar.info(
    f"💰 Paper Balance : "
    f"₹{safe_float(trader.balance):,.2f}"
)

st.sidebar.success(
    "🤖 AI Engine : ACTIVE"
)

st.sidebar.info(
    "🏦 Broker : "
    + str(
        settings.get(
            "broker",
            "Kotak Neo",
        )
    )
)

st.sidebar.divider()


# ============================================================
# NAVIGATION
# ============================================================

page = st.sidebar.radio(
    "📂 Navigation",
    [
        "🏠 Dashboard",
        "📈 Market",
        "💰 Trading",
        "📦 Portfolio",
        "📊 Reports",
        "⚙ Settings",
    ],
)


# ============================================================
# PARAMETERS
# ============================================================

st.sidebar.title(
    "⚙ Parameters"
)


# ============================================================
# SYMBOL
# ============================================================

default_symbol = settings.get(
    "symbol",
    "^NSEI",
)

if default_symbol not in symbols:

    default_symbol = "^NSEI"


symbol = st.sidebar.selectbox(
    "Select Symbol",
    symbols,
    index=symbols.index(
        default_symbol
    ),
)


# ============================================================
# IMPORTANT SESSION STATE
# Selected underlying symbol is always stored separately.
# ============================================================

st.session_state[
    "selected_underlying_symbol"
] = symbol


# ============================================================
# STRATEGY
# ============================================================

strategies = [

    "EMA Crossover",
    "RSI",
    "SuperTrend",
    "MACD + Volume",
    "AI Combo",
]


default_strategy = settings.get(
    "strategy",
    "AI Combo",
)

if default_strategy not in strategies:

    default_strategy = "AI Combo"


strategy_name = st.sidebar.selectbox(
    "Strategy",
    strategies,
    index=strategies.index(
        default_strategy
    ),
)


# ============================================================
# AI STRATEGY
# ============================================================

selected_strategy = strategy_name

if strategy_name == "AI Combo":

    try:

        ai_result = auto_strategy()

        if ai_result:

            selected_strategy = str(
                ai_result
            )

            st.sidebar.success(
                "🤖 AI Strategy : "
                + selected_strategy
            )

        else:

            st.sidebar.caption(
                "AI Strategy : Default"
            )

    except Exception:

        st.sidebar.caption(
            "AI Strategy : Default"
        )


# ============================================================
# DEFAULT VARIABLES
# ============================================================

is_option_index = (
    symbol in OPTION_SYMBOL_MAP
)

market_type = "INDEX"

option_mode = "N/A"

strike_mode = "ATM"

selected_lots = 1

LOT_SIZE = 1

quantity = 1

option_contract = None

option_contract_by_option = {}

price_by_option = {}

underlying_price = 0.0

current_price = 0.0

futures_symbol = None


# ============================================================
# MARKET TYPE
# ============================================================

if is_option_index:

    market_type = st.sidebar.selectbox(

        "Market",

        [
            "OPTIONS",
            "FUTURES",
            "INDEX",
        ],

        index=0,

        key="index_market_type",
    )

else:

    market_type = st.sidebar.selectbox(

        "Market",

        [
            "STOCK",
            "FUTURES",
        ],

        index=0,

        key="stock_market_type",
    )


# ============================================================
# OPTION CONFIGURATION
# ============================================================

if (
    market_type == "OPTIONS"
    and is_option_index
):

    index_name = (
        OPTION_SYMBOL_MAP[
            symbol
        ]
    )

    try:

        LOT_SIZE = int(
            get_lot_size(
                index_name
            )
        )

    except Exception:

        LOT_SIZE = 1


    options = [
        "CE",
        "PE",
        "ALL",
    ]


    default_option = settings.get(
        "option",
        "ALL",
    )

    if default_option not in options:

        default_option = "ALL"


    option_mode = st.sidebar.selectbox(

        "Option Mode",

        options,

        index=options.index(
            default_option
        ),

        key="dashboard_option_mode",
    )


    try:

        strike_modes = get_strike_modes()

        if not strike_modes:

            strike_modes = [
                "ITM",
                "ATM",
                "OTM",
            ]

    except Exception:

        strike_modes = [
            "ITM",
            "ATM",
            "OTM",
        ]


    default_strike = settings.get(
        "strike",
        "ATM",
    )

    if default_strike not in strike_modes:

        default_strike = "ATM"


    strike_mode = st.sidebar.selectbox(

        "Strike",

        strike_modes,

        index=strike_modes.index(
            default_strike
        ),

        key="dashboard_strike_mode",
    )


    selected_lots = st.sidebar.number_input(

        "Number of Lots",

        min_value=1,

        max_value=100,

        value=1,

        step=1,

        key="dashboard_lots",
    )


    quantity = (
        int(selected_lots)
        * int(LOT_SIZE)
    )


    st.sidebar.caption(
        f"📦 Lot Size : {LOT_SIZE}"
    )

    st.sidebar.info(
        f"🔢 Order Quantity : {quantity}"
    )


# ============================================================
# FUTURES CONFIGURATION
# ============================================================

if market_type == "FUTURES":

    futures_symbols = []

    try:

        delta = DeltaFutures()

        futures_data = delta.get_futures()

        if futures_data:

            for product in futures_data:

                if not isinstance(
                    product,
                    dict,
                ):

                    continue

                product_symbol = product.get(
                    "symbol"
                )

                if product_symbol:

                    futures_symbols.append(
                        str(
                            product_symbol
                        )
                        .strip()
                        .upper()
                    )


        futures_symbols = sorted(
            list(
                set(
                    futures_symbols
                )
            )
        )

    except Exception as e:

        st.sidebar.warning(
            f"Delta Futures Error: {e}"
        )

        futures_symbols = []


    if not futures_symbols:

        futures_symbols = [
            "BTCUSD",
            "ETHUSD",
            "1000BONKUSD",
        ]


    default_futures = settings.get(
        "futures_symbol",
        futures_symbols[0],
    )

    if default_futures not in futures_symbols:

        default_futures = futures_symbols[0]


    futures_symbol = st.sidebar.selectbox(

        "Delta Futures",

        futures_symbols,

        index=futures_symbols.index(
            default_futures
        ),

        key="dashboard_futures_symbol",
    )


    # --------------------------------------------------------
    # Store actual futures symbol separately.
    # --------------------------------------------------------

    st.session_state[
        "futures_symbol"
    ] = futures_symbol


    option_mode = "N/A"

    strike_mode = "N/A"

    selected_lots = 1

    LOT_SIZE = 1

    quantity = 1


# ============================================================
# FUTURES LIVE PRICE
# ============================================================

if market_type == "FUTURES":

    try:

        delta = DeltaFutures()

        ticker = delta.get_ticker(
            futures_symbol
        )

        if isinstance(
            ticker,
            dict,
        ):

            current_price = safe_float(
                ticker.get(
                    "price",
                    ticker.get(
                        "close",
                        0,
                    ),
                )
            )


        if current_price > 0:

            st.sidebar.success(
                f"💰 {futures_symbol} "
                f"${current_price:,.8f}"
            )

        else:

            st.sidebar.warning(
                "⚠️ Futures price unavailable"
            )

    except Exception as e:

        current_price = 0.0

        st.sidebar.warning(
            f"Futures price error: {e}"
        )


# ============================================================
# MARKET STATUS
# ============================================================

market_status_symbol = (
    futures_symbol
    if market_type == "FUTURES"
    else symbol
)

market_status = get_market_status(
    market_status_symbol
)


if market_status["market"] == "DELTA":

    st.sidebar.success(
        "🟢 DELTA MARKET : 24/7"
    )

    st.sidebar.caption(
        "No daily market close"
    )

else:

    if market_status["status"] == "ENTRY_OPEN":

        st.sidebar.success(
            "🟢 INDIAN MARKET : OPEN"
        )

    elif market_status["status"] == "PRE_MARKET":

        st.sidebar.warning(
            "🟡 INDIAN MARKET : PRE-MARKET"
        )

    else:

        st.sidebar.error(
            "🔴 INDIAN MARKET : CLOSED"
        )


# ============================================================
# TRADING MODE
# ============================================================

st.sidebar.divider()

st.sidebar.subheader(
    "🤖 Trading Mode"
)


paper_trading = st.sidebar.toggle(
    "🟢 Paper Trading",
    value=True,
    key="paper_trading_switch",
)


auto_paper_trading = st.sidebar.toggle(
    "🟢 Auto Paper Trading",
    value=False,
    key="auto_paper_trading_switch",
)


live_auto_trading = st.sidebar.toggle(
    "🔴 Live Auto Trading",
    value=False,
    key="live_auto_trading_switch",
)


# ============================================================
# MODE CONTROL
# ============================================================

if live_auto_trading:

    try:

        enable_auto()

    except Exception:

        pass

    st.sidebar.warning(
        "🔴 LIVE AUTO TRADING : ON"
    )

    live_confirm = st.sidebar.checkbox(
        "I confirm real orders can be placed",
        key="live_trade_confirmation",
    )

    if not live_confirm:

        try:

            disable_auto()

        except Exception:

            pass

        st.sidebar.error(
            "🔒 Live trading locked"
        )


elif paper_trading:

    try:

        disable_auto()

    except Exception:

        pass

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


# ============================================================
# DASHBOARD
# ============================================================

if page == "🏠 Dashboard":

    # ========================================================
    # DASHBOARD SYMBOL
    # ========================================================
    #
    # IMPORTANT:
    #
    # Indian OPTIONS:
    #     dashboard_symbol = underlying index
    #
    # Example:
    #     ^NSEBANK
    #
    # Actual option contract:
    #     BANKNIFTYEXPIRY56500PE
    #
    # The option contract is ONLY used for trading.
    # It must NOT replace the dashboard underlying symbol.
    #
    # Delta FUTURES:
    #     dashboard_symbol = selected futures symbol
    #
    # ========================================================

    if market_type == "FUTURES" and futures_symbol:

        dashboard_symbol = futures_symbol

    else:

        dashboard_symbol = symbol


    # --------------------------------------------------------
    # Store selected dashboard symbol.
    # --------------------------------------------------------

    st.session_state[
        "dashboard_symbol"
    ] = dashboard_symbol


    # ========================================================
    # GET SIGNAL
    # ========================================================

    try:

        signal_data = get_signals(
            dashboard_symbol
        )

    except Exception as e:

        signal_data = {
            "error": str(e)
        }


    if not isinstance(
        signal_data,
        dict,
    ):

        signal_data = {
            "error": "Invalid signal response"
        }


    # ========================================================
    # PRICE
    # ========================================================

    if signal_data.get("error"):

        st.warning(
            "⚠️ Market data unavailable: "
            + str(
                signal_data.get(
                    "error"
                )
            )
        )

    else:

        if market_type == "FUTURES":

            if current_price <= 0:

                current_price = safe_float(
                    signal_data.get(
                        "Close",
                        signal_data.get(
                            "Price",
                            0,
                        ),
                    )
                )

        else:

            current_price = safe_float(
                signal_data.get(
                    "Close",
                    0,
                )
            )

        underlying_price = current_price


    st.session_state[
        "current_price"
    ] = underlying_price


    # ========================================================
    # OPTION CONTRACT
    # ========================================================

    option_contract = None

    option_contract_by_option = {}


    if (
        market_type == "OPTIONS"
        and is_option_index
        and underlying_price > 0
    ):

        index_name = OPTION_SYMBOL_MAP[
            symbol
        ]


        # ----------------------------------------------------
        # CE
        # ----------------------------------------------------

        if option_mode in [
            "CE",
            "ALL",
        ]:

            try:

                ce_contract = resolve_option_contract(

                    index_name=index_name,

                    underlying_price=(
                        underlying_price
                    ),

                    option_type="CE",

                    strike_mode=strike_mode,

                )

            except Exception as e:

                logging.warning(
                    f"CE contract error: {e}"
                )

                ce_contract = None


            if ce_contract:

                option_contract_by_option[
                    "CE"
                ] = ce_contract


        # ----------------------------------------------------
        # PE
        # ----------------------------------------------------

        if option_mode in [
            "PE",
            "ALL",
        ]:

            try:

                pe_contract = resolve_option_contract(

                    index_name=index_name,

                    underlying_price=(
                        underlying_price
                    ),

                    option_type="PE",

                    strike_mode=strike_mode,

                )

            except Exception as e:

                logging.warning(
                    f"PE contract error: {e}"
                )

                pe_contract = None


            if pe_contract:

                option_contract_by_option[
                    "PE"
                ] = pe_contract


        if option_mode in [
            "CE",
            "PE",
        ]:

            option_contract = (
                option_contract_by_option.get(
                    option_mode
                )
            )


        # ----------------------------------------------------
        # OPTION CONTRACT DISPLAY
        # ----------------------------------------------------

        st.sidebar.divider()

        st.sidebar.subheader(
            "📦 Option Contract"
        )


        if option_mode == "ALL":

            ce = option_contract_by_option.get(
                "CE"
            )

            pe = option_contract_by_option.get(
                "PE"
            )


            if ce:

                st.sidebar.success(
                    "🟢 CE Ready"
                )

                st.sidebar.caption(
                    f"Strike: {ce.get('strike')}"
                )

                st.sidebar.caption(
                    f"Symbol: {ce.get('symbol', 'N/A')}"
                )

            else:

                st.sidebar.error(
                    "❌ CE Contract unavailable"
                )


            if pe:

                st.sidebar.success(
                    "🔴 PE Ready"
                )

                st.sidebar.caption(
                    f"Strike: {pe.get('strike')}"
                )

                st.sidebar.caption(
                    f"Symbol: {pe.get('symbol', 'N/A')}"
                )

            else:

                st.sidebar.error(
                    "❌ PE Contract unavailable"
                )


        elif option_contract:

            st.sidebar.success(
                "📋 Option Contract Ready"
            )

            st.sidebar.caption(
                f"Type: {option_contract.get('option_type')}"
            )

            st.sidebar.caption(
                f"Strike: {option_contract.get('strike')}"
            )

            st.sidebar.caption(
                f"Mode: {option_contract.get('strike_mode')}"
            )

            st.sidebar.caption(
                f"Symbol: {option_contract.get('symbol', 'N/A')}"
            )


    # ========================================================
    # OPTION PRICES
    # ========================================================

    price_by_option = {}


    if market_type == "OPTIONS":

        option_scan = get_cached_option_chain()


        if isinstance(
            option_scan,
            dict,
        ):

            selected_index = (
                OPTION_SYMBOL_MAP.get(
                    symbol
                )
            )


            selected_data = (
                option_scan.get(
                    selected_index
                )
            )


            if isinstance(
                selected_data,
                dict,
            ):

                # --------------------------------------------
                # CE
                # --------------------------------------------

                for key in [
                    "CE",
                    "ce",
                    "CE_LTP",
                    "ce_ltp",
                    "call_ltp",
                    "call_price",
                ]:

                    value = safe_float(
                        selected_data.get(
                            key,
                            0,
                        )
                    )

                    if value > 0:

                        price_by_option[
                            "CE"
                        ] = value

                        break


                # --------------------------------------------
                # PE
                # --------------------------------------------

                for key in [
                    "PE",
                    "pe",
                    "PE_LTP",
                    "pe_ltp",
                    "put_ltp",
                    "put_price",
                ]:

                    value = safe_float(
                        selected_data.get(
                            key,
                            0,
                        )
                    )

                    if value > 0:

                        price_by_option[
                            "PE"
                        ] = value

                        break


    # ========================================================
    # OPTION PRICE DISPLAY
    # ========================================================

    ce_ltp = safe_float(
        price_by_option.get(
            "CE",
            0,
        )
    )

    pe_ltp = safe_float(
        price_by_option.get(
            "PE",
            0,
        )
    )


    if market_type == "OPTIONS":

        st.sidebar.divider()

        st.sidebar.subheader(
            "💰 Option LTP"
        )


        if ce_ltp > 0:

            st.sidebar.success(
                f"🟢 CE LTP : ₹{ce_ltp:,.2f}"
            )

        else:

            st.sidebar.warning(
                "⚠️ CE LTP unavailable"
            )


        if pe_ltp > 0:

            st.sidebar.success(
                f"🔴 PE LTP : ₹{pe_ltp:,.2f}"
            )

        else:

            st.sidebar.warning(
                "⚠️ PE LTP unavailable"
            )


        st.session_state[
            "option_prices"
        ] = price_by_option

        st.session_state[
            "option_contracts"
        ] = option_contract_by_option


    # ========================================================
    # SIGNAL
    # ========================================================

    raw_signal = signal_data.get(

        "SIGNAL",

        signal_data.get(

            "Signal",

            signal_data.get(
                "signal",
                "HOLD",
            ),
        ),
    )


    signal = normalize_signal(
        raw_signal
    )


    # ========================================================
    # SIGNAL STRENGTH
    # ========================================================

    signal_strength = safe_float(

        signal_data.get(

            "Signal_Strength",

            signal_data.get(

                "Strength",

                signal_data.get(
                    "Confidence",
                    0,
                ),
            ),
        )
    )


    # ========================================================
    # TRADE SYMBOL
    # ========================================================
    #
    # IMPORTANT:
    #
    # This is the execution symbol.
    #
    # FUTURES:
    #     BTCUSD / ETHUSD / etc.
    #
    # OPTIONS:
    #     underlying symbol is retained here for compatibility
    #     with the existing TradeManager logic.
    #
    # The actual CE/PE contract is kept separately inside:
    #
    #     option_contract_by_option
    #
    # ========================================================

    if (
        market_type == "FUTURES"
        and futures_symbol
    ):

        trade_symbol = futures_symbol

    else:

        trade_symbol = symbol


    # Store execution symbol separately.

    st.session_state[
        "trade_symbol"
    ] = trade_symbol


    # ========================================================
    # MARKET STATUS
    # ========================================================

    trade_market_status = get_market_status(
        trade_symbol
    )


    # ========================================================
    # AUTO PAPER EXIT
    # ========================================================

    if (
        paper_trading
        and auto_paper_trading
        and not live_auto_trading
    ):

        try:

            # ------------------------------------------------
            # OPTIONS ALL
            # ------------------------------------------------

            if (
                market_type == "OPTIONS"
                and option_mode == "ALL"
            ):

                if ce_ltp > 0:

                    trade_manager.check_position(
                        current_price=ce_ltp,
                        symbol=trade_symbol,
                        option_mode="CE",
                    )


                if pe_ltp > 0:

                    trade_manager.check_position(
                        current_price=pe_ltp,
                        symbol=trade_symbol,
                        option_mode="PE",
                    )


            # ------------------------------------------------
            # OPTIONS CE / PE
            # ------------------------------------------------

            elif (
                market_type == "OPTIONS"
                and option_mode in [
                    "CE",
                    "PE",
                ]
            ):

                option_price = safe_float(
                    price_by_option.get(
                        option_mode,
                        0,
                    )
                )


                if option_price > 0:

                    trade_manager.check_position(
                        current_price=option_price,
                        symbol=trade_symbol,
                        option_mode=option_mode,
                    )


            # ------------------------------------------------
            # INDEX / STOCK / FUTURES
            # ------------------------------------------------

            else:

                if current_price > 0:

                    trade_manager.check_position(
                        current_price=current_price,
                        symbol=trade_symbol,
                        option_mode="N/A",
                    )


        except Exception as e:

            logging.exception(
                f"Auto exit error: {e}"
            )


    # ========================================================
    # INDIAN MARKET CLOSE
    # ========================================================

    try:

        if (
            paper_trading
            and auto_paper_trading
            and not live_auto_trading
            and trade_market_status["market"] == "INDIA"
            and trade_market_status["status"] == "MARKET_CLOSED"
        ):

            active_positions = (
                trader.get_active_positions()
            )

            close_price_map = {}


            if isinstance(
                active_positions,
                dict,
            ):

                for (
                    position_key,
                    position,
                ) in active_positions.items():

                    if not isinstance(
                        position,
                        dict,
                    ):

                        continue


                    pos_symbol = str(
                        position.get(
                            "symbol",
                            "",
                        )
                    )


                    pos_option = str(
                        position.get(
                            "option_mode",
                            "N/A",
                        )
                    ).strip().upper()


                    if pos_option == "CE":

                        if ce_ltp > 0:

                            close_price_map[
                                position_key
                            ] = ce_ltp


                    elif pos_option == "PE":

                        if pe_ltp > 0:

                            close_price_map[
                                position_key
                            ] = pe_ltp


                    else:

                        if (
                            current_price > 0
                            and not is_delta_symbol(
                                pos_symbol
                            )
                        ):

                            close_price_map[
                                position_key
                            ] = current_price


            if close_price_map:

                trader.market_close_auto_exit(
                    price_map=close_price_map
                )


    except Exception as e:

        logging.exception(
            f"Market close error: {e}"
        )


    # ========================================================
    # AUTO PAPER ENTRY
    # ========================================================

    if (
        paper_trading
        and auto_paper_trading
        and not live_auto_trading
        and signal in [
            "BUY",
            "SELL",
        ]
    ):

        try:

            # =================================================
            # IMPORTANT:
            # No new Indian-market entry when market is closed
            # =================================================

            if (
                trade_market_status["market"] == "INDIA"
                and not trade_market_status["entry_allowed"]
                and signal == "BUY"
            ):

                st.info(
                    "⏸️ AUTO PAPER ENTRY BLOCKED: "
                    "Indian market is closed/pre-market."
                )

            # =================================================
            # OPTIONS ALL
            # =================================================

            elif (
                market_type == "OPTIONS"
                and option_mode == "ALL"
            ):

                ce_price = safe_float(
                    price_by_option.get(
                        "CE",
                        0,
                    )
                )

                pe_price = safe_float(
                    price_by_option.get(
                        "PE",
                        0,
                    )
                )


                # ------------------------------------------------
                # ALL → BUY CE + BUY PE SEPARATELY
                # ------------------------------------------------

                if signal == "BUY":

                    # --------------------------------------------
                    # CE BUY
                    # --------------------------------------------

                    if ce_price > 0:

                        try:

                            ce_position = trader.get_position(
                                trade_symbol,
                                "CE",
                            )

                        except Exception:

                            ce_position = None


                        if ce_position:

                            st.info(
                                "ℹ️ AUTO PAPER ALL: "
                                "CE position already active."
                            )

                        else:

                            ce_success, ce_result = (
                                trade_manager.process(

                                    symbol=trade_symbol,

                                    signal="BUY",

                                    current_price=ce_price,

                                    capital=trader.balance,

                                    option_mode="CE",

                                    lots=int(
                                        selected_lots
                                    ),

                                    lot_size=int(
                                        LOT_SIZE
                                    ),

                                    price_by_option={
                                        "CE": ce_price
                                    },
                                )
                            )


                            if ce_success:

                                st.success(
                                    "🟢 AUTO PAPER ALL → "
                                    "CE BUY: "
                                    + str(
                                        ce_result
                                    )
                                )

                            else:

                                st.info(
                                    "ℹ️ AUTO PAPER ALL → "
                                    "CE: "
                                    + str(
                                        ce_result
                                    )
                                )

                    else:

                        st.warning(
                            "⛔ AUTO PAPER ALL: "
                            "CE LTP unavailable."
                        )


                    # --------------------------------------------
                    # PE BUY
                    # --------------------------------------------

                    if pe_price > 0:

                        try:

                            pe_position = trader.get_position(
                                trade_symbol,
                                "PE",
                            )

                        except Exception:

                            pe_position = None


                        if pe_position:

                            st.info(
                                "ℹ️ AUTO PAPER ALL: "
                                "PE position already active."
                            )

                        else:

                            pe_success, pe_result = (
                                trade_manager.process(

                                    symbol=trade_symbol,

                                    signal="BUY",

                                    current_price=pe_price,

                                    capital=trader.balance,

                                    option_mode="PE",

                                    lots=int(
                                        selected_lots
                                    ),

                                    lot_size=int(
                                        LOT_SIZE
                                    ),

                                    price_by_option={
                                        "PE": pe_price
                                    },
                                )
                            )


                            if pe_success:

                                st.success(
                                    "🔴 AUTO PAPER ALL → "
                                    "PE BUY: "
                                    + str(
                                        pe_result
                                    )
                                )

                            else:

                                st.info(
                                    "ℹ️ AUTO PAPER ALL → "
                                    "PE: "
                                    + str(
                                        pe_result
                                    )
                                )

                    else:

                        st.warning(
                            "⛔ AUTO PAPER ALL: "
                            "PE LTP unavailable."
                        )


                # ------------------------------------------------
                # ALL → EXIT EXISTING BUY POSITIONS
                # ------------------------------------------------

                elif signal == "SELL":

                    # --------------------------------------------
                    # CE EXIT
                    # --------------------------------------------

                    if ce_price > 0:

                        try:

                            ce_position = trader.get_position(
                                trade_symbol,
                                "CE",
                            )

                        except Exception:

                            ce_position = None


                        if ce_position:

                            ce_success, ce_result = (
                                trade_manager.process(

                                    symbol=trade_symbol,

                                    signal="SELL",

                                    current_price=ce_price,

                                    capital=trader.balance,

                                    option_mode="CE",

                                    lots=int(
                                        selected_lots
                                    ),

                                    lot_size=int(
                                        LOT_SIZE
                                    ),

                                    price_by_option={
                                        "CE": ce_price
                                    },
                                )
                            )


                            if ce_success:

                                st.success(
                                    "🔴 AUTO PAPER ALL → "
                                    "CE EXIT: "
                                    + str(
                                        ce_result
                                    )
                                )

                            else:

                                st.info(
                                    "ℹ️ AUTO PAPER ALL → "
                                    "CE EXIT: "
                                    + str(
                                        ce_result
                                    )
                                )

                        else:

                            st.info(
                                "ℹ️ AUTO PAPER ALL: "
                                "No active CE BUY position."
                            )


                    # --------------------------------------------
                    # PE EXIT
                    # --------------------------------------------

                    if pe_price > 0:

                        try:

                            pe_position = trader.get_position(
                                trade_symbol,
                                "PE",
                            )

                        except Exception:

                            pe_position = None


                        if pe_position:

                            pe_success, pe_result = (
                                trade_manager.process(

                                    symbol=trade_symbol,

                                    signal="SELL",

                                    current_price=pe_price,

                                    capital=trader.balance,

                                    option_mode="PE",

                                    lots=int(
                                        selected_lots
                                    ),

                                    lot_size=int(
                                        LOT_SIZE
                                    ),

                                    price_by_option={
                                        "PE": pe_price
                                    },
                                )
                            )


                            if pe_success:

                                st.success(
                                    "🔴 AUTO PAPER ALL → "
                                    "PE EXIT: "
                                    + str(
                                        pe_result
                                    )
                                )

                            else:

                                st.info(
                                    "ℹ️ AUTO PAPER ALL → "
                                    "PE EXIT: "
                                    + str(
                                        pe_result
                                    )
                                )

                        else:

                            st.info(
                                "ℹ️ AUTO PAPER ALL: "
                                "No active PE BUY position."
                            )


                    if (
                        ce_price <= 0
                        and pe_price <= 0
                    ):

                        st.warning(
                            "⛔ AUTO PAPER ALL EXIT blocked: "
                            "CE/PE LTP unavailable."
                        )


            # =================================================
            # OPTIONS CE / PE
            # =================================================

            elif (
                market_type == "OPTIONS"
                and option_mode in [
                    "CE",
                    "PE",
                ]
            ):

                option_price = safe_float(
                    price_by_option.get(
                        option_mode,
                        0,
                    )
                )


                if option_price <= 0:

                    st.warning(
                        f"⛔ AUTO PAPER {option_mode} blocked: "
                        "actual option LTP unavailable."
                    )

                # ------------------------------------------------
                # BUY
                # ------------------------------------------------

                elif signal == "BUY":

                    try:

                        existing_position = trader.get_position(
                            trade_symbol,
                            option_mode,
                        )

                    except Exception:

                        existing_position = None


                    if existing_position:

                        st.info(
                            f"ℹ️ AUTO PAPER {option_mode}: "
                            "Position already active."
                        )

                    else:

                        success, result = (
                            trade_manager.process(

                                symbol=trade_symbol,

                                signal="BUY",

                                current_price=option_price,

                                capital=trader.balance,

                                option_mode=option_mode,

                                lots=int(
                                    selected_lots
                                ),

                                lot_size=int(
                                    LOT_SIZE
                                ),

                                price_by_option={
                                    option_mode: option_price
                                },
                            )
                        )


                        if success:

                            st.success(
                                "🤖 AUTO PAPER "
                                f"{option_mode} BUY: "
                                + str(result)
                            )

                        else:

                            st.info(
                                "ℹ️ AUTO PAPER "
                                f"{option_mode}: "
                                + str(result)
                            )


                # ------------------------------------------------
                # SELL = EXIT ONLY
                # ------------------------------------------------

                elif signal == "SELL":

                    try:

                        existing_position = trader.get_position(
                            trade_symbol,
                            option_mode,
                        )

                    except Exception:

                        existing_position = None


                    if not existing_position:

                        st.info(
                            f"ℹ️ AUTO PAPER {option_mode}: "
                            "No active BUY position to exit."
                        )

                    else:

                        success, result = (
                            trade_manager.process(

                                symbol=trade_symbol,

                                signal="SELL",

                                current_price=option_price,

                                capital=trader.balance,

                                option_mode=option_mode,

                                lots=int(
                                    selected_lots
                                ),

                                lot_size=int(
                                    LOT_SIZE
                                ),

                                price_by_option={
                                    option_mode: option_price
                                },
                            )
                        )


                        if success:

                            st.success(
                                "🔴 AUTO PAPER "
                                f"{option_mode} EXIT: "
                                + str(result)
                            )

                        else:

                            st.info(
                                "ℹ️ AUTO PAPER "
                                f"{option_mode} EXIT: "
                                + str(result)
                            )


            # =================================================
            # INDEX / STOCK / DELTA FUTURES
            # =================================================

            else:

                if current_price <= 0:

                    st.warning(
                        "⚠️ Current market price unavailable."
                    )

                else:

                    success, result = (
                        trade_manager.process(

                            symbol=trade_symbol,

                            signal=signal,

                            current_price=current_price,

                            capital=trader.balance,

                            option_mode="N/A",

                            lots=1,

                            lot_size=1,
                        )
                    )


                    if success:

                        st.success(
                            "🤖 AUTO PAPER TRADE: "
                            + str(result)
                        )

                    else:

                        st.info(
                            "ℹ️ Trade: "
                            + str(result)
                        )


        except Exception as e:

            logging.exception(
                f"Auto trade error: {e}"
            )

            st.error(
                f"❌ Auto Trade Error: {e}"
            )


    # ========================================================
    # OFFLINE PAPER OPTION TEST
    # ========================================================

    if (
        market_type == "OPTIONS"
        and is_option_index
    ):

        st.markdown(
            "### 🧪 Offline Paper Option Test"
        )

        st.caption(
            "Market closed होने पर भी CE/PE Paper BUY → "
            "LTP → SL/Target → EXIT flow test करें. "
            "यह LIVE order नहीं भेजता."
        )


        with st.expander(
            "🧪 Open Paper Option Test",
            expanded=False,
        ):

            test_index = OPTION_SYMBOL_MAP.get(
                symbol,
                "NIFTY",
            )


            tc1, tc2, tc3 = st.columns(3)


            with tc1:

                test_option = st.selectbox(
                    "Test Option",
                    [
                        "CE",
                        "PE",
                    ],
                    key="offline_test_option",
                )


            with tc2:

                test_strike = st.number_input(
                    "Test Strike",
                    min_value=1.0,
                    value=23500.0,
                    step=50.0,
                    key="offline_test_strike",
                )


            with tc3:

                test_expiry = st.text_input(
                    "Test Expiry",
                    value="PAPER",
                    key="offline_test_expiry",
                )


            pc1, pc2, pc3 = st.columns(3)


            with pc1:

                test_entry = st.number_input(
                    "Entry / BUY Price ₹",
                    min_value=0.05,
                    value=150.0,
                    step=1.0,
                    key="offline_test_entry",
                )


            with pc2:

                test_ltp = st.number_input(
                    "Test Current LTP ₹",
                    min_value=0.05,
                    value=160.0,
                    step=1.0,
                    key="offline_test_ltp",
                )


            with pc3:

                test_qty = st.number_input(
                    "Quantity",
                    min_value=1,
                    value=int(LOT_SIZE),
                    step=max(
                        1,
                        int(LOT_SIZE),
                    ),
                    key="offline_test_qty",
                )


            rc1, rc2, rc3 = st.columns(3)


            with rc1:

                test_sl_pct = st.number_input(
                    "Stop Loss %",
                    min_value=0.1,
                    max_value=50.0,
                    value=1.0,
                    step=0.1,
                    key="offline_test_sl_pct",
                )


            with rc2:

                test_target_pct = st.number_input(
                    "Target %",
                    min_value=0.1,
                    max_value=100.0,
                    value=2.0,
                    step=0.1,
                    key="offline_test_target_pct",
                )


            with rc3:

                test_trailing = st.checkbox(
                    "Trailing Enabled",
                    value=True,
                    key="offline_test_trailing",
                )


            test_symbol = (
                f"PAPERTEST_{test_index}"
            )

            test_key = (
                f"{test_symbol}_{test_option}"
            )


            st.info(
                f"Test Contract: {test_index} "
                f"{test_strike:g}{test_option} | "
                f"Expiry: {test_expiry} | "
                f"Qty: {int(test_qty)}"
            )


            active_test_position = trader.get_position(
                test_symbol,
                test_option,
            )


            if active_test_position:

                test_entry_live = safe_float(
                    active_test_position.get(
                        "entry",
                        0,
                    )
                )

                test_sl_live = safe_float(
                    active_test_position.get(
                        "stoploss",
                        0,
                    )
                )

                test_target_live = safe_float(
                    active_test_position.get(
                        "target",
                        0,
                    )
                )

                test_pnl = (
                    (
                        test_ltp
                        - test_entry_live
                    )
                    * int(
                        active_test_position.get(
                            "qty",
                            0,
                        )
                    )
                )


                st.success(
                    f"🟢 ACTIVE {test_option} | "
                    f"Entry ₹{test_entry_live:,.2f} | "
                    f"LTP ₹{test_ltp:,.2f} | "
                    f"SL ₹{test_sl_live:,.2f} | "
                    f"Target ₹{test_target_live:,.2f} | "
                    f"P&L ₹{test_pnl:,.2f}"
                )


            b1, b2, b3 = st.columns(3)


            with b1:

                if st.button(
                    f"🟢 PAPER BUY {test_option}",
                    key="offline_test_buy",
                    use_container_width=True,
                ):

                    if active_test_position:

                        st.warning(
                            f"⚠️ {test_option} test "
                            "position already active."
                        )

                    else:

                        entry = safe_float(
                            test_entry
                        )

                        sl = entry * (
                            1.0
                            - safe_float(
                                test_sl_pct
                            ) / 100.0
                        )

                        target = entry * (
                            1.0
                            + safe_float(
                                test_target_pct
                            ) / 100.0
                        )


                        try:

                            ok, result = trader.buy(

                                symbol=test_symbol,

                                price=entry,

                                qty=int(test_qty),

                                target=target,

                                stoploss=sl,

                                trailing_enabled=bool(
                                    test_trailing
                                ),

                                trailing_start=(
                                    entry * 0.005
                                ),

                                trailing_distance=(
                                    entry * 0.0025
                                ),

                                option_mode=test_option,

                                option_contract={
                                    "index": test_index,
                                    "option_type": test_option,
                                    "strike": test_strike,
                                    "expiry": test_expiry,
                                    "test": True,
                                },
                            )


                            if ok:

                                st.success(
                                    f"🟢 PAPER {test_option} OPENED | "
                                    f"Entry ₹{entry:,.2f} | "
                                    f"SL ₹{sl:,.2f} | "
                                    f"Target ₹{target:,.2f} | "
                                    f"Qty {int(test_qty)}"
                                )

                            else:

                                st.error(
                                    f"❌ BUY failed: {result}"
                                )


                        except Exception as e:

                            st.error(
                                f"❌ Paper BUY error: {e}"
                            )


            with b2:

                if st.button(
                    "⚡ CHECK SL / TARGET",
                    key="offline_test_check",
                    use_container_width=True,
                ):

                    try:

                        ok, result = trader.auto_exit(

                            current_price=safe_float(
                                test_ltp
                            ),

                            symbol=test_symbol,

                            option_mode=test_option,
                        )


                        if ok:

                            st.success(
                                f"⚡ Auto Exit: {result}"
                            )

                        else:

                            st.info(
                                f"ℹ️ No exit triggered: {result}"
                            )


                    except Exception as e:

                        st.error(
                            f"❌ Auto Exit error: {e}"
                        )


            with b3:

                if st.button(
                    f"🔴 SELL / EXIT {test_option}",
                    key="offline_test_sell",
                    use_container_width=True,
                ):

                    try:

                        ok, result = trader.sell(

                            symbol=test_symbol,

                            option_mode=test_option,

                            current_price=safe_float(
                                test_ltp
                            ),
                        )


                        if ok:

                            st.success(
                                f"🔴 {test_option} EXITED | "
                                f"Realized P&L "
                                f"₹{safe_float(result):,.2f}"
                            )

                        else:

                            st.warning(
                                f"⚠️ EXIT: {result}"
                            )


                    except Exception as e:

                        st.error(
                            f"❌ Exit error: {e}"
                        )


            st.caption(
                "Suggested test: BUY at ₹150 → "
                "set Current LTP ₹160 → "
                "CHECK SL/TARGET → then SELL/EXIT. "
                "Target at 2% is ₹153, so ₹160 "
                "should trigger Target."
            )


    # ========================================================
    # MAIN DASHBOARD
    # ========================================================

    st.title(
        "📊 SmartTrader Dashboard"
    )


    # ========================================================
    # SELECTED MARKET DISPLAY
    # ========================================================

    if market_type == "FUTURES":

        st.caption(
            f"📌 Selected Futures: {dashboard_symbol}"
        )

    elif market_type == "OPTIONS":

        st.caption(
            f"📌 Selected Index: {dashboard_symbol} "
            f"• Option Mode: {option_mode}"
        )

    else:

        st.caption(
            f"📌 Selected Symbol: {dashboard_symbol}"
        )


    # ========================================================
    # MARKET BANNER
    # ========================================================

    if trade_market_status["market"] == "DELTA":

        st.success(
            "🟢 DELTA EXCHANGE • MARKET OPEN 24/7"
        )

    elif trade_market_status["status"] == "ENTRY_OPEN":

        st.success(
            "🟢 INDIAN MARKET • ENTRY OPEN • 09:15–15:30"
        )

    elif trade_market_status["status"] == "PRE_MARKET":

        st.warning(
            "🟡 INDIAN MARKET • PRE-MARKET • Opens 09:15"
        )

    else:

        st.error(
            "🔴 INDIAN MARKET • CLOSED • New entries blocked"
        )


    # ========================================================
    # TOP METRICS
    # ========================================================

    c1, c2, c3, c4 = st.columns(4)


    with c1:

        st.metric(
            "Symbol",
            dashboard_symbol,
        )


    with c2:

        if is_delta_symbol(
            dashboard_symbol
        ):

            st.metric(
                "Price",
                f"${underlying_price:,.8f}",
            )

        else:

            st.metric(
                "Price",
                f"₹{underlying_price:,.2f}",
            )


    with c3:

        st.metric(
            "Signal",
            signal,
        )


    with c4:

        st.metric(
            "Strength",
            f"{signal_strength:.0f}%",
        )


    # ========================================================
    # OPTION MARKET
    # ========================================================

    if market_type == "OPTIONS":

        st.markdown(
            "### 📦 Option Market"
        )


        o1, o2, o3, o4 = st.columns(4)


        with o1:

            st.metric(
                "Underlying",
                f"₹{underlying_price:,.2f}",
            )


        with o2:

            ce_contract = (
                option_contract_by_option.get(
                    "CE"
                )
            )

            st.metric(
                "CE Strike",
                (
                    str(
                        ce_contract.get(
                            "strike"
                        )
                    )
                    if ce_contract
                    else "N/A"
                ),
            )


        with o3:

            st.metric(
                "CE LTP",
                (
                    f"₹{ce_ltp:,.2f}"
                    if ce_ltp > 0
                    else "N/A"
                ),
            )


        with o4:

            st.metric(
                "PE LTP",
                (
                    f"₹{pe_ltp:,.2f}"
                    if pe_ltp > 0
                    else "N/A"
                ),
            )


        if (
            ce_ltp <= 0
            or pe_ltp <= 0
        ):

            st.warning(
                "⚠️ Actual CE/PE option LTP "
                "available नहीं है। Auto Paper "
                "Option Entry blocked है."
            )


    # ========================================================
    # INDICATORS
    # ========================================================

    st.markdown(
        "### 📈 Indicators"
    )


    i1, i2, i3, i4, i5 = st.columns(5)


    ema9 = safe_float(
        signal_data.get(
            "EMA9",
            signal_data.get(
                "EMA_9",
                0,
            ),
        )
    )


    ema21 = safe_float(
        signal_data.get(
            "EMA21",
            signal_data.get(
                "EMA_21",
                0,
            ),
        )
    )


    rsi = safe_float(
        signal_data.get(
            "RSI",
            0,
        )
    )


    macd = safe_float(
        signal_data.get(
            "MACD",
            0,
        )
    )


    supertrend = safe_float(
        signal_data.get(
            "SUPERTREND",
            signal_data.get(
                "SUPERTREND_VALUE",
                signal_data.get(
                    "SuperTrend",
                    0,
                ),
            ),
        )
    )


    delta_display = is_delta_symbol(
        dashboard_symbol
    )


    with i1:

        if delta_display:

            st.metric(
                "EMA 9",
                f"${ema9:,.8f}",
            )

        else:

            st.metric(
                "EMA 9",
                f"₹{ema9:,.2f}",
            )


    with i2:

        if delta_display:

            st.metric(
                "EMA 21",
                f"${ema21:,.8f}",
            )

        else:

            st.metric(
                "EMA 21",
                f"₹{ema21:,.2f}",
            )


    with i3:

        st.metric(
            "RSI",
            f"{rsi:.2f}",
        )


    with i4:

        if delta_display:

            st.metric(
                "MACD",
                f"${macd:,.8f}",
            )

        else:

            st.metric(
                "MACD",
                f"{macd:.4f}",
            )


    with i5:

        if delta_display:

            st.metric(
                "SuperTrend",
                f"${supertrend:,.8f}",
            )

        else:

            st.metric(
                "SuperTrend",
                f"₹{supertrend:,.2f}",
            )


    # ========================================================
    # ACTIVE POSITIONS
    # ========================================================

    st.markdown(
        "### 📦 Active Positions"
    )


    try:

        active_positions = (
            trader.get_active_positions()
        )

    except Exception as e:

        logging.warning(
            f"Active positions error: {e}"
        )

        active_positions = {}


    if not isinstance(
        active_positions,
        dict,
    ):

        active_positions = {}


    if active_positions:

        rows = []


        for (
            position_key,
            position,
        ) in active_positions.items():

            if not isinstance(
                position,
                dict,
            ):

                continue


            pos_symbol = str(
                position.get(
                    "symbol",
                    "",
                )
            )


            pos_option = str(
                position.get(
                    "option_mode",
                    "N/A",
                )
            ).upper()


            pos_side = normalize_position_side(
                position
            )


            entry = safe_float(
                position.get(
                    "entry",
                    0,
                )
            )


            qty = int(
                safe_float(
                    position.get(
                        "qty",
                        0,
                    )
                )
            )


            # ------------------------------------------------
            # CURRENT LTP
            # ------------------------------------------------

            if (
                market_type == "OPTIONS"
                and pos_option == "CE"
            ):

                ltp = ce_ltp

            elif (
                market_type == "OPTIONS"
                and pos_option == "PE"
            ):

                ltp = pe_ltp

            elif is_delta_symbol(
                pos_symbol
            ):

                try:

                    delta_signal = get_signals(
                        pos_symbol
                    )

                    if isinstance(
                        delta_signal,
                        dict,
                    ):

                        ltp = safe_float(
                            delta_signal.get(
                                "Price",
                                delta_signal.get(
                                    "Close",
                                    0,
                                ),
                            )
                        )

                    else:

                        ltp = 0.0

                except Exception:

                    ltp = 0.0

            else:

                ltp = current_price


            # ------------------------------------------------
            # P&L
            # ------------------------------------------------

            if (
                ltp > 0
                and qty > 0
            ):

                if pos_side == "SHORT":

                    pnl = (
                        entry
                        - ltp
                    ) * qty

                else:

                    pnl = (
                        ltp
                        - entry
                    ) * qty

            else:

                pnl = 0.0


            # ------------------------------------------------
            # SL / TARGET
            # ------------------------------------------------

            stoploss = safe_float(
                position.get(
                    "stoploss",
                    position.get(
                        "stop_loss",
                        0,
                    ),
                )
            )


            target = safe_float(
                position.get(
                    "target",
                    0,
                )
            )


            # ------------------------------------------------
            # DISPLAY
            # ------------------------------------------------

            if is_delta_symbol(
                pos_symbol
            ):

                entry_display = (
                    f"${entry:,.8f}"
                )

                ltp_display = (
                    f"${ltp:,.8f}"
                    if ltp > 0
                    else "N/A"
                )

                stop_display = (
                    f"${stoploss:,.8f}"
                    if stoploss > 0
                    else "N/A"
                )

                target_display = (
                    f"${target:,.8f}"
                    if target > 0
                    else "N/A"
                )

                pnl_display = (
                    f"${pnl:,.8f}"
                )

            else:

                entry_display = (
                    f"₹{entry:,.2f}"
                )

                ltp_display = (
                    f"₹{ltp:,.2f}"
                    if ltp > 0
                    else "N/A"
                )

                stop_display = (
                    f"₹{stoploss:,.2f}"
                    if stoploss > 0
                    else "N/A"
                )

                target_display = (
                    f"₹{target:,.2f}"
                    if target > 0
                    else "N/A"
                )

                pnl_display = (
                    f"₹{pnl:,.2f}"
                )


            rows.append({

                "Position":
                    pos_side,

                "Symbol":
                    pos_symbol,

                "Option":
                    pos_option,

                "Entry":
                    entry_display,

                "LTP":
                    ltp_display,

                "Qty":
                    qty,

                "Stop Loss":
                    stop_display,

                "Target":
                    target_display,

                "P&L":
                    pnl_display,
            })


        if rows:

            st.table(
                rows
            )

        else:

            st.info(
                "No valid active positions."
            )

    else:

        st.info(
            "No active positions."
        )


    # ========================================================
    # DETAILED DASHBOARD PAGE
    # ========================================================
    #
    # THIS IS THE MAIN FIX.
    #
    # Indian OPTIONS:
    #     symbol = selected underlying
    #     trade_symbol = None
    #
    # Delta FUTURES:
    #     symbol = selected futures
    #     trade_symbol = selected futures
    #
    # Therefore pages/dashboard_page.py will not accidentally
    # fall back to ^NSEI when BANKNIFTY/SENSEX/etc. is selected.
    #
    # ========================================================

    try:

        if market_type == "FUTURES" and futures_symbol:

            detailed_dashboard_symbol = futures_symbol

            detailed_trade_symbol = futures_symbol

        else:

            detailed_dashboard_symbol = symbol

            detailed_trade_symbol = None


        # ----------------------------------------------------
        # Keep session state synchronized.
        # ----------------------------------------------------

        st.session_state[
            "dashboard_symbol"
        ] = detailed_dashboard_symbol

        st.session_state[
            "selected_underlying_symbol"
        ] = symbol


        # ----------------------------------------------------
        # Call detailed dashboard.
        # ----------------------------------------------------

        dashboard_page(

            trader=trader,

            current_price=underlying_price,

            symbol=detailed_dashboard_symbol,

            market_type=market_type,

            trade_symbol=detailed_trade_symbol,

        )

    except Exception as e:

        logging.exception(
            f"Dashboard Page Error: {e}"
        )

        st.error(
            f"❌ Dashboard Page Error: {e}"
        )


# ============================================================
# MARKET PAGE
# ============================================================

elif page == "📈 Market":

    try:

        market_page(

            symbol=symbol,

            trader=trader,

            INDICES=INDICES,

            FO_STOCKS=FO_STOCKS,

            scan_all_option_chain=(
                scan_all_option_chain
            ),

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
            ),
        )

    except Exception as e:

        st.error(
            f"❌ Market Page Error: {e}"
        )


# ============================================================
# TRADING PAGE
# ============================================================

elif page == "💰 Trading":

    try:

        trading_page(
            trader=trader,
            symbol=symbol,
        )

    except Exception as e:

        st.error(
            f"❌ Trading Page Error: {e}"
        )


# ============================================================
# PORTFOLIO PAGE
# ============================================================

elif page == "📦 Portfolio":

    try:

        portfolio_page(
            trader=trader,
            symbol=symbol,
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


# ============================================================
# REPORTS PAGE
# ============================================================

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


# ============================================================
# SETTINGS PAGE
# ============================================================

elif page == "⚙ Settings":

    try:

        settings_page()

    except Exception as e:

        st.error(
            f"❌ Settings Error: {e}"
        )


# ============================================================
# AUTO REFRESH
# ============================================================
# 15 seconds
# ============================================================

try:

    st_autorefresh(
        interval=15000,
        key="market_refresh",
    )

except Exception:

    pass


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "Jha SmartTrader AI Pro • "
    "AI Trading Terminal"
)


ist = ZoneInfo(
    "Asia/Kolkata"
)

st.caption(
    "Last Refresh: "
    + datetime.now(
        ist
    ).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    + " IST"
)