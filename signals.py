import logging
import math
import time

import pandas as pd
import requests
import yfinance as yf
import pandas_ta as ta


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
# Download Market Data
# =========================================================

def download_data(symbol, period="30d", interval="5m"):

    try:

        symbol = str(symbol).upper().strip()

        # =================================================
        # DELTA FUTURES
        # =================================================

        # Delta Futures symbols such as:
        # 1000BONKUSD
        # BTCUSD
        # ETHUSD
        #
        # Do NOT send these symbols to Yahoo Finance.

        is_delta_symbol = (
            symbol == "1000BONKUSD"
            or symbol.endswith("USD")
        )

        if is_delta_symbol:

            logging.info(
                f"Using Delta Exchange data for {symbol}"
            )

            # -------------------------------------------------
            # Delta API
            # -------------------------------------------------

            base_url = (
                "https://api.india.delta.exchange"
            )

            endpoint = (
                f"{base_url}/v2/history/candles"
            )

            # -------------------------------------------------
            # Resolution
            # -------------------------------------------------

            resolution = interval

            if resolution not in [
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
                "1w"
            ]:

                resolution = "5m"

            # -------------------------------------------------
            # Number of candles
            #
            # We need enough candles for:
            # EMA21
            # RSI14
            # MACD
            # SuperTrend
            # Volume20
            #
            # 1000 candles is more than enough.
            # -------------------------------------------------

            end_time = int(
                time.time()
            )

            candle_count = 1000

            interval_seconds = {
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
                "1w": 604800
            }

            seconds = interval_seconds.get(
                resolution,
                300
            )

            start_time = (
                end_time
                - (
                    candle_count
                    * seconds
                )
            )

            # -------------------------------------------------
            # Request
            # -------------------------------------------------

            response = requests.get(
                endpoint,
                params={
                    "resolution": resolution,
                    "symbol": symbol,
                    "start": start_time,
                    "end": end_time
                },
                headers={
                    "Accept": "application/json",
                    "User-Agent":
                        "JhaSmartTraderAIPro/1.0"
                },
                timeout=15
            )

            response.raise_for_status()

            data = response.json()

            # -------------------------------------------------
            # Validate Response
            # -------------------------------------------------

            if not data.get("success"):

                logging.warning(
                    f"Delta API failed for {symbol}: "
                    f"{data}"
                )

                return None

            candles = data.get(
                "result",
                []
            )

            if not candles:

                logging.warning(
                    f"No Delta candles returned "
                    f"for {symbol}"
                )

                return None

            # -------------------------------------------------
            # Convert Delta candles to DataFrame
            # -------------------------------------------------

            rows = []

            for candle in candles:

                try:

                    rows.append({
                        "Time": pd.to_datetime(
                            candle.get("time"),
                            unit="s"
                        ),

                        "Open": float(
                            candle.get("open", 0)
                        ),

                        "High": float(
                            candle.get("high", 0)
                        ),

                        "Low": float(
                            candle.get("low", 0)
                        ),

                        "Close": float(
                            candle.get("close", 0)
                        ),

                        "Volume": float(
                            candle.get("volume", 0)
                        )
                    })

                except Exception:

                    continue

            if not rows:

                logging.warning(
                    f"Unable to parse Delta candles "
                    f"for {symbol}"
                )

                return None

            df = pd.DataFrame(rows)

            # -------------------------------------------------
            # Datetime Index
            # -------------------------------------------------

            df["Time"] = pd.to_datetime(
                df["Time"]
            )

            df.set_index(
                "Time",
                inplace=True
            )

            # -------------------------------------------------
            # Sort Oldest -> Newest
            # -------------------------------------------------

            df.sort_index(
                inplace=True
            )

            # -------------------------------------------------
            # Remove Duplicate Candles
            # -------------------------------------------------

            df = df[
                ~df.index.duplicated(
                    keep="last"
                )
            ]

            # -------------------------------------------------
            # Required Columns
            # -------------------------------------------------

            required_columns = [
                "Open",
                "High",
                "Low",
                "Close",
                "Volume"
            ]

            for column in required_columns:

                if column not in df.columns:

                    logging.warning(
                        f"Missing column {column} "
                        f"for {symbol}"
                    )

                    return None

            # -------------------------------------------------
            # Numeric Conversion
            # -------------------------------------------------

            for column in required_columns:

                df[column] = pd.to_numeric(
                    df[column],
                    errors="coerce"
                )

            # -------------------------------------------------
            # Remove Invalid Rows
            # -------------------------------------------------

            df.dropna(
                subset=[
                    "Open",
                    "High",
                    "Low",
                    "Close"
                ],
                inplace=True
            )

            if df.empty:

                return None

            logging.info(
                f"Delta data loaded: "
                f"{symbol} | "
                f"{len(df)} candles"
            )

            return df

        # =================================================
        # YAHOO FINANCE
        # =================================================

        df = yf.download(
            symbol,
            period=period,
            interval=interval,
            auto_adjust=False,
            progress=False,
            threads=False
        )

        if df is None or df.empty:

            logging.warning(
                f"No market data returned for {symbol}"
            )

            return None

        # =================================================
        # Fix yfinance MultiIndex
        # =================================================

        if isinstance(
            df.columns,
            pd.MultiIndex
        ):

            df.columns = [
                column[0]
                if isinstance(column, tuple)
                else column
                for column in df.columns
            ]

        # =================================================
        # Remove Duplicate Columns
        # =================================================

        df = df.loc[
            :,
            ~df.columns.duplicated()
        ]

        # =================================================
        # Required Columns
        # =================================================

        required_columns = [
            "Open",
            "High",
            "Low",
            "Close",
            "Volume"
        ]

        for column in required_columns:

            if column not in df.columns:

                logging.warning(
                    f"Missing column {column} "
                    f"for {symbol}"
                )

                return None

        # =================================================
        # Keep Required Columns
        # =================================================

        df = df[
            required_columns
        ].copy()

        # =================================================
        # Numeric Conversion
        # =================================================

        for column in required_columns:

            df[column] = pd.to_numeric(
                df[column],
                errors="coerce"
            )

        # =================================================
        # Remove Invalid OHLC Rows
        # =================================================

        df.dropna(
            subset=[
                "Open",
                "High",
                "Low",
                "Close"
            ],
            inplace=True
        )

        if df.empty:

            return None

        return df

    except Exception as e:

        logging.exception(
            f"Data download error for {symbol}: {e}"
        )

        return None
# =========================================================
# Main Signal Engine
# =========================================================

def get_signals(symbol):

    try:

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
                    f"No market data available for {symbol}"
            }

        # =================================================
        # OHLCV
        # =================================================

        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        volume = df["Volume"]

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
        # RSI
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

        if macd is not None and not macd.empty:

            macd_columns = list(
                macd.columns
            )

            # -------------------------------------------------
            # MACD Main
            # -------------------------------------------------

            macd_main = next(
                (
                    column
                    for column in macd_columns
                    if str(column).startswith("MACD_")
                    and not str(column).startswith("MACDh")
                    and not str(column).startswith("MACDs")
                ),
                None
            )

            # -------------------------------------------------
            # MACD Signal
            # -------------------------------------------------

            macd_signal_column = next(
                (
                    column
                    for column in macd_columns
                    if str(column).startswith("MACDs")
                ),
                None
            )

            # -------------------------------------------------
            # MACD Histogram
            # -------------------------------------------------

            macd_hist_column = next(
                (
                    column
                    for column in macd_columns
                    if str(column).startswith("MACDh")
                ),
                None
            )

            # -------------------------------------------------
            # Assign MACD
            # -------------------------------------------------

            if macd_main is not None:

                df["MACD"] = macd[
                    macd_main
                ]

            else:

                df["MACD"] = 0.0

            # -------------------------------------------------
            # Assign MACD Signal
            # -------------------------------------------------

            if macd_signal_column is not None:

                df["MACD_SIGNAL"] = macd[
                    macd_signal_column
                ]

            else:

                df["MACD_SIGNAL"] = 0.0

            # -------------------------------------------------
            # Assign MACD Histogram
            # -------------------------------------------------

            if macd_hist_column is not None:

                df["MACD_HIST"] = macd[
                    macd_hist_column
                ]

            else:

                df["MACD_HIST"] = (
                    df["MACD"]
                    - df["MACD_SIGNAL"]
                )

        else:

            df["MACD"] = 0.0

            df["MACD_SIGNAL"] = 0.0

            df["MACD_HIST"] = 0.0

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

        if (
            supertrend is not None
            and not supertrend.empty
        ):

            st_columns = list(
                supertrend.columns
            )

            # -------------------------------------------------
            # Direction Column
            # -------------------------------------------------

            direction_column = next(
                (
                    column
                    for column in st_columns
                    if str(column).startswith("SUPERTd")
                ),
                None
            )

            # -------------------------------------------------
            # SuperTrend Value Column
            # -------------------------------------------------

            value_column = next(
                (
                    column
                    for column in st_columns
                    if str(column).startswith("SUPERT_")
                    and not str(column).startswith("SUPERTd")
                    and not str(column).startswith("SUPERTl")
                    and not str(column).startswith("SUPERTs")
                ),
                None
            )

            # -------------------------------------------------
            # Direction
            # -------------------------------------------------

            if direction_column is not None:

                df["ST_DIRECTION"] = (
                    supertrend[
                        direction_column
                    ]
                )

            else:

                df["ST_DIRECTION"] = 0.0

            # -------------------------------------------------
            # SuperTrend Value
            # -------------------------------------------------

            if value_column is not None:

                df["SUPERTREND"] = (
                    supertrend[
                        value_column
                    ]
                )

            else:

                df["SUPERTREND"] = close

        else:

            df["ST_DIRECTION"] = 0.0

            df["SUPERTREND"] = close

        # =================================================
        # Volume Average
        # =================================================

        df["AVG_VOLUME"] = (
            volume
            .rolling(
                window=20,
                min_periods=20
            )
            .mean()
        )

        # =================================================
        # Remove Incomplete Indicator Rows
        # =================================================

        indicator_columns = [
            "EMA9",
            "EMA21",
            "RSI",
            "MACD",
            "MACD_SIGNAL",
            "ST_DIRECTION",
            "SUPERTREND",
            "AVG_VOLUME"
        ]

        df = df.dropna(
            subset=indicator_columns
        )

        if df.empty:

            return {
                "error":
                    "Indicators could not be calculated"
            }

        if len(df) < 2:

            return {
                "error":
                    "Insufficient candles for signal calculation"
            }

        # =================================================
        # Latest Candle
        # =================================================

        latest = df.iloc[-1]

        previous = df.iloc[-2]

        # =================================================
        # Current OHLC
        # =================================================

        current_open = safe_float(
            latest.get("Open")
        )

        current_high = safe_float(
            latest.get("High")
        )

        current_low = safe_float(
            latest.get("Low")
        )

        current_close = safe_float(
            latest.get("Close")
        )

        current_volume = safe_float(
            latest.get("Volume")
        )

        # =================================================
        # Indicator Values
        # =================================================

        ema9 = safe_float(
            latest.get("EMA9")
        )

        ema21 = safe_float(
            latest.get("EMA21")
        )

        rsi = safe_float(
            latest.get("RSI")
        )

        macd_value = safe_float(
            latest.get("MACD")
        )

        macd_signal_value = safe_float(
            latest.get("MACD_SIGNAL")
        )

        macd_hist = safe_float(
            latest.get("MACD_HIST")
        )

        st_direction = safe_float(
            latest.get("ST_DIRECTION"),
            0.0
        )

        supertrend_value = safe_float(
            latest.get("SUPERTREND"),
            current_close
        )

        average_volume = safe_float(
            latest.get("AVG_VOLUME")
        )

        # =================================================
        # Previous Candle Values
        # =================================================

        previous_ema9 = safe_float(
            previous.get("EMA9")
        )

        previous_ema21 = safe_float(
            previous.get("EMA21")
        )

        previous_macd = safe_float(
            previous.get("MACD")
        )

        previous_macd_signal = safe_float(
            previous.get("MACD_SIGNAL")
        )

        previous_st_direction = safe_float(
            previous.get("ST_DIRECTION"),
            0.0
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
            previous_ema9 <= previous_ema21
            and ema9 > ema21
        )

        bearish_crossover = (
            previous_ema9 >= previous_ema21
            and ema9 < ema21
        )

        # =================================================
        # RSI Signal
        # =================================================

        if rsi > 55 and rsi < 70:

            rsi_signal = "BUY"

        elif rsi < 45 and rsi > 30:

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
            previous_macd <= previous_macd_signal
            and macd_value > macd_signal_value
        )

        bearish_macd_crossover = (
            previous_macd >= previous_macd_signal
            and macd_value < macd_signal_value
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
            and st_direction > 0
        )

        bearish_st_flip = (
            previous_st_direction >= 0
            and st_direction < 0
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

        # =================================================
        # Volume Confirmation
        # =================================================

        volume_confirmation = (
            volume_ratio >= 1.20
        )

        # =================================================
        # Price vs SuperTrend
        # =================================================

        price_above_supertrend = (
            current_close > supertrend_value
        )

        price_below_supertrend = (
            current_close < supertrend_value
        )

        # =================================================
        # Individual Signal Score
        # =================================================

        buy_count = 0

        sell_count = 0

        # EMA
        if ema_signal == "BUY":
            buy_count += 1

        elif ema_signal == "SELL":
            sell_count += 1

        # RSI
        if rsi_signal == "BUY":
            buy_count += 1

        elif rsi_signal == "SELL":
            sell_count += 1

        # MACD
        if macd_signal_name == "BUY":
            buy_count += 1

        elif macd_signal_name == "SELL":
            sell_count += 1

        # SuperTrend
        if st_signal == "BUY":
            buy_count += 1

        elif st_signal == "SELL":
            sell_count += 1

        # =================================================
        # Combined Signal
        # =================================================

        if (
            buy_count >= 3
            and volume_confirmation
            and price_above_supertrend
        ):

            combined_signal = "BUY"

        elif (
            sell_count >= 3
            and volume_confirmation
            and price_below_supertrend
        ):

            combined_signal = "SELL"

        elif (
            buy_count >= 3
            and price_above_supertrend
        ):

            combined_signal = "BUY"

        elif (
            sell_count >= 3
            and price_below_supertrend
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

        if volume_confirmation:

            if combined_signal == "BUY":

                buy_strength += 10

            elif combined_signal == "SELL":

                sell_strength += 10

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

            signal_type = "EMA_BULLISH_CROSS"

        elif bearish_crossover:

            signal_type = "EMA_BEARISH_CROSS"

        elif bullish_macd_crossover:

            signal_type = "MACD_BULLISH_CROSS"

        elif bearish_macd_crossover:

            signal_type = "MACD_BEARISH_CROSS"

        elif bullish_st_flip:

            signal_type = "SUPERTREND_BULLISH_FLIP"

        elif bearish_st_flip:

            signal_type = "SUPERTREND_BEARISH_FLIP"

        else:

            signal_type = "TREND_CONTINUATION"

        # =================================================
        # Final Result
        # =================================================

        return {

            # -------------------------------------------------
            # Basic
            # -------------------------------------------------

            "Symbol": symbol,

            "SIGNAL": combined_signal,

            "Signal": combined_signal,

            "Signal_Strength": signal_strength,

            "Signal_Type": signal_type,

            "Timestamp": str(
                df.index[-1]
            ),

            # -------------------------------------------------
            # OHLC
            # -------------------------------------------------

            "Open": current_open,

            "High": current_high,

            "Low": current_low,

            "Close": current_close,

            "Price": current_close,

            # -------------------------------------------------
            # Volume
            # -------------------------------------------------

            "Volume": current_volume,

            "AVG_VOLUME": average_volume,

            "Volume_Ratio": round(
                volume_ratio,
                2
            ),

            "VOLUME_CONFIRMATION":
                volume_confirmation,

            # -------------------------------------------------
            # EMA
            # -------------------------------------------------

            "EMA9": ema9,

            "EMA21": ema21,

            "EMA_SIGNAL":
                ema_signal,

            "EMA_BULLISH_CROSS":
                bullish_crossover,

            "EMA_BEARISH_CROSS":
                bearish_crossover,

            # -------------------------------------------------
            # RSI
            # -------------------------------------------------

            "RSI": rsi,

            "RSI_SIGNAL":
                rsi_signal,

            # -------------------------------------------------
            # MACD
            # -------------------------------------------------

            "MACD": macd_value,

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
                sell_count
        }

    except Exception as e:

        logging.exception(
            f"Signal engine error for {symbol}"
        )

        return {
            "error": str(e),
            "Symbol": symbol
        }