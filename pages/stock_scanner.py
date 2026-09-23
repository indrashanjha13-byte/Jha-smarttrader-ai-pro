import streamlit as st
import pandas as pd

from stock_ai_scanner import (
    scan_stocks,
    filter_signals,
)


st.set_page_config(
    page_title="Stock AI Scanner",
    page_icon="📊",
    layout="wide",
)


st.title("📊 Stock AI Scanner")
st.caption(
    "AI-powered BUY / SELL / HOLD stock scanner"
)


# =========================================================
# SETTINGS
# =========================================================

st.sidebar.header("⚙️ Scanner Settings")

stock_count = st.sidebar.selectbox(
    "Stocks to Scan",
    [5, 10, 20, 50],
    index=0,
)

interval = st.sidebar.selectbox(
    "Timeframe",
    ["5m", "15m", "1h", "1d"],
    index=0,
)

period = st.sidebar.selectbox(
    "Data Period",
    ["5d", "1mo", "3mo"],
    index=0,
)

min_confidence = st.sidebar.slider(
    "Minimum Confidence",
    50,
    100,
    65,
    5,
)

signal_filter = st.sidebar.selectbox(
    "Signal Filter",
    [
        "ALL",
        "BUY",
        "SELL",
        "HOLD",
    ],
)


# =========================================================
# STOCK UNIVERSE
# =========================================================

from stock_ai_scanner import NSE_STOCKS


symbols = list(NSE_STOCKS)


# फिलहाल testing के लिए limited stocks
symbols = symbols[:stock_count]


st.sidebar.write(
    f"Available Universe: {len(NSE_STOCKS)}"
)

st.sidebar.write(
    f"Current Scan: {len(symbols)} stocks"
)


# =========================================================
# RUN SCANNER
# =========================================================

if st.button(
    "🔍 RUN AI STOCK SCAN",
    type="primary",
    use_container_width=True,
):

    with st.spinner(
        f"Scanning {len(symbols)} stocks..."
    ):

        try:

            df = scan_stocks(
                symbols=symbols,
                interval=interval,
                period=period,
                max_workers=8,
            )

        except Exception as exc:

            st.error(
                f"Scanner Error: {exc}"
            )

            st.stop()


    if df is None or df.empty:

        st.warning(
            "No stock data returned."
        )

        st.stop()


    # =====================================================
    # FILTER
    # =====================================================

    try:

        filtered_df = filter_signals(
            df,
            signal=signal_filter,
            min_confidence=min_confidence,
        )

    except Exception:

        filtered_df = df.copy()

        if signal_filter != "ALL":

            filtered_df = filtered_df[
                filtered_df["signal"]
                .astype(str)
                .str.upper()
                == signal_filter
            ]

        if "confidence" in filtered_df.columns:

            filtered_df = filtered_df[
                pd.to_numeric(
                    filtered_df["confidence"],
                    errors="coerce",
                ).fillna(0)
                >= min_confidence
            ]


    # =====================================================
    # SUMMARY
    # =====================================================

    signals = (
        df["signal"]
        .astype(str)
        .str.upper()
        if "signal" in df.columns
        else pd.Series(dtype=str)
    )


    buy_count = int(
        (signals == "BUY").sum()
    )

    sell_count = int(
        (signals == "SELL").sum()
    )

    hold_count = int(
        (signals == "HOLD").sum()
    )


    col1, col2, col3, col4 = st.columns(4)


    col1.metric(
        "📊 Scanned",
        len(df),
    )

    col2.metric(
        "🟢 AI BUY",
        buy_count,
    )

    col3.metric(
        "🔴 AI SELL",
        sell_count,
    )

    col4.metric(
        "🟡 HOLD",
        hold_count,
    )


    st.divider()


    # =====================================================
    # FORMAT DISPLAY
    # =====================================================

    preferred_columns = [

        "rank",
        "symbol",
        "signal",
        "confidence",
        "score",
        "price",
        "entry",
        "stop_loss",
        "target",
        "rsi",
        "volume_ratio",
        "trend",
        "macd",
        "macd_signal",
        "supertrend",

    ]


    display_columns = [

        column
        for column in preferred_columns
        if column in filtered_df.columns

    ]


    display_df = (
        filtered_df[display_columns].copy()
        if display_columns
        else filtered_df.copy()
    )


    # =====================================================
    # NUMBER FORMATTING
    # =====================================================

    for column in [

        "confidence",
        "score",
        "price",
        "entry",
        "stop_loss",
        "target",
        "rsi",
        "volume_ratio",
        "macd",
        "macd_signal",
        "supertrend",

    ]:

        if column in display_df.columns:

            display_df[column] = pd.to_numeric(
                display_df[column],
                errors="coerce",
            )


    # =====================================================
    # MAIN TABLE
    # =====================================================

    st.subheader(
        f"📋 AI Signals ({len(display_df)})"
    )


    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
    )


    # =====================================================
    # BUY STOCKS
    # =====================================================

    buy_df = df[
        df["signal"]
        .astype(str)
        .str.upper()
        == "BUY"
    ] if "signal" in df.columns else pd.DataFrame()


    if not buy_df.empty:

        st.subheader(
            "🟢 Top AI BUY Stocks"
        )


        buy_display = (
            buy_df[display_columns]
            if display_columns
            else buy_df
        )


        st.dataframe(
            buy_display,
            use_container_width=True,
            hide_index=True,
        )


    # =====================================================
    # SELL STOCKS
    # =====================================================

    sell_df = df[
        df["signal"]
        .astype(str)
        .str.upper()
        == "SELL"
    ] if "signal" in df.columns else pd.DataFrame()


    if not sell_df.empty:

        st.subheader(
            "🔴 Top AI SELL Stocks"
        )


        sell_display = (
            sell_df[display_columns]
            if display_columns
            else sell_df
        )


        st.dataframe(
            sell_display,
            use_container_width=True,
            hide_index=True,
        )


    # =====================================================
    # CSV EXPORT
    # =====================================================

    csv_data = filtered_df.to_csv(
        index=False
    )


    st.download_button(
        "⬇️ Download Scan CSV",
        csv_data,
        file_name="stock_ai_scan.csv",
        mime="text/csv",
    )


else:

    st.info(
        "Click **RUN AI STOCK SCAN** "
        "to start."
    )


    st.markdown(
        """
## 🚀 Stock AI Scanner

यह scanner stocks को analyse करेगा:

- 🟢 AI BUY
- 🔴 AI SELL
- 🟡 HOLD
- 📊 Confidence
- ⭐ AI Score
- 💰 Current Price
- 🎯 Entry
- 🛑 Stop Loss
- 🎯 Target
- RSI
- MACD
- Volume
- Trend
- SuperTrend

### Current Stage

पहले scanner engine को छोटे stock batch पर test किया जा रहा है।

उसके बाद इसी system को **3000+ stocks** तक expand किया जाएगा।
"""
    )