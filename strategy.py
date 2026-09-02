import logging
import math

import pandas as pd


# =========================================================
# Helper
# =========================================================

def _safe_float(value, default=0.0):
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
# SuperTrend + MACD + Volume
# =========================================================

def generate_signal(
    supertrend,
    macd,
    macd_signal,
    volume,
    avg_volume
):
    """
    Primary confirmation strategy.

    BUY:
        SuperTrend bullish
        MACD > Signal
        Volume > Average Volume

    SELL:
        SuperTrend bearish
        MACD < Signal
        Volume > Average Volume

    Otherwise:
        NO TRADE
    """

    try:

        st = _safe_float(supertrend)
        macd_value = _safe_float(macd)
        macd_sig = _safe_float(macd_signal)
        vol = _safe_float(volume)
        avg_vol = _safe_float(avg_volume)

        if (
            st > 0
            and macd_value > macd_sig
            and vol > avg_vol
        ):
            return "BUY"

        if (
            st < 0
            and macd_value < macd_sig
            and vol > avg_vol
        ):
            return "SELL"

    except Exception as e:

        logging.error(
            f"generate_signal error: {e}"
        )

    return "NO TRADE"


# =========================================================
# EMA Signal
# =========================================================

def ema_signal(ema9, ema21):

    try:

        e9 = _safe_float(ema9)
        e21 = _safe_float(ema21)

        if e9 > e21:
            return "BUY"

        if e9 < e21:
            return "SELL"

    except Exception as e:

        logging.error(
            f"ema_signal error: {e}"
        )

    return "NO TRADE"


# =========================================================
# RSI Signal
# =========================================================

def rsi_signal(rsi):

    try:

        r = _safe_float(rsi)

        if r <= 30:
            return "BUY"

        if r >= 70:
            return "SELL"

    except Exception as e:

        logging.error(
            f"rsi_signal error: {e}"
        )

    return "NO TRADE"


# =========================================================
# SuperTrend Signal
# =========================================================

def supertrend_signal(supertrend):

    try:

        st = _safe_float(supertrend)

        if st > 0:
            return "BUY"

        if st < 0:
            return "SELL"

    except Exception as e:

        logging.error(
            f"supertrend_signal error: {e}"
        )

    return "NO TRADE"


# =========================================================
# MACD Signal
# =========================================================

def macd_signal(macd, macd_signal_value):

    try:

        macd_value = _safe_float(macd)
        signal_value = _safe_float(
            macd_signal_value
        )

        if macd_value > signal_value:
            return "BUY"

        if macd_value < signal_value:
            return "SELL"

    except Exception as e:

        logging.error(
            f"macd_signal error: {e}"
        )

    return "NO TRADE"


# =========================================================
# Combined Strategy
# =========================================================

def combined_signal(
    ema9,
    ema21,
    rsi,
    macd,
    macd_signal_value,
    supertrend,
    volume,
    avg_volume
):
    """
    Combines EMA, RSI, MACD, SuperTrend
    and Volume confirmation.
    """

    try:

        ema = ema_signal(
            ema9,
            ema21
        )

        rsi_sig = rsi_signal(
            rsi
        )

        macd_sig = macd_signal(
            macd,
            macd_signal_value
        )

        st_sig = supertrend_signal(
            supertrend
        )

        volume_value = _safe_float(
            volume
        )

        avg_volume_value = _safe_float(
            avg_volume
        )

        volume_ok = (
            avg_volume_value > 0
            and volume_value > avg_volume_value
        )

        buy_votes = sum(
            [
                ema == "BUY",
                rsi_sig == "BUY",
                macd_sig == "BUY",
                st_sig == "BUY"
            ]
        )

        sell_votes = sum(
            [
                ema == "SELL",
                rsi_sig == "SELL",
                macd_sig == "SELL",
                st_sig == "SELL"
            ]
        )

        if buy_votes >= 3 and volume_ok:
            return "BUY"

        if sell_votes >= 3 and volume_ok:
            return "SELL"

        return "HOLD"

    except Exception as e:

        logging.error(
            f"combined_signal error: {e}"
        )

        return "HOLD"

# =========================================================
# Option Selection
# =========================================================

def option_selection(
    signal,
    strike_mode,
    option_side="CE"
):
    """
    Converts signal + strike preference
    into an option action.

    Option Side:
    CE  -> Call Option
    PE  -> Put Option
    ALL -> Both CE and PE
    """

    signal = str(
        signal or ""
    ).upper()

    mode = str(
        strike_mode or "ATM"
    ).upper()

    side = str(
        option_side or "CE"
    ).upper()

    # =========================
    # BUY Signal
    # =========================

    if signal == "BUY":

        if side == "PE":
            return f"Buy PE {mode}"

        if side == "ALL":
            return f"Buy CE {mode} + Buy PE {mode}"

        return f"Buy CE {mode}"

    # =========================
    # SELL Signal
    # =========================

    if signal == "SELL":

        if side == "PE":
            return f"Sell PE {mode}"

        if side == "ALL":
            return f"Sell CE {mode} + Sell PE {mode}"

        return f"Sell CE {mode}"

    return "No Trade"

# =========================================================
# Scalper Signal
# =========================================================

def scalper_signal(df):

    """
    Short-term price-action scalper.

    BUY:
        EMA9 > EMA21
        RSI > 50
        Current candle bullish
        Previous candle bearish

    SELL:
        EMA9 < EMA21
        RSI < 50
        Current candle bearish
        Previous candle bullish

    Target:
        1.5 × Risk
    """

    try:

        if df is None:
            return {
                "signal": "WAIT",
                "entry": None,
                "stop_loss": None,
                "target": None
            }

        if len(df) < 25:
            return {
                "signal": "WAIT",
                "entry": None,
                "stop_loss": None,
                "target": None
            }

        data = df.copy()

        # Handle MultiIndex
        if isinstance(
            data.columns,
            pd.MultiIndex
        ):

            data.columns = [
                c[0]
                if isinstance(c, tuple)
                else c
                for c in data.columns
            ]

        data.columns = [
            str(c).lower()
            for c in data.columns
        ]

        required = [
            "open",
            "high",
            "low",
            "close"
        ]

        for column in required:

            if column not in data.columns:

                return {
                    "signal": "WAIT",
                    "entry": None,
                    "stop_loss": None,
                    "target": None
                }

        # =================================================
        # EMA
        # =================================================

        data["ema9"] = (
            data["close"]
            .ewm(
                span=9,
                adjust=False
            )
            .mean()
        )

        data["ema21"] = (
            data["close"]
            .ewm(
                span=21,
                adjust=False
            )
            .mean()
        )

        # =================================================
        # RSI
        # =================================================

        delta = data["close"].diff()

        gain = delta.clip(
            lower=0
        )

        loss = -delta.clip(
            upper=0
        )

        avg_gain = gain.rolling(
            14
        ).mean()

        avg_loss = loss.rolling(
            14
        ).mean()

        avg_loss = avg_loss.replace(
            0,
            0.000001
        )

        rs = avg_gain / avg_loss

        data["rsi"] = (
            100
            - (
                100 / (1 + rs)
            )
        )

        data = data.dropna(
            subset=[
                "ema9",
                "ema21",
                "rsi"
            ]
        )

        if len(data) < 2:

            return {
                "signal": "WAIT",
                "entry": None,
                "stop_loss": None,
                "target": None
            }

        last = data.iloc[-1]
        previous = data.iloc[-2]

        entry = _safe_float(
            last["close"]
        )

        # =================================================
        # BUY
        # =================================================

        bullish_setup = (
            last["ema9"] > last["ema21"]
            and last["rsi"] > 50
            and last["close"] > last["open"]
            and previous["close"] < previous["open"]
        )

        if bullish_setup:

            stop_loss = _safe_float(
                last["low"],
                entry
            )

            risk = entry - stop_loss

            if risk <= 0:
                risk = entry * 0.0025
                stop_loss = entry - risk

            target = (
                entry
                + (risk * 1.5)
            )

            return {
                "signal": "BUY",
                "entry": round(entry, 2),
                "stop_loss": round(
                    stop_loss,
                    2
                ),
                "target": round(
                    target,
                    2
                )
            }

        # =================================================
        # SELL
        # =================================================

        bearish_setup = (
            last["ema9"] < last["ema21"]
            and last["rsi"] < 50
            and last["close"] < last["open"]
            and previous["close"] > previous["open"]
        )

        if bearish_setup:

            stop_loss = _safe_float(
                last["high"],
                entry
            )

            risk = stop_loss - entry

            if risk <= 0:
                risk = entry * 0.0025
                stop_loss = entry + risk

            target = (
                entry
                - (risk * 1.5)
            )

            return {
                "signal": "SELL",
                "entry": round(entry, 2),
                "stop_loss": round(
                    stop_loss,
                    2
                ),
                "target": round(
                    target,
                    2
                )
            }

        return {
            "signal": "WAIT",
            "entry": None,
            "stop_loss": None,
            "target": None
        }

    except Exception as e:

        logging.exception(
            f"scalper_signal error: {e}"
        )

        return {
            "signal": "WAIT",
            "entry": None,
            "stop_loss": None,
            "target": None
        }

