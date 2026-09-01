import streamlit as st
import pandas as pd
from datetime import datetime
import os

from signals import get_signals


SETTINGS_FILE = "settings.json"
TRADE_FILE = "paper_trades.csv"


# =========================================================
# SETTINGS
# =========================================================

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            import json

            with open(SETTINGS_FILE, "r") as f:
                data = json.load(f)

            return data if isinstance(data, dict) else {}

        except Exception:
            return {}

    return {}


# =========================================================
# PAPER TRADES
# =========================================================

def load_trades():

    columns = [
        "Time",
        "Symbol",
        "Side",
        "Entry",
        "Stoploss",
        "Target",
        "Quantity",
        "Status",
        "Exit",
        "P&L"
    ]

    if os.path.exists(TRADE_FILE):

        try:
            df = pd.read_csv(TRADE_FILE)

            for column in columns:
                if column not in df.columns:
                    df[column] = ""

            return df[columns]

        except Exception:
            pass

    return pd.DataFrame(columns=columns)


def save_trade(trade):

    df = load_trades()

    new_trade = pd.DataFrame([trade])

    df = pd.concat(
        [df, new_trade],
        ignore_index=True
    )

    df.to_csv(
        TRADE_FILE,
        index=False
    )


# =========================================================
# GET MARKET SIGNAL
# =========================================================

def get_market_signal(symbol):

    try:

        data = get_signals(symbol)

        if not isinstance(data, dict):
            return {
                "error": "Invalid signal response"
            }

        if "error" in data:
            return data

        price = float(
            data.get("Close", 0) or 0
        )

        # Try common signal field names
        signal = (
            data.get("signal")
            or data.get("Signal")
            or data.get("final_signal")
            or data.get("action")
            or "WAIT"
        )

        signal = str(signal).upper()

        if "BUY" in signal:
            signal = "BUY"

        elif "SELL" in signal:
            signal = "SELL"

        else:
            signal = "WAIT"

        # Try confidence fields
        confidence = (
            data.get("confidence")
            or data.get("Confidence")
            or data.get("ai_confidence")
            or 0
        )

        try:
            confidence = float(confidence)
        except Exception:
            confidence = 0

        return {
            "price": price,
            "signal": signal,
            "confidence": confidence,
            "raw": data
        }

    except Exception as e:

        return {
            "error": str(e)
        }


# =========================================================
# P&L CALCULATION
# =========================================================

def calculate_pnl(
    side,
    entry,
    exit_price,
    quantity
):

    try:

        entry = float(entry)
        exit_price = float(exit_price)
        quantity = int(quantity)

        if side == "BUY":

            return (
                exit_price - entry
            ) * quantity

        if side == "SELL":

            return (
                entry - exit_price
            ) * quantity

        return 0

    except Exception:

        return 0


# =========================================================
# TRADING PAGE
# =========================================================

def trading_page(
    trader=None,
    symbol=None
):

    settings = load_settings()

    # =====================================================
    # SETTINGS
    # =====================================================

    paper_trade = settings.get(
        "paper_trade",
        True
    )

    auto_trade = settings.get(
        "auto_trade",
        False
    )

    ai_mode = settings.get(
        "ai_mode",
        "Balanced"
    )

    confidence_limit = int(
        settings.get(
            "confidence",
            70
        )
    )

    timeframe = settings.get(
        "timeframe",
        "5m"
    )

    target_points = float(
        settings.get(
            "default_target",
            40
        )
    )

    stoploss_points = float(
        settings.get(
            "default_stoploss",
            20
        )
    )

    max_trades = int(
        settings.get(
            "max_trades",
            5
        )
    )

    # =====================================================
    # TITLE
    # =====================================================

    st.title(
        "💰 SmartTrader AI Pro — Trading"
    )

    st.caption(
        "Paper Trading Terminal"
    )

    # =====================================================
    # TOP STATUS
    # =====================================================

    col1, col2, col3, col4 = st.columns(4)

    with col1:

        st.metric(
            "Trading Mode",
            "PAPER" if paper_trade else "LIVE"
        )

    with col2:

        st.metric(
            "AI Mode",
            ai_mode
        )

    with col3:

        st.metric(
            "Timeframe",
            timeframe
        )

    with col4:

        st.metric(
            "Auto Trading",
            "ON" if auto_trade else "OFF"
        )

    st.divider()

    # =====================================================
    # SAFETY
    # =====================================================

    if paper_trade:

        st.success(
            "🟢 PAPER TRADING ACTIVE"
        )

    else:

        st.error(
            "🔴 LIVE MODE SELECTED"
        )

        st.warning(
            "Live order execution is disabled. "
            "No broker order will be sent."
        )

    # =====================================================
    # SYMBOL
    # =====================================================

    st.header("📊 Market")

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

    if symbol not in symbols:
        symbol = "^NSEI"

    selected_symbol = st.selectbox(
        "Trading Symbol",
        symbols,
        index=symbols.index(symbol)
    )

    # =====================================================
    # MARKET SIGNAL
    # =====================================================

    st.header("🤖 AI Market Signal")

    if st.button(
        "🔄 Refresh Signal",
        use_container_width=True
    ):

        with st.spinner(
            "Loading market signal..."
        ):

            result = get_market_signal(
                selected_symbol
            )

            st.session_state[
                "trading_signal"
            ] = result

    result = st.session_state.get(
        "trading_signal"
    )

    if result:

        if "error" in result:

            st.error(
                f"Market data error: "
                f"{result['error']}"
            )

        else:

            price = result["price"]
            signal = result["signal"]
            confidence = result["confidence"]

            col1, col2, col3 = st.columns(3)

            with col1:

                st.metric(
                    "Current Price",
                    f"₹{price:,.2f}"
                )

            with col2:

                st.metric(
                    "Signal",
                    signal
                )

            with col3:

                st.metric(
                    "Confidence",
                    f"{confidence:.0f}%"
                )

            if signal == "BUY":

                st.success(
                    f"🟢 BUY Signal — "
                    f"Confidence {confidence:.0f}%"
                )

            elif signal == "SELL":

                st.error(
                    f"🔴 SELL Signal — "
                    f"Confidence {confidence:.0f}%"
                )

            else:

                st.warning(
                    "⏳ WAIT — No confirmed trade"
                )

            # Confidence filter

            if confidence < confidence_limit:

                st.warning(
                    f"⚠️ Signal blocked: "
                    f"{confidence:.0f}% confidence "
                    f"is below required "
                    f"{confidence_limit}%."
                )

            else:

                st.success(
                    f"✅ Confidence filter passed "
                    f"({confidence:.0f}% ≥ "
                    f"{confidence_limit}%)"
                )

    else:

        st.info(
            "Click 'Refresh Signal' to get "
            "the latest market signal."
        )

    st.divider()

    # =====================================================
    # TRADE SETUP
    # =====================================================

    st.header("🎯 Trade Setup")

    current_price = 0.0

    if result and "error" not in result:

        current_price = float(
            result.get("price", 0)
        )

    entry_default = (
        current_price
        if current_price > 0
        else 100.0
    )

    entry_price = st.number_input(
        "Entry Price",
        min_value=0.0,
        value=float(entry_default),
        step=0.05
    )

    trade_side = st.selectbox(
        "Trade Side",
        [
            "Auto Signal",
            "BUY",
            "SELL"
        ]
    )

    quantity = st.number_input(
        "Quantity",
        min_value=1,
        value=1,
        step=1
    )

    # =====================================================
    # SIDE
    # =====================================================

    if trade_side == "Auto Signal":

        if result and "error" not in result:

            execution_side = result.get(
                "signal",
                "WAIT"
            )

        else:

            execution_side = "WAIT"

    else:

        execution_side = trade_side

    # =====================================================
    # SL / TARGET
    # =====================================================

    if execution_side == "BUY":

        default_sl = max(
            entry_price - stoploss_points,
            0
        )

        default_target = (
            entry_price +
            target_points
        )

    elif execution_side == "SELL":

        default_sl = (
            entry_price +
            stoploss_points
        )

        default_target = max(
            entry_price -
            target_points,
            0
        )

    else:

        default_sl = max(
            entry_price - stoploss_points,
            0
        )

        default_target = (
            entry_price +
            target_points
        )

    col1, col2 = st.columns(2)

    with col1:

        stoploss = st.number_input(
            "Stoploss",
            min_value=0.0,
            value=float(default_sl),
            step=0.05
        )

    with col2:

        target = st.number_input(
            "Target",
            min_value=0.0,
            value=float(default_target),
            step=0.05
        )

    # =====================================================
    # RISK REWARD
    # =====================================================

    risk = abs(
        entry_price - stoploss
    )

    reward = abs(
        target - entry_price
    )

    if risk > 0:

        rr = reward / risk

    else:

        rr = 0

    st.info(
        f"Risk: ₹{risk:.2f} | "
        f"Reward: ₹{reward:.2f} | "
        f"Risk/Reward: 1:{rr:.2f}"
    )

    # =====================================================
    # EXECUTION STATUS
    # =====================================================

    st.header("🚀 Execution")

    if execution_side == "BUY":

        st.success(
            "🟢 BUY selected"
        )

    elif execution_side == "SELL":

        st.error(
            "🔴 SELL selected"
        )

    else:

        st.warning(
            "⏳ WAIT — No valid trade"
        )

    # =====================================================
    # PAPER TRADE BUTTON
    # =====================================================

    if st.button(
        "🧪 Execute Paper Trade",
        type="primary",
        use_container_width=True
    ):

        # -------------------------------------------------
        # PAPER MODE CHECK
        # -------------------------------------------------

        if not paper_trade:

            st.error(
                "Paper Trading is OFF. "
                "Live execution is disabled."
            )

        # -------------------------------------------------
        # SIGNAL CHECK
        # -------------------------------------------------

        elif execution_side not in [
            "BUY",
            "SELL"
        ]:

            st.warning(
                "No valid BUY/SELL signal."
            )

        # -------------------------------------------------
        # CONFIDENCE CHECK
        # -------------------------------------------------

        elif (
            result
            and "error" not in result
            and result.get(
                "confidence",
                0
            ) < confidence_limit
            and trade_side == "Auto Signal"
        ):

            st.warning(
                "Trade blocked by AI confidence filter."
            )

        # -------------------------------------------------
        # ENTRY CHECK
        # -------------------------------------------------

        elif entry_price <= 0:

            st.error(
                "Invalid entry price."
            )

        # -------------------------------------------------
        # RISK CHECK
        # -------------------------------------------------

        elif risk <= 0:

            st.error(
                "Stoploss must be different "
                "from entry price."
            )

        # -------------------------------------------------
        # DAILY TRADE LIMIT
        # -------------------------------------------------

        else:

            trades = load_trades()

            today = datetime.now().strftime(
                "%Y-%m-%d"
            )

            today_trades = trades[
                trades["Time"].astype(str).str.startswith(
                    today
                )
            ]

            if len(today_trades) >= max_trades:

                st.error(
                    f"Daily trade limit reached: "
                    f"{max_trades}"
                )

            else:

                trade = {

                    "Time":
                        datetime.now().strftime(
                            "%Y-%m-%d %H:%M:%S"
                        ),

                    "Symbol":
                        selected_symbol,

                    "Side":
                        execution_side,

                    "Entry":
                        entry_price,

                    "Stoploss":
                        stoploss,

                    "Target":
                        target,

                    "Quantity":
                        quantity,

                    "Status":
                        "OPEN",

                    "Exit":
                        "",

                    "P&L":
                        0
                }

                save_trade(trade)

                st.success(
                    f"✅ Paper Trade Opened: "
                    f"{execution_side} "
                    f"{selected_symbol}"
                )

                st.rerun()

    st.divider()

    # =====================================================
    # OPEN POSITIONS
    # =====================================================

    st.header("📌 Open Positions")

    trades = load_trades()

    if not trades.empty:

        open_trades = trades[
            trades["Status"] == "OPEN"
        ].copy()

        if not open_trades.empty:

            st.dataframe(
                open_trades,
                use_container_width=True,
                hide_index=True
            )

        else:

            st.info(
                "No open positions."
            )

    else:

        st.info(
            "No paper trades yet."
        )

    # =====================================================
    # CLOSE PAPER TRADE
    # =====================================================

    if not trades.empty:

        open_trades = trades[
            trades["Status"] == "OPEN"
        ].copy()

        if not open_trades.empty:

            st.divider()

            st.header(
                "🛑 Close Paper Position"
            )

            position_index = st.selectbox(
                "Select Position",
                open_trades.index.tolist(),
                format_func=lambda x:
                    f"{open_trades.loc[x, 'Symbol']} "
                    f"{open_trades.loc[x, 'Side']} "
                    f"@ {open_trades.loc[x, 'Entry']}"
            )

            exit_price = st.number_input(
                "Exit Price",
                min_value=0.0,
                value=0.0,
                step=0.05
            )

            if st.button(
                "🛑 Close Position",
                use_container_width=True
            ):

                if exit_price <= 0:

                    st.error(
                        "Enter a valid exit price."
                    )

                else:

                    idx = position_index

                    side = str(
                        trades.loc[idx, "Side"]
                    )

                    entry = float(
                        trades.loc[idx, "Entry"]
                    )

                    qty = int(
                        trades.loc[idx, "Quantity"]
                    )

                    pnl = calculate_pnl(
                        side,
                        entry,
                        exit_price,
                        qty
                    )

                    trades.loc[
                        idx,
                        "Status"
                    ] = "CLOSED"

                    trades.loc[
                        idx,
                        "Exit"
                    ] = exit_price

                    trades.loc[
                        idx,
                        "P&L"
                    ] = pnl

                    trades.to_csv(
                        TRADE_FILE,
                        index=False
                    )

                    if pnl >= 0:

                        st.success(
                            f"✅ Position Closed — "
                            f"P&L ₹{pnl:.2f}"
                        )

                    else:

                        st.error(
                            f"❌ Position Closed — "
                            f"P&L ₹{pnl:.2f}"
                        )

                    st.rerun()

    st.divider()

    # =====================================================
    # TRADE HISTORY
    # =====================================================

    st.header("📜 Trade History")

    trades = load_trades()

    if not trades.empty:

        st.dataframe(
            trades.tail(20),
            use_container_width=True,
            hide_index=True
        )

    else:

        st.info(
            "Trade history is empty."
        )

    # =====================================================
    # STATISTICS
    # =====================================================

    st.header("📊 Trading Statistics")

    if not trades.empty:

        total_trades = len(trades)

        closed = trades[
            trades["Status"] == "CLOSED"
        ].copy()

        if not closed.empty:

            pnl = pd.to_numeric(
                closed["P&L"],
                errors="coerce"
            ).fillna(0)

            total_pnl = float(
                pnl.sum()
            )

            winning = int(
                (pnl > 0).sum()
            )

            losing = int(
                (pnl < 0).sum()
            )

            win_rate = (
                winning /
                len(closed) *
                100
            )

        else:

            total_pnl = 0
            winning = 0
            losing = 0
            win_rate = 0

        col1, col2, col3, col4 = st.columns(4)

        with col1:

            st.metric(
                "Total Trades",
                total_trades
            )

        with col2:

            st.metric(
                "Winning",
                winning
            )

        with col3:

            st.metric(
                "Losing",
                losing
            )

        with col4:

            st.metric(
                "Win Rate",
                f"{win_rate:.1f}%"
            )

        st.metric(
            "Total P&L",
            f"₹{total_pnl:.2f}"
        )

    else:

        st.info(
            "Statistics will appear after trades."
        )
