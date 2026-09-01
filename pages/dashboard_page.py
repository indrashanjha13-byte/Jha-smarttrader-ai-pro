import streamlit as st
from datetime import datetime, time
import os
import pandas as pd
import yfinance as yf
import plotly.express as px
import plotly.graph_objects as go
import traceback

from ai_learning import load_learning, best_strategy
from signals import get_signals
from ai_decision import ai_decision
from telegram_bot import send_alert
from option_chain_v2 import get_option_chain_summary
from option_chain_signal import option_ai_signal
from trade_manager import TradeManager
from trade_exit import exit_manager
from broker.broker_manager import BrokerManager
import config


def status_ribbon():
    c1, c2, c3, c4, c5 = st.columns(5)
    broker = BrokerManager(config.BROKER)

    # -------------------------------------------------------------
    # Paper Trading Switch Status Check
    # -------------------------------------------------------------
    is_paper = getattr(config, "PAPER_TRADE", True)

    if is_paper:
        broker_status = "🟡 PAPER MODE"
    else:
        broker_status = "🟢 LIVE CONNECTED" if getattr(broker.broker, "connected", False) else "🔴 NOT CONNECTED"

    c1.info(f"🏦 {config.BROKER}")
    c1.caption(broker_status)
    c2.success("🟢 Market")
    c3.info("🤖 AI")
    c4.warning("⚙ Auto")
    c5.success("📱 Telegram")

def account_summary(trader, current_price):
    balance = trader.balance
    if trader.position:
        position = trader.position["symbol"]
        pnl = (current_price - trader.position["entry"]) * trader.position["qty"]
    else:
        position = "No Position"
        pnl = 0.0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💰 Balance", f"₹ {balance:.2f}")
    c2.metric("📦 Position", position)
    c3.metric("📈 Live P&L", f"₹ {pnl:.2f}")
    c4.metric("💵 Cash", f"₹ {balance:.2f}")

def market_status():
    st.subheader("🟢 Market Status")
    now = datetime.now().time()
    market_open, market_close = time(9, 15), time(15, 30)
    status = "🟢 OPEN" if market_open <= now <= market_close else "🔴 CLOSED"

    c1, c2, c3 = st.columns(3)
    c1.metric("Market", status)
    c2.metric("Time", datetime.now().strftime("%H:%M:%S"))
    c3.metric("Date", datetime.now().strftime("%d-%b-%Y"))

def performance_report():
    st.subheader("📊 Performance Report")
    if not os.path.exists("trade_history.csv"):
        st.info("No Trade History Available")
        return

    trades = pd.read_csv("trade_history.csv")
    if "PNL" in trades.columns and "PnL" not in trades.columns:
        trades = trades.rename(columns={"PNL": "PnL"})

    trades = trades.loc[:, ~trades.columns.duplicated(keep="first")]

    if "PnL" not in trades.columns:
        st.warning("No PnL data available yet.")
        return

    trades["PnL"] = pd.to_numeric(trades["PnL"], errors="coerce").fillna(0)
    total = len(trades)
    win = len(trades[trades["PnL"] > 0])
    loss = len(trades[trades["PnL"] < 0])
    net = trades["PnL"].sum()
    win_rate = round((win / total) * 100, 2) if total > 0 else 0

    gross_profit = trades.loc[trades["PnL"] > 0, "PnL"].sum()
    gross_loss = abs(trades.loc[trades["PnL"] < 0, "PnL"].sum())
    profit_factor = round(gross_profit / max(gross_loss, 1), 2)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Trades", total)
    c2.metric("Win Rate", f"{win_rate}%")
    c3.metric("Net P&L", f"₹ {net:.2f}")
    c4.metric("Profit Factor", profit_factor)

    st.divider()
    equity = trades["PnL"].cumsum()
    fig = px.line(y=equity, title="Equity Curve")
    st.plotly_chart(fig, use_container_width=True)

