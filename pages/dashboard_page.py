import streamlit as st
from datetime import datetime, time
import os

import pandas as pd
import yfinance as yf

import plotly.express as px
import plotly.graph_objects as go

from ai_learning import (
    load_learning,
    best_strategy
)
from signals import get_signals
from ai_decision import ai_decision
from telegram_bot import send_alert
from option_chain_v2 import get_option_chain_summary
from option_chain_signal import option_ai_signal
from trade_manager import TradeManager
from trade_exit import exit_manager
from signals import get_signals

from strategy import (
    generate_signal,
    ema_signal,
    rsi_signal,
    supertrend_signal
)

from ai_engine import (
    ai_brain,
    confidence_score
)

from ai_learning import auto_strategy

from broker.broker_manager import BrokerManager
import config

manager = TradeManager()

def status_ribbon():

    c1, c2, c3, c4, c5 = st.columns(5)

    broker = BrokerManager(config.BROKER)

    if config.MODE == "PAPER":
        broker_status = "🟡 PAPER"
    else:
        if broker.broker.connected:
            broker_status = "🟢 CONNECTED"
        else:
            broker_status = "🔴 NOT CONNECTED"

    with c1:
        st.info(
            f"🏦 {config.BROKER}"
        )
        st.caption(broker_status)

    with c2:
        st.success("🟢 Market")

    with c3:
        st.info("🤖 AI")

    with c4:
        st.warning("⚙ Auto")

    with c5:
        st.success("📱 Telegram")

def account_summary(trader, current_price):

    balance = trader.balance

    if trader.position:

        position = trader.position["symbol"]

        pnl = (
            current_price
            - trader.position["entry"]
        ) * trader.position["qty"]

    else:

        position = "No Position"
        pnl = 0

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "💰 Balance",
        f"₹ {balance:.2f}"
    )

    c2.metric(
        "📦 Position",
        position
    )

    c3.metric(
        "📈 Live P&L",
        f"₹ {pnl:.2f}"
    )

    c4.metric(
        "💵 Cash",
        f"₹ {balance:.2f}"
    )

def live_index_cards():

    st.subheader("📊 Live Market")

    symbols = {
        "NIFTY": "^NSEI",
        "BANKNIFTY": "^NSEBANK",
        "SENSEX": "^BSESN"
    }

    cols = st.columns(3)

    for i, (name, ticker) in enumerate(symbols.items()):

        try:

            df = yf.download(
                ticker,
                period="2d",
                interval="1d",
                progress=False,
                auto_adjust=False
            )

            if len(df) >= 2:

                prev = float(df["Close"].iloc[-2])
                curr = float(df["Close"].iloc[-1])

                change = round(curr - prev, 2)
                pct = round((change / prev) * 100, 2)

                cols[i].metric(
                    name,
                    f"{curr:.2f}",
                    f"{pct}%"
                )

        except:

            cols[i].metric(
                name,
                "--",
                "--"
            )
def market_status():

    st.subheader("🟢 Market Status")

    now = datetime.now().time()

    market_open = time(9, 15)
    market_close = time(15, 30)

    if market_open <= now <= market_close:
        status = "🟢 OPEN"
    else:
        status = "🔴 CLOSED"

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "Market",
        status
    )

    c2.metric(
        "Time",
        datetime.now().strftime("%H:%M:%S")
    )

    c3.metric(
        "Date",
        datetime.now().strftime("%d-%b-%Y")
    )
def performance_report():

    st.subheader("📊 Performance Report")

    if not os.path.exists("trade_history.csv"):
        st.info("No Trade History Available")
        return

    trades = pd.read_csv("trade_history.csv")
    
    # =========================
    # Normalize PnL column
    # =========================

    if "PnL" not in trades.columns and "PNL" in trades.columns:
        trades = trades.rename(columns={"PNL": "PnL"})

    # Remove duplicate columns AFTER rename
    trades = trades.loc[:, ~trades.columns.duplicated(keep="first")]

    
    if "PnL" not in trades.columns:
        st.warning("No PnL data available yet.")
        return

    # Make sure PnL is numeric
    trades["PnL"] = pd.to_numeric(
        trades["PnL"],
        errors="coerce"
    ).fillna(0)

    total = len(trades)

    win = len(
        trades[trades["PnL"] > 0]
    )

    loss = len(
        trades[trades["PnL"] < 0]
    )

    net = trades["PnL"].sum()

    win_rate = (
        round((win / total) * 100, 2)
        if total > 0 else 0
    )

    # =========================
    # BUY / SELL
    # =========================

    buy = (
        len(trades[trades["Action"] == "BUY"])
        if "Action" in trades.columns
        else 0
    )

    sell = (
        len(trades[trades["Action"] == "SELL"])
        if "Action" in trades.columns
        else 0
    )

    # =========================
    # Profit Factor
    # =========================

    gross_profit = trades.loc[
        trades["PnL"] > 0,
        "PnL"
    ].sum()

    gross_loss = abs(
        trades.loc[
            trades["PnL"] < 0,
            "PnL"
        ].sum()
    )

    profit_factor = round(
        gross_profit / max(gross_loss, 1),
        2
    )

    # =========================
    # Drawdown
    # =========================

    drawdown = round(
        trades["PnL"].min(),
        2
    )

    # =========================
    # Display
    # =========================

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Total Trades",
        total
    )

    c2.metric(
        "Win Rate",
        f"{win_rate}%"
    )

    c3.metric(
        "Net P&L",
        f"₹ {net:.2f}"
    )

    c4.metric(
        "Profit Factor",
        profit_factor
    )

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "🟢 Wins",
        win
    )

    c2.metric(
        "🔴 Losses",
        loss
    )

    c3.metric(
        "📉 Max Drawdown",
        f"₹ {drawdown:.2f}"
    )

    st.write(
        f"🟢 BUY Orders: {buy}"
    )

    st.write(
        f"🔴 SELL Orders: {sell}"
    )
    st.subheader("📊 Performance Dashboard")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Trades", total)
    c2.metric("BUY", buy)
    c3.metric("SELL", sell)
    c4.metric("Wins", win)

    c5, c6, c7, c8 = st.columns(4)

    c5.metric("Loss", loss)
    c6.metric("Win %", f"{win_rate}%")
    c7.metric("Net Profit", f"₹{net:.2f}")
    c8.metric("Profit Factor", profit_factor)

    st.metric(
        "Max Drawdown",
        f"₹{drawdown}"
    )
    st.divider()

    st.subheader("📈 Equity Curve")

    if "PnL" not in trades.columns:
        trades["PnL"] = 0

    trades["PnL"] = pd.to_numeric(
        trades["PnL"],
        errors="coerce"
    ).fillna(0)

    equity = trades["PnL"].cumsum()


    fig = px.line(
        y=equity,
        title="Equity Curve"
    )
    
    st.plotly_chart(
        fig,
        width="stretch"
    )
    st.divider()

    st.subheader("🥧 Win / Loss Distribution")

    pie = pd.DataFrame({
        "Result": ["Win", "Loss"],
        "Count": [win, loss]
    })

    fig2 = px.pie(
        pie,
        names="Result",
        values="Count",
        title="Win vs Loss"
    )

    st.plotly_chart(
        fig2,
        use_container_width=True
    )
   
def monthly_pnl():

    st.subheader("📅 Monthly P&L")

    if not os.path.exists("trade_history.csv"):

        st.info("No Monthly P&L Data")
        return

    history = pd.read_csv("trade_history.csv")

    if "Date" in history.columns:
        history["Date"] = pd.to_datetime(
            history["Date"],
            errors="coerce"
        )

    elif "Time" in history.columns:
        history["Date"] = pd.to_datetime(
            history["Time"],
            errors="coerce"
        )

    else:
        st.warning("No Date/Time column found.")
        return
    if "PNL" not in history.columns:
        st.info("No PnL Data Yet")
        return

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
        width="stretch"
    )

    fig = px.bar(
        monthly,
        x="Month",
        y="PNL",
        title="Monthly Profit / Loss"
    )

    st.plotly_chart(
        fig,
        width="stretch"
    )
def dashboard_page(
    trader,
    current_price,
    symbol
):

    st.title("📈 Jha SmartTrader AI Pro")

    st.session_state.setdefault("scanner_df", pd.DataFrame())

    status_ribbon()

    st.caption("AI Powered Intraday Trading Dashboard")

    st.divider()

    account_summary(
        trader,
        current_price
    )

    st.divider()

    market_status()

    st.divider()

    performance_report()

    st.divider()

    monthly_pnl()

    st.divider()

    st.subheader("💰 Live Paper Trading")

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "Balance",
        f"₹ {trader.balance:.2f}"
    )

    if trader.position:

        c2.metric(
            "Position",
            trader.position["symbol"]
        )

        live_pnl = (
            current_price -
            trader.position["entry"]
        ) * trader.position["qty"]

        c3.metric(
            "Live P&L",
            f"₹ {live_pnl:.2f}"
        )

    else:

        c2.metric(
            "Position",
            "None"
        )

        c3.metric(
            "Live P&L",
            "₹ 0"
        )

        st.divider()

        st.subheader("📦 Portfolio")

    if trader.position:

        st.success(
            f"Open Position : {trader.position['symbol']}"
        )

        st.write(
            f"Qty : {trader.position['qty']}"
        )

        st.write(
            f"Entry Price : ₹ {trader.position['entry']}"
        )

    else:

        st.info("No Open Position")

    # =====================
    # AI Learning
    # =====================

    st.subheader("🧠 AI Learning")

    learning = load_learning()

    st.write(
        "Wins :",
        learning.get("wins", 0)
    )

    st.write(
        "Losses :",
        learning.get("losses", 0)
    )

    best = best_strategy()

    if best != "No Data":

        strategy, acc = best

        st.success(
            f"🏆 Best Strategy : {strategy}"
        )

        st.info(
            f"Accuracy : {acc}%"
        )

    else:

        st.warning(
            "AI has not learned yet."
        )
    st.divider()

    st.subheader("📈 AI Confidence")

    best = best_strategy()

    if best == "No Data":

        st.progress(0)

        st.metric(
            "Confidence",
            "0%"
        )

    else:

        strategy, acc = best

        st.progress(acc / 100)

        st.metric(
            "Confidence",
            f"{acc}%"
        )

    st.divider()

    st.subheader("⚙ Auto Trading")

    col1, col2 = st.columns(2)

    with col1:
        st.metric("Status", "🔴 STOPPED")

    with col2:
        st.metric("Mode", "Paper Trading")

    st.divider()

    st.subheader("📱 Telegram")

    st.metric("Alerts", "ON")

    st.divider()

    st.subheader("🏦 Broker")

    st.metric("Broker", "Kotak Neo")

    st.divider()

    st.subheader("📦 Portfolio")

    if trader.position:

        portfolio = pd.DataFrame([
            {
                "Symbol": trader.position["symbol"],
                "Qty": trader.position["qty"],
                "Entry": trader.position["entry"],
                "Current": round(current_price, 2),
                "P&L": round(
                    (current_price - trader.position["entry"])
                    * trader.position["qty"],
                    2
                )
            }
        ])

        st.dataframe(
            portfolio,
            width="stretch"
        )

    else:

        st.info("No Holdings Available")
        
    st.divider()

    st.subheader("🛡 Risk Manager")

    risk = 2

    capital = trader.balance

    max_loss = capital * risk / 100

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
        "Risk Per Trade",
        f"{risk}%"
    )

    with col2:
        st.metric(
            "Capital",
            f"₹ {capital:,.0f}"
        )
    with col3:
        st.metric(
            "Maximum Loss",
            f"₹ {max_loss:,.0f}"
        )
    st.divider()

    st.subheader("📏 Position Size Calculator")

    capital = trader.balance

    entry = st.number_input(
        "Entry Price",
        value=100.0
    )

    stop = st.number_input(
        "Stop Loss",
        value=95.0
    )

    risk_percent = st.slider(
        "Risk %",
        1,
        5,
        2
    )

    risk_amount = capital * risk_percent / 100

    risk_per_share = abs(entry - stop)

    if risk_per_share > 0:
        qty = int(risk_amount / risk_per_share)
    else:
        qty = 0

    st.metric("Suggested Quantity", qty)

    st.divider()

    st.subheader("🤖 AI Signal")

    signal = "HOLD"
    confidence = 0
    strategy = "None"

    best = best_strategy()

    if best != "No Data":
        strategy, confidence = best

        if confidence >= 80:
            signal = "🟢 BUY"
        elif confidence >= 60:
            signal = "🟡 HOLD"
        else:
            signal = "🔴 SELL"

    c1, c2, c3 = st.columns(3)

    with c1:
        st.metric("Signal", signal)

    with c2:
        st.metric("Confidence", f"{confidence}%")

    with c3:
        st.metric("Strategy", strategy)

    st.divider()

    # =====================
    # Live Market Chart
    # =====================

    st.subheader("📈 Live Market Chart")

    chart_data = yf.download(

        symbol,

        period="5d",

        interval="15m",

        auto_adjust=False

    )

    if not chart_data.empty:

        if isinstance(
            chart_data.columns,
            pd.MultiIndex
        ):

            chart_data.columns = (
                chart_data.columns
                .get_level_values(0)
            )

        close = chart_data["Close"]

        ema9 = close.ewm(
            span=9
        ).mean()

        ema21 = close.ewm(
            span=21
        ).mean()

        fig = go.Figure()

        fig.add_trace(

            go.Candlestick(

                x=chart_data.index,

                open=chart_data["Open"],

                high=chart_data["High"],

                low=chart_data["Low"],

                close=chart_data["Close"],

                name="Price"

            )

        )

        fig.add_trace(

            go.Scatter(

                x=chart_data.index,

                y=ema9,

                name="EMA 9"

            )

        )

        fig.add_trace(

            go.Scatter(

                x=chart_data.index,

                y=ema21,

                name="EMA 21"

            )

        )

        fig.add_trace(

            go.Bar(

                x=chart_data.index,

                y=chart_data["Volume"],

                name="Volume",

                marker_color="royalblue",

                opacity=0.3,

                yaxis="y2"

            )

        )

        fig.update_layout(

            template="plotly_dark",

            height=650,

            xaxis_rangeslider_visible=False,

            yaxis=dict(title="Price"),

            yaxis2=dict(

                title="Volume",

                overlaying="y",

                side="right",

                showgrid=False

            )

        )

        st.plotly_chart(

            fig,

            use_container_width=True

        )

        st.divider()

        st.subheader("📊 Top Gainers / Top Losers")

        top_stocks = [
            "RELIANCE.NS",
            "TCS.NS",
            "INFY.NS",
            "HDFCBANK.NS",
            "SBIN.NS",
            "LT.NS"
        ]

        rows = []

        for s in top_stocks:
            try:
                d = yf.download(
                    s,
                    period="2d",
                    interval="1d",
                    progress=False
                )

                if len(d) >= 2:
                    prev = float(d["Close"].iloc[-2])
                    curr = float(d["Close"].iloc[-1])

                    change = round(
                        ((curr - prev) / prev) * 100,
                        2
                    )

                    rows.append({
                        "Symbol": s,
                        "Price": curr,
                        "Change %": change
                    })

            except:
                pass

            if rows:

                df = pd.DataFrame(rows)

                df = df.sort_values(
                    "Change %",
                    ascending=False
                )

                st.dataframe(
                    df,
                    use_container_width=True
                )

           

        st.subheader("🤖 AI Market Scanner")

# ==========================
# Scanner Filters
# ==========================

        st.subheader("🎯 Scanner Filters")

        col1, col2, col3 = st.columns(3)

        with col1:
            signal_filter = st.selectbox(
                "Signal",
                ["ALL", "BUY", "SELL", "HOLD"]
            )

        with col2:
            min_confidence = st.slider(
                "Min Confidence",
                50,
                100,
                70
            )

        with col3:
            trend_filter = st.selectbox(
                "Trend",
                ["ALL", "Bullish", "Bearish", "Sideways"]
            )

        def run_scanner():

            scanner = []
            
            watchlist = [
                "RELIANCE.NS",
                "TCS.NS",
                "INFY.NS",
                "HDFCBANK.NS",
                "SBIN.NS"
            ]

            for stock in watchlist:

                st.write(f"Scanning: {stock}")

                try:
                    data = yf.download(
                        stock,
                        period="2d",
                        interval="15m",
                        progress=False
                    )

                    
                    st.write(stock, len(data))

                    if not data.empty:

                        if isinstance(data.columns, pd.MultiIndex):
                            data.columns = data.columns.get_level_values(0)

                        
                        close = float(data["Close"].iloc[-1])

                        print(f"Scanning {stock}")

                        signal = get_signals(stock)

                        print(signal)

                        
                        if "error" in signal:
                            st.write(f"Signal Error for {stock}: {signal['error']}")
                            continue

                       
                        ai = ai_decision(
                            rsi=signal["RSI"],
                            macd=signal["MACD"],
                            macd_signal=signal["MACD_SIGNAL"],
                            ema9=signal["EMA9"],
                            ema21=signal["EMA21"],
                            supertrend=signal["SUPERTREND"],
                            volume=signal["Volume"],
                            avg_volume=signal["AVG_VOLUME"]
                        )

                        
                        st.write(ai)

                        decision = ai["decision"]
                        confidence = ai["confidence"]

                        manager.process(
                            stock,
                            decision,
                            close,
                            qty
                        )
                        
                        if exit_manager.trade_open:

                            result = exit_manager.check(close)

                            if result == "TARGET":
                                st.success("🎯 Target Hit! Trade Closed")

                            elif result == "STOPLOSS":
                                st.error("🛑 Stop Loss Hit! Trade Closed")

                        if decision == "BUY":
                            signal_icon = "🟢 BUY"

                        elif decision == "SELL":
                            signal_icon = "🔴 SELL"
                        else:

                            signal_icon = "🟡 HOLD"

                        if signal["EMA9"] > signal["EMA21"]:
                            trend = "📈 Bullish"

                        elif signal["EMA9"] < signal["EMA21"]:
                            trend = "📉 Bearish"

                        else:
                            trend = "➡ Sideways"

                        scanner.append({
                            "Symbol": stock.replace(".NS", ""),
                            "Price": round(close, 2),
                            "Signal": signal_icon,
                            "Confidence": confidence,
                            "Trend": trend,
                            "RSI": round(signal["RSI"], 2),
                            "MACD": round(signal["MACD"], 2),
                            "Volume": signal["Volume"]
                        })

                        print("===================================")
                        print(stock)
                        print(scanner)
                        print("Length =", len(scanner))
                        print("===================================")

                        st.success(f"{stock} Added")
                       
                        message = f"""
                        🚀 Jha SmartTrader AI Pro

                        📈 Stock : {stock.replace('.NS','')}

                        📊 Signal : {signal_icon}

                        💰 Price : ₹{round(close,2)}

                        🔥 Confidence : {confidence}%

                        📈 Trend : {trend}

                        📉 RSI : {round(signal['RSI'],2)}

                        📊 MACD : {round(signal['MACD'],2)}
                        """
                        
                        if decision != "HOLD":
                            send_alert(message)
                       
                except Exception as e:
                    import traceback

                    st.error(f"{stock} Error: {e}")

                    st.code(traceback.format_exc())

            if scanner:

                scanner_df = pd.DataFrame(scanner)

                print(scanner_df)

                scanner_df = scanner_df.sort_values(
                    by="Confidence",
                    ascending=False
                )
                
                st.write("Scanner List")
                st.write(scanner)

                st.write("Scanner DataFrame")
                st.dataframe(scanner_df)

            # ==========================
            # Apply Scanner Filters
            # ==========================

            if signal_filter != "ALL":
                scanner_df = scanner_df[
                    scanner_df["Signal"].str.contains(signal_filter)
                ]

            scanner_df = scanner_df[
                scanner_df["Confidence"] >= min_confidence
            ]

            if trend_filter != "ALL":
                scanner_df = scanner_df[
                    scanner_df["Trend"].str.contains(trend_filter)
                ]

            st.success(f"Scanner Finished ✅ ({len(scanner_df)} Stocks)")

            st.dataframe(
                scanner_df,
                width="stretch"
            )

            if not scanner_df.empty:

                buy_count = len(scanner_df[scanner_df["Signal"] == "🟢 BUY"])
                sell_count = len(scanner_df[scanner_df["Signal"] == "🔴 SELL"])
                hold_count = len(scanner_df[scanner_df["Signal"] == "🟡 HOLD"])

                st.divider()

                st.subheader("📊 Scanner Summary")

                c1, c2, c3 = st.columns(3)

                c1.metric("🟢 BUY", buy_count)
                c2.metric("🔴 SELL", sell_count)
                c3.metric("🟡 HOLD", hold_count)

                best_stock = scanner_df.iloc[0]

                st.success(
                    f"🏆 Highest Confidence : {best_stock['Symbol']} ({best_stock['Confidence']}%)"
                )
        # ==========================
        # Export Scanner Report
        # ==========================

                st.divider()

                csv = scanner_df.to_csv(index=False).encode("utf-8")

                st.download_button(
                    label="📥 Download Scanner Report",
                    data=csv,
                    file_name="scanner_report.csv",
                    mime="text/csv"
                )

            else:

                st.warning("No Strong Signals Found")
                
        # ==========================
        # RUN SCANNER BUTTON
        # ==========================

        if st.button("▶ Run Scanner"):
            run_scanner()

            st.divider()
        
            st.subheader("📜 Trade History")
        
            if os.path.exists("trade_history.csv"):
        
                history = pd.read_csv("trade_history.csv")
        
                st.dataframe(
                    history,
                    use_container_width=True
                )
        
            else:
        
                st.info("No Trade History Found")
                
        st.divider()

        st.subheader("📊 Option Chain AI")

        option = get_option_chain_summary()

        if "error" not in option:

            ai = option_ai_signal(option["PCR"])

            c1, c2, c3 = st.columns(3)

            c1.metric("Spot", option["Spot"])
            c2.metric("ATM", option["ATM"])
            c3.metric("PCR", option["PCR"])

            st.metric("AI Signal", ai["Signal"])
            st.progress(ai["Confidence"] / 100)

        else:
            st.error(option["error"])


    st.divider()

    st.subheader("🤖 AI Prediction")

    try:

        best = best_strategy()

        if best == "No Data":

            st.info("AI has not learned yet.")

        else:

            strategy, acc = best

            c1, c2 = st.columns(2)

            c1.metric(
                "Best Strategy",
                strategy
            )

            c2.metric(
                "Accuracy",
                f"{acc}%"
            )

    except Exception as e:

        st.error(f"AI Prediction Error: {e}")

    st.divider() 

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.button("🟢 Buy")

    with c2:
        st.button("🔴 Sell")

    with c3:
        st.button("📊 Refresh")

    with c4:
        st.button("📥 Export Report")

        st.divider()

    st.caption(

        f"Last Refresh : {datetime.now()}"

    )
    
   