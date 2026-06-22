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

trader = PaperTrader()

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

        if result == "BUY":
            send_alert(f"BUY Signal on {symbol}")
            place_trade("BUY", symbol, 1)

        elif result == "SELL":
            send_alert(f"SELL Signal on {symbol}")
            place_trade("SELL", symbol, 1)

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

st.button("Start Trading")
st.button("Stop Trading")

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

try:
    df = pd.read_csv("trade_history.csv")
    st.dataframe(df)
except:
    st.info("No Trade History Found")

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

try:
    df = pd.read_csv("trade_history.csv")

    total_trades = len(df)

    buy_trades = len(df[df["Side"] == "BUY"])
    sell_trades = len(df[df["Side"] == "SELL"])

    st.write("Total Trades:", total_trades)
    st.write("Buy Trades:", buy_trades)
    st.write("Sell Trades:", sell_trades)

except:
    st.info("No Analytics Available")
st.subheader("Trade Analytics")

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
