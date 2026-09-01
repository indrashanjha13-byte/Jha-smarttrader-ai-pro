import logging
import math

import pandas as pd
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

        df = yf.download(
            symbol,
            period=period,
            interval=interval,
            auto_adjust=False,
            progress=False,
            threads=False
        )

        if df is None or df.empty:
            return None

        # Fix yfinance MultiIndex
        if isinstance(df.columns, pd.MultiIndex):

            df.columns = [
                column[0]
                if isinstance(column, tuple)
                else column
                for column in df.columns
            ]

        # Remove duplicate columns
        df = df.loc[:, ~df.columns.duplicated()]

        required = [
            "Open",
            "High",
            "Low",
            "Close",
            "Volume"
        ]

        for column in required:

            if column not in df.columns:
                logging.warning(
                    f"Missing column {column} for {symbol}"
                )
                return None

        df = df[required].copy()

        for column in required:
            df[column] = pd.to_numeric(
                df[column],
                errors="coerce"
            )

        df.dropna(
            subset=["Open", "High", "Low", "Close"],
            inplace=True
        )

        if df.empty:
            return None

        return df

    except Exception as e:

        logging.error(
            f"Data download error for {symbol}: {e}"
        )

        return None


# =========================================================
# Main Signal Engine
# =========================================================

def get_signals(symbol):

    try:

        df = download_data(
            symbol,
            period="30d",
            interval="5m"
        )

        if df is None or df.empty:

            return {
                "error": f"No market data available for {symbol}"
            }

        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        volume = df["Volume"]

        # =================================================
        # EMA
        # =================================================

        df["EMA9"] = ta.ema(
            close,
            length=9
        )

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

            macd_columns = list(macd.columns)

            # pandas_ta normally returns:
            # MACD_12_26_9
            # MACDh_12_26_9
            # MACDs_12_26_9

            macd_main = next(
                (
                    c for c in macd_columns
                    if str(c).startswith("MACD_")
                    and not str(c).startswith("MACDh")
                    and not str(c).startswith("MACDs")
                ),
                None
            )

            macd_signal_column = next(
                (
                    c for c in macd_columns
                    if str(c).startswith("MACDs")
                ),
                None
            )

            if macd_main is not None:
                df["MACD"] = macd[macd_main]
            else:
                df["MACD"] = 0.0

            if macd_signal_column is not None:
                df["MACD_SIGNAL"] = macd[
                    macd_signal_column
                ]
            else:
                df["MACD_SIGNAL"] = 0.0

        else:

            df["MACD"] = 0.0
            df["MACD_SIGNAL"] = 0.0

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

        if supertrend is not None and not supertrend.empty:

            st_columns = list(
                supertrend.columns
            )

            direction_column = next(
                (
                    c for c in st_columns
                    if str(c).startswith("SUPERTd")
                ),
                None
            )

            value_column = next(
                (
                    c for c in st_columns
                    if str(c).startswith("SUPERT_")
                    and not str(c).startswith("SUPERTd")
                    and not str(c).startswith("SUPERTl")
                    and not str(c).startswith("SUPERTs")
                ),
                None
            )

            if direction_column is not None:

                df["ST_DIRECTION"] = (
                    supertrend[direction_column]
                )

            else:

                df["ST_DIRECTION"] = 0

            if value_column is not None:

                df["SUPERTREND"] = (
                    supertrend[value_column]
                )

            else:

                df["SUPERTREND"] = close

        else:

            df["ST_DIRECTION"] = 0
            df["SUPERTREND"] = close

        # =================================================
        # Volume Average
        # =================================================

        df["AVG_VOLUME"] = (
            volume
            .rolling(
                window=20,
                min_periods=1
            )
            .mean()
        )

        # =================================================
        # Remove incomplete indicator rows
        # =================================================

        df = df.dropna(
            subset=[
                "EMA9",
                "EMA21",
                "RSI"
            ]
        )

        if df.empty:

            return {
                "error": "Indicators could not be calculated"
            }

        latest = df.iloc[-1]

        # =================================================
        # Latest Values
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

        st_direction = safe_float(
            latest.get("ST_DIRECTION"),
            0
        )

        supertrend_value = safe_float(
            latest.get("SUPERTREND")
        )

        current_volume = safe_float(
            latest.get("Volume")
        )

        average_volume = safe_float(
            latest.get("AVG_VOLUME")
        )

        current_close = safe_float(
            latest.get("Close")
        )

        current_open = safe_float(
            latest.get("Open")
        )

        current_high = safe_float(
            latest.get("High")
        )

        current_low = safe_float(
            latest.get("Low")
        )

        # =================================================
        # Individual Signals
        # =================================================

        if ema9 > ema21:

            ema_signal = "BUY"

        elif ema9 < ema21:

            ema_signal = "SELL"

        else:

            ema_signal = "HOLD"


        if rsi > 55:

            rsi_signal = "BUY"

        elif rsi < 45:

            rsi_signal = "SELL"

        else:

            rsi_signal = "HOLD"


        if st_direction > 0:

            st_signal = "BUY"

        elif st_direction < 0:

            st_signal = "SELL"

        else:

            st_signal = "HOLD"


        if macd_value > macd_signal_value:

            macd_signal_name = "BUY"

        elif macd_value < macd_signal_value:

            macd_signal_name = "SELL"

        else:

            macd_signal_name = "HOLD"


        # =================================================
        # Volume Confirmation
        # =================================================

        if average_volume > 0:

            volume_ratio = (
                current_volume /
                average_volume
            )

        else:

            volume_ratio = 0.0


        volume_confirmation = (
            volume_ratio >= 1.20
        )


        # =================================================
        # Combined Signal
        # =================================================

        buy_count = sum(
            [
                ema_signal == "BUY",
                rsi_signal == "BUY",
                st_signal == "BUY",
                macd_signal_name == "BUY"
            ]
        )

        sell_count = sum(
            [
                ema_signal == "SELL",
                rsi_signal == "SELL",
                st_signal == "SELL",
                macd_signal_name == "SELL"
            ]
        )


        if buy_count >= 3 and volume_confirmation:

            combined_signal = "BUY"

        elif sell_count >= 3 and volume_confirmation:

            combined_signal = "SELL"

        elif buy_count >= 3:

            combined_signal = "BUY"

        elif sell_count >= 3:

            combined_signal = "SELL"

        else:

            combined_signal = "HOLD"


        # =================================================
        # Return
        # =================================================

        return {

            "Symbol": symbol,

            "Close": current_close,
            "Open": current_open,
            "High": current_high,
            "Low": current_low,

            "Volume": current_volume,
            "AVG_VOLUME": average_volume,
            "Volume_Ratio": round(
                volume_ratio,
                2
            ),

            "EMA9": ema9,
            "EMA21": ema21,

            "RSI": rsi,

            "MACD": macd_value,
            "MACD_SIGNAL": macd_signal_value,

            "SUPERTREND": st_direction,
            "SUPERTREND_VALUE": supertrend_value,
            "ST_DIRECTION": st_direction,

            "EMA_SIGNAL": ema_signal,
            "RSI_SIGNAL": rsi_signal,
            "SUPERTREND_SIGNAL": st_signal,
            "MACD_SIGNAL_NAME": macd_signal_name,

            "VOLUME_CONFIRMATION":
                volume_confirmation,

            "SIGNAL":
                combined_signal
        }


    except Exception as e:

        logging.exception(
            f"Signal engine error for {symbol}"
        )

        return {
            "error": str(e)
        }