def dashboard_page(trader, current_price, symbol):
    manager = TradeManager(paper_trader=trader)
    st.title("📈 Jha SmartTrader AI Pro")
    status_ribbon()
    st.caption("AI Powered Intraday Trading Dashboard")
    st.divider()

    # -------------------------------------------------------------
    # Paper Trading On/Off Switch Control (NEW)
    # -------------------------------------------------------------
    st.subheader("🎛 Execution Mode Switch")
    paper_trade_switch = st.toggle(
        "📝 Enable Paper Trading (Virtual Buy/Sell)",
        value=getattr(config, "PAPER_TRADE", True),
        key="dashboard_paper_trade_toggle"
    )
    
    # Update config dynamically based on toggle
    config.PAPER_TRADE = paper_trade_switch

    if paper_trade_switch:
        st.info("ℹ️ **Paper Trading is ON:** Orders will execute virtually without real funds.")
    else:
        st.warning("⚠️ **Paper Trading is OFF:** Live/Real trading mode is active.")

    st.divider()

    account_summary(trader, current_price)
    st.divider()

    market_status()
    st.divider()

    performance_report()
    st.divider()

    # Portfolio Section
    st.subheader("📦 Portfolio & Risk Management")
    if trader.position:
        portfolio_df = pd.DataFrame([{
            "Symbol": trader.position["symbol"],
            "Qty": trader.position["qty"],
            "Entry": trader.position["entry"],
            "Current": round(current_price, 2),
            "P&L": round((current_price - trader.position["entry"]) * trader.position["qty"], 2)
        }])
        st.dataframe(portfolio_df, use_container_width=True)
    else:
        st.info("No Open Position")

    # Risk Manager & Calculator
    capital = trader.balance
    risk_percent = st.slider("Risk %", 1, 5, 2)
    entry = st.number_input("Entry Price", value=100.0)
    stop = st.number_input("Stop Loss", value=95.0)

    risk_amount = capital * risk_percent / 100
    risk_per_share = abs(entry - stop)
    calc_qty = int(risk_amount / risk_per_share) if risk_per_share > 0 else 0
    st.metric("Suggested Quantity", calc_qty)

    st.divider()

    # Live Market Chart
    st.subheader("📈 Live Market Chart")
    try:
        chart_data = yf.download(symbol, period="5d", interval="15m", auto_adjust=False, progress=False)
        if not chart_data.empty:
            if isinstance(chart_data.columns, pd.MultiIndex):
                chart_data.columns = chart_data.columns.get_level_values(0)

            close = chart_data["Close"]
            ema9 = close.ewm(span=9).mean()
            ema21 = close.ewm(span=21).mean()

            fig = go.Figure()
            fig.add_trace(go.Candlestick(x=chart_data.index, open=chart_data["Open"], high=chart_data["High"], low=chart_data["Low"], close=chart_data["Close"], name="Price"))
            fig.add_trace(go.Scatter(x=chart_data.index, y=ema9, name="EMA 9"))
            fig.add_trace(go.Scatter(x=chart_data.index, y=ema21, name="EMA 21"))
            fig.update_layout(template="plotly_dark", height=500, xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"Chart Error: {e}")

    st.divider()

    # AI Market Scanner
    st.subheader("🤖 AI Market Scanner")
    col1, col2, col3 = st.columns(3)
    signal_filter = col1.selectbox("Signal", ["ALL", "BUY", "SELL", "HOLD"])
    min_confidence = col2.slider("Min Confidence", 50, 100, 70)
    trend_filter = col3.selectbox("Trend", ["ALL", "Bullish", "Bearish", "Sideways"])

    if st.button("▶ Run Scanner"):
        scanner = []
        watchlist = ["RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "SBIN.NS"]

        for stock in watchlist:
            try:
                data = yf.download(stock, period="2d", interval="15m", progress=False)
                if not data.empty:
                    if isinstance(data.columns, pd.MultiIndex):
                        data.columns = data.columns.get_level_values(0)

                    c_price = float(data["Close"].iloc[-1])
                    signal = get_signals(stock)
                    if "error" in signal:
                        continue

                    ai = ai_decision(
                        rsi=signal["RSI"], macd=signal["MACD"], macd_signal=signal["MACD_SIGNAL"],
                        ema9=signal["EMA9"], ema21=signal["EMA21"], supertrend=signal["SUPERTREND"],
                        volume=signal["Volume"], avg_volume=signal["AVG_VOLUME"]
                    )
                    decision, confidence = ai["decision"], ai["confidence"]
                    
                    # Process trade using safe quantity
                    result, message = manager.process(
                        symbol=stock,
                        signal=decision,
                        current_price=c_price,
                        capital=trader.balance
                    )

                    signal_icon = "🟢 BUY" if decision == "BUY" else ("🔴 SELL" if decision == "SELL" else "🟡 HOLD")
                    trend = "📈 Bullish" if signal["EMA9"] > signal["EMA21"] else ("📉 Bearish" if signal["EMA9"] < signal["EMA21"] else "➡ Sideways")

                    scanner.append({
                        "Symbol": stock.replace(".NS", ""), "Price": round(c_price, 2),
                        "Signal": signal_icon, "Confidence": confidence, "Trend": trend,
                        "RSI": round(signal["RSI"], 2), "MACD": round(signal["MACD"], 2), "Volume": signal["Volume"]
                    })
            except Exception as e:
                st.error(f"Error scanning {stock}: {e}")

        if scanner:
            scanner_df = pd.DataFrame(scanner)
            if signal_filter != "ALL":
                scanner_df = scanner_df[scanner_df["Signal"].str.contains(signal_filter)]
            scanner_df = scanner_df[scanner_df["Confidence"] >= min_confidence]
            if trend_filter != "ALL":
                scanner_df = scanner_df[scanner_df["Trend"].str.contains(trend_filter)]

            st.dataframe(scanner_df, use_container_width=True)

    st.divider()

    # Option Chain AI
    st.subheader("📊 Option Chain AI")
    try: 
        option = get_option_chain_summary(symbol)
        if "error" not in option:
            ai_opt = option_ai_signal(option["PCR"])
            c1, c2, c3 = st.columns(3)
            c1.metric("Spot", option["Spot"])
            c2.metric("ATM", option["ATM"])
            c3.metric("PCR", option["PCR"])
            st.metric("AI Signal", ai_opt["Signal"])
        else:
            st.error(option["error"])
    except Exception as e:
        st.error(f"Option Chain Error: {e}")

    st.caption(f"Last Refresh: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    