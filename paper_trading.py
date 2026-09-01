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
    Paper trading engine.

    Supports:
    - BUY position
    - SELL/SHORT position
    - Target
    - Stoploss
    - Auto Exit
    - P&L calculation
    - Trade history CSV
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
        stoploss
    ):
        """Open a BUY/LONG paper position."""

        try:
            if self.position is not None:
                return False, "❌ An active position already exists"

            price = float(price)
            qty = int(qty)
            target = float(target)
            stoploss = float(stoploss)

            if price <= 0:
                return False, "❌ Invalid entry price"

            if qty <= 0:
                return False, "❌ Invalid quantity"

            if target <= price:
                return False, "❌ BUY target must be above entry"

            if stoploss >= price:
                return False, "❌ BUY stoploss must be below entry"

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
                "stoploss": stoploss,
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
                f"BUY | {symbol} | "
                f"Entry={price} | Qty={qty} | "
                f"Target={target} | SL={stoploss}"
            )

            return True, "✅ BUY Order Executed Successfully"

        except Exception as e:
            logging.error(
                f"❌ Paper Buy Error: {e}"
            )
            return False, f"Error: {e}"

    # =====================================================
    # SHORT SELL
    # =====================================================

    def short(
        self,
        symbol,
        price,
        qty,
        target,
        stoploss
    ):
        """
        Open a SELL/SHORT paper position.

        For SHORT:
        Target < Entry
        Stoploss > Entry
        """

        try:
            if self.position is not None:
                return False, "❌ An active position already exists"

            price = float(price)
            qty = int(qty)
            target = float(target)
            stoploss = float(stoploss)

            if price <= 0:
                return False, "❌ Invalid entry price"

            if qty <= 0:
                return False, "❌ Invalid quantity"

            if target >= price:
                return False, "❌ SELL target must be below entry"

            if stoploss <= price:
                return False, "❌ SELL stoploss must be above entry"

            self.position = {
                "symbol": symbol,
                "side": "SELL",
                "entry": price,
                "qty": qty,
                "target": target,
                "stoploss": stoploss,
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
                f"SHORT | {symbol} | "
                f"Entry={price} | Qty={qty} | "
                f"Target={target} | SL={stoploss}"
            )

            return True, "✅ SELL/SHORT Order Executed Successfully"

        except Exception as e:
            logging.error(
                f"❌ Paper Short Error: {e}"
            )
            return False, f"Error: {e}"

    # =====================================================
    # EXIT POSITION
    # =====================================================

    def sell(self, current_price):
        """
        Closes the active position.

        BUY:
            P&L = (Exit - Entry) × Qty

        SELL:
            P&L = (Entry - Exit) × Qty
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
            # BUY balance settlement
            # -------------------------------------------------

            if side == "BUY":

                invested_capital = entry * qty

                self.balance += (
                    invested_capital + pnl
                )

            # -------------------------------------------------
            # SHORT balance settlement
            # -------------------------------------------------

            else:

                self.balance += pnl

            # -------------------------------------------------
            # Save completed trade
            # -------------------------------------------------

            self.save_trade(
                action="SELL" if side == "BUY" else "BUY TO COVER",
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
                f"EXIT | {symbol} | "
                f"Side={side} | "
                f"Exit={current_price} | "
                f"PNL={pnl}"
            )

            return True, pnl

        except Exception as e:
            logging.error(
                f"❌ Paper Exit Error: {e}"
            )
            return False, str(e)

    # =====================================================
    # AUTO EXIT
    # =====================================================

    def auto_exit(self, current_price):
        """
        Automatically checks Target and Stoploss.

        BUY:
            Price >= Target  -> TARGET
            Price <= SL      -> STOPLOSS

        SELL:
            Price <= Target  -> TARGET
            Price >= SL      -> STOPLOSS
        """

        if self.position is None:
            return None

        try:
            current_price = float(current_price)

            position = self.position

            symbol = position["symbol"]
            side = position.get("side", "BUY")

            target = float(position["target"])
            stoploss = float(position["stoploss"])

            # =================================================
            # BUY POSITION
            # =================================================

            if side == "BUY":

                if current_price >= target:

                    success, result = self.sell(
                        current_price
                    )

                    if success:
                        update_learning(
                            "AI Combo",
                            symbol,
                            "WIN"
                        )

                        return "🎯 Target Hit"

                elif current_price <= stoploss:

                    success, result = self.sell(
                        current_price
                    )

                    if success:
                        update_learning(
                            "AI Combo",
                            symbol,
                            "LOSS"
                        )

                        return "🛑 Stoploss Hit"

            # =================================================
            # SELL / SHORT POSITION
            # =================================================

            elif side == "SELL":

                if current_price <= target:

                    success, result = self.sell(
                        current_price
                    )

                    if success:
                        update_learning(
                            "AI Combo",
                            symbol,
                            "WIN"
                        )

                        return "🎯 Short Target Hit"

                elif current_price >= stoploss:

                    success, result = self.sell(
                        current_price
                    )

                    if success:
                        update_learning(
                            "AI Combo",
                            symbol,
                            "LOSS"
                        )

                        return "🛑 Short Stoploss Hit"

        except Exception as e:
            logging.error(
                f"❌ Auto Exit Error: {e}"
            )

        return None

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
    Utility function for testing target/stoploss.

    BUY:
        Target = Entry + target_points
        SL     = Entry - stoploss_points

    SELL:
        Target = Entry - target_points
        SL     = Entry + stoploss_points
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
