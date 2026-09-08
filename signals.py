import logging
import math
import time as time_module

import pandas as pd
import requests
import yfinance as yf
import pandas_ta as ta


# =========================================================
# Logging
# =========================================================

logger = logging.getLogger(__name__)


# =========================================================
# Delta Exchange
# =========================================================

DELTA_24X7_SYMBOLS = {
    "BTCUSD",
    "ETHUSD",
    "1000BONKUSD",
}


DELTA_API_BASE = (
    "https://api.india.delta.exchange"
)


# =========================================================
# Safe Number Helper
# =========================================================

def safe_float(value, default=0.0):

    try:

        if value is None:
            return default

        value = float(value)

        if math.isnan(value) or math.isinf(value):
            return default

        return value

    except Exception:

        return default


# =========================================================
# Delta Symbol Check
# =========================================================

def is_delta_symbol(symbol):

    try:

        symbol = str(
            symbol or ""
        ).strip().upper()

        if not symbol:
            return False

        if symbol in DELTA_24X7_SYMBOLS:
            return True

        return symbol.endswith("USD")

    except Exception:

        return False


# =========================================================
# Delta Resolution
# =========================================================

def normalize_delta_resolution(interval):

    interval = str(
        interval or "5m"
    ).strip().lower()

    supported = {
        "1m",
        "3m",
        "5m",
        "15m",
        "30m",
        "1h",
        "2h",
        "4h",
        "6h",
        "1d",
        "1w",
    }

    if interval not in supported:
        return "5m"

    return interval


# =========================================================
# Delta Resolution Seconds
# =========================================================

DELTA_INTERVAL_SECONDS = {

    "1m": 60,

    "3m": 180,

    "5m": 300,

    "15m": 900,

    "30m": 1800,

    "1h": 3600,

    "2h": 7200,

    "4h": 14400,

    "6h": 21600,

    "1d": 86400,

    "1w": 604800,
}


# =========================================================
# Parse Delta Candle
# =========================================================

def parse_delta_candle(candle):

    try:

        # -------------------------------------------------
        # Delta API normally returns dictionary candles.
        # -------------------------------------------------

        if isinstance(candle, dict):

            timestamp = (
                candle.get("time")
                or candle.get("timestamp")
                or candle.get("start")
            )

            open_price = (
                candle.get("open")
            )

            high_price = (
                candle.get("high")
            )

            low_price = (
                candle.get("low")
            )

            close_price = (
                candle.get("close")
            )

            volume = (
                candle.get("volume")
                or candle.get("vol")
                or 0
            )

        # -------------------------------------------------
        # Some API responses can be list based.
        # -------------------------------------------------

        elif isinstance(candle, (list, tuple)):

            if len(candle) < 5:
                return None

            timestamp = candle[0]
            open_price = candle[1]
            high_price = candle[2]
            low_price = candle[3]
            close_price = candle[4]

            volume = (
                candle[5]
                if len(candle) > 5
                else 0
            )

        else:

            return None

        timestamp = safe_float(
            timestamp,
            0.0
        )

        open_price = safe_float(
            open_price,
            0.0
        )

        high_price = safe_float(
            high_price,
            0.0
        )

        low_price = safe_float(
            low_price,
            0.0
        )

        close_price = safe_float(
            close_price,
            0.0
        )

        volume = safe_float(
            volume,
            0.0
        )

        if timestamp <= 0:
            return None

        if (
            open_price <= 0
            or high_price <= 0
            or low_price <= 0
            or close_price <= 0
        ):
            return None

        # -------------------------------------------------
        # Delta timestamps are normally seconds.
        # Protect against millisecond timestamps.
        # -------------------------------------------------

        if timestamp > 10_000_000_000:

            timestamp = timestamp / 1000.0

        candle_time = pd.to_datetime(
            timestamp,
            unit="s",
            utc=True
        )

        return {

            "Time": candle_time,

            "Open": open_price,

            "High": high_price,

            "Low": low_price,

            "Close": close_price,

            "Volume": volume,
        }

    except Exception as e:

        logger.debug(
            f"Delta candle parse error: {e}"
        )

        return None


# =========================================================
# Download Delta Futures Data
# =========================================================

def download_delta_data(
    symbol,
    interval="5m",
    candle_count=1000,
):

    try:

        symbol = str(
            symbol or ""
        ).strip().upper()

        resolution = (
            normalize_delta_resolution(
                interval
            )
        )

        endpoint = (
            f"{DELTA_API_BASE}"
            "/v2/history/candles"
        )

        end_time = int(
            time_module.time()
        )

        seconds = (
            DELTA_INTERVAL_SECONDS.get(
                resolution,
                300
            )
        )

        # -------------------------------------------------
        # Request enough historical candles.
        # -------------------------------------------------

        start_time = (
            end_time
            - (
                int(candle_count)
                * seconds
            )
        )

        params = {

            "resolution": resolution,

            "symbol": symbol,

            "start": start_time,

            "end": end_time,
        }

        headers = {

            "Accept": "application/json",

            "User-Agent":
                "JhaSmartTraderAIPro/1.0",
        }

        logger.info(
            f"Delta request: "
            f"{symbol} | "
            f"{resolution}"
        )

        response = requests.get(

            endpoint,

            params=params,

            headers=headers,

            timeout=15,
        )

        response.raise_for_status()

        data = response.json()

        if not isinstance(data, dict):

            logger.warning(
                f"Invalid Delta response "
                f"for {symbol}"
            )

            return None

        if not data.get("success"):

            logger.warning(
                f"Delta API returned failure "
                f"for {symbol}: {data}"
            )

            return None

        candles = data.get(
            "result",
            []
        )

        if not candles:

            logger.warning(
                f"No Delta candles returned "
                f"for {symbol}"
            )

            return None

        rows = []

        for candle in candles:

            parsed = parse_delta_candle(
                candle
            )

            if parsed is not None:

                rows.append(parsed)

        if not rows:

            logger.warning(
                f"Unable to parse Delta candles "
                f"for {symbol}"
            )

            return None

        df = pd.DataFrame(
            rows
        )

        # -------------------------------------------------
        # Datetime
        # -------------------------------------------------

        df["Time"] = pd.to_datetime(
            df["Time"],
            utc=True,
            errors="coerce"
        )

        df.dropna(
            subset=["Time"],
            inplace=True
        )

        df.set_index(
            "Time",
            inplace=True
        )

        # -------------------------------------------------
        # Sort
        # -------------------------------------------------

        df.sort_index(
            inplace=True
        )

        # -------------------------------------------------
        # Remove duplicates
        # -------------------------------------------------

        df = df[
            ~df.index.duplicated(
                keep="last"
            )
        ]

        # -------------------------------------------------
        # Numeric columns
        # -------------------------------------------------

        required_columns = [

            "Open",
            "High",
            "Low",
            "Close",
            "Volume",
        ]

        for column in required_columns:

            df[column] = pd.to_numeric(

                df[column],

                errors="coerce"
            )

        # -------------------------------------------------
        # Remove invalid OHLC
        # -------------------------------------------------

        df.dropna(

            subset=[
                "Open",
                "High",
                "Low",
                "Close",
            ],

            inplace=True
        )

        # -------------------------------------------------
        # Keep positive prices
        # -------------------------------------------------

        df = df[
            (df["Open"] > 0)
            & (df["High"] > 0)
            & (df["Low"] > 0)
            & (df["Close"] > 0)
        ]

        if df.empty:

            return None

        logger.info(

            f"Delta data loaded: "
            f"{symbol} | "
            f"{len(df)} candles | "
            f"Last: {df['Close'].iloc[-1]}"
        )

        return df

    except Exception as e:

        logger.exception(

            f"Delta data download error "
            f"for {symbol}: {e}"
        )

        return None


# =========================================================
# Download Yahoo Finance Data
# =========================================================

def download_yahoo_data(
    symbol,
    period="30d",
    interval="5m",
):

    try:

        df = yf.download(

            symbol,

            period=period,

            interval=interval,

            auto_adjust=False,

            progress=False,

            threads=False,
        )

        if df is None or df.empty:

            logger.warning(
                f"No Yahoo data returned "
                f"for {symbol}"
            )

            return None

        # -------------------------------------------------
        # Fix MultiIndex
        # -------------------------------------------------

        if isinstance(
            df.columns,
            pd.MultiIndex
        ):

            df.columns = [

                column[0]
                if isinstance(
                    column,
                    tuple
                )
                else column

                for column in df.columns
            ]

        # -------------------------------------------------
        # Remove duplicate columns
        # -------------------------------------------------

        df = df.loc[

            :,

            ~df.columns.duplicated()
        ]

        required_columns = [

            "Open",
            "High",
            "Low",
            "Close",
            "Volume",
        ]

        for column in required_columns:

            if column not in df.columns:

                logger.warning(

                    f"Missing column "
                    f"{column} for {symbol}"
                )

                return None

        df = df[
            required_columns
        ].copy()

        for column in required_columns:

            df[column] = pd.to_numeric(

                df[column],

                errors="coerce"
            )

        df.dropna(

            subset=[
                "Open",
                "High",
                "Low",
                "Close",
            ],

            inplace=True
        )

        if df.empty:

            return None

        return df

    except Exception as e:

        logger.exception(

            f"Yahoo data download error "
            f"for {symbol}: {e}"
        )

        return None


# =========================================================
# Main Market Data Downloader
# =========================================================

def download_data(
    symbol,
    period="30d",
    interval="5m",
):

    try:

        symbol = str(
            symbol or ""
        ).strip().upper()

        if not symbol:

            return None

        # -------------------------------------------------
        # Delta Futures
        # -------------------------------------------------

        if is_delta_symbol(symbol):

            return download_delta_data(

                symbol,

                interval=interval,

                candle_count=1000,
            )

        # -------------------------------------------------
        # Indian / Yahoo Finance
        # -------------------------------------------------

        return download_yahoo_data(

            symbol,

            period=period,

            interval=interval,
        )

    except Exception as e:

        logger.exception(
            f"Market data error for "
            f"{symbol}: {e}"
        )

        return None


# =========================================================
# Indicator Calculation
# =========================================================

def calculate_indicators(df):

    try:

        if df is None or df.empty:

            return None

        df = df.copy()

        close = pd.to_numeric(
            df["Close"],
            errors="coerce"
        )

        high = pd.to_numeric(
            df["High"],
            errors="coerce"
        )

        low = pd.to_numeric(
            df["Low"],
            errors="coerce"
        )

        volume = pd.to_numeric(
            df["Volume"],
            errors="coerce"
        )

        # =================================================
        # EMA 9
        # =================================================

        df["EMA9"] = ta.ema(
            close,
            length=9
        )

        # =================================================
        # EMA 21
        # =================================================

        df["EMA21"] = ta.ema(
            close,
            length=21
        )

        # =================================================
        # RSI 14
        # =================================================

        df["RSI"] = ta.rsi(
            close,
            length=14
        )

        # =================================================
        # MACD
        # =================================================

        macd = ta.macd(

            close,

            fast=12,

            slow=26,

            signal=9
        )

        df["MACD"] = 0.0

        df["MACD_SIGNAL"] = 0.0

        df["MACD_HIST"] = 0.0

        if (
            macd is not None
            and not macd.empty
        ):

            for column in macd.columns:

                name = str(
                    column
                )

                if name.startswith(
                    "MACD_"
                ) and not name.startswith(
                    "MACDh"
                ) and not name.startswith(
                    "MACDs"
                ):

                    df["MACD"] = macd[
                        column
                    ]

                elif name.startswith(
                    "MACDs"
                ):

                    df["MACD_SIGNAL"] = macd[
                        column
                    ]

                elif name.startswith(
                    "MACDh"
                ):

                    df["MACD_HIST"] = macd[
                        column
                    ]

        # -------------------------------------------------
        # MACD histogram fallback
        # -------------------------------------------------

        df["MACD_HIST"] = (

            df["MACD"]

            - df["MACD_SIGNAL"]
        )

        # =================================================
        # SuperTrend
        # =================================================

        supertrend = ta.supertrend(

            high,

            low,

            close,

            length=10,

            multiplier=3.0
        )

        df["ST_DIRECTION"] = 0.0

        df["SUPERTREND"] = close

        if (
            supertrend is not None
            and not supertrend.empty
        ):

            for column in supertrend.columns:

                name = str(
                    column
                )

                if name.startswith(
                    "SUPERTd"
                ):

                    df["ST_DIRECTION"] = (
                        supertrend[column]
                    )

                elif (

                    name.startswith(
                        "SUPERT_"
                    )

                    and not name.startswith(
                        "SUPERTd"
                    )

                    and not name.startswith(
                        "SUPERTl"
                    )

                    and not name.startswith(
                        "SUPERTs"
                    )

                ):

                    df["SUPERTREND"] = (
                        supertrend[column]
                    )

        # =================================================
        # Average Volume
        # =================================================

        df["AVG_VOLUME"] = (

            volume.rolling(

                window=20,

                min_periods=20
            ).mean()
        )

        # =================================================
        # Clean
        # =================================================

        indicator_columns = [

            "EMA9",
            "EMA21",
            "RSI",
            "MACD",
            "MACD_SIGNAL",
            "MACD_HIST",
            "ST_DIRECTION",
            "SUPERTREND",
            "AVG_VOLUME",
        ]

        for column in indicator_columns:

            df[column] = pd.to_numeric(

                df[column],

                errors="coerce"
            )

        df.dropna(

            subset=indicator_columns,

            inplace=True
        )

        if df.empty:

            return None

        return df

    except Exception as e:

        logger.exception(
            f"Indicator calculation error: {e}"
        )

        return None


