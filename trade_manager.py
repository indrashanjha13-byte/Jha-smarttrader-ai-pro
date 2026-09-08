import logging
from datetime import datetime, time

from ai_learning import auto_strategy
from risk_manager import calculate_trade_details
from config import LOT_SIZE, MODE


logger = logging.getLogger(__name__)


class TradeManager:
    """
    Central Paper Trading Manager

    Indian Options:
        CE / PE -> BUY only
        SELL    -> EXIT existing BUY

    Delta Futures:
        BUY  -> LONG
        SELL -> SHORT
        Opposite signal -> Close existing + Reverse
    """

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

        if s.endswith("USD"):
            return True

        if s.endswith("USDT"):
            return True

        return False

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
        # DELTA FUTURES
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
        # INDIAN MARKET
        # ------------------------------------------------------

        now = datetime.now().time()

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

            signal = str(signal or "HOLD").strip().upper()

            option_mode = str(
                option_mode or "N/A"
            ).strip().upper()

            current_price = float(current_price or 0)

            capital = float(capital or 0)

            lots = int(lots or 1)

            if lot_size is None:
                lot_size = LOT_SIZE

            lot_size = int(lot_size or 1)

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

        if signal not in {"BUY", "SELL", "HOLD"}:

            return False, f"❌ Invalid signal: {signal}"

        if signal == "HOLD":

            return False, "⏸️ HOLD signal - no trade."

        if current_price <= 0:

            return False, "❌ Invalid market price."

        if self.paper_trader is None:

            return False, "❌ PaperTrader is not connected."

        # ------------------------------------------------------
        # PAPER MODE CHECK
        # ------------------------------------------------------

        if str(MODE).upper() != "PAPER":

            return (
                False,
                "⚠️ Live trading is disabled. MODE must be PAPER.",
            )

        # ------------------------------------------------------
        # AI STRATEGY CHECK
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

            return (
                False,
                f"⏰ {timing['message']}",
            )

        position = self._get_position(
            symbol,
            "N/A",
        )

        # ------------------------------------------------------
        # BUY SIGNAL -> LONG
        # ------------------------------------------------------

        if signal == "BUY":

            # No position -> OPEN LONG
            if not position:

                return self._open_delta_long(
                    symbol=symbol,
                    current_price=current_price,
                    capital=capital,
                    lots=lots,
                    lot_size=lot_size,
                )

            position_side = str(
                position.get(
                    "position_side",
                    position.get("side", "BUY"),
                )
            ).upper()

            # Existing LONG -> duplicate protection
            if position_side in {"LONG", "BUY"}:

                return (
                    False,
                    "⚠️ BUY ignored - LONG position already active.",
                )

            # Existing SHORT -> CLOSE SHORT + OPEN LONG
            if position_side in {"SHORT", "SELL"}:

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
                        symbol=symbol,
                        current_price=current_price,
                        capital=capital,
                        lots=lots,
                        lot_size=lot_size,
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

        # ------------------------------------------------------
        # SELL SIGNAL -> SHORT
        # ------------------------------------------------------

        if signal == "SELL":

            # No position -> OPEN SHORT
            if not position:

                return self._open_delta_short(
                    symbol=symbol,
                    current_price=current_price,
                    capital=capital,
                    lots=lots,
                    lot_size=lot_size,
                )

            position_side = str(
                position.get(
                    "position_side",
                    position.get("side", "BUY"),
                )
            ).upper()

            # Existing SHORT -> duplicate protection
            if position_side in {"SHORT", "SELL"}:

                return (
                    False,
                    "⚠️ SELL ignored - SHORT position already active.",
                )

            # Existing LONG -> CLOSE LONG + OPEN SHORT
            if position_side in {"LONG", "BUY"}:

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
                        symbol=symbol,
                        current_price=current_price,
                        capital=capital,
                        lots=lots,
                        lot_size=lot_size,
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
    # OPEN DELTA LONG
    # ==========================================================

    def _open_delta_long(
        self,
        symbol,
        current_price,
        capital,
        lots=1,
        lot_size=1,
    ):

        if current_price <= 0:

            return False, "❌ Invalid Delta price."

        # ------------------------------------------------------
        # Duplicate protection
        # ------------------------------------------------------

        existing = self._get_position(
            symbol,
            "N/A",
        )

        if existing:

            side = str(
                existing.get(
                    "position_side",
                    existing.get("side", "BUY"),
                )
            ).upper()

            if side in {"LONG", "BUY"}:

                return (
                    False,
                    "⚠️ LONG position already active.",
                )

        # ------------------------------------------------------
        # Delta default risk model
        #
        # 1% SL
        # 2% Target
        # ------------------------------------------------------

        stop_loss = current_price * 0.99
        target = current_price * 1.02

        # ------------------------------------------------------
        # Quantity
        #
        # For safe paper execution, at least 1 contract.
        # ------------------------------------------------------

        quantity = max(
            1,
            int(lots) * max(1, int(lot_size)),
        )

        try:

            result = self.paper_trader.buy(
                symbol=symbol,
                price=current_price,
                qty=quantity,
                stoploss=stop_loss,
                target=target,
                option_mode="N/A",
                trailing_enabled=self.trailing_enabled,
                trailing_percent=self.trailing_percent,
                strike=None,
                expiry=None,
                option_type=None,
            )

        except TypeError:

            # Compatibility with older PaperTrader.buy()
            result = self.paper_trader.buy(
                symbol=symbol,
                price=current_price,
                qty=quantity,
                stoploss=stop_loss,
                target=target,
                option_mode="N/A",
            )

        success, message = self._normalize_trade_result(
            result
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
    # OPEN DELTA SHORT
    # ==========================================================

    def _open_delta_short(
        self,
        symbol,
        current_price,
        capital,
        lots=1,
        lot_size=1,
    ):

        if current_price <= 0:

            return False, "❌ Invalid Delta price."

        # ------------------------------------------------------
        # Duplicate protection
        # ------------------------------------------------------

        existing = self._get_position(
            symbol,
            "N/A",
        )

        if existing:

            side = str(
                existing.get(
                    "position_side",
                    existing.get("side", "BUY"),
                )
            ).upper()

            if side in {"SHORT", "SELL"}:

                return (
                    False,
                    "⚠️ SHORT position already active.",
                )

        # ------------------------------------------------------
        # SHORT risk model
        #
        # SL above entry
        # Target below entry
        # ------------------------------------------------------

        stop_loss = current_price * 1.01
        target = current_price * 0.98

        quantity = max(
            1,
            int(lots) * max(1, int(lot_size)),
        )

        try:

            result = self.paper_trader.short(
                symbol=symbol,
                price=current_price,
                qty=quantity,
                stoploss=stop_loss,
                target=target,
                option_mode="N/A",
                trailing_enabled=self.trailing_enabled,
                trailing_percent=self.trailing_percent,
                strike=None,
                expiry=None,
                option_type=None,
            )

        except TypeError:

            result = self.paper_trader.short(
                symbol=symbol,
                price=current_price,
                qty=quantity,
                stoploss=stop_loss,
                target=target,
                option_mode="N/A",
            )

        success, message = self._normalize_trade_result(
            result
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
    # INDIAN OPTIONS PROCESSOR
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

        timing = self.market_timing(symbol)

        # ------------------------------------------------------
        # SELL = EXIT ONLY
        # ------------------------------------------------------

        if signal == "SELL":

            if option_mode == "ALL":

                positions = (
                    self.paper_trader.get_all_positions()
                )

                closed_count = 0

                for position in positions:

                    pos_symbol = str(
                        position.get("symbol", "")
                    ).upper()

                    if pos_symbol != symbol.upper():
                        continue

                    pos_side = str(
                        position.get(
                            "position_side",
                            position.get("side", "BUY"),
                        )
                    ).upper()

                    if pos_side not in {"LONG", "BUY"}:
                        continue

                    success, _ = (
                        self.paper_trader.sell(
                            symbol=symbol,
                            option_mode=position.get(
                                "option_mode",
                                "N/A",
                            ),
                            current_price=current_price,
                        )
                    )

                    if success:
                        closed_count += 1

                if closed_count:

                    return (
                        True,
                        f"🔴 OPTIONS EXIT | "
                        f"{symbol} | "
                        f"{closed_count} position(s) closed.",
                    )

                return (
                    False,
                    "⚠️ No active BUY option position to exit.",
                )

            # Normal CE / PE / N/A
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
                    f"{result}",
                )

            return (
                False,
                f"⚠️ {result}",
            )

        # ------------------------------------------------------
        # BUY ENTRY MARKET CHECK
        # ------------------------------------------------------

        if not timing["entry_allowed"]:

            return (
                False,
                f"⏰ {timing['message']}",
            )

        # ------------------------------------------------------
        # ALL = BUY CE + BUY PE
        # ------------------------------------------------------

        if option_mode == "ALL":

            results = []

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

            if ce_success or pe_success:

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
        # CE / PE
        # ------------------------------------------------------

        return self._buy_option(
            symbol=symbol,
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
            "N/A",
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

        # ------------------------------------------------------
        # DUPLICATE PROTECTION
        # ------------------------------------------------------

        existing = self._get_position(
            symbol,
            option_mode,
        )

        if existing:

            return (
                False,
                f"⚠️ {option_mode} BUY position already active.",
            )

        # ------------------------------------------------------
        # STOP LOSS
        # ------------------------------------------------------

        stop_loss = current_price * 0.99

        # ------------------------------------------------------
        # RISK MANAGER
        # ------------------------------------------------------

        calculated_lots = lots

        target = current_price * 1.02

        try:

            risk_details = calculate_trade_details(
                entry_price=current_price,
                stoploss=stop_loss,
                capital=capital,
                lot_size=lot_size,
                reward_ratio=2,
            )

            if isinstance(risk_details, dict):

                calculated_lots = int(
                    risk_details.get(
                        "lots",
                        risk_details.get(
                            "quantity_lots",
                            lots,
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
            * max(1, int(lot_size))
        )

        # ------------------------------------------------------
        # PAPER BUY
        # ------------------------------------------------------

        try:

            result = self.paper_trader.buy(
                symbol=symbol,
                price=current_price,
                qty=quantity,
                stoploss=stop_loss,
                target=target,
                option_mode=option_mode,
                trailing_enabled=self.trailing_enabled,
                trailing_percent=self.trailing_percent,
                strike=strike,
                expiry=expiry,
                option_type=option_type,
            )

        except TypeError:

            result = self.paper_trader.buy(
                symbol=symbol,
                price=current_price,
                qty=quantity,
                stoploss=stop_loss,
                target=target,
                option_mode=option_mode,
            )

        success, message = self._normalize_trade_result(
            result
        )

        if success:

            self.last_signal[
                f"{symbol}:{option_mode}"
            ] = "BUY"

            return (
                True,
                f"🟢 OPTION BUY | "
                f"{symbol} {option_mode} | "
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

        if isinstance(result, tuple):

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

        if isinstance(result, bool):

            return result, ""

        if result is None:

            return False, "No result returned."

        return True, str(result)

    # ==========================================================
    # POSITION CHECK / AUTO EXIT
    # ==========================================================

    def check_position(
        self,
        current_price,
        symbol,
        option_mode="N/A",
    ):

        if not self.paper_trader:

            return False, "PaperTrader unavailable."

        if current_price <= 0:

            return False, "Invalid current price."

        try:

            result = self.paper_trader.auto_exit(
                symbol=symbol,
                option_mode=option_mode,
                current_price=current_price,
            )

            success, message = (
                self._normalize_trade_result(result)
            )

            return success, message

        except TypeError:

            try:

                result = self.paper_trader.auto_exit(
                    symbol,
                    option_mode,
                    current_price,
                )

                return self._normalize_trade_result(
                    result
                )

            except Exception as e:

                logger.exception(
                    "Auto exit failed"
                )

                return False, str(e)

        except Exception as e:

            logger.exception(
                "Auto exit failed"
            )

            return False, str(e)

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

            return False, "PaperTrader unavailable."

        position = self._get_position(
            symbol,
            option_mode,
        )

        if not position:

            return False, "No active position."

        side = str(
            position.get(
                "position_side",
                position.get("side", "BUY"),
            )
        ).upper()

        try:

            if side in {"SHORT", "SELL"}:

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

            return False, str(e)

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

        if not self.paper_trader:

            return []

        try:

            return self.paper_trader.get_all_positions()

        except Exception:

            return []