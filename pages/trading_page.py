import streamlit as st
import pandas as pd
from datetime import datetime
import os
import logging

from signals import get_signals
from settings_manager import load_settings, save_settings
from paper_trading import PaperTrader
from option_contracts import get_lot_size
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
        "Market",
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

    try:

        if not os.path.exists(TRADE_FILE):
            return pd.DataFrame(columns=columns)

        df = pd.read_csv(
            TRADE_FILE,
            dtype=str
        )

        # =================================================
        # ENSURE ALL REQUIRED COLUMNS
        # =================================================

        for column in columns:

            if column not in df.columns:
                df[column] = ""

        df = df[columns].copy()

        # =================================================
        # CLEAN TEXT COLUMNS
        # =================================================

        for column in [
            "Time",
            "Market",
            "Symbol",
            "Side",
            "Status"
        ]:

            df[column] = (
                df[column]
                .fillna("")
                .astype(str)
                .str.strip()
            )

        # =================================================
        # NORMALIZE SIDE / STATUS
        # =================================================

        df["Side"] = (
            df["Side"]
            .str.upper()
        )

        df["Status"] = (
            df["Status"]
            .str.upper()
        )

        # =================================================
        # MARKET NORMALIZATION
        # =================================================

        df["Market"] = (
            df["Market"]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.upper()
        )

        # Backward compatibility:
        # USD / USDT symbols = DELTA
        # Everything else = INDIA

        delta_mask = (
            df["Symbol"]
            .astype(str)
            .str.strip()
            .str.upper()
            .str.endswith(("USD", "USDT"))
        )

        df.loc[
            df["Market"].eq(""),
            "Market"
        ] = "INDIA"

        df.loc[
            delta_mask,
            "Market"
        ] = "DELTA"


        # =================================================
        # NUMERIC COLUMNS
        # =================================================

        numeric_columns = [
            "Entry",
            "Stoploss",
            "Target",
            "Quantity",
            "Exit",
            "P&L"
        ]

        for column in numeric_columns:

            df[column] = pd.to_numeric(
                df[column],
                errors="coerce"
            )

        # =================================================
        # OPEN TRADES
        # =================================================

        open_mask = (
            df["Status"]
            .eq("OPEN")
        )

        # OPEN trade ka Exit blank/NaN rahega
        df.loc[
            open_mask,
            "Exit"
        ] = float("nan")

        # OPEN trade ka P&L zero rahega
        df.loc[
            open_mask,
            "P&L"
        ] = 0.0

        # =================================================
        # CLOSED TRADES
        # =================================================

        closed_mask = (
            df["Status"]
            .eq("CLOSED")
        )

        for idx in df.index[closed_mask]:

            try:

                entry = float(
                    df.at[idx, "Entry"]
                )

                exit_price = float(
                    df.at[idx, "Exit"]
                )

                quantity = int(
                    float(
                        df.at[idx, "Quantity"]
                    )
                )

                side = str(
                    df.at[idx, "Side"]
                ).upper().strip()

                # Agar CLOSED trade ka P&L missing hai
                # to Entry/Exit se calculate karo.

                if (
                    pd.isna(
                        df.at[idx, "P&L"]
                    )
                    and
                    entry == entry
                    and
                    exit_price == exit_price
                    and
                    quantity > 0
                ):

                    pnl = calculate_pnl(
                        side,
                        entry,
                        exit_price,
                        quantity
                    )

                    df.at[
                        idx,
                        "P&L"
                    ] = float(pnl)

            except Exception:
                pass

        # =================================================
        # QUANTITY
        # =================================================

        df["Quantity"] = (
            pd.to_numeric(
                df["Quantity"],
                errors="coerce"
            )
            .fillna(0)
            .astype(int)
        )

        # =================================================
        # FINAL P&L CLEANUP
        # =================================================

        df["P&L"] = (
            pd.to_numeric(
                df["P&L"],
                errors="coerce"
            )
            .fillna(0.0)
        )

        return df

    except Exception as e:

        st.warning(
            f"Unable to load trade history: {e}"
        )

        return pd.DataFrame(
            columns=columns
        )

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
            f"Unable to save trade: {e}"
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

        # =================================================
        # PRICE
        # =================================================

        price = float(
            data.get("Close")
            or data.get("Price")
            or 0
        )

        # =================================================
        # SIGNAL
        # =================================================

        signal = (
            data.get("SIGNAL")
            or data.get("Signal")
            or data.get("signal")
            or data.get("final_signal")
            or data.get("action")
            or "WAIT"
        )

        signal = str(
            signal
        ).strip().upper()

        # -------------------------------------------------
        # IMPORTANT:
        # HOLD ko WAIT me convert nahi karna hai
        # -------------------------------------------------

        if signal in (
            "BUY",
            "STRONG BUY"
        ):

            signal = "BUY"

        elif signal in (
            "SELL",
            "STRONG SELL"
        ):

            signal = "SELL"

        elif signal in (
            "HOLD",
            "WAIT",
            "NEUTRAL"
        ):

            signal = "HOLD"

        else:

            signal = "WAIT"

        # =================================================
        # CONFIDENCE / SIGNAL STRENGTH
        # =================================================

        confidence = (
            data.get("Signal_Strength")
            if data.get("Signal_Strength") is not None
            else data.get("signal_strength")
        )

        # Fallback
        if confidence is None:

            confidence = (
                data.get("confidence")
                or data.get("Confidence")
                or data.get("ai_confidence")
                or 0
            )

        try:

            confidence = float(
                confidence
            )

        except Exception:

            confidence = 0.0

        # =================================================
        # MARKET TYPE
        # =================================================

        market_type = str(
            data.get("Market_Type")
            or ""
        ).strip().upper()

        # =================================================
        # DELTA DETECTION
        # =================================================

        is_delta = bool(
            data.get("Is_Delta")
            or market_type == "DELTA"
            or str(symbol).upper().endswith(
                ("USD", "USDT")
            )
        )

        # =================================================
        # FINAL RESULT
        # =================================================

        return {

            "price": price,

            "signal": signal,

            "confidence": confidence,

            "market_type": market_type,

            "is_delta": is_delta,

            "raw_data": data,

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

        side = str(side).upper().strip()

        if side == "BUY":

            return (
                exit_price - entry
            ) * quantity

        if side in {
            "SELL",
            "SHORT"
        }:

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
        ).strip()

        side = str(
            position.get("side", "")
        ).upper().strip()

        # =================================================
        # MARKET IDENTIFICATION
        # =================================================

        position_market = str(
            position.get("market", "")
        ).strip().upper()

        # Fallback for older positions
        if position_market not in (
            "INDIA",
            "DELTA"
        ):

            try:

                from paper_trading import PaperTrader

                position_market = (
                    PaperTrader.get_market_type(
                        symbol
                    )
                )

            except Exception:

                if symbol.upper().endswith(
                    ("USD", "USDT")
                ):
                    position_market = "DELTA"
                else:
                    position_market = "INDIA"

        # =================================================
        # POSITION SIDE -> TRADE SIDE
        # =================================================

        position_side = str(
            position.get(
                "position_side",
                position.get("side", "")
            )
        ).upper().strip()

        if position_side == "LONG":

            side = "BUY"

        elif position_side == "SHORT":

            side = "SELL"

        else:

            side = str(
                position.get("side", "")
            ).upper().strip()

        entry = float(
            position.get("entry", 0)
        )

        qty = int(
            position.get("qty", 0)
        )

        exit_price = float(
            exit_price
        )

        # =================================================
        # ENSURE MARKET COLUMN EXISTS
        # =================================================

        if "Market" not in trades.columns:

            trades["Market"] = (
                trades["Symbol"]
                .astype(str)
                .str.strip()
                .str.upper()
                .str.endswith(
                    ("USD", "USDT")
                )
            ).map({
                True: "DELTA",
                False: "INDIA"
            })

        else:

            trades["Market"] = (
            trades["Market"]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.upper()
        )

        # Recover missing Market values
        missing_market = (
            trades["Market"]
            .eq("")
        )

        if missing_market.any():

            trades.loc[
                missing_market,
                "Market"
            ] = (
                trades.loc[
                    missing_market,
                    "Symbol"
                ]
                .astype(str)
                .str.strip()
                .str.upper()
                .str.endswith(
                    ("USD", "USDT")
                )
                .map({
                    True: "DELTA",
                   False: "INDIA"
                })
            )


        # =================================================
        # FIND MATCHING OPEN TRADE
        # MARKET + SYMBOL + SIDE
        # =================================================

        matching = trades[
            (
                trades["Status"]
                .astype(str)
                .str.strip()
                .str.upper()
                .eq("OPEN")
            )
            &
            (
                trades["Market"]
                .astype(str)
                .str.strip()
                .str.upper()
                .eq(position_market)
            )
            &
            (
                trades["Symbol"]
                .astype(str)
                .str.strip()
                .str.upper()
                .eq(
                    symbol.strip().upper()
                )
            )
            &
            (
                trades["Side"]
                .astype(str)
                .str.strip()
                .str.upper()
                .eq(side)
            )
        ]

        if matching.empty:
            return False
        
        # -------------------------------------------------
        # MATCH ENTRY
        # -------------------------------------------------

        matching = matching[
            pd.to_numeric(
                matching["Entry"],
                errors="coerce"
            ).round(8)
            ==
            round(entry, 8)
        ]

        # -------------------------------------------------
        # MATCH QUANTITY
        # -------------------------------------------------

        matching = matching[
            pd.to_numeric(
                matching["Quantity"],
                errors="coerce"
            )
            .fillna(0)
            .astype(int)
            .eq(qty)
        ]

        if matching.empty:
            return False

        # Latest matching OPEN trade
        row_index = matching.index[-1]

        # -------------------------------------------------
        # CALCULATE P&L
        # -------------------------------------------------

        pnl = calculate_pnl(
            side,
            entry,
            exit_price,
            qty
        )

        # -------------------------------------------------
        # UPDATE TRADE
        # -------------------------------------------------

        trades.at[
            row_index,
            "Status"
        ] = "CLOSED"

        trades.at[
            row_index,
            "Exit"
        ] = exit_price

        trades.at[
            row_index,
            "P&L"
        ] = pnl

        # -------------------------------------------------
        # SAVE ACTIVE STOPLOSS
        # -------------------------------------------------

        if "stoploss" in position:

            try:

                trades.at[
                    row_index,
                    "Stoploss"
                ] = float(
                    position["stoploss"]
                )

            except Exception:
                pass

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
    symbol=None,
    default_quantity=1
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
        "Jha SmartTrader AI Pro"
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
            "PAPER TRADING ACTIVE"
        )

        st.caption(
            "Virtual orders only - Real orders can be sent to Kotak Neo."
        )


    else:

        st.error(
            "LIVE TRADING MODE - Orders may be sent to Kotak Neo."
        )







    # =====================================================

    st.header("Symbol / Market")

    # -----------------------------------------------------
    # READ MARKET FROM DASHBOARD SESSION STATE
    # -----------------------------------------------------

    market_type = st.session_state.get(
        "market_type",
        st.session_state.get(
            "selected_market",
            ""
        )
    )

    market_type = str(
        market_type or ""
    ).strip().upper()

    # -----------------------------------------------------
    # DELTA DETECTION
    # -----------------------------------------------------

    incoming_symbol = str(
        symbol or ""
    ).strip().upper()

    is_delta = (
        market_type in {
            "DELTA",
            "DELTA FUTURES",
            "DELTA_FUTURES",
            "FUTURES"
        }
        or incoming_symbol.endswith(
            ("USD", "USDT")
        )
    )

    # =====================================================
    # DELTA FUTURES
    # =====================================================

    if is_delta:

        delta_symbol = (
            incoming_symbol
            or str(
                st.session_state.get(
                    "selected_symbol",
                    ""
                )
            ).strip().upper()
            or str(
                st.session_state.get(
                    "symbol",
                    ""
                )
            ).strip().upper()
            or "BTCUSD"
        )

        # Old NSE symbol ko Delta me allow mat karo
        if delta_symbol in {
            "",
            "^NSEI",
            "^NSEBANK",
            "^BSESN"
        }:

            delta_symbol = (
                str(
                    st.session_state.get(
                        "selected_symbol",
                        "BTCUSD"
                    )
                )
                .strip()
                .upper()
            )

            if delta_symbol in {
                "",
                "^NSEI",
                "^NSEBANK",
                "^BSESN"
            }:

                delta_symbol = "BTCUSD"

        selected_symbol = st.text_input(
            "Trading Symbol",
            value=delta_symbol,
            key="delta_trading_symbol"
        ).strip().upper()

        if not selected_symbol:

            selected_symbol = delta_symbol

        st.success(
            f"DELTA FUTURES | {selected_symbol} | MARKET OPEN 24/7"
            f"{selected_symbol} | "
            f"MARKET OPEN 24/7"
        )

    # =====================================================
    # INDIAN MARKET
    # =====================================================

    else:

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

        incoming_indian_symbol = (
            incoming_symbol
            if incoming_symbol in symbols
            else "^NSEI"
        )

        selected_symbol = st.selectbox(
            "Trading Symbol",
            symbols,
            index=symbols.index(
                incoming_indian_symbol
            ),
            key="indian_trading_symbol"
        )

        st.caption(
            f"INDIAN MARKET | {selected_symbol}"
        )


    # =====================================================
    # INITIALIZE SIGNAL RESULT
    # =====================================================

    result = st.session_state.get(
        "trading_signal"
    )

    # =====================================================
    # MARKET SIGNAL
    # =====================================================


    if st.button(
        "Generate Market Signal",
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

    # -----------------------------------------------------
    # ALWAYS READ LATEST RESULT
    # -----------------------------------------------------

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

            price = float(
                result.get(
                    "price",
                    0
                ) or 0
            )

            signal = str(
                result.get(
                    "signal",
                    "WAIT"
                )
            ).upper()

            confidence = float(
                result.get(
                    "confidence",
                    0
                ) or 0
            )

            # -------------------------------------------------
            # SIGNAL METRICS
            # -------------------------------------------------

            col1, col2, col3 = st.columns(3)

            with col1:

                if is_delta:

                    st.metric(
                        "Current Price",
                        f"${price:,.8f}"
                    )

                else:

                    st.metric(
                        "Current Price",
                        f"\u20b9{price:,.2f}"
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

            # -------------------------------------------------
            # SIGNAL STATUS
            # -------------------------------------------------

            if signal == "BUY":

                st.success(
                    f"BUY Signal | Confidence {confidence:.0f}%"

                )

            elif signal == "SELL":

                st.error(
                    f"SELL Signal | Confidence {confidence:.0f}%"

                )

            else:

                st.warning(
                    "Signal blocked: market conditions do not meet the required criteria."
                )

            # -------------------------------------------------
            # CONFIDENCE FILTER
            # -------------------------------------------------

            if confidence < confidence_limit:

                st.warning(
                    f"Signal blocked: {confidence:.0f}% confidence is below required {confidence_limit}%."



                )

            else:

                st.success(
                    f"Confidence filter passed ({confidence:.0f}% >= {confidence_limit}%)"


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

    st.header("Trade Setup")

    current_price = 0.0

    # -----------------------------------------------------
    # PRIMARY PRICE
    # -----------------------------------------------------

    if result and "error" not in result:

        try:

            current_price = float(
                result.get("price")
                or result.get("Price")
                or result.get("Close")
                or 0
            )

        except Exception:

            current_price = 0.0


    # -----------------------------------------------------
    # DELTA PRICE FALLBACK
    # -----------------------------------------------------

    if is_delta and current_price <= 0:

        try:

            delta_symbol_for_price = str(
               selected_symbol
            ).strip().upper()

            delta_data = get_signals(
                delta_symbol_for_price
            )

            if isinstance(delta_data, dict):

                current_price = float(
                    delta_data.get("Close")
                    or delta_data.get("Price")
                    or 0
                )

        except Exception:

            current_price = 0.0


    # -----------------------------------------------------
    # FINAL PRICE VALIDATION
    # -----------------------------------------------------

    if current_price <= 0:

        st.warning(
            "Current market price unavailable."
        )

    # -----------------------------------------------------
    # ENTRY PRICE
    # -----------------------------------------------------

    entry_key = (
        f"trading_entry_price_"
        f"{str(selected_symbol).strip().upper()}"
    )

    # -----------------------------------------------------
    # DELTA = LIVE MARKET PRICE
    # -----------------------------------------------------

    if is_delta and current_price > 0:

        # Old Streamlit value such as 100.0 ko overwrite karo
        st.session_state[entry_key] = float(current_price)

        entry_default = float(current_price)

    else:

        entry_default = (
            float(current_price)
            if current_price > 0
            else 100.0
        )


    entry_price = st.number_input(
        "Entry Price",
        min_value=0.0,
        value=float(entry_default),
        step=(
            0.00000001
            if is_delta
           else 0.05
        ),
        format=(
            "%.8f"
            if is_delta
            else "%.2f"
        ),
        key=entry_key,
        disabled=is_delta
    )

    # -----------------------------------------------------
    # FINAL DELTA ENTRY VALIDATION
    # -----------------------------------------------------

    if is_delta and current_price > 0:

        entry_price = float(current_price)

        st.caption(
            f"Delta Entry = Live Market Price ${entry_price:.8f}"
        )

    # =====================================================
    # PAPER AUTO EXIT
    # =====================================================

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

                    if is_delta:

                        st.success(
                            f"Delta position synced | Exit Price ${entry_price:.8f}"
                            f"Price: ${current_price:.8f}"
                        )

                    else:

                        st.success(
                            f"Paper Position Auto Closed | Price: ${current_price:.8f}"

                        )

                else:

                    if is_delta:

                        st.warning(
                            f"Delta Paper Position Auto Closed | CSV Sync Not Found | Price: ${current_price:.8f}"


                        )

                    else:

                        st.warning(
                            "Delta Paper Position Auto Closed | CSV Sync Not Found"
                            f" | Price: ${current_price:.8f}"
                        )


                st.rerun()

        except Exception as e:

            st.error(
                f"Trading error: {e}"
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
        ],
        key="trading_trade_side"
    )

    # =====================================================
    # QUANTITY
    # =====================================================

    try:

        default_quantity = int(
            default_quantity
        )

    except Exception:

        default_quantity = 1

    if default_quantity < 1:

        default_quantity = 1

    quantity = st.number_input(
        "Quantity",
        min_value=1,
        value=default_quantity,
        step=default_quantity,
        key=f"trading_quantity_{selected_symbol}"
    )

    st.caption(
        f"Selected Symbol: {selected_symbol} | "
        f"Default Quantity: {default_quantity}"
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

    if is_delta:

        # -------------------------------------------------
        # DELTA FUTURES
        # Percentage-based SL / TARGET
        # -------------------------------------------------

        delta_sl_percent = 0.50
        delta_target_percent = 1.00

        if execution_side == "BUY":

            default_sl = (
                entry_price
                * (1.0 - delta_sl_percent / 100.0)
            )

            default_target = (
                entry_price
                * (1.0 + delta_target_percent / 100.0)
            )

        elif execution_side == "SELL":

            default_sl = (
                entry_price
                * (1.0 + delta_sl_percent / 100.0)
            )

            default_target = max(
                entry_price
                * (1.0 - delta_target_percent / 100.0),
                0.0
            )

        else:

            default_sl = (
                entry_price
                * (1.0 - delta_sl_percent / 100.0)
            )

            default_target = (
                entry_price
                * (1.0 + delta_target_percent / 100.0)
            )

    else:

        # -------------------------------------------------
        # INDIAN MARKET
        # Existing point-based logic
        # -------------------------------------------------

        if execution_side == "BUY":

            default_sl = max(
                entry_price - stoploss_points,
                0
            )

            default_target = (
                entry_price + target_points
            )

        elif execution_side == "SELL":

            default_sl = (
                entry_price + stoploss_points
            )

            default_target = max(
                entry_price - target_points,
                0
            )

        else:

            default_sl = max(
                entry_price - stoploss_points,
                0
            )

            default_target = (
                entry_price + target_points
            )

    price_step = (
        0.00000001
        if is_delta
        else 0.05
    )

    price_format = (
        "%.8f"
        if is_delta
        else "%.2f"
    )

    # =====================================================
    # SL / TARGET INPUT
    # =====================================================

    sl_key = (
        f"trading_stoploss_"
        f"{str(selected_symbol).strip().upper()}_"
        f"{execution_side}"
    )

    target_key = (
        f"trading_target_"
        f"{str(selected_symbol).strip().upper()}_"
        f"{execution_side}"
    )

    # -----------------------------------------------------
    # DELTA FUTURES
    # Percentage-based SL / TARGET
    # -----------------------------------------------------

    if is_delta and entry_price > 0:

        stoploss = float(default_sl)
        target = float(default_target)

    else:

        col1, col2 = st.columns(2)

        with col1:

            stoploss = st.number_input(
                "Stoploss",
                min_value=0.0,
                value=float(default_sl),
                step=price_step,
                format=price_format,
                key=sl_key
            )

        with col2:

            target = st.number_input(
                "Target",
                min_value=0.0,
                value=float(default_target),
                step=price_step,
                format=price_format,
                key=target_key
            )

    # -----------------------------------------------------
    # DELTA SL / TARGET DISPLAY
    # -----------------------------------------------------

    if is_delta:

        col1, col2 = st.columns(2)

        with col1:

            st.metric(
                "Stoploss",
                f"${stoploss:.8f}"
            )

        with col2:

            st.metric(
                "Target",
                f"${target:.8f}"
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

    if is_delta:

        st.info(
            f"Risk: ${risk:.8f} | "
            f"Reward: ${reward:.8f} | "
            f"Risk/Reward: 1:{rr:.2f}"
        )

    else:

        st.info(
            f"Risk: \u20b9{risk:.2f} | "
            f"Reward: \u20b9{reward:.2f} | "
            f"Risk/Reward: 1:{rr:.2f}"
        )

    # =====================================================
    # TRAILING STOPLOSS
    # =====================================================

    st.subheader(
        "Trailing Stoploss"
    )

    col1, col2, col3 = st.columns(3)

    with col1:

        trailing_enabled = st.checkbox(
            "Enable Trailing Stoploss",
            value=trailing_enabled,
            key="trading_trailing_enabled"
        )

    with col2:

        trailing_start = st.number_input(
            "Trailing Start (Points)",
            min_value=0.00000001,
            value=float(trailing_start),
            step=price_step,
            format=price_format,
            key="trading_trailing_start"
        )

    with col3:

        trailing_distance = st.number_input(
            "Trailing Distance (Points)",
            min_value=0.00000001,
            value=float(trailing_distance),
            step=price_step,
            format=price_format,
            key="trading_trailing_distance"
        )

    if trailing_enabled:

        if trailing_distance >= trailing_start:

            st.error(
                "Trailing stop cannot activate: current price is less than Trailing Start."
                "less than Trailing Start."
            )

        else:

            st.success(
                f"Trailing Stop ON | "
                f"Start: +{trailing_start:.8f} | "
                f"Distance: {trailing_distance:.8f}"
                if is_delta
                else
                f"Trailing Stop ON | "
                f"Start: +{trailing_start:.2f} | "
                f"Distance: {trailing_distance:.2f}"
            )

    else:

        st.info(
            "Trailing Stop is disabled."
        )

    # =====================================================
    # EXECUTION STATUS
    # =====================================================

    st.header("Trade Execution")

    if execution_side == "BUY":

        st.success(
            "BUY Signal - Ready to Execute"
        )

    elif execution_side == "SELL":

        st.error(
            "SELL Signal - Ready to Execute"
        )

    else:

        st.warning(
            "WAIT - No Trade Signal"
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
            "BUY",
            type="primary",
            use_container_width=True,
            key="trading_buy_button"
        )

    with sell_col:

        sell_clicked = st.button(
            "SELL",
            use_container_width=True,
            key="trading_sell_button"
        )

    # =====================================================
    # DETERMINE CLICKED SIDE
    # =====================================================

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
        # ENTRY CHECK
        # -------------------------------------------------

        if entry_price <= 0:

            st.error(
                "Entry price must be greater than 0."
            )

        # -------------------------------------------------
        # QUANTITY CHECK
        # -------------------------------------------------

        elif int(quantity) <= 0:

            st.error(
                "Quantity must be greater than 0."
            )

        # -------------------------------------------------
        # RISK CHECK
        # -------------------------------------------------

        elif risk <= 0:

            st.error(
                "Risk must be greater than 0 and less than the entry price."
                "from entry price."
            )

        # -------------------------------------------------
        # TARGET CHECK
        # -------------------------------------------------

        elif target <= 0:

            st.error(
                "Target must be greater than 0."
            )

        # -------------------------------------------------
        # TRAILING CHECK
        # -------------------------------------------------

        elif (
            trailing_enabled
            and trailing_distance >= trailing_start
        ):

            st.error(
                "Trailing distance must be less than Trailing Start."

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

            # -------------------------------------------------
            # MARKET-SPECIFIC DAILY TRADE LIMIT
            # INDIA and DELTA are counted independently.
            # -------------------------------------------------

            current_market = (
                "DELTA"
                if is_delta
                else "INDIA"
            )

            if not trades.empty:

                today_trades = trades[
                    trades["Time"]
                    .astype(str)
                    .str.startswith(today)
                ].copy()

                # Normalize Market column
                if "Market" not in today_trades.columns:

                    today_trades["Market"] = (
                        today_trades["Symbol"]
                        .astype(str)
                        .str.strip()
                        .str.upper()
                        .str.endswith(("USD", "USDT"))
                    ).map({
                        True: "DELTA",
                        False: "INDIA"
                    })

                else:

                    today_trades["Market"] = (
                        today_trades["Market"]
                        .fillna("")
                        .astype(str)
                        .str.strip()
                        .str.upper()
                    )

                    empty_market = today_trades["Market"].eq("")

                    today_trades.loc[empty_market, "Market"] = (
                        today_trades.loc[empty_market, "Symbol"]
                        .astype(str)
                        .str.strip()
                        .str.upper()
                        .str.endswith(("USD", "USDT"))
                    ).map({
                        True: "DELTA",
                        False: "INDIA"
                    })

                # Count only the current market
                today_market_trades = today_trades[
                    today_trades["Market"].eq(current_market)
                ]

            else:

                today_market_trades = trades

            if len(today_market_trades) >= max_trades:

                st.error(
                    f"Daily trade limit reached. Maximum allowed trades: "
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


                        "Market":
                            "DELTA" if is_delta else "INDIA",
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
                        f"Paper trade executed | "
                        f"{execution_side} "
                        f"{selected_symbol} | "
                        f"Qty {quantity}"
                    )

                    st.rerun()

                else:

                    st.error(
                        f"Paper trade failed | "
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
                        "Live trading is disabled. "
                        "Real order blocked."
                    )

                else:

                    st.warning(
                        "LIVE TRADING ENABLED - Real orders may be sent to Kotak Neo."
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
                            f"Live order placed | "
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

                            "Market":
                                "DELTA" if is_delta else "INDIA",

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
                            "Live order failed."
                        )

                        st.json(
                            live_result
                        )

    st.divider()

    # =====================================================
    # OPEN POSITIONS
    # =====================================================

    st.header(
        "Open Positions"
    )

    trades = load_trades()

    if not trades.empty:

        # =================================================
        # CURRENT SYMBOL
        # =================================================

        current_symbol = str(
            selected_symbol
        ).strip().upper()

        # =================================================
        # CURRENT SYMBOL OPEN POSITIONS
        # =================================================

        open_trades = trades[
            (
                trades["Status"]
                .astype(str)
                .str.strip()
                .str.upper()
                .eq("OPEN")
            )
            &
            (
                trades["Symbol"]
                .astype(str)
                .str.strip()
                .str.upper()
                .eq(current_symbol)
            )
        ].copy()

        if not open_trades.empty:

            st.dataframe(
                open_trades,
                use_container_width=True,
                hide_index=True
            )

        else:

            st.info(
                f"No open position for {current_symbol}."
            )

    else:

        st.info(
            "No paper trades yet."
        )
    # =====================================================
    # CLOSE PAPER TRADE
    # =====================================================

    if not trades.empty:

        # =================================================
        # CURRENT SYMBOL
        # =================================================

        current_symbol = str(
            selected_symbol
        ).strip().upper()

        # =================================================
        # CURRENT SYMBOL OPEN TRADES ONLY
        # =================================================

        open_trades = trades[
            (
                trades["Status"]
                .astype(str)
                .str.strip()
                .str.upper()
                .eq("OPEN")
            )
            &
            (
                trades["Symbol"]
                .astype(str)
                .str.strip()
                .str.upper()
                .eq(current_symbol)
            )
        ].copy()

        if not open_trades.empty:

            st.divider()

            st.header(
                "Close Paper Trade"
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

                step=price_step,

                format=price_format,

                key="manual_exit_price"
            )

            if st.button(
                "Close Position",
                use_container_width=True,
                key="close_paper_position"
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
                    ).strip().upper()

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

                    # =================================================
                    # CALCULATE P&L
                    # =================================================

                    pnl = calculate_pnl(
                        side,
                        entry,
                        exit_price,
                        qty
                    )

                    # =================================================
                    # CLOSE TRADE
                    # =================================================

                    trades.loc[
                        idx,
                        "Status"
                    ] = "CLOSED"

                    trades.loc[
                        idx,
                        "Exit"
                    ] = float(exit_price)

                    trades.loc[
                        idx,
                        "P&L"
                    ] = float(pnl)

                    # =================================================
                    # SAVE TRADE
                    # =================================================

                    trades.to_csv(
                        TRADE_FILE,
                        index=False
                    )

                    # =================================================
                    # RESULT
                    # =================================================

                    if is_delta:

                        if pnl >= 0:

                            st.success(
                                f"Trade closed | "
                                f"P&L ${pnl:.8f}"
                            )

                        else:

                            st.error(
                                f"Trade closed with loss | "
                                f"P&L ${pnl:.8f}"
                            )

                    else:

                        if pnl >= 0:

                            st.success(
                                f"Trade closed | "
                                f"P&L \u20b9{pnl:,.2f}"
                            )

                        else:

                            st.error(
                                f"Trade closed with loss | "
                                f"P&L \u20b9{pnl:,.2f}"
                            )

                    st.rerun()

    st.divider()

    # =====================================================
    # TRADE HISTORY
    # =====================================================

    st.header(
        "Trade History"
    )

    trades = load_trades()

    if not trades.empty:

        # =====================================================
        # CURRENT SYMBOL TRADE HISTORY ONLY
        # =====================================================

        current_symbol = str(
            selected_symbol
        ).strip().upper()

        history_trades = trades[
            trades["Symbol"]
            .astype(str)
            .str.strip()
            .str.upper()
            .eq(current_symbol)
        ].copy()

        if not history_trades.empty:

            st.dataframe(
                history_trades.tail(20),
                use_container_width=True,
                hide_index=True
            )

        else:

            st.info(
                f"No trade history for {current_symbol}."
            )

    else:

        st.info(
            "Trade history is empty."
        )
    # =====================================================
    # STATISTICS
    # =====================================================

    st.header(
        "Trading Statistics"
    )

    if not trades.empty:

        # =====================================================
        # CURRENT SYMBOL CLOSED TRADES ONLY
        # =====================================================

        current_symbol = str(
            selected_symbol
        ).strip().upper()

        closed = trades[
            (
               trades["Status"]
                .astype(str)
                .str.strip()
                .str.upper()
                .eq("CLOSED")
            )
            &
            (
                trades["Symbol"]
                .astype(str)
                .str.strip()
                .str.upper()
                .eq(current_symbol)
            )
        ].copy()
       
        total_trades = len(
            closed
                )

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

        if is_delta:

            st.metric(
                "Total P&L",
                f"${total_pnl:.8f}"
            )

        else:

            st.metric(
                "Total P&L",
                f"\u20b9{total_pnl:,.2f}"
            )

    else:

        st.info(
            "Statistics will appear after trades."
        )
