import logging

from ai_learning import auto_strategy
from risk_manager import calculate_trade_details
from config import LOT_SIZE, MODE

# DEPLOYMENT_REFRESH_2026

class TradeManager:
    """
    Buyer-Only Options Trade Manager.

    Rules:
    - CE -> BUY only
    - PE -> BUY only
    - ALL -> CE + PE BUY positions supported
    - SELL -> EXIT existing BUY position only
    - No short selling
    - PAPER trading only
    - Automatic SL / Target / Trailing SL
    """

    def __init__(
        self,
        paper_trader=None,
        trailing_enabled=False,
        trailing_start=10.0,
        trailing_distance=5.0
    ):
        self.paper_trader = paper_trader

        self.last_signal = None
        self.last_signals = {}

        self.active_position = None

        self.trailing_enabled = bool(trailing_enabled)
        self.trailing_start = float(trailing_start)
        self.trailing_distance = float(trailing_distance)

    # =========================================================
    # PAPER TRADER
    # =========================================================

    def set_paper_trader(self, paper_trader):
        self.paper_trader = paper_trader

    # =========================================================
    # TRAILING SETTINGS
    # =========================================================

    def set_trailing_settings(
        self,
        enabled=False,
        start=10.0,
        distance=5.0
    ):
        try:
            start = float(start)
            distance = float(distance)

            if start <= 0:
                return False, "Trailing start must be greater than 0"

            if distance <= 0:
                return False, "Trailing distance must be greater than 0"

            if distance >= start:
                return False, "Trailing distance must be less than trailing start"

            self.trailing_enabled = bool(enabled)
            self.trailing_start = start
            self.trailing_distance = distance

            logging.info(
                f"Trailing settings updated | "
                f"Enabled={self.trailing_enabled} | "
                f"Start={start} | "
                f"Distance={distance}"
            )

            return True, "Trailing settings updated"

        except Exception as e:
            return False, f"Trailing settings error: {e}"

    # =========================================================
    # POSITION KEY
    # =========================================================

    def _position_key(self, symbol, option_mode):
        return f"{str(symbol).upper()}_{str(option_mode).upper()}"

    # =========================================================
    # PROCESS TRADE
    # =========================================================

    def process(
        self,
        symbol,
        signal,
        current_price,
        capital,
        option_mode="N/A",
        lots=1,
        lot_size=None,
        price_by_option=None
    ):
        """
        Main trade processing.

        BUY:
            Opens BUY position.

        SELL:
            Closes existing BUY position.

        ALL:
            Requires separate CE / PE prices when opening
            both option types.
        """

        try:
            # -------------------------------------------------
            # Normalize
            # -------------------------------------------------

            symbol = str(symbol).strip().upper()
            signal = str(signal).strip().upper()
            option_mode = str(option_mode).strip().upper()

            current_price = float(current_price)
            capital = float(capital)
            lots = int(lots)

            if lot_size is None:
                lot_size = LOT_SIZE

            lot_size = int(lot_size)

            # -------------------------------------------------
            # Validation
            # -------------------------------------------------

            if not symbol:
                return False, "❌ Invalid symbol"

            if signal == "HOLD":
                return False, "HOLD"

            if signal not in ("BUY", "SELL"):
                return False, f"❌ Invalid signal: {signal}"

            if current_price <= 0:
                return False, "❌ Invalid current price"

            if capital <= 0:
                return False, "❌ Invalid capital"

            if lots <= 0:
                return False, "❌ Lots must be greater than 0"

            if lot_size <= 0:
                return False, "❌ Lot size must be greater than 0"

            if option_mode not in ("CE", "PE", "ALL", "N/A"):
                return False, (
                    "❌ Invalid option mode. "
                    "Use CE, PE, ALL or N/A."
                )

            # -------------------------------------------------
            # LIVE LOCK
            # -------------------------------------------------

            if MODE != "PAPER":
                logging.warning(
                    "LIVE mode requested, but live execution is disabled."
                )

                return False, (
                    "🔒 LIVE trading is currently locked. "
                    "Use PAPER mode for testing."
                )

            # -------------------------------------------------
            # Paper Trader Check
            # -------------------------------------------------

            if self.paper_trader is None:
                return False, "❌ PaperTrader is not connected"

            # -------------------------------------------------
            # Strategy
            # -------------------------------------------------

            selected_strategy = "AI Combo"

            try:
                selected_strategy = auto_strategy() or "AI Combo"
            except Exception:
                selected_strategy = "AI Combo"

            # =================================================
            # SELL = EXIT ONLY
            # =================================================

            if signal == "SELL":

                # -------------------------------------------------
                # ALL = Close CE + PE BUY positions
                # -------------------------------------------------

                if option_mode == "ALL":

                    positions = self.paper_trader.get_active_positions()

                    if not positions:
                        return False, "⚠️ No active BUY positions to exit."

                    closed = []
                    failed = []

                    for key, position in list(positions.items()):

                        position_symbol = str(
                            position.get("symbol", "")
                        ).upper()

                        if position_symbol != symbol:
                            continue

                        position_option = str(
                            position.get("option_mode", "N/A")
                        ).upper()

                        exit_price = current_price

                        # Separate price support
                        if isinstance(price_by_option, dict):
                            if position_option in price_by_option:
                                try:
                                    exit_price = float(
                                        price_by_option[position_option]
                                    )
                                except Exception:
                                    exit_price = current_price

                        success, result = self.paper_trader.sell(
                            exit_price,
                            exit_reason="SIGNAL_SELL",
                            symbol=symbol,
                            option_mode=position_option
                        )

                        if success:
                            closed.append({
                                "option_mode": position_option,
                                "price": exit_price,
                                "result": result
                            })
                        else:
                            failed.append({
                                "option_mode": position_option,
                                "result": result
                            })

                    if not closed:
                        return False, (
                            f"⚠️ No active BUY position found for {symbol}."
                        )

                    self.active_position = None
                    self.last_signal = "SELL"

                    return True, {
                        "action": "SELL",
                        "type": "EXIT_ONLY",
                        "symbol": symbol,
                        "closed_positions": closed,
                        "failed_positions": failed,
                        "mode": "PAPER"
                    }

                # -------------------------------------------------
                # CE / PE / N/A = Close specific BUY
                # -------------------------------------------------

                success, result = self.paper_trader.sell(
                    current_price,
                    exit_reason="SIGNAL_SELL",
                    symbol=symbol,
                    option_mode=option_mode
                )

                if not success:
                    return False, result

                self.active_position = None

                key = self._position_key(symbol, option_mode)

                self.last_signals[key] = "SELL"
                self.last_signal = "SELL"

                logging.info(
                    f"🔴 BUY position exited | "
                    f"Symbol={symbol} | "
                    f"Option={option_mode} | "
                    f"Reason=SIGNAL_SELL"
                )

                return True, {
                    "action": "SELL",
                    "type": "EXIT_ONLY",
                    "symbol": symbol,
                    "option_mode": option_mode,
                    "exit_price": current_price,
                    "result": result,
                    "mode": "PAPER"
                }

            # =================================================
            # BUY
            # =================================================

            if signal == "BUY":

                # -------------------------------------------------
                # ALL MODE
                # -------------------------------------------------

                if option_mode == "ALL":

                    if not isinstance(price_by_option, dict):
                        return False, (
                            "❌ ALL mode requires separate "
                            "CE and PE prices."
                        )

                    results = []

                    # ---------------------------------------------
                    # CE
                    # ---------------------------------------------

                    if "CE" in price_by_option:

                        try:
                            ce_price = float(price_by_option["CE"])
                        except Exception:
                            ce_price = 0

                        if ce_price > 0:

                            success, result = self._buy_option(
                                symbol=symbol,
                                option_mode="CE",
                                current_price=ce_price,
                                capital=capital,
                                lots=lots,
                                lot_size=lot_size,
                                selected_strategy=selected_strategy
                            )

                            results.append({
                                "option_mode": "CE",
                                "success": success,
                                "result": result
                            })

                    # ---------------------------------------------
                    # PE
                    # ---------------------------------------------

                    if "PE" in price_by_option:

                        try:
                            pe_price = float(price_by_option["PE"])
                        except Exception:
                            pe_price = 0

                        if pe_price > 0:

                            success, result = self._buy_option(
                                symbol=symbol,
                                option_mode="PE",
                                current_price=pe_price,
                                capital=capital,
                                lots=lots,
                                lot_size=lot_size,
                                selected_strategy=selected_strategy
                            )

                            results.append({
                                "option_mode": "PE",
                                "success": success,
                                "result": result
                            })

                    if not results:
                        return False, (
                            "❌ No valid CE/PE price available "
                            "for ALL mode."
                        )

                    self.last_signal = "BUY"

                    return True, {
                        "action": "BUY",
                        "type": "ALL",
                        "symbol": symbol,
                        "results": results,
                        "mode": "PAPER"
                    }

                # -------------------------------------------------
                # CE / PE / N/A
                # -------------------------------------------------

                return self._buy_option(
                    symbol=symbol,
                    option_mode=option_mode,
                    current_price=current_price,
                    capital=capital,
                    lots=lots,
                    lot_size=lot_size,
                    selected_strategy=selected_strategy
                )

            return False, "❌ Unknown signal"

        except Exception as e:

            logging.exception(
                "❌ TradeManager process error"
            )

            return False, f"TradeManager error: {e}"

    # =========================================================
    # BUY OPTION
    # =========================================================

    def _buy_option(
        self,
        symbol,
        option_mode,
        current_price,
        capital,
        lots,
        lot_size,
        selected_strategy
    ):

        try:

            option_mode = str(option_mode).upper()

            if option_mode not in ("CE", "PE", "N/A"):
                return False, (
                    f"❌ Invalid BUY option mode: {option_mode}"
                )

            current_price = float(current_price)

            if current_price <= 0:
                return False, "❌ Invalid option price"

            # -------------------------------------------------
            # Position key
            # -------------------------------------------------

            key = self._position_key(
                symbol,
                option_mode
            )

            # -------------------------------------------------
            # Duplicate BUY protection
            # -------------------------------------------------

            existing = self.paper_trader.get_position(
                symbol,
                option_mode
            )

            if existing is not None:
                return False, (
                    f"⚠️ {option_mode} BUY position already active."
                )

            # -------------------------------------------------
            # Stoploss
            # -------------------------------------------------
            if option_mode == "N/A":
                stoploss_price = round(
                    current_price * 0.99,
                8
                )
            else:
                stoploss_price = round(
                    current_price * 0.99,
                    2
                )

            # -------------------------------------------------
            # Risk Manager
            # -------------------------------------------------

            trade = calculate_trade_details(
                capital=capital,
                entry_price=current_price,
                stoploss_price=stoploss_price,
                lot_size=lot_size,
                reward_ratio=2.0
            )

            if not isinstance(trade, dict):
                return False, "❌ Invalid risk calculation"

            calculated_lots = int(
                trade.get("lots", 0)
            )

            if calculated_lots <= 0:
                return False, (
                    "⚠️ Risk manager says capital "
                    "is insufficient."
                )

            final_lots = min(
                lots,
                calculated_lots
            )

            if final_lots <= 0:
                return False, "❌ Invalid final lot count"

            quantity = final_lots * lot_size

            # -------------------------------------------------
            # Target
            # -------------------------------------------------

            target = float(
                trade.get("target_price", 0)
            )

            # Always ensure target is above entry
            if target <= current_price:
                target = current_price * 1.02

            # Precision based on instrument
            if option_mode == "N/A":
                target = round(target, 8)
            else:
                target = round(target, 2)

            # Final safety check
            if target <= current_price:
                return False, "❌ Invalid BUY target"

            # -------------------------------------------------
            # BUY
            # -------------------------------------------------

            success, message = self.paper_trader.buy(
                symbol=symbol,
                price=current_price,
                qty=quantity,
                target=target,
                stoploss=stoploss_price,
                trailing_enabled=self.trailing_enabled,
                trailing_start=self.trailing_start,
                trailing_distance=self.trailing_distance,
                option_mode=option_mode
            )

            if not success:
                return False, message

            # -------------------------------------------------
            # Update position metadata
            # -------------------------------------------------

            position = self.paper_trader.get_position(
                symbol,
                option_mode
            )

            if position is not None:

                position["option_mode"] = option_mode
                position["lots"] = final_lots
                position["lot_size"] = lot_size
                position["strategy"] = selected_strategy
                position["status"] = "OPEN"

            self.active_position = position

            self.last_signals[key] = "BUY"
            self.last_signal = "BUY"

            logging.info(
                f"🟢 BUY opened | "
                f"Symbol={symbol} | "
                f"Option={option_mode} | "
                f"Lots={final_lots} | "
                f"Qty={quantity} | "
                f"Entry={current_price} | "
                f"SL={stoploss_price} | "
                f"Target={target}"
            )

            return True, {
                "action": "BUY",
                "symbol": symbol,
                "option_mode": option_mode,
                "lots": final_lots,
                "lot_size": lot_size,
                "qty": quantity,
                "entry": current_price,
                "stoploss": stoploss_price,
                "target": target,
                "strategy": selected_strategy,
                "risk": trade,
                "mode": "PAPER"
            }

        except Exception as e:

            logging.exception(
                "❌ BUY option error"
            )

            return False, (
                f"BUY option error: {e}"
            )

    # =========================================================
    # GET ACTIVE POSITIONS
    # =========================================================

    def get_active_position(self):

        try:

            if self.paper_trader is None:
                return None

            positions = self.paper_trader.get_active_positions()

            if not positions:
                self.active_position = None
                return None

            # Compatibility:
            # return first position
            self.active_position = next(
                iter(positions.values())
            )

            return self.active_position

        except Exception:
            return self.active_position

    # =========================================================
    # GET ALL ACTIVE POSITIONS
    # =========================================================

    def get_active_positions(self):

        try:

            if self.paper_trader is None:
                return {}

            return self.paper_trader.get_active_positions()

        except Exception as e:

            logging.exception(
                "❌ Active positions error"
            )

            return {}

    # =========================================================
    # CHECK POSITION
    # =========================================================

    def check_position(
        self,
        current_price,
        symbol=None,
        option_mode=None,
        price_map=None
    ):

        try:

            if self.paper_trader is None:
                return False, (
                    "PaperTrader is not connected"
                )

            # -------------------------------------------------
            # Specific position
            # -------------------------------------------------

            if symbol is not None and option_mode is not None:

                symbol = str(symbol).upper()
                option_mode = str(option_mode).upper()

                position = self.paper_trader.get_position(
                    symbol,
                    option_mode
                )

                if position is None:

                    return True, {
                        "status": "NO_POSITION",
                        "symbol": symbol,
                        "option_mode": option_mode
                    }

                price = float(current_price)

                if isinstance(price_map, dict):

                    key = self._position_key(
                        symbol,
                        option_mode
                    )

                    if key in price_map:
                        price = float(
                            price_map[key]
                        )

                exit_result = (
                    self.paper_trader.auto_exit(
                        price,
                        symbol=symbol,
                        option_mode=option_mode
                    )
                )

                position = self.paper_trader.get_position(
                    symbol,
                    option_mode
                )

                if position is None:

                    self.active_position = None

                    return True, {
                        "status": "EXIT",
                        "result": exit_result
                    }

                entry = float(
                    position.get(
                        "entry",
                        price
                    )
                )

                qty = int(
                    position.get(
                        "qty",
                        0
                    )
                )

                pnl = (
                    price - entry
                ) * qty

                self.active_position = position

                return True, {
                    "status": "HOLD",
                    "symbol": symbol,
                    "option_mode": option_mode,
                    "side": "BUY",
                    "entry": entry,
                    "current_price": price,
                    "qty": qty,
                    "lots": position.get("lots", 0),
                    "lot_size": position.get("lot_size", 0),
                    "stoploss": position.get("stoploss"),
                    "target": position.get("target"),
                    "pnl": round(pnl, 2),
                    "trailing_active": position.get(
                        "trailing_active",
                        False
                    )
                }

            # -------------------------------------------------
            # ALL positions
            # -------------------------------------------------

            positions = self.paper_trader.get_active_positions()

            if not positions:

                self.active_position = None

                return True, {
                    "status": "NO_POSITION"
                }

            results = {}

            for key, position in list(positions.items()):

                position_symbol = position.get(
                    "symbol"
                )

                position_option = position.get(
                    "option_mode",
                    "N/A"
                )

                price = float(current_price)

                if isinstance(price_map, dict):

                    if key in price_map:
                        price = float(
                            price_map[key]
                        )

                result = self.check_position(
                    price,
                    symbol=position_symbol,
                    option_mode=position_option
                )

                results[key] = result[1]

            return True, {
                "status": "MULTIPLE_POSITIONS",
                "positions": results
            }

        except Exception as e:

            logging.exception(
                "❌ Position check error"
            )

            return False, (
                f"Position check error: {e}"
            )

    # =========================================================
    # CLOSE POSITION
    # =========================================================

    def close_position(
        self,
        current_price,
        reason="MANUAL",
        symbol=None,
        option_mode=None
    ):

        try:

            if self.paper_trader is None:
                return False, (
                    "PaperTrader is not connected"
                )

            if symbol is None or option_mode is None:
                return False, (
                    "❌ Symbol and option mode "
                    "are required to close a position."
                )

            success, result = self.paper_trader.sell(
                float(current_price),
                exit_reason=reason,
                symbol=str(symbol).upper(),
                option_mode=str(option_mode).upper()
            )

            if success:

                self.active_position = None

                logging.info(
                    f"🔚 BUY position closed | "
                    f"Symbol={symbol} | "
                    f"Option={option_mode} | "
                    f"Reason={reason} | "
                    f"Result={result}"
                )

            return success, result

        except Exception as e:

            logging.exception(
                "❌ Manual close error"
            )

            return False, str(e)