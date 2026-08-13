import streamlit as st
import pandas as pd
from signals import get_signals
import plotly.express as px



# =========================
# Live Position
# =========================
def live_position(trader, symbol):

    st.header("📈 Live Position")

    if trader.position:

        entry = trader.position["entry"]
        qty = trader.position["qty"]

        try:
            current = get_signals(symbol)["Close"]
        except:
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

    if trader.position:

        data = pd.DataFrame([
            {
                "Symbol": trader.position["symbol"],
                "Qty": trader.position["qty"],
                "Entry": trader.position["entry"],
                "Target": trader.position.get("target", "-"),
                "Stoploss": trader.position.get("stoploss", "-")
            }
        ])

        st.dataframe(
            data,
            use_container_width=True
        )

    else:

        st.info("No Holdings")


# =========================
# Order History
# =========================
def order_history():

    st.header("📜 Order History")

    try:

        history = pd.read_csv("trade_history.csv")

        cols = [
            "Date",
            "Symbol",
            "Action",
            "Entry",
            "Exit",
            "Qty",
            "PNL"
        ]

        available = [c for c in cols if c in history.columns]

        st.dataframe(
            history[available],
            use_container_width=True
        )

    except:

        st.info("No Order History Found")


# =========================
# Portfolio Page
# =========================

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

    portfolio_allocation(trader)

    st.divider()

    equity_curve()

    st.divider()

    best_worst_trade()

    st.divider()

    portfolio_health(trader)

    st.divider()

def performance_summary():

    st.header("📊 Performance Summary")

    try:

        history = pd.read_csv("trade_history.csv")

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

        st.metric(
            "Net Profit",
            f"₹ {net:.2f}"
        )

    except:

        st.info("No Performance Data")

def monthly_pnl():

    st.header("📅 Monthly P&L")

    try:

        history = pd.read_csv("trade_history.csv")

        history["Date"] = pd.to_datetime(
            history["Date"],
            errors="coerce"
        )

        monthly = (
            history.groupby(
                history["Date"].dt.strftime("%Y-%m")
            )["PNL"]
            .sum()
            .reset_index()
        )

        monthly.columns = ["Month", "PNL"]

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

    except:

        st.info("No Monthly P&L Data")

def portfolio_allocation(trader):

    st.header("🥧 Portfolio Allocation")

    if trader.position:

        data = pd.DataFrame({

            "Asset": [trader.position["symbol"], "Cash"],

            "Value": [

                trader.position["entry"] * trader.position["qty"],

                trader.balance

            ]
        })

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

    else:

        st.info("No Portfolio Allocation")

def equity_curve():

    st.header("📈 Equity Curve")

    try:

        history = pd.read_csv("trade_history.csv")

        history["Equity"] = history["PNL"].cumsum()

        fig = px.line(

            history,

            y="Equity",

            title="Account Equity Curve"

        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    except:

        st.info("No Equity Data")


def best_worst_trade():

    st.header("🏆 Best / Worst Trade")

    try:

        history = pd.read_csv("trade_history.csv")

        if history.empty:
            st.info("No Trade Data")
            return

        if "PNL" not in history.columns:
            st.error("PNL column not found")
            return

        best = history.loc[history["PNL"].idxmax()]
        worst = history.loc[history["PNL"].idxmin()]

        c1, c2 = st.columns(2)

        with c1:

            st.success("🏆 Best Trade")

            st.write(f"**Symbol:** {best['Symbol']}")
            st.write(f"**Action:** {best['Action']}")
            st.write(f"**Entry:** ₹ {best['Entry']:.2f}")
            st.write(f"**Exit:** ₹ {best['Exit']:.2f}")
            st.metric("Profit", f"₹ {best['PNL']:.2f}")

        with c2:

            st.error("💀 Worst Trade")

            st.write(f"**Symbol:** {worst['Symbol']}")
            st.write(f"**Action:** {worst['Action']}")
            st.write(f"**Entry:** ₹ {worst['Entry']:.2f}")
            st.write(f"**Exit:** ₹ {worst['Exit']:.2f}")
            st.metric("Loss", f"₹ {worst['PNL']:.2f}")

    except Exception as e:

        st.info("No Trade Data")

def portfolio_health(trader):

    st.header("🤖 AI Portfolio Health")

    score = 100

    if trader.position:
        score -= 20

    if trader.balance < 50000:
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

