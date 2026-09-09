# ============================================================
# Jha SmartTrader AI Pro
# dashboard.py
# ============================================================

from pathlib import Path
from datetime import datetime, time
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
# AUTO REFRESH
# ============================================================

try:
    st_autorefresh(
        interval=15000,
        key="market_refresh",
    )
except Exception:
    pass


# ============================================================
# SAFE FLOAT
# ============================================================

def safe_float(value, default=0.0):
    try:
        if value is None:
            return default

        if isinstance(value, str):
            value = value.strip()

            if not value:
                return default

            value = value.replace(",", "")

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
    value = str(value or "").upper().strip()

    if "BUY" in value and "SELL" not in value:
        return "BUY"

    if "SELL" in value and "BUY" not in value:
        return "SELL"

    return "HOLD"


# ============================================================
# POSITION SIDE
# ============================================================

def normalize_position_side(position):
    """
    Normalize BUY/SELL and LONG/SHORT into LONG/SHORT.

    Indian Options:
        BUY  -> LONG

    Delta Futures:
        BUY  -> LONG
        SELL -> SHORT
    """

    if not isinstance(position, dict):
        return "LONG"

    raw_position_side = str(
        position.get(
            "position_side",
            ""
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
                "BUY"
            )
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
    # DELTA EXCHANGE
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
    # INDIAN MARKET
    # --------------------------------------------------------

    now = datetime.now().time()

    entry_start = time(
        9,
        15,
    )

    entry_end = time(
        15,
        30,
    )

    if now < entry_start:

        return {
            "market": "INDIA",
            "status": "PRE_MARKET",
            "market_open": False,
            "entry_allowed": False,
            "manage_positions": False,
            "message": (
                "⏰ Indian market opens at 09:15."
            ),
        }

    if entry_start <= now < entry_end:

        return {
            "market": "INDIA",
            "status": "ENTRY_OPEN",
            "market_open": True,
            "entry_allowed": True,
            "manage_positions": True,
            "message": (
                "🟢 Indian market is OPEN."
            ),
        }

    return {
        "market": "INDIA",
        "status": "MARKET_CLOSED",
        "market_open": False,
        "entry_allowed": False,
        "manage_positions": False,
        "message": (
            "🔴 Indian market closed. "
            "New BUY entry allowed only "
            "between 09:15 and 15:30."
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
# LOGO
# ============================================================

BASE_DIR = Path(
    __file__
).resolve().parent

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
        dict
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
            "Kotak Neo"
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
    "^NSEI"
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
    "AI Combo"
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
        "ALL"
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

        strike_modes = (
            get_strike_modes()
        )

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
        "ATM"
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

        futures_data = (
            delta.get_futures()
        )

        if futures_data:

            for product in futures_data:

                if not isinstance(
                    product,
                    dict
                ):
                    continue

                product_symbol = (
                    product.get(
                        "symbol"
                    )
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
        futures_symbols[0]
    )

    if default_futures not in futures_symbols:

        default_futures = (
            futures_symbols[0]
        )


    futures_symbol = st.sidebar.selectbox(

        "Delta Futures",

        futures_symbols,

        index=futures_symbols.index(
            default_futures
        ),

        key="dashboard_futures_symbol",
    )


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
            dict
        ):

            current_price = safe_float(
                ticker.get(
                    "price",
                    ticker.get(
                        "close",
                        0
                    )
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
    # GET SIGNAL
    # ========================================================

    try:

        if market_type == "FUTURES":

            signal_data = get_signals(
                futures_symbol
            )

        else:

            signal_data = get_signals(
                symbol
            )

    except Exception as e:

        signal_data = {
            "error": str(e)
        }


    if not isinstance(
        signal_data,
        dict
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
                            0
                        )
                    )
                )

        else:

            current_price = safe_float(
                signal_data.get(
                    "Close",
                    0
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

        index_name = (
            OPTION_SYMBOL_MAP[
                symbol
            ]
        )


        if option_mode in [
            "CE",
            "ALL",
        ]:

            try:

                ce_contract = (
                    resolve_option_contract(

                        index_name=index_name,

                        underlying_price=(
                            underlying_price
                        ),

                        option_type="CE",

                        strike_mode=strike_mode,
                    )
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


        if option_mode in [
            "PE",
            "ALL",
        ]:

            try:

                pe_contract = (
                    resolve_option_contract(

                        index_name=index_name,

                        underlying_price=(
                            underlying_price
                        ),

                        option_type="PE",

                        strike_mode=strike_mode,
                    )
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

        try:

            option_scan = (
                scan_all_option_chain()
            )

        except Exception as e:

            option_scan = None

            logging.warning(
                f"Option chain error: {e}"
            )


        if isinstance(
            option_scan,
            dict
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
                dict
            ):

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
                            0
                        )
                    )

                    if value > 0:

                        price_by_option[
                            "CE"
                        ] = value

                        break


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
                            0
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
            0
        )
    )

    pe_ltp = safe_float(
        price_by_option.get(
            "PE",
            0
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
                "HOLD"
            )
        )
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
                    0
                )
            )
        )
    )


    # ========================================================
    # TRADE SYMBOL
    # ========================================================

    if (
        market_type == "FUTURES"
        and futures_symbol
    ):

        trade_symbol = futures_symbol

    else:

        trade_symbol = symbol


    # ========================================================
    # MARKET STATUS
    # ========================================================

    trade_market_status = (
        get_market_status(
            trade_symbol
        )
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
                        0
                    )
                )


                if option_price > 0:

                    trade_manager.check_position(
                        current_price=option_price,
                        symbol=trade_symbol,
                        option_mode=option_mode,
                    )


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
                dict
            ):

                for (
                    position_key,
                    position
                ) in active_positions.items():

                    if not isinstance(
                        position,
                        dict
                    ):
                        continue


                    pos_option = str(
                        position.get(
                            "option_mode",
                            "N/A"
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

                        if current_price > 0:

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
            # OPTIONS ALL
            # =================================================

            if (
                market_type == "OPTIONS"
                and option_mode == "ALL"
            ):

                ce_price = safe_float(
                    price_by_option.get(
                        "CE",
                        0
                    )
                )

                pe_price = safe_float(
                    price_by_option.get(
                        "PE",
                        0
                    )
                )


                if signal == "BUY":

                    if (
                        ce_price <= 0
                        or pe_price <= 0
                    ):

                        st.warning(
                            "⛔ AUTO PAPER ALL blocked: "
                            "actual CE + PE LTP required."
                        )

                    else:

                        success, result = (
                            trade_manager.process(

                                symbol=trade_symbol,

                                signal="BUY",

                                current_price=ce_price,

                                capital=trader.balance,

                                option_mode="ALL",

                                lots=int(
                                    selected_lots
                                ),

                                lot_size=int(
                                    LOT_SIZE
                                ),

                                price_by_option={
                                    "CE": ce_price,
                                    "PE": pe_price,
                                },
                            )
                        )


                        if success:

                            st.success(
                                "🤖 AUTO PAPER ALL: "
                                + str(result)
                            )

                        else:

                            st.info(
                                "ℹ️ AUTO PAPER ALL: "
                                + str(result)
                            )


                elif signal == "SELL":

                    if (
                        ce_price <= 0
                        and pe_price <= 0
                    ):

                        st.warning(
                            "⛔ AUTO PAPER EXIT blocked: "
                            "actual option LTP unavailable."
                        )

                    else:

                        success, result = (
                            trade_manager.process(

                                symbol=trade_symbol,

                                signal="SELL",

                                current_price=(
                                    ce_price
                                    if ce_price > 0
                                    else pe_price
                                ),

                                capital=trader.balance,

                                option_mode="ALL",

                                lots=int(
                                    selected_lots
                                ),

                                lot_size=int(
                                    LOT_SIZE
                                ),

                                price_by_option={
                                    "CE": ce_price,
                                    "PE": pe_price,
                                },
                            )
                        )


                        if success:

                            st.success(
                                "🔴 AUTO PAPER ALL EXIT: "
                                + str(result)
                            )

                        else:

                            st.info(
                                "ℹ️ AUTO PAPER ALL: "
                                + str(result)
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
                        0
                    )
                )


                if option_price <= 0:

                    st.warning(
                        f"⛔ AUTO PAPER {option_mode} blocked: "
                        "actual option LTP unavailable."
                    )

                else:

                    success, result = (
                        trade_manager.process(

                            symbol=trade_symbol,

                            signal=signal,

                            current_price=option_price,

                            capital=trader.balance,

                            option_mode=option_mode,

                            lots=int(
                                selected_lots
                            ),

                            lot_size=int(
                                LOT_SIZE
                            ),

                            option_contract=(
                                option_contract
                            ),
                        )
                    )


                    if success:

                        st.success(
                            "🤖 AUTO PAPER "
                            f"{option_mode}: "
                            + str(result)
                        )

                    else:

                        st.info(
                            "ℹ️ Trade: "
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
    # MAIN DASHBOARD
    # ========================================================

    st.title(
        "📊 SmartTrader Dashboard"
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
            trade_symbol
        )


    with c2:

        if is_delta_symbol(trade_symbol):

            st.metric(
                "Price",
                f"${underlying_price:,.8f}"
            )

        else:

            st.metric(
                "Price",
                f"₹{underlying_price:,.2f}"
            )


    with c3:

        st.metric(
            "Signal",
            signal
        )


    with c4:

        st.metric(
            "Strength",
            f"{signal_strength:.0f}%"
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
                f"₹{underlying_price:,.2f}"
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
                )
            )


        with o3:

            st.metric(
                "CE LTP",
                (
                    f"₹{ce_ltp:,.2f}"
                    if ce_ltp > 0
                    else "N/A"
                )
            )


        with o4:

            st.metric(
                "PE LTP",
                (
                    f"₹{pe_ltp:,.2f}"
                    if pe_ltp > 0
                    else "N/A"
                )
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
                0
            )
        )
    )

    ema21 = safe_float(
        signal_data.get(
            "EMA21",
            signal_data.get(
                "EMA_21",
                0
            )
        )
    )

    rsi = safe_float(
        signal_data.get(
            "RSI",
            0
        )
    )

    macd = safe_float(
        signal_data.get(
            "MACD",
            0
        )
    )

    supertrend = safe_float(
        signal_data.get(
            "SUPERTREND",
            signal_data.get(
                "SUPERTREND_VALUE",
                signal_data.get(
                    "SuperTrend",
                    0
                )
            )
        )
    )


    delta_display = is_delta_symbol(
        trade_symbol
    )


    with i1:

        if delta_display:

            st.metric(
                "EMA 9",
                f"${ema9:,.8f}"
            )

        else:

            st.metric(
                "EMA 9",
                f"₹{ema9:,.2f}"
            )


    with i2:

        if delta_display:

            st.metric(
                "EMA 21",
                f"${ema21:,.8f}"
            )

        else:

            st.metric(
                "EMA 21",
                f"₹{ema21:,.2f}"
            )


    with i3:

        st.metric(
            "RSI",
            f"{rsi:.2f}"
        )


    with i4:

        if delta_display:

            st.metric(
                "MACD",
                f"${macd:,.8f}"
            )

        else:

            st.metric(
                "MACD",
                f"{macd:.4f}"
            )


    with i5:

        if delta_display:

            st.metric(
                "SuperTrend",
                f"${supertrend:,.8f}"
            )

        else:

            st.metric(
                "SuperTrend",
                f"₹{supertrend:,.2f}"
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
        dict
    ):

        active_positions = {}


    if active_positions:

        rows = []


        for (
            position_key,
            position
        ) in active_positions.items():

            if not isinstance(
                position,
                dict
            ):
                continue


            pos_symbol = str(
                position.get(
                    "symbol",
                    ""
                )
            )


            pos_option = str(
                position.get(
                    "option_mode",
                    "N/A"
                )
            ).upper()


            pos_side = normalize_position_side(
                position
            )


            entry = safe_float(
                position.get(
                    "entry",
                    0
                )
            )


            qty = int(
                safe_float(
                    position.get(
                        "qty",
                        0
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

            elif is_delta_symbol(pos_symbol):

                try:
                    delta_signal = get_signals(pos_symbol)

                    if isinstance(delta_signal, dict):
                        ltp = safe_float(
                            delta_signal.get("Price", 0)
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

            if ltp > 0 and qty > 0:

                if pos_side == "SHORT":

                    pnl = (
                        entry - ltp
                    ) * qty

                else:

                    pnl = (
                        ltp - entry
                    ) * qty

            else:

                pnl = 0.0


            # ------------------------------------------------
            # DISPLAY PRICES
            # ------------------------------------------------

            stoploss = safe_float(
                position.get(
                    "stoploss",
                    position.get(
                        "stop_loss",
                        0
                    )
                )
            )


            target = safe_float(
                position.get(
                    "target",
                    0
                )
            )


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


            rows.append(

                {

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
                        ( 
                            f"${pnl:,.8f}"
                                if is_delta_symbol(pos_symbol)
                                else f"₹{pnl:,.2f}"
                        ),
                    }
                )


        if rows:

            st.table(rows)
               

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

    try:

        dashboard_page(

            trader,

            underlying_price,

            symbol,

        )
        

    except Exception as e:

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
# FOOTER
# ============================================================

st.divider()

st.caption(
    "Jha SmartTrader AI Pro • "
    "AI Trading Terminal"
)

st.caption(
    "Last Refresh: "
    + datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )
)