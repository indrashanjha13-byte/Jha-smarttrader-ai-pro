import datetime
import logging

class DemoBroker:
    def __init__(self, initial_balance=100000.0):
        self.connected = False
        self.balance = float(initial_balance)
        self.positions = []
        self.holdings = []
        self.orders = []

    def connect(self):
        self.connected = True
        return True

    def get_balance(self):
        return self.balance

    def get_positions(self):
        return self.positions

    def get_holdings(self):
        return self.holdings

    def order_book(self):
        return self.orders

    def buy(self, symbol, qty, price=0.0, **kwargs):
        qty = int(qty)
        price = float(price)

        # Record Order History
        order = {
            "Timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Action": "BUY",
            "Symbol": symbol,
            "Qty": qty,
            "Price": price,
            "Status": "EXECUTED"
        }
        self.orders.append(order)

        # Update Position State
        existing = next((p for p in self.positions if p["symbol"] == symbol), None)
        if existing:
            total_qty = existing["qty"] + qty
            avg_price = ((existing["entry"] * existing["qty"]) + (price * qty)) / total_qty if total_qty > 0 else price
            existing["qty"] = total_qty
            existing["entry"] = avg_price
        else:
            self.positions.append({
                "symbol": symbol,
                "qty": qty,
                "entry": price,
                "target": kwargs.get("target", price + 40 if price else 0),
                "stoploss": kwargs.get("stoploss", price - 20 if price else 0)
            })

        # Deduct Estimated Balance
        cost = price * qty
        if self.balance >= cost:
            self.balance -= cost

        logging.info(f"DEMO BUY -> {symbol} Qty={qty} @ {price}")
        return {"status": "success", "order": order}

    def sell(self, symbol, qty, price=0.0, **kwargs):
        qty = int(qty)
        price = float(price)

        # Record Order History
        order = {
            "Timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Action": "SELL",
            "Symbol": symbol,
            "Qty": qty,
            "Price": price,
            "Status": "EXECUTED"
        }
        self.orders.append(order)

        # Update Position State
        existing = next((p for p in self.positions if p["symbol"] == symbol), None)
        if existing:
            if existing["qty"] <= qty:
                self.positions.remove(existing)
            else:
                existing["qty"] -= qty

        # Add Proceeds to Balance
        self.balance += (price * qty)

        logging.info(f"DEMO SELL -> {symbol} Qty={qty} @ {price}")
        return {"status": "success", "order": order}
