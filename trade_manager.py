import logging

from ai_learning import auto_strategy
from risk_manager import calculate_trade_details
from config import LOT_SIZE, MODE


class TradeManager:
    """
    Central trade execution manager.

    PAPER mode:
        Uses the supplied PaperTrader only.

    LIVE mode:
        Blocked for now for safety.
        Broker integration will be added after Paper Trading testing.
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
        self.active_position = None

        # =====================================================
        # TRAILING STOPLOSS SETTINGS
        # =====================================================

        self.trailing_enabled = bool(trailing_enabled)
        self.trailing_start = float(trailing_start)
        self.trailing_distance = float(trailing_distance)

    # =========================================================
    # Set Paper Trader
    # =========================================================

    def set_paper_trader(self, paper_trader):
        self.paper_trader = paper_trader

    # =========================================================
    # Set Trailing Stoploss
    # =========================================================

    def set_trailing_settings(
        self,
        enabled=False,
        start=10.0,
        distance=5.0
    ):
        """
        Update trailing stoploss settings.

        PAPER TRADING ONLY.
        """

        start = float(start)
        distance = float(distance)

        if start <= 0:
            return False, "Trailing start must be greater than 0"

        if distance <= 0:
            return False, "Trailing distance must be greater than 0"

        if distance >= start:
            return False, (
                "Trailing distance must be less "
                "than trailing start"
            )

        self.trailing_enabled = bool(enabled)
        self.trailing_start = start
        self.trailing_distance = distance

        logging.info(
            f"Trailing settings updated | "
            f"Enabled={self.trailing_enabled} | "
            f"Start={self.trailing_start} | "
            f"Distance={self.trailing_distance}"
        )

        return True, "Trailing settings updated"

    # =========================================================
    # Process Signal
    # =========================================================

    def process(
        self,
        symbol,
        signal,
        current_price,
        capital
    ):
        try:
            symbol = str(symbol).strip().upper()
            signal = str(signal).strip().upper()
            current_price = float(current_price)
            capital = float(capital)

            # =====================================================
            # Validation
            # =====================================================

            if not symbol:
                return False, "Invalid symbol"

            if signal not in ("BUY", "SELL"):
                return False, "Invalid signal"

            if current_price <= 0:
                return False, "Invalid price"

            if capital <= 0:
                return False, "Invalid capital"

            # =====================================================
            # Paper Trading Settings
            # =====================================================

            risk_percent = 1.0
            stoploss_percent = 0.5
            target_percent = 1.0

            # =====================================================
            # Risk Calculation
            # =====================================================

            risk_amount = capital * (
                risk_percent / 100
            )

            sl_distance = current_price * (
                stoploss_percent / 100
            )

            if sl_distance <= 0:
                return False, "Invalid stoploss distance"

            # =====================================================
            # Quantity
            # =====================================================

            quantity = int(
                risk_amount / sl_distance
            )

            if quantity < 1:
                quantity = 1

            # =====================================================
            # Entry / SL / Target
            # =====================================================

            entry_price = current_price

            if signal == "BUY":

                stoploss = (
                    entry_price - sl_distance
                )

                target = (
                    entry_price
                    + entry_price * target_percent / 100
                )

            else:  # SELL

                stoploss = (
                    entry_price + sl_distance
                )

                target = (
                    entry_price
                    - entry_price * target_percent / 100
                )

            # =====================================================
            # Paper Trade
            # =====================================================

            paper_trade = {
                "symbol": symbol,
                "side": signal,
                "entry_price": round(entry_price, 2),
                "quantity": quantity,
                "stoploss": round(stoploss, 2),
                "target": round(target, 2),
                "capital": round(capital, 2),
                "mode": "PAPER",
                "status": "OPEN"
            }

            self.active_position = paper_trade

            return True, paper_trade

        except Exception as e:
            return False, f"Process error: {e}"
        
    # =========================================================
    # Get Active Position
    # =========================================================

    def get_active_position(self):
        return self.active_position
    
    # =========================================================
    # Check Paper Position
    # =========================================================

    def check_position(
        self,
        position,
        current_price
    ):
        try:
            current_price = float(current_price)

            if not position:
                return False, "No active position"

            if current_price <= 0:
                return False, "Invalid price"

            side = position["side"]
            entry_price = float(position["entry_price"])
            quantity = int(position["quantity"])
            stoploss = float(position["stoploss"])
            target = float(position["target"])

            # =====================================================
            # BUY Position
            # =====================================================

            if side == "BUY":

                if current_price <= stoploss:
                    pnl = (
                        current_price - entry_price
                    ) * quantity

                    return True, {
                        "status": "EXIT",
                        "reason": "STOPLOSS",
                        "exit_price": current_price,
                        "pnl": round(pnl, 2)
                    }

                if current_price >= target:
                    pnl = (
                        current_price - entry_price
                    ) * quantity

                    return True, {
                        "status": "EXIT",
                        "reason": "TARGET",
                        "exit_price": current_price,
                        "pnl": round(pnl, 2)
                    }

            # =====================================================
            # SELL Position
            # =====================================================

            elif side == "SELL":

                if current_price >= stoploss:
                    pnl = (
                        entry_price - current_price
                    ) * quantity

                    return True, {
                        "status": "EXIT",
                        "reason": "STOPLOSS",
                        "exit_price": current_price,
                        "pnl": round(pnl, 2)
                    }

                if current_price <= target:
                    pnl = (
                        entry_price - current_price
                    ) * quantity

                    return True, {
                        "status": "EXIT",
                        "reason": "TARGET",
                        "exit_price": current_price,
                        "pnl": round(pnl, 2)
                    }

            return True, {
                "status": "HOLD",
                "current_price": current_price,
                "pnl": round(
                    (
                        current_price - entry_price
                    ) * quantity
                    if side == "BUY"
                    else (
                        entry_price - current_price
                    ) * quantity,
                    2
                )
            }

        except Exception as e:
            return False, f"Position check error: {e}"

            # -------------------------------------------------
            # HOLD
            # -------------------------------------------------

            if signal == "HOLD":
                return False, "HOLD"

            # -------------------------------------------------
            # Duplicate signal protection
            # -------------------------------------------------

            if signal == self.last_signal:
                return False, "Duplicate signal ignored"

            # -------------------------------------------------
            # PAPER MODE ONLY
            # -------------------------------------------------

            if MODE != "PAPER":
                logging.warning(
                    "LIVE mode requested, but live execution is "
                    "disabled in this Phase."
                )

                return False, (
                    "🔒 LIVE trading is currently locked. "
                    "Use PAPER mode for testing."
                )

            if self.paper_trader is None:
                return False, "PaperTrader is not connected"

            # -------------------------------------------------
            # Existing position check
            # -------------------------------------------------

            if self.paper_trader.position is not None:

                existing = self.paper_trader.position

                # If opposite signal comes, close existing position.
                existing_side = existing.get("side", "BUY")

                if (
                    signal == "BUY"
                    and existing_side == "SELL"
                ) or (
                    signal == "SELL"
                    and existing_side == "BUY"
                ):

                    success, result = self.paper_trader.sell(
                        current_price
                    )

                    if success:
                        self.last_signal = signal

                        return True, (
                            f"🔄 Existing position closed: "
                            f"PnL ₹{result}"
                        )

                    return False, str(result)

                return False, "Position already open"

            # -------------------------------------------------
            # BUY / SELL Risk Calculation
            # -------------------------------------------------

            selected_strategy = "AI Combo"

            try:
                selected_strategy = auto_strategy() or "AI Combo"
            except Exception:
                pass

            # BUY:
            # 1% stop loss
            # 1:2 reward:risk

            if signal == "BUY":

                stoploss_price = round(
                    current_price * 0.99,
                    2
                )

                trade = calculate_trade_details(
                    capital=capital,
                    entry_price=current_price,
                    stoploss_price=stoploss_price,
                    lot_size=LOT_SIZE,
                    reward_ratio=2.0
                )

                lots = int(trade.get("lots", 0))
                qty = int(trade.get("quantity", 0))
                target = float(
                    trade.get("target_price", 0)
                )

                if lots <= 0 or qty <= 0:
                    return False, (
                        "⚠️ Trade skipped: "
                        "capital is insufficient for 1 lot "
                        "under the configured risk."
                    )

                success, message = self.paper_trader.buy(
                    symbol=symbol,
                    price=current_price,
                    qty=qty,
                    target=target,
                    stoploss=stoploss_price,
                    trailing_enabled=self.trailing_enabled,
                    trailing_start=self.trailing_start,
                    trailing_distance=self.trailing_distance
                )

                if not success:
                    return False, message

                self.last_signal = "BUY"

                logging.info(
                    f"🟢 PAPER BUY | {symbol} | "
                    f"Qty={qty} | Entry={current_price} | "
                    f"SL={stoploss_price} | Target={target}"
                )

                return True, {
                    "action": "BUY",
                    "symbol": symbol,
                    "qty": qty,
                    "entry": current_price,
                    "stoploss": stoploss_price,
                    "target": target,
                    "lots": lots,
                    "strategy": selected_strategy,
                    "risk": trade
                }

            # -------------------------------------------------
            # SELL / SHORT
            # -------------------------------------------------

            if signal == "SELL":

                # For short:
                # Stop loss = 1% above entry
                # Target = 2% below entry

                stoploss_price = round(
                    current_price * 1.01,
                    2
                )

                target_price = round(
                    current_price * 0.98,
                    2
                )

                risk_per_unit = (
                    stoploss_price - current_price
                )

                risk_amount = capital * 0.02

                risk_per_lot = (
                    risk_per_unit * LOT_SIZE
                )

                if risk_per_lot <= 0:
                    return False, "Invalid short risk calculation"

                lots = int(
                    risk_amount // risk_per_lot
                )

                qty = lots * LOT_SIZE

                if lots <= 0 or qty <= 0:
                    return False, (
                        "⚠️ Short trade skipped: "
                        "capital is insufficient for 1 lot."
                    )

                success, message = self.paper_trader.short(
                    symbol=symbol,
                    price=current_price,
                    qty=qty,
                    target=target_price,
                    stoploss=stoploss_price,
                    trailing_enabled=self.trailing_enabled,
                    trailing_start=self.trailing_start,
                    trailing_distance=self.trailing_distance
                )

                if not success:
                    return False, message

                self.last_signal = "SELL"

                logging.info(
                    f"🔴 PAPER SHORT | {symbol} | "
                    f"Qty={qty} | Entry={current_price} | "
                    f"SL={stoploss_price} | Target={target_price}"
                )

                return True, {
                    "action": "SELL",
                    "symbol": symbol,
                    "qty": qty,
                    "entry": current_price,
                    "stoploss": stoploss_price,
                    "target": target_price,
                    "lots": lots,
                    "strategy": selected_strategy
                }

            return False, "Unknown signal"

        except Exception as e:

            logging.exception(
                "❌ TradeManager process error"
            )

            return False, str(e)
