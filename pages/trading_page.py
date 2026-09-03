import streamlit as st
import pandas as pd
from datetime import datetime
import os
import logging

from signals import get_signals
from settings_manager import load_settings, save_settings
from paper_trading import PaperTrader

from auto_mode import is_enabled
from auto_trader import place_trade


SETTINGS_FILE = "settings.json"
TRADE_FILE = "paper_trades.csv"


# =========================================================
# PAPER / LIVE TRADE HISTORY
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

    try:

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

        return True

    except Exception as e:

        st.error(
            f"❌ Trade history save error: {e}"
        )

        return False


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

        # -------------------------------------------------
        # SIGNAL
        # -------------------------------------------------

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

        # -------------------------------------------------
        # CONFIDENCE
        # -------------------------------------------------

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

        side = str(side).upper()

        if side == "BUY":

            return (
                exit_price - entry
            ) * quantity

        if side == "SELL":

            return (
                entry - exit_price
            ) * quantity

        return 0.0

    except Exception:

        return 0.0
# =========================================================
# AUTO EXIT CSV SYNC
# =========================================================

def sync_auto_exit_to_paper_trades(
    position,
    exit_price
):
    """
    Sync PaperTrader auto-exit with paper_trades.csv.
    Finds the matching OPEN trade and marks it CLOSED.
    """

    try:

        if not position:
            return False

        trades = load_trades()

        if trades.empty:
            return False

        symbol = str(
            position.get("symbol", "")
        )

        side = str(
            position.get("side", "")
        ).upper()

        entry = float(
            position.get("entry", 0)
        )

        qty = int(
            position.get("qty", 0)
        )

        exit_price = float(exit_price)

        # Find matching OPEN trade
        matching = trades[
            (trades["Status"].astype(str).str.upper() == "OPEN")
            & (trades["Symbol"].astype(str) == symbol)
            & (trades["Side"].astype(str).str.upper() == side)
        ]

        if matching.empty:
            return False

        # Match entry
        matching = matching[
            pd.to_numeric(
                matching["Entry"],
                errors="coerce"
            ).round(4) == round(entry, 4)
        ]

        # Match quantity
        matching = matching[
            pd.to_numeric(
                matching["Quantity"],
                errors="coerce"
            ).fillna(0).astype(int) == qty
        ]

        if matching.empty:
            return False

        # Latest matching OPEN trade
        row_index = matching.index[-1]

        pnl = calculate_pnl(
            side,
            entry,
            exit_price,
            qty
        )

        # Update CSV row
        trades.at[row_index, "Status"] = "CLOSED"
        trades.at[row_index, "Exit"] = exit_price
        trades.at[row_index, "P&L"] = pnl

        # Save current active SL
        if "stoploss" in position:

            trades.at[row_index, "Stoploss"] = float(
                position["stoploss"]
            )

        trades.to_csv(
            TRADE_FILE,
            index=False
        )

        return True

    except Exception as e:

        logging.error(
            f"Auto exit CSV sync error: {e}"
        )

        return False

# =========================================================
# TRADING PAGE
# =========================================================

def trading_page(
    trader=None,
    symbol=None
):

    settings = load_settings()

    # =====================================================
    # PAPER TRADER CONNECTION
    # =====================================================

    if trader is None:

        if "trader" not in st.session_state:

            st.session_state.trader = PaperTrader(
                initial_balance=100000
            )

        trader = st.session_state.trader

    # =====================================================
    # TRADING MODE
    # =====================================================

    # Sidebar auto_mode.py is the single source of truth.
    #
    # AUTO_TRADING = False
    #     -> PAPER TRADING
    #
    # AUTO_TRADING = True
    #     -> LIVE TRADING
    # =====================================================

    live_trading = is_enabled()

    paper_trade = not live_trading

    auto_trade = live_trading

    # =====================================================
    # SETTINGS
    # =====================================================

    ai_mode = settings.get(
        "ai_mode",
        "Balanced"
    )

    try:

        confidence_limit = int(
            settings.get(
                "confidence",
                70
            )
        )

    except Exception:

        confidence_limit = 70

    timeframe = settings.get(
        "timeframe",
        "5m"
    )

    try:

        target_points = float(
            settings.get(
                "default_target",
                40
            )
        )

    except Exception:

        target_points = 40.0

    try:

        stoploss_points = float(
            settings.get(
                "default_stoploss",
                20
            )
        )

    except Exception:

        stoploss_points = 20.0

    try:

        max_trades = int(
            settings.get(
                "max_trades",
                5
            )
        )

    except Exception:

        max_trades = 5

    # =====================================================
    # TRAILING STOPLOSS SETTINGS
    # =====================================================

    trailing_enabled = settings.get(
        "trailing_enabled",
        False
    )

    try:

        trailing_start = float(
            settings.get(
                "trailing_start",
                10
            )
        )

    except Exception:

        trailing_start = 10.0

    try:

        trailing_distance = float(
            settings.get(
                "trailing_distance",
                5
            )
        )

    except Exception:

        trailing_distance = 5.0

    # =====================================================
    # TITLE
    # =====================================================

    st.title(
        "💰 SmartTrader AI Pro — Trading"
    )

    st.caption(
        "Paper + Live Trading Terminal"
    )

    # =====================================================
    # TOP STATUS
    # =====================================================

    col1, col2, col3, col4 = st.columns(4)

    with col1:

        st.metric(
            "Trading Mode",
            "🟢 PAPER"
            if paper_trade
            else "🔴 LIVE"
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
            "Execution",
            "PAPER"
            if paper_trade
            else "LIVE"
        )

    st.divider()

    # =====================================================
    # SAFETY STATUS
    # =====================================================

    if paper_trade:

        st.success(
            "🟢 PAPER TRADING ACTIVE"
        )

        st.caption(
            "Virtual orders only — "
            "no real broker order will be sent."
        )

    else:

        st.error(
            "🔴 LIVE AUTO TRADING ACTIVE"
        )

        st.warning(
            "⚠️ Real orders can be sent to Kotak Neo."
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

            price = result.get(
                "price",
                0
            )

            signal = result.get(
                "signal",
                "WAIT"
            )

            confidence = result.get(
                "confidence",
                0
            )

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

            # -------------------------------------------------
            # CONFIDENCE FILTER
            # -------------------------------------------------

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

        try:

            current_price = float(
                result.get(
                    "price",
                    0
                )
            )

        except Exception:

            current_price = 0.0

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

   # =========================================================
   # PAPER AUTO EXIT
   # =========================================================

    if (
        trader is not None
        and trader.position is not None
        and current_price > 0
    ):

        try:

            # Save position BEFORE auto_exit clears it
            position_before_exit = dict(
                trader.position
            )

            exit_result = trader.auto_exit(
                current_price
            )

            if exit_result:

                # Sync auto-exit with paper_trades.csv
                synced = sync_auto_exit_to_paper_trades(
                    position_before_exit,
                    current_price
                )

                if synced:

                    st.success(
                        f"🛑 Paper Position Auto Closed | "
                        f"Price: ₹{current_price:.2f}"
                    )

                else:

                    st.warning(
                        f"🛑 Paper Position Auto Closed | "
                        f"CSV Sync Not Found | "
                        f"Price: ₹{current_price:.2f}"
                    )

                st.rerun()

        except Exception as e:

            st.error(
                f"❌ Trailing/Auto Exit Error: {e}"
            )
            
    # =====================================================
    # TRADE SIDE
    # =====================================================

    trade_side = st.selectbox(
        "Trade Side",
        [
            "Auto Signal",
            "BUY",
            "SELL"
        ]
    )

    # =====================================================
    # QUANTITY
    # =====================================================

    quantity = st.number_input(
        "Quantity",
        min_value=1,
        value=1,
        step=1
    )

    # =====================================================
    # EXECUTION SIDE
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

    execution_side = str(
        execution_side
    ).upper()

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
            entry_price -
            stoploss_points,
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
    # RISK / REWARD
    # =====================================================

    risk = abs(
        entry_price -
        stoploss
    )

    reward = abs(
        target -
        entry_price
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
    # TRAILING STOPLOSS
    # =====================================================

    st.subheader(
        "🔒 Trailing Stoploss"
    )

    col1, col2, col3 = st.columns(3)

    with col1:

        trailing_enabled = st.checkbox(
            "Enable Trailing Stoploss",
            value=trailing_enabled
        )

    with col2:

        trailing_start = st.number_input(
            "Trailing Start (Points)",
            min_value=0.05,
            value=float(trailing_start),
            step=0.05
        )

    with col3:

        trailing_distance = st.number_input(
            "Trailing Distance (Points)",
            min_value=0.05,
            value=float(trailing_distance),
            step=0.05
        )

    if trailing_enabled:

        if trailing_distance >= trailing_start:

            st.error(
                "⚠️ Trailing Distance must be "
                "less than Trailing Start."
            )

        else:

            st.success(
                f"🟢 Trailing ON | "
                f"Start: +{trailing_start:.2f} | "
                f"Distance: {trailing_distance:.2f}"
            )

    else:

        st.info(
            "⚪ Trailing Stoploss is OFF"
        )

    # =====================================================
    # EXECUTION STATUS
    # =====================================================

    st.header("🚀 Execution")

    # -----------------------------------------------------
    # SHOW BUY / SELL BUTTONS
    # -----------------------------------------------------

    if execution_side == "BUY":

        st.success(
            "🟢 AI / Selected Side: BUY"
        )

    elif execution_side == "SELL":

        st.error(
            "🔴 AI / Selected Side: SELL"
        )

    else:

        st.warning(
            "⏳ AI Signal is currently WAIT"
        )

    st.caption(
        "Manual BUY/SELL buttons are available below."
    )

    # =====================================================
    # BUY / SELL BUTTONS
    # =====================================================

    buy_col, sell_col = st.columns(2)

    with buy_col:

        buy_clicked = st.button(
            "🟢 BUY",
            type="primary",
            use_container_width=True
        )

    with sell_col:

        sell_clicked = st.button(
            "🔴 SELL",
            use_container_width=True
        )

    # -----------------------------------------------------
    # DETERMINE CLICKED SIDE
    # -----------------------------------------------------

    clicked_side = None

    if buy_clicked:

        clicked_side = "BUY"

    elif sell_clicked:

        clicked_side = "SELL"

    # =====================================================
    # TRADE EXECUTION
    # =====================================================

    if clicked_side:

        # -------------------------------------------------
        # SAVE TRAILING SETTINGS
        # -------------------------------------------------

        save_settings({

            "trailing_enabled":
                bool(trailing_enabled),

            "trailing_start":
                float(trailing_start),

            "trailing_distance":
                float(trailing_distance)
        })

        # -------------------------------------------------
        # EXECUTION SIDE
        # -------------------------------------------------

        execution_side = clicked_side

        # -------------------------------------------------
        # CONFIDENCE CHECK
        #
        # Manual BUY/SELL is allowed.
        # Auto Signal confidence filter is NOT applied
        # because user explicitly clicked BUY or SELL.
        # -------------------------------------------------

        # -------------------------------------------------
        # ENTRY CHECK
        # -------------------------------------------------

        if entry_price <= 0:

            st.error(
                "❌ Invalid entry price."
            )

        # -------------------------------------------------
        # QUANTITY CHECK
        # -------------------------------------------------

        elif int(quantity) <= 0:

            st.error(
                "❌ Quantity must be greater than zero."
            )

        # -------------------------------------------------
        # RISK CHECK
        # -------------------------------------------------

        elif risk <= 0:

            st.error(
                "❌ Stoploss must be different "
                "from entry price."
            )

        # -------------------------------------------------
        # TARGET CHECK
        # -------------------------------------------------

        elif target <= 0:

            st.error(
                "❌ Target must be greater than zero."
            )

        # -------------------------------------------------
        # TRAILING CHECK
        # -------------------------------------------------

        elif (
            trailing_enabled
            and trailing_distance >= trailing_start
        ):

            st.error(
                "❌ Trailing Distance must be "
                "less than Trailing Start."
            )

        # =================================================
        # ALL VALIDATIONS PASSED
        # =================================================

        else:

            # -------------------------------------------------
            # DAILY TRADE LIMIT
            # -------------------------------------------------

            trades = load_trades()

            today = datetime.now().strftime(
                "%Y-%m-%d"
            )

            if not trades.empty:

                today_trades = trades[
                    trades["Time"]
                    .astype(str)
                    .str.startswith(today)
                ]

            else:

                today_trades = trades

            if len(today_trades) >= max_trades:

                st.error(
                    f"🚫 Daily trade limit reached: "
                    f"{max_trades}"
                )

            # =================================================
            # PAPER TRADING
            # =================================================

            elif paper_trade:

                try:

                    if execution_side == "BUY":

                        success, message = trader.buy(

                            symbol=selected_symbol,

                            price=float(
                                entry_price
                            ),

                            qty=int(
                                quantity
                            ),

                            target=float(
                                target
                            ),

                            stoploss=float(
                                stoploss
                            ),

                            trailing_enabled=bool(
                                trailing_enabled
                            ),

                            trailing_start=float(
                                trailing_start
                            ),

                            trailing_distance=float(
                                trailing_distance
                            )
                        )

                    else:

                        success, message = trader.short(

                            symbol=selected_symbol,

                            price=float(
                                entry_price
                            ),

                            qty=int(
                                quantity
                            ),

                            target=float(
                                target
                            ),

                            stoploss=float(
                                stoploss
                            ),

                            trailing_enabled=bool(
                                trailing_enabled
                            ),

                            trailing_start=float(
                                trailing_start
                            ),

                            trailing_distance=float(
                                trailing_distance
                            )
                        )

                except Exception as e:

                    success = False
                    message = str(e)

                # -------------------------------------------------
                # PAPER RESULT
                # -------------------------------------------------

                if success:

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
                            float(entry_price),

                        "Stoploss":
                            float(stoploss),

                        "Target":
                            float(target),

                        "Quantity":
                            int(quantity),

                        "Status":
                            "OPEN",

                        "Exit":
                            "",

                        "P&L":
                            0
                    }

                    save_trade(
                        trade
                    )

                    st.success(
                        f"✅ Paper Trade Opened: "
                        f"{execution_side} "
                        f"{selected_symbol} | "
                        f"Qty {quantity}"
                    )

                    st.rerun()

                else:

                    st.error(
                        f"❌ Paper Trade Failed: "
                        f"{message}"
                    )

            # =================================================
            # LIVE TRADING
            # =================================================

            else:

                # -------------------------------------------------
                # LIVE SAFETY CHECK
                # -------------------------------------------------

                if not is_enabled():

                    st.error(
                        "🔒 Live Trading is currently OFF. "
                        "Real order blocked."
                    )

                else:

                    st.warning(
                        "⚠️ Sending real order to Kotak Neo..."
                    )

                    with st.spinner(
                        "Connecting to Kotak Neo..."
                    ):

                        try:

                            live_result = place_trade(

                                action=
                                    execution_side,

                                symbol=
                                    selected_symbol,

                                qty=
                                    int(quantity),

                                # 0 = MARKET ORDER
                                price=0.0
                            )

                        except Exception as e:

                            live_result = {

                                "status":
                                    "error",

                                "message":
                                    str(e)
                            }

                    # -------------------------------------------------
                    # LIVE RESULT
                    # -------------------------------------------------

                    if (
                        isinstance(
                            live_result,
                            dict
                        )
                        and live_result.get(
                            "status"
                        ) == "success"
                    ):

                        st.success(
                            f"🔴 LIVE ORDER SUCCESSFULLY SENT\n\n"
                            f"{execution_side} | "
                            f"{selected_symbol} | "
                            f"Qty: {quantity}"
                        )

                        st.json(
                            live_result
                        )

                        # -------------------------------------------------
                        # SAVE LIVE EXECUTION
                        # -------------------------------------------------

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
                                float(entry_price),

                            "Stoploss":
                                float(stoploss),

                            "Target":
                                float(target),

                            "Quantity":
                                int(quantity),

                            "Status":
                                "LIVE_SENT",

                            "Exit":
                                "",

                            "P&L":
                                0
                        }

                        save_trade(
                            trade
                        )

                    else:

                        st.error(
                            "❌ LIVE ORDER FAILED"
                        )

                        st.json(
                            live_result
                        )


    st.divider()

    # =====================================================
    # OPEN POSITIONS
    # =====================================================

    st.header(
        "📌 Open Positions"
    )

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
                "No open paper positions."
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
                        trades.loc[
                            idx,
                            "Side"
                        ]
                    )

                    entry = float(
                        trades.loc[
                            idx,
                            "Entry"
                        ]
                    )

                    qty = int(
                        trades.loc[
                            idx,
                            "Quantity"
                        ]
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

    st.header(
        "📜 Trade History"
    )

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

    st.header(
        "📊 Trading Statistics"
    )

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

            total_pnl = 0.0
            winning = 0
            losing = 0
            win_rate = 0.0

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
