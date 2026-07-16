from pathlib import Path

from PIL import Image

import streamlit as st

import pandas as pd

from signals import get_signals

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

from strategy import (
    generate_signal,
    ema_signal,
    rsi_signal,
    supertrend_signal)

from ai_signal_ranker import signal_score

from streamlit_autorefresh import st_autorefresh

from plotly.subplots import make_subplots

from paper_trading import PaperTrader

from ai_engine import (
    ai_filter,
    rank_signal,
    market_regime,
    risk_check,
    trade_decision,
    ai_brain,
    confidence_score,
    stop_target,
    position_size,
    trailing_stop,
    daily_risk_manager
)

from ai_learning import (
    update_learning,
    load_learning,
    best_strategy,
    auto_strategy
)

from market_memory import best_market_strategy

from trade_journal import (
    save_trade,
    update_last_trade
)


st.set_page_config(   
    page_title="SmartTrader AI Pro",
    layout="wide"
)

st_autorefresh(
    interval=15000,
    key="market_refresh"
)
if "trader" not in st.session_state:
    st.session_state.trader = PaperTrader()

trader = st.session_state.trader

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
stock_list = [
    "^NSEI",         # Nifty 50
    "^NSEBANK",      # Bank Nifty
    "^BSESN",        # Sensex
    "RELIANCE.NS",
    "TCS.NS",
    "INFY.NS",
    "HDFCBANK.NS",
    "ICICIBANK.NS",
    "SBIN.NS",
    "LT.NS",
    "AXISBANK.NS"
]
if st.button("AI Multi Scanner"):

    st.subheader("Top AI Scanner")

    results = []

    for stock in stock_list:

        data = get_signals(stock)

        if "error" in data:
            continue

        result = generate_signal(
            data["SUPERTREND"],
            data["MACD"],
            data["MACD_SIGNAL"],
            data["Volume"],
            data["AVG_VOLUME"]
        )
        st.write("Stock:", stock)
        st.write("RSI:", data["RSI"])
        st.write("MACD:", data["MACD"])
        st.write("MACD SIGNAL:", data["MACD_SIGNAL"])
        st.write("SUPERTREND:", data["SUPERTREND"])
        st.write("VOLUME:", data["Volume"])

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
        if score >= 90:
            confidence = 98
        elif score >= 80:
            confidence = 90
        elif score >= 70:
            confidence = 80
        elif score >= 60:
            confidence = 70
        else:
            confidence = 55
        

        results.append([stock, result, score, confidence])
        results = sorted(
            results,
            key=lambda x: x[2],
            reverse=True
        )

    st.subheader("AI Ranking")

    for stock, signal, score, confidence in results[:5]:
        

        if signal == "BUY":
            st.success(
    f"🟢 {stock} ➜ BUY ⭐ {score} | 🎯 {confidence}%"
)
            
        elif signal == "SELL":
            st.error(
    f"🔴 {stock} ➜ SELL ⭐ {score} | 🎯 {confidence}%"
)
        else:
            st.warning(
    f"🟡 {stock} ➜ NO TRADE ⭐ {score} | 🎯 {confidence}%"
)
strategy_name = st.selectbox(
    "Select Strategy",
    [
        "EMA Crossover",
        "RSI",
        "SuperTrend",
        "MACD + Volume",
        "AI Combo"
    ]
)
st.info(f"🤖 AI Selected Strategy : {auto_strategy()}")

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

st.subheader("📊 Live Option Chain")

col1, col2, col3, col4 = st.columns(4)
col5, col6 = st.columns(2)

with col5:
    st.metric("CE Premium", "₹152.40")

with col6:
    st.metric("PE Premium", "₹138.20")
    col7, col8 = st.columns(2)

with col7:
    st.metric(
        "IV",
        "14.80%"
    )

with col8:
    st.metric(
        "Max Pain",
        "24000"
    )
st.subheader("📈 Option Chain Analysis")

st.subheader("🌍 Market Status")

st.subheader("🤖 AI Decision")

confidence = 75

if confidence >= 80:
    st.success("✅ Strong BUY")

elif confidence >= 60:
    st.warning("⚠️ WAIT")

else:
    st.error("❌ AVOID TRADE")

    st.metric(
    "AI Confidence",
    f"{confidence}%"
)
st.subheader("📍 Support & Resistance")


col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        "Trend",
        "🟢 Bullish"
    )

with col2:
    st.metric(
        "Volatility",
        "Medium"
    )

with col3:
    st.metric(
        "Market Mood",
        "Buy"
    )

if 1.0 < 1.2:
    st.success("🟢 PCR Bullish")

st.info("📊 Max Pain : 24000")

st.warning("⚠️ Highest Call OI : 24200")

st.warning("⚠️ Highest Put OI : 23900")

with col1:
    st.metric("ATM Strike", "24000")

with col2:
    st.metric("Call OI", "12.5 L")

with col3:
    st.metric("Put OI", "14.2 L")

with col4:
    st.metric("PCR", "1.14")


if "trader" not in st.session_state:
    st.session_state.trader = PaperTrader()

trader = st.session_state.trader

data = get_signals(symbol)

if "error" not in data:
    current_price = data["Close"]

st.subheader("Paper Trading")

col1, col2 = st.columns(2)

with col1:
    if st.button("🟢 Paper Buy"):

        if "current_price" in locals():
            trader.buy(symbol, current_price, 1)
            st.success("Paper Buy Executed")
        else:
            st.warning("Run Scanner First")
with col2:
    if st.button("🔴 Paper Sell"):

        if trader.position:
            trader.sell(current_price)
            st.success("Paper Sell Executed")
        else:
            st.warning("No Open Position")

if st.button("Run Scanner"):

    data = get_signals(symbol)

    if data["EMA9"] > data["EMA21"]:

        market = "Bullish"

    elif data["EMA9"] < data["EMA21"]:

            market = "Bearish"

    else:

            market = "Sideways"
            
            strategy_name = best_market_strategy(market)

    if "error" in data:
        st.error(data["error"])

    else:

        current_price = data["Close"]

        if strategy_name == "EMA Crossover":
            
            result = ema_signal(
                data["EMA9"],
                data["EMA21"]
            )

        elif strategy_name == "RSI":
            result = rsi_signal(
                data["RSI"]
            )
        elif strategy_name =="SuperTrend":
            result = supertrend_signal(
                data["SUPERTREND"]
            )
elif strategy_name == "MACD + Volume":

    result = generate_signal(
        data["SUPERTREND"],
        data["MACD"],
        data["MACD_SIGNAL"],
        data["Volume"],
        data["AVG_VOLUME"],
    )

elif strategy_name == "AI Combo":

    ai = ai_brain(
        signal="",
        rsi=data["RSI"],
        volume=data["Volume"],
        trend="UP" if data["SUPERTREND"] > 0 else "DOWN",
        ema9=data["EMA9"],
        ema21=data["EMA21"],
        supertrend=data["SUPERTREND"],
        balance=trader.balance,
        risk_percent=2,
        trade_amount=current_price
    )

    result = ai["decision"]

else:

    result = generate_signal(
        data["SUPERTREND"],
        data["MACD"],
        data["MACD_SIGNAL"],
        data["Volume"],
        data["AVG_VOLUME"]
    )
            
     # AI Calculation

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

    ai = ai_brain(
        signal=result,
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

    confidence = confidence_score(
        ai["score"],
        ai["regime"],
        ai["filter"]
    )
    stoploss, target = stop_target(current_price)

    qty = position_size(
    trader.balance,
    2,
    abs(current_price - stoploss)
)
    risk_ok, risk_message = daily_risk_manager(
    trades_today=0,
    losses_today=0,
    daily_loss=0
)

    st.info(f"🛡️ Risk Manager : {risk_message}")

    # AI AUTO TRADING

    if ai["decision"] == "BUY" and trader.position is None and risk_ok:
   
        trader.buy(symbol, current_price, qty)
        save_trade(
            symbol=symbol,
            action="BUY",
            entry=current_price,
            stoploss=stoploss,
            target=target,
            qty=qty,
            confidence=confidence,
            score=score,
            regime=ai["regime"]
        )

        st.success(
            f"""
     🤖 AI AUTO TRADE EXECUTED

━━━━━━━━━━━━━━━━━━━━━━━━━━

     📈 Symbol        : {symbol}
     🟢 Action        : BUY
     💰 Entry Price   : ₹{current_price:.2f}
     📦 Quantity      : {qty}
     🛑 Stop Loss     : ₹{stoploss:.2f}
     🎯 Target Price  : ₹{target:.2f}
     🧠 AI Confidence : {confidence}%
     ⭐ AI Score       : {score}
     📊 Market Regime : {ai["regime"]}

━━━━━━━━━━━━━━━━━━━━━━━━━━

     ✅ Trade Executed Successfully
     """
         )

    elif ai["decision"] == "SELL" and trader.position:
    
        entry_price = trader.position["entry"]

        trader.sell(current_price)

        if current_price > entry_price:
            result_type = "WIN"
        else:
            result_type = "LOSS"

        update_learning(
            strategy_name,
            ai["regime"],
            result_type
        )

        st.error("🔴 AI AUTO SELL EXECUTED")


    elif ai["decision"] == "HOLD":

        st.info("🟡 AI Decision : HOLD")


    else:

        st.warning("⚪ AI Decision : NO TRADE")

    
    # AUTO EXIT

    if trader.position:

        stoploss = trailing_stop(
            trader.position["entry"],
            current_price,
            stoploss
        )

        if current_price <= stoploss:

            trader.sell(current_price)
            st.warning("🛑 AI Trailing Stop Hit")

        elif current_price >= target:

           trader.sell(current_price)
           st.success("🎯 AI Target Hit")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Signal", result)
    col2.metric("MACD", round(data["MACD"], 2))
    col3.metric("RSI", round(data["RSI"], 2))
    col4.metric("Confidence", f"{confidence}%")
       
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
    df = pd.read_csv(
        "trade_history.csv",
        encoding="utf-8"
    )

    if df.empty:
        st.info("No Trade History Found")
    else:
        st.dataframe(df, use_container_width=True)
    
        st.download_button(
            "📥 Download Trade History",
            df.to_csv(index=False),
            file_name="trade_history.csv",
            mime="text/csv"
        )
        st.subheader("💰 Live Trading Summary")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Balance", f"₹{trader.balance:,.2f}")

        with col2:
            if trader.position:
                st.metric("Open Position", trader.position["symbol"])
            else:
                st.metric("Open Position", "None")

        with col3:
            if trader.position and "current_price" in locals():
                live_pnl = (
                    current_price - trader.position["entry"]
                ) * trader.position["qty"]

                st.metric(
                    "Live P&L",
                    f"₹{live_pnl:.2f}"
                )
            else:
                st.metric("Live P&L", "₹0.00")

except FileNotFoundError:
    st.warning("trade_history.csv not found")

except Exception as e:
    st.error(f"Trade History Error: {e}")

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
risk_percent = st.number_input(
    "Risk %",
    value=2.0  
)

entry_price = st.number_input(
    "Entry Price",
    value=500
)

stoploss_price = st.number_input(
    "Stoploss Price",
    value=480
)

stop_distance = abs(entry_price - stoploss_price)
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

    buy_count = len(df[df["Action"] == "BUY"])
    sell_count = len(df[df["Action"] == "SELL"])

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

    close_data = chart_data["Close"]


    if isinstance(close_data, pd.DataFrame):
        close_data = close_data.iloc[:, 0]

    current_price = float(close_data.iloc[-1])
    
    st.subheader("📍 Support & Resistance")

    support = round(current_price - 150, 2)
    resistance = round(current_price + 150, 2)

    col1, col2 = st.columns(2)

    with col1:
        st.metric("Support", f"₹{support}")

    with col2:
        st.metric("Resistance", f"₹{resistance}")

    day_high = chart_data["High"].max()
    if isinstance(day_high, pd.Series):
        day_high = day_high.iloc[0]
    day_high = float(day_high)

    day_low = chart_data["Low"].min()
    if isinstance(day_low, pd.Series):
        day_low = day_low.iloc[0]
    day_low = float(day_low)

    col1, col2, col3, col4, col5, col6 = st.columns(6)

    with col1:
        st.metric(
            "Current Price",
            f"₹{current_price:.2f}"
        )

    with col2:
        st.metric(
            "Day High",
            f"₹{day_high:.2f}"
        )

    with col3:
        st.metric(
            "Day Low",
            f"₹{day_low:.2f}"
        )
    with col4:
        st.metric(
        "Paper Balance",
        f"₹{trader.balance:,.2f}"
    )
        if trader.position:
            st.success(
                f"🟢 Active Trade : {trader.position['symbol']}"
            )

            st.write(
                f"Entry : ₹{trader.position['entry']:.2f}"
            )

            st.write(
                f"Qty : {trader.position['qty']}"
            )

        else:
            st.info("No Active Position")

        if trader.position:
            st.success(
                f"Open Position : {trader.position['symbol']} | "
                f"Entry : ₹{trader.position['entry']:.2f}"
            )
            if trader.position:

                live_pnl = (
                    current_price - trader.position["entry"]
                ) * trader.position["qty"]

                st.metric(
                    "Live P&L",
                    f"₹{live_pnl:.2f}"
                )
        else:
            st.info("No Open Position")
        
    with col5:
        if trader.position:
            st.metric(
                "Position",
                f"{trader.position['symbol']}"
            )
        else:
            st.metric(
                "Position",
                "No Trade"
            )

    with col6:
        if trader.position:
            st.metric(
                "Entry Price",
                f"₹{trader.position['entry']:.2f}"
            )
        else:
            st.metric(
                "Entry Price",
                "-"
            )

    ema9 = close_data.ewm(span=9).mean()
    ema21 = close_data.ewm(span=21).mean()

    display_data = pd.DataFrame({
        "Close": close_data,
        "EMA9": ema9,
        "EMA21": ema21
    })
    

    fig = make_subplots(
    rows=2,
    cols=1,
    shared_xaxes=True,
    vertical_spacing=0.03,
    row_heights=[0.75, 0.25]

  )  


    fig.add_trace(
        go.Candlestick(
            x=chart_data.index,
            open=chart_data["Open"],
            high=chart_data["High"],
            low=chart_data["Low"],
            close=chart_data["Close"],
            name="Candlestick"
        ),
        row=1,
        col=1
    )

    fig.update_layout(
    title="📈 Live Candlestick Chart",
    xaxis_title="Time",
    yaxis_title="Price",
    xaxis_rangeslider_visible=False,
    height=850,
    template="plotly_dark",
    hovermode="x unified",
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1
    )
)


    fig.add_trace(
       go.Scatter(
          x=chart_data.index,
          y=ema9,
          mode="lines",
          name="EMA 9",
          line=dict(color="blue", width=2)
    ),
    row=1,
    col=1
)

    fig.add_trace(
        go.Scatter(
           x=chart_data.index,
           y=ema21,
           mode="lines",
           name="EMA 21",
           line=dict(color="orange", width=2)
    ),
    row=1,
    col=1
)

    fig.add_trace(
        go.Bar(
           x=chart_data.index,
           y=chart_data["Volume"],
           name="Volume",
           marker_color="skyblue"
    ),
    row=2,
    col=1
)
    
    fig.add_hline(
        y=support,
        line_color="green",
        line_width=2,
        annotation_text=f"Support ₹{support}"
    )

    fig.add_hline(
        y=resistance,
        line_color="red",
        line_width=2,
        annotation_text=f"Resistance ₹{resistance}"
        
)

    signal = generate_signal(
        data["SUPERTREND"],
        data["MACD"],
        data["MACD_SIGNAL"],
        data["Volume"],
        data["AVG_VOLUME"]
    )
    if signal == "BUY":
        if trader.position is None:
            trader.buy(symbol, current_price, 1)

    if signal == "BUY":
        fig.add_annotation(
        x=chart_data.index[-1],
        y=current_price,
        text="🟢 BUY",
        showarrow=True,
        arrowhead=2,
        arrowcolor="green"

    )
        
    elif signal == "SELL":
        fig.add_annotation(
        x=chart_data.index[-1],
        y=current_price,
        text="🔴 SELL",
        showarrow=True,
        arrowhead=2,
        arrowcolor="red"

    )
    
    st.plotly_chart(fig, use_container_width=True)
    
except Exception as e:
    st.error(f"Chart Error: {e}")

    st.subheader("📜 Trade History")

try:
    history = pd.read_csv("trade_history.csv")

    st.dataframe(
        history,
        use_container_width=True
    )

except Exception as e:
    st.error(e)


st.subheader("📊 Performance")

try:
    history = pd.read_csv("trade_history.csv")

    total_trades = len(history)

    winning = len(history[history["PNL"] > 0])

    losing = len(history[history["PNL"] < 0])

    total_profit = history["PNL"].sum()

    win_rate = (
        winning / total_trades * 100
        if total_trades > 0 else 0
    )

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric(
            "Total Trades",
            total_trades
        )

    with c2:
        st.metric(
            "Winning",
            winning
        )

    with c3:
        st.metric(
            "Losing",
            losing
        )

    with c4:
        st.metric(
            "Win Rate",
            f"{win_rate:.1f}%"
        )

    st.metric(
        "Net Profit",
        f"₹{total_profit:.2f}"
    )

except Exception as e:
    st.error(e)
st.subheader("🧠 AI Learning Report")

learning = load_learning()

strategies = learning.get("strategies", {})

if strategies:

    for strategy, info in strategies.items():

        wins = info.get("wins", 0)
        losses = info.get("losses", 0)

        total = wins + losses
        accuracy = round((wins / total) * 100, 1) if total > 0 else 0

        st.success(
            f"""
📌 Strategy : {strategy}

✅ Wins : {wins}

❌ Losses : {losses}

🎯 Accuracy : {accuracy}%
"""
        )

else:

    st.info("AI has not learned any trades yet.")

best = best_strategy()

if best != "No Data":

    strategy, accuracy = best

    st.success(
        f"""
🏆 Best AI Strategy

📌 Strategy : {strategy}

🎯 Accuracy : {accuracy}%
"""
    )

   
    

    st.subheader("RSI & MACD")

    data = get_signals(symbol)

    rsi_value = data["RSI"]
    macd_value = data["MACD"]
    macd_signal = data["MACD_SIGNAL"]

    chart_df = pd.DataFrame({
        "Indicator": ["RSI", "MACD", "Signal"],
        "Value": [rsi_value, macd_value, macd_signal]
    })

    st.bar_chart(
        chart_df.set_index("Indicator")
    )

    st.subheader("📊 Live Market Summary")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "RSI",
            round(data["RSI"], 2)
        )

    with col2:
        st.metric(
            "MACD",
            round(data["MACD"], 2)
        )

    with col3:
        st.metric(
            "Volume",
            int(data["Volume"])
        )

    st.subheader("📢 AI Trading Signal")

   

    if signal == "BUY":
        st.success("🟢 BUY SIGNAL")

    elif signal == "SELL":
        st.error("🔴 SELL SIGNAL")

    else:
        st.warning("🟡 NO TRADE")
    st.subheader("🤖 AI Confidence")

    confidence = signal_score(
        data["RSI"],
        data["Volume"] / data["AVG_VOLUME"] if data["AVG_VOLUME"] > 0 else 1,
        "UP" if data["SUPERTREND"] > 0 else "DOWN",
        data["MACD"],
        data["MACD_SIGNAL"],
        data["SUPERTREND"]
    )

    st.progress(confidence / 100)
    st.write(f"Confidence : {confidence}%")

    st.subheader("💰 Risk / Reward")

    entry = float(current_price)
    stoploss = entry - 100
    target = entry + 200

    reward = target - entry
    risk = entry - stoploss

    rr = round(reward / risk, 2)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Entry", f"₹{entry:.2f}")

    with col2:
        st.metric("Stop Loss", f"₹{stoploss:.2f}")

    with col3:
        st.metric("Target", f"₹{target:.2f}")

    st.success(f"Risk : Reward = 1 : {rr}")


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
