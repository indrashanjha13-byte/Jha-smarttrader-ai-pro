import logging
from datetime import datetime, time
from zoneinfo import ZoneInfo

from ai_learning import auto_strategy
from risk_manager import calculate_trade_details
from config import LOT_SIZE, MODE


logger = logging.getLogger(__name__)

IST = ZoneInfo("Asia/Kolkata")


class TradeManager:
    """
    Central Paper Trading Manager.

    INDIAN OPTIONS:
        BUY CE -> Open CE LONG
        BUY PE -> Open PE LONG
        SELL CE -> Exit existing CE BUY
        SELL PE -> Exit existing PE BUY
        ALL -> BUY CE + BUY PE / SELL exits both

    DELTA FUTURES:
        BUY  -> LONG
        SELL -> SHORT
        SELL on LONG  -> Close LONG + Reverse SHORT
        BUY on SHORT  -> Close SHORT + Reverse LONG

    LIVE BROKER ORDERS ARE NOT USED.
    """

    # ==========================================================
    # INIT
    # ==========================================================

    def __init__(self, paper_trader=None):

        self.paper_trader = paper_trader

        self.last_signal = {}
        self.last_signals = {}

        self.active_position = None

        self.trailing_enabled = True
        self.trailing_percent = 0.5

    # ==========================================================
    # PAPER TRADER
    # ==========================================================

    def set_paper_trader(self, paper_trader):
        self.paper_trader = paper_trader

    # ==========================================================
    # TRAILING SETTINGS
    # ==========================================================

    def set_trailing_settings(
        self,
        enabled=True,
        trailing_percent=0.5,
    ):

        self.trailing_enabled = bool(enabled)

        try:
            self.trailing_percent = float(trailing_percent)
        except Exception:
            self.trailing_percent = 0.5

    # ==========================================================
    # DELTA MARKET DETECTOR
    # ==========================================================

    @staticmethod
    def is_delta_market(symbol):

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

        if s in delta_symbols:
            return True

        return s.endswith("USD") or s.endswith("USDT")

    # ==========================================================
    # POSITION KEY
    # ==========================================================

    @staticmethod
    def _position_key(symbol, option_mode="N/A"):

        return (
            str(symbol or "").strip().upper(),
            str(option_mode or "N/A").strip().upper(),
        )

    # ==========================================================
    # MARKET TIMING
    # ==========================================================

    def market_timing(self, symbol=None):

        symbol = str(symbol or "").strip().upper()

        # ------------------------------------------------------
        # DELTA
        # ------------------------------------------------------

        if self.is_delta_market(symbol):

            return {
                "market": "DELTA",
                "status": "OPEN_24X7",
                "entry_allowed": True,
                "manage_positions": True,
                "message": "Delta Futures market is open 24/7.",
            }

        # ------------------------------------------------------
        # INDIA - IST
        # ------------------------------------------------------

        now = datetime.now(IST).time()

        market_open = time(9, 15)
        market_close = time(15, 30)

        if market_open <= now <= market_close:

            return {
                "market": "INDIA",
                "status": "MARKET_OPEN",
                "entry_allowed": True,
                "manage_positions": True,
                "message": "Indian market is open.",
            }

        return {
            "market": "INDIA",
            "status": "MARKET_CLOSED",
            "entry_allowed": False,
            "manage_positions": True,
            "message": "Indian market is closed. Trading entry disabled.",
        }

    # ==========================================================
    # POSITION HELPERS
    # ==========================================================

    def _get_position(self, symbol, option_mode="N/A"):

        if not self.paper_trader:
            return None

        try:

            return self.paper_trader.get_position(
                symbol,
                option_mode,
            )

        except Exception as e:

            logger.warning(
                "Position lookup failed: %s",
                e,
            )

            return None

    # ==========================================================
    # GET ALL POSITIONS
    # ==========================================================

    def _get_all_positions(self):

        if not self.paper_trader:
            return {}

        try:

            return self.paper_trader.get_active_positions()

        except Exception as e:

            logger.warning(
                "Active positions lookup failed: %s",
                e,
            )

            return {}

    # ==========================================================
    # MAIN PROCESS
    # ==========================================================

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
    ):

        try:

            symbol = str(symbol or "").strip().upper()

            signal = str(
                signal or "HOLD"
            ).strip().upper()

            option_mode = str(
                option_mode or "N/A"
            ).strip().upper()

            current_price = float(
                current_price or 0
            )

            capital = float(
                capital or 0
            )

            lots = int(
                lots or 1
            )

            if lot_size is None:
                lot_size = LOT_SIZE

            lot_size = int(
                lot_size or 1
            )

        except Exception as e:

            logger.exception(
                "TradeManager input normalization failed"
            )

            return False, f"❌ Invalid trade input: {e}"

        # ------------------------------------------------------
        # BASIC VALIDATION
        # ------------------------------------------------------

        if not symbol:
            return False, "❌ Symbol missing."

        if signal not in {
            "BUY",
            "SELL",
            "HOLD",
        }:
            return False, f"❌ Invalid signal: {signal}"

        if signal == "HOLD":
            return False, "⏸️ HOLD signal - no trade."

        if current_price <= 0:
            return False, "❌ Invalid market price."

        if self.paper_trader is None:
            return False, "❌ PaperTrader is not connected."

        # ------------------------------------------------------
        # PAPER MODE ONLY
        # ------------------------------------------------------

        if str(MODE).upper() != "PAPER":

            return (
                False,
                "⚠️ Live trading is disabled. MODE must be PAPER.",
            )

        # ------------------------------------------------------
        # AI STRATEGY
        # ------------------------------------------------------

        try:

            auto_strategy(
                symbol=symbol,
                signal=signal,
                current_price=current_price,
            )

        except TypeError:

            try:

                auto_strategy(
                    symbol,
                    signal,
                    current_price,
                )

            except Exception:
                pass

        except Exception as e:

            logger.warning(
                "AI strategy check skipped: %s",
                e,
            )

        # ======================================================
        # DELTA FUTURES
        # ======================================================

        if self.is_delta_market(symbol):

            return self._process_delta(
                symbol=symbol,
                signal=signal,
                current_price=current_price,
                capital=capital,
                lots=lots,
                lot_size=lot_size,
            )

        # ======================================================
        # INDIAN OPTIONS
        # ======================================================

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
        )

    # ==========================================================
    # DELTA PROCESSOR
    # ==========================================================

    def _process_delta(
        self,
        symbol,
        signal,
        current_price,
        capital,
        lots=1,
        lot_size=1,
    ):

        timing = self.market_timing(symbol)

        if not timing["entry_allowed"]:

            return False, f"⏰ {timing['message']}"

        position = self._get_position(
            symbol,
            "N/A",
        )

        # ======================================================
        # BUY -> LONG
        # ======================================================

        if signal == "BUY":

            if not position:

                return self._open_delta_long(
                    symbol,
                    current_price,
                    capital,
                    lots,
                    lot_size,
                )

            position_side = str(
                position.get(
                    "position_side",
                    position.get("side", "BUY"),
                )
            ).upper()

            if position_side in {
                "LONG",
                "BUY",
            }:

                return (
                    False,
                    "⚠️ BUY ignored - LONG position already active.",
                )

            if position_side in {
                "SHORT",
                "SELL",
            }:

                logger.info(
                    "Delta reversal SHORT -> LONG: %s",
                    symbol,
                )

                closed, close_result = (
                    self.paper_trader.cover_short(
                        symbol=symbol,
                        option_mode="N/A",
                        current_price=current_price,
                    )
                )

                if not closed:

                    return (
                        False,
                        f"❌ Unable to close SHORT: {close_result}",
                    )

                opened, open_result = (
                    self._open_delta_long(
                        symbol,
                        current_price,
                        capital,
                        lots,
                        lot_size,
                    )
                )

                if opened:

                    return (
                        True,
                        f"🔄 SHORT → LONG | {open_result}",
                    )

                return (
                    False,
                    f"⚠️ SHORT closed, LONG not opened: {open_result}",
                )

        # ======================================================
        # SELL -> SHORT
        # ======================================================

        if signal == "SELL":

            if not position:

                return self._open_delta_short(
                    symbol,
                    current_price,
                    capital,
                    lots,
                    lot_size,
                )

            position_side = str(
                position.get(
                    "position_side",
                    position.get("side", "BUY"),
                )
            ).upper()

            if position_side in {
                "SHORT",
                "SELL",
            }:

                return (
                    False,
                    "⚠️ SELL ignored - SHORT position already active.",
                )

            if position_side in {
                "LONG",
                "BUY",
            }:

                logger.info(
                    "Delta reversal LONG -> SHORT: %s",
                    symbol,
                )

                closed, close_result = (
                    self.paper_trader.sell(
                        symbol=symbol,
                        option_mode="N/A",
                        current_price=current_price,
                    )
                )

                if not closed:

                    return (
                        False,
                        f"❌ Unable to close LONG: {close_result}",
                    )

                opened, open_result = (
                    self._open_delta_short(
                        symbol,
                        current_price,
                        capital,
                        lots,
                        lot_size,
                    )
                )

                if opened:

                    return (
                        True,
                        f"🔄 LONG → SHORT | {open_result}",
                    )

                return (
                    False,
                    f"⚠️ LONG closed, SHORT not opened: {open_result}",
                )

        return False, "⚠️ No valid Delta trade action."

    # ==========================================================
    # DELTA LONG
    # ==========================================================

    def _open_delta_long(
        self,
        symbol,
        current_price,
        capital,
        lots=1,
        lot_size=1,
    ):

        stop_loss = current_price * 0.99
        target = current_price * 1.02

        quantity = max(
            1,
            int(lots) * max(
                1,
                int(lot_size),
            ),
        )

        try:

            result = self.paper_trader.buy(
                symbol=symbol,
                price=current_price,
                qty=quantity,
                target=target,
                stoploss=stop_loss,
                trailing_enabled=self.trailing_enabled,
                trailing_start=current_price * 0.005,
                trailing_distance=current_price * 0.0025,
                option_mode="N/A",
                option_contract=None,
            )

        except Exception as e:

            logger.exception(
                "Delta LONG paper order failed"
            )

            return False, str(e)

        success, message = (
            self._normalize_trade_result(result)
        )

        if success:

            self.last_signal[symbol] = "BUY"
            self.last_signals[symbol] = "BUY"

            return (
                True,
                f"🟢 DELTA LONG OPENED | "
                f"{symbol} | "
                f"Entry ${current_price:.8f} | "
                f"SL ${stop_loss:.8f} | "
                f"Target ${target:.8f} | "
                f"Qty {quantity}",
            )

        return (
            False,
            f"❌ Delta LONG failed: {message}",
        )

    # ==========================================================
    # DELTA SHORT
    # ==========================================================

    def _open_delta_short(
        self,
        symbol,
        current_price,
        capital,
        lots=1,
        lot_size=1,
    ):

        stop_loss = current_price * 1.01
        target = current_price * 0.98

        quantity = max(
            1,
            int(lots) * max(
                1,
                int(lot_size),
            ),
        )

        try:

            result = self.paper_trader.short(
                symbol=symbol,
                price=current_price,
                qty=quantity,
                target=target,
                stoploss=stop_loss,
                trailing_enabled=self.trailing_enabled,
                trailing_start=current_price * 0.005,
                trailing_distance=current_price * 0.0025,
                option_mode="N/A",
                option_contract=None,
            )

        except Exception as e:

            logger.exception(
                "Delta SHORT paper order failed"
            )

            return False, str(e)

        success, message = (
            self._normalize_trade_result(result)
        )

        if success:

            self.last_signal[symbol] = "SELL"
            self.last_signals[symbol] = "SELL"

            return (
                True,
                f"🔴 DELTA SHORT OPENED | "
                f"{symbol} | "
                f"Entry ${current_price:.8f} | "
                f"SL ${stop_loss:.8f} | "
                f"Target ${target:.8f} | "
                f"Qty {quantity}",
            )

        return (
            False,
            f"❌ Delta SHORT failed: {message}",
        )

    # ==========================================================
    # INDIAN OPTIONS
    # ==========================================================

    def _process_indian_options(
        self,
        symbol,
        signal,
        current_price,
        capital,
        option_mode,
        lots=1,
        lot_size=1,
        strike=None,
        expiry=None,
        option_type=None,
    ):

        option_mode = str(
            option_mode or "N/A"
        ).upper()

        # ======================================================
        # SELL = EXIT ONLY
        # ======================================================

        if signal == "SELL":

            # --------------------------------------------------
            # ALL -> EXIT CE + PE
            # --------------------------------------------------

            if option_mode == "ALL":

                positions = self._get_all_positions()

                closed_count = 0
                close_results = []

                for position_key, position in list(
                    positions.items()
                ):

                    if not position:
                        continue

                    pos_symbol = str(
                        position.get(
                            "symbol",
                            "",
                        )
                    ).upper()

                    if pos_symbol != symbol.upper():
                        continue

                    pos_mode = str(
                        position.get(
                            "option_mode",
                            "N/A",
                        )
                    ).upper()

                    if pos_mode not in {
                        "CE",
                        "PE",
                    }:
                        continue

                    pos_side = str(
                        position.get(
                            "position_side",
                            position.get(
                                "side",
                                "BUY",
                            ),
                        )
                    ).upper()

                    if pos_side not in {
                        "LONG",
                        "BUY",
                    }:
                        continue

                    success, result = (
                        self.paper_trader.sell(
                            symbol=symbol,
                            option_mode=pos_mode,
                            current_price=current_price,
                        )
                    )

                    if success:

                        closed_count += 1
                        close_results.append(
                            f"{pos_mode}: ₹{float(result):.2f}"
                        )

                if closed_count:

                    return (
                        True,
                        f"🔴 OPTIONS EXIT | "
                        f"{symbol} | "
                        f"{closed_count} position(s) closed | "
                        f"{' | '.join(close_results)}",
                    )

                return (
                    False,
                    "⚠️ No active BUY option position to exit.",
                )

            # --------------------------------------------------
            # CE / PE -> EXIT ONLY
            # --------------------------------------------------

            if option_mode not in {
                "CE",
                "PE",
            }:

                return (
                    False,
                    "❌ Option SELL requires CE, PE or ALL.",
                )

            success, result = (
                self.paper_trader.sell(
                    symbol=symbol,
                    option_mode=option_mode,
                    current_price=current_price,
                )
            )

            if success:

                return (
                    True,
                    f"🔴 OPTION EXIT | "
                    f"{symbol} {option_mode} | "
                    f"P&L ₹{float(result):.2f}",
                )

            return (
                False,
                f"⚠️ {result}",
            )

        # ======================================================
        # BUY ENTRY
        # ======================================================

        timing = self.market_timing(symbol)

        if not timing["entry_allowed"]:

            return (
                False,
                f"⏰ {timing['message']}",
            )

        # ------------------------------------------------------
        # ALL -> BUY CE + PE
        # ------------------------------------------------------

        if option_mode == "ALL":

            results = []
            success_count = 0

            ce_success, ce_result = (
                self._buy_option(
                    symbol=symbol,
                    current_price=current_price,
                    capital=capital,
                    option_mode="CE",
                    lots=lots,
                    lot_size=lot_size,
                    strike=strike,
                    expiry=expiry,
                    option_type="CE",
                )
            )

            results.append(
                f"CE: {ce_result}"
            )

            if ce_success:
                success_count += 1

            pe_success, pe_result = (
                self._buy_option(
                    symbol=symbol,
                    current_price=current_price,
                    capital=capital,
                    option_mode="PE",
                    lots=lots,
                    lot_size=lot_size,
                    strike=strike,
                    expiry=expiry,
                    option_type="PE",
                )
            )

            results.append(
                f"PE: {pe_result}"
            )

            if pe_success:
                success_count += 1

            if success_count:

                return (
                    True,
                    "🟢 OPTIONS ALL | "
                    + " | ".join(results),
                )

            return (
                False,
                "⚠️ OPTIONS ALL | "
                + " | ".join(results),
            )

        # ------------------------------------------------------
        # ONLY CE / PE BUY
        # ------------------------------------------------------

        if option_mode not in {
            "CE",
            "PE",
        }:

            return (
                False,
                "❌ Option BUY requires CE, PE or ALL.",
            )

        return self._buy_option(
            symbol=symbol,
            current_price=current_price,
            capital=capital,
            option_mode=option_mode,
            lots=lots,
            lot_size=lot_size,
            strike=strike,
            expiry=expiry,
            option_type=option_type or option_mode,
        )

    # ==========================================================
    # BUY OPTION
    # ==========================================================

    def _buy_option(
        self,
        symbol,
        current_price,
        capital,
        option_mode,
        lots=1,
        lot_size=1,
        strike=None,
        expiry=None,
        option_type=None,
    ):

        option_mode = str(
            option_mode or "N/A"
        ).upper()

        if option_mode not in {
            "CE",
            "PE",
        }:

            return (
                False,
                f"❌ Invalid option mode: {option_mode}",
            )

        if current_price <= 0:

            return (
                False,
                "❌ Invalid option price.",
            )

        # ======================================================
        # DUPLICATE
        # ======================================================

        existing = self._get_position(
            symbol,
            option_mode,
        )

        if existing:

            return (
                False,
                f"⚠️ {symbol} {option_mode} "
                f"BUY position already active.",
            )

        # ======================================================
        # RISK
        # ======================================================

        stop_loss = current_price * 0.99
        target = current_price * 1.02

        calculated_lots = int(lots)

        try:

            risk_details = calculate_trade_details(
                entry_price=current_price,
                stoploss=stop_loss,
                capital=capital,
                lot_size=lot_size,
                reward_ratio=2,
            )

            if isinstance(
                risk_details,
                dict,
            ):

                calculated_lots = int(
                    risk_details.get(
                        "lots",
                        risk_details.get(
                            "quantity_lots",
                            calculated_lots,
                        ),
                    )
                )

                target = float(
                    risk_details.get(
                        "target",
                        risk_details.get(
                            "take_profit",
                            target,
                        ),
                    )
                )

        except Exception as e:

            logger.warning(
                "Risk manager fallback used: %s",
                e,
            )

        calculated_lots = max(
            1,
            min(
                int(lots),
                int(calculated_lots),
            ),
        )

        quantity = (
            calculated_lots
            * max(
                1,
                int(lot_size),
            )
        )

        # ======================================================
        # OPTION CONTRACT
        # ======================================================

        option_contract = {
            "index": symbol,
            "option_type": (
                option_type
                or option_mode
            ),
            "strike": strike,
            "expiry": expiry,
        }

        # ======================================================
        # PAPER BUY
        # ======================================================

        try:

            result = self.paper_trader.buy(
                symbol=symbol,
                price=current_price,
                qty=quantity,
                target=target,
                stoploss=stop_loss,
                trailing_enabled=self.trailing_enabled,
                trailing_start=current_price * 0.005,
                trailing_distance=current_price * 0.0025,
                option_mode=option_mode,
                option_contract=option_contract,
            )

        except Exception as e:

            logger.exception(
                "Paper Option BUY failed"
            )

            return (
                False,
                f"❌ Paper Option BUY error: {e}",
            )

        success, message = (
            self._normalize_trade_result(result)
        )

        if success:

            self.last_signal[
                f"{symbol}:{option_mode}"
            ] = "BUY"

            self.last_signals[
                f"{symbol}:{option_mode}"
            ] = "BUY"

            strike_text = (
                str(strike)
                if strike is not None
                else "ATM"
            )

            expiry_text = (
                str(expiry)
                if expiry
                else "N/A"
            )

            return (
                True,
                f"🟢 PAPER OPTION BUY | "
                f"{symbol} {option_mode} | "
                f"Strike {strike_text} | "
                f"Expiry {expiry_text} | "
                f"Entry ₹{current_price:.2f} | "
                f"SL ₹{stop_loss:.2f} | "
                f"Target ₹{target:.2f} | "
                f"Qty {quantity}",
            )

        return (
            False,
            f"❌ Option BUY failed: {message}",
        )

    # ==========================================================
    # RESULT NORMALIZER
    # ==========================================================

    @staticmethod
    def _normalize_trade_result(result):

        if isinstance(
            result,
            tuple,
        ):

            if len(result) >= 2:

                return (
                    bool(result[0]),
                    result[1],
                )

            if len(result) == 1:

                return (
                    bool(result[0]),
                    "",
                )

        if isinstance(
            result,
            bool,
        ):

            return result, ""

        if result is None:

            return (
                False,
                "No result returned.",
            )

        if isinstance(
            result,
            dict,
        ):

            return (
                True,
                result,
            )

        return (
            True,
            str(result),
        )

    # ==========================================================
    # AUTO EXIT
    # ==========================================================

    def check_position(
        self,
        current_price,
        symbol,
        option_mode="N/A",
    ):

        if not self.paper_trader:

            return (
                False,
                "PaperTrader unavailable.",
            )

        try:

            current_price = float(
                current_price
            )

        except Exception:

            return (
                False,
                "Invalid current price.",
            )

        if current_price <= 0:

            return (
                False,
                "Invalid current price.",
            )

        try:

            result = self.paper_trader.auto_exit(
                current_price=current_price,
                symbol=symbol,
                option_mode=option_mode,
            )

            if result is None:

                return (
                    False,
                    "No auto exit triggered.",
                )

            return (
                True,
                result,
            )

        except Exception as e:

            logger.exception(
                "Auto exit failed"
            )

            return (
                False,
                str(e),
            )

    # ==========================================================
    # CLOSE POSITION
    # ==========================================================

    def close_position(
        self,
        symbol,
        option_mode="N/A",
        current_price=0,
    ):

        if not self.paper_trader:

            return (
                False,
                "PaperTrader unavailable.",
            )

        position = self._get_position(
            symbol,
            option_mode,
        )

        if not position:

            return (
                False,
                "No active position.",
            )

        try:

            current_price = float(
                current_price
            )

        except Exception:

            return (
                False,
                "Invalid current price.",
            )

        if current_price <= 0:

            return (
                False,
                "Invalid current price.",
            )

        side = str(
            position.get(
                "position_side",
                position.get(
                    "side",
                    "BUY",
                ),
            )
        ).upper()

        try:

            if side in {
                "SHORT",
                "SELL",
            }:

                return self.paper_trader.cover_short(
                    symbol=symbol,
                    option_mode=option_mode,
                    current_price=current_price,
                )

            return self.paper_trader.sell(
                symbol=symbol,
                option_mode=option_mode,
                current_price=current_price,
            )

        except Exception as e:

            logger.exception(
                "Close position failed"
            )

            return (
                False,
                str(e),
            )

    # ==========================================================
    # ACTIVE POSITION
    # ==========================================================

    def get_active_position(
        self,
        symbol,
        option_mode="N/A",
    ):

        return self._get_position(
            symbol,
            option_mode,
        )

    # ==========================================================
    # ALL ACTIVE POSITIONS
    # ==========================================================

    def get_active_positions(self):

        return self._get_all_positions()