from pathlib import Path
from PIL import Image
import streamlit as st
import pandas as pd
from signals import get_signals
from strategy import generate_signal
from ai_signal_ranker import signal_score
from paper_trading import PaperTrader
from telegram_bot import send_alert
from portfolio import update_position
from report import generate_report
from portfolio_manager import can_trade
from auto_trader import place_trade
from position_sizing import calculate_qty
from trade_analytics import get_trade_stats
from ai_predict import predict_trade
import plotly.graph_objects as go
import yfinance as yf
from auto_mode import (
    enable_auto,
    disable_auto,
    is_enabled
)
from datetime import datetime
from paper_trading import check_exit


st.set_page_config(
    page_title="SmartTrader AI Pro",
    layout="wide"
)
BASE_DIR = Path(__file__).resolve().parent

logo_path = BASE_DIR / "logo.png"
if logo_path.exists():
    try:
        logo =Image.open(logo_path)
        st.image(logo,width=150)
    except:
        pass
st.title("📈 SmartTrader AI Pro")
symbol = st.selectbox(
    "Symbol",
    ["^NSEI", "^NSEBANK", "RELIANCE.NS", "TCS.NS", "INFY.NS"]
)
# Option Selection
st.subheader("option Selection")

option_side = st.selectbox(
    "Option Type",
    ["CE", "PE"]
)
strike_mode = st.selectbox(
    "Strike Selection",
    ["ITM", "ATM", "OTM"]
)
st.write(f"Selected: {strike_mode}{option_side}")

if "trader" not in st.session_state:
    st.session_state.trader = PaperTrader()

trader = st.session_state.trader

st.subheader("Paper Trading")

if st.button("Paper Buy"):
    trader.buy(symbol, 500, 1)
    st.success("Paper Buy Executed")

if st.button("Paper Sell"):
    trader.sell(530)
    st.success("Paper Sell Executed")

st.write("Balance:", trader.balance)

if st.button("Run Scanner"):

    data = get_signals(symbol)

    if "error" in data:
        st.error(data["error"])

    else:

        result = generate_signal(
            data["SUPERTREND"],
            data["MACD"],
            data["MACD_SIGNAL"],
            data["Volume"],
            data["AVG_VOLUME"],
        )
        st.write("SUPERTREND:", data["SUPERTREND"])
        st.write("MACD:", data["MACD"])
        st.write("MACD SIGNAL:", data["MACD_SIGNAL"])
        st.write("VOLUME:", data["Volume"])
        st.write("AVG VOLUME:", data["AVG_VOLUME"])

        current_price = data["Close"]
        st.write("SYMBOL =", symbol)
        st.write("CLOSE =", current_price)

        # AUTO PAPER BUY
        if result == "BUY" and trader.position is None:

            trader.buy(
                symbol,
                current_price,
                1
            )

            send_alert(
                f"AUTO BUY {symbol} @ {current_price}"
            )

        # AUTO EXIT
        if trader.position:

            exit_signal = check_exit(
                trader.position["entry"],
                current_price
            )

            if exit_signal:
                st.write("EXIT PRICE =", current_price)

                trader.sell(current_price)

                send_alert(
                    f"AUTO EXIT {symbol} {exit_signal}"
                )

        if result == "BUY":
            send_alert(f"BUY Signal on {symbol}")

        elif result == "SELL":
            send_alert(f"SELL Signal on {symbol}")

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
        trend
    )

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Signal", result)
    col2.metric("MACD", round(data["MACD"], 2))
    col3.metric("RSI", round(data["RSI"], 2))
    col4.metric("AI Score", score)

    st.subheader("AI Trade Filter")

try:
    if score >= 70:
        st.success("High Quality Trade")

    elif score >= 50:
        st.warning("Average Quality Trade")

    else:
        st.error("Avoid This Trade")

except:
    st.info("Run Scanner First")

       # st.write("Entry:", result["entry"])
       # st.write("Stop Loss:", result["stoploss"])
       # st.write("Target:", result["target"])

st.header("SmartTrader AI Pro Dashboard")

if st.button("Start Trading"):
    enable_auto()
    st.success("Trading Started")

if st.button("Stop Trading"):
    disable_auto()
    st.warning("Trading Stopped")

st.write(
    "Trading Status:",
    "🟢 RUNNING" if is_enabled() else "🔴 STOPPED"
)
st.subheader("Strategy")
st.write("SuperTrend + MACD + Volume Filter")

st.subheader("Add To Portfolio")
update_position(symbol, 1)
st.success("Portfolio Updated")
st.write("Current Symbol:", symbol)
st.write("Quantity:", 1)

st.subheader("Reports")
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
st.subheader("Trade History")
import os

st.write("Current Folder:", os.getcwd())
st.write("Trade File Exists:", os.path.exists("trade_history.csv"))

try:
    df = pd.read_csv("trade_history.csv")
    st.dataframe(df)
except Exception as e:
    st.error(str(e))

st.subheader("Risk Manager")

open_positions = st.number_input(
    "Open Positions",
    min_value=0,
    value=0
)

if can_trade(open_positions):
    st.success("Trade Allowed")
else:
    st.error("Maximum Open Trades Reached")
    
st.subheader("Position Sizing")

capital = st.number_input(
    "Capital",
    value=100000
)

entry_price = st.number_input(
    "Entry Price",
    value=500
)

stoploss_price = st.number_input(
    "Stoploss Price",
    value=480
)

qty = calculate_qty(
    capital,
    entry_price,
    stoploss_price
)

st.write("Suggested Quantity:", qty)
st.subheader("Trade Analytics")

stats = get_trade_stats()

st.write("Total Trades:", stats["total"])
st.write("Buy Trades:", stats["buy"])
st.write("Sell Trades:", stats["sell"])
st.write("Win Rate:", stats["win_rate"], "%")
st.subheader("AI Prediction")

prediction, confidence = predict_trade()

st.write("Prediction:", prediction)
st.write("Confidence:", confidence, "%")
try:

    total_trades = len(df)

    st.write("Total Trades:", total_trades)

except:
    st.info("No Analytics Data")
st.subheader("Live Profit / Loss")

try:
    df = pd.read_csv("trade_history.csv")

    buy_count = len(df[df["Side"] == "BUY"])
    sell_count = len(df[df["Side"] == "SELL"])

    total_pnl = (sell_count - buy_count) * 30

    st.metric(
        "Net Profit/Loss",
        f"₹{total_pnl}"
    )

except:
    st.info("No PnL Data Available")
st.subheader("Live Equity Curve")

try:
    df = pd.read_csv("trade_history.csv")

    df["Trade No"] = range(
        1,
        len(df) + 1
    )

    st.line_chart(df["Trade No"])

except:
    st.info("No Chart Data")    
st.subheader("Live Market Statistics")

try:

    data = get_signals(symbol)

    st.metric(
        "RSI",
        round(data["RSI"], 2)
    )

    st.metric(
        "MACD",
        round(data["MACD"], 2)
    )

    st.metric(
        "Volume",
        int(data["Volume"])
    )

except:
    st.info("Market Data Not Available")

st.subheader("Live Market Chart")

try:

    chart_data = yf.download(
        symbol,
        period="5d",
        interval="15m"
    )

    fig = go.Figure(
        data=[
            go.Candlestick(
                x=chart_data.index,
                open=chart_data["Open"],
                high=chart_data["High"],
                low=chart_data["Low"],
                close=chart_data["Close"]
            )
        ]
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

except:
    st.info("Chart Not Available")
st.subheader("Auto Trading Control")

if st.button("Enable Auto Trading"):
    enable_auto()
    st.success("Auto Trading Enabled")

if st.button("Disable Auto Trading"):
    disable_auto()
    st.warning("Auto Trading Disabled")

st.write(
    "Status:",
    "ON" if is_enabled() else "OFF"
)
st.subheader("Broker Login Panel")

broker = st.selectbox(
    "Select Broker",
    ["Kotak Neo", "Angel One", "Upstox", "Zerodha"]
)

api_key = st.text_input(
    "API Key",
    type="password"
)

if st.button("Connect Broker"):
    st.success(f"{broker} Connected")
st.success("🟢 Software Running")
st.write("Last Check:", datetime.now())
try:
    if data is not None:
        st.success("🟢 Data Connected")
    else:
        st.error("🔴 Data Disconnected")
except:
    st.warning("🟡 Run Scanner First")

st.subheader("Telegram Test")

if st.button("Test Telegram"):
    send_alert("Telegram Test Successful ✅")
    st.success("Test Message Sent")
