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
# PAPER TRADER - BUYER ONLY
# =========================================================

class PaperTrader:
    """
    Buyer-Only Paper Trading Engine.

    Supports:
    - CE BUY
    - PE BUY
    - Multiple option positions
    - SELL = EXIT existing BUY only
    - Target
    - Initial Stoploss
    - Trailing Stoploss
    - Automatic Target / SL / Trailing SL Exit
    - P&L calculation
    - Trade history CSV

    SHORT SELLING IS NOT SUPPORTED.
    LIVE BROKER ORDERS ARE NOT USED.
    """

    def __init__(self, initial_balance=100000.0):

        self.balance = float(initial_balance)

        # =====================================================
        # Multiple Positions
        # =====================================================

        self.positions = {}

        # Backward compatibility
        self.position = None

    # =========================================================
    # POSITION KEY
    # =========================================================

    def _position_key(self, symbol, option_mode="N/A"):

        symbol = str(symbol).strip().upper()
        option_mode = str(option_mode).strip().upper()

        return f"{symbol}_{option_mode}"

    # =========================================================
    # SYNC OLD self.position
    # =========================================================

    def _sync_position(self):

        if self.positions:
            self.position = next(
                iter(self.positions.values())
            )
        else:
            self.position = None

    # =========================================================
    # BUY
    # =========================================================

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
        option_mode="N/A"
    ):
        """
        Open BUY position.

        CE / PE only.
        """

        try:

            symbol = str(symbol).strip().upper()
            option_mode = str(option_mode).strip().upper()

            # -------------------------------------------------
            # Validate option
            # -------------------------------------------------

            if option_mode not in ("CE", "PE", "N/A"):

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
                        "❌ Trailing distance should be "
                        "less than trailing start"
                    )

            # -------------------------------------------------
            # Position key
            # -------------------------------------------------

            position_key = self._position_key(
                symbol,
                option_mode
            )

            # -------------------------------------------------
            # Duplicate CE / PE protection
            # -------------------------------------------------

            if position_key in self.positions:

                return False, (
                    f"⚠️ {symbol} {option_mode} "
                    f"BUY position already exists"
                )

            # -------------------------------------------------
            # Required capital
            # -------------------------------------------------

            cost = price * qty

            if cost > self.balance:

                return False, (
                    "❌ Insufficient Paper Trading Balance"
                )

            # -------------------------------------------------
            # Deduct capital
            # -------------------------------------------------

            self.balance -= cost

            # -------------------------------------------------
            # Create position
            # -------------------------------------------------

            position = {

                "symbol": symbol,

                "option_mode": option_mode,

                "side": "BUY",

                "entry": price,

                "qty": qty,

                "target": target,

                # Current active SL
                "stoploss": stoploss,

                # Original SL
                "initial_stoploss": stoploss,

                # Trailing settings
                "trailing_enabled": trailing_enabled,

                "trailing_start": trailing_start,

                "trailing_distance": trailing_distance,

                # Price tracking
                "highest_price": price,

                # Compatibility
                "lowest_price": price,

                # Trailing status
                "trailing_active": False,

                "entry_time": datetime.now(),

                "status": "OPEN"
            }

            # -------------------------------------------------
            # Save position
            # -------------------------------------------------

            self.positions[position_key] = position

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
                pnl=0.0
            )

            logging.info(
                f"🟢 PAPER BUY | "
                f"{symbol} {option_mode} | "
                f"Entry={price} | "
                f"Qty={qty} | "
                f"Target={target} | "
                f"SL={stoploss} | "
                f"Trailing={trailing_enabled}"
            )

            return True, {
                "action": "BUY",
                "symbol": symbol,
                "option_mode": option_mode,
                "side": "BUY",
                "entry": price,
                "qty": qty,
                "target": target,
                "stoploss": stoploss,
                "trailing_enabled": trailing_enabled,
                "status": "OPEN"
            }

        except Exception as e:

            logging.exception(
                "❌ Paper Buy Error"
            )

            return False, f"Error: {e}"

    # =========================================================
    # NO SHORT FUNCTION
    # =========================================================

    # IMPORTANT:
    # short() intentionally removed.
    #
    # This system is BUYER ONLY.
    #
    # SELL means EXIT existing BUY position.
    # =========================================================

    # =========================================================
    # TRAILING STOPLOSS
    # =========================================================

    def update_trailing_stop(
        self,
        current_price,
        symbol=None,
        option_mode=None
    ):
        """
        BUY-only trailing stoploss.

        Highest price is tracked.

        When profit >= trailing_start:

            New SL =
            Highest Price - Trailing Distance

        SL only moves upward.
        """

        try:

            current_price = float(current_price)

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

            # -------------------------------------------------
            # BUY only
            # -------------------------------------------------

            if position.get("side") != "BUY":
                return None

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

            # -------------------------------------------------
            # Highest price
            # -------------------------------------------------

            highest_price = float(
                position.get(
                    "highest_price",
                    entry
                )
            )

            if current_price > highest_price:

                highest_price = current_price

                position["highest_price"] = (
                    highest_price
                )

            # -------------------------------------------------
            # Profit
            # -------------------------------------------------

            profit_points = (
                highest_price - entry
            )

            # -------------------------------------------------
            # Activate trailing
            # -------------------------------------------------

            if profit_points >= trailing_start:

                position["trailing_active"] = True

                new_stoploss = round(
                    highest_price -
                    trailing_distance,
                    2
                )

                old_stoploss = float(
                    position["stoploss"]
                )

                # SL only moves UP
                if new_stoploss > old_stoploss:

                    position["stoploss"] = (
                        new_stoploss
                    )

                    logging.info(
                        f"📈 TRAILING SL MOVED | "
                        f"{position['symbol']} "
                        f"{position.get('option_mode', 'N/A')} | "
                        f"Price={current_price} | "
                        f"Old SL={old_stoploss} | "
                        f"New SL={new_stoploss}"
                    )

                    return new_stoploss

        except Exception as e:

            logging.exception(
                f"❌ Trailing Stop Error: {e}"
            )

        return None

    # =========================================================
    # SELL = EXIT BUY ONLY
    # =========================================================

    def sell(
        self,
        current_price,
        exit_reason="MANUAL",
        symbol=None,
        option_mode=None
    ):
        """
        SELL is ONLY used to close an existing BUY position.

        No short selling.
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

                # Backward compatibility
                if self.position is None:

                    return False, (
                        "❌ No Active BUY Position Found"
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
                    "❌ No Active BUY Position Found"
                )

            # -------------------------------------------------
            # Only BUY can be closed
            # -------------------------------------------------

            if position.get("side") != "BUY":

                return False, (
                    "❌ Invalid position. "
                    "Only BUY positions are supported."
                )

            # -------------------------------------------------
            # Position data
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
            # P&L
            # -------------------------------------------------

            pnl = round(
                (current_price - entry) * qty,
                2
            )

            # -------------------------------------------------
            # Return invested capital + P&L
            # -------------------------------------------------

            invested_capital = (
                entry * qty
            )

            self.balance += (
                invested_capital + pnl
            )

            # -------------------------------------------------
            # Save trade
            # -------------------------------------------------

            self.save_trade(
                action="SELL",
                symbol=symbol,
                entry=entry,
                exit_price=current_price,
                qty=qty,
                target=target,
                stoploss=stoploss,
                pnl=pnl
            )

            # -------------------------------------------------
            # Remove position
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
                f"🔚 PAPER SELL / EXIT | "
                f"{symbol} {option_mode} | "
                f"Reason={exit_reason} | "
                f"Entry={entry} | "
                f"Exit={current_price} | "
                f"Qty={qty} | "
                f"PNL={pnl}"
            )

            return True, pnl

        except Exception as e:

            logging.exception(
                "❌ Paper Exit Error"
            )

            return False, str(e)

    # =========================================================
    # AUTO EXIT ONE POSITION
    # =========================================================

    def auto_exit(
        self,
        current_price,
        symbol=None,
        option_mode=None
    ):
        """
        Automatically checks:

        1. Target
        2. Initial / Trailing SL
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

            target = float(
                position["target"]
            )

            # -------------------------------------------------
            # Update trailing SL first
            # -------------------------------------------------

            self.update_trailing_stop(
                current_price,
                symbol,
                option_mode
            )

            # Position may have changed
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

            # -------------------------------------------------
            # TARGET
            # -------------------------------------------------

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
                        "message": "🎯 Target Hit",
                        "symbol": symbol,
                        "option_mode": option_mode,
                        "pnl": result
                    }

            # -------------------------------------------------
            # STOPLOSS
            # -------------------------------------------------

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

                    if trailing_active:

                        message = (
                            "🔒 Trailing Stoploss Hit"
                        )

                    else:

                        message = (
                            "🛑 Stoploss Hit"
                        )

                    return {
                        "status": "EXIT",
                        "reason": reason,
                        "message": message,
                        "symbol": symbol,
                        "option_mode": option_mode,
                        "pnl": result
                    }

        except Exception as e:

            logging.exception(
                f"❌ Auto Exit Error: {e}"
            )

        return None

    # =========================================================
    # AUTO EXIT ALL POSITIONS
    # =========================================================

    def auto_exit_all(
        self,
        price_map
    ):
        """
        Check all open CE / PE positions.

        Example:

        price_map = {
            "BANKNIFTY_CE": 150,
            "BANKNIFTY_PE": 120
        }
        """

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

    # =========================================================
    # GET ACTIVE POSITIONS
    # =========================================================

    def get_active_positions(self):

        return dict(
            self.positions
        )

    # =========================================================
    # GET POSITION
    # =========================================================

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

    # =========================================================
    # POSITION STATUS
    # =========================================================

    def get_position_status(
        self,
        symbol=None,
        option_mode=None
    ):

        # -----------------------------------------------------
        # Specific position
        # -----------------------------------------------------

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

        # -----------------------------------------------------
        # All positions
        # -----------------------------------------------------

        if not self.positions:
            return None

        return {
            key: self._format_position_status(
                position
            )
            for key, position
            in self.positions.items()
        }

    # =========================================================
    # FORMAT POSITION
    # =========================================================

    def _format_position_status(
        self,
        position
    ):

        return {

            "symbol": position.get(
                "symbol"
            ),

            "option_mode": position.get(
                "option_mode",
                "N/A"
            ),

            "side": "BUY",

            "entry": position.get(
                "entry"
            ),

            "current_stoploss": position.get(
                "stoploss"
            ),

            "initial_stoploss": position.get(
                "initial_stoploss"
            ),

            "target": position.get(
                "target"
            ),

            "qty": position.get(
                "qty"
            ),

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

    # =========================================================
    # BALANCE
    # =========================================================

    def get_balance(self):

        return round(
            self.balance,
            2
        )

    # =========================================================
    # TOTAL OPEN P&L
    # =========================================================

    def get_open_pnl(
        self,
        price_map
    ):

        total_pnl = 0.0

        try:

            for key, position in self.positions.items():

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

                pnl = (
                    current_price - entry
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

    # =========================================================
    # SAVE TRADE
    # =========================================================

    def save_trade(
        self,
        action,
        symbol,
        entry,
        exit_price,
        qty,
        target,
        stoploss,
        pnl
    ):
        """
        Save trade into trade_history.csv.
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
    """
    Buyer-only utility.

    SELL is treated as EXIT signal,
    not as short entry.

    Returns:
        TARGET
        STOPLOSS
        None
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

        # -----------------------------------------------------
        # BUY position exit logic
        # -----------------------------------------------------

        if current >= (
            entry + target_points
        ):

            return "TARGET"

        if current <= (
            entry - stoploss_points
        ):

            return "STOPLOSS"

    except Exception:

        pass

    return None