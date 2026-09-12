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
    Paper Trading Engine

    Indian Options:
        CE -> BUY only
        PE -> BUY only
        SELL -> EXIT existing BUY

    Delta Futures:
        BUY  -> LONG
        SELL -> SHORT
        SELL on LONG  -> CLOSE LONG
        BUY  on SHORT -> CLOSE SHORT

    No live broker orders are executed here.
    """

    # =====================================================
    # INIT
    # =====================================================

    def __init__(self, initial_balance=100000.0):

        self.balance = float(initial_balance)

        # Multiple independent positions
        self.positions = {}

        # Backward compatibility
        self.position = None

    # =====================================================
    # DELTA SYMBOL DETECTION
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

    def _position_key(self, symbol, option_mode="N/A",
                      strike=None, expiry=None):

        symbol = str(symbol or "").strip().upper()
        option_mode = str(option_mode or "N/A").strip().upper()

        # Delta / normal instrument
        if option_mode == "N/A":
            return f"{symbol}_N/A"

        # Option identity
        strike_text = ""

        if strike is not None:
            try:
                strike_text = str(int(float(strike)))
            except Exception:
                strike_text = str(strike).strip()

        expiry_text = str(expiry or "").strip().upper()

        return (
            f"{symbol}_{option_mode}_"
            f"{strike_text}_{expiry_text}"
        )

    # =====================================================
    # FIND POSITION KEY
    # =====================================================

    def _find_position_key(
        self,
        symbol,
        option_mode="N/A",
        strike=None,
        expiry=None
    ):
        """
        New exact lookup first.
        Backward compatibility with old keys is preserved.
        """

        exact_key = self._position_key(
            symbol,
            option_mode,
            strike,
            expiry
        )

        if exact_key in self.positions:
            return exact_key

        # Old format compatibility
        old_key = self._position_key(
            symbol,
            option_mode
        )

        if old_key in self.positions:
            return old_key

        # Search by metadata for older/newer positions
        symbol_u = str(symbol or "").strip().upper()
        mode_u = str(option_mode or "N/A").strip().upper()

        for key, position in self.positions.items():

            if not isinstance(position, dict):
                continue

            if str(
                position.get("symbol", "")
            ).upper() != symbol_u:
                continue

            if str(
                position.get("option_mode", "N/A")
            ).upper() != mode_u:
                continue

            if strike is not None:

                pos_strike = (
                    position.get("strike")
                    or (position.get("option_contract") or {}).get("strike")
                )

                if pos_strike is not None:

                    try:
                        if float(pos_strike) != float(strike):
                            continue
                    except Exception:
                        if str(pos_strike) != str(strike):
                            continue

            if expiry is not None:

                pos_expiry = (
                    position.get("expiry")
                    or (position.get("option_contract") or {}).get("expiry")
                )

                if str(pos_expiry or "").upper() != str(expiry).upper():
                    continue

            return key

        return None

    # =====================================================
    # SYNC OLD POSITION
    # =====================================================

    def _sync_position(self):

        if self.positions:
            self.position = next(
                iter(self.positions.values())
            )
        else:
            self.position = None

    # =====================================================
    # NORMALIZE CONTRACT
    # =====================================================

    @staticmethod
    def _normalize_contract(option_contract):

        if not isinstance(option_contract, dict):
            return option_contract

        contract = dict(option_contract)

        if contract.get("option_type"):
            contract["option_type"] = str(
                contract["option_type"]
            ).upper()

        if contract.get("exchange"):
            contract["exchange"] = str(
                contract["exchange"]
            ).upper()

        return contract

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

        try:

            symbol = str(
                symbol or ""
            ).strip().upper()

            option_mode = str(
                option_mode or "N/A"
            ).strip().upper()

            if option_mode not in (
                "CE",
                "PE",
                "N/A"
            ):
                return False, (
                    "❌ Invalid option mode. "
                    "Use CE, PE or N/A."
                )

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

            if not symbol:
                return False, "❌ Invalid symbol"

            if price <= 0:
                return False, "❌ Invalid entry price"

            if qty <= 0:
                return False, "❌ Invalid quantity"

            if target <= price:
                return False, (
                    "❌ BUY target must be above entry"
                )

            if stoploss >= price:
                return False, (
                    "❌ BUY stoploss must be below entry"
                )

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
                        "❌ Trailing distance must be "
                        "less than trailing start"
                    )

            option_contract = self._normalize_contract(
                option_contract
            )

            strike = None
            expiry = None

            if isinstance(option_contract, dict):

                strike = option_contract.get("strike")
                expiry = option_contract.get("expiry")

            position_key = self._position_key(
                symbol,
                option_mode,
                strike,
                expiry
            )

            if position_key in self.positions:

                return False, (
                    f"⚠️ {symbol} {option_mode} "
                    f"position already exists"
                )

            cost = price * qty

            if cost > self.balance:
                return False, (
                    "❌ Insufficient Paper Trading Balance"
                )

            self.balance -= cost

            position = {

                "position_key": position_key,

                "symbol": symbol,

                "option_mode": option_mode,

                "option_contract": option_contract,

                "strike": strike,

                "expiry": expiry,

                "side": "BUY",

                "position_side": "LONG",

                "entry": price,

                "current_price": price,

                "last_price": price,

                "qty": qty,

                "target": target,

                "stoploss": stoploss,

                "initial_stoploss": stoploss,

                "trailing_enabled": trailing_enabled,

                "trailing_start": trailing_start,

                "trailing_distance": trailing_distance,

                "highest_price": price,

                "lowest_price": price,

                "trailing_active": False,

                "entry_time": datetime.now(),

                "status": "OPEN"
            }

            self.positions[position_key] = position

            self._sync_position()

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
                f"🟢 PAPER BUY | "
                f"{symbol} {option_mode} | "
                f"Entry={price} | Qty={qty} | "
                f"Target={target} | SL={stoploss}"
            )

            return True, {
                "status": "success",
                "action": "BUY",
                "symbol": symbol,
                "option_mode": option_mode,
                "option_contract": option_contract,
                "strike": strike,
                "expiry": expiry,
                "side": "BUY",
                "position_side": "LONG",
                "entry": price,
                "qty": qty,
                "target": target,
                "stoploss": stoploss,
                "trailing_enabled": trailing_enabled,
                "position_key": position_key,
                "status_position": "OPEN"
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

        try:

            symbol = str(
                symbol or ""
            ).strip().upper()

            option_mode = str(
                option_mode or "N/A"
            ).strip().upper()

            if not self.is_delta_symbol(symbol):
                return False, (
                    "❌ SHORT is supported "
                    "only for Delta Futures"
                )

            if option_mode != "N/A":
                return False, (
                    "❌ Delta Futures SHORT "
                    "must use option_mode=N/A"
                )

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
                    "❌ SHORT target must be below entry"
                )

            if stoploss <= price:
                return False, (
                    "❌ SHORT stoploss must be above entry"
                )

            if trailing_enabled:

                if trailing_start <= 0:
                    return False, "❌ Invalid trailing start"

                if trailing_distance <= 0:
                    return False, "❌ Invalid trailing distance"

                if trailing_distance >= trailing_start:
                    return False, (
                        "❌ Trailing distance must be "
                        "less than trailing start"
                    )

            position_key = self._position_key(
                symbol,
                "N/A"
            )

            if position_key in self.positions:
                return False, (
                    f"⚠️ {symbol} SHORT position already exists"
                )

            margin = price * qty

            if margin > self.balance:
                return False, (
                    "❌ Insufficient Paper Trading Balance"
                )

            self.balance -= margin

            position = {

                "position_key": position_key,

                "symbol": symbol,

                "option_mode": "N/A",

                "option_contract": option_contract,

                "side": "SELL",

                "position_side": "SHORT",

                "entry": price,

                "current_price": price,

                "last_price": price,

                "qty": qty,

                "target": target,

                "stoploss": stoploss,

                "initial_stoploss": stoploss,

                "trailing_enabled": trailing_enabled,

                "trailing_start": trailing_start,

                "trailing_distance": trailing_distance,

                "highest_price": price,

                "lowest_price": price,

                "trailing_active": False,

                "entry_time": datetime.now(),

                "status": "OPEN"
            }

            self.positions[position_key] = position

            self._sync_position()

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
                f"{symbol} | Entry={price} | "
                f"Qty={qty} | Target={target} | SL={stoploss}"
            )

            return True, {
                "status": "success",
                "action": "SHORT",
                "symbol": symbol,
                "option_mode": "N/A",
                "side": "SELL",
                "position_side": "SHORT",
                "entry": price,
                "qty": qty,
                "target": target,
                "stoploss": stoploss,
                "position_key": position_key,
                "status_position": "OPEN"
            }

        except Exception as e:

            logging.exception(
                "❌ Paper Short Error"
            )

            return False, f"Error: {e}"

    # =====================================================
    # UPDATE CURRENT PRICE
    # =====================================================

    def update_position_price(
        self,
        current_price,
        symbol=None,
        option_mode=None,
        strike=None,
        expiry=None
    ):

        try:

            price = float(current_price)

            if price <= 0:
                return False

            key = self._find_position_key(
                symbol,
                option_mode or "N/A",
                strike,
                expiry
            )

            if key is None:
                return False

            position = self.positions.get(key)

            if position is None:
                return False

            position["current_price"] = price
            position["last_price"] = price

            return True

        except Exception:
            return False

    # =====================================================
    # TRAILING STOPLOSS
    # =====================================================

    def update_trailing_stop(
        self,
        current_price,
        symbol=None,
        option_mode=None,
        strike=None,
        expiry=None
    ):

        try:

            current_price = float(current_price)

            if current_price <= 0:
                return None

            if symbol is not None:

                position_key = self._find_position_key(
                    symbol,
                    option_mode or "N/A",
                    strike,
                    expiry
                )

                position = self.positions.get(
                    position_key
                )

            else:

                position = self.position
                position_key = None

            if position is None:
                return None

            position["current_price"] = current_price
            position["last_price"] = current_price

            side = position.get(
                "position_side",
                "LONG"
            )

            entry = float(
                position["entry"]
            )

            if not bool(
                position.get(
                    "trailing_enabled",
                    False
                )
            ):
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

            # -------------------------------------------------
            # LONG
            # -------------------------------------------------

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

                        return new_stoploss

            # -------------------------------------------------
            # SHORT
            # -------------------------------------------------

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

                    if new_stoploss < old_stoploss:

                        position[
                            "stoploss"
                        ] = new_stoploss

                        return new_stoploss

        except Exception as e:

            logging.exception(
                f"❌ Trailing Stop Error: {e}"
            )

        return None

    # =====================================================
    # SELL / CLOSE LONG
    # =====================================================

    def sell(
        self,
        current_price,
        exit_reason="MANUAL",
        symbol=None,
        option_mode=None,
        strike=None,
        expiry=None
    ):

        try:

            current_price = float(current_price)

            if current_price <= 0:
                return False, "❌ Invalid exit price"

            if symbol is not None:

                position_key = self._find_position_key(
                    symbol,
                    option_mode or "N/A",
                    strike,
                    expiry
                )

                position = self.positions.get(
                    position_key
                )

            else:

                position = self.position

                if position is None:
                    return False, (
                        "❌ No Active Position Found"
                    )

                position_key = position.get(
                    "position_key"
                )

                if not position_key:

                    position_key = self._find_position_key(
                        position.get("symbol"),
                        position.get(
                            "option_mode",
                            "N/A"
                        ),
                        position.get("strike"),
                        position.get("expiry")
                    )

            if position is None:
                return False, (
                    "❌ No Active BUY/LONG Position Found"
                )

            if position.get(
                "position_side",
                "LONG"
            ) != "LONG":

                return False, (
                    "❌ This is a SHORT position. "
                    "Use cover_short()."
                )

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

            pnl = round(
                (current_price - entry) * qty,
                2
            )

            invested_capital = entry * qty

            self.balance += (
                invested_capital + pnl
            )

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

            if position_key in self.positions:
                del self.positions[position_key]

            self._sync_position()

            try:

                update_learning(
                    "AI Combo",
                    symbol,
                    "WIN" if pnl >= 0 else "LOSS"
                )

            except Exception:
                pass

            logging.info(
                f"🔚 PAPER LONG EXIT | "
                f"{symbol} {option_mode} | "
                f"Reason={exit_reason} | "
                f"Entry={entry} | Exit={current_price} | "
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
        option_mode=None,
        strike=None,
        expiry=None
    ):

        try:

            current_price = float(current_price)

            if current_price <= 0:
                return False, "❌ Invalid cover price"

            if symbol is not None:

                position_key = self._find_position_key(
                    symbol,
                    option_mode or "N/A",
                    strike,
                    expiry
                )

                position = self.positions.get(
                    position_key
                )

            else:

                position = self.position

                if position is None:
                    return False, (
                        "❌ No Active SHORT Position Found"
                    )

                position_key = position.get(
                    "position_key"
                )

            if position is None:
                return False, (
                    "❌ No Active SHORT Position Found"
                )

            if position.get(
                "position_side"
            ) != "SHORT":

                return False, (
                    "❌ Position is not SHORT"
                )

            symbol = position["symbol"]

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

            pnl = round(
                (entry - current_price) * qty,
                2
            )

            margin = entry * qty

            self.balance += (
                margin + pnl
            )

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

            if position_key in self.positions:
                del self.positions[position_key]

            self._sync_position()

            try:

                update_learning(
                    "AI Combo",
                    symbol,
                    "WIN" if pnl >= 0 else "LOSS"
                )

            except Exception:
                pass

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
        option_mode=None,
        strike=None,
        expiry=None
    ):

        try:

            current_price = float(current_price)

            if current_price <= 0:
                return None

            if symbol is not None:

                position_key = self._find_position_key(
                    symbol,
                    option_mode or "N/A",
                    strike,
                    expiry
                )

                position = self.positions.get(
                    position_key
                )

            else:

                position = self.position

                if position is None:
                    return None

                position_key = position.get(
                    "position_key"
                )

            if position is None:
                return None

            symbol = position["symbol"]
            option_mode = position.get(
                "option_mode",
                "N/A"
            )

            position["current_price"] = current_price
            position["last_price"] = current_price

            side = position.get(
                "position_side",
                "LONG"
            )

            target = float(
                position["target"]
            )

            self.update_trailing_stop(
                current_price,
                symbol,
                option_mode,
                position.get("strike"),
                position.get("expiry")
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

            if side == "LONG":

                if current_price >= target:

                    success, result = self.sell(
                        current_price,
                        exit_reason="TARGET",
                        symbol=symbol,
                        option_mode=option_mode,
                        strike=position.get("strike"),
                        expiry=position.get("expiry")
                    )

                    if success:

                        return {
                            "status": "EXIT",
                            "reason": "TARGET",
                            "message": "🎯 LONG Target Hit",
                            "symbol": symbol,
                            "option_mode": option_mode,
                            "side": "LONG",
                            "pnl": result
                        }

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
                        option_mode=option_mode,
                        strike=position.get("strike"),
                        expiry=position.get("expiry")
                    )

                    if success:

                        return {
                            "status": "EXIT",
                            "reason": reason,
                            "message": (
                                "🔒 LONG Trailing Stoploss Hit"
                                if trailing_active
                                else "🛑 LONG Stoploss Hit"
                            ),
                            "symbol": symbol,
                            "option_mode": option_mode,
                            "side": "LONG",
                            "pnl": result
                        }

            elif side == "SHORT":

                if current_price <= target:

                    success, result = self.cover_short(
                        current_price,
                        exit_reason="TARGET",
                        symbol=symbol,
                        option_mode=option_mode
                    )

                    if success:

                        return {
                            "status": "EXIT",
                            "reason": "TARGET",
                            "message": "🎯 SHORT Target Hit",
                            "symbol": symbol,
                            "option_mode": option_mode,
                            "side": "SHORT",
                            "pnl": result
                        }

                if current_price >= stoploss:

                    reason = (
                        "TRAILING_STOPLOSS"
                        if trailing_active
                        else "STOPLOSS"
                    )

                    success, result = self.cover_short(
                        current_price,
                        exit_reason=reason,
                        symbol=symbol,
                        option_mode=option_mode
                    )

                    if success:

                        return {
                            "status": "EXIT",
                            "reason": reason,
                            "message": (
                                "🔒 SHORT Trailing Stoploss Hit"
                                if trailing_active
                                else "🛑 SHORT Stoploss Hit"
                            ),
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

    def auto_exit_all(self, price_map):

        results = []

        if not isinstance(price_map, dict):
            return results

        for position_key in list(
            self.positions.keys()
        ):

            position = self.positions.get(
                position_key
            )

            if not position:
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
                ),
                strike=position.get("strike"),
                expiry=position.get("expiry")
            )

            if result:
                results.append(result)

        return results

    # =====================================================
    # MARKET CLOSE
    # =====================================================

    def market_close_auto_exit(
        self,
        price_map=None
    ):

        closed = []
        failed = []

        try:

            positions = self.get_active_positions()

            if not positions:

                return {
                    "status": "NO_POSITION",
                    "closed": [],
                    "failed": [],
                    "count": 0
                }

            price_map = (
                price_map
                if isinstance(price_map, dict)
                else {}
            )

            for position_key, position in list(
                positions.items()
            ):

                if not position:
                    continue

                exit_price = price_map.get(
                    position_key
                )

                if exit_price is None:

                    failed.append({
                        "position_key": position_key,
                        "symbol": position.get("symbol"),
                        "option_mode": position.get(
                            "option_mode",
                            "N/A"
                        ),
                        "reason": "Latest price not available"
                    })

                    continue

                try:
                    exit_price = float(exit_price)
                except Exception:

                    failed.append({
                        "position_key": position_key,
                        "reason": "Invalid exit price"
                    })

                    continue

                if exit_price <= 0:

                    failed.append({
                        "position_key": position_key,
                        "reason": "Exit price <= 0"
                    })

                    continue

                symbol = position["symbol"]
                option_mode = position.get(
                    "option_mode",
                    "N/A"
                )

                side = position.get(
                    "position_side",
                    "LONG"
                )

                if side == "LONG":

                    success, result = self.sell(
                        exit_price,
                        exit_reason="MARKET_CLOSE",
                        symbol=symbol,
                        option_mode=option_mode,
                        strike=position.get("strike"),
                        expiry=position.get("expiry")
                    )

                else:

                    success, result = self.cover_short(
                        exit_price,
                        exit_reason="MARKET_CLOSE",
                        symbol=symbol,
                        option_mode=option_mode
                    )

                if success:

                    closed.append({
                        "position_key": position_key,
                        "symbol": symbol,
                        "option_mode": option_mode,
                        "side": side,
                        "exit_price": exit_price,
                        "result": result
                    })

                else:

                    failed.append({
                        "position_key": position_key,
                        "symbol": symbol,
                        "option_mode": option_mode,
                        "side": side,
                        "reason": result
                    })

            return {
                "status": "MARKET_CLOSE",
                "closed": closed,
                "failed": failed,
                "count": len(closed)
            }

        except Exception as e:

            logging.exception(
                f"❌ Market Close Exit Error: {e}"
            )

            return {
                "status": "ERROR",
                "closed": closed,
                "failed": failed,
                "message": str(e)
            }

    # =====================================================
    # ACTIVE POSITIONS
    # =====================================================

    def get_active_positions(self):
        return dict(self.positions)

    # =====================================================
    # GET POSITION
    # =====================================================

    def get_position(
        self,
        symbol,
        option_mode="N/A",
        strike=None,
        expiry=None
    ):

        key = self._find_position_key(
            symbol,
            option_mode,
            strike,
            expiry
        )

        if key is None:
            return None

        return self.positions.get(key)

    # =====================================================
    # POSITION STATUS
    # =====================================================

    def get_position_status(
        self,
        symbol=None,
        option_mode=None
    ):

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

        if not self.positions:
            return None

        return {
            key: self._format_position_status(position)
            for key, position
            in self.positions.items()
        }

    # =====================================================
    # FORMAT POSITION
    # =====================================================

    def _format_position_status(self, position):

        return {

            "position_key": position.get(
                "position_key"
            ),

            "symbol": position.get("symbol"),

            "option_mode": position.get(
                "option_mode",
                "N/A"
            ),

            "strike": position.get("strike"),

            "expiry": position.get("expiry"),

            "option_contract": position.get(
                "option_contract"
            ),

            "side": position.get(
                "side",
                "BUY"
            ),

            "position_side": position.get(
                "position_side",
                "LONG"
            ),

            "entry": position.get("entry"),

            "current_price": position.get(
                "current_price"
            ),

            "current_stoploss": position.get(
                "stoploss"
            ),

            "initial_stoploss": position.get(
                "initial_stoploss"
            ),

            "target": position.get("target"),

            "qty": position.get("qty"),

            "trailing_enabled": position.get(
                "trailing_enabled",
                False
            ),

            "trailing_active": position.get(
                "trailing_active",
                False
            ),

            "trailing_start": position.get(
                "trailing_start",
                0
            ),

            "trailing_distance": position.get(
                "trailing_distance",
                0
            ),

            "highest_price": position.get(
                "highest_price"
            ),

            "lowest_price": position.get(
                "lowest_price"
            ),

            "status": position.get(
                "status",
                "OPEN"
            )
        }

    # =====================================================
    # BALANCE
    # =====================================================

    def get_balance(self):
        return round(self.balance, 2)

    # =====================================================
    # OPEN P&L
    # =====================================================

    def get_open_pnl(self, price_map):

        total_pnl = 0.0

        if not isinstance(price_map, dict):
            return 0.0

        try:

            for key, position in self.positions.items():

                current_price = price_map.get(key)

                if current_price is None:
                    continue

                current_price = float(current_price)

                if current_price <= 0:
                    continue

                entry = float(position["entry"])
                qty = int(position["qty"])

                if position.get(
                    "position_side",
                    "LONG"
                ) == "LONG":

                    pnl = (
                        current_price - entry
                    ) * qty

                else:

                    pnl = (
                        entry - current_price
                    ) * qty

                total_pnl += pnl

        except Exception as e:

            logging.exception(
                f"❌ Open P&L Error: {e}"
            )

        return round(total_pnl, 2)

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

        try:

            file_path = "trade_history.csv"

            file_exists = os.path.exists(
                file_path
            )

            is_empty = (
                not file_exists
                or os.path.getsize(file_path) == 0
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
                f"❌ Failed to save trade history: {e}"
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

    try:

        entry = float(entry)
        current = float(current)
        target_points = float(target_points)
        stoploss_points = float(stoploss_points)

        action = str(
            action or "BUY"
        ).upper()

        if action in ("BUY", "LONG"):

            if current >= entry + target_points:
                return "TARGET"

            if current <= entry - stoploss_points:
                return "STOPLOSS"

        elif action in ("SELL", "SHORT"):

            if current <= entry - target_points:
                return "TARGET"

            if current >= entry + stoploss_points:
                return "STOPLOSS"

    except Exception:
        pass

    return None