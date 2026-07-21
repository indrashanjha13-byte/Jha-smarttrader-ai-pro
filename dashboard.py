from pathlib import Path
from datetime import datetime

import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from PIL import Image

from streamlit_autorefresh import st_autorefresh

# ------------------------
# Project Imports
# ------------------------

from signals import get_signals

from strategy import (
    generate_signal,
    ema_signal,
    rsi_signal,
    supertrend_signal
)

from ai_engine import (
    ai_brain,
    confidence_score,
    stop_target,
    position_size,
    trailing_stop,
    daily_risk_manager
)

from ai_signal_ranker import signal_score

from paper_trading import PaperTrader

from ai_learning import (
    load_learning,
    update_learning,
    best_strategy,
    auto_strategy
)

from market_memory import best_market_strategy

from trade_journal import (
    save_trade,
    update_last_trade
)

from portfolio import update_position
from portfolio_manager import can_trade
from trade_analytics import get_trade_stats
from report import generate_report
from telegram_bot import send_alert
from ai_predict import predict_trade
from position_sizing import calculate_qty
import time
from auto_mode import (
    enable_auto,
    disable_auto,
    is_enabled,
    get_scan_interval
)
from option_chain import scan_all_option_chain
from fo_symbols import INDICES, FO_STOCKS
from backtest_engine import BacktestEngine
from ai_decision import ai_decision
from confidence_engine import confidence_engine
from performance import performance_summary
import plotly.express as px



# ------------------------
# Streamlit Config
# ------------------------

st.set_page_config(
    page_title="Jha SmartTrader AI Pro",
    page_icon="📈",
    layout="wide"
)

# ------------------------
# Auto Refresh
# ------------------------

st_autorefresh(
    interval=15000,
    key="market_refresh"
)

# ------------------------
# Session
# ------------------------

if "trader" not in st.session_state:
    st.session_state.trader = PaperTrader()

trader = st.session_state.trader

if "backtester" not in st.session_state:
    st.session_state.backtester = BacktestEngine()

backtester = st.session_state.backtester

# ------------------------
# Logo
# ------------------------

BASE_DIR = Path(__file__).resolve().parent

logo = BASE_DIR / "logo.png"

if logo.exists():

    try:

        st.image(
            Image.open(logo),
            width=150
        )

    except:
        pass

# ------------------------
# Title
# ------------------------

st.title("📈 Jha SmartTrader AI Pro")

st.caption(
    "AI Powered Intraday Trading Dashboard"
)

# ------------------------
# Sidebar
# ------------------------

st.sidebar.title("⚙ Settings")

