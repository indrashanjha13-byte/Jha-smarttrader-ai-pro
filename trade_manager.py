import logging
from datetime import datetime, time
from zoneinfo import ZoneInfo

from ai_learning import auto_strategy
from risk_manager import calculate_trade_details
from config import LOT_SIZE, MODE


IST = ZoneInfo("Asia/Kolkata")


class TradeManager:
    """
    Central Paper Trading Manager.

    Indian Options:
        CE BUY only
        PE BUY only
        SELL = EXIT existing BUY
        ALL = CE + PE BUY, never short

    Delta Futures:
        BUY  = LONG
        SELL = SHORT
        SELL on LONG = CLOSE LONG + optional reverse
        BUY on SHORT = CLOSE SHORT + optional reverse

    Live broker orders are NOT executed here.
    """

    # =====================================================
    # INIT
    # =====================================================

    def __init__(self, paper_trader=None):

        self.paper_trader = paper_trader

        self.last_signal = {}
        self.last_signals = {}

        self.active_position = None

        # IMPORTANT:
        # Trailing default OFF
        self.trailing_enabled = False
        self.trailing_percent = 0.5

    # =====================================================
    # PAPER TRADER
    # =====================================================

    def set_paper_trader(self, paper_trader):

        self.paper_trader = paper_trader

    # =====================================================
    # TRAILING SETTINGS
    # =====================================================

    def set_trailing_settings(
        self,
        enabled=False,
        percent=0.5
    ):

        self.trailing_enabled = bool(enabled)

        try:
            self.trailing_percent = float(percent)
        except Exception:
            self.trailing_percent = 0.5

    # =====================================================
    # DELTA SYMBOL
    # =====================================================

    @staticmethod
    def is_delta_symbol(symbol):

        s = str(symbol or "").strip().upper()

        delta_symbols = {
            "BTCUSD",
            "ETHUSD",
            "SOLUSD",
            "XRPUSD",
            "DOGEUSD",
            "ADAUSD",
            "BNBUSD",
            "AVAXUSD",
            "DOTUSD",
            "LINKUSD",
            "MATICUSD",
            "1000BONKUSD",
            "1000PEPEUSD",
            "BTCUSDT",
            "ETHUSDT",
        }

        return s in delta_symbols

    # =====================================================
    # POSITION KEY
    # =====================================================

    @staticmethod
    def _position_key(
        symbol,
        option_mode="N/A",
        strike=None,
        expiry=None
    ):

        symbol = str(
            symbol or ""
        ).upper().strip()

        option_mode = str(
            option_mode or "N/A"
        ).upper().strip()

        if option_mode == "N/A":
            return f"{symbol}_N/A"

        strike_text = ""

        if strike is not None:

            try:
                strike_text = str(
                    int(float(strike))
                )
            except Exception:
                strike_text = str(strike)

        expiry_text = str(
            expiry or ""
        ).upper().strip()

        return (
            f"{symbol}_{option_mode}_"
            f"{strike_text}_{expiry_text}"
        )

    # =====================================================
    # MARKET TIME
    # =====================================================

    def is_market_open(self, symbol):

        if self.is_delta_symbol(symbol):
            return True

        now = datetime.now(IST)

        # Saturday / Sunday
        if now.weekday() >= 5:
            return False

        market_open = time(9, 15)
        market_close = time(15, 30)

        return (
            market_open
            <= now.time()
            <= market_close
        )

    # =====================================================
    # NORMALIZE SIGNAL
    # =====================================================

    @staticmethod
    def _normalize_signal(signal):

        value = str(
            signal or ""
        ).strip().upper()

        if value in (
            "BUY",
            "LONG"
        ):
            return "BUY"

        if value in (
            "SELL",
            "SHORT"
        ):
            return "SELL"

        if value in (
            "HOLD",
            "WAIT",
            "NEUTRAL",
            ""
        ):
            return "HOLD"

        return value

    # =====================================================
    # NORMALIZE RESULT
    # =====================================================

    @staticmethod
    def _normalize_trade_result(result):

        if isinstance(result, tuple):

            if len(result) >= 2:
                return bool(result[0]), result[1]

            if len(result) == 1:
                return bool(result[0]), result[0]

            return False, "Empty result"

        if isinstance(result, bool):
            return result, result

        if result is None:
            return False, "No result returned"

        if isinstance(result, dict):

            status = str(
                result.get("status", "")
            ).lower()

            success_value = result.get(
                "success"
            )

            ok_value = result.get(
                "ok"
            )

            if status in (
                "error",
                "failed",
                "failure",
                "rejected"
            ):
                return False, result

            if success_value is False:
                return False, result

            if ok_value is False:
                return False, result

            return True, result

        return True, result

    # =====================================================
    # PROCESS
    # =====================================================

    def process(
        self,
        symbol,
        signal,
        current_price,
        capital=100000,
        option_mode="N/A",
        lots=1,
        lot_size=None,
        strike=None,
        expiry=None,
        option_type=None,
        price_by_option=None,
        contract_by_option=None
    ):

        symbol = str(
            symbol or ""
        ).strip().upper()

        signal = self._normalize_signal(signal)

        option_mode = str(
            option_mode or "N/A"
        ).upper().strip()

        if option_type:
            option_type = str(
                option_type
            ).upper().strip()

        if lot_size is None:
            lot_size = LOT_SIZE

        try:
            current_price = float(current_price)
        except Exception:
            return False, "❌ Invalid current price"

        if not symbol:
            return False, "❌ Invalid symbol"

        if signal not in (
            "BUY",
            "SELL",
            "HOLD"
        ):
            return False, f"❌ Invalid signal: {signal}"

        if signal == "HOLD":
            return True, {
                "status": "HOLD",
                "symbol": symbol
            }

        if current_price <= 0:
            return False, "❌ Current price must be > 0"

        if self.paper_trader is None:
            return False, "❌ PaperTrader not connected"

        if str(MODE).upper() != "PAPER":
            return False, (
                "❌ TradeManager is currently restricted "
                "to PAPER mode"
            )

        # -------------------------------------------------
        # AI strategy update
        # -------------------------------------------------

        try:
            auto_strategy(
                symbol,
                signal
            )
        except Exception:
            pass

        # -------------------------------------------------
        # DELTA
        # -------------------------------------------------

        if self.is_delta_symbol(symbol):

            return self._process_delta(
                symbol=symbol,
                signal=signal,
                current_price=current_price,
                capital=capital,
                lots=lots,
                lot_size=lot_size
            )

        # -------------------------------------------------
        # INDIAN OPTIONS
        # -------------------------------------------------

        return self._process_indian_options(
            symbol=symbol,
            signal=signal,
            current_price=current_price,
            capital=capital,
            option_mode=option_mode,
            lots=lots,
            lot_size=lot_size,
            strike=strike,
            expiry=expiry,
            option_type=option_type,
            price_by_option=price_by_option,
            contract_by_option=contract_by_option
        )

    # =====================================================
    # DELTA PROCESS
    # =====================================================

    def _process_delta(
        self,
        symbol,
        signal,
        current_price,
        capital,
        lots,
        lot_size
    ):

        position = self.paper_trader.get_position(
            symbol,
            "N/A"
        )

        quantity = max(
            1,
            int(lots) * int(lot_size)
        )

        # -------------------------------------------------
        # BUY
        # -------------------------------------------------

        if signal == "BUY":

            if position is not None:

                side = position.get(
                    "position_side"
                )

                if side == "LONG":

                    return True, {
                        "status": "NO_ACTION",
                        "message": (
                            f"🟢 {symbol} already LONG"
                        )
                    }

                if side == "SHORT":

                    success, result = (
                        self.paper_trader.cover_short(
                            current_price,
                            exit_reason="REVERSE_TO_LONG",
                            symbol=symbol,
                            option_mode="N/A"
                        )
                    )

                    if not success:
                        return False, result

            stoploss = round(
                current_price * 0.99,
                8
            )

            target = round(
                current_price * 1.02,
                8
            )

            result = self.paper_trader.buy(
                symbol=symbol,
                price=current_price,
                qty=quantity,
                target=target,
                stoploss=stoploss,
                trailing_enabled=self.trailing_enabled,
                trailing_start=(
                    current_price
                    * self.trailing_percent
                    / 100
                ),
                trailing_distance=(
                    current_price
                    * self.trailing_percent
                    / 200
                ),
                option_mode="N/A"
            )

            success, data = (
                self._normalize_trade_result(result)
            )

            if success:
                self.last_signal[symbol] = "BUY"
                self.last_signals[symbol] = "BUY"

            return success, data

        # -------------------------------------------------
        # SELL
        # -------------------------------------------------

        if signal == "SELL":

            if position is None:

                stoploss = round(
                    current_price * 1.01,
                    8
                )

                target = round(
                    current_price * 0.98,
                    8
                )

                result = self.paper_trader.short(
                    symbol=symbol,
                    price=current_price,
                    qty=quantity,
                    target=target,
                    stoploss=stoploss,
                    trailing_enabled=self.trailing_enabled,
                    trailing_start=(
                        current_price
                        * self.trailing_percent
                        / 100
                    ),
                    trailing_distance=(
                        current_price
                        * self.trailing_percent
                        / 200
                    )
                )

                success, data = (
                    self._normalize_trade_result(result)
                )

                if success:
                    self.last_signal[symbol] = "SELL"
                    self.last_signals[symbol] = "SELL"

                return success, data

            side = position.get(
                "position_side"
            )

            if side == "SHORT":

                return True, {
                    "status": "NO_ACTION",
                    "message": (
                        f"🔴 {symbol} already SHORT"
                    )
                }

            success, result = (
                self.paper_trader.sell(
                    current_price,
                    exit_reason="SIGNAL_SELL",
                    symbol=symbol,
                    option_mode="N/A"
                )
            )

            if success:
                self.last_signal[symbol] = "SELL"
                self.last_signals[symbol] = "SELL"

            return success, result

        return True, {
            "status": "NO_ACTION"
        }

    # =====================================================
    # INDIAN OPTIONS
    # =====================================================

    def _process_indian_options(
        self,
        symbol,
        signal,
        current_price,
        capital,
        option_mode,
        lots,
        lot_size,
        strike,
        expiry,
        option_type,
        price_by_option=None,
        contract_by_option=None
    ):

        if option_mode not in (
            "CE",
            "PE",
            "ALL"
        ):
            return False, (
                "❌ Indian Options mode must be "
                "CE, PE or ALL"
            )

        # =================================================
        # SELL = EXIT ONLY
        # =================================================

        if signal == "SELL":

            modes = (
                ["CE", "PE"]
                if option_mode == "ALL"
                else [option_mode]
            )

            results = []

            for mode in modes:

                price = current_price

                if isinstance(price_by_option, dict):

                    try:
                        price = float(
                            price_by_option.get(
                                mode,
                                current_price
                            )
                        )
                    except Exception:
                        price = current_price

                position = self.paper_trader.get_position(
                    symbol,
                    mode,
                    strike=strike,
                    expiry=expiry
                )

                if position is None:
                    continue

                success, result = (
                    self.paper_trader.sell(
                        price,
                        exit_reason="SIGNAL_SELL",
                        symbol=symbol,
                        option_mode=mode,
                        strike=position.get("strike"),
                        expiry=position.get("expiry")
                    )
                )

                results.append({
                    "option_mode": mode,
                    "success": success,
                    "result": result
                })

            if not results:

                return True, {
                    "status": "NO_POSITION",
                    "message": (
                        f"ℹ️ No BUY position to exit "
                        f"for {symbol}"
                    )
                }

            return True, {
                "status": "SELL_EXIT",
                "results": results
            }

        # =================================================
        # BUY
        # =================================================

        if not self.is_market_open(symbol):

            return False, (
                "⏰ Indian market is closed"
            )

        modes = (
            ["CE", "PE"]
            if option_mode == "ALL"
            else [option_mode]
        )

        results = []

        for mode in modes:

            price = current_price

            if isinstance(price_by_option, dict):

                try:
                    price = float(
                        price_by_option.get(
                            mode,
                            current_price
                        )
                    )
                except Exception:
                    price = current_price

            contract = None

            if isinstance(contract_by_option, dict):

                contract = contract_by_option.get(
                    mode
                )

            result = self._buy_option(
                symbol=symbol,
                option_type=mode,
                current_price=price,
                capital=capital,
                lots=lots,
                lot_size=lot_size,
                strike=strike,
                expiry=expiry,
                option_contract=contract
            )

            success, data = (
                self._normalize_trade_result(result)
            )

            results.append({
                "option_mode": mode,
                "success": success,
                "result": data
            })

        if option_mode == "ALL":

            successful = [
                x for x in results
                if x["success"]
            ]

            return (
                bool(successful),
                {
                    "status": "ALL_BUY",
                    "results": results
                }
            )

        return (
            results[0]["success"],
            results[0]["result"]
        )

    # =====================================================
    # BUY OPTION
    # =====================================================

    def _buy_option(
        self,
        symbol,
        option_type,
        current_price,
        capital,
        lots,
        lot_size,
        strike=None,
        expiry=None,
        option_contract=None
    ):

        option_type = str(
            option_type or ""
        ).upper().strip()

        if option_type not in (
            "CE",
            "PE"
        ):
            return False, (
                "❌ Invalid option type"
            )

        if current_price <= 0:
            return False, (
                "❌ Invalid option premium"
            )

        # -------------------------------------------------
        # Contract metadata
        # -------------------------------------------------

        contract = {}

        if isinstance(option_contract, dict):
            contract.update(option_contract)

        contract.setdefault(
            "index",
            symbol
        )

        contract["option_type"] = option_type

        if strike is not None:
            contract["strike"] = strike

        if expiry is not None:
            contract["expiry"] = expiry

        contract.setdefault(
            "exchange",
            "NSE"
        )

        strike = contract.get(
            "strike",
            strike
        )

        expiry = contract.get(
            "expiry",
            expiry
        )

        # -------------------------------------------------
        # Expiry required for real option contract
        # -------------------------------------------------

        if expiry in (
            None,
            "",
            "NONE",
            "EXPIRY"
        ):

            logging.warning(
                f"⚠️ {symbol} {option_type}: "
                "expiry not available"
            )

        # -------------------------------------------------
        # Existing position
        # -------------------------------------------------

        existing = self.paper_trader.get_position(
            symbol,
            option_type,
            strike=strike,
            expiry=expiry
        )

        if existing is not None:

            return False, (
                f"⚠️ {symbol} {option_type} "
                f"position already exists"
            )

        # -------------------------------------------------
        # Risk
        # -------------------------------------------------

        stoploss = round(
            current_price * 0.99,
            8
        )

        target = round(
            current_price * 1.02,
            8
        )

        try:

            details = calculate_trade_details(
                capital=capital,
                entry_price=current_price,
                stoploss_price=stoploss,
                lot_size=lot_size,
                target_price=target
            )

        except TypeError:

            details = calculate_trade_details(
                capital=capital,
                entry_price=current_price,
                stoploss_price=stoploss,
                lot_size=lot_size
            )

        except Exception as e:

            logging.warning(
                f"Risk calculation failed: {e}"
            )

            details = {}

        calculated_lots = 0

        if isinstance(details, dict):

            for key in (
                "lots",
                "calculated_lots"
            ):

                if key in details:

                    try:
                        calculated_lots = int(
                            details[key]
                        )
                        break
                    except Exception:
                        pass

        # -------------------------------------------------
        # If risk manager returns 0, do NOT force 1
        # -------------------------------------------------

        if calculated_lots <= 0:

            # User-selected lots can still be used
            # only if capital can support it.
            try:
                requested_lots = int(lots)
            except Exception:
                requested_lots = 0

            if requested_lots <= 0:

                return False, (
                    "❌ Risk calculation allows "
                    "0 lots"
                )

            calculated_lots = requested_lots

        else:

            try:
                requested_lots = int(lots)
            except Exception:
                requested_lots = calculated_lots

            calculated_lots = min(
                requested_lots,
                calculated_lots
            )

        if calculated_lots <= 0:

            return False, (
                "❌ No valid lot quantity available"
            )

        quantity = (
            calculated_lots
            * int(lot_size)
        )

        # -------------------------------------------------
        # BUY paper option
        # -------------------------------------------------

        result = self.paper_trader.buy(
            symbol=symbol,
            price=current_price,
            qty=quantity,
            target=target,
            stoploss=stoploss,
            trailing_enabled=self.trailing_enabled,
            trailing_start=(
                current_price
                * self.trailing_percent
                / 100
            ),
            trailing_distance=(
                current_price
                * self.trailing_percent
                / 200
            ),
            option_mode=option_type,
            option_contract=contract
        )

        success, data = (
            self._normalize_trade_result(result)
        )

        if success:

            self.last_signal[
                self._position_key(
                    symbol,
                    option_type,
                    strike,
                    expiry
                )
            ] = "BUY"

            self.last_signals[
                self._position_key(
                    symbol,
                    option_type,
                    strike,
                    expiry
                )
            ] = "BUY"

        return success, data

    # =====================================================
    # CHECK POSITION / AUTO EXIT
    # =====================================================

    def check_position(
        self,
        current_price,
        symbol,
        option_mode="N/A",
        strike=None,
        expiry=None
    ):

        if self.paper_trader is None:
            return None

        try:

            return self.paper_trader.auto_exit(
                current_price=current_price,
                symbol=symbol,
                option_mode=option_mode,
                strike=strike,
                expiry=expiry
            )

        except Exception as e:

            logging.exception(
                f"❌ Position check error: {e}"
            )

            return None

    # =====================================================
    # CLOSE POSITION
    # =====================================================

    def close_position(
        self,
        symbol,
        current_price,
        option_mode="N/A",
        strike=None,
        expiry=None
    ):

        if self.paper_trader is None:
            return False, "❌ PaperTrader unavailable"

        position = self.paper_trader.get_position(
            symbol,
            option_mode,
            strike=strike,
            expiry=expiry
        )

        if position is None:

            return False, (
                "❌ No active position"
            )

        side = position.get(
            "position_side",
            "LONG"
        )

        if side == "SHORT":

            return self.paper_trader.cover_short(
                current_price,
                exit_reason="MANUAL_CLOSE",
                symbol=symbol,
                option_mode=option_mode
            )

        return self.paper_trader.sell(
            current_price,
            exit_reason="MANUAL_CLOSE",
            symbol=symbol,
            option_mode=option_mode,
            strike=position.get("strike"),
            expiry=position.get("expiry")
        )

    # =====================================================
    # ACTIVE POSITIONS
    # =====================================================

    def get_active_positions(self):

        if self.paper_trader is None:
            return {}

        return self.paper_trader.get_active_positions()