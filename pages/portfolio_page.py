import streamlit as st
import pandas as pd
from signals import get_signals
import plotly.express as px


# ============================================================
# Helper Functions
# ============================================================

def normalize_history(df):
    if df.empty:
        return df

    if "PnL" in df.columns and "PNL" not in df.columns:
        df = df.rename(columns={"PnL": "PNL"})

    if "PNL" in df.columns:
        df["PNL"] = pd.to_numeric(
            df["PNL"],
            errors="coerce"
        ).fillna(0)

    return df


def safe_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default

def get_option_ltp(trader, position):
    """
    Get the correct LTP for an OPTIONS position.

    IMPORTANT:
    Never use the underlying index/stock current_price as
    the option LTP.

    Priority:
    1. trader.price_by_option
    2. trader.option_prices
    3. trader.get_option_price(...)
    4. position-specific option LTP
    5. entry price

    For CE/PE positions, underlying NIFTY/BANKNIFTY spot
    must NEVER be used as the option LTP.
    """

    entry = safe_float(
        position.get("entry", 0)
    )

    option_mode = str(
        position.get(
            "option_mode",
            position.get(
                "option_type",
                ""
            )
        )
    ).upper().strip()

    # --------------------------------------------------------
    # 1. trader.price_by_option
    # --------------------------------------------------------
    price_by_option = getattr(
        trader,
        "price_by_option",
        None
    )

    if isinstance(price_by_option, dict):

        value = safe_float(
            price_by_option.get(
                option_mode,
                0
            )
        )

        if value > 0:
            return value

    # --------------------------------------------------------
    # 2. trader.option_prices
    # --------------------------------------------------------
    option_prices = getattr(
        trader,
        "option_prices",
        None
    )

    if isinstance(option_prices, dict):

        value = safe_float(
            option_prices.get(
                option_mode,
                0
            )
        )

        if value > 0:
            return value

    # --------------------------------------------------------
    # 3. Trader option-price method
    # --------------------------------------------------------
    get_price = getattr(
        trader,
        "get_option_price",
        None
    )

    if callable(get_price) and option_mode in (
        "CE",
        "PE",
    ):

        try:
            value = safe_float(
                get_price(option_mode)
            )

            if value > 0:
                return value

        except Exception:
            pass

    # --------------------------------------------------------
    # 4. Position-specific OPTION LTP
    # --------------------------------------------------------
    # Only use explicitly stored option LTP fields.
    # Do NOT use generic current_price/current because
    # those may contain the underlying index price.
    for key in (
        "option_ltp",
        "ltp",
        "LTP",
        "last_price",
        "last",
    ):
        value = safe_float(
            position.get(key, 0)
        )

        if value > 0:
            return value

    # --------------------------------------------------------
    # 5. Safe fallback
    # --------------------------------------------------------
    return entry

def get_active_positions(trader):
    """
    Return active positions in a normalized list.

    Supports:
    - trader.get_active_positions()
    - trader.active_positions
    - trader.positions
    - trader.position
    """

    # --------------------------------------------------------
    # 1. Method
    # --------------------------------------------------------
    getter = getattr(
        trader,
        "get_active_positions",
        None
    )

    if callable(getter):

        try:
            positions = getter()

            if positions:

                if isinstance(positions, dict):
                    return list(positions.values())

                if isinstance(positions, list):
                    return positions

        except Exception:
            pass

    # --------------------------------------------------------
    # 2. active_positions
    # --------------------------------------------------------
    positions = getattr(
        trader,
        "active_positions",
        None
    )

    if positions:

        if isinstance(positions, dict):
            return list(positions.values())

        if isinstance(positions, list):
            return positions

    # --------------------------------------------------------
    # 3. positions
    # --------------------------------------------------------
    positions = getattr(
        trader,
        "positions",
        None
    )

    if positions:

        if isinstance(positions, dict):
            return list(positions.values())

        if isinstance(positions, list):
            return positions

    # --------------------------------------------------------
    # 4. Legacy single position
    # --------------------------------------------------------
    position = getattr(
        trader,
        "position",
        None
    )

    if position:
        return [position]

    return []


# ============================================================
# Live Position
# ============================================================

def live_position(trader, symbol):

    st.header("📈 Live Position")

    positions = get_active_positions(trader)

    if not positions:
        st.info("No Open Position")
        return

    rows = []

    for position in positions:

        if not isinstance(position, dict):
            continue

        entry = safe_float(
            position.get("entry", 0)
        )

        qty = int(
            safe_float(
                position.get("qty", 0)
            )
        )

        position_symbol = position.get(
            "symbol",
            symbol
        )

        option_mode = str(
            position.get(
                "option_mode",
                position.get(
                    "option_type",
                    "N/A"
                )
            )
        ).upper()

        market_type = str(
            position.get(
                "market_type",
                ""
            )
        ).upper()

        # ----------------------------------------------------
        # OPTIONS
        # ----------------------------------------------------
        if (
            market_type == "OPTIONS"
            or option_mode in ("CE", "PE")
            or "CE" in str(position_symbol).upper()
            or "PE" in str(position_symbol).upper()
        ):

            current = get_option_ltp(
                trader,
                position
            )

        # ----------------------------------------------------
        # NON OPTIONS
        # ----------------------------------------------------
        else:

            try:

                sig = get_signals(
                    position_symbol
                )

                if (
                    isinstance(sig, dict)
                    and "error" not in sig
                ):

                    current = safe_float(
                        sig.get(
                            "Close",
                            entry
                        ),
                        entry
                    )

                else:
                    current = entry

            except Exception:
                current = entry

        target = safe_float(
            position.get(
                "target",
                entry + 40
            ),
            entry + 40
        )

        stoploss = safe_float(
            position.get(
                "stoploss",
                entry - 20
            ),
            entry - 20
        )

        pnl = round(
            (current - entry) * qty,
            2
        )

        rows.append(
            {
                "Symbol": position_symbol,
                "Option": option_mode,
                "Qty": qty,
                "Entry": entry,
                "LTP": current,
                "Target": target,
                "Stoploss": stoploss,
                "P&L": pnl,
            }
        )

    if not rows:
        st.info("No Open Position")
        return

    data = pd.DataFrame(rows)

    st.dataframe(
        data,
        use_container_width=True,
        hide_index=True,
    )

    total_pnl = round(
        data["P&L"].sum(),
        2
    )

    st.metric(
        "Total Open P&L",
        f"₹ {total_pnl:,.2f}"
    )


# ============================================================
# Holdings
# ============================================================

def holdings(trader):

    st.header("💼 Holdings")

    positions = get_active_positions(trader)

    if not positions:
        st.info("No Holdings")
        return

    rows = []

    for position in positions:

        if not isinstance(position, dict):
            continue

        rows.append(
            {
                "Symbol": position.get(
                    "symbol",
                    "-"
                ),
                "Option": position.get(
                    "option_mode",
                    position.get(
                        "option_type",
                        "N/A"
                    )
                ),
                "Qty": position.get(
                    "qty",
                    0
                ),
                "Entry": position.get(
                    "entry",
                    0.0
                ),
                "Target": position.get(
                    "target",
                    "-"
                ),
                "Stoploss": position.get(
                    "stoploss",
                    "-"
                ),
            }
        )

    if rows:
        st.dataframe(
            pd.DataFrame(rows),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No Holdings")


# ============================================================
# Order History
# ============================================================

def order_history():

    st.header("📜 Order History")

    try:

        history = pd.read_csv(
            "trade_history.csv"
        )

        history = normalize_history(
            history
        )

        cols = [
            "Date",
            "Symbol",
            "Action",
            "Entry",
            "Exit",
            "Qty",
            "PNL",
        ]

        available = [
            c for c in cols
            if c in history.columns
        ]

        if not history.empty and available:

            st.dataframe(
                history[available],
                use_container_width=True
            )

        else:
            st.info(
                "No Order History Found"
            )

    except Exception:
        st.info(
            "No Order History Found"
        )


# ============================================================
# Performance Summary
# ============================================================

def performance_summary():

    st.header("📊 Performance Summary")

    try:

        history = pd.read_csv(
            "trade_history.csv"
        )

        history = normalize_history(
            history
        )

        if (
            history.empty
            or "PNL" not in history.columns
        ):
            st.info(
                "No Performance Data Available"
            )
            return

        total = len(history)

        win = len(
            history[
                history["PNL"] > 0
            ]
        )

        loss = len(
            history[
                history["PNL"] < 0
            ]
        )

        net = history["PNL"].sum()

        win_rate = (
            round(
                (win / total) * 100,
                2
            )
            if total > 0
            else 0
        )

        c1, c2, c3, c4 = st.columns(4)

        c1.metric(
            "Trades",
            total
        )

        c2.metric(
            "Winning",
            win
        )

        c3.metric(
            "Losing",
            loss
        )

        c4.metric(
            "Win %",
            f"{win_rate}%"
        )

        st.metric(
            "Net Profit",
            f"₹ {net:.2f}"
        )

    except Exception:
        st.info(
            "No Performance Data"
        )


# ============================================================
# Monthly P&L
# ============================================================

def monthly_pnl():

    st.header("📅 Monthly P&L")

    try:

        history = pd.read_csv(
            "trade_history.csv"
        )

        history = normalize_history(
            history
        )

        date_col = (
            "Date"
            if "Date" in history.columns
            else (
                "Time"
                if "Time" in history.columns
                else None
            )
        )

        if (
            not date_col
            or "PNL" not in history.columns
            or history.empty
        ):
            st.info(
                "No Monthly P&L Data"
            )
            return

        history["ParsedDate"] = pd.to_datetime(
            history[date_col],
            errors="coerce"
        )

        history = history.dropna(
            subset=["ParsedDate"]
        )

        monthly = (
            history
            .groupby(
                history["ParsedDate"]
                .dt
                .strftime("%Y-%m")
            )["PNL"]
            .sum()
            .reset_index()
        )

        monthly.columns = [
            "Month",
            "PNL"
        ]

        st.dataframe(
            monthly,
            use_container_width=True
        )

        fig = px.bar(
            monthly,
            x="Month",
            y="PNL",
            title="Monthly Profit / Loss"
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    except Exception:
        st.info(
            "No Monthly P&L Data"
        )


# ============================================================
# Portfolio Allocation
# ============================================================

def portfolio_allocation(trader):

    st.header("🥧 Portfolio Allocation")

    positions = get_active_positions(
        trader
    )

    if not positions:

        st.info(
            "No Portfolio Allocation"
        )
        return

    assets = []
    values = []

    for position in positions:

        if not isinstance(position, dict):
            continue

        symbol = position.get(
            "symbol",
            "Position"
        )

        entry = safe_float(
            position.get(
                "entry",
                0
            )
        )

        qty = safe_float(
            position.get(
                "qty",
                0
            )
        )

        assets.append(
            symbol
        )

        values.append(
            entry * qty
        )

    balance = safe_float(
        getattr(
            trader,
            "balance",
            0
        )
    )

    if balance > 0:

        assets.append("Cash")
        values.append(balance)

    if not values:
        st.info(
            "No Portfolio Allocation"
        )
        return

    data = pd.DataFrame(
        {
            "Asset": assets,
            "Value": values,
        }
    )

    fig = px.pie(
        data,
        names="Asset",
        values="Value",
        hole=0.45,
        title="Portfolio Allocation"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )


# ============================================================
# Equity Curve
# ============================================================

def equity_curve():

    st.header("📈 Equity Curve")

    try:

        history = pd.read_csv(
            "trade_history.csv"
        )

        history = normalize_history(
            history
        )

        if (
            history.empty
            or "PNL" not in history.columns
        ):
            st.info(
                "No Equity Data Available"
            )
            return

        history["Equity"] = (
            history["PNL"].cumsum()
        )

        fig = px.line(
            history,
            y="Equity",
            title="Account Equity Curve"
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    except Exception:
        st.info(
            "No Equity Data"
        )


# ============================================================
# Best / Worst Trade
# ============================================================

def best_worst_trade():

    st.header("🏆 Best / Worst Trade")

    try:

        history = pd.read_csv(
            "trade_history.csv"
        )

        history = normalize_history(
            history
        )

        if (
            history.empty
            or "PNL" not in history.columns
        ):
            st.info(
                "No Trade Data Available"
            )
            return

        best = history.loc[
            history["PNL"].idxmax()
        ]

        worst = history.loc[
            history["PNL"].idxmin()
        ]

        c1, c2 = st.columns(2)

        with c1:

            st.success(
                "🏆 Best Trade"
            )

            st.write(
                f"**Symbol:** "
                f"{best.get('Symbol', '-')}"
            )

            st.write(
                f"**Action:** "
                f"{best.get('Action', '-')}"
            )

            st.write(
                f"**Entry:** "
                f"₹ {safe_float(best.get('Entry', 0)):.2f}"
            )

            st.write(
                f"**Exit:** "
                f"₹ {safe_float(best.get('Exit', 0)):.2f}"
            )

            st.metric(
                "Profit",
                f"₹ {safe_float(best.get('PNL', 0)):.2f}"
            )

        with c2:

            st.error(
                "💀 Worst Trade"
            )

            st.write(
                f"**Symbol:** "
                f"{worst.get('Symbol', '-')}"
            )

            st.write(
                f"**Action:** "
                f"{worst.get('Action', '-')}"
            )

            st.write(
                f"**Entry:** "
                f"₹ {safe_float(worst.get('Entry', 0)):.2f}"
            )

            st.write(
                f"**Exit:** "
                f"₹ {safe_float(worst.get('Exit', 0)):.2f}"
            )

            st.metric(
                "Loss",
                f"₹ {safe_float(worst.get('PNL', 0)):.2f}"
            )

    except Exception:
        st.info(
            "No Trade Data Available"
        )


# ============================================================
# Portfolio Health
# ============================================================

def portfolio_health(trader):

    st.header("🤖 AI Portfolio Health")

    score = 100

    positions = get_active_positions(
        trader
    )

    if positions:
        score -= 20

    balance = safe_float(
        getattr(
            trader,
            "balance",
            0
        )
    )

    if balance < 50000:
        score -= 20

    if score >= 80:
        status = "🟢 SAFE"

    elif score >= 60:
        status = "🟡 MODERATE"

    else:
        status = "🔴 RISKY"

    st.progress(
        score / 100
    )

    c1, c2 = st.columns(2)

    c1.metric(
        "Health Score",
        f"{score}%"
    )

    c2.metric(
        "Status",
        status
    )


# ============================================================
# Portfolio Page
# ============================================================

def portfolio_page(trader, symbol):

    st.title("📦 Portfolio")

    live_position(
        trader,
        symbol
    )

    st.divider()

    holdings(
        trader
    )

    st.divider()

    order_history()

    st.divider()

    performance_summary()

    st.divider()

    monthly_pnl()

    st.divider()

    portfolio_allocation(
        trader
    )

    st.divider()

    equity_curve()

    st.divider()

    best_worst_trade()

    st.divider()

    portfolio_health(
        trader
    )