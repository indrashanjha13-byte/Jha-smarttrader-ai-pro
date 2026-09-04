import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from signals import get_signals
from ai_decision import ai_decision
import requests

def market_status_ribbon():
    c1, c2, c3, c4 = st.columns(4)
    c1.success("📈 NSE")
    c2.success("🏦 BANKNIFTY")
    c3.info("🤖 AI Scanner")
    c4.warning("📦 Option Chain")

def live_market_chart(
    symbol,
    trader,
    market_type="OPTIONS",
    futures_symbol=None,
    futures_price=0.0
):

    st.divider()
    st.header("📈 Live Market Chart")

    # =====================================================
    # DELTA FUTURES
    # =====================================================

    if market_type == "FUTURES":

        if not futures_symbol:
            st.warning("⚠️ No Futures contract selected")
            return 0.0

        current_price = float(
            futures_price or 0
        )

        if current_price <= 0:
            st.warning(
                f"⚠️ No live price available for "
                f"{futures_symbol}"
            )
            return 0.0

        support = round(
            current_price - 150,
            2
        )

        resistance = round(
            current_price + 150,
            2
        )

        c1, c2, c3, c4 = st.columns(4)

        c1.metric(
            "Contract",
            str(futures_symbol)
        )

        c2.metric(
            "Current",
            f"₹{current_price:.2f}"
        )

        c3.metric(
            "Support",
            f"₹{support:.2f}"
        )

        c4.metric(
            "Resistance",
            f"₹{resistance:.2f}"
        )

        st.info(
            "📦 Delta Futures live price"
        )

        return current_price


    # =====================================================
    # NORMAL / OPTIONS MARKET
    # =====================================================

    try:

        chart_data = yf.download(
            symbol,
            period="5d",
            interval="15m",
            auto_adjust=False,
            progress=False
        )

    except Exception as e:

        st.error(
            f"Error fetching data: {e}"
        )

        return 0.0


    if chart_data.empty:

        st.warning(
            "No Data Found"
        )

        return 0.0


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


    current_price = float(
        close.iloc[-1]
    )

    support = round(
        current_price - 150,
        2
    )

    resistance = round(
        current_price + 150,
        2
    )


    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Current",
        f"₹{current_price:.2f}"
    )

    c2.metric(
        "Support",
        f"₹{support:.2f}"
    )

    c3.metric(
        "Resistance",
        f"₹{resistance:.2f}"
    )

    c4.metric(
        "Balance",
        f"₹{getattr(trader, 'balance', 0):,.0f}"
    )


    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        row_heights=[
            0.75,
            0.25
        ],
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
        height=650,
        xaxis_rangeslider_visible=False,
        hovermode="x unified"
    )


    st.plotly_chart(
        fig,
        use_container_width=True
    )


    return current_price

def live_alerts(trader, current_price, signal):
    st.header("🔔 Live Alerts")
    alerts = []

    if signal == "BUY":
        alerts.append("🟢 BUY Signal Generated")
    elif signal == "SELL":
        alerts.append("🔴 SELL Signal Generated")
    elif signal == "HOLD":
        alerts.append("🟡 HOLD Signal")

    # Position Alerts safely checked
    if hasattr(trader, "position") and trader.position:
        try:
            target = trader.position.get("target")
            stoploss = trader.position.get("stoploss")
            if target and current_price >= target:
                alerts.append("🎯 Target Reached")
            elif stoploss and current_price <= stoploss:
                alerts.append("🛑 Stoploss Reached")
        except Exception:
            pass

    if alerts:
        for alert in alerts:
            st.success(alert)
    else:
        st.info("No Active Alerts")

def top_gainers_losers():
    st.header("📊 Top Gainers / Top Losers")

    symbols = [
        "RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS",
        "SBIN.NS", "LT.NS", "ICICIBANK.NS", "AXISBANK.NS"
    ]
    rows = []

    for s in symbols:
        try:
            d = yf.download(s, period="2d", interval="1d", progress=False)
            if len(d) >= 2:
                prev = float(d["Close"].iloc[-2])
                curr = float(d["Close"].iloc[-1])
                change = curr - prev
                percent = round((change / prev) * 100, 2)

                rows.append({
                    "Symbol": s.replace(".NS", ""),
                    "Price": round(curr, 2),
                    "Change %": percent
                })
        except Exception:
            pass

    if rows:
        df = pd.DataFrame(rows)
        gainers = df.sort_values("Change %", ascending=False).head(5)
        losers = df.sort_values("Change %", ascending=True).head(5)

        col1, col2 = st.columns(2)
        with col1:
            st.success("🟢 Top Gainers")
            st.dataframe(gainers, use_container_width=True)

        with col2:
            st.error("🔴 Top Losers")
            st.dataframe(losers, use_container_width=True)

def ai_market_scanner():
    st.header("🤖 AI Market Scanner")
    scan_symbols = [
        "^NSEI", "^NSEBANK", "RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS"
    ]
    scanner = []

    for s in scan_symbols:
        try:
            data = get_signals(s)
            if "error" in data:
                continue

            decision = ai_decision(
                rsi=data["RSI"],
                macd=data["MACD"],
                macd_signal=data["MACD_SIGNAL"],
                ema9=data["EMA9"],
                ema21=data["EMA21"],
                supertrend=data["SUPERTREND"],
                volume=data["Volume"],
                avg_volume=data["AVG_VOLUME"]
            )

            scanner.append({
                "Symbol": s.replace(".NS", ""),
                "Price": round(data.get("Close", 0), 2),
                "RSI": round(data.get("RSI", 0), 2),
                "Signal": decision.get("decision", "HOLD"),
                "Confidence": f"{decision.get('confidence', 0)}%"
            })
        except Exception:
            pass

    if scanner:
        df = pd.DataFrame(scanner)
        st.dataframe(df, use_container_width=True)

def market_news():
    st.header("📰 Market News")
    rss = "https://feeds.finance.yahoo.com/rss/2.0/headline?s=%5ENSEI&region=US&lang=en-US"

    try:
        import feedparser
        feed = feedparser.parse(rss)
        for item in feed.entries[:5]:
            st.markdown(f"### {item.title}")
            st.write(item.link)
            st.divider()
    except Exception:
        st.warning("News Not Available")

def market_page(
    symbol,
    trader,
    INDICES,
    FO_STOCKS,
    scan_all_option_chain,
    market_type="OPTIONS",
    futures_symbol=None,
    futures_price=0.0
):
    st.title("📈 Market")
    market_status_ribbon()
    st.divider()

    st.subheader("🇮🇳 Live Indices")
    index_list = {
        "NIFTY 50": "^NSEI",
        "BANKNIFTY": "^NSEBANK",
        "SENSEX": "^BSESN"
    }

    cols = st.columns(3)
    for i, (name, ticker) in enumerate(index_list.items()):
        try:
            data = yf.download(ticker, period="2d", interval="1d", progress=False)
            if len(data) >= 2:
                prev = float(data["Close"].iloc[-2])
                curr = float(data["Close"].iloc[-1])
                change = round(curr - prev, 2)
                percent = round((change / prev) * 100, 2)
                cols[i].metric(name, f"{curr:.2f}", f"{change:.2f} ({percent}%)")
            else:
                cols[i].metric(name, "No Data")
        except Exception:
            cols[i].metric(name, "No Data")

    st.divider()

    # =========================================================
    # DELTA FUTURES LIVE PRICE
    # =========================================================

    if market_type == "FUTURES" and futures_symbol:

        st.subheader("📦 Delta Futures")

        futures_col1, futures_col2 = st.columns(2)

        futures_col1.metric(
            "Contract",
            str(futures_symbol)
        )

        if futures_price and float(futures_price) > 0:

            futures_col2.metric(
                "Live Price",
                f"₹{float(futures_price):,.2f}"
            )

        else:

            futures_col2.metric(
                "Live Price",
                "No Data"
            )

    st.divider()

    st.header("📊 Live Option Chain")
    option_symbol = st.selectbox(
        "Select Option Symbol",
        INDICES + FO_STOCKS
    )

    if st.button("📡 Load Option Chain"):
        with st.spinner("Loading..."):
            data = scan_all_option_chain()

        if data and option_symbol in data:
            if "error" in data[option_symbol]:
                st.error(data[option_symbol]["error"])
            else:
                st.success("✅ Option Chain Loaded")
                st.json(data[option_symbol])

    # Safely get current price from live_market_chart
    current_price = live_market_chart(
        symbol,
        trader,
        market_type=market_type,
        futures_symbol=(
            futures_symbol
            if market_type == "FUTURES"
            else None
        ),
        futures_price=(
            futures_price
            if market_type == "FUTURES"
            else 0.0
        )
    )
    
    st.divider()
    top_gainers_losers()

    st.divider()
    ai_market_scanner()

    st.divider()
    data = get_signals(symbol)

    if "error" not in data:
        decision = ai_decision(
            rsi=data["RSI"],
            macd=data["MACD"],
            macd_signal=data["MACD_SIGNAL"],
            ema9=data["EMA9"],
            ema21=data["EMA21"],
            supertrend=data["SUPERTREND"],
            volume=data["Volume"],
            avg_volume=data["AVG_VOLUME"]
        )

        live_alerts(
            trader,
            current_price,
            decision.get(
                "decision",
                "HOLD"
            )
        )

    else:
        st.error(
            f"Signal Error: {data['error']}"
        )
    st.divider()