import csv
import os
import logging
from datetime import datetime


# =========================================================
# AI LEARNING
# =========================================================

try:
    from ai_learning import update_learning
except ImportError:

    def update_learning(strategy, symbol, result):
        return None


# =========================================================
# PAPER TRADER
# =========================================================

class PaperTrader:
    """
    Paper Trading Engine.

    Indian Options:
        CE -> BUY
        PE -> BUY
        SELL -> EXIT existing BUY

    Delta Futures:
        BUY  -> LONG
        SELL -> SHORT
        SELL on LONG  -> CLOSE LONG
        BUY  on SHORT -> CLOSE SHORT

    Supports:
        - Multiple positions
        - Target
        - Initial Stoploss
        - Trailing Stoploss
        - Automatic Target / SL / Trailing SL
        - LONG P&L
        - SHORT P&L
        - Trade history CSV

    LIVE BROKER ORDERS ARE NOT USED.
    """

    # =====================================================
    # INIT
    # =====================================================

    def __init__(self, initial_balance=100000.0):

        self.balance = float(initial_balance)

        # Multiple positions
        self.positions = {}

        # Backward compatibility
        self.position = None

    # =====================================================
    # DELTA DETECTION
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

        if s in delta_symbols:
            return True

        return (
            s.endswith("USD")
            or s.endswith("USDT")
        )

    # =====================================================
    # POSITION KEY
    # =====================================================

    def _position_key(
        self,
        symbol,
        option_mode="N/A"
    ):

        symbol = str(
            symbol
        ).strip().upper()

        option_mode = str(
            option_mode
        ).strip().upper()

        return f"{symbol}_{option_mode}"

    # =====================================================
    # SYNC OLD POSITION
    # =====================================================

    def _sync_position(self):

        if self.positions:

            self.position = next(
                iter(
                    self.positions.values()
                )
            )

        else:

            self.position = None

    # =====================================================
    # BUY
    # =====================================================

    def buy(
        self,
        symbol,
        price,
        qty,
        target,
        stoploss,
        trailing_enabled=False,
        trailing_start=10.0,
        trailing_distance=5.0,
        option_mode="N/A",
        option_contract=None
    ):
        """
        Open BUY / LONG position.

        For Indian Options:
            CE / PE BUY

        For Delta Futures:
            BUY = LONG
        """

        try:

            symbol = str(
                symbol
            ).strip().upper()

            option_mode = str(
                option_mode
            ).strip().upper()

            # -------------------------------------------------
            # Validate option mode
            # -------------------------------------------------

            if option_mode not in (
                "CE",
                "PE",
                "N/A"
            ):

                return False, (
                    "❌ Invalid option mode. "
                    "Use CE, PE or N/A."
                )

            # -------------------------------------------------
            # Convert values
            # -------------------------------------------------

            price = float(price)
            qty = int(qty)
            target = float(target)
            stoploss = float(stoploss)

            trailing_enabled = bool(
                trailing_enabled
            )

            trailing_start = float(
                trailing_start
            )

            trailing_distance = float(
                trailing_distance
            )

            # -------------------------------------------------
            # Basic validation
            # -------------------------------------------------

            if not symbol:

                return False, (
                    "❌ Invalid symbol"
                )

            if price <= 0:

                return False, (
                    "❌ Invalid entry price"
                )

            if qty <= 0:

                return False, (
                    "❌ Invalid quantity"
                )

            if target <= price:

                return False, (
                    "❌ BUY/LONG target "
                    "must be above entry"
                )

            if stoploss >= price:

                return False, (
                    "❌ BUY/LONG stoploss "
                    "must be below entry"
                )

            # -------------------------------------------------
            # Trailing validation
            # -------------------------------------------------

            if trailing_enabled:

                if trailing_start <= 0:

                    return False, (
                        "❌ Invalid trailing start"
                    )

                if trailing_distance <= 0:

                    return False, (
                        "❌ Invalid trailing distance"
                    )

                if trailing_distance >= trailing_start:

                    return False, (
                        "❌ Trailing distance should "
                        "be less than trailing start"
                    )

            # -------------------------------------------------
            # Position key
            # -------------------------------------------------

            position_key = self._position_key(
                symbol,
                option_mode
            )

            # -------------------------------------------------
            # Duplicate protection
            # -------------------------------------------------

            if position_key in self.positions:

                existing = self.positions[
                    position_key
                ]

                existing_side = existing.get(
                    "side",
                    "BUY"
                )

                return False, (
                    f"⚠️ {symbol} "
                    f"{option_mode} "
                    f"{existing_side} "
                    f"position already exists"
                )

            # -------------------------------------------------
            # Required capital
            # -------------------------------------------------

            cost = price * qty

            if cost > self.balance:

                return False, (
                    "❌ Insufficient "
                    "Paper Trading Balance"
                )

            # -------------------------------------------------
            # Deduct capital
            # -------------------------------------------------

            self.balance -= cost

            # -------------------------------------------------
            # Create LONG position
            # -------------------------------------------------

            position = {

                "symbol": symbol,

                "option_mode": option_mode,

                "option_contract": (
                    option_contract
                ),

                "side": "BUY",

                "position_side": "LONG",

                "entry": price,

                "qty": qty,

                "target": target,

                "stoploss": stoploss,

                "initial_stoploss": stoploss,

                "trailing_enabled": (
                    trailing_enabled
                ),

                "trailing_start": (
                    trailing_start
                ),

                "trailing_distance": (
                    trailing_distance
                ),

                "highest_price": price,

                "lowest_price": price,

                "trailing_active": False,

                "entry_time": datetime.now(),

                "status": "OPEN"
            }

            # -------------------------------------------------
            # Save
            # -------------------------------------------------

            self.positions[
                position_key
            ] = position

            self._sync_position()

            # -------------------------------------------------
            # Trade history
            # -------------------------------------------------

            self.save_trade(
                action="BUY",
                symbol=symbol,
                entry=price,
                exit_price="",
                qty=qty,
                target=target,
                stoploss=stoploss,
                pnl=0.0,
                side="LONG"
            )

            logging.info(
                f"🟢 PAPER LONG | "
                f"{symbol} {option_mode} | "
                f"Entry={price} | "
                f"Qty={qty} | "
                f"Target={target} | "
                f"SL={stoploss}"
            )

            return True, {

                "action": "BUY",

                "symbol": symbol,

                "option_mode": option_mode,

                "option_contract": (
                    option_contract
                ),

                "side": "BUY",

                "position_side": "LONG",

                "entry": price,

                "qty": qty,

                "target": target,

                "stoploss": stoploss,

                "trailing_enabled": (
                    trailing_enabled
                ),

                "status": "OPEN"
            }

        except Exception as e:

            logging.exception(
                "❌ Paper Buy Error"
            )

            return False, f"Error: {e}"

    # =====================================================
    # SHORT
    # =====================================================

    def short(
        self,
        symbol,
        price,
        qty,
        target,
        stoploss,
        trailing_enabled=False,
        trailing_start=10.0,
        trailing_distance=5.0,
        option_mode="N/A",
        option_contract=None
    ):
        """
        Open SHORT position.

        Intended primarily for Delta Futures.

        SHORT:
            Target < Entry
            Stoploss > Entry
        """

        try:

            symbol = str(
                symbol
            ).strip().upper()

            option_mode = str(
                option_mode
            ).strip().upper()

            # -------------------------------------------------
            # SHORT restricted to Delta Futures
            # -------------------------------------------------

            if not self.is_delta_symbol(
                symbol
            ):

                return False, (
                    "❌ SHORT is supported "
                    "only for Delta Futures"
                )

            # -------------------------------------------------
            # Option mode
            # -------------------------------------------------

            if option_mode != "N/A":

                return False, (
                    "❌ Delta Futures SHORT "
                    "must use option_mode=N/A"
                )

            # -------------------------------------------------
            # Convert
            # -------------------------------------------------

            price = float(price)
            qty = int(qty)
            target = float(target)
            stoploss = float(stoploss)

            trailing_enabled = bool(
                trailing_enabled
            )

            trailing_start = float(
                trailing_start
            )

            trailing_distance = float(
                trailing_distance
            )

            # -------------------------------------------------
            # Validate
            # -------------------------------------------------

            if not symbol:

                return False, (
                    "❌ Invalid symbol"
                )

            if price <= 0:

                return False, (
                    "❌ Invalid short entry price"
                )

            if qty <= 0:

                return False, (
                    "❌ Invalid quantity"
                )

            if target >= price:

                return False, (
                    "❌ SHORT target "
                    "must be below entry"
                )

            if stoploss <= price:

                return False, (
                    "❌ SHORT stoploss "
                    "must be above entry"
                )

            # -------------------------------------------------
            # Trailing validation
            # -------------------------------------------------

            if trailing_enabled:

                if trailing_start <= 0:

                    return False, (
                        "❌ Invalid trailing start"
                    )

                if trailing_distance <= 0:

                    return False, (
                        "❌ Invalid trailing distance"
                    )

                if trailing_distance >= trailing_start:

                    return False, (
                        "❌ Trailing distance should "
                        "be less than trailing start"
                    )

            # -------------------------------------------------
            # Position key
            # -------------------------------------------------

            position_key = self._position_key(
                symbol,
                "N/A"
            )

            # -------------------------------------------------
            # Duplicate
            # -------------------------------------------------

            if position_key in self.positions:

                existing = self.positions[
                    position_key
                ]

                return False, (
                    f"⚠️ {symbol} "
                    f"SHORT position already exists"
                )

            # -------------------------------------------------
            # Margin / paper capital
            # -------------------------------------------------

            margin = price * qty

            if margin > self.balance:

                return False, (
                    "❌ Insufficient "
                    "Paper Trading Balance"
                )

            # -------------------------------------------------
            # Reserve margin
            # -------------------------------------------------

            self.balance -= margin

            # -------------------------------------------------
            # Create SHORT
            # -------------------------------------------------

            position = {

                "symbol": symbol,

                "option_mode": "N/A",

                "option_contract": (
                    option_contract
                ),

                "side": "SELL",

                "position_side": "SHORT",

                "entry": price,

                "qty": qty,

                "target": target,

                "stoploss": stoploss,

                "initial_stoploss": stoploss,

                "trailing_enabled": (
                    trailing_enabled
                ),

                "trailing_start": (
                    trailing_start
                ),

                "trailing_distance": (
                    trailing_distance
                ),

                "highest_price": price,

                "lowest_price": price,

                "trailing_active": False,

                "entry_time": datetime.now(),

                "status": "OPEN"
            }

            # -------------------------------------------------
            # Save
            # -------------------------------------------------

            self.positions[
                position_key
            ] = position

            self._sync_position()

            # -------------------------------------------------
            # History
            # -------------------------------------------------

            self.save_trade(
                action="SHORT",
                symbol=symbol,
                entry=price,
                exit_price="",
                qty=qty,
                target=target,
                stoploss=stoploss,
                pnl=0.0,
                side="SHORT"
            )

            logging.info(
                f"🔴 PAPER SHORT | "
                f"{symbol} | "
                f"Entry={price} | "
                f"Qty={qty} | "
                f"Target={target} | "
                f"SL={stoploss}"
            )

            return True, {

                "action": "SHORT",

                "symbol": symbol,

                "option_mode": "N/A",

                "side": "SELL",

                "position_side": "SHORT",

                "entry": price,

                "qty": qty,

                "target": target,

                "stoploss": stoploss,

                "trailing_enabled": (
                    trailing_enabled
                ),

                "status": "OPEN"
            }

        except Exception as e:

            logging.exception(
                "❌ Paper Short Error"
            )

            return False, f"Error: {e}"

    # =====================================================
    # TRAILING STOPLOSS
    # =====================================================

    def update_trailing_stop(
        self,
        current_price,
        symbol=None,
        option_mode=None
    ):
        """
        LONG:
            Highest price tracked.
            SL moves upward.

        SHORT:
            Lowest price tracked.
            SL moves downward.
        """

        try:

            current_price = float(
                current_price
            )

            if current_price <= 0:

                return None

            # -------------------------------------------------
            # Find position
            # -------------------------------------------------

            if symbol is not None:

                position_key = self._position_key(
                    symbol,
                    option_mode or "N/A"
                )

                position = self.positions.get(
                    position_key
                )

            else:

                position = self.position

            if position is None:

                return None

            side = position.get(
                "position_side",
                "LONG"
            )

            entry = float(
                position["entry"]
            )

            trailing_enabled = bool(
                position.get(
                    "trailing_enabled",
                    False
                )
            )

            if not trailing_enabled:

                return None

            trailing_start = float(
                position.get(
                    "trailing_start",
                    10.0
                )
            )

            trailing_distance = float(
                position.get(
                    "trailing_distance",
                    5.0
                )
            )

            # =================================================
            # LONG TRAILING
            # =================================================

            if side == "LONG":

                highest_price = float(
                    position.get(
                        "highest_price",
                        entry
                    )
                )

                if current_price > highest_price:

                    highest_price = current_price

                    position[
                        "highest_price"
                    ] = highest_price

                profit_points = (
                    highest_price - entry
                )

                if profit_points >= trailing_start:

                    position[
                        "trailing_active"
                    ] = True

                    new_stoploss = round(
                        highest_price
                        - trailing_distance,
                        8
                    )

                    old_stoploss = float(
                        position["stoploss"]
                    )

                    if new_stoploss > old_stoploss:

                        position[
                            "stoploss"
                        ] = new_stoploss

                        logging.info(
                            f"📈 LONG TRAILING SL | "
                            f"{position['symbol']} | "
                            f"Old={old_stoploss} | "
                            f"New={new_stoploss}"
                        )

                        return new_stoploss

            # =================================================
            # SHORT TRAILING
            # =================================================

            elif side == "SHORT":

                lowest_price = float(
                    position.get(
                        "lowest_price",
                        entry
                    )
                )

                if current_price < lowest_price:

                    lowest_price = current_price

                    position[
                        "lowest_price"
                    ] = lowest_price

                profit_points = (
                    entry - lowest_price
                )

                if profit_points >= trailing_start:

                    position[
                        "trailing_active"
                    ] = True

                    new_stoploss = round(
                        lowest_price
                        + trailing_distance,
                        8
                    )

                    old_stoploss = float(
                        position["stoploss"]
                    )

                    # SHORT SL only moves DOWN
                    if new_stoploss < old_stoploss:

                        position[
                            "stoploss"
                        ] = new_stoploss

                        logging.info(
                            f"📉 SHORT TRAILING SL | "
                            f"{position['symbol']} | "
                            f"Old={old_stoploss} | "
                            f"New={new_stoploss}"
                        )

                        return new_stoploss

        except Exception as e:

            logging.exception(
                f"❌ Trailing Stop Error: {e}"
            )

        return None

    # =====================================================
    # SELL / EXIT
    # =====================================================

    def sell(
        self,
        current_price,
        exit_reason="MANUAL",
        symbol=None,
        option_mode=None
    ):
        """
        SELL closes an existing BUY/LONG position.

        For SHORT position:
            use cover_short().
        """

        try:

            current_price = float(
                current_price
            )

            if current_price <= 0:

                return False, (
                    "❌ Invalid exit price"
                )

            # -------------------------------------------------
            # Find
            # -------------------------------------------------

            if symbol is not None:

                position_key = self._position_key(
                    symbol,
                    option_mode or "N/A"
                )

                position = self.positions.get(
                    position_key
                )

            else:

                if self.position is None:

                    return False, (
                        "❌ No Active Position Found"
                    )

                position = self.position

                position_key = self._position_key(
                    position.get("symbol"),
                    position.get(
                        "option_mode",
                        "N/A"
                    )
                )

            if position is None:

                return False, (
                    "❌ No Active BUY/LONG "
                    "Position Found"
                )

            # -------------------------------------------------
            # Only LONG
            # -------------------------------------------------

            side = position.get(
                "position_side",
                "LONG"
            )

            if side != "LONG":

                return False, (
                    "❌ This is a SHORT position. "
                    "Use cover_short()."
                )

            # -------------------------------------------------
            # Data
            # -------------------------------------------------

            symbol = position["symbol"]

            option_mode = position.get(
                "option_mode",
                "N/A"
            )

            entry = float(
                position["entry"]
            )

            qty = int(
                position["qty"]
            )

            target = float(
                position["target"]
            )

            stoploss = float(
                position["stoploss"]
            )

            # -------------------------------------------------
            # LONG P&L
            # -------------------------------------------------

            pnl = round(
                (
                    current_price
                    - entry
                ) * qty,
                2
            )

            invested_capital = (
                entry * qty
            )

            # Return capital + P&L
            self.balance += (
                invested_capital
                + pnl
            )

            # -------------------------------------------------
            # Save
            # -------------------------------------------------

            self.save_trade(
                action="SELL",
                symbol=symbol,
                entry=entry,
                exit_price=current_price,
                qty=qty,
                target=target,
                stoploss=stoploss,
                pnl=pnl,
                side="LONG"
            )

            # -------------------------------------------------
            # Remove
            # -------------------------------------------------

            if position_key in self.positions:

                del self.positions[
                    position_key
                ]

            self._sync_position()

            # -------------------------------------------------
            # Learning
            # -------------------------------------------------

            result_type = (
                "WIN"
                if pnl >= 0
                else "LOSS"
            )

            try:

                update_learning(
                    "AI Combo",
                    symbol,
                    result_type
                )

            except Exception:
                pass

            logging.info(
                f"🔚 PAPER LONG EXIT | "
                f"{symbol} | "
                f"Reason={exit_reason} | "
                f"Entry={entry} | "
                f"Exit={current_price} | "
                f"Qty={qty} | "
                f"PNL={pnl}"
            )

            return True, pnl

        except Exception as e:

            logging.exception(
                "❌ Paper Long Exit Error"
            )

            return False, str(e)

    # =====================================================
    # COVER SHORT
    # =====================================================

    def cover_short(
        self,
        current_price,
        exit_reason="MANUAL",
        symbol=None,
        option_mode=None
    ):
        """
        Close an existing SHORT position.

        SHORT P&L:

            (Entry - Exit) * Qty
        """

        try:

            current_price = float(
                current_price
            )

            if current_price <= 0:

                return False, (
                    "❌ Invalid cover price"
                )

            # -------------------------------------------------
            # Find
            # -------------------------------------------------

            if symbol is not None:

                position_key = self._position_key(
                    symbol,
                    option_mode or "N/A"
                )

                position = self.positions.get(
                    position_key
                )

            else:

                if self.position is None:

                    return False, (
                        "❌ No Active SHORT "
                        "Position Found"
                    )

                position = self.position

                position_key = self._position_key(
                    position.get("symbol"),
                    position.get(
                        "option_mode",
                        "N/A"
                    )
                )

            if position is None:

                return False, (
                    "❌ No Active SHORT "
                    "Position Found"
                )

            # -------------------------------------------------
            # SHORT only
            # -------------------------------------------------

            side = position.get(
                "position_side",
                "LONG"
            )

            if side != "SHORT":

                return False, (
                    "❌ Position is not SHORT"
                )

            # -------------------------------------------------
            # Data
            # -------------------------------------------------

            symbol = position["symbol"]

            option_mode = position.get(
                "option_mode",
                "N/A"
            )

            entry = float(
                position["entry"]
            )

            qty = int(
                position["qty"]
            )

            target = float(
                position["target"]
            )

            stoploss = float(
                position["stoploss"]
            )

            # -------------------------------------------------
            # SHORT P&L
            # -------------------------------------------------

            pnl = round(
                (
                    entry
                    - current_price
                ) * qty,
                2
            )

            margin = (
                entry * qty
            )

            # Return margin + P&L
            self.balance += (
                margin
                + pnl
            )

            # -------------------------------------------------
            # Save
            # -------------------------------------------------

            self.save_trade(
                action="COVER",
                symbol=symbol,
                entry=entry,
                exit_price=current_price,
                qty=qty,
                target=target,
                stoploss=stoploss,
                pnl=pnl,
                side="SHORT"
            )

            # -------------------------------------------------
            # Remove
            # -------------------------------------------------

            if position_key in self.positions:

                del self.positions[
                    position_key
                ]

            self._sync_position()

            # -------------------------------------------------
            # Learning
            # -------------------------------------------------

            result_type = (
                "WIN"
                if pnl >= 0
                else "LOSS"
            )

            try:

                update_learning(
                    "AI Combo",
                    symbol,
                    result_type
                )

            except Exception:
                pass

            logging.info(
                f"🔚 PAPER SHORT COVER | "
                f"{symbol} | "
                f"Reason={exit_reason} | "
                f"Entry={entry} | "
                f"Exit={current_price} | "
                f"Qty={qty} | "
                f"PNL={pnl}"
            )

            return True, pnl

        except Exception as e:

            logging.exception(
                "❌ Paper Short Cover Error"
            )

            return False, str(e)

    # =====================================================
    # AUTO EXIT
    # =====================================================

    def auto_exit(
        self,
        current_price,
        symbol=None,
        option_mode=None
    ):
        """
        Automatically checks Target / SL
        for LONG and SHORT.
        """

        try:

            current_price = float(
                current_price
            )

            if current_price <= 0:

                return None

            # -------------------------------------------------
            # Find
            # -------------------------------------------------

            if symbol is not None:

                position_key = self._position_key(
                    symbol,
                    option_mode or "N/A"
                )

                position = self.positions.get(
                    position_key
                )

            else:

                position = self.position

                if position is not None:

                    position_key = self._position_key(
                        position.get("symbol"),
                        position.get(
                            "option_mode",
                            "N/A"
                        )
                    )

                else:

                    position_key = None

            if position is None:

                return None

            symbol = position["symbol"]

            option_mode = position.get(
                "option_mode",
                "N/A"
            )

            side = position.get(
                "position_side",
                "LONG"
            )

            target = float(
                position["target"]
            )

            # -------------------------------------------------
            # Update trailing
            # -------------------------------------------------

            self.update_trailing_stop(
                current_price,
                symbol,
                option_mode
            )

            position = self.positions.get(
                position_key
            )

            if position is None:

                return None

            stoploss = float(
                position["stoploss"]
            )

            trailing_active = bool(
                position.get(
                    "trailing_active",
                    False
                )
            )

            # =================================================
            # LONG
            # =================================================

            if side == "LONG":

                # TARGET
                if current_price >= target:

                    success, result = self.sell(
                        current_price,
                        exit_reason="TARGET",
                        symbol=symbol,
                        option_mode=option_mode
                    )

                    if success:

                        return {

                            "status": "EXIT",

                            "reason": "TARGET",

                            "message": (
                                "🎯 LONG Target Hit"
                            ),

                            "symbol": symbol,

                            "option_mode": option_mode,

                            "side": "LONG",

                            "pnl": result
                        }

                # STOPLOSS
                if current_price <= stoploss:

                    reason = (
                        "TRAILING_STOPLOSS"
                        if trailing_active
                        else "STOPLOSS"
                    )

                    success, result = self.sell(
                        current_price,
                        exit_reason=reason,
                        symbol=symbol,
                        option_mode=option_mode
                    )

                    if success:

                        message = (
                            "🔒 LONG Trailing Stoploss Hit"
                            if trailing_active
                            else "🛑 LONG Stoploss Hit"
                        )

                        return {

                            "status": "EXIT",

                            "reason": reason,

                            "message": message,

                            "symbol": symbol,

                            "option_mode": option_mode,

                            "side": "LONG",

                            "pnl": result
                        }

            # =================================================
            # SHORT
            # =================================================

            elif side == "SHORT":

                # TARGET BELOW ENTRY
                if current_price <= target:

                    success, result = (
                        self.cover_short(
                            current_price,
                            exit_reason="TARGET",
                            symbol=symbol,
                            option_mode=option_mode
                        )
                    )

                    if success:

                        return {

                            "status": "EXIT",

                            "reason": "TARGET",

                            "message": (
                                "🎯 SHORT Target Hit"
                            ),

                            "symbol": symbol,

                            "option_mode": option_mode,

                            "side": "SHORT",

                            "pnl": result
                        }

                # STOPLOSS ABOVE ENTRY
                if current_price >= stoploss:

                    reason = (
                        "TRAILING_STOPLOSS"
                        if trailing_active
                        else "STOPLOSS"
                    )

                    success, result = (
                        self.cover_short(
                            current_price,
                            exit_reason=reason,
                            symbol=symbol,
                            option_mode=option_mode
                        )
                    )

                    if success:

                        message = (
                            "🔒 SHORT Trailing Stoploss Hit"
                            if trailing_active
                            else "🛑 SHORT Stoploss Hit"
                        )

                        return {

                            "status": "EXIT",

                            "reason": reason,

                            "message": message,

                            "symbol": symbol,

                            "option_mode": option_mode,

                            "side": "SHORT",

                            "pnl": result
                        }

        except Exception as e:

            logging.exception(
                f"❌ Auto Exit Error: {e}"
            )

        return None

    # =====================================================
    # AUTO EXIT ALL
    # =====================================================

    def auto_exit_all(
        self,
        price_map
    ):

        results = []

        try:

            for position_key in list(
                self.positions.keys()
            ):

                position = self.positions.get(
                    position_key
                )

                if position is None:
                    continue

                price = price_map.get(
                    position_key
                )

                if price is None:
                    continue

                result = self.auto_exit(
                    price,
                    symbol=position["symbol"],
                    option_mode=position.get(
                        "option_mode",
                        "N/A"
                    )
                )

                if result is not None:

                    results.append(result)

        except Exception as e:

            logging.exception(
                f"❌ Auto Exit All Error: {e}"
            )

        return results

    # =====================================================
    # MARKET CLOSE AUTO EXIT
    # =====================================================

    def market_close_auto_exit(
        self,
        price_map=None
    ):
        """
        Force close remaining positions.

        Dashboard already calls this only for
        Indian market close.

        Supports both LONG and SHORT safely.
        """

        closed = []
        failed = []

        try:

            positions = self.get_active_positions()

            if not positions:

                return {

                    "status": "NO_POSITION",

                    "closed": [],

                    "failed": []
                }

            for position_key, position in list(
                positions.items()
            ):

                if position is None:
                    continue

                symbol = str(
                    position.get(
                        "symbol",
                        ""
                    )
                ).upper()

                option_mode = str(
                    position.get(
                        "option_mode",
                        "N/A"
                    )
                ).upper()

                side = position.get(
                    "position_side",
                    "LONG"
                )

                exit_price = None

                if isinstance(
                    price_map,
                    dict
                ):

                    exit_price = price_map.get(
                        position_key
                    )

                if exit_price is None:

                    failed.append({

                        "position_key":
                            position_key,

                        "symbol":
                            symbol,

                        "option_mode":
                            option_mode,

                        "reason":
                            "Latest price not available"
                    })

                    continue

                try:

                    exit_price = float(
                        exit_price
                    )

                except Exception:

                    failed.append({

                        "position_key":
                            position_key,

                        "symbol":
                            symbol,

                        "option_mode":
                            option_mode,

                        "reason":
                            "Invalid exit price"
                    })

                    continue

                if exit_price <= 0:

                    failed.append({

                        "position_key":
                            position_key,

                        "symbol":
                            symbol,

                        "option_mode":
                            option_mode,

                        "reason":
                            "Exit price <= 0"
                    })

                    continue

                # -------------------------------------------------
                # LONG
                # -------------------------------------------------

                if side == "LONG":

                    success, result = self.sell(
                        exit_price,
                        exit_reason="MARKET_CLOSE",
                        symbol=symbol,
                        option_mode=option_mode
                    )

                # -------------------------------------------------
                # SHORT
                # -------------------------------------------------

                else:

                    success, result = (
                        self.cover_short(
                            exit_price,
                            exit_reason="MARKET_CLOSE",
                            symbol=symbol,
                            option_mode=option_mode
                        )
                    )

                if success:

                    closed.append({

                        "position_key":
                            position_key,

                        "symbol":
                            symbol,

                        "option_mode":
                            option_mode,

                        "side":
                            side,

                        "exit_price":
                            exit_price,

                        "result":
                            result
                    })

                else:

                    failed.append({

                        "position_key":
                            position_key,

                        "symbol":
                            symbol,

                        "option_mode":
                            option_mode,

                        "side":
                            side,

                        "reason":
                            result
                    })

            return {

                "status":
                    "MARKET_CLOSE",

                "closed":
                    closed,

                "failed":
                    failed,

                "count":
                    len(closed)
            }

        except Exception as e:

            logging.exception(
                f"❌ Market Close Exit Error: {e}"
            )

            return {

                "status":
                    "ERROR",

                "closed":
                    closed,

                "failed":
                    failed,

                "message":
                    str(e)
            }

    # =====================================================
    # ACTIVE POSITIONS
    # =====================================================

    def get_active_positions(self):

        return dict(
            self.positions
        )

    # =====================================================
    # GET POSITION
    # =====================================================

    def get_position(
        self,
        symbol,
        option_mode="N/A"
    ):

        key = self._position_key(
            symbol,
            option_mode
        )

        return self.positions.get(
            key
        )

    # =====================================================
    # POSITION STATUS
    # =====================================================

    def get_position_status(
        self,
        symbol=None,
        option_mode=None
    ):

        # Specific
        if symbol is not None:

            position = self.get_position(
                symbol,
                option_mode or "N/A"
            )

            if position is None:

                return None

            return self._format_position_status(
                position
            )

        # All
        if not self.positions:

            return None

        return {

            key:
                self._format_position_status(
                    position
                )

            for key, position
            in self.positions.items()
        }

    # =====================================================
    # FORMAT POSITION
    # =====================================================

    def _format_position_status(
        self,
        position
    ):

        side = position.get(
            "position_side",
            "LONG"
        )

        return {

            "symbol":
                position.get("symbol"),

            "option_mode":
                position.get(
                    "option_mode",
                    "N/A"
                ),

            "side":
                position.get(
                    "side",
                    "BUY"
                ),

            "position_side":
                side,

            "entry":
                position.get("entry"),

            "current_stoploss":
                position.get("stoploss"),

            "initial_stoploss":
                position.get(
                    "initial_stoploss"
                ),

            "target":
                position.get("target"),

            "qty":
                position.get("qty"),

            "trailing_enabled":
                position.get(
                    "trailing_enabled",
                    False
                ),

            "trailing_active":
                position.get(
                    "trailing_active",
                    False
                ),

            "trailing_start":
                position.get(
                    "trailing_start",
                    0
                ),

            "trailing_distance":
                position.get(
                    "trailing_distance",
                    0
                ),

            "highest_price":
                position.get(
                    "highest_price"
                ),

            "lowest_price":
                position.get(
                    "lowest_price"
                ),

            "status":
                position.get(
                    "status",
                    "OPEN"
                )
        }

    # =====================================================
    # BALANCE
    # =====================================================

    def get_balance(self):

        return round(
            self.balance,
            2
        )

    # =====================================================
    # OPEN P&L
    # =====================================================

    def get_open_pnl(
        self,
        price_map
    ):

        total_pnl = 0.0

        try:

            for key, position in (
                self.positions.items()
            ):

                current_price = price_map.get(
                    key
                )

                if current_price is None:
                    continue

                entry = float(
                    position["entry"]
                )

                qty = int(
                    position["qty"]
                )

                current_price = float(
                    current_price
                )

                side = position.get(
                    "position_side",
                    "LONG"
                )

                # LONG
                if side == "LONG":

                    pnl = (
                        current_price
                        - entry
                    ) * qty

                # SHORT
                else:

                    pnl = (
                        entry
                        - current_price
                    ) * qty

                total_pnl += pnl

        except Exception as e:

            logging.exception(
                f"❌ Open P&L Error: {e}"
            )

        return round(
            total_pnl,
            2
        )

    # =====================================================
    # SAVE TRADE
    # =====================================================

    def save_trade(
        self,
        action,
        symbol,
        entry,
        exit_price,
        qty,
        target,
        stoploss,
        pnl,
        side=None
    ):
        """
        Save trade into trade_history.csv.

        Compatible with old calls.
        """

        try:

            file_path = (
                "trade_history.csv"
            )

            file_exists = os.path.exists(
                file_path
            )

            is_empty = (
                not file_exists
                or os.path.getsize(
                    file_path
                ) == 0
            )

            with open(
                file_path,
                "a",
                newline="",
                encoding="utf-8"
            ) as f:

                writer = csv.writer(f)

                if is_empty:

                    writer.writerow([

                        "Date",
                        "Action",
                        "Symbol",
                        "Side",
                        "Entry",
                        "Exit",
                        "Qty",
                        "Target",
                        "Stoploss",
                        "PNL"
                    ])

                writer.writerow([

                    datetime.now().strftime(
                        "%Y-%m-%d %H:%M:%S"
                    ),

                    action,

                    symbol,

                    side or "",

                    entry,

                    exit_price,

                    qty,

                    target,

                    stoploss,

                    pnl
                ])

        except Exception as e:

            logging.error(
                f"❌ Failed to save "
                f"trade history: {e}"
            )


# =========================================================
# CHECK EXIT
# =========================================================

def check_exit(
    entry,
    current,
    action="BUY",
    target_points=40,
    stoploss_points=20
):
    """
    BUY / LONG:
        TARGET above entry
        STOPLOSS below entry

    SELL / SHORT:
        TARGET below entry
        STOPLOSS above entry
    """

    try:

        entry = float(entry)

        current = float(current)

        target_points = float(
            target_points
        )

        stoploss_points = float(
            stoploss_points
        )

        action = str(
            action
        ).upper()

        # =================================================
        # BUY / LONG
        # =================================================

        if action in (
            "BUY",
            "LONG"
        ):

            if current >= (
                entry + target_points
            ):

                return "TARGET"

            if current <= (
                entry - stoploss_points
            ):

                return "STOPLOSS"

        # =================================================
        # SELL / SHORT
        # =================================================

        elif action in (
            "SELL",
            "SHORT"
        ):

            if current <= (
                entry - target_points
            ):

                return "TARGET"

            if current >= (
                entry + stoploss_points
            ):

                return "STOPLOSS"

    except Exception:

        pass

    return None