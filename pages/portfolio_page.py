import streamlit as st
import pandas as pd
from signals import get_signals
import plotly.express as px

# Helper function to normalize DataFrame columns
def normalize_history(df):
    if df.empty:
        return df
    if "PnL" in df.columns and "PNL" not in df.columns:
        df = df.rename(columns={"PnL": "PNL"})
    if "PNL" in df.columns:
        df["PNL"] = pd.to_numeric(df["PNL"], errors="coerce").fillna(0)
    return df

# =========================
# Live Position
# =========================
def live_position(trader, symbol):
    st.header("📈 Live Position")

    if hasattr(trader, "position") and trader.position:
        entry = trader.position.get("entry", 0.0)
        qty = trader.position.get("qty", 0)

        try:
            sig = get_signals(symbol)
            current = sig.get("Close", entry) if isinstance(sig, dict) and "error" not in sig else entry
        except Exception:
            current = entry

        target = trader.position.get("target", entry + 40)
        stoploss = trader.position.get("stoploss", entry - 20)
        pnl = round((current - entry) * qty, 2)

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Entry", f"₹ {entry:.2f}")
        c2.metric("Current", f"₹ {current:.2f}")
        c3.metric("Target", f"₹ {target:.2f}")
        c4.metric("Stoploss", f"₹ {stoploss:.2f}")
        c5.metric("P&L", f"₹ {pnl:.2f}")

    else:
        st.info("No Open Position")


# =========================
# Holdings
# =========================
def holdings(trader):
    st.header("💼 Holdings")

    if hasattr(trader, "position") and trader.position:
        data = pd.DataFrame([
            {
                "Symbol": trader.position.get("symbol", "-"),
                "Qty": trader.position.get("qty", 0),
                "Entry": trader.position.get("entry", 0.0),
                "Target": trader.position.get("target", "-"),
                "Stoploss": trader.position.get("stoploss", "-")
            }
        ])

        st.dataframe(data, use_container_width=True)
    else:
        st.info("No Holdings")


# =========================
# Order History
# =========================
def order_history():
    st.header("📜 Order History")

    try:
        history = pd.read_csv("trade_history.csv")
        history = normalize_history(history)
        cols = ["Date", "Symbol", "Action", "Entry", "Exit", "Qty", "PNL"]
        available = [c for c in cols if c in history.columns]

        if not history.empty and available:
            st.dataframe(history[available], use_container_width=True)
        else:
            st.info("No Order History Found")
    except Exception:
        st.info("No Order History Found")


# =========================
# Performance Summary
# =========================
def performance_summary():
    st.header("📊 Performance Summary")

    try:
        history = pd.read_csv("trade_history.csv")
        history = normalize_history(history)

        if history.empty or "PNL" not in history.columns:
            st.info("No Performance Data Available")
            return

        total = len(history)
        win = len(history[history["PNL"] > 0])
        loss = len(history[history["PNL"] < 0])
        net = history["PNL"].sum()
        win_rate = round((win / total) * 100, 2) if total > 0 else 0

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Trades", total)
        c2.metric("Winning", win)
        c3.metric("Losing", loss)
        c4.metric("Win %", f"{win_rate}%")

        st.metric("Net Profit", f"₹ {net:.2f}")

    except Exception:
        st.info("No Performance Data")


# =========================
# Monthly P&L
# =========================
def monthly_pnl():
    st.header("📅 Monthly P&L")

    try:
        history = pd.read_csv("trade_history.csv")
        history = normalize_history(history)

        date_col = "Date" if "Date" in history.columns else ("Time" if "Time" in history.columns else None)
        if not date_col or "PNL" not in history.columns or history.empty:
            st.info("No Monthly P&L Data")
            return

        history["ParsedDate"] = pd.to_datetime(history[date_col], errors="coerce")
        history = history.dropna(subset=["ParsedDate"])

        monthly = (
            history.groupby(history["ParsedDate"].dt.strftime("%Y-%m"))["PNL"]
            .sum()
            .reset_index()
        )
        monthly.columns = ["Month", "PNL"]

        st.dataframe(monthly, use_container_width=True)

        fig = px.bar(monthly, x="Month", y="PNL", title="Monthly Profit / Loss")
        st.plotly_chart(fig, use_container_width=True)

    except Exception:
        st.info("No Monthly P&L Data")


# =========================
# Portfolio Allocation
# =========================
def portfolio_allocation(trader):
    st.header("🥧 Portfolio Allocation")

    if hasattr(trader, "position") and trader.position:
        data = pd.DataFrame({
            "Asset": [trader.position.get("symbol", "Stock"), "Cash"],
            "Value": [
                trader.position.get("entry", 0) * trader.position.get("qty", 0),
                getattr(trader, "balance", 0)
            ]
        })

        fig = px.pie(data, names="Asset", values="Value", hole=0.45, title="Portfolio Allocation")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No Portfolio Allocation")


# =========================
# Equity Curve
# =========================
def equity_curve():
    st.header("📈 Equity Curve")

    try:
        history = pd.read_csv("trade_history.csv")
        history = normalize_history(history)

        if history.empty or "PNL" not in history.columns:
            st.info("No Equity Data Available")
            return

        history["Equity"] = history["PNL"].cumsum()
        fig = px.line(history, y="Equity", title="Account Equity Curve")
        st.plotly_chart(fig, use_container_width=True)

    except Exception:
        st.info("No Equity Data")


# =========================
# Best / Worst Trade
# =========================
def best_worst_trade():
    st.header("🏆 Best / Worst Trade")

    try:
        history = pd.read_csv("trade_history.csv")
        history = normalize_history(history)

        if history.empty or "PNL" not in history.columns:
            st.info("No Trade Data Available")
            return

        best = history.loc[history["PNL"].idxmax()]
        worst = history.loc[history["PNL"].idxmin()]

        c1, c2 = st.columns(2)

        with c1:
            st.success("🏆 Best Trade")
            st.write(f"**Symbol:** {best.get('Symbol', '-')}")
            st.write(f"**Action:** {best.get('Action', '-')}")
            st.write(f"**Entry:** ₹ {best.get('Entry', 0):.2f}" if isinstance(best.get('Entry'), (int, float)) else f"**Entry:** {best.get('Entry')}")
            st.write(f"**Exit:** ₹ {best.get('Exit', 0):.2f}" if isinstance(best.get('Exit'), (int, float)) else f"**Exit:** {best.get('Exit')}")
            st.metric("Profit", f"₹ {best.get('PNL', 0):.2f}")

        with c2:
            st.error("💀 Worst Trade")
            st.write(f"**Symbol:** {worst.get('Symbol', '-')}")
            st.write(f"**Action:** {worst.get('Action', '-')}")
            st.write(f"**Entry:** ₹ {worst.get('Entry', 0):.2f}" if isinstance(worst.get('Entry'), (int, float)) else f"**Entry:** {worst.get('Entry')}")
            st.write(f"**Exit:** ₹ {worst.get('Exit', 0):.2f}" if isinstance(worst.get('Exit'), (int, float)) else f"**Exit:** {worst.get('Exit')}")
            st.metric("Loss", f"₹ {worst.get('PNL', 0):.2f}")

    except Exception:
        st.info("No Trade Data Available")


# =========================
# Portfolio Health
# =========================
def portfolio_health(trader):
    st.header("🤖 AI Portfolio Health")

    score = 100
    if hasattr(trader, "position") and trader.position:
        score -= 20

    balance = getattr(trader, "balance", 0)
    if balance < 50000:
        score -= 20

    if score >= 80:
        status = "🟢 SAFE"
    elif score >= 60:
        status = "🟡 MODERATE"
    else:
        status = "🔴 RISKY"

    st.progress(score / 100)

    c1, c2 = st.columns(2)
    c1.metric("Health Score", f"{score}%")
    c2.metric("Status", status)


# =========================
# Portfolio Page
# =========================
def portfolio_page(trader, symbol):
    st.title("📦 Portfolio")

    live_position(trader, symbol)
    st.divider()

    holdings(trader)
    st.divider()

    order_history()
    st.divider()

    performance_summary()
    st.divider()

    monthly_pnl()
    st.divider()

    portfolio_allocation(trader)
    st.divider()

    equity_curve()
    st.divider()

    best_worst_trade()
    st.divider()

    portfolio_health(trader)