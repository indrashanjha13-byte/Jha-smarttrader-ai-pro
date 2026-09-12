# =========================================================
# JHA SMARTTRADER AI PRO
# pages/dashboard_page.py
# =========================================================

import os
from datetime import datetime, time
from zoneinfo import ZoneInfo

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

from ai_decision import ai_decision
from broker.broker_manager import BrokerManager
from signals import get_signals, download_data
import config

# =========================================================
# KOTAK / OPTION CHAIN
# =========================================================

try:
    from option_chain import get_atm_option_prices
except Exception:
    get_atm_option_prices = None


# =========================================================
# DELTA EXCHANGE
# =========================================================

DELTA_SYMBOLS = {
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


# =========================================================
# OPTION INDEX MAP
# =========================================================

OPTION_INDEX_MAP = {
    "^NSEI": "NIFTY",
    "^NSEBANK": "BANKNIFTY",
    "^CNXFINANCE": "FINNIFTY",
    "^NSEMDCP50": "MIDCPNIFTY",
    "^BSESN": "SENSEX",

    "NIFTY": "NIFTY",
    "BANKNIFTY": "BANKNIFTY",
    "FINNIFTY": "FINNIFTY",
    "MIDCPNIFTY": "MIDCPNIFTY",
    "SENSEX": "SENSEX",
}


# =========================================================
# SAFE HELPERS
# =========================================================

def safe_float(value, default=0.0):
    try:
        if value is None:
            return default

        if isinstance(value, (list, tuple)):
            if not value:
                return default
            value = value[0]

        if pd.isna(value):
            return default

        return float(value)

    except Exception:
        return default


def normalize_signal(value):
    try:
        value = str(value or "HOLD").strip().upper()

        if value in {"BUY", "LONG"}:
            return "BUY"

        if value in {"SELL", "SHORT"}:
            return "SELL"

        return "HOLD"

    except Exception:
        return "HOLD"


def get_position_side(position):

    if not isinstance(position, dict):
        return "LONG"

    raw = str(
        position.get(
            "position_side",
            position.get(
                "side",
                position.get(
                    "action",
                    "BUY",
                ),
            ),
        )
    ).strip().upper()

    if raw in {"SHORT", "SELL"}:
        return "SHORT"

    return "LONG"


def format_price(value, delta=False):

    number = safe_float(value)

    if delta:
        return f"${number:,.8f}"

    return f"₹{number:,.2f}"


def format_pnl(value, delta=False):

    number = safe_float(value)

    if delta:
        return f"${number:,.8f}"

    return f"₹{number:,.2f}"


# =========================================================
# DELTA SYMBOL CHECK
# =========================================================

def is_delta_symbol(symbol):

    try:
        s = str(symbol or "").strip().upper()

        if not s:
            return False

        if s in DELTA_SYMBOLS:
            return True

        return s.endswith("USD") or s.endswith("USDT")

    except Exception:
        return False


# =========================================================
# OPTION INDEX RESOLVER
# =========================================================

def get_option_index_name(symbol):

    key = str(symbol or "").strip().upper()

    return OPTION_INDEX_MAP.get(key)


# =========================================================
# GET KOTAK ATM OPTION DATA
# =========================================================

@st.cache_data(
    ttl=10,
    show_spinner=False,
)
def get_dashboard_option_data(
    index_name,
    underlying_price,
):

    if not index_name:
        return None

    underlying_price = safe_float(
        underlying_price
    )

    if underlying_price <= 0:
        return None

    if get_atm_option_prices is None:
        return None

    try:

        result = get_atm_option_prices(
            index_name=index_name,
            underlying_price=underlying_price,
        )

        if not isinstance(result, dict):
            return None

        return result

    except Exception as e:

        return {
            "success": False,
            "error": str(e),
        }


# =========================================================
# POSITION HELPERS
# =========================================================

def get_active_positions(trader):

    try:

        positions = trader.get_active_positions()

        if isinstance(
            positions,
            dict,
        ) and positions:

            return positions

    except Exception:
        pass

    positions = getattr(
        trader,
        "positions",
        {},
    )

    if isinstance(
        positions,
        dict,
    ) and positions:

        return positions

    position = getattr(
        trader,
        "position",
        None,
    )

    if isinstance(
        position,
        dict,
    ) and position:

        position_symbol = str(
            position.get(
                "symbol",
                "",
            )
        ).strip().upper()

        option_mode = str(
            position.get(
                "option_mode",
                "N/A",
            )
        ).strip().upper()

        if not position_symbol:
            position_symbol = "UNKNOWN"

        key = (
            f"{position_symbol}_"
            f"{option_mode}"
        )

        return {
            key: position
        }

    return {}


def get_position_ltp(
    position_symbol,
    active_symbol,
    display_price,
    entry,
):

    position_symbol = str(
        position_symbol or ""
    ).strip().upper()

    active_symbol = str(
        active_symbol or ""
    ).strip().upper()

    entry = safe_float(entry)

    if position_symbol:

        try:

            signal = get_signals(
                position_symbol
            )

            if isinstance(
                signal,
                dict,
            ):

                latest = safe_float(
                    signal.get(
                        "Price",
                        0,
                    )
                )

                if latest > 0:
                    return latest

        except Exception:
            pass

    if position_symbol == active_symbol:

        latest = safe_float(
            display_price
        )

        if latest > 0:
            return latest

    return entry


def calculate_position_pnl(
    position,
    ltp,
):

    if not isinstance(
        position,
        dict,
    ):
        return 0.0

    entry = safe_float(
        position.get(
            "entry",
            0,
        )
    )

    qty = safe_float(
        position.get(
            "qty",
            position.get(
                "quantity",
                0,
            ),
        )
    )

    side = get_position_side(
        position
    )

    if side == "SHORT":

        return (
            entry - ltp
        ) * qty

    return (
        ltp - entry
    ) * qty


# =========================================================
# MARKET STATUS
# =========================================================

def get_market_status(symbol):

    # -----------------------------------------------------
    # DELTA IS 24/7
    # -----------------------------------------------------

    if is_delta_symbol(symbol):

        return {
            "market": "DELTA",
            "status": "OPEN_24X7",
            "open": True,
            "market_open": True,
            "entry_allowed": True,
            "message": (
                "🟢 DELTA EXCHANGE • "
                "MARKET OPEN 24/7"
            ),
        }

    ist = ZoneInfo("Asia/Kolkata")
    now = datetime.now(ist)

    weekday = now.weekday()
    current_time = now.time()

    # -----------------------------------------------------
    # SATURDAY / SUNDAY
    # -----------------------------------------------------

    if weekday >= 5:

        return {
            "market": "INDIA",
            "status": "CLOSED",
            "open": False,
            "market_open": False,
            "entry_allowed": False,
            "message": (
                "🔴 INDIAN MARKET • CLOSED • "
                "WEEKEND"
            ),
        }

    # -----------------------------------------------------
    # MARKET TIMES
    # -----------------------------------------------------

    pre_market_start = time(9, 0)
    market_open = time(9, 15)
    market_close = time(15, 30)

    # -----------------------------------------------------
    # PRE MARKET
    # -----------------------------------------------------

    if (
        pre_market_start
        <= current_time
        < market_open
    ):

        return {
            "market": "INDIA",
            "status": "PRE-MARKET",
            "open": False,
            "market_open": False,
            "entry_allowed": False,
            "message": (
                "🟡 INDIAN MARKET • "
                "PRE-MARKET • Opens 09:15 IST"
            ),
        }

    # -----------------------------------------------------
    # OPEN
    # -----------------------------------------------------

    if (
        market_open
        <= current_time
        <= market_close
    ):

        return {
            "market": "INDIA",
            "status": "OPEN",
            "open": True,
            "market_open": True,
            "entry_allowed": True,
            "message": (
                "🟢 INDIAN MARKET • "
                "OPEN • 09:15–15:30 IST"
            ),
        }

    # -----------------------------------------------------
    # CLOSED
    # -----------------------------------------------------

    return {
        "market": "INDIA",
        "status": "CLOSED",
        "open": False,
        "market_open": False,
        "entry_allowed": False,
        "message": (
            "🔴 INDIAN MARKET • "
            "CLOSED • Session 09:15–15:30 IST"
        ),
    }


# =========================================================
# STATUS RIBBON
# =========================================================

def status_ribbon():

    c1, c2, c3, c4, c5 = st.columns(5)

    try:

        broker = BrokerManager(
            config.BROKER
        )

    except Exception:

        broker = None

    paper_mode = bool(
        getattr(
            config,
            "PAPER_TRADE",
            True,
        )
    )

    if paper_mode:

        broker_status = "🟡 PAPER MODE"

    else:

        connected = False

        try:

            connected = bool(
                getattr(
                    broker.broker,
                    "connected",
                    False,
                )
            )

        except Exception:

            connected = False

        broker_status = (
            "🟢 LIVE CONNECTED"
            if connected
            else "🔴 NOT CONNECTED"
        )

    c1.info(
        f"🏦 {config.BROKER}"
    )

    c1.caption(
        broker_status
    )

    c2.success(
        "🟢 Market"
    )

    c3.info(
        "🤖 AI"
    )

    c4.warning(
        "⚙ Auto"
    )

    c5.success(
        "📱 Telegram"
    )


# =========================================================
# ACCOUNT SUMMARY
# =========================================================

def account_summary(
    trader,
    current_price,
    symbol,
):

    balance = safe_float(
        getattr(
            trader,
            "balance",
            0.0,
        )
    )

    active_positions = get_active_positions(
        trader
    )

    position = None

    active_symbol = str(
        symbol or ""
    ).strip().upper()

    for candidate in active_positions.values():

        if not isinstance(
            candidate,
            dict,
        ):
            continue

        candidate_symbol = str(
            candidate.get(
                "symbol",
                "",
            )
        ).strip().upper()

        if candidate_symbol == active_symbol:

            position = candidate
            break

    if position is None:

        for candidate in active_positions.values():

            if isinstance(
                candidate,
                dict,
            ):

                position = candidate
                break

    if position:

        position_symbol = str(
            position.get(
                "symbol",
                symbol,
            )
        ).strip().upper()

        position_side = get_position_side(
            position
        )

        entry = safe_float(
            position.get(
                "entry",
                0,
            )
        )

        ltp = get_position_ltp(
            position_symbol=position_symbol,
            active_symbol=active_symbol,
            display_price=current_price,
            entry=entry,
        )

        pnl = calculate_position_pnl(
            position,
            ltp,
        )

        delta = is_delta_symbol(
            position_symbol
        )

        position_text = (
            f"{position_symbol} • "
            f"{position_side}"
        )

        pnl_text = format_pnl(
            pnl,
            delta,
        )

    else:

        position_text = "No Position"
        pnl_text = "₹0.00"

    c1, c2, c3, c4 = st.columns(4)

    if is_delta_symbol(symbol):

        balance_text = f"${balance:,.8f}"
        cash_text = f"${balance:,.8f}"

        if not position:
            pnl_text = "$0.00000000"

    else:

        balance_text = f"₹{balance:,.2f}"
        cash_text = f"₹{balance:,.2f}"

        if not position:
            pnl_text = "₹0.00"

    c1.metric(
        "💰 Balance",
        balance_text,
    )

    c2.metric(
        "📦 Position",
        position_text,
    )

    c3.metric(
        "📈 Live P&L",
        pnl_text,
    )

    c4.metric(
        "💵 Cash",
        cash_text,
    )


# =========================================================
# MARKET STATUS DISPLAY
# =========================================================

def market_status(symbol):

    info = get_market_status(symbol)

    st.subheader(
        "🟢 Market Status"
    )

    c1, c2, c3 = st.columns(3)

    if info["market"] == "DELTA":

        c1.metric(
            "Market",
            "🟢 OPEN 24/7",
        )

    elif info["status"] == "PRE-MARKET":

        c1.metric(
            "Market",
            "🟡 PRE-MARKET",
        )

    elif info.get(
        "market_open",
        info.get("open", False),
    ):

        c1.metric(
            "Market",
            "🟢 OPEN",
        )

    else:

        c1.metric(
            "Market",
            "🔴 CLOSED",
        )

    ist = ZoneInfo("Asia/Kolkata")
    now_ist = datetime.now(ist)

    c2.metric(
        "Time",
        now_ist.strftime(
            "%H:%M:%S"
        ) + " IST",
    )

    c3.metric(
        "Date",
        now_ist.strftime(
            "%d-%b-%Y"
        ),
    )

    if info["market"] == "DELTA":

        st.success(
            "🟢 DELTA EXCHANGE • "
            "MARKET OPEN 24/7"
        )

        st.caption(
            f"Trading Symbol: {symbol} | "
            "Crypto Futures • "
            "No daily market close"
        )

    elif info["status"] == "PRE-MARKET":

        st.warning(
            "🟡 INDIAN MARKET • PRE-MARKET"
        )

        st.caption(
            f"Trading Symbol: {symbol} | "
            "Pre-Market: 09:00–09:15 IST | "
            "Normal Market: 09:15–15:30 IST"
        )

    elif info.get(
        "market_open",
        info.get("open", False),
    ):

        st.success(
            "🟢 INDIAN MARKET • OPEN"
        )

        st.caption(
            f"Trading Symbol: {symbol} | "
            "Indian session: 09:15–15:30 IST"
        )

    else:

        if (
            datetime.now(
                ZoneInfo("Asia/Kolkata")
            ).weekday()
            >= 5
        ):

            st.error(
                "🔴 INDIAN MARKET • "
                "CLOSED • WEEKEND"
            )

            st.caption(
                f"Trading Symbol: {symbol} | "
                "Saturday/Sunday • "
                "Indian market closed"
            )

        else:

            st.error(
                "🔴 INDIAN MARKET • CLOSED"
            )

            st.caption(
                f"Trading Symbol: {symbol} | "
                "Indian session: 09:15–15:30 IST"
            )


# =========================================================
# SIGNAL / INDICATORS
# =========================================================

def signal_indicators(symbol):

    st.subheader(
        "🤖 AI Signal & Technical Indicators"
    )

    try:

        signal = get_signals(
            symbol
        )

        if not isinstance(
            signal,
            dict,
        ):

            st.error(
                "Signal engine returned invalid data."
            )

            return None

        if "error" in signal:

            st.error(
                f"Signal Error: "
                f"{signal.get('error')}"
            )

            return signal

        price = safe_float(
            signal.get(
                "Price",
                0,
            )
        )

        ema9 = safe_float(
            signal.get(
                "EMA9",
                0,
            )
        )

        ema21 = safe_float(
            signal.get(
                "EMA21",
                0,
            )
        )

        rsi = safe_float(
            signal.get(
                "RSI",
                0,
            )
        )

        macd = safe_float(
            signal.get(
                "MACD",
                0,
            )
        )

        macd_signal = safe_float(
            signal.get(
                "MACD_SIGNAL",
                0,
            )
        )

        macd_hist = safe_float(
            signal.get(
                "MACD_HIST",
                macd - macd_signal,
            )
        )

        supertrend = safe_float(
            signal.get(
                "SUPERTREND_VALUE",
                signal.get(
                    "SUPERTREND",
                    0,
                ),
            )
        )

        volume = safe_float(
            signal.get(
                "Volume",
                0,
            )
        )

        avg_volume = safe_float(
            signal.get(
                "AVG_VOLUME",
                0,
            )
        )

        decision = normalize_signal(
            signal.get(
                "SIGNAL",
                signal.get(
                    "Signal",
                    signal.get(
                        "signal",
                        "HOLD",
                    ),
                ),
            )
        )

        strength = safe_float(
            signal.get(
                "Signal_Strength",
                signal.get(
                    "Strength",
                    signal.get(
                        "Confidence",
                        signal.get(
                            "confidence",
                            0,
                        ),
                    ),
                ),
            )
        )

        strength = max(
            0.0,
            min(
                100.0,
                strength,
            ),
        )

        signal_type = str(
            signal.get(
                "Signal_Type",
                signal.get(
                    "signal_type",
                    signal.get(
                        "Type",
                        "N/A",
                    ),
                ),
            )
        )

        delta = is_delta_symbol(
            symbol
        )

        market_text = (
            "🟢 DELTA FUTURES • 24/7"
            if delta
            else "🇮🇳 INDIAN MARKET"
        )

        st.caption(
            f"{market_text} • {symbol}"
        )

        c1, c2, c3, c4 = st.columns(4)

        c1.metric(
            "💵 Price",
            format_price(
                price,
                delta,
            ),
        )

        c2.metric(
            "📊 Signal",
            decision,
        )

        c3.metric(
            "🎯 Strength",
            f"{strength:.1f}%",
        )

        c4.metric(
            "📌 Type",
            signal_type,
        )

        if decision == "BUY":

            if delta:

                st.success(
                    f"🟢 DELTA FUTURES "
                    f"BUY / LONG • "
                    f"{symbol} • "
                    f"{strength:.1f}%"
                )

            else:

                st.success(
                    f"🟢 BUY SIGNAL • "
                    f"{symbol} • "
                    f"{strength:.1f}%"
                )

        elif decision == "SELL":

            if delta:

                st.error(
                    f"🔴 DELTA FUTURES "
                    f"SELL / SHORT • "
                    f"{symbol} • "
                    f"{strength:.1f}%"
                )

            else:

                st.error(
                    f"🔴 SELL SIGNAL • "
                    f"{symbol} • "
                    f"{strength:.1f}%"
                )

        else:

            st.warning(
                f"🟡 HOLD / WAIT • "
                f"{symbol} • "
                f"{strength:.1f}%"
            )

        st.divider()

        c1, c2, c3, c4, c5 = st.columns(5)

        c1.metric(
            "EMA 9",
            format_price(
                ema9,
                delta,
            ),
        )

        c2.metric(
            "EMA 21",
            format_price(
                ema21,
                delta,
            ),
        )

        c3.metric(
            "RSI",
            f"{rsi:.2f}",
        )

        c4.metric(
            "MACD",
            (
                f"${macd:,.8f}"
                if delta
                else f"₹{macd:,.2f}"
            ),
        )

        c5.metric(
            "SuperTrend",
            format_price(
                supertrend,
                delta,
            ),
        )

        with st.expander(
            "🔎 Advanced Indicator Details"
        ):

            d1, d2, d3, d4 = st.columns(4)

            d1.metric(
                "MACD Signal",
                (
                    f"${macd_signal:,.8f}"
                    if delta
                    else f"₹{macd_signal:,.2f}"
                ),
            )

            d2.metric(
                "MACD Histogram",
                (
                    f"${macd_hist:,.8f}"
                    if delta
                    else f"₹{macd_hist:,.2f}"
                ),
            )

            d3.metric(
                "Volume",
                f"{volume:,.2f}",
            )

            d4.metric(
                "Avg Volume",
                f"{avg_volume:,.2f}",
            )

        # -------------------------------------------------
        # AI DECISION
        # -------------------------------------------------

        try:

            ai = ai_decision(
                rsi=rsi,
                macd=macd,
                macd_signal=macd_signal,
                ema9=ema9,
                ema21=ema21,
                supertrend=supertrend,
                volume=volume,
                avg_volume=avg_volume,
            )

            if isinstance(
                ai,
                dict,
            ):

                ai_value = normalize_signal(
                    ai.get(
                        "decision",
                        "HOLD",
                    )
                )

                ai_confidence = safe_float(
                    ai.get(
                        "confidence",
                        0,
                    )
                )

                ai_confidence = max(
                    0.0,
                    min(
                        100.0,
                        ai_confidence,
                    ),
                )

                ai_reason = str(
                    ai.get(
                        "reason",
                        ai.get(
                            "message",
                            "",
                        ),
                    )
                )

                st.info(
                    f"🧠 AI Decision: "
                    f"**{ai_value}** "
                    f"| Confidence: "
                    f"**{ai_confidence:.1f}%**"
                )

                st.caption(
                    f"Technical Signal: "
                    f"{decision} • "
                    f"Strength: "
                    f"{strength:.1f}%"
                )

                if ai_reason:

                    st.caption(
                        f"Reason: {ai_reason}"
                    )

        except Exception as e:

            st.caption(
                "AI decision detail unavailable: "
                f"{e}"
            )

        if delta:

            if decision == "BUY":

                st.success(
                    "📈 Delta Execution Direction: "
                    "**BUY / LONG**"
                )

            elif decision == "SELL":

                st.error(
                    "📉 Delta Execution Direction: "
                    "**SELL / SHORT**"
                )

            else:

                st.warning(
                    "⏸ Delta Execution: WAIT"
                )

        return signal

    except Exception as e:

        st.error(
            f"Indicator Error: {e}"
        )

        return None


# =========================================================
# PERFORMANCE REPORT
# =========================================================

def performance_report():

    st.subheader(
        "📊 Performance Report"
    )

    history_file = "trade_history.csv"

    if not os.path.exists(
        history_file
    ):

        st.info(
            "No Trade History Available"
        )

        return

    try:

        trades = pd.read_csv(
            history_file
        )

        if (
            "PNL" in trades.columns
            and "PnL" not in trades.columns
        ):

            trades = trades.rename(
                columns={
                    "PNL": "PnL"
                }
            )

        if "PnL" not in trades.columns:

            st.warning(
                "No PnL data available yet."
            )

            return

        trades = trades.loc[
            :,
            ~trades.columns.duplicated(
                keep="first"
            ),
        ]

        trades["PnL"] = pd.to_numeric(
            trades["PnL"],
            errors="coerce",
        ).fillna(0)

        total = len(
            trades
        )

        wins = len(
            trades[
                trades["PnL"] > 0
            ]
        )

        losses = len(
            trades[
                trades["PnL"] < 0
            ]
        )

        net = safe_float(
            trades["PnL"].sum()
        )

        win_rate = (
            (wins / total) * 100
            if total > 0
            else 0
        )

        gross_profit = safe_float(
            trades.loc[
                trades["PnL"] > 0,
                "PnL",
            ].sum()
        )

        gross_loss = abs(
            safe_float(
                trades.loc[
                    trades["PnL"] < 0,
                    "PnL",
                ].sum()
            )
        )

        profit_factor = (
            gross_profit / gross_loss
            if gross_loss > 0
            else 0
        )

        c1, c2, c3, c4 = st.columns(4)

        c1.metric(
            "Total Trades",
            total,
        )

        c2.metric(
            "Win Rate",
            f"{win_rate:.2f}%",
        )

        c3.metric(
            "Net P&L",
            f"₹{net:,.2f}",
        )

        c4.metric(
            "Profit Factor",
            f"{profit_factor:.2f}",
        )

        if total > 0:

            equity = (
                trades["PnL"]
                .cumsum()
            )

            fig = px.line(
                y=equity,
                title="Equity Curve",
            )

            fig.update_layout(
                height=350,
                margin=dict(
                    l=10,
                    r=10,
                    t=45,
                    b=10,
                ),
            )

            st.plotly_chart(
                fig,
                use_container_width=True,
            )

    except Exception as e:

        st.error(
            f"Performance Report Error: {e}"
        )


# =========================================================
# CHART PATTERN DETECTION
# =========================================================

def detect_chart_patterns(data):

    patterns = []

    if data is None or data.empty:
        return patterns

    if len(data) < 3:
        return patterns

    try:

        for i in range(1, len(data)):

            prev_open = safe_float(
                data["Open"].iloc[i - 1]
            )

            prev_close = safe_float(
                data["Close"].iloc[i - 1]
            )

            curr_open = safe_float(
                data["Open"].iloc[i]
            )

            curr_close = safe_float(
                data["Close"].iloc[i]
            )

            curr_high = safe_float(
                data["High"].iloc[i]
            )

            curr_low = safe_float(
                data["Low"].iloc[i]
            )

            prev_body = abs(
                prev_close - prev_open
            )

            curr_body = abs(
                curr_close - curr_open
            )

            curr_range = (
                curr_high - curr_low
            )

            if curr_range <= 0:
                continue

            # Bullish Engulfing

            if (
                prev_close < prev_open
                and curr_close > curr_open
                and curr_open <= prev_close
                and curr_close >= prev_open
            ):

                patterns.append(
                    {
                        "index": i,
                        "name": "Bullish Engulfing",
                        "type": "bullish",
                    }
                )

            # Bearish Engulfing

            elif (
                prev_close > prev_open
                and curr_close < curr_open
                and curr_open >= prev_close
                and curr_close <= prev_open
            ):

                patterns.append(
                    {
                        "index": i,
                        "name": "Bearish Engulfing",
                        "type": "bearish",
                    }
                )

            lower_wick = (
                min(
                    curr_open,
                    curr_close,
                )
                - curr_low
            )

            upper_wick = (
                curr_high
                - max(
                    curr_open,
                    curr_close,
                )
            )

            # Hammer

            if (
                lower_wick >= curr_body * 2
                and upper_wick <= max(
                    curr_body,
                    curr_range * 0.15,
                )
            ):

                patterns.append(
                    {
                        "index": i,
                        "name": "Hammer",
                        "type": "bullish",
                    }
                )

            # Shooting Star

            if (
                upper_wick >= curr_body * 2
                and lower_wick <= max(
                    curr_body,
                    curr_range * 0.15,
                )
            ):

                patterns.append(
                    {
                        "index": i,
                        "name": "Shooting Star",
                        "type": "bearish",
                    }
                )

        return patterns

    except Exception:

        return patterns


# =========================================================
# DELTA MARKET CHART
# =========================================================

def delta_chart(symbol):

    st.subheader(
        "📈 Live Market Chart"
    )

    st.info(
        f"🟢 Delta Futures: {symbol}"
    )

    st.caption(
        "Delta Exchange crypto futures "
        "are available 24/7."
    )

    try:

        data = download_data(
            symbol,
            period="2d",
            interval="5m",
        )

        if data is None or data.empty:

            st.warning(
                "No Delta candle data available."
            )

            return

        data = data.copy()

        if isinstance(
            data.columns,
            pd.MultiIndex,
        ):

            data.columns = [
                str(
                    col[0]
                    if isinstance(
                        col,
                        tuple,
                    )
                    else col
                )
                for col in data.columns
            ]

        candidates = [
            "Time",
            "Datetime",
            "datetime",
            "time",
            "Timestamp",
            "timestamp",
            "Date",
            "date",
        ]

        time_col = None

        for col in candidates:

            if col in data.columns:

                time_col = col
                break

        if time_col is None:

            data = data.reset_index()

            for col in candidates:

                if col in data.columns:

                    time_col = col
                    break

        if time_col is None:

            for col in data.columns:

                parsed = pd.to_datetime(
                    data[col],
                    errors="coerce",
                )

                if parsed.notna().sum() > 0:

                    time_col = col
                    break

        if time_col is None:

            st.error(
                "Delta Chart Error: "
                "Candle time column not found."
            )

            return

        data["Time"] = pd.to_datetime(
            data[time_col],
            errors="coerce",
        )

        rename_map = {}

        for col in data.columns:

            key = str(
                col
            ).strip().lower()

            if key == "open":
                rename_map[col] = "Open"

            elif key == "high":
                rename_map[col] = "High"

            elif key == "low":
                rename_map[col] = "Low"

            elif key == "close":
                rename_map[col] = "Close"

        data = data.rename(
            columns=rename_map
        )

        required = [
            "Time",
            "Open",
            "High",
            "Low",
            "Close",
        ]

        missing = [
            col
            for col in required
            if col not in data.columns
        ]

        if missing:

            st.error(
                "Delta Chart Error: "
                "Missing columns: "
                + ", ".join(missing)
            )

            return

        for col in [
            "Open",
            "High",
            "Low",
            "Close",
        ]:

            data[col] = pd.to_numeric(
                data[col],
                errors="coerce",
            )

        data = data.dropna(
            subset=required
        )

        if data.empty:

            st.warning(
                "Delta candle data is empty."
            )

            return

        data = data.sort_values(
            "Time"
        )

        data["EMA9"] = (
            data["Close"]
            .ewm(
                span=9,
                adjust=False,
            )
            .mean()
        )

        data["EMA21"] = (
            data["Close"]
            .ewm(
                span=21,
                adjust=False,
            )
            .mean()
        )

        patterns = detect_chart_patterns(
            data
        )

        fig = go.Figure()

        fig.add_trace(
            go.Candlestick(
                x=data["Time"],
                open=data["Open"],
                high=data["High"],
                low=data["Low"],
                close=data["Close"],
                name="Price",
            )
        )

        fig.add_trace(
            go.Scatter(
                x=data["Time"],
                y=data["EMA9"],
                name="EMA 9",
                mode="lines",
            )
        )

        fig.add_trace(
            go.Scatter(
                x=data["Time"],
                y=data["EMA21"],
                name="EMA 21",
                mode="lines",
            )
        )

        bullish_x = []
        bullish_y = []
        bullish_text = []

        bearish_x = []
        bearish_y = []
        bearish_text = []

        for pattern in patterns:

            i = pattern["index"]

            if pattern["type"] == "bullish":

                bullish_x.append(
                    data["Time"].iloc[i]
                )

                bullish_y.append(
                    data["Low"].iloc[i]
                )

                bullish_text.append(
                    pattern["name"]
                )

            else:

                bearish_x.append(
                    data["Time"].iloc[i]
                )

                bearish_y.append(
                    data["High"].iloc[i]
                )

                bearish_text.append(
                    pattern["name"]
                )

        if bullish_x:

            fig.add_trace(
                go.Scatter(
                    x=bullish_x,
                    y=bullish_y,
                    mode="markers+text",
                    name="Bullish Pattern",
                    text=bullish_text,
                    textposition="bottom center",
                    marker=dict(
                        symbol="triangle-up",
                        size=10,
                    ),
                )
            )

        if bearish_x:

            fig.add_trace(
                go.Scatter(
                    x=bearish_x,
                    y=bearish_y,
                    mode="markers+text",
                    name="Bearish Pattern",
                    text=bearish_text,
                    textposition="top center",
                    marker=dict(
                        symbol="triangle-down",
                        size=10,
                    ),
                )
            )

        fig.update_layout(
            height=550,
            xaxis_rangeslider_visible=False,
            margin=dict(
                l=10,
                r=10,
                t=40,
                b=10,
            ),
            hovermode="x unified",
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
        )

    except Exception as e:

        st.error(
            f"Delta Chart Error: {e}"
        )


# =========================================================
# INDIAN MARKET CHART
# =========================================================

def indian_chart(symbol):

    try:

        data = yf.download(
            symbol,
            period="5d",
            interval="15m",
            auto_adjust=False,
            progress=False,
        )

        if data is None or data.empty:

            st.warning(
                "No Indian market chart data available."
            )

            return

        data = data.copy()

        if isinstance(
            data.columns,
            pd.MultiIndex,
        ):

            data.columns = (
                data.columns
                .get_level_values(0)
            )

        for col in [
            "Open",
            "High",
            "Low",
            "Close",
        ]:

            if col not in data.columns:

                st.warning(
                    f"Missing chart column: {col}"
                )

                return

            data[col] = pd.to_numeric(
                data[col],
                errors="coerce",
            )

        data = data.dropna(
            subset=[
                "Open",
                "High",
                "Low",
                "Close",
            ]
        )

        if data.empty:

            st.warning(
                "Indian chart data is empty."
            )

            return

        close = data["Close"]

        ema9 = close.ewm(
            span=9,
            adjust=False,
        ).mean()

        ema21 = close.ewm(
            span=21,
            adjust=False,
        ).mean()

        patterns = detect_chart_patterns(
            data
        )

        fig = go.Figure()

        fig.add_trace(
            go.Candlestick(
                x=data.index,
                open=data["Open"],
                high=data["High"],
                low=data["Low"],
                close=data["Close"],
                name="Price",
            )
        )

        fig.add_trace(
            go.Scatter(
                x=data.index,
                y=ema9,
                name="EMA 9",
                mode="lines",
            )
        )

        fig.add_trace(
            go.Scatter(
                x=data.index,
                y=ema21,
                name="EMA 21",
                mode="lines",
            )
        )

        bullish_x = []
        bullish_y = []
        bullish_text = []

        bearish_x = []
        bearish_y = []
        bearish_text = []

        for pattern in patterns:

            i = pattern["index"]

            if pattern["type"] == "bullish":

                bullish_x.append(
                    data.index[i]
                )

                bullish_y.append(
                    safe_float(
                        data["Low"].iloc[i]
                    )
                )

                bullish_text.append(
                    pattern["name"]
                )

            else:

                bearish_x.append(
                    data.index[i]
                )

                bearish_y.append(
                    safe_float(
                        data["High"].iloc[i]
                    )
                )

                bearish_text.append(
                    pattern["name"]
                )

        if bullish_x:

            fig.add_trace(
                go.Scatter(
                    x=bullish_x,
                    y=bullish_y,
                    mode="markers+text",
                    name="Bullish Pattern",
                    text=bullish_text,
                    textposition="bottom center",
                    marker=dict(
                        symbol="triangle-up",
                        size=10,
                    ),
                )
            )

        if bearish_x:

            fig.add_trace(
                go.Scatter(
                    x=bearish_x,
                    y=bearish_y,
                    mode="markers+text",
                    name="Bearish Pattern",
                    text=bearish_text,
                    textposition="top center",
                    marker=dict(
                        symbol="triangle-down",
                        size=10,
                    ),
                )
            )

        fig.update_layout(
            title=f"{symbol} • Candlestick Chart",
            height=550,
            xaxis_rangeslider_visible=False,
            hovermode="x unified",
            margin=dict(
                l=10,
                r=10,
                t=45,
                b=10,
            ),
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
        )

        if patterns:

            latest_patterns = patterns[-5:]

            pattern_text = " • ".join(
                p["name"]
                for p in latest_patterns
            )

            st.info(
                f"🔎 Chart Patterns: "
                f"{pattern_text}"
            )

        else:

            st.caption(
                "🔎 Chart Patterns: "
                "No confirmed candle pattern detected."
            )

    except Exception as e:

        st.error(
            f"Indian Chart Error: {e}"
        )


# =========================================================
# MULTI INDEX AI SCANNER
# =========================================================

def multi_index_scanner():

    st.subheader(
        "🤖 Multi-Index AI Market Scanner"
    )

    c1, c2 = st.columns(2)

    signal_filter = c1.selectbox(
        "Signal",
        [
            "ALL",
            "BUY",
            "SELL",
            "HOLD",
        ],
        key="multi_index_signal",
    )

    min_confidence = c2.slider(
        "Min Confidence",
        50,
        100,
        70,
        key="multi_index_confidence",
    )

    trend_filter = st.selectbox(
        "Trend",
        [
            "ALL",
            "Bullish",
            "Bearish",
            "Sideways",
        ],
        key="multi_index_trend",
    )

    watchlist = {
        "NIFTY": "^NSEI",
        "BANKNIFTY": "^NSEBANK",
        "FINNIFTY": "^CNXFINANCE",
        "MIDCPNIFTY": "^NSEMDCP50",
        "SENSEX": "^BSESN",
    }

    if not st.button(
        "▶ Run Multi-Index Scanner",
        key="run_multi_index_scanner",
    ):

        return

    scanner_rows = []

    with st.spinner(
        "Scanning indexes..."
    ):

        for index_name, ticker in watchlist.items():

            try:

                data = yf.download(
                    ticker,
                    period="2d",
                    interval="5m",
                    progress=False,
                )

                if data is None or data.empty:
                    continue

                if isinstance(
                    data.columns,
                    pd.MultiIndex,
                ):

                    data.columns = (
                        data.columns
                        .get_level_values(0)
                    )

                close_value = (
                    data["Close"].iloc[-1]
                )

                if hasattr(
                    close_value,
                    "iloc",
                ):

                    close_value = (
                        close_value.iloc[0]
                    )

                current_price = safe_float(
                    close_value
                )

                signal = get_signals(
                    ticker
                )

                if (
                    not isinstance(
                        signal,
                        dict,
                    )
                    or "error" in signal
                ):

                    continue

                ai = ai_decision(
                    rsi=safe_float(
                        signal.get(
                            "RSI",
                            0,
                        )
                    ),
                    macd=safe_float(
                        signal.get(
                            "MACD",
                            0,
                        )
                    ),
                    macd_signal=safe_float(
                        signal.get(
                            "MACD_SIGNAL",
                            0,
                        )
                    ),
                    ema9=safe_float(
                        signal.get(
                            "EMA9",
                            0,
                        )
                    ),
                    ema21=safe_float(
                        signal.get(
                            "EMA21",
                            0,
                        )
                    ),
                    supertrend=safe_float(
                        signal.get(
                            "SUPERTREND_VALUE",
                            signal.get(
                                "SUPERTREND",
                                0,
                            ),
                        )
                    ),
                    volume=safe_float(
                        signal.get(
                            "Volume",
                            0,
                        )
                    ),
                    avg_volume=safe_float(
                        signal.get(
                            "AVG_VOLUME",
                            0,
                        )
                    ),
                )

                if not isinstance(
                    ai,
                    dict,
                ):
                    continue

                decision = normalize_signal(
                    ai.get(
                        "decision",
                        "HOLD",
                    )
                )

                confidence = safe_float(
                    ai.get(
                        "confidence",
                        0,
                    )
                )

                ema9_value = safe_float(
                    signal.get(
                        "EMA9",
                        0,
                    )
                )

                ema21_value = safe_float(
                    signal.get(
                        "EMA21",
                        0,
                    )
                )

                if ema9_value > ema21_value:
                    trend = "Bullish"

                elif ema9_value < ema21_value:
                    trend = "Bearish"

                else:
                    trend = "Sideways"

                if confidence < min_confidence:
                    continue

                if (
                    signal_filter != "ALL"
                    and decision != signal_filter
                ):
                    continue

                if (
                    trend_filter != "ALL"
                    and trend != trend_filter
                ):
                    continue

                if decision == "BUY":

                    option_signal = "🟢 BUY CE"

                elif decision == "SELL":

                    option_signal = "🔴 BUY PE"

                else:

                    option_signal = "🟡 WAIT"

                scanner_rows.append(
                    {
                        "Index": index_name,
                        "Price": round(
                            current_price,
                            2,
                        ),
                        "Signal": option_signal,
                        "Confidence": round(
                            confidence,
                            1,
                        ),
                        "Trend": trend,
                        "RSI": round(
                            safe_float(
                                signal.get(
                                    "RSI",
                                    0,
                                )
                            ),
                            2,
                        ),
                        "MACD": round(
                            safe_float(
                                signal.get(
                                    "MACD",
                                    0,
                                )
                            ),
                            4,
                        ),
                    }
                )

            except Exception as e:

                st.warning(
                    f"{index_name}: {e}"
                )

    if not scanner_rows:

        st.info(
            "No qualifying index signal found."
        )

        return

    df = pd.DataFrame(
        scanner_rows
    )

    st.table(df)

    best = max(
        scanner_rows,
        key=lambda x: x["Confidence"],
    )

    st.success(
        f"⭐ Best Signal: "
        f"{best['Index']} → "
        f"{best['Signal']} "
        f"({best['Confidence']}%)"
    )


# =========================================================
# OPTION CHAIN AI
# =========================================================

def option_chain_ai(
    active_symbol,
    is_delta,
    option_data=None,
):

    st.subheader(
        "📊 Option Chain AI"
    )

    if is_delta:

        st.info(
            "ℹ️ Delta Futures selected: "
            "Indian Option Chain is not applicable."
        )

        st.caption(
            f"{active_symbol} is a Delta Futures "
            "contract. Use BUY/SELL Futures execution."
        )

        return

    # -----------------------------------------------------
    # NO OPTION DATA
    # -----------------------------------------------------

    if not isinstance(
        option_data,
        dict,
    ):

        st.warning(
            "Option Chain data unavailable."
        )

        return

    if option_data.get(
        "success",
        True,
    ) is False:

        st.warning(
            "Option Chain unavailable: "
            + str(
                option_data.get(
                    "error",
                    "Unknown error",
                )
            )
        )

        return

    # -----------------------------------------------------
    # READ DATA
    # -----------------------------------------------------

    spot = safe_float(
        option_data.get(
            "underlying",
            option_data.get(
                "Spot",
                0,
            ),
        )
    )

    atm = safe_float(
        option_data.get(
            "strike",
            option_data.get(
                "ATM",
                0,
            ),
        )
    )

    ce_ltp = safe_float(
        option_data.get(
            "CE_LTP",
            option_data.get(
                "CE",
                0,
            ),
        )
    )

    pe_ltp = safe_float(
        option_data.get(
            "PE_LTP",
            option_data.get(
                "PE",
                0,
            ),
        )
    )

    expiry = str(
        option_data.get(
            "expiry",
            "",
        )
    )

    ce_contract = option_data.get(
        "CE_CONTRACT",
        {},
    )

    pe_contract = option_data.get(
        "PE_CONTRACT",
        {},
    )

    # -----------------------------------------------------
    # TOP METRICS
    # -----------------------------------------------------

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Spot",
        f"₹{spot:,.2f}"
        if spot > 0
        else "Waiting",
    )

    c2.metric(
        "ATM",
        f"{atm:,.0f}"
        if atm > 0
        else "Waiting",
    )

    c3.metric(
        "CE Premium",
        (
            f"₹{ce_ltp:,.2f}"
            if ce_ltp > 0
            else "Waiting"
        ),
    )

    c4.metric(
        "PE Premium",
        (
            f"₹{pe_ltp:,.2f}"
            if pe_ltp > 0
            else "Waiting"
        ),
    )

    # -----------------------------------------------------
    # CONTRACT DETAILS
    # -----------------------------------------------------

    if expiry:

        st.caption(
            f"Expiry: {expiry}"
        )

    d1, d2 = st.columns(2)

    with d1:

        if isinstance(
            ce_contract,
            dict,
        ) and ce_contract:

            st.success(
                "🟢 CE READY"
            )

            st.caption(
                "Symbol: "
                + str(
                    ce_contract.get(
                        "trading_symbol",
                        "N/A",
                    )
                )
            )

            st.caption(
                "Token: "
                + str(
                    ce_contract.get(
                        "token",
                        "N/A",
                    )
                )
            )

            st.caption(
                "LTP: "
                + (
                    f"₹{ce_ltp:,.2f}"
                    if ce_ltp > 0
                    else "Waiting"
                )
            )

    with d2:

        if isinstance(
            pe_contract,
            dict,
        ) and pe_contract:

            st.success(
                "🟢 PE READY"
            )

            st.caption(
                "Symbol: "
                + str(
                    pe_contract.get(
                        "trading_symbol",
                        "N/A",
                    )
                )
            )

            st.caption(
                "Token: "
                + str(
                    pe_contract.get(
                        "token",
                        "N/A",
                    )
                )
            )

            st.caption(
                "LTP: "
                + (
                    f"₹{pe_ltp:,.2f}"
                    if pe_ltp > 0
                    else "Waiting"
                )
            )


# =========================================================
# PORTFOLIO
# =========================================================

def portfolio_section(
    trader,
    active_symbol,
    display_price,
    is_delta,
):

    st.subheader(
        "📦 Portfolio  & Risk Management"
    )

    active_positions = get_active_positions(
        trader
    )

    if not active_positions:

        st.info(
            "No Open Position"
        )

        return

    rows = []

    total_delta_pnl = 0.0
    total_india_pnl = 0.0

    active_symbol_upper = str(
        active_symbol or ""
    ).strip().upper()

    for _, position in active_positions.items():

        if not isinstance(
            position,
            dict,
        ):
            continue

        position_symbol = str(
            position.get(
                "symbol",
                active_symbol_upper,
            )
        ).strip().upper()

        if not position_symbol:
            continue

        position_side = get_position_side(
            position
        )

        option_mode = str(
            position.get(
                "option_mode",
                "N/A",
            )
        ).strip().upper()

        entry = safe_float(
            position.get(
                "entry",
                0,
            )
        )

        qty = safe_float(
            position.get(
                "qty",
                position.get(
                    "quantity",
                    0,
                ),
            )
        )

        stoploss = safe_float(
            position.get(
                "stoploss",
                position.get(
                    "stop_loss",
                    position.get(
                        "current_stoploss",
                        0,
                    ),
                ),
            )
        )

        target = safe_float(
            position.get(
                "target",
                0,
            )
        )

        position_delta = is_delta_symbol(
            position_symbol
        )

        ltp = get_position_ltp(
            position_symbol=position_symbol,
            active_symbol=active_symbol_upper,
            display_price=display_price,
            entry=entry,
        )

        pnl = calculate_position_pnl(
            position,
            ltp,
        )

        if position_delta:

            total_delta_pnl += pnl

        else:

            total_india_pnl += pnl

        rows.append(
            {
                "Symbol": position_symbol,
                "Position": position_side,
                "Option": option_mode,
                "Entry": format_price(
                    entry,
                    position_delta,
                ),
                "LTP": format_price(
                    ltp,
                    position_delta,
                ),
                "Quantity": qty,
                "Stop Loss": format_price(
                    stoploss,
                    position_delta,
                ),
                "Target": format_price(
                    target,
                    position_delta,
                ),
                "P&L": format_pnl(
                    pnl,
                    position_delta,
                ),
            }
        )

    if not rows:

        st.info(
            "No Open Position"
        )

        return

    portfolio_df = pd.DataFrame(
        rows
    )

    st.table(
        portfolio_df
    )

    has_delta = False
    has_india = False

    for row in rows:

        if is_delta_symbol(
            row["Symbol"]
        ):

            has_delta = True

        else:

            has_india = True

    if has_delta and has_india:

        c1, c2 = st.columns(2)

    else:

        c1 = st.container()
        c2 = None

    if has_delta:

        c1.metric(
            "📊 Delta Total Open P&L",
            f"${total_delta_pnl:,.8f}",
        )

    if has_india:

        if c2 is not None:

            c2.metric(
                "📊 India Total Open P&L",
                f"₹{total_india_pnl:,.2f}",
            )

        else:

            st.metric(
                "📊 India Total Open P&L",
                f"₹{total_india_pnl:,.2f}",
            )


# =========================================================
# DELTA EXECUTION
# =========================================================

def delta_execution_status(
    signal_data,
):

    st.subheader(
        "⚡ Delta Futures Execution"
    )

    current_signal = "HOLD"

    if isinstance(
        signal_data,
        dict,
    ):

        current_signal = normalize_signal(
            signal_data.get(
                "SIGNAL",
                signal_data.get(
                    "Signal",
                    signal_data.get(
                        "signal",
                        "HOLD",
                    ),
                ),
            )
        )

    if current_signal == "BUY":

        st.success(
            "🟢 Signal Direction: BUY / LONG"
        )

        st.caption(
            "Delta Futures supports long BUY execution."
        )

    elif current_signal == "SELL":

        st.error(
            "🔴 Signal Direction: SELL / SHORT"
        )

        st.caption(
            "Delta Futures supports short SELL execution."
        )

    else:

        st.warning(
            "🟡 No Delta entry — WAIT"
        )

    st.caption(
        "Execution is controlled by "
        "TradeManager and auto-trader."
    )
# =========================================================
# RISK MANAGER
# =========================================================

def risk_manager(
    trader,
    display_price,
    is_delta,
    active_symbol=None,
    default_quantity=1,
    option_mode="CE",
    option_ce_ltp=0.0,
    option_pe_ltp=0.0,
):
    """
    Central Risk Manager.

    DELTA:
        Single futures risk calculation.

    CE:
        CE-only risk calculation.

    PE:
        PE-only risk calculation.

    ALL:
        Independent CE + PE risk calculations.
        Combined risk/reward is also displayed.

    No live broker order is placed here.
    """

    st.subheader("🛡 Risk Management")

    # =====================================================
    # BASIC VALUES
    # =====================================================

    capital = safe_float(
        getattr(trader, "balance", 0.0)
    )

    symbol_key = str(
        active_symbol or "UNKNOWN"
    ).strip().upper()

    option_mode = str(
        option_mode or "CE"
    ).strip().upper()

    if option_mode not in {"CE", "PE", "ALL"}:
        option_mode = "CE"

    option_ce_ltp = safe_float(option_ce_ltp)
    option_pe_ltp = safe_float(option_pe_ltp)

    safe_symbol_key = (
        symbol_key
        .replace("^", "")
        .replace("-", "_")
        .replace("/", "_")
        .replace(" ", "_")
        .replace(".", "_")
    )

    # =====================================================
    # RISK %
    # =====================================================

    risk_key = (
        f"dashboard_risk_percent_"
        f"{safe_symbol_key}"
    )

    risk_percent = st.slider(
        "Risk %",
        min_value=1,
        max_value=5,
        value=2,
        step=1,
        key=risk_key,
    )

    risk_amount = (
        capital * risk_percent / 100
    )

    # =====================================================
    # DELTA FUTURES
    # =====================================================

    if is_delta:

        entry_key = (
            f"dashboard_entry_price_"
            f"{safe_symbol_key}_DELTA"
        )

        stop_key = (
            f"dashboard_stop_price_"
            f"{safe_symbol_key}_DELTA"
        )

        target_key = (
            f"dashboard_target_price_"
            f"{safe_symbol_key}_DELTA"
        )

        quantity_key = (
            f"dashboard_order_quantity_"
            f"{safe_symbol_key}_DELTA"
        )

        default_entry = safe_float(
            display_price,
            0.0032,
        )

        if default_entry <= 0:
            default_entry = 0.0032

        default_stop = default_entry * 0.99

        default_target = (
            default_entry
            + (default_entry - default_stop) * 2
        )

        entry = st.number_input(
            "Entry Price",
            min_value=0.0,
            value=float(default_entry),
            step=0.00000001,
            format="%.8f",
            key=entry_key,
        )

        stop = st.number_input(
            "Stop Loss",
            min_value=0.0,
            value=float(default_stop),
            step=0.00000001,
            format="%.8f",
            key=stop_key,
        )

        target = st.number_input(
            "Target Price",
            min_value=0.0,
            value=float(default_target),
            step=0.00000001,
            format="%.8f",
            key=target_key,
        )

        safe_default_quantity = max(
            1,
            int(
                safe_float(
                    default_quantity,
                    1,
                )
            ),
        )

        order_quantity = st.number_input(
            "Order Quantity",
            min_value=1,
            max_value=1000000,
            value=safe_default_quantity,
            step=1,
            key=quantity_key,
        )

        risk_per_unit = abs(
            entry - stop
        )

        reward_per_unit = (
            abs(target - entry)
            if entry > 0 and target > 0
            else 0.0
        )

        mathematical_qty = (
            int(risk_amount / risk_per_unit)
            if risk_per_unit > 0
            else 0
        )

        total_risk = (
            risk_per_unit * order_quantity
        )

        total_reward = (
            reward_per_unit * order_quantity
        )

        reward_risk_ratio = (
            reward_per_unit / risk_per_unit
            if risk_per_unit > 0
            else 0.0
        )

        st.divider()

        c1, c2, c3 = st.columns(3)

        c1.metric(
            "🛡 TOTAL RISK",
            f"${total_risk:,.8f}",
        )

        c2.metric(
            "🎯 TOTAL REWARD",
            f"${total_reward:,.8f}",
        )

        c3.metric(
            "⚖️ RISK / REWARD",
            f"1 : {reward_risk_ratio:.2f}",
        )

        d1, d2, d3 = st.columns(3)

        d1.metric(
            "Risk Amount",
            f"${risk_amount:,.8f}",
        )

        d2.metric(
            "Risk / Unit",
            f"${risk_per_unit:,.8f}",
        )

        d3.metric(
            "Reward / Unit",
            f"${reward_per_unit:,.8f}",
        )

        st.metric(
            "📦 Order Quantity",
            int(order_quantity),
        )

        st.caption(
            f"Selected Symbol: {symbol_key}"
        )

        st.caption(
            "Delta Futures quantity is contract-based. "
            "Actual execution quantity remains controlled "
            "by TradeManager."
        )

        if total_risk > risk_amount:
            st.warning(
                f"⚠️ Order risk ${total_risk:,.8f} "
                f"is above risk budget "
                f"${risk_amount:,.8f}."
            )

        if reward_risk_ratio >= 2:
            st.success(
                f"✅ Good Risk/Reward: "
                f"1 : {reward_risk_ratio:.2f}"
            )
        elif reward_risk_ratio >= 1:
            st.warning(
                f"⚠️ Moderate Risk/Reward: "
                f"1 : {reward_risk_ratio:.2f}"
            )
        else:
            st.error(
                f"🔴 Poor Risk/Reward: "
                f"1 : {reward_risk_ratio:.2f}"
            )

        return {
            "entry": entry,
            "stop": stop,
            "target": target,
            "risk_percent": risk_percent,
            "risk_amount": risk_amount,
            "risk_per_unit": risk_per_unit,
            "reward_per_unit": reward_per_unit,
            "reward": total_reward,
            "total_risk": total_risk,
            "risk_reward_ratio": reward_risk_ratio,
            "order_quantity": int(order_quantity),
            "suggested_quantity": mathematical_qty,
            "option_mode": "DELTA",
        }

    # =====================================================
    # INDIAN OPTIONS
    # =====================================================

    st.info(
        f"📊 Option Mode: {option_mode} | "
        f"CE ₹{option_ce_ltp:,.2f} | "
        f"PE ₹{option_pe_ltp:,.2f}"
    )

    safe_default_quantity = max(
        1,
        int(
            safe_float(
                default_quantity,
                1,
            )
        ),
    )

    price_step = 0.05

    # =====================================================
    # INTERNAL OPTION CALCULATOR
    # =====================================================

    def calculate_option(
        label,
        ltp,
        risk_budget,
        quantity_key_suffix,
        color_icon,
    ):
        ltp = safe_float(ltp)

        default_entry = (
            ltp
            if ltp > 0
            else safe_float(display_price, 100.0)
        )

        if default_entry <= 0:
            default_entry = 100.0

        # Default: 20% premium SL
        default_stop = default_entry * 0.80

        # Default: 2R target
        default_target = (
            default_entry
            + (default_entry - default_stop) * 2
        )

        entry_key = (
            f"dashboard_entry_price_"
            f"{safe_symbol_key}_{quantity_key_suffix}"
        )

        stop_key = (
            f"dashboard_stop_price_"
            f"{safe_symbol_key}_{quantity_key_suffix}"
        )

        target_key = (
            f"dashboard_target_price_"
            f"{safe_symbol_key}_{quantity_key_suffix}"
        )

        quantity_key = (
            f"dashboard_order_quantity_"
            f"{safe_symbol_key}_{quantity_key_suffix}"
        )

        st.markdown(
            f"### {color_icon} {label} Risk Management"
        )

        st.caption(
            f"Current Kotak LTP: ₹{ltp:,.2f}"
        )

        entry = st.number_input(
            f"{label} Entry Price",
            min_value=0.0,
            value=float(default_entry),
            step=price_step,
            format="%.2f",
            key=entry_key,
        )

        stop = st.number_input(
            f"{label} Stop Loss",
            min_value=0.0,
            value=float(default_stop),
            step=price_step,
            format="%.2f",
            key=stop_key,
        )

        target = st.number_input(
            f"{label} Target Price",
            min_value=0.0,
            value=float(default_target),
            step=price_step,
            format="%.2f",
            key=target_key,
        )

        order_quantity = st.number_input(
            f"{label} Order Quantity",
            min_value=1,
            max_value=1000000,
            value=safe_default_quantity,
            step=1,
            key=quantity_key,
        )

        risk_per_unit = abs(
            entry - stop
        )

        reward_per_unit = (
            abs(target - entry)
            if entry > 0 and target > 0
            else 0.0
        )

        total_risk = (
            risk_per_unit * order_quantity
        )

        total_reward = (
            reward_per_unit * order_quantity
        )

        reward_risk_ratio = (
            reward_per_unit / risk_per_unit
            if risk_per_unit > 0
            else 0.0
        )

        mathematical_qty = (
            int(risk_budget / risk_per_unit)
            if risk_per_unit > 0
            else 0
        )

        return {
            "entry": entry,
            "stop": stop,
            "target": target,
            "quantity": int(order_quantity),
            "risk_per_unit": risk_per_unit,
            "reward_per_unit": reward_per_unit,
            "total_risk": total_risk,
            "total_reward": total_reward,
            "risk_reward_ratio": reward_risk_ratio,
            "suggested_quantity": mathematical_qty,
            "risk_budget": risk_budget,
            "ltp": ltp,
        }

    # =====================================================
    # CE ONLY
    # =====================================================

    if option_mode == "CE":

        st.success(
            f"🟢 CE Risk Reference: "
            f"₹{option_ce_ltp:,.2f}"
        )

        ce = calculate_option(
            label="CE",
            ltp=option_ce_ltp,
            risk_budget=risk_amount,
            quantity_key_suffix="CE",
            color_icon="🟢",
        )

        st.divider()

        c1, c2, c3 = st.columns(3)

        c1.metric(
            "🛡 TOTAL RISK",
            f"₹{ce['total_risk']:,.2f}",
        )

        c2.metric(
            "🎯 TOTAL REWARD",
            f"₹{ce['total_reward']:,.2f}",
        )

        c3.metric(
            "⚖️ RISK / REWARD",
            f"1 : {ce['risk_reward_ratio']:.2f}",
        )

        d1, d2, d3 = st.columns(3)

        d1.metric(
            "Risk Amount",
            f"₹{risk_amount:,.2f}",
        )

        d2.metric(
            "Risk / Unit",
            f"₹{ce['risk_per_unit']:,.2f}",
        )

        d3.metric(
            "Reward / Unit",
            f"₹{ce['reward_per_unit']:,.2f}",
        )

        st.metric(
            "📦 Order Quantity",
            ce["quantity"],
        )

        st.caption(
            f"Selected Symbol: {symbol_key}"
        )

        st.caption(
            "Option Mode: CE"
        )

        st.caption(
            f"Mathematical Risk Quantity: "
            f"{ce['suggested_quantity']:,}"
        )

        if ce["total_risk"] > risk_amount:
            st.warning(
                f"⚠️ Total risk ₹{ce['total_risk']:,.2f} "
                f"is above risk budget "
                f"₹{risk_amount:,.2f}."
            )

        if ce["risk_reward_ratio"] >= 2:
            st.success(
                f"✅ Good Risk/Reward: "
                f"1 : {ce['risk_reward_ratio']:.2f}"
            )
        elif ce["risk_reward_ratio"] >= 1:
            st.warning(
                f"⚠️ Moderate Risk/Reward: "
                f"1 : {ce['risk_reward_ratio']:.2f}"
            )
        else:
            st.error(
                f"🔴 Poor Risk/Reward: "
                f"1 : {ce['risk_reward_ratio']:.2f}"
            )

        return {
            "entry": ce["entry"],
            "stop": ce["stop"],
            "target": ce["target"],
            "risk_percent": risk_percent,
            "risk_amount": risk_amount,
            "risk_per_unit": ce["risk_per_unit"],
            "reward_per_unit": ce["reward_per_unit"],
            "reward": ce["total_reward"],
            "total_risk": ce["total_risk"],
            "risk_reward_ratio": ce["risk_reward_ratio"],
            "order_quantity": ce["quantity"],
            "suggested_quantity": ce["suggested_quantity"],
            "option_mode": "CE",
            "option_ce_ltp": option_ce_ltp,
            "option_pe_ltp": option_pe_ltp,
        }

    # =====================================================
    # PE ONLY
    # =====================================================

    if option_mode == "PE":

        st.error(
            f"🔴 PE Risk Reference: "
            f"₹{option_pe_ltp:,.2f}"
        )

        pe = calculate_option(
            label="PE",
            ltp=option_pe_ltp,
            risk_budget=risk_amount,
            quantity_key_suffix="PE",
            color_icon="🔴",
        )

        st.divider()

        c1, c2, c3 = st.columns(3)

        c1.metric(
            "🛡 TOTAL RISK",
            f"₹{pe['total_risk']:,.2f}",
        )

        c2.metric(
            "🎯 TOTAL REWARD",
            f"₹{pe['total_reward']:,.2f}",
        )

        c3.metric(
            "⚖️ RISK / REWARD",
            f"1 : {pe['risk_reward_ratio']:.2f}",
        )

        d1, d2, d3 = st.columns(3)

        d1.metric(
            "Risk Amount",
            f"₹{risk_amount:,.2f}",
        )

        d2.metric(
            "Risk / Unit",
            f"₹{pe['risk_per_unit']:,.2f}",
        )

        d3.metric(
            "Reward / Unit",
            f"₹{pe['reward_per_unit']:,.2f}",
        )

        st.metric(
            "📦 Order Quantity",
            pe["quantity"],
        )

        st.caption(
            f"Selected Symbol: {symbol_key}"
        )

        st.caption(
            "Option Mode: PE"
        )

        st.caption(
            f"Mathematical Risk Quantity: "
            f"{pe['suggested_quantity']:,}"
        )

        if pe["total_risk"] > risk_amount:
            st.warning(
                f"⚠️ Total risk ₹{pe['total_risk']:,.2f} "
                f"is above risk budget "
                f"₹{risk_amount:,.2f}."
            )

        if pe["risk_reward_ratio"] >= 2:
            st.success(
                f"✅ Good Risk/Reward: "
                f"1 : {pe['risk_reward_ratio']:.2f}"
            )
        elif pe["risk_reward_ratio"] >= 1:
            st.warning(
                f"⚠️ Moderate Risk/Reward: "
                f"1 : {pe['risk_reward_ratio']:.2f}"
            )
        else:
            st.error(
                f"🔴 Poor Risk/Reward: "
                f"1 : {pe['risk_reward_ratio']:.2f}"
            )

        return {
            "entry": pe["entry"],
            "stop": pe["stop"],
            "target": pe["target"],
            "risk_percent": risk_percent,
            "risk_amount": risk_amount,
            "risk_per_unit": pe["risk_per_unit"],
            "reward_per_unit": pe["reward_per_unit"],
            "reward": pe["total_reward"],
            "total_risk": pe["total_risk"],
            "risk_reward_ratio": pe["risk_reward_ratio"],
            "order_quantity": pe["quantity"],
            "suggested_quantity": pe["suggested_quantity"],
            "option_mode": "PE",
            "option_ce_ltp": option_ce_ltp,
            "option_pe_ltp": option_pe_ltp,
        }

    # =====================================================
    # ALL = CE + PE
    # =====================================================

    st.warning(
        "📊 ALL Mode: CE और PE दोनों के लिए "
        "अलग-अलग risk management active है."
    )

    # Shared risk budget:
    # CE = 50%, PE = 50%
    ce_risk_budget = risk_amount / 2
    pe_risk_budget = risk_amount / 2

    ce = calculate_option(
        label="CE",
        ltp=option_ce_ltp,
        risk_budget=ce_risk_budget,
        quantity_key_suffix="ALL_CE",
        color_icon="🟢",
    )

    st.divider()

    pe = calculate_option(
        label="PE",
        ltp=option_pe_ltp,
        risk_budget=pe_risk_budget,
        quantity_key_suffix="ALL_PE",
        color_icon="🔴",
    )

    # =====================================================
    # CE / PE SUMMARY
    # =====================================================

    st.divider()

    st.markdown("### 📊 CE + PE Risk Summary")

    s1, s2, s3 = st.columns(3)

    s1.metric(
        "🟢 CE Risk",
        f"₹{ce['total_risk']:,.2f}",
    )

    s2.metric(
        "🔴 PE Risk",
        f"₹{pe['total_risk']:,.2f}",
    )

    s3.metric(
        "🛡 Combined Risk",
        f"₹{ce['total_risk'] + pe['total_risk']:,.2f}",
    )

    s4, s5, s6 = st.columns(3)

    s4.metric(
        "🎯 CE Reward",
        f"₹{ce['total_reward']:,.2f}",
    )

    s5.metric(
        "🎯 PE Reward",
        f"₹{pe['total_reward']:,.2f}",
    )

    combined_reward = (
        ce["total_reward"]
        + pe["total_reward"]
    )

    combined_risk = (
        ce["total_risk"]
        + pe["total_risk"]
    )

    s6.metric(
        "🎯 Combined Reward",
        f"₹{combined_reward:,.2f}",
    )

    combined_rr = (
        combined_reward / combined_risk
        if combined_risk > 0
        else 0.0
    )

    st.metric(
        "⚖️ COMBINED RISK / REWARD",
        f"1 : {combined_rr:.2f}",
    )

    st.caption(
        f"Total Risk Budget: ₹{risk_amount:,.2f} "
        f"(CE ₹{ce_risk_budget:,.2f} + "
        f"PE ₹{pe_risk_budget:,.2f})"
    )

    # =====================================================
    # WARNINGS
    # =====================================================

    if combined_risk > risk_amount:
        st.warning(
            f"⚠️ Combined option risk "
            f"₹{combined_risk:,.2f} "
            f"is above total risk budget "
            f"₹{risk_amount:,.2f}."
        )
    else:
        st.success(
            f"✅ Combined option risk "
            f"₹{combined_risk:,.2f} "
            f"is within risk budget "
            f"₹{risk_amount:,.2f}."
        )

    # =====================================================
    # CE / PE R:R STATUS
    # =====================================================

    r1, r2 = st.columns(2)

    with r1:
        if ce["risk_reward_ratio"] >= 2:
            st.success(
                f"🟢 CE R:R = "
                f"1 : {ce['risk_reward_ratio']:.2f}"
            )
        elif ce["risk_reward_ratio"] >= 1:
            st.warning(
                f"🟡 CE R:R = "
                f"1 : {ce['risk_reward_ratio']:.2f}"
            )
        else:
            st.error(
                f"🔴 CE R:R = "
                f"1 : {ce['risk_reward_ratio']:.2f}"
            )

    with r2:
        if pe["risk_reward_ratio"] >= 2:
            st.success(
                f"🟢 PE R:R = "
                f"1 : {pe['risk_reward_ratio']:.2f}"
            )
        elif pe["risk_reward_ratio"] >= 1:
            st.warning(
                f"🟡 PE R:R = "
                f"1 : {pe['risk_reward_ratio']:.2f}"
            )
        else:
            st.error(
                f"🔴 PE R:R = "
                f"1 : {pe['risk_reward_ratio']:.2f}"
            )

    st.caption(
        f"Selected Symbol: {symbol_key}"
    )

    st.caption(
        "Option Mode: ALL"
    )

    st.caption(
        f"CE Mathematical Risk Quantity: "
        f"{ce['suggested_quantity']:,}"
    )

    st.caption(
        f"PE Mathematical Risk Quantity: "
        f"{pe['suggested_quantity']:,}"
    )

    st.caption(
        "Indian option risk is calculated from "
        "the selected CE/PE premium. "
        "ALL mode uses a shared risk budget split "
        "50% CE + 50% PE. "
        "Order quantity follows lot size × lots."
    )

    # =====================================================
    # COMPATIBILITY RETURN
    # =====================================================

    # Existing dashboard callers expect these top-level
    # fields. CE is used as the primary compatibility side.
    return {
        "entry": ce["entry"],
        "stop": ce["stop"],
        "target": ce["target"],
        "risk_percent": risk_percent,
        "risk_amount": risk_amount,
        "risk_per_unit": ce["risk_per_unit"],
        "reward_per_unit": ce["reward_per_unit"],
        "reward": combined_reward,
        "total_risk": combined_risk,
        "risk_reward_ratio": combined_rr,
        "order_quantity": ce["quantity"],
        "suggested_quantity": ce["suggested_quantity"],
        "option_mode": "ALL",
        "option_ce_ltp": option_ce_ltp,
        "option_pe_ltp": option_pe_ltp,
        "CE": ce,
        "PE": pe,
        "combined_risk": combined_risk,
        "combined_reward": combined_reward,
        "combined_risk_reward_ratio": combined_rr,
    }
# =========================================================
# MAIN DASHBOARD PAGE
# =========================================================

def dashboard_page(
    trader,
    current_price,
    symbol,
    market_type=None,
    trade_symbol=None,
    market_status_value=None,
    market_message=None,
    default_quantity=1,
    option_mode="CE",
):

    # =====================================================
    # RESOLVE ACTIVE SYMBOL
    # =====================================================

    requested_symbol = str(
        trade_symbol or ""
    ).strip().upper()

    incoming_symbol = str(
        symbol or ""
    ).strip().upper()

    session_trade = str(
        st.session_state.get(
            "trade_symbol",
            "",
        )
        or ""
    ).strip().upper()

    session_futures = str(
        st.session_state.get(
            "futures_symbol",
            "",
        )
        or ""
    ).strip().upper()

    market_type_upper = str(
        market_type or ""
    ).strip().upper()

    if requested_symbol:

        active_symbol = requested_symbol

    elif (
        market_type_upper == "FUTURES"
        and incoming_symbol
    ):

        active_symbol = incoming_symbol

    elif incoming_symbol:

        active_symbol = incoming_symbol

    elif (
        market_type_upper == "FUTURES"
        and session_futures
    ):

        active_symbol = session_futures

    elif session_trade:

        active_symbol = session_trade

    else:

        active_symbol = "^NSEI"

    # =====================================================
    # SESSION SYNC
    # =====================================================

    st.session_state[
        "trade_symbol"
    ] = active_symbol

    if market_type_upper == "FUTURES":

        st.session_state[
            "futures_symbol"
        ] = active_symbol

    # =====================================================
    # OPTION MODE
    # =====================================================

    option_mode = str(
        option_mode
        or st.session_state.get(
            "option_mode",
            "CE",
        )
        or "CE"
    ).strip().upper()

    if option_mode not in {
        "CE",
        "PE",
        "ALL",
    }:

        option_mode = "CE"

    # =====================================================
    # MARKET
    # =====================================================

    market_info = get_market_status(
        active_symbol
    )

    is_delta = (
        market_info["market"]
        == "DELTA"
    )

    # =====================================================
    # HEADER
    # =====================================================

    st.title(
        "📈 Jha SmartTrader AI Pro"
    )

    status_ribbon()

    st.caption(
        "AI Powered Intraday Trading Dashboard"
    )

    st.divider()

    # =====================================================
    # MARKET RIBBON
    # =====================================================

    if is_delta:

        st.success(
            "🟢 DELTA EXCHANGE • "
            "MARKET OPEN 24/7"
        )

        st.caption(
            f"Trading Symbol: {active_symbol} | "
            "Crypto Futures • "
            "No daily market close"
        )

    elif market_info["open"]:

        st.success(
            "🟢 INDIAN MARKET • OPEN"
        )

        st.caption(
            f"Trading Symbol: {active_symbol} | "
            "Indian session: 09:15–15:30"
        )

    else:

        if (
            datetime.now(
                ZoneInfo("Asia/Kolkata")
            ).weekday()
            >= 5
        ):

            st.error(
                "🔴 INDIAN MARKET • "
                "CLOSED • WEEKEND"
            )

        else:

            st.error(
                "🔴 INDIAN MARKET • CLOSED"
            )

        st.caption(
            f"Trading Symbol: {active_symbol} | "
            "Indian session: 09:15–15:30"
        )

    st.divider()

    # =====================================================
    # EXECUTION MODE
    # =====================================================

    st.subheader(
        "🎛 Execution Mode Switch"
    )

    paper_mode = st.toggle(
        "📝 Enable Paper Trading "
        "(Virtual Buy/Sell)",
        value=bool(
            getattr(
                config,
                "PAPER_TRADE",
                True,
            )
        ),
        key="dashboard_paper_trade_toggle",
    )

    config.PAPER_TRADE = paper_mode

    if paper_mode:

        st.info(
            "ℹ️ Paper Trading is ON — "
            "orders execute virtually."
        )

    else:

        st.warning(
            "⚠️ Paper Trading is OFF — "
            "Live/Real trading mode is active."
        )

    st.divider()

    # =====================================================
    # ACCOUNT
    # =====================================================

    account_summary(
        trader=trader,
        current_price=current_price,
        symbol=active_symbol,
    )

    st.divider()

    # =====================================================
    # MARKET STATUS
    # =====================================================

    market_status(
        active_symbol
    )

    st.divider()

    # =====================================================
    # SIGNALS
    # =====================================================

    signal_data = signal_indicators(
        active_symbol
    )

    # =====================================================
    # LIVE PRICE
    # =====================================================

    display_price = safe_float(
        current_price
    )

    if isinstance(
        signal_data,
        dict,
    ):

        signal_price = safe_float(
            signal_data.get(
                "Price",
                0,
            )
        )

        if signal_price > 0:

            display_price = signal_price

    if display_price <= 0:

        display_price = safe_float(
            current_price
        )

    if is_delta:

        st.metric(
            "💵 Live Delta Price",
            format_price(
                display_price,
                True,
            ),
        )

    else:

        st.metric(
            "💵 Live Market Price",
            format_price(
                display_price,
                False,
            ),
        )

    # =====================================================
    # GET EXACT KOTAK OPTION PRICE
    # =====================================================

    option_data = None

    option_index = None

    option_ce_ltp = 0.0
    option_pe_ltp = 0.0

    if not is_delta:

        option_index = get_option_index_name(
            active_symbol
        )

        if option_index:

            option_data = (
                get_dashboard_option_data(
                    index_name=option_index,
                    underlying_price=display_price,
                )
            )

            if isinstance(
                option_data,
                dict,
            ):

                option_ce_ltp = safe_float(
                    option_data.get(
                        "CE_LTP",
                        option_data.get(
                            "CE",
                            0,
                        ),
                    )
                )

                option_pe_ltp = safe_float(
                    option_data.get(
                        "PE_LTP",
                        option_data.get(
                            "PE",
                            0,
                        ),
                    )
                )

    # =====================================================
    # OPTION PRICE STATUS
    # =====================================================

    if (
        not is_delta
        and option_index
    ):

        if (
            option_ce_ltp > 0
            or option_pe_ltp > 0
        ):

            st.success(
                f"🟢 Kotak Neo Option Prices • "
                f"{option_index} • "
                f"ATM"
            )

            pc1, pc2 = st.columns(2)

            pc1.metric(
                "CE LTP",
                (
                    f"₹{option_ce_ltp:,.2f}"
                    if option_ce_ltp > 0
                    else "Waiting"
                ),
            )

            pc2.metric(
                "PE LTP",
                (
                    f"₹{option_pe_ltp:,.2f}"
                    if option_pe_ltp > 0
                    else "Waiting"
                ),
            )

        else:

            st.warning(
                f"⚠️ Kotak option price unavailable "
                f"for {option_index}."
            )

    st.divider()

    # =====================================================
    # PERFORMANCE
    # =====================================================

    performance_report()

    st.divider()

    # =====================================================
    # PORTFOLIO
    # =====================================================

    portfolio_section(
        trader=trader,
        active_symbol=active_symbol,
        display_price=display_price,
        is_delta=is_delta,
    )

    st.divider()

    # =====================================================
    # DELTA EXECUTION
    # =====================================================

    if is_delta:

        delta_execution_status(
            signal_data
        )

        st.divider()

    # =====================================================
    # MARKET CHART
    # =====================================================

    if is_delta:

        delta_chart(
            active_symbol
        )

    else:

        st.subheader(
            "📈 Live Market Chart"
        )

        indian_chart(
            active_symbol
        )

    st.divider()

    # =====================================================
    # MULTI INDEX SCANNER
    # =====================================================

    multi_index_scanner()

    st.divider()

    # =====================================================
    # OPTION CHAIN
    # =====================================================

    option_chain_ai(
        active_symbol,
        is_delta,
        option_data=option_data,
    )

    st.divider()

    # =====================================================
    # LAST REFRESH
    # =====================================================

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