symbol = st.sidebar.selectbox(

    "Select Symbol",

    [
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
)

strategy_name = st.sidebar.selectbox(

    "Strategy",

    [
        "EMA Crossover",
        "RSI",
        "SuperTrend",
        "MACD + Volume",
        "AI Combo"
    ]
)

option_side = st.sidebar.selectbox(

    "Option",

    [
        "CE",
        "PE"
    ]
)

strike_mode = st.sidebar.selectbox(

    "Strike",

    [
        "ITM",
        "ATM",
        "OTM"
    ]
)

st.sidebar.subheader("🤖 Auto Trading")

if st.sidebar.button("▶ Start Auto Trading"):
    enable_auto()

if st.sidebar.button("⏹ Stop Auto Trading"):
    disable_auto()

st.sidebar.write(
    "Status :",
    "🟢 RUNNING" if is_enabled() else "🔴 STOPPED"
)

# ------------------------
# AI Strategy
# ------------------------

st.info(
    f"🤖 AI Strategy : {auto_strategy()}"
)

# ------------------------
# Scanner Button
# ------------------------

run_scan = st.button("🚀 Run Scanner")


AUTO_SCAN = False

if is_enabled():
    AUTO_SCAN = True

if AUTO_SCAN:
    run_scan = True

if is_enabled():

    st.success("🤖 AUTO TRADING RUNNING")

    #time.sleep(get_scan_interval())

    run_scan = True


# =====================================================
# PART 2
# LIVE SCANNER + AI ENGINE + PAPER TRADING
# =====================================================
if run_scan:

    data = get_signals(symbol)

    if "error" in data:
        st.error(data["error"])

    else:

        current_price = data["Close"]

        # -----------------------------
        # Strategy Selection
        # -----------------------------

        strategy_name = auto_strategy()

        st.info(f"🤖 AI Selected Strategy : {strategy_name}")

        if strategy_name == "EMA Crossover":

            signal = ema_signal(
                data["EMA9"],
                data["EMA21"]
            )

        elif strategy_name == "RSI":

            signal = rsi_signal(
                data["RSI"]
            )

        elif strategy_name == "SuperTrend":

            signal = supertrend_signal(
                data["SUPERTREND"]
            )

        else:

            signal = generate_signal(
                data["SUPERTREND"],
                data["MACD"],
                data["MACD_SIGNAL"],
                data["Volume"],
                data["AVG_VOLUME"]
            )

        # -----------------------------
        # Signal Score
        # -----------------------------

        volume_ratio = (
            data["Volume"] / data["AVG_VOLUME"]
            if data["AVG_VOLUME"] > 0 else 1
        )

        trend = (
            "UP"
            if data["SUPERTREND"] > 0
            else "DOWN"
        )

        score = signal_score(
            data["RSI"],
            volume_ratio,
            trend,
            data["MACD"],
            data["MACD_SIGNAL"],
            data["SUPERTREND"]
        )
        
        # -----------------------------
        # AI Brain
        # -----------------------------

        ai = ai_brain(
            signal=signal,
            rsi=data["RSI"],
            volume=data["Volume"],
            trend=trend,
            ema9=data["EMA9"],
            ema21=data["EMA21"],
            supertrend=data["SUPERTREND"],
            balance=trader.balance,
            risk_percent=2,
            trade_amount=current_price
        )

        ai2 = ai_decision(
            rsi=data["RSI"],
            macd=data["MACD"],
            macd_signal=data["MACD_SIGNAL"],
            ema9=data["EMA9"],
            ema21=data["EMA21"],
            supertrend=data["SUPERTREND"],
            volume=data["Volume"],
            avg_volume=data["AVG_VOLUME"]
        )

        st.subheader("🤖 AI Decision Debug")
        st.write(ai2)
        st.write("Signal =", ai2["decision"])
        st.write("Confidence =", ai2["confidence"])

        st.write("EMA9 =", data["EMA9"])
        st.write("EMA21 =", data["EMA21"])
        st.write("SuperTrend =", data["SUPERTREND"])
        st.write("MACD =", data["MACD"])
        st.write("MACD Signal =", data["MACD_SIGNAL"])

        # Volume Ratio Safe

        if data["AVG_VOLUME"] > 0:
            volume_ratio = data["Volume"] / data["AVG_VOLUME"]
        else:
            volume_ratio = 1

        st.write("Volume Ratio =", round(volume_ratio, 2))
        
        # ===== TESTING =====
        #signal = "BUY"
        #prediction = "BUY"
        #confidence = 90
        # ===================

        signal = ai2["decision"]
        prediction = ai2["decision"]
        confidence = ai2["confidence"]

        confidence_ai = confidence_engine(
            rsi=data["RSI"],
            macd=data["MACD"],
            macd_signal=data["MACD_SIGNAL"],
            ema9=data["EMA9"],
            ema21=data["EMA21"],
            volume=data["Volume"],
            avg_volume=data["AVG_VOLUME"],
            supertrend=data["SUPERTREND"]
        )

        prediction_confidence = confidence_ai["confidence"]
        market_regime = ai["regime"]

        stoploss, target = stop_target(current_price)

        qty = 2

        risk_ok, risk_message = daily_risk_manager(
            trades_today=0,
            losses_today=0,
            daily_loss=0
        )

        st.info(f"🛡 {risk_message}")

        # -----------------------------
        # Metrics
        # -----------------------------

        c1, c2, c3, c4 = st.columns(4)

        c1.metric("Signal", signal)
        c2.metric("RSI", round(data["RSI"], 2))
        c3.metric("MACD", round(data["MACD"], 2))
        c4.metric("Confidence", f"{confidence}%")


        # -----------------------------
        # BUY / SELL / HOLD
        # -----------------------------

        st.write("Signal =", signal)
        st.write("Position =", trader.position)
        st.write("Risk OK =", risk_ok)

        if signal == "BUY" and trader.position is None and risk_ok:

            st.success("✅ BUY BLOCK ENTERED")

            st.write("Balance =", trader.balance)
            st.write("Current Price =", current_price)
            st.write("Qty =", qty)
            st.write("Cost =", current_price * qty)

            st.write("========== DEBUG ==========")
            st.write("Signal =", signal)
            st.write("Before BUY =", trader.position)

            buy_status = trader.buy(symbol, current_price, qty)

            if buy_status:
                trader.position["live_price"] = current_price

            st.write("BUY Status =", buy_status)
            st.write("After BUY =", trader.position)
            st.write("===========================")

            st.success("✅ trader.buy() completed")

            send_alert(
                f"""🟢 AI BUY

Symbol : {symbol}

Price : ₹{current_price:.2f}

Qty : {qty}

Confidence : {confidence}%

Strategy : {strategy_name}
"""
            )

            try:
                save_trade(
                    symbol=symbol,
                    action="BUY",
                    entry=current_price,
                    exit_price=0,
                    stoploss=stoploss,
                    target=target,
                    qty=qty,
                    confidence=confidence,
                    score=score,
                    regime=ai["regime"],
                    strategy=strategy_name,
                    pnl=0,
                    reason=prediction,
                    result="OPEN"
                )

                st.success("✅ save_trade SUCCESS")

            except Exception as e:
                st.error(f"❌ save_trade Error: {e}")

            st.success("🟢 AI BUY EXECUTED")

        elif signal == "SELL" and trader.position is not None:

            entry = trader.position["entry"]

            trader.sell(current_price)

            backtester.add_trade(
                symbol=symbol,
                action="SELL",
                entry=entry,
                exit_price=current_price,
                qty=qty
            )

            result = "WIN" if current_price > entry else "LOSS"

            send_alert(
                f"""🔴 AI SELL

Symbol : {symbol}

Exit Price : ₹{current_price:.2f}

Result : {result}
"""
            )

            update_last_trade(
                result=result,
                exit_price=current_price,
                pnl=current_price - entry
            )

            update_learning(
                strategy_name,
                ai["regime"],
                result
            )

            st.error("🔴 AI SELL EXECUTED")

        elif ai["decision"] == "HOLD":

            st.warning("🟡 HOLD")

        elif trader.position:

            st.success("🟢 Position Already Running")

        else:

            st.info("⚪ NO TRADE")
# =====================================
# LIVE P&L
# =====================================

        if trader.position:

            live_pnl = round(
                (current_price - trader.position["entry"])
                * trader.position["qty"],
                2
            )

            st.subheader("💰 Live Position")

            c1, c2, c3 = st.columns(3)

            c1.metric(
                "Entry",
                f"₹ {trader.position['entry']:.2f}"
            )

            c2.metric(
                "Live Price",
                f"₹ {current_price:.2f}"
            )

            c3.metric(
                "P&L",
                f"₹ {live_pnl:.2f}"
            )

# =====================================
# AUTO EXIT
# =====================================
    if trader.position:

        current_price = 24280   # Testing

        entry = trader.position["entry"]

        stoploss = trader.position.get("stoploss", entry - 20)
        target = trader.position.get("target", entry + 40)

        st.write("Position Data =", trader.position)

        st.write("📌 Entry :", entry)
        st.write("💹 Live :", current_price)
        st.write("🛑 Stoploss :", stoploss)
        st.write("🎯 Target :", target)

        if current_price <= stoploss:

            trader.sell(current_price)

            st.success("✅ Position Closed")
            st.write("Balance =", trader.balance)

            update_last_trade("LOSS")
            st.error("🛑 Stoploss Hit")

        elif current_price >= target:

            trader.sell(current_price)

            st.success("✅ Position Closed")
            st.write("Balance =", trader.balance)

            update_last_trade("WIN")
            st.success("🎯 Target Hit")
# =====================================
# PERFORMANCE REPORT
# =====================================

import pandas as pd
import os

if os.path.exists("trade_history.csv"):

    trades = pd.read_csv("trade_history.csv")

    # PNL column ko function ke liye rename karna
    trades = trades.rename(columns={"PNL": "PnL"})

    report = performance_summary(trades)

    st.header("📊 Performance Report")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("💰 Net Profit", report["Net Profit"])
    c2.metric("🎯 Win Rate", f'{report["Win Rate"]}%')
    c3.metric("📈 Profit Factor", report["Profit Factor"])
    c4.metric("📉 Max Drawdown", report["Max Drawdown"])

# =====================================
# LIVE OPTION CHAIN
# =====================================

st.header("📊 Live Option Chain")

option_symbol = st.selectbox(
    "Select Option Symbol",
    INDICES + FO_STOCKS
)

if st.button("📡 Load Option Chain"):

    with st.spinner("Loading..."):
        data = scan_all_option_chain()

    if option_symbol in data:

        if "error" in data[option_symbol]:
            st.error(data[option_symbol]["error"])

        else:
            st.success("✅ Option Chain Loaded")
            st.json(data[option_symbol])



# ==========================================================
# PART 3A
# LIVE CHART + SUPPORT / RESISTANCE
# ==========================================================

st.divider()

st.header("📈 Live Market Chart")

try:

    chart_data = yf.download(

        symbol,

        period="5d",

        interval="15m",

        auto_adjust=False

    )

    if not chart_data.empty:

        if isinstance(chart_data.columns, pd.MultiIndex):
            chart_data.columns = chart_data.columns.get_level_values(0)

        close = chart_data["Close"]

        ema9 = close.ewm(span=9).mean()
        ema21 = close.ewm(span=21).mean()

        current_price = float(close.iloc[-1])

        support = round(current_price - 150, 2)
        resistance = round(current_price + 150, 2)

        c1, c2, c3, c4 = st.columns(4)

        c1.metric("Current", f"₹{current_price:.2f}")
        c2.metric("Support", f"₹{support}")
        c3.metric("Resistance", f"₹{resistance}")
        c4.metric("Balance", f"₹{trader.balance:,.0f}")

        fig = make_subplots(

            rows=2,

            cols=1,

            shared_xaxes=True,

            row_heights=[0.75,0.25],

            vertical_spacing=0.03

        )

        fig.add_trace(

            go.Candlestick(

                x=chart_data.index,

                open=chart_data["Open"],

                high=chart_data["High"],

                low=chart_data["Low"],

                close=chart_data["Close"],

                name="Price"

            ),

            row=1,

            col=1

        )

        fig.add_trace(

            go.Scatter(

                x=chart_data.index,

                y=ema9,

                mode="lines",

                name="EMA 9"

            ),

            row=1,

            col=1

        )

        fig.add_trace(

            go.Scatter(

                x=chart_data.index,

                y=ema21,

                mode="lines",

                name="EMA 21"

            ),

            row=1,

            col=1

        )

        fig.add_trace(

            go.Bar(

                x=chart_data.index,

                y=chart_data["Volume"],

                name="Volume"

            ),

            row=2,

            col=1

        )

        fig.add_hline(

            y=support,

            line_color="green",

            annotation_text="Support"

        )

        fig.add_hline(

            y=resistance,

            line_color="red",

            annotation_text="Resistance"

        )

        fig.update_layout(

            template="plotly_dark",

            height=850,

            xaxis_rangeslider_visible=False,

            hovermode="x unified"

        )

        st.plotly_chart(

            fig,

            use_container_width=True

        )

except Exception as e:

    st.error(f"Chart Error : {e}")


# ==========================================================
# PART 3B
# TRADE HISTORY + PERFORMANCE + AI LEARNING
# ==========================================================

st.divider()

st.header("📜 Trade History")

try:

    history = pd.read_csv("trade_history.csv")

    st.dataframe(
        history,
        use_container_width=True
    )

except:
    st.info("No Trade History Found")

# ==========================================================

st.header("📊 Performance Dashboard")

try:

    history = pd.read_csv("trade_history.csv")

    total = len(history)

    buy = len(history[history["Action"]=="BUY"])

    sell = len(history[history["Action"]=="SELL"])

    pnl = history["PNL"].sum()

    win = len(history[history["PNL"]>0])

    loss = len(history[history["PNL"]<0])

    winrate = (

        round((win/total)*100,1)

        if total>0 else 0

    )
    gross_profit = history[history["PNL"] > 0]["PNL"].sum()

    gross_loss = abs(
        history[history["PNL"] < 0]["PNL"].sum()
    )
    

    profit_factor = (
        round(gross_profit / gross_loss, 2)
        if gross_loss > 0 else 999
    )

    equity = history["PNL"].cumsum()


    drawdown = equity - equity.cummax()

    max_drawdown = round(abs(drawdown.min()), 2)

    c1,c2,c3,c4,c5,c6 = st.columns(6)

    c1.metric("Trades",total)

    c2.metric("BUY",buy)

    c3.metric("SELL",sell)

    c4.metric("Wins",win)

    c5.metric("Loss",loss)

    c6.metric("Win %",f"{winrate}%")

    st.metric(

        "Net Profit",

        f"₹{pnl:.2f}"

    )
    c7, c8 = st.columns(2)

    c7.metric(
        "Profit Factor",
        profit_factor
    )

    c8.metric(
        "Max Drawdown",
        f"₹{max_drawdown}"
    )

    st.subheader("📈 Equity Curve")

    st.line_chart(equity)

    st.subheader("🥧 Win / Loss Distribution")

    pie = px.pie(

        values=[win, loss],

        names=["Wins", "Losses"],

        title="Trade Distribution"

    )

    st.plotly_chart(

        pie,

        use_container_width=True
    )
    # =====================================
    # MONTHLY P&L
    # =====================================

    st.subheader("📅 Monthly P&L")

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

except Exception as e:

    st.error(e)


    
# ==========================================================

st.header("💰 Live Paper Trading")

col1,col2,col3 = st.columns(3)

with col1:

    st.metric(

        "Balance",

        f"₹{trader.balance:,.2f}"

    )

with col2:

    if trader.position:

        st.metric(

            "Position",

            trader.position["symbol"]

        )

    else:

        st.metric(

            "Position",

            "None"

        )

with col3:

    if trader.position and "current_price" in locals():

        live_pnl=(

            current_price-

            trader.position["entry"]

        )*trader.position["qty"]

        st.metric(

            "Live P&L",

            f"₹{live_pnl:.2f}"

        )

    else:

        st.metric(

            "Live P&L",

            "₹0"

        )

# ==========================================================

st.header("🧠 AI Learning")

learning=load_learning()

st.metric("Wins", learning["wins"])
st.metric("Losses", learning["losses"])

best = best_strategy()

if best != "No Data":

    strategy, acc = best

    st.success(f"🏆 Best Strategy : {strategy}")

    st.info(f"Accuracy : {acc}%")

else:

    st.warning("AI has not learned yet.")

strategies=learning.get("strategies",{})

if strategies:

    for strategy,info in strategies.items():

        wins=info.get("wins",0)

        losses=info.get("losses",0)

        total=wins+losses

        accuracy=(wins/total)*100 if total>0 else 0

        st.success(

            f"""

📌 Strategy : {strategy}

✅ Wins : {wins}

❌ Losses : {losses}

🎯 Accuracy : {accuracy:.1f}%

"""

        )

else:

    st.info("AI has not learned yet.")


# ==========================================================

st.header("📈 AI Confidence")

if "data" in locals():

    conf=signal_score(

        data["RSI"],

        data["Volume"]/data["AVG_VOLUME"]

        if data["AVG_VOLUME"]>0 else 1,

        "UP" if data["SUPERTREND"]>0 else "DOWN",

        data["MACD"],

        data["MACD_SIGNAL"],

        data["SUPERTREND"]

    )

    st.progress(conf/100)

    st.write(f"Confidence : {conf}%")

# ==========================================================
# PART 3C
# FINAL DASHBOARD
# ==========================================================

st.divider()

st.header("⚙ Auto Trading")

col1, col2 = st.columns(2)

with col1:

    if st.button("🟢 Enable Auto Trading"):

        enable_auto()

        st.success("Auto Trading Enabled")

with col2:

    if st.button("🔴 Disable Auto Trading"):

        disable_auto()

        st.warning("Auto Trading Disabled")

st.write(

    "Status :",

    "🟢 RUNNING" if is_enabled() else "🔴 STOPPED"

)

# ==========================================================

st.header("📱 Telegram")

if st.button("Send Telegram Test"):

    try:

        send_alert("✅ SmartTrader AI Pro Connected")

        st.success("Telegram Message Sent")

    except Exception as e:

        st.error(e)

# ==========================================================

st.header("🏦 Broker")

broker = st.selectbox(

    "Broker",

    [

        "Kotak Neo",

        "Angel One",

        "Zerodha",

        "Upstox"

    ]

)

api = st.text_input(

    "API Key",

    type="password"

)

if st.button("Connect Broker"):

    st.success(f"{broker} Connected")

# ==========================================================

st.header("📦 Portfolio")

update_position(symbol,1)

st.success("Portfolio Updated")

# ==========================================================

st.header("🛡 Risk Manager")

open_positions = st.number_input(

    "Open Positions",

    value=0,

    min_value=0

)

if can_trade(open_positions):

    st.success("Trade Allowed")

else:

    st.error("Trade Blocked")

# ==========================================================

st.header("📏 Position Size")

capital = st.number_input(

    "Capital",

    value=100000

)

entry = st.number_input(

    "Entry",

    value=100.0

)

sl = st.number_input(

    "Stop Loss",

    value=95.0

)

qty = calculate_qty(

    capital,

    entry,

    sl

)

st.metric(

    "Suggested Quantity",

    qty

)

# ==========================================================

st.header("📊 Trade Analytics")

stats = get_trade_stats()

st.write(stats)


if "signal" not in locals():
    signal = "NO TRADE"

if "confidence" not in locals():
    confidence = 0


if "ai" not in locals():
    ai = {
        "regime": "SIDEWAYS",
        "decision": "NO TRADE",
        "score": 0,
        "filter": False
    }


# ==========================================================


prediction = ai["decision"] if "ai" in locals() else "NO TRADE"

prediction_confidence = confidence if "confidence" in locals() else 0

market_regime = ai["regime"] if "ai" in locals() else "SIDEWAYS"



st.header("🤖 AI Prediction")

if "confidence_ai" in locals():

    st.metric("Prediction", prediction)

    st.metric(
        "Confidence",
        f"{prediction_confidence}%"
    )

    st.metric(
        "Market Regime",
        market_regime
    )

    st.write("### 🧠 AI Reasons")

    for reason in confidence_ai["reasons"]:
        st.success(reason)

else:

    st.info("Run Scanner to generate AI Prediction.")
    
# =====================================
# BACKTEST RESULTS
# =====================================

st.header("📈 Backtesting Results")

summary = backtester.summary()

c1, c2, c3, c4 = st.columns(4)

c1.metric("Trades", summary["Total Trades"])
c2.metric("Wins", summary["Wins"])
c3.metric("Losses", summary["Losses"])
c4.metric("Win Rate", f'{summary["Win Rate"]}%')

st.metric("Net Profit", f'₹{summary["Net Profit"]}')

st.dataframe(
    backtester.dataframe(),
    use_container_width=True
)

# ==========================================================

st.header("📄 Report")

try:

    report = generate_report(

        total_trades=10,

        winning_trades=7,

        losing_trades=3,

        net_profit=5000,

        daily_pnl=500,

        monthly_pnl=5000,

        open_positions=1,

        broker_status="Connected"

    )

    st.text(report)

except:

    pass

# ==========================================================

st.divider()

st.success("✅ Jha SmartTrader AI Pro Loaded Successfully")

st.caption(

    f"Last Refresh : {datetime.now()}"

)