# =========================================================
# Main Signal Engine
# =========================================================

def get_signals(symbol):

    try:

        symbol = str(
            symbol or ""
        ).strip().upper()

        # =================================================
        # Download Data
        # =================================================

        df = download_data(

            symbol,

            period="30d",

            interval="5m"
        )

        if df is None or df.empty:

            return {

                "error":
                    f"No market data available "
                    f"for {symbol}",

                "Symbol": symbol,
            }

        # =================================================
        # Indicators
        # =================================================

        df = calculate_indicators(
            df
        )

        if df is None or df.empty:

            return {

                "error":
                    "Indicators could not "
                    "be calculated",

                "Symbol": symbol,
            }

        if len(df) < 2:

            return {

                "error":
                    "Insufficient candles "
                    "for signal calculation",

                "Symbol": symbol,
            }

        # =================================================
        # Latest / Previous
        # =================================================

        latest = df.iloc[-1]

        previous = df.iloc[-2]

        # =================================================
        # OHLC
        # =================================================

        current_open = safe_float(
            latest["Open"]
        )

        current_high = safe_float(
            latest["High"]
        )

        current_low = safe_float(
            latest["Low"]
        )

        current_close = safe_float(
            latest["Close"]
        )

        current_volume = safe_float(
            latest["Volume"]
        )

        # =================================================
        # Indicators
        # =================================================

        ema9 = safe_float(
            latest["EMA9"]
        )

        ema21 = safe_float(
            latest["EMA21"]
        )

        rsi = safe_float(
            latest["RSI"]
        )

        macd_value = safe_float(
            latest["MACD"]
        )

        macd_signal_value = safe_float(
            latest["MACD_SIGNAL"]
        )

        macd_hist = safe_float(
            latest["MACD_HIST"]
        )

        st_direction = safe_float(
            latest["ST_DIRECTION"]
        )

        supertrend_value = safe_float(

            latest["SUPERTREND"],

            current_close
        )

        average_volume = safe_float(
            latest["AVG_VOLUME"]
        )

        # =================================================
        # Previous Indicators
        # =================================================

        previous_ema9 = safe_float(
            previous["EMA9"]
        )

        previous_ema21 = safe_float(
            previous["EMA21"]
        )

        previous_macd = safe_float(
            previous["MACD"]
        )

        previous_macd_signal = safe_float(
            previous["MACD_SIGNAL"]
        )

        previous_st_direction = safe_float(
            previous["ST_DIRECTION"]
        )

        # =================================================
        # EMA Signal
        # =================================================

        if ema9 > ema21:

            ema_signal = "BUY"

        elif ema9 < ema21:

            ema_signal = "SELL"

        else:

            ema_signal = "HOLD"

        # =================================================
        # EMA Crossover
        # =================================================

        bullish_crossover = (

            previous_ema9
            <= previous_ema21

            and

            ema9 > ema21
        )

        bearish_crossover = (

            previous_ema9
            >= previous_ema21

            and

            ema9 < ema21
        )

        # =================================================
        # RSI Signal
        # =================================================

        if (
            rsi > 55
            and rsi < 70
        ):

            rsi_signal = "BUY"

        elif (
            rsi < 45
            and rsi > 30
        ):

            rsi_signal = "SELL"

        else:

            rsi_signal = "HOLD"

        # =================================================
        # MACD Signal
        # =================================================

        if macd_value > macd_signal_value:

            macd_signal_name = "BUY"

        elif macd_value < macd_signal_value:

            macd_signal_name = "SELL"

        else:

            macd_signal_name = "HOLD"

        # =================================================
        # MACD Crossover
        # =================================================

        bullish_macd_crossover = (

            previous_macd
            <= previous_macd_signal

            and

            macd_value
            > macd_signal_value
        )

        bearish_macd_crossover = (

            previous_macd
            >= previous_macd_signal

            and

            macd_value
            < macd_signal_value
        )

        # =================================================
        # SuperTrend Signal
        # =================================================

        if st_direction > 0:

            st_signal = "BUY"

        elif st_direction < 0:

            st_signal = "SELL"

        else:

            st_signal = "HOLD"

        # =================================================
        # SuperTrend Flip
        # =================================================

        bullish_st_flip = (

            previous_st_direction <= 0

            and

            st_direction > 0
        )

        bearish_st_flip = (

            previous_st_direction >= 0

            and

            st_direction < 0
        )

        # =================================================
        # Volume Ratio
        # =================================================

        if average_volume > 0:

            volume_ratio = (

                current_volume
                / average_volume
            )

        else:

            volume_ratio = 0.0

        volume_confirmation = (

            volume_ratio >= 1.20
        )

        # =================================================
        # Price vs SuperTrend
        # =================================================

        price_above_supertrend = (

            current_close
            > supertrend_value
        )

        price_below_supertrend = (

            current_close
            < supertrend_value
        )

        # =================================================
        # Signal Counts
        # =================================================

        buy_count = 0

        sell_count = 0

        # -------------------------------------------------
        # EMA
        # -------------------------------------------------

        if ema_signal == "BUY":

            buy_count += 1

        elif ema_signal == "SELL":

            sell_count += 1

        # -------------------------------------------------
        # RSI
        # -------------------------------------------------

        if rsi_signal == "BUY":

            buy_count += 1

        elif rsi_signal == "SELL":

            sell_count += 1

        # -------------------------------------------------
        # MACD
        # -------------------------------------------------

        if macd_signal_name == "BUY":

            buy_count += 1

        elif macd_signal_name == "SELL":

            sell_count += 1

        # -------------------------------------------------
        # SuperTrend
        # -------------------------------------------------

        if st_signal == "BUY":

            buy_count += 1

        elif st_signal == "SELL":

            sell_count += 1

        # =================================================
        # Combined Signal
        # =================================================

        if (

            buy_count >= 3

            and

            price_above_supertrend

        ):

            combined_signal = "BUY"

        elif (

            sell_count >= 3

            and

            price_below_supertrend

        ):

            combined_signal = "SELL"

        else:

            combined_signal = "HOLD"

        # =================================================
        # Signal Strength
        # =================================================

        buy_strength = (

            buy_count / 4
        ) * 100

        sell_strength = (

            sell_count / 4
        ) * 100

        # -------------------------------------------------
        # Volume bonus
        # -------------------------------------------------

        if volume_confirmation:

            if combined_signal == "BUY":

                buy_strength += 10

            elif combined_signal == "SELL":

                sell_strength += 10

        # -------------------------------------------------
        # SuperTrend price bonus
        # -------------------------------------------------

        if price_above_supertrend:

            buy_strength += 10

        elif price_below_supertrend:

            sell_strength += 10

        buy_strength = min(

            round(buy_strength),

            100
        )

        sell_strength = min(

            round(sell_strength),

            100
        )

        if combined_signal == "BUY":

            signal_strength = buy_strength

        elif combined_signal == "SELL":

            signal_strength = sell_strength

        else:

            signal_strength = max(

                buy_strength,

                sell_strength
            )

        # =================================================
        # Signal Type
        # =================================================

        if bullish_crossover:

            signal_type = (
                "EMA_BULLISH_CROSS"
            )

        elif bearish_crossover:

            signal_type = (
                "EMA_BEARISH_CROSS"
            )

        elif bullish_macd_crossover:

            signal_type = (
                "MACD_BULLISH_CROSS"
            )

        elif bearish_macd_crossover:

            signal_type = (
                "MACD_BEARISH_CROSS"
            )

        elif bullish_st_flip:

            signal_type = (
                "SUPERTREND_BULLISH_FLIP"
            )

        elif bearish_st_flip:

            signal_type = (
                "SUPERTREND_BEARISH_FLIP"
            )

        else:

            signal_type = (
                "TREND_CONTINUATION"
            )

        # =================================================
        # Market Type
        # =================================================

        market_type = (

            "DELTA"

            if is_delta_symbol(symbol)

            else "INDIA"
        )

        # =================================================
        # Currency
        # =================================================

        if market_type == "DELTA":

            price_display = (
                f"${current_close:,.8f}"
            )

            ema9_display = (
                f"${ema9:,.8f}"
            )

            ema21_display = (
                f"${ema21:,.8f}"
            )

            supertrend_display = (
                f"${supertrend_value:,.8f}"
            )

        else:

            price_display = (
                f"₹{current_close:,.2f}"
            )

            ema9_display = (
                f"₹{ema9:,.2f}"
            )

            ema21_display = (
                f"₹{ema21:,.2f}"
            )

            supertrend_display = (
                f"₹{supertrend_value:,.2f}"
            )

        # =================================================
        # Final Result
        # =================================================

        return {

            # -------------------------------------------------
            # Basic
            # -------------------------------------------------

            "Symbol":
                symbol,

            "SIGNAL":
                combined_signal,

            "Signal":
                combined_signal,

            "Signal_Strength":
                signal_strength,

            "Signal_Type":
                signal_type,

            "Timestamp":
                str(df.index[-1]),

            "Market_Type":
                market_type,

            "Is_Delta":
                market_type == "DELTA",

            # -------------------------------------------------
            # OHLC
            # -------------------------------------------------

            "Open":
                current_open,

            "High":
                current_high,

            "Low":
                current_low,

            "Close":
                current_close,

            "Price":
                current_close,

            "Price_Display":
                price_display,

            # -------------------------------------------------
            # Volume
            # -------------------------------------------------

            "Volume":
                current_volume,

            "AVG_VOLUME":
                average_volume,

            "Volume_Ratio":
                round(
                    volume_ratio,
                    2
                ),

            "VOLUME_CONFIRMATION":
                volume_confirmation,

            # -------------------------------------------------
            # EMA
            # -------------------------------------------------

            "EMA9":
                ema9,

            "EMA9_Display":
                ema9_display,

            "EMA21":
                ema21,

            "EMA21_Display":
                ema21_display,

            "EMA_SIGNAL":
                ema_signal,

            "EMA_BULLISH_CROSS":
                bullish_crossover,

            "EMA_BEARISH_CROSS":
                bearish_crossover,

            # -------------------------------------------------
            # RSI
            # -------------------------------------------------

            "RSI":
                round(
                    rsi,
                    2
                ),

            "RSI_SIGNAL":
                rsi_signal,

            # -------------------------------------------------
            # MACD
            # -------------------------------------------------

            "MACD":
                macd_value,

            "MACD_SIGNAL":
                macd_signal_value,

            "MACD_HIST":
                macd_hist,

            "MACD_SIGNAL_NAME":
                macd_signal_name,

            "MACD_BULLISH_CROSS":
                bullish_macd_crossover,

            "MACD_BEARISH_CROSS":
                bearish_macd_crossover,

            # -------------------------------------------------
            # SuperTrend
            # -------------------------------------------------

            "SUPERTREND":
                supertrend_value,

            "SUPERTREND_VALUE":
                supertrend_value,

            "SUPERTREND_Display":
                supertrend_display,

            "ST_DIRECTION":
                st_direction,

            "SUPERTREND_SIGNAL":
                st_signal,

            "SUPERTREND_BULLISH_FLIP":
                bullish_st_flip,

            "SUPERTREND_BEARISH_FLIP":
                bearish_st_flip,

            # -------------------------------------------------
            # Price Confirmation
            # -------------------------------------------------

            "PRICE_ABOVE_SUPERTREND":
                price_above_supertrend,

            "PRICE_BELOW_SUPERTREND":
                price_below_supertrend,

            # -------------------------------------------------
            # Signal Counts
            # -------------------------------------------------

            "BUY_COUNT":
                buy_count,

            "SELL_COUNT":
                sell_count,
        }

    except Exception as e:

        logger.exception(

            f"Signal engine error "
            f"for {symbol}: {e}"
        )

        return {

            "error":
                str(e),

            "Symbol":
                symbol,
        }