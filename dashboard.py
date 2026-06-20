from pathlib import Path
from PIL import Image
import streamlit as st
from signals import get_signals
from strategy import generate_signal
from ai_signal_ranker import signal_score
from paper_trading import PaperTrader

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
        volume_ratio = data["Volume"] / data["AVG_VOLUME"]
        trend = "UP" if data["SUPERTREND"] > 0 else "DOWN"
        score = signal_score(
            data["RSI"],
            volume_ratio,
            trend
        )
        


        col1,col2,col3,col4 = st.columns(4)


        col1.metric(
            "Signal",
            result
        )

        col2.metric(
            "MACD",
            round(data["MACD"],2)
        )

        col3.metric(
            "RSI",
            round(data["RSI"],2)
        )
        col4.metric(
            "AI Score",
            score
        )


       # st.write("Entry:", result["entry"])
       # st.write("Stop Loss:", result["stoploss"])
       # st.write("Target:", result["target"])

st.header("SmartTrader AI Pro Dashboard")

st.button("Start Trading")
st.button("Stop Trading")

st.subheader("Strategy")
st.write("SuperTrend + MACD + Volume Filter")

st.subheader("Portfolio")
st.write("Portfolio Manager Loaded")

st.subheader("Reports")
st.write("Trading Report")
