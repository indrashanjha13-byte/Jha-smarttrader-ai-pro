# ============================================================
# Jha SmartTrader AI Pro
# dashboard.py
# ============================================================

from pathlib import Path
from datetime import datetime, time
from zoneinfo import ZoneInfo
import pandas as pd
import inspect
import logging

import streamlit as st
from PIL import Image
from streamlit_autorefresh import st_autorefresh

# ============================================================
# PROJECT IMPORTS
# ============================================================

from signals import get_signals
from ai_decision import ai_decision
from paper_trading import PaperTrader
from trade_manager import TradeManager
from backtest_engine import BacktestEngine

from ai_learning import auto_strategy

from auto_mode import (
    enable_auto,
    disable_auto,
)

from option_chain import (
    scan_all_option_chain,
    get_exact_option_prices,
)

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
# KOTAK NEO OPTION RESOLVER
# ============================================================

from kotak_option_resolver import resolve_atm_option

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
# OPTION CHAIN CACHE
# ============================================================

@st.cache_data(ttl=10, show_spinner=False)
def get_cached_option_chain():

    try:
        return scan_all_option_chain()

    except Exception as e:
        logging.warning(
            f"Option chain error: {e}"
        )
        return None

# ============================================================
# EXACT OPTION PRICE CACHE
# ============================================================

@st.cache_data(ttl=10, show_spinner=False)
def get_cached_exact_option_prices(
    index_name,
    strike,
    expiry=None,
    underlying_price=0.0,
):
    """
    Get exact CE/PE option prices.

    IMPORTANT:
    underlying_price is passed to option_chain.py
    so Kotak Neo can be used as the primary LTP source.
    """

    try:

        underlying_price = safe_float(
            underlying_price
        )

        return get_exact_option_prices(
            index_name=index_name,
            strike=strike,
            expiry=expiry,
            underlying_price=underlying_price,
        )

    except Exception as e:

        logging.warning(
            f"Exact option price error: {e}"
        )

        return None

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

    if not isinstance(position, dict):
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
# DELTA SYMBOL DETECTION
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
# MARKET STATUS
# ============================================================

def get_market_status(symbol):

    # --------------------------------------------------------
    # DELTA = 24/7
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
    # INDIA MARKET STATUS
    # --------------------------------------------------------

    ist = ZoneInfo("Asia/Kolkata")

    now_dt = datetime.now(ist)
    now = now_dt.time()

    # --------------------------------------------------------
    # WEEKEND CHECK
    # Saturday = 5
    # Sunday   = 6
    # --------------------------------------------------------

    if now_dt.weekday() >= 5:

        return {
            "market": "INDIA",
            "status": "MARKET_CLOSED",
            "market_open": False,
            "entry_allowed": False,
            "manage_positions": True,
            "message": "🔴 Indian Market CLOSED • Weekend.",
        }

    # --------------------------------------------------------
    # MARKET TIMINGS
    # --------------------------------------------------------

    pre_market_start = time(9, 0)
    market_open = time(9, 15)
    market_close = time(15, 30)

    # --------------------------------------------------------
    # PRE-MARKET
    # --------------------------------------------------------

    if pre_market_start <= now < market_open:

        return {
            "market": "INDIA",
            "status": "PRE_MARKET",
            "market_open": False,
            "entry_allowed": False,
            "manage_positions": True,
            "message": "🟡 Indian Market PRE-MARKET • Opens 09:15 IST.",
         }

    # --------------------------------------------------------
    # MARKET OPEN
    # --------------------------------------------------------

    if market_open <= now < market_close:

        return {
            "market": "INDIA",
            "status": "ENTRY_OPEN",
            "market_open": True,
            "entry_allowed": True,
            "manage_positions": True,
            "message": "🟢 Indian Market OPEN • 09:15–15:30 IST.",
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
        "message": "🔴 Indian Market CLOSED • Session 09:15–15:30 IST.",
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

logo_path = BASE_DIR / "logo.png"

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

# ============================================================
# DELTA ALL COINS FUNCTIONS
# ============================================================
# DELTA ALL COINS
# ============================================================

@st.cache_data(ttl=10)
def get_cached_delta_products():
    """Load all live Delta Futures/Perpetual contracts."""
    try:
        delta = DeltaFutures()
        products = delta.get_futures()

        if not isinstance(products, list):
            return []

        return products

    except Exception as e:
        logging.exception("Delta products error")
        return []

@st.cache_data(ttl=5)
def get_cached_delta_tickers():
    """Load live tickers for Delta Futures/Perpetual contracts."""
    try:
        delta = DeltaFutures()
        tickers = delta.get_all_tickers()

        if not isinstance(tickers, list):
            return []

        return tickers

    except Exception as e:
        logging.exception("Delta tickers error")
        return []

def render_delta_all_coins():

    st.title("📊 Delta All Coins")
    st.caption(
        "Delta Exchange India • Live Futures & Perpetual Contracts • 24/7"
    )

    # --------------------------------------------------------
    # LOAD PRODUCTS + TICKERS
    # --------------------------------------------------------

    products = get_cached_delta_products()
    tickers = get_cached_delta_tickers()

    if not products:
        st.error("❌ Delta Futures contracts load nahi ho rahe.")
        st.info("Please check Delta API connection.")
        return

    # --------------------------------------------------------
    # MAP PRODUCTS
    # --------------------------------------------------------

    product_map = {}

    for product in products:

        if not isinstance(product, dict):
            continue

        symbol = str(
            product.get("symbol", "")
        ).strip().upper()

        if symbol:
            product_map[symbol] = product

    # --------------------------------------------------------
    # MAP TICKERS
    # --------------------------------------------------------

    ticker_map = {}

    for ticker in tickers:

        if not isinstance(ticker, dict):
            continue

        symbol = str(
            ticker.get("symbol", "")
        ).strip().upper()

        if symbol:
            ticker_map[symbol] = ticker

    # --------------------------------------------------------
    # BUILD ALL CONTRACT DATA
    # --------------------------------------------------------

    rows = []

    for symbol, product in product_map.items():

        ticker = ticker_map.get(symbol, {})

        price = safe_float(
            ticker.get(
                "close",
                ticker.get(
                    "price",
                    ticker.get(
                        "mark_price",
                        0
                    )
                )
            )
        )

        change = safe_float(
            ticker.get(
                "ltp_change_24h",
                ticker.get(
                    "mark_change_24h",
                    0
                )
            )
        )

        high = safe_float(
            ticker.get(
                "high",
                0
            )
        )

        low = safe_float(
            ticker.get(
                "low",
                0
            )
        )

        volume = safe_float(
            ticker.get(
                "volume",
                0
            )
        )

        oi = safe_float(
            ticker.get(
                "oi",
                ticker.get(
                    "oi_contracts",
                    0
                )
            )
        )

        oi_value = safe_float(
            ticker.get(
                "oi_value_usd",
                ticker.get(
                    "oi_value",
                    0
                )
            )
        )

        funding = safe_float(
            ticker.get(
                "funding_rate",
                0
            )
        )

        leverage = safe_float(
            ticker.get(
                "leverage",
                product.get(
                    "default_leverage",
                    0
                )
            )
        )

        contract_type = str(
            product.get(
                "contract_type",
                ticker.get(
                    "contract_type",
                    ""
                )
            )
        ).strip()

        contract_upper = contract_type.upper()

        if "PERPETUAL" in contract_upper:
            contract_display = "PERPETUAL"
        elif "FUTURE" in contract_upper:
            contract_display = "FUTURES"
        else:
            contract_display = (
                contract_upper
                if contract_upper
                else "-"
            )

        status = str(
            ticker.get(
                "product_trading_status",
                product.get(
                    "state",
                    ""
                )
            )
        ).strip()

        underlying = product.get(
            "underlying_asset",
            {}
        )

        if isinstance(underlying, dict):
            coin = str(
                underlying.get(
                    "symbol",
                    symbol.replace(
                        "USD",
                        ""
                    )
                )
            )
        else:
            coin = str(
                underlying
                or symbol.replace(
                    "USD",
                    ""
                )
            )

        rows.append(
            {
                "Coin": coin,
                "Symbol": symbol,
                "LTP": price,
                "24H %": change,
                "24H High": high,
                "24H Low": low,
                "Volume": volume,
                "Open Interest": oi,
                "OI Value": oi_value,
                "Funding": funding,
                "Leverage": leverage,
                "Contract": contract_display,
                "Status": status or "-",
                "Description": str(
                    product.get(
                        "description",
                        ""
                    )
                ),
            }
        )

    # --------------------------------------------------------
    # DATAFRAME
    # --------------------------------------------------------

    if not rows:
        st.warning(
            "⚠️ Live Delta contracts available nahi hain."
        )
        return

    df = pd.DataFrame(rows)

    df = df.sort_values(
        by=["Coin", "Symbol"]
    ).reset_index(
        drop=True
    )

    # --------------------------------------------------------
    # TOP METRICS
    # --------------------------------------------------------

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric(
            "📦 Total Contracts",
            len(df)
        )

    with c2:
        st.metric(
            "🟢 Live Prices",
            int(
                (df["LTP"] > 0).sum()
            )
        )

    with c3:
        st.metric(
            "♾️ Perpetual",
            int(
                (
                    df["Contract"]
                    == "PERPETUAL"
                ).sum()
            )
        )

    with c4:
        st.metric(
            "📅 Futures",
            int(
                (
                    df["Contract"]
                    == "FUTURES"
                ).sum()
            )
        )

    st.divider()

    # --------------------------------------------------------
    # SEARCH
    # --------------------------------------------------------

    search = st.text_input(
        "🔎 Search Delta Coin / Contract",
        placeholder=(
            "BTCUSD, ETHUSD, SOLUSD, XRPUSD..."
        ),
        key="delta_all_coins_search"
    )

    contract_filter = st.selectbox(
        "Contract Type",
        [
            "ALL",
            "PERPETUAL",
            "FUTURES",
        ],
        key="delta_contract_filter"
    )

    filtered_df = df.copy()

    if search:

        search_text = (
            str(search)
            .strip()
            .upper()
        )

        filtered_df = filtered_df[
            filtered_df[
                "Symbol"
            ].str.contains(
                search_text,
                na=False
            )
            |
            filtered_df[
                "Coin"
            ].str.contains(
                search_text,
                na=False
            )
        ]

    if contract_filter != "ALL":

        filtered_df = filtered_df[
            filtered_df[
                "Contract"
            ]
            == contract_filter
        ]

    st.caption(
        f"Showing {len(filtered_df)} "
        f"of {len(df)} contracts"
    )

    # --------------------------------------------------------
    # EMPTY SEARCH
    # --------------------------------------------------------

    if filtered_df.empty:

        st.warning(
            "❌ Search ke liye koi Delta "
            "contract nahi mila."
        )
        return

    # --------------------------------------------------------
    # DISPLAY TABLE
    # --------------------------------------------------------

    display_df = filtered_df.copy()

    display_df["LTP"] = display_df[
        "LTP"
    ].apply(
        lambda x: (
            f"${x:,.8f}"
            if x > 0
            else "-"
        )
    )

    display_df["24H %"] = display_df[
        "24H %"
    ].apply(
        lambda x: f"{x:.2f}%"
    )

    display_df["24H High"] = display_df[
        "24H High"
    ].apply(
        lambda x: (
            f"${x:,.8f}"
            if x > 0
            else "-"
        )
    )

    display_df["24H Low"] = display_df[
        "24H Low"
    ].apply(
        lambda x: (
            f"${x:,.8f}"
            if x > 0
            else "-"
        )
    )

    display_df["Volume"] = display_df[
        "Volume"
    ].apply(
        lambda x: f"{x:,.2f}"
    )

    display_df["Open Interest"] = (
        display_df[
            "Open Interest"
        ].apply(
            lambda x: f"{x:,.2f}"
        )
    )

    display_df["OI Value"] = (
        display_df[
            "OI Value"
        ].apply(
            lambda x: f"${x:,.2f}"
        )
    )

    display_df["Funding"] = (
        display_df[
            "Funding"
        ].apply(
            lambda x: f"{x:.6f}%"
        )
    )

    display_df["Leverage"] = (
        display_df[
            "Leverage"
        ].apply(
            lambda x: (
                f"{x:.0f}x"
                if x > 0
                else "-"
            )
        )
    )

    st.dataframe(
        display_df[
            [
                "Coin",
                "Symbol",
                "LTP",
                "24H %",
                "24H High",
                "24H Low",
                "Volume",
                "Open Interest",
                "OI Value",
                "Funding",
                "Leverage",
                "Contract",
                "Status",
            ]
        ],
        use_container_width=True,
        hide_index=True,
        height=600,
    )

    # --------------------------------------------------------
    # SELECT CONTRACT
    # --------------------------------------------------------

    st.divider()

    selected_symbol = st.selectbox(
        "🪙 Select Coin / Contract for AI Analysis",
        filtered_df[
            "Symbol"
        ].tolist(),
        key="delta_all_coins_selected"
    )

    selected_row = filtered_df[
        filtered_df[
            "Symbol"
        ]
        == selected_symbol
    ]

    if selected_row.empty:
        return

    selected = selected_row.iloc[0]

    # --------------------------------------------------------
    # SELECTED CONTRACT
    # --------------------------------------------------------

    st.subheader(
        f"🪙 {selected_symbol}"
    )

    m1, m2, m3, m4 = st.columns(4)

    with m1:
        st.metric(
            "Live Price",
            (
                f"${selected['LTP']:,.8f}"
                if selected["LTP"] > 0
                else "N/A"
            )
        )

    with m2:
        st.metric(
            "24H Change",
            f"{selected['24H %']:.2f}%"
        )

    with m3:
        st.metric(
            "Open Interest",
            f"{selected['Open Interest']:,.2f}"
        )

    with m4:
        st.metric(
            "Funding",
            f"{selected['Funding']:.6f}%"
        )

    # --------------------------------------------------------
    # CONTRACT DETAILS
    # --------------------------------------------------------

    with st.expander(
        "📋 Contract Details",
        expanded=False
    ):

        selected_product = product_map.get(
            selected_symbol,
            {}
        )

        details = {
            "Symbol": selected_symbol,
            "Coin": selected["Coin"],
            "Contract Type": selected_product.get(
                "contract_type",
                "N/A"
            ),
            "Product ID": selected_product.get(
                "id",
                "N/A"
            ),
            "Description": selected_product.get(
                "description",
                "N/A"
            ),
            "Underlying": selected_product.get(
                "underlying_asset",
                "N/A"
            ),
            "Settlement Asset": selected_product.get(
                "settling_asset",
                "N/A"
            ),
            "Tick Size": selected_product.get(
                "tick_size",
                "N/A"
            ),
            "Contract Value": selected_product.get(
                "contract_value",
                "N/A"
            ),
            "Leverage": selected["Leverage"],
            "Status": selected["Status"],
        }

        st.dataframe(
            pd.DataFrame(
                list(details.items()),
                columns=[
                    "Field",
                    "Value"
                ]
            ),
            use_container_width=True,
            hide_index=True,
        )

    # --------------------------------------------------------
    # AI ANALYSIS
    # --------------------------------------------------------

    st.subheader(
        "🤖 AI Analysis"
    )

    try:

        analysis_signal = get_signals(
            selected_symbol
        )

        if isinstance(
            analysis_signal,
            dict
        ):

            signal_value = (
                analysis_signal.get(
                    "signal",
                    analysis_signal.get(
                        "action",
                        "HOLD"
                    )
                )
            )

            confidence = safe_float(
                analysis_signal.get(
                    "confidence",
                    0
                )
            )

            trend = analysis_signal.get(
                "trend",
                "N/A"
            )

            a1, a2, a3 = st.columns(3)

            with a1:
                st.metric(
                    "Signal",
                    str(
                        signal_value
                    ).upper()
                )

            with a2:
                st.metric(
                    "Confidence",
                    f"{confidence:.1f}%"
                )

            with a3:
                st.metric(
                    "Trend",
                    str(trend)
                )

            with st.expander(
                "🔍 Full AI Signal Data",
                expanded=False
            ):
                st.json(
                    analysis_signal
                )

        else:

            st.info(
                "AI signal data available nahi hai."
            )

    except Exception as e:

        st.warning(
            f"⚠️ AI analysis unavailable: {e}"
        )

    # --------------------------------------------------------
    # SAFETY
    # --------------------------------------------------------

    st.info(
        "ℹ️ Delta All Coins screen market-data "
        "aur AI analysis ke liye hai. Is screen "
        "se koi live order automatically place "
        "nahi hota."
    )

# ============================================================

# ============================================================

# NAVIGATION
# ============================================================

page = st.sidebar.radio(
    "📂 Navigation",
    [
        "🏠 Dashboard",
        "📊 Delta All Coins",
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

index_name = OPTION_SYMBOL_MAP.get(
    symbol,
    "",
)

exact_strike = 0.0
exact_strike_from_api = 0.0

expiry_from_api = None

ce_ltp_exact = 0.0
pe_ltp_exact = 0.0

exact_option_data = None

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

    index_name = OPTION_SYMBOL_MAP[
        symbol
    ]

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

    st.sidebar.success(
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
                        ).strip().upper()
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

live_confirm = False

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
# HELPER:
# KOTAK ATM CONTRACT
# ============================================================

def get_kotak_atm_contract(
    index_name,
    underlying_price,
    option_type,
    fallback_lot_size=1,
):

    try:

        result = resolve_atm_option(
            index_name,
            underlying_price,
            option_type,
        )

        if not isinstance(
            result,
            dict,
        ):

            logging.warning(
                "Kotak resolver returned "
                "non-dict result."
            )

            return None

        contracts = result.get(
            "contracts",
            {},
        )

        if not isinstance(
            contracts,
            dict,
        ):
            contracts = {}

        raw_contract = contracts.get(
            option_type
        )

        if not isinstance(
            raw_contract,
            dict,
        ):

            raw_contract = result.get(
                option_type
            )

        if not isinstance(
            raw_contract,
            dict,
        ):

            logging.warning(
                f"Kotak {option_type} "
                "contract missing."
            )

            return None

        contract = dict(
            raw_contract
        )

        kotak_expiry = (
            contract.get(
                "expiry"
            )
            or result.get(
                "expiry"
            )
        )

        kotak_exchange = (
            contract.get(
                "exchange_segment"
            )
            or result.get(
                "exchange_segment"
            )
            or "nse_fo"
        )

        kotak_strike = safe_float(
            contract.get(
                "strike",
                0,
            )
        )

        if kotak_strike <= 0:

            kotak_strike = safe_float(
                result.get(
                    "atm_strike",
                    0,
                )
            )

        kotak_lot_size = int(
            safe_float(
                contract.get(
                    "lot_size",
                    fallback_lot_size,
                ),
                fallback_lot_size,
            )
        )

        if kotak_lot_size <= 0:

            kotak_lot_size = int(
                fallback_lot_size
            )

        kotak_symbol = str(
            contract.get(
                "trading_symbol",
                contract.get(
                    "pTrdSymbol",
                    contract.get(
                        "symbol",
                        "",
                    ),
                ),
            )
            or ""
        ).strip()

        kotak_token = str(
            contract.get(
                "token",
                contract.get(
                    "pSymbol",
                    "",
                ),
            )
            or ""
        ).strip()

        kotak_instrument = str(
            contract.get(
                "instrument",
                contract.get(
                    "pInstType",
                    "OPTIDX",
                ),
            )
            or "OPTIDX"
        ).strip()

        kotak_option_type = str(
            contract.get(
                "option_type",
                option_type,
            )
            or option_type
        ).upper()

        normalized = dict(
            contract
        )

        normalized.update(
            {
                "index": index_name,

                "underlying_price": safe_float(
                    result.get(
                        "underlying_price",
                        underlying_price,
                    )
                ),

                "option_type": kotak_option_type,

                "strike": kotak_strike,

                "expiry": kotak_expiry,

                "lot_size": kotak_lot_size,

                "trading_symbol": kotak_symbol,

                "symbol": kotak_symbol,

                "kotak_symbol": kotak_symbol,

                "kotak_trading_symbol": kotak_symbol,

                "kotak_token": kotak_token,

                "exchange_segment": kotak_exchange,

                "kotak_exchange_segment": kotak_exchange,

                "instrument": kotak_instrument,

                "kotak_instrument": kotak_instrument,

                "source": "KOTAK_NEO",
            }
        )

        if kotak_symbol:

            normalized[
                "display_symbol"
            ] = kotak_symbol

        else:

            normalized[
                "display_symbol"
            ] = (
                f"{index_name} "
                f"{kotak_expiry or ''} "
                f"{kotak_strike:g}"
                f"{kotak_option_type}"
            ).strip()

        logging.info(
            "KOTAK ATM CONTRACT | "
            f"{index_name} | "
            f"{kotak_option_type} | "
            f"Strike={kotak_strike} | "
            f"Expiry={kotak_expiry} | "
            f"Symbol={kotak_symbol} | "
            f"Token={kotak_token}"
        )

        return normalized

    except Exception as e:

        logging.exception(
            f"Kotak {option_type} resolver error: {e}"
        )

        return None

# ============================================================
# HELPER:
# TRADE MANAGER COMPATIBILITY
# ============================================================

def process_trade_compatible(
    symbol,
    signal,
    current_price,
    capital,
    option_mode="N/A",
    lots=1,
    lot_size=1,
    strike=None,
    expiry=None,
    option_type=None,
    price_by_option=None,
):

    """
    Calls TradeManager.process() using only arguments
    supported by the currently installed TradeManager.

    Compatible with older/newer TradeManager versions.
    """

    try:

        process_method = (
            trade_manager.process
        )

        # IMPORTANT:
        # signature must exist before it is used.
        signature = None
        supported = set()

        try:

            signature = inspect.signature(
                process_method
            )

            supported = set(
                signature.parameters.keys()
            )

        except Exception as e:

            logging.warning(
                f"TradeManager signature inspect error: {e}"
            )

        kwargs = {
            "symbol": symbol,
            "signal": signal,
            "current_price": current_price,
            "capital": capital,
            "option_mode": option_mode,
            "lots": lots,
            "lot_size": lot_size,
            "strike": strike,
            "expiry": expiry,
            "option_type": option_type,
            "price_by_option": price_by_option,
        }

        # ----------------------------------------------------
        # **kwargs support
        # ----------------------------------------------------

        accepts_kwargs = False

        if signature is not None:

            try:

                for parameter in (
                    signature.parameters.values()
                ):

                    if (
                        parameter.kind
                        == inspect.Parameter.VAR_KEYWORD
                    ):

                        accepts_kwargs = True
                        break

            except Exception:
                pass

        if accepts_kwargs:

            return process_method(
                **kwargs
            )

        # ----------------------------------------------------
        # Only supported parameters
        # ----------------------------------------------------

        filtered_kwargs = {}

        for key, value in kwargs.items():

            if (
                key in supported
                and value is not None
            ):

                filtered_kwargs[
                    key
                ] = value

        return process_method(
            **filtered_kwargs
        )

    except Exception as e:

        logging.exception(
            f"TradeManager process error: {e}"
        )

        return (
            False,
            str(e),
        )

# ============================================================
# DASHBOARD PAGE
# ============================================================

if page == "🏠 Dashboard":

    # ========================================================
    # DASHBOARD SYMBOL
    # ========================================================

    if (
        market_type == "FUTURES"
        and futures_symbol
    ):

        dashboard_symbol = futures_symbol

    else:

        dashboard_symbol = symbol

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
    # AI DECISION
    # ========================================================

    ai_result = {
        "decision": "HOLD",
        "score": 0,
        "confidence": 0.0,
        "volume_confirmed": False,
    }

    if not signal_data.get("error"):

        try:

            ai_result = ai_decision(
                rsi=signal_data.get(
                    "RSI",
                    50.0,
                ),

                macd=signal_data.get(
                    "MACD",
                    0.0,
                ),

                macd_signal=signal_data.get(
                    "MACD_SIGNAL",
                    0.0,
                ),

                ema9=signal_data.get(
                    "EMA9",
                    0.0,
                ),

                ema21=signal_data.get(
                    "EMA21",
                    0.0,
                ),

                supertrend=signal_data.get(
                    "ST_DIRECTION",
                    0.0,
                ),

                volume=signal_data.get(
                    "Volume",
                    0.0,
                ),

                avg_volume=signal_data.get(
                    "AVG_VOLUME",
                    0.0,
                ),
            )

        except Exception as e:

            logging.exception(
                "AI decision calculation failed"
            )

            ai_result = {
                "decision": "HOLD",
                "score": 0,
                "confidence": 0.0,
                "volume_confirmed": False,
            }

    ai_decision_value = str(
        ai_result.get(
            "decision",
            "HOLD",
        )
    ).upper()

    ai_score = safe_float(
        ai_result.get(
            "score",
            0,
        )
    )

    ai_confidence = safe_float(
        ai_result.get(
            "confidence",
            0,
        )
    )

    ai_volume_confirmed = bool(
        ai_result.get(
            "volume_confirmed",
            False,
        )
    )

    signal_data[
        "AI_DECISION"
    ] = ai_decision_value

    signal_data[
        "AI_SCORE"
    ] = ai_score

    signal_data[
        "AI_CONFIDENCE"
    ] = ai_confidence

    signal_data[
        "AI_VOLUME_CONFIRMED"
    ] = ai_volume_confirmed

    st.session_state[
        "ai_decision"
    ] = ai_decision_value

    st.session_state[
        "ai_score"
    ] = ai_score

    st.session_state[
        "ai_confidence"
    ] = ai_confidence

    st.session_state[
        "ai_volume_confirmed"
    ] = ai_volume_confirmed


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
                    signal_data.get(
                        "Price",
                        0,
                    ),
                )
            )

        underlying_price = current_price

    st.session_state[
        "current_price"
    ] = underlying_price

    # ========================================================
    # RESET OPTION DATA
    # ========================================================

    option_contract = None
    option_contract_by_option = {}
    price_by_option = {}

    exact_strike = 0.0
    exact_strike_from_api = 0.0

    expiry_from_api = None

    ce_ltp_exact = 0.0
    pe_ltp_exact = 0.0

    exact_option_data = None

    # ========================================================
    # OPTION CONTRACT RESOLUTION
    # ========================================================

    if (
        market_type == "OPTIONS"
        and is_option_index
        and underlying_price > 0
    ):

        index_name = OPTION_SYMBOL_MAP[
            symbol
        ]

        # ====================================================
        # RESOLVE CE
        # ====================================================

        if option_mode in [
            "CE",
            "ALL",
        ]:

            ce_contract = None

            if strike_mode == "ATM":

                ce_contract = (
                    get_kotak_atm_contract(
                        index_name=index_name,
                        underlying_price=underlying_price,
                        option_type="CE",
                        fallback_lot_size=LOT_SIZE,
                    )
                )

            if ce_contract is None:

                try:

                    ce_contract = (
                        resolve_option_contract(
                            index_name=index_name,
                            underlying_price=underlying_price,
                            option_type="CE",
                            strike_mode=strike_mode,
                        )
                    )

                except Exception as e:

                    logging.warning(
                        f"CE contract error: {e}"
                    )

                    ce_contract = None

            if isinstance(
                ce_contract,
                dict,
            ):

                option_contract_by_option[
                    "CE"
                ] = ce_contract

        # ====================================================
        # RESOLVE PE
        # ====================================================

        if option_mode in [
            "PE",
            "ALL",
        ]:

            pe_contract = None

            if strike_mode == "ATM":

                pe_contract = (
                    get_kotak_atm_contract(
                        index_name=index_name,
                        underlying_price=underlying_price,
                        option_type="PE",
                        fallback_lot_size=LOT_SIZE,
                    )
                )

            if pe_contract is None:

                try:

                    pe_contract = (
                        resolve_option_contract(
                            index_name=index_name,
                            underlying_price=underlying_price,
                            option_type="PE",
                            strike_mode=strike_mode,
                        )
                    )

                except Exception as e:

                    logging.warning(
                        f"PE contract error: {e}"
                    )

                    pe_contract = None

            if isinstance(
                pe_contract,
                dict,
            ):

                option_contract_by_option[
                    "PE"
                ] = pe_contract

        # ====================================================
        # SELECTED CONTRACT
        # ====================================================

        if option_mode in [
            "CE",
            "PE",
        ]:

            option_contract = (
                option_contract_by_option.get(
                    option_mode
                )
            )

        # ====================================================
        # FIND STRIKE
        # ====================================================

        if option_contract:

            exact_strike = safe_float(
                option_contract.get(
                    "strike",
                    0,
                )
            )

        else:

            ce = option_contract_by_option.get(
                "CE"
            )

            pe = option_contract_by_option.get(
                "PE"
            )

            if ce:

                exact_strike = safe_float(
                    ce.get(
                        "strike",
                        0,
                    )
                )

            elif pe:

                exact_strike = safe_float(
                    pe.get(
                        "strike",
                        0,
                    )
                )

        # ====================================================
        # FIND EXPIRY
        # ====================================================

        kotak_expiry = None

        if option_contract:

            kotak_expiry = (
                option_contract.get(
                    "expiry"
                )
            )

        else:

            ce = option_contract_by_option.get(
                "CE"
            )

            pe = option_contract_by_option.get(
                "PE"
            )

            if ce:

                kotak_expiry = ce.get(
                    "expiry"
                )

            elif pe:

                kotak_expiry = pe.get(
                    "expiry"
                )

        # ====================================================
        # EXACT OPTION LTP
        #
        # IMPORTANT:
        # underlying_price is REQUIRED here so that
        # option_chain.py uses Kotak Neo.
        # ====================================================

        if (
            exact_strike > 0
            and index_name
        ):

            try:

                exact_option_data = (
                    get_cached_exact_option_prices(
                        index_name=index_name,
                        strike=exact_strike,
                        expiry=kotak_expiry,
                        underlying_price=underlying_price,
                    )
                )

                # ------------------------------------------------
                # FALLBACK WITHOUT EXPIRY
                #
                # IMPORTANT:
                # underlying_price must still be passed.
                # ------------------------------------------------

                if not isinstance(
                    exact_option_data,
                    dict,
                ):

                    exact_option_data = (
                        get_cached_exact_option_prices(
                            index_name=index_name,
                            strike=exact_strike,
                            expiry=None,
                            underlying_price=underlying_price,
                        )
                    )

                logging.info(
                    "EXACT OPTION RESULT | "
                    f"Index={index_name} | "
                    f"Underlying={underlying_price} | "
                    f"Strike={exact_strike} | "
                    f"Expiry={kotak_expiry} | "
                    f"Data={exact_option_data}"
                )

            except Exception as e:

                logging.exception(
                    "Exact option LTP error"
                )

                exact_option_data = None

        # ====================================================
        # READ OPTION PRICE
        # ====================================================

        if isinstance(
            exact_option_data,
            dict,
        ):

            exact_strike_from_api = safe_float(
                exact_option_data.get(
                    "strike",
                    exact_strike,
                )
            )

            if exact_strike_from_api <= 0:

                exact_strike_from_api = (
                    exact_strike
                )

            expiry_from_api = (
                exact_option_data.get(
                    "expiry",
                    kotak_expiry,
                )
            )

            ce_ltp_exact = safe_float(
                exact_option_data.get(
                    "CE",
                    0,
                )
            )

            pe_ltp_exact = safe_float(
                exact_option_data.get(
                    "PE",
                    0,
                )
            )

            if ce_ltp_exact > 0:

                price_by_option[
                    "CE"
                ] = ce_ltp_exact

            if pe_ltp_exact > 0:

                price_by_option[
                    "PE"
                ] = pe_ltp_exact
            # =================================================
            #SYNC KOTAK CONTRACTS FROM EXACT OPTION API
            # =================================================

            def _normalize_kotak_contract(contract, option_type):

                if not isinstance(contract, dict):
                    return None

                normalized = dict(contract)

                trading_symbol = str(
                    contract.get("trading_symbol")
                    or contract.get("kotak_trading_symbol")
                    or contract.get("symbol")
                    or ""
                ).strip()

                token = str(
                   contract.get("token")
                   or contract.get("kotak_token")
                   or ""
                ).strip()

                exchange_segment = str(
                    contract.get("exchange_segment")
                    or contract.get("kotak_exchange_segment")
                    or "nse_fo"
                ).strip()

                instrument = str(
                    contract.get("instrument")
                    or contract.get("kotak_instrument")
                    or "OPTIDX"
                ).strip()

                normalized.update({
                    "trading_symbol": trading_symbol,
                    "symbol": trading_symbol,
                    "kotak_symbol": trading_symbol,
                    "kotak_trading_symbol": trading_symbol,
                    "token": token,
                    "kotak_token": token,
                    "exchange_segment": exchange_segment,
                    "kotak_exchange_segment": exchange_segment,
                    "instrument": instrument,
                    "kotak_instrument": instrument,
                    "option_type": str(
                        contract.get("option_type", option_type)
                    ).upper(),
                    "source": "KOTAK_NEO",
                })

                return normalized

            ce_api_contract = _normalize_kotak_contract(
                exact_option_data.get("CE_CONTRACT"),
                "CE",
            )

            pe_api_contract = _normalize_kotak_contract(
                exact_option_data.get("PE_CONTRACT"),
                "PE",
            )

            if ce_api_contract:
                option_contract_by_option[
                    "CE"
                ] = ce_api_contract

            if pe_api_contract:
                option_contract_by_option[
                    "PE"
            ] = pe_api_contract

            # =================================================
            # UPDATE CE
            # =================================================

            if "CE" in option_contract_by_option:

                ce_contract = (
                    option_contract_by_option[
                        "CE"
                    ]
                )

                ce_contract[
                    "strike"
                ] = exact_strike_from_api

                if (
                    not ce_contract.get(
                        "expiry"
                    )
                    and expiry_from_api
                ):

                    ce_contract[
                        "expiry"
                    ] = expiry_from_api

                ce_contract[
                    "ltp"
                ] = ce_ltp_exact

            # =================================================
            # UPDATE PE
            # =================================================

            if "PE" in option_contract_by_option:

                pe_contract = (
                    option_contract_by_option[
                        "PE"
                    ]
                )

                pe_contract[
                    "strike"
                ] = exact_strike_from_api

                if (
                    not pe_contract.get(
                        "expiry"
                    )
                    and expiry_from_api
                ):

                    pe_contract[
                        "expiry"
                    ] = expiry_from_api

                pe_contract[
                    "ltp"
                ] = pe_ltp_exact

            # =================================================
            # SELECTED CONTRACT UPDATE
            # =================================================

            if option_mode in [
                "CE",
                "PE",
            ]:

                option_contract = (
                    option_contract_by_option.get(
                        option_mode
                    )
                )

        else:

            logging.warning(
                "Exact option data unavailable | "
                f"Index={index_name} | "
                f"Underlying={underlying_price} | "
                f"Strike={exact_strike}"
            )

    # ========================================================
    # SAVE OPTION DATA
    # ========================================================

    st.session_state[
        "option_prices"
    ] = price_by_option

    st.session_state[
        "option_contracts"
    ] = option_contract_by_option

    st.session_state[
        "kotak_option_contracts"
    ] = option_contract_by_option

    st.session_state[
        "option_index"
    ] = index_name

    st.session_state[
        "option_mode"
    ] = option_mode

    st.session_state[
        "option_strike_mode"
    ] = strike_mode

    # ========================================================
    # OPTION CONTRACT DISPLAY
    # ========================================================

    if (
        market_type == "OPTIONS"
        and is_option_index
    ):

        st.sidebar.divider()

        st.sidebar.subheader(
            "📦 Option Contract"
        )

        # ====================================================
        # ALL
        # ====================================================

        if option_mode == "ALL":

            ce = (
                option_contract_by_option.get(
                    "CE"
                )
            )

            pe = (
                option_contract_by_option.get(
                    "PE"
                )
            )

            if ce:

                st.sidebar.success(
                    "🟢 CE Ready"
                )

                st.sidebar.caption(
                    f"Strike: "
                    f"{ce.get('strike', 'N/A')}"
                )

                st.sidebar.caption(
                    f"Expiry: "
                    f"{ce.get('expiry', 'N/A')}"
                )

                st.sidebar.caption(
                    f"LTP: ₹"
                    f"{safe_float(ce.get('ltp', 0)):,.2f}"
                )

                st.sidebar.caption(
                    "Kotak Symbol: "
                    f"{ce.get('kotak_trading_symbol', 'N/A')}"
                )

                st.sidebar.caption(
                    "Kotak Token: "
                    f"{ce.get('kotak_token', 'N/A')}"
                )

                st.sidebar.caption(
                    "Segment: "
                    f"{ce.get('kotak_exchange_segment', 'nse_fo')}"
                )

                st.sidebar.caption(
                    "Instrument: "
                    f"{ce.get('kotak_instrument', 'OPTIDX')}"
                )

                st.sidebar.caption(
                    f"Lot Size: "
                    f"{ce.get('lot_size', LOT_SIZE)}"
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
                    f"Strike: "
                    f"{pe.get('strike', 'N/A')}"
                )

                st.sidebar.caption(
                    f"Expiry: "
                    f"{pe.get('expiry', 'N/A')}"
                )

                st.sidebar.caption(
                    f"LTP: ₹"
                    f"{safe_float(pe.get('ltp', 0)):,.2f}"
                )

                st.sidebar.caption(
                    "Kotak Symbol: "
                    f"{pe.get('kotak_trading_symbol', 'N/A')}"
                )

                st.sidebar.caption(
                    "Kotak Token: "
                    f"{pe.get('kotak_token', 'N/A')}"
                )

                st.sidebar.caption(
                    "Segment: "
                    f"{pe.get('kotak_exchange_segment', 'nse_fo')}"
                )

                st.sidebar.caption(
                    "Instrument: "
                    f"{pe.get('kotak_instrument', 'OPTIDX')}"
                )

                st.sidebar.caption(
                    f"Lot Size: "
                    f"{pe.get('lot_size', LOT_SIZE)}"
                )

            else:

                st.sidebar.error(
                    "❌ PE Contract unavailable"
                )

        # ====================================================
        # CE / PE
        # ====================================================

        elif option_contract:

            st.sidebar.success(
                "📋 Option Contract Ready"
            )

            st.sidebar.caption(
                f"Type: "
                f"{option_contract.get('option_type', option_mode)}"
            )

            st.sidebar.caption(
                f"Strike: "
                f"{option_contract.get('strike', 'N/A')}"
            )

            st.sidebar.caption(
                f"Expiry: "
                f"{option_contract.get('expiry', 'N/A')}"
            )

            st.sidebar.caption(
                f"Mode: "
                f"{strike_mode}"
            )

            st.sidebar.caption(
                f"LTP: ₹"
                f"{safe_float(option_contract.get('ltp', 0)):,.2f}"
            )

            st.sidebar.caption(
                "Kotak Symbol: "
                f"{option_contract.get('kotak_trading_symbol', 'N/A')}"
            )

            st.sidebar.caption(
                "Kotak Token: "
                f"{option_contract.get('kotak_token', 'N/A')}"
            )

            st.sidebar.caption(
                "Exchange Segment: "
                f"{option_contract.get('kotak_exchange_segment', 'nse_fo')}"
            )

            st.sidebar.caption(
                "Instrument: "
                f"{option_contract.get('kotak_instrument', 'OPTIDX')}"
            )

        else:

            st.sidebar.warning(
                "⚠️ Option contract unavailable."
            )

    # ========================================================
    # EXACT OPTION PRICE DISPLAY
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

    if (
        market_type == "OPTIONS"
        and is_option_index
    ):

        st.sidebar.divider()

        st.sidebar.subheader(
            "💰 Exact Option LTP"
        )

        if option_mode in [
            "CE",
            "ALL",
        ]:

            if ce_ltp > 0:

                st.sidebar.success(
                    f"🟢 CE LTP : ₹{ce_ltp:,.2f}"
                )

            else:

                st.sidebar.warning(
                    "⚠️ CE exact LTP unavailable"
                )

        if option_mode in [
            "PE",
            "ALL",
        ]:

            if pe_ltp > 0:

                st.sidebar.success(
                    f"🔴 PE LTP : ₹{pe_ltp:,.2f}"
                )

            else:

                st.sidebar.warning(
                    "⚠️ PE exact LTP unavailable"
                )

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
    # AI SIGNAL OVERRIDE
    # ========================================================

    ai_trade_signal = normalize_signal(
        signal_data.get(
            "AI_DECISION",
            "HOLD",
        )
    )

    ai_trade_confidence = safe_float(
        signal_data.get(
            "AI_CONFIDENCE",
            0,
        )
    )

    if ai_trade_signal in [
        "BUY",
        "SELL",
    ]:

        signal = ai_trade_signal

    else:

        signal = "HOLD"

    # ========================================================
    # SIGNAL STRENGTH / AI CONFIDENCE
    # ========================================================

    signal_strength = safe_float(
        signal_data.get(
            "AI_CONFIDENCE",
            signal_data.get(
                "Signal_Strength",
                signal_data.get(
                    "Strength",
                    signal_data.get(
                        "Confidence",
                        0,
                    ),
                ),
            ),
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

    st.session_state[
        "trade_symbol"
    ] = trade_symbol

    # ========================================================
    # MARKET STATUS FOR TRADE
    # ========================================================

    trade_market_status = get_market_status(
        trade_symbol
    )

    # ========================================================
    # AI CONFIDENCE GATE
    # ========================================================

    MIN_AUTO_CONFIDENCE = 70.0

    auto_confidence_ok = (
        signal_strength >= MIN_AUTO_CONFIDENCE
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
                        0,
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
            # INDIAN MARKET ENTRY BLOCK
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
            # AI DIRECTIONAL OPTION MODE
            #
            # BUY  -> CE BUY
            # SELL -> PE BUY
            #
            # ALL does NOT buy CE + PE together.
            # =================================================

            elif (
                market_type == "OPTIONS"
                and option_mode == "ALL"
            ):

                # -------------------------------------------------
                # AI SIGNAL → OPTION DIRECTION
                # -------------------------------------------------

                if signal == "BUY":

                    ai_option = "CE"
                    direction_text = "🟢 BULLISH → CE BUY"

                elif signal == "SELL":

                    ai_option = "PE"
                    direction_text = "🔴 BEARISH → PE BUY"

                else:

                    ai_option = None
                    direction_text = ""

                # -------------------------------------------------
                # AI CONFIDENCE CHECK
                # -------------------------------------------------

                if not auto_confidence_ok:

                    st.info(
                        "ℹ️ AUTO PAPER ALL blocked: "
                        f"AI confidence {signal_strength:.1f}% "
                        f"< {MIN_AUTO_CONFIDENCE:.0f}%."
                    )

                # -------------------------------------------------
                # HOLD / UNKNOWN → NO ENTRY
                # -------------------------------------------------

                elif ai_option is None:

                    st.info(
                        "ℹ️ AUTO PAPER ALL: "
                        f"Signal={signal}. No option entry."
                    )

                else:

                    # -------------------------------------------------
                    # GET EXACT OPTION LTP
                    # -------------------------------------------------

                    option_price = safe_float(
                        price_by_option.get(
                            ai_option,
                            0,
                        )
                    )

                    # -------------------------------------------------
                    # GET OPTION CONTRACT
                    # -------------------------------------------------

                    selected_contract = (
                        option_contract_by_option.get(
                            ai_option,
                            {},
                        )
                    )

                    selected_strike = safe_float(
                        selected_contract.get(
                            "strike",
                            0,
                        )
                    )

                    selected_expiry = (
                        selected_contract.get(
                            "expiry"
                        )
                    )

                    # -------------------------------------------------
                    # LTP VALIDATION
                    # -------------------------------------------------

                    if option_price <= 0:

                        st.warning(
                            "⛔ AUTO PAPER ALL blocked: "
                            f"{ai_option} exact LTP unavailable."
                        )

                    # -------------------------------------------------
                    # STRIKE VALIDATION
                    # -------------------------------------------------

                    elif selected_strike <= 0:

                        st.warning(
                            "⛔ AUTO PAPER ALL blocked: "
                            f"{ai_option} strike unavailable."
                        )

                    # -------------------------------------------------
                    # EXPIRY VALIDATION
                    # -------------------------------------------------

                    elif not selected_expiry:

                        st.warning(
                            "⛔ AUTO PAPER ALL blocked: "
                            f"{ai_option} expiry unavailable."
                        )

                    else:

                        # -------------------------------------------------
                        # EXISTING POSITION CHECK
                        # -------------------------------------------------

                        try:

                            existing_position = (
                                trader.get_position(
                                    trade_symbol,
                                    ai_option,
                                )
                            )

                        except Exception:

                            existing_position = None

                        # -------------------------------------------------
                        # DUPLICATE ENTRY BLOCK
                        # -------------------------------------------------

                        if existing_position:

                            st.info(
                                "ℹ️ AUTO PAPER ALL: "
                                f"{ai_option} position already active. "
                                "Duplicate entry blocked."
                            )

                        else:

                            # -------------------------------------------------
                            # OPTION BUY
                            #
                            # IMPORTANT:
                            # Even when AI signal = SELL,
                            # we BUY the PE option.
                            #
                            # Therefore actual transaction signal
                            # remains BUY.
                            # -------------------------------------------------

                            (
                                success,
                                result,
                            ) = process_trade_compatible(

                                symbol=trade_symbol,

                                signal="BUY",

                                current_price=option_price,

                                capital=trader.balance,

                                option_mode=ai_option,

                                lots=int(
                                    selected_lots
                                ),

                                lot_size=int(
                                    LOT_SIZE
                                ),

                                strike=selected_strike,

                                expiry=selected_expiry,

                                option_type=ai_option,

                                price_by_option={
                                    ai_option: option_price
                                },
                            )

                            # -------------------------------------------------
                            # SUCCESS
                            # -------------------------------------------------

                            if success:

                                st.success(
                                    "🤖 AUTO PAPER ALL | "
                                    f"{direction_text} | "
                                    f"Strike {selected_strike:g} | "
                                    f"LTP ₹{option_price:,.2f} | "
                                    f"Expiry {selected_expiry} | "
                                    + str(
                                        result
                                    )
                                )

                            # -------------------------------------------------
                            # FAILED
                            # -------------------------------------------------

                            else:

                                st.info(
                                    "ℹ️ AUTO PAPER ALL "
                                    f"{ai_option} ENTRY: "
                                    + str(
                                        result
                                    )
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

                selected_contract = (
                    option_contract_by_option.get(
                        option_mode,
                        {},
                    )
                )

                selected_strike = safe_float(
                    selected_contract.get(
                        "strike",
                        0,
                    )
                )

                selected_expiry = (
                    selected_contract.get(
                        "expiry"
                    )
                )

                if option_price <= 0:

                    st.warning(
                        f"⛔ AUTO PAPER {option_mode} blocked: "
                        "exact option LTP unavailable."
                    )

                elif selected_strike <= 0:

                    st.warning(
                        f"⚠️ AUTO PAPER {option_mode} blocked: "
                        "strike unavailable."
                    )

                elif not selected_expiry:

                    st.warning(
                        f"⚠️ AUTO PAPER {option_mode} blocked: "
                        "expiry unavailable."
                    )
                # ------------------------------------------------
                # BUY ONLY IF NO POSITION
                # ------------------------------------------------

                elif signal == "BUY":

                    if not auto_confidence_ok:

                        st.info(
                            f"ℹ️ AUTO PAPER {option_mode} BUY blocked: "
                            f"AI confidence {signal_strength:.1f}% "
                            f"< {MIN_AUTO_CONFIDENCE:.0f}%."
                        )

                    else:

                        try:

                            existing_position = (
                                trader.get_position(
                                    trade_symbol,
                                    option_mode,
                                )
                            )

                        except Exception:

                            existing_position = None

                        if existing_position:

                            st.info(
                                f"ℹ️ AUTO PAPER {option_mode}: "
                                "Position already active."
                            )

                        else:
                            (
                                success,
                                result,
                            ) = process_trade_compatible(

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

                                strike=selected_strike,

                                expiry=selected_expiry,

                                option_type=option_mode,

                                price_by_option={
                                    option_mode: option_price
                                },
                            )

                            if success:

                                st.success(
                                    "🤖 AUTO PAPER "
                                    f"{option_mode} BUY | "
                                    f"Strike {selected_strike:g} | "
                                    f"LTP ₹{option_price:,.2f} | "
                                    f"Expiry {selected_expiry} | "
                                    + str(result)
                                )

                            else:

                                st.info(
                                    f"ℹ️ AUTO PAPER {option_mode}: "
                                    + str(result)
                                )

                # ------------------------------------------------
                # SELL = EXIT ONLY
                # ------------------------------------------------

                elif signal == "SELL":

                    try:

                        existing_position = (
                            trader.get_position(
                                trade_symbol,
                                option_mode,
                            )
                        )

                    except Exception:

                        existing_position = None

                    if not existing_position:

                        st.info(
                            f"ℹ️ AUTO PAPER {option_mode}: "
                            "No active BUY position to exit."
                        )

                    else:

                        (
                            success,
                            result,
                        ) = process_trade_compatible(

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

                            strike=selected_strike,

                            expiry=selected_expiry,

                            option_type=option_mode,

                            price_by_option={
                                option_mode: option_price
                            },
                        )

                        if success:

                            st.success(
                                "🔴 AUTO PAPER "
                                f"{option_mode} EXIT | "
                                f"LTP ₹{option_price:,.2f} | "
                                + str(result)
                            )

                        else:

                            st.info(
                                f"ℹ️ AUTO PAPER "
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

                # -------------------------------------------------
                # BUY ENTRY → AI CONFIDENCE REQUIRED
                # -------------------------------------------------

                elif (
                    signal == "BUY"
                    and not auto_confidence_ok
                ):

                    st.info(
                        "ℹ️ AUTO PAPER BUY blocked: "
                        f"AI confidence {signal_strength:.1f}% "
                        f"< {MIN_AUTO_CONFIDENCE:.0f}%."
                    )

                else:

                    (
                        success,
                        result,
                    ) = process_trade_compatible(

                        symbol=trade_symbol,

                        signal=signal,

                        current_price=current_price,

                        capital=trader.balance,

                        option_mode="N/A",

                        lots=1,

                        lot_size=1,
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

                default_test_strike = (
                    safe_float(
                        exact_strike_from_api
                    )
                    or safe_float(
                        exact_strike
                    )
                    or 23400.0
                )

                test_strike = st.number_input(
                    "Test Strike",
                    min_value=1.0,
                    value=float(
                        default_test_strike
                    ),
                    step=50.0,
                    key="offline_test_strike",
                )

            with tc3:

                test_expiry = st.text_input(
                    "Test Expiry",
                    value=(
                        str(
                            expiry_from_api
                            or "PAPER"
                        )
                    ),
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

            st.info(
                f"Test Contract: {test_index} "
                f"{test_strike:g}{test_option} | "
                f"Expiry: {test_expiry} | "
                f"Qty: {int(test_qty)}"
            )

            try:

                active_test_position = (
                    trader.get_position(
                        test_symbol,
                        test_option,
                    )
                )

            except Exception:

                active_test_position = None

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

                                # -------------------------------------------------
                                # OFFLINE TEST: SYNC TEST LTP INTO PAPER POSITION
                                # -------------------------------------------------

                                try:
                                    test_position = trader.get_position(
                                        test_symbol,
                                        test_option,
                                    )

                                    if isinstance(
                                        test_position,
                                        dict,
                                    ):
                                        test_ltp_value = safe_float(
                                            test_ltp
                                        )

                                        if test_ltp_value > 0:
                                            test_position[
                                                "current_price"
                                            ] = test_ltp_value

                                            test_position[
                                                "last_price"
                                            ] = test_ltp_value

                                except Exception:
                                    logging.exception(
                                        "Offline test LTP sync failed"
                                    )

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

                        exit_result = trader.auto_exit(
                            current_price=safe_float(test_ltp),
                            symbol=test_symbol,
                            option_mode=test_option,
                            strike=test_strike,
                            expiry=test_expiry,
                        )

                        if exit_result is None:

                            st.info(
                                f"ℹ️ No exit triggered at "
                                f"₹{safe_float(test_ltp):,.2f}. "
                                f"SL/Target not reached."
                            )

                        else:

                            st.success(
                                f"⚡ Auto Exit: {exit_result}"
                            )

                    except Exception as e:

                        logging.exception(
                            "Offline paper option auto exit failed"
                        )

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
                "Current LTP ₹160 → CHECK SL/TARGET → "
                "then SELL/EXIT."
            )

    # ========================================================
    # DETAILED DASHBOARD PAGE
    # ========================================================

    try:

        if (
            market_type == "FUTURES"
            and futures_symbol
        ):

            detailed_dashboard_symbol = (
                futures_symbol
            )

            detailed_trade_symbol = (
                futures_symbol
            )

        else:

            detailed_dashboard_symbol = symbol
            detailed_trade_symbol = None

        st.session_state[
            "dashboard_symbol"
        ] = detailed_dashboard_symbol

        st.session_state[
            "selected_underlying_symbol"
        ] = symbol

        dashboard_page(

            trader=trader,

            current_price=underlying_price,

            symbol=detailed_dashboard_symbol,

            market_type=market_type,

            trade_symbol=detailed_trade_symbol,

            default_quantity=int(
                quantity
            ),
        )

    except Exception as e:

        logging.exception(
            f"Dashboard Page Error: {e}"
        )

        st.error(
            f"❌ Dashboard Page Error: {e}"
        )

# ============================================================
# DELTA ALL COINS PAGE
# ============================================================
elif page == "📊 Delta All Coins":
    render_delta_all_coins()

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
            default_quantity=int(quantity),
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
