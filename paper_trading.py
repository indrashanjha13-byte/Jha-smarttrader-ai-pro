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

    Supports:
    - BUY / LONG
    - SELL / SHORT
    - Target
    - Initial Stoploss
    - Trailing Stoploss
    - Automatic Target / SL / Trailing SL Exit
    - P&L calculation
    - Trade history CSV

    LIVE BROKER ORDERS ARE NOT USED.
    """

    def __init__(self, initial_balance=100000.0):
        self.balance = float(initial_balance)
        self.position = None

    # =====================================================
    # BUY / LONG
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
        trailing_distance=5.0
    ):
        """Open a BUY/LONG paper position."""

        try:

            if self.position is not None:
                return False, "❌ An active position already exists"

            price = float(price)
            qty = int(qty)
            target = float(target)
            stoploss = float(stoploss)

            trailing_enabled = bool(trailing_enabled)
            trailing_start = float(trailing_start)
            trailing_distance = float(trailing_distance)

            if price <= 0:
                return False, "❌ Invalid entry price"

            if qty <= 0:
                return False, "❌ Invalid quantity"

            if target <= price:
                return False, "❌ BUY target must be above entry"

            if stoploss >= price:
                return False, "❌ BUY stoploss must be below entry"

            if trailing_enabled:

                if trailing_start <= 0:
                    return False, "❌ Invalid trailing start"

                if trailing_distance <= 0:
                    return False, "❌ Invalid trailing distance"

                if trailing_distance >= trailing_start:
                    return False, (
                        "❌ Trailing distance should be "
                        "less than trailing start"
                    )

            cost = price * qty

            if cost > self.balance:
                return False, "❌ Insufficient Paper Trading Balance"

            self.balance -= cost

            self.position = {

                "symbol": symbol,
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
                "lowest_price": price,

                # Trailing status
                "trailing_active": False,

                "entry_time": datetime.now()
            }

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
                f"🟢 BUY | {symbol} | "
                f"Entry={price} | Qty={qty} | "
                f"Target={target} | SL={stoploss} | "
                f"Trailing={trailing_enabled}"
            )

            return True, "✅ BUY Order Executed Successfully"

        except Exception as e:

            logging.exception(
                "❌ Paper Buy Error"
            )

            return False, f"Error: {e}"

    # =====================================================
    # SHORT / SELL
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
        trailing_distance=5.0
    ):
        """Open a SELL/SHORT paper position."""

        try:

            if self.position is not None:
                return False, "❌ An active position already exists"

            price = float(price)
            qty = int(qty)
            target = float(target)
            stoploss = float(stoploss)

            trailing_enabled = bool(trailing_enabled)
            trailing_start = float(trailing_start)
            trailing_distance = float(trailing_distance)

            if price <= 0:
                return False, "❌ Invalid entry price"

            if qty <= 0:
                return False, "❌ Invalid quantity"

            if target >= price:
                return False, "❌ SELL target must be below entry"

            if stoploss <= price:
                return False, "❌ SELL stoploss must be above entry"

            if trailing_enabled:

                if trailing_start <= 0:
                    return False, "❌ Invalid trailing start"

                if trailing_distance <= 0:
                    return False, "❌ Invalid trailing distance"

                if trailing_distance >= trailing_start:
                    return False, (
                        "❌ Trailing distance should be "
                        "less than trailing start"
                    )

            self.position = {

                "symbol": symbol,
                "side": "SELL",

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
                "lowest_price": price,

                # Trailing status
                "trailing_active": False,

                "entry_time": datetime.now()
            }

            self.save_trade(
                action="SHORT",
                symbol=symbol,
                entry=price,
                exit_price="",
                qty=qty,
                target=target,
                stoploss=stoploss,
                pnl=0.0
            )

            logging.info(
                f"🔴 SHORT | {symbol} | "
                f"Entry={price} | Qty={qty} | "
                f"Target={target} | SL={stoploss} | "
                f"Trailing={trailing_enabled}"
            )

            return True, "✅ SELL/SHORT Order Executed Successfully"

        except Exception as e:

            logging.exception(
                "❌ Paper Short Error"
            )

            return False, f"Error: {e}"

    # =====================================================
    # TRAILING STOPLOSS
    # =====================================================

    def update_trailing_stop(self, current_price):
        """
        Update trailing stoploss.

        BUY:
            Track highest price.
            When profit >= trailing_start:
                SL = highest_price - trailing_distance

        SELL:
            Track lowest price.
            When profit >= trailing_start:
                SL = lowest_price + trailing_distance

        Stoploss NEVER moves backward.
        """

        if self.position is None:
            return None

        try:

            current_price = float(current_price)

            if current_price <= 0:
                return None

            position = self.position

            side = position.get("side", "BUY")

            entry = float(position["entry"])

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
                    10
                )
            )

            trailing_distance = float(
                position.get(
                    "trailing_distance",
                    5
                )
            )

            # =================================================
            # BUY
            # =================================================

            if side == "BUY":

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

                profit_points = (
                    highest_price - entry
                )

                # Activate trailing
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
                            f"📈 BUY Trailing SL moved | "
                            f"{position['symbol']} | "
                            f"Price={current_price} | "
                            f"SL={new_stoploss}"
                        )

                        return new_stoploss

            # =================================================
            # SELL / SHORT
            # =================================================

            elif side == "SELL":

                lowest_price = float(
                    position.get(
                        "lowest_price",
                        entry
                    )
                )

                if current_price < lowest_price:

                    lowest_price = current_price

                    position["lowest_price"] = (
                        lowest_price
                    )

                profit_points = (
                    entry - lowest_price
                )

                # Activate trailing
                if profit_points >= trailing_start:

                    position["trailing_active"] = True

                    new_stoploss = round(
                        lowest_price +
                        trailing_distance,
                        2
                    )

                    old_stoploss = float(
                        position["stoploss"]
                    )

                    # SL only moves DOWN
                    if new_stoploss < old_stoploss:

                        position["stoploss"] = (
                            new_stoploss
                        )

                        logging.info(
                            f"📉 SELL Trailing SL moved | "
                            f"{position['symbol']} | "
                            f"Price={current_price} | "
                            f"SL={new_stoploss}"
                        )

                        return new_stoploss

        except Exception as e:

            logging.exception(
                f"❌ Trailing Stop Error: {e}"
            )

        return None

    # =====================================================
    # EXIT POSITION
    # =====================================================

    def sell(self, current_price, exit_reason="MANUAL"):
        """
        Close active paper position.
        """

        if self.position is None:
            return False, "❌ No Active Position Found"

        try:

            current_price = float(current_price)

            if current_price <= 0:
                return False, "❌ Invalid exit price"

            position = self.position

            symbol = position["symbol"]
            side = position.get("side", "BUY")

            entry = float(position["entry"])
            qty = int(position["qty"])
            target = float(position["target"])
            stoploss = float(position["stoploss"])

            # -------------------------------------------------
            # P&L
            # -------------------------------------------------

            if side == "SELL":

                pnl = round(
                    (entry - current_price) * qty,
                    2
                )

            else:

                pnl = round(
                    (current_price - entry) * qty,
                    2
                )

            # -------------------------------------------------
            # Balance
            # -------------------------------------------------

            if side == "BUY":

                invested_capital = entry * qty

                self.balance += (
                    invested_capital + pnl
                )

            else:

                self.balance += pnl

            # -------------------------------------------------
            # Save trade
            # -------------------------------------------------

            self.save_trade(
                action=(
                    "SELL"
                    if side == "BUY"
                    else "BUY TO COVER"
                ),
                symbol=symbol,
                entry=entry,
                exit_price=current_price,
                qty=qty,
                target=target,
                stoploss=stoploss,
                pnl=pnl
            )

            self.position = None

            logging.info(
                f"🔚 EXIT | {symbol} | "
                f"Side={side} | "
                f"Reason={exit_reason} | "
                f"Exit={current_price} | "
                f"PNL={pnl}"
            )

            return True, pnl

        except Exception as e:

            logging.exception(
                "❌ Paper Exit Error"
            )

            return False, str(e)

    # =====================================================
    # AUTO EXIT
    # =====================================================

    def auto_exit(self, current_price):
        """
        Automatic Target / Stoploss / Trailing Stoploss.

        BUY:
            Target -> current >= target
            SL     -> current <= stoploss

        SELL:
            Target -> current <= target
            SL     -> current >= stoploss
        """

        if self.position is None:
            return None

        try:

            current_price = float(current_price)

            if current_price <= 0:
                return None

            position = self.position

            symbol = position["symbol"]
            side = position.get("side", "BUY")

            target = float(position["target"])

            # -------------------------------------------------
            # FIRST UPDATE TRAILING SL
            # -------------------------------------------------

            self.update_trailing_stop(
                current_price
            )

            # Get UPDATED SL
            stoploss = float(
                self.position["stoploss"]
            )

            trailing_active = bool(
                self.position.get(
                    "trailing_active",
                    False
                )
            )

            # =================================================
            # BUY
            # =================================================

            if side == "BUY":

                if current_price >= target:

                    success, result = self.sell(
                        current_price,
                        exit_reason="TARGET"
                    )

                    if success:

                        update_learning(
                            "AI Combo",
                            symbol,
                            "WIN"
                        )

                        return "🎯 Target Hit"

                if current_price <= stoploss:

                    success, result = self.sell(
                        current_price,
                        exit_reason=(
                            "TRAILING_STOPLOSS"
                            if trailing_active
                            else "STOPLOSS"
                        )
                    )

                    if success:

                        result_type = (
                            "WIN"
                            if result >= 0
                            else "LOSS"
                        )

                        update_learning(
                            "AI Combo",
                            symbol,
                            result_type
                        )

                        if trailing_active:
                            return (
                                "🔒 Trailing Stoploss Hit"
                            )

                        return "🛑 Stoploss Hit"

            # =================================================
            # SELL / SHORT
            # =================================================

            elif side == "SELL":

                if current_price <= target:

                    success, result = self.sell(
                        current_price,
                        exit_reason="TARGET"
                    )

                    if success:

                        update_learning(
                            "AI Combo",
                            symbol,
                            "WIN"
                        )

                        return "🎯 Short Target Hit"

                if current_price >= stoploss:

                    success, result = self.sell(
                        current_price,
                        exit_reason=(
                            "TRAILING_STOPLOSS"
                            if trailing_active
                            else "STOPLOSS"
                        )
                    )

                    if success:

                        result_type = (
                            "WIN"
                            if result >= 0
                            else "LOSS"
                        )

                        update_learning(
                            "AI Combo",
                            symbol,
                            result_type
                        )

                        if trailing_active:
                            return (
                                "🔒 Short Trailing Stoploss Hit"
                            )

                        return "🛑 Short Stoploss Hit"

        except Exception as e:

            logging.exception(
                f"❌ Auto Exit Error: {e}"
            )

        return None

    # =====================================================
    # POSITION STATUS
    # =====================================================

    def get_position_status(self):

        if self.position is None:
            return None

        position = self.position

        return {
            "symbol": position.get("symbol"),
            "side": position.get("side"),
            "entry": position.get("entry"),
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
            )
        }

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
        pnl
    ):
        """Save trade data into trade_history.csv."""

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
    Utility function for testing Target / Stoploss.
    """

    try:

        entry = float(entry)
        current = float(current)

        action = str(action).upper()

        if action == "SELL":

            if current <= entry - target_points:
                return "TARGET"

            if current >= entry + stoploss_points:
                return "STOPLOSS"

        else:

            if current >= entry + target_points:
                return "TARGET"

            if current <= entry - stoploss_points:
                return "STOPLOSS"

    except Exception:
        pass

    return None