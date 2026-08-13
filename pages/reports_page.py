import streamlit as st
import pandas as pd
import plotly.express as px
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import tempfile


# ===================================
# PDF Export
# ===================================

def export_pdf(history):

    pdf_file = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".pdf"
    )

    c = canvas.Canvas(
        pdf_file.name,
        pagesize=letter
    )

    c.setFont("Helvetica-Bold", 16)
    c.drawString(
        50,
        780,
        "Jha SmartTrader AI Pro Report"
    )

    y = 740

    for _, row in history.iterrows():

        c.setFont("Helvetica", 10)

        text = (
            f"{row['Date']} | "
            f"{row['Symbol']} | "
            f"{row['Action']} | "
            f"Entry : {row['Entry']} | "
            f"Exit : {row['Exit']} | "
            f"PNL : {row['PNL']}"
        )

        c.drawString(
            40,
            y,
            text
        )

        y -= 18

        if y < 60:
            c.showPage()
            y = 760

    c.save()

    return pdf_file.name


# ===================================
# Reports Page
# ===================================

def reports_page():

    st.title("📄 Reports")

    st.info("Trading Reports")

    try:

        history = pd.read_csv("trade_history.csv")

        history["Date"] = pd.to_datetime(
            history["Date"],
            errors="coerce"
        )

        # ===================================
        # Trade History
        # ===================================

        st.subheader("📜 Trade History")

        st.dataframe(
            history,
            use_container_width=True
        )

        st.divider()

        # ===================================
        # Performance Summary
        # ===================================

        total = len(history)

        win = len(history[history["PNL"] > 0])

        loss = len(history[history["PNL"] < 0])

        net = history["PNL"].sum()

        win_rate = (
            round((win / total) * 100, 2)
            if total > 0
            else 0
        )

        st.subheader("📊 Performance Summary")

        c1, c2, c3, c4 = st.columns(4)

        c1.metric("Trades", total)
        c2.metric("Winning", win)
        c3.metric("Losing", loss)
        c4.metric("Win %", f"{win_rate}%")

        st.metric(
            "Net Profit",
            f"₹ {net:.2f}"
        )

        st.divider()

        # ===================================
        # Monthly P&L
        # ===================================

        st.subheader("📅 Monthly P&L")

        monthly = (
            history.groupby(
                history["Date"].dt.strftime("%Y-%m")
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

        st.divider()

        # ===================================
        # Equity Curve
        # ===================================

        st.subheader("📈 Equity Curve")

        history["Equity"] = history["PNL"].cumsum()

        fig = px.line(
            history,
            x="Date",
            y="Equity",
            title="Account Equity Curve",
            markers=True
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

        st.divider()

        # ===================================
        # Best & Worst Trade
        # ===================================

        st.subheader("🏆 Best & Worst Trade")

        best = history.loc[history["PNL"].idxmax()]
        worst = history.loc[history["PNL"].idxmin()]

        col1, col2 = st.columns(2)

        with col1:
            st.success("🏆 Best Trade")
            st.metric(
                best["Symbol"],
                f"₹ {best['PNL']:.2f}"
            )

        with col2:
            st.error("💀 Worst Trade")
            st.metric(
                worst["Symbol"],
                f"₹ {worst['PNL']:.2f}"
            )

        st.divider()

        # ===================================
        # Export Reports
        # ===================================

        st.subheader("📤 Export Reports")

        col1, col2 = st.columns(2)

        with col1:

            csv = history.to_csv(index=False).encode("utf-8")

            st.download_button(
                label="⬇ Download CSV",
                data=csv,
                file_name="trade_history.csv",
                mime="text/csv"
            )

        with col2:

            pdf_path = export_pdf(history)

            with open(pdf_path, "rb") as pdf:

                st.download_button(
                    label="📄 Download PDF",
                    data=pdf,
                    file_name="SmartTrader_Report.pdf",
                    mime="application/pdf"
                )

        st.divider()

        # ===================================
        # AI Performance Report
        # ===================================

        st.subheader("🤖 AI Performance Report")

        accuracy = round((win / total) * 100, 2) if total > 0 else 0
        risk = round((loss / total) * 100, 2) if total > 0 else 0

        if accuracy >= 80:
            rating = "⭐⭐⭐⭐⭐ Excellent"
        elif accuracy >= 70:
            rating = "⭐⭐⭐⭐ Very Good"
        elif accuracy >= 60:
            rating = "⭐⭐⭐ Good"
        elif accuracy >= 50:
            rating = "⭐⭐ Average"
        else:
            rating = "⭐ Needs Improvement"

        c1, c2, c3 = st.columns(3)

        c1.metric("AI Accuracy", f"{accuracy}%")
        c2.metric("Risk Score", f"{risk}%")
        c3.metric("Strategy Rating", rating)

        st.progress(accuracy / 100)

        st.divider()

        # ===================================
        # Trade Distribution
        # ===================================

        st.subheader("🥧 Trade Distribution")

        trade_data = pd.DataFrame({
            "Result": ["Winning", "Losing"],
            "Trades": [win, loss]
        })

        fig = px.pie(
            trade_data,
            names="Result",
            values="Trades",
            hole=0.45,
            title="Winning vs Losing Trades"
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )
        st.divider()

        # ===================================
        # Daily P&L
        # ===================================

        st.subheader("📆 Daily P&L")

        daily = (
            history.groupby(
                history["Date"].dt.strftime("%Y-%m-%d")
            )["PNL"]
            .sum()
            .reset_index()
        )

        daily.columns = ["Date", "PNL"]

        fig = px.line(
            daily,
            x="Date",
            y="PNL",
            markers=True,
            title="Daily Profit / Loss"
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

        st.divider()

        # ===================================
        # Advanced Trade Statistics
        # ===================================

        st.subheader("📊 Advanced Trade Statistics")

        avg_win = round(
            history[history["PNL"] > 0]["PNL"].mean(),
            2
        ) if win > 0 else 0

        avg_loss = round(
            history[history["PNL"] < 0]["PNL"].mean(),
            2
        ) if loss > 0 else 0

        profit_factor = round(
            history[history["PNL"] > 0]["PNL"].sum() /
            abs(history[history["PNL"] < 0]["PNL"].sum()),
            2
        ) if loss > 0 else 0

        c1, c2, c3 = st.columns(3)

        c1.metric(
            "💰 Avg Winning Trade",
            f"₹ {avg_win:.2f}"
        )

        c2.metric(
            "📉 Avg Losing Trade",
            f"₹ {avg_loss:.2f}"
        )

        c3.metric(
            "⚡ Profit Factor",
            profit_factor
        )

        st.divider()

        # ===================================
        # Max Drawdown
        # ===================================

        st.subheader("📉 Max Drawdown")

        equity = history["PNL"].cumsum()

        running_max = equity.cummax()

        drawdown = equity - running_max

        max_drawdown = round(drawdown.min(), 2)

        st.metric(
            "Maximum Drawdown",
            f"₹ {max_drawdown}"
        )

        fig = px.area(
            x=history["Date"],
            y=drawdown,
            title="Drawdown Curve"
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

        st.divider()

        # ===================================
        # Winning / Losing Streak
        # ===================================

        st.subheader("🏆 Winning / Losing Streak")

        streak = 0
        max_win = 0
        max_loss = 0

        for pnl in history["PNL"]:

            if pnl > 0:

                if streak >= 0:
                    streak += 1
                else:
                    streak = 1

                max_win = max(max_win, streak)

            elif pnl < 0:

                if streak <= 0:
                    streak -= 1
                else:
                    streak = -1

                max_loss = min(max_loss, streak)

        col1, col2 = st.columns(2)

        col1.metric(
            "🔥 Longest Winning Streak",
            max_win
        )

        col2.metric(
            "💀 Longest Losing Streak",
            abs(max_loss)
        )

    except Exception as e:

        st.error(f"❌ Error Loading Reports : {e}")