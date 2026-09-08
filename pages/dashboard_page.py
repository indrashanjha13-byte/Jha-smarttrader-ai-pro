# =========================================================
# JHA SMARTTRADER AI PRO
# pages/dashboard_page.py
# =========================================================

import os
from datetime import datetime, time

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

from ai_decision import ai_decision
from broker.broker_manager import BrokerManager
from option_chain_v2 import get_option_chain_summary
from signals import get_signals, download_data

import config


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
# SAFE HELPERS
# =========================================================

def safe_float(value, default=0.0):
    try:
        if value is None:
            return default

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
    """
    Always normalize position to LONG / SHORT.
    """

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
# MARKET STATUS
# =========================================================

def get_market_status(symbol):

    if is_delta_symbol(symbol):

        return {
            "market": "DELTA",
            "status": "OPEN_24X7",
            "open": True,
            "entry_allowed": True,
            "message": "🟢 DELTA EXCHANGE • MARKET OPEN 24/7",
        }

    now = datetime.now().time()

    market_open = time(9, 15)
    market_close = time(15, 30)

    if market_open <= now <= market_close:

        return {
            "market": "INDIA",
            "status": "OPEN",
            "open": True,
            "entry_allowed": True,
            "message": "🟢 INDIAN MARKET • OPEN",
        }

    return {
        "market": "INDIA",
        "status": "CLOSED",
        "open": False,
        "entry_allowed": False,
        "message": "🔴 INDIAN MARKET • CLOSED",
    }


# =========================================================
# STATUS RIBBON
# =========================================================

def status_ribbon():

    c1, c2, c3, c4, c5 = st.columns(5)

    try:
        broker = BrokerManager(config.BROKER)
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

    c1.info(f"🏦 {config.BROKER}")
    c1.caption(broker_status)

    c2.success("🟢 Market")
    c3.info("🤖 AI")
    c4.warning("⚙ Auto")
    c5.success("📱 Telegram")


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

    position = getattr(
        trader,
        "position",
        None,
    )

    if position:

        position_symbol = str(
            position.get(
                "symbol",
                symbol,
            )
        ).upper()

        position_side = get_position_side(
            position
        )

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

        ltp = safe_float(
            current_price,
            entry,
        )

        if ltp <= 0:
            ltp = entry

        if position_side == "SHORT":

            pnl = (
                entry - ltp
            ) * qty

        else:

            pnl = (
                ltp - entry
            ) * qty

        delta = is_delta_symbol(
            position_symbol
        )

        position_text = (
            f"{position_symbol} • {position_side}"
        )

        pnl_text = format_pnl(
            pnl,
            delta,
        )

    else:

        position_text = "No Position"
        pnl_text = "₹0.00"

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "💰 Balance",
        f"₹{balance:,.2f}",
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
        f"₹{balance:,.2f}",
    )


# =========================================================
# MARKET STATUS DISPLAY
# =========================================================

def market_status(symbol):

    info = get_market_status(
        symbol
    )

    st.subheader(
        "🟢 Market Status"
    )

    c1, c2, c3 = st.columns(3)

    if info["market"] == "DELTA":

        c1.metric(
            "Market",
            "🟢 OPEN 24/7",
        )

    else:

        c1.metric(
            "Market",
            "🟢 OPEN"
            if info["open"]
            else "🔴 CLOSED",
        )

    c2.metric(
        "Time",
        datetime.now().strftime(
            "%H:%M:%S"
        ),
    )

    c3.metric(
        "Date",
        datetime.now().strftime(
            "%d-%b-%Y"
        ),
    )

    if info["market"] == "DELTA":

        st.success(
            "🟢 DELTA EXCHANGE • MARKET OPEN 24/7"
        )

        st.caption(
            f"Trading Symbol: {symbol} | "
            "Crypto Futures • No daily market close"
        )

    elif info["open"]:

        st.success(
            "🟢 INDIAN MARKET • OPEN"
        )

        st.caption(
            f"Trading Symbol: {symbol} | "
            "Indian session: 09:15–15:30"
        )

    else:

        st.error(
            "🔴 INDIAN MARKET • CLOSED"
        )

        st.caption(
            f"Trading Symbol: {symbol} | "
            "Indian session: 09:15–15:30"
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
                f"Signal Error: {signal.get('error')}"
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

        # -------------------------------------------------
        # Main signal cards
        # -------------------------------------------------

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

        # -------------------------------------------------
        # Signal message
        # -------------------------------------------------

        if decision == "BUY":

            if delta:

                st.success(
                    f"🟢 DELTA FUTURES BUY / LONG • "
                    f"{symbol} • {strength:.1f}%"
                )

            else:

                st.success(
                    f"🟢 BUY SIGNAL • "
                    f"{symbol} • {strength:.1f}%"
                )

        elif decision == "SELL":

            if delta:

                st.error(
                    f"🔴 DELTA FUTURES SELL / SHORT • "
                    f"{symbol} • {strength:.1f}%"
                )

            else:

                st.error(
                    f"🔴 SELL SIGNAL • "
                    f"{symbol} • {strength:.1f}%"
                )

        else:

            st.warning(
                f"🟡 HOLD / WAIT • "
                f"{symbol} • {strength:.1f}%"
            )

        st.divider()

        # -------------------------------------------------
        # Indicators
        # -------------------------------------------------

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

        # -------------------------------------------------
        # Advanced indicators
        # -------------------------------------------------

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
        # AI Decision
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
                    f"Strength: {strength:.1f}%"
                )

                if ai_reason:

                    st.caption(
                        f"Reason: {ai_reason}"
                    )

        except Exception as e:

            st.caption(
                f"AI decision detail unavailable: {e}"
            )

        # -------------------------------------------------
        # Delta execution direction
        # -------------------------------------------------

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
        "Delta Exchange crypto futures are available 24/7."
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

        # -------------------------------------------------
        # Flatten columns
        # -------------------------------------------------

        if isinstance(
            data.columns,
            pd.MultiIndex,
        ):

            data.columns = [
                str(
                    col[0]
                    if isinstance(col, tuple)
                    else col
                )
                for col in data.columns
            ]

        # -------------------------------------------------
        # Find time column
        # -------------------------------------------------

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
                "Delta Chart Error: Candle time column not found."
            )

            return

        data["Time"] = pd.to_datetime(
            data[time_col],
            errors="coerce",
        )

        # -------------------------------------------------
        # Normalize OHLC
        # -------------------------------------------------

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
                "Delta Chart Error: Missing columns: "
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

        # -------------------------------------------------
        # EMA
        # -------------------------------------------------

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

        # -------------------------------------------------
        # Chart
        # -------------------------------------------------

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

        fig.update_layout(
            height=500,
            xaxis_rangeslider_visible=False,
            hovermode="x unified",
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
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

                close_value = data["Close"].iloc[-1]

                if hasattr(
                    close_value,
                    "iloc",
                ):

                    close_value = close_value.iloc[0]

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

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
    )

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
            f"{active_symbol} is a Delta Futures contract. "
            "Use BUY/SELL Futures execution instead."
        )

        return

    try:

        option = get_option_chain_summary(
            active_symbol
        )

        if (
            isinstance(
                option,
                dict,
            )
            and "error" not in option
        ):

            c1, c2, c3, c4 = st.columns(4)

            c1.metric(
                "Spot",
                option.get(
                    "Spot",
                    0,
                ),
            )

            c2.metric(
                "ATM",
                option.get(
                    "ATM",
                    0,
                ),
            )

            c3.metric(
                "CE Premium",
                option.get(
                    "CE_Premium",
                    "Waiting",
                ) or "Waiting",
            )

            c4.metric(
                "PE Premium",
                option.get(
                    "PE_Premium",
                    "Waiting",
                ) or "Waiting",
            )

        else:

            st.warning(
                option.get(
                    "error",
                    "Option Chain unavailable.",
                )
            )

    except Exception as e:

        st.error(
            f"Option Chain Error: {e}"
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
        "📦 Portfolio & Risk Management"
    )

    # -----------------------------------------------------
    # Get all positions
    # -----------------------------------------------------

    try:

        active_positions = (
            trader.get_active_positions()
        )

    except Exception:

        active_positions = getattr(
            trader,
            "positions",
            {},
        )

    if not isinstance(
        active_positions,
        dict,
    ):

        active_positions = {}

    # -----------------------------------------------------
    # Fallback
    # -----------------------------------------------------

    if not active_positions:

        position = getattr(
            trader,
            "position",
            None,
        )

        if position:

            position_symbol = str(
                position.get(
                    "symbol",
                    active_symbol,
                )
            ).upper()

            option_mode = str(
                position.get(
                    "option_mode",
                    "N/A",
                )
            ).upper()

            key = (
                f"{position_symbol}_{option_mode}"
            )

            active_positions = {
                key: position
            }

    if not active_positions:

        st.info(
            "No Open Position"
        )

        return

    # -----------------------------------------------------
    # Build rows
    # -----------------------------------------------------

    rows = []

    for _, position in active_positions.items():

        if not isinstance(
            position,
            dict,
        ):
            continue

        position_symbol = str(
            position.get(
                "symbol",
                active_symbol,
            )
        ).upper()

        position_side = get_position_side(
            position
        )

        option_mode = str(
            position.get(
                "option_mode",
                "N/A",
            )
        ).upper()

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

        # -------------------------------------------------
        # Current LTP
        # -------------------------------------------------

        ltp = safe_float(
            display_price,
            entry,
        )

        # If this is not the active symbol, try to get
        # its own latest signal price.
        if (
            position_symbol != str(
                active_symbol
            ).upper()
        ):

            try:

                position_signal = get_signals(
                    position_symbol
                )

                if isinstance(
                    position_signal,
                    dict,
                ):

                    signal_ltp = safe_float(
                        position_signal.get(
                            "Price",
                            0,
                        )
                    )

                    if signal_ltp > 0:

                        ltp = signal_ltp

            except Exception:
                pass

        if ltp <= 0:

            ltp = entry

        # -------------------------------------------------
        # P&L
        # -------------------------------------------------

        if position_side == "SHORT":

            pnl = (
                entry - ltp
            ) * qty

        else:

            pnl = (
                ltp - entry
            ) * qty

        # -------------------------------------------------
        # Row
        # -------------------------------------------------

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

    # -----------------------------------------------------
    # Table
    # -----------------------------------------------------

    portfolio_df = pd.DataFrame(
        rows
    )

    st.dataframe(
        portfolio_df,
        use_container_width=True,
        hide_index=True,
    )

    # -----------------------------------------------------
    # Position summary
    # -----------------------------------------------------

    total_pnl = 0.0

    for _, position in active_positions.items():

        if not isinstance(
            position,
            dict,
        ):
            continue

        position_symbol = str(
            position.get(
                "symbol",
                active_symbol,
            )
        ).upper()

        position_side = get_position_side(
            position
        )

        entry = safe_float(
            position.get(
                "entry",
                0,
            )
        )

        qty = safe_float(
            position.get(
                "qty",
                0,
            )
        )

        if position_symbol == str(
            active_symbol
        ).upper():

            ltp = safe_float(
                display_price,
                entry,
            )

        else:

            ltp = entry

            try:

                sig = get_signals(
                    position_symbol
                )

                if isinstance(
                    sig,
                    dict,
                ):

                    latest = safe_float(
                        sig.get(
                            "Price",
                            0,
                        )
                    )

                    if latest > 0:
                        ltp = latest

            except Exception:
                pass

        if position_side == "SHORT":

            total_pnl += (
                entry - ltp
            ) * qty

        else:

            total_pnl += (
                ltp - entry
            ) * qty

    st.metric(
        "📊 Total Open P&L",
        format_pnl(
            total_pnl,
            is_delta,
        ),
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
        "Execution is controlled by TradeManager "
        "and the auto-trader."
    )


# =========================================================
# RISK MANAGER
# =========================================================

def risk_manager(
    trader,
    display_price,
    is_delta,
):

    st.subheader(
        "🛡 Risk Management"
    )

    capital = safe_float(
        getattr(
            trader,
            "balance",
            0.0,
        )
    )

    risk_percent = st.slider(
        "Risk %",
        min_value=1,
        max_value=5,
        value=2,
        step=1,
        key="dashboard_risk_percent",
    )

    # -----------------------------------------------------
    # Defaults
    # -----------------------------------------------------

    if is_delta:

        default_entry = safe_float(
            display_price,
            0.0032,
        )

        if default_entry <= 0:
            default_entry = 0.0032

        default_stop = (
            default_entry * 0.99
        )

        price_format = "%.8f"

    else:

        default_entry = safe_float(
            display_price,
            100.0,
        )

        if default_entry <= 0:
            default_entry = 100.0

        default_stop = (
            default_entry * 0.98
        )

        price_format = "%.2f"

    # -----------------------------------------------------
    # Entry / SL
    # -----------------------------------------------------

    entry = st.number_input(
        "Entry Price",
        min_value=0.0,
        value=float(default_entry),
        step=(
            0.00000001
            if is_delta
            else 0.05
        ),
        format=price_format,
        key="dashboard_entry_price",
    )

    stop = st.number_input(
        "Stop Loss",
        min_value=0.0,
        value=float(default_stop),
        step=(
            0.00000001
            if is_delta
            else 0.05
        ),
        format=price_format,
        key="dashboard_stop_price",
    )

    risk_amount = (
        capital
        * risk_percent
        / 100
    )

    risk_per_unit = abs(
        entry - stop
    )

    if risk_per_unit > 0:

        suggested_qty = int(
            risk_amount
            / risk_per_unit
        )

    else:

        suggested_qty = 0

    # -----------------------------------------------------
    # Delta warning
    # -----------------------------------------------------

    if is_delta:

        st.caption(
            "Delta Futures quantity is contract-based."
        )

        st.metric(
            "Risk Amount",
            f"${risk_amount:,.2f}",
        )

        if suggested_qty > 1_000_000:

            st.metric(
                "Suggested Quantity",
                "Contract-based",
            )

            st.warning(
                "⚠️ The mathematical risk quantity is "
                "very large because this contract has "
                "a very small unit price."
            )

            st.caption(
                "Actual execution quantity is controlled "
                "by TradeManager."
            )

        else:

            st.metric(
                "Suggested Quantity",
                suggested_qty,
            )

    else:

        st.metric(
            "Risk Amount",
            f"₹{risk_amount:,.2f}",
        )

        st.metric(
            "Suggested Quantity",
            suggested_qty,
        )

    return {
        "entry": entry,
        "stop": stop,
        "risk_percent": risk_percent,
        "risk_amount": risk_amount,
        "suggested_quantity": suggested_qty,
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
):

    # =====================================================
    # RESOLVE ACTIVE SYMBOL
    # =====================================================

    active_symbol = None

    if trade_symbol:

        active_symbol = str(
            trade_symbol
        ).strip().upper()

    if not active_symbol:

        session_futures = st.session_state.get(
            "futures_symbol"
        )

        if session_futures:

            active_symbol = str(
                session_futures
            ).strip().upper()

    if not active_symbol:

        session_trade = st.session_state.get(
            "trade_symbol"
        )

        if session_trade:

            active_symbol = str(
                session_trade
            ).strip().upper()

    if (
        str(
            market_type or ""
        ).strip().upper()
        == "FUTURES"
    ):

        futures_symbol = st.session_state.get(
            "futures_symbol"
        )

        if futures_symbol:

            active_symbol = str(
                futures_symbol
            ).strip().upper()

    if not active_symbol:

        active_symbol = str(
            symbol or "^NSEI"
        ).strip().upper()

    # =====================================================
    # SESSION SYNC
    # =====================================================

    st.session_state[
        "trade_symbol"
    ] = active_symbol

    if (
        str(
            market_type or ""
        ).strip().upper()
        == "FUTURES"
    ):

        st.session_state[
            "futures_symbol"
        ] = active_symbol

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
            "🟢 DELTA EXCHANGE • MARKET OPEN 24/7"
        )

        st.caption(
            f"Trading Symbol: {active_symbol} | "
            "Crypto Futures • No daily market close"
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
        "📝 Enable Paper Trading (Virtual Buy/Sell)",
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
    # RISK MANAGER
    # =====================================================

    risk_manager(
        trader=trader,
        display_price=display_price,
        is_delta=is_delta,
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
    )

    st.divider()

    # =====================================================
    # LAST REFRESH
    # =====================================================

    st.caption(
        "Last Refresh: "
        + datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    )