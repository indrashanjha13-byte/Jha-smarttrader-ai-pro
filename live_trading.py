import logging
import config
from broker.broker_manager import BrokerManager
from broker.demo_api import DemoBroker as DemoBrokerAPI

# Initialize Demo API for Paper Mode persistence
demo_broker = DemoBrokerAPI()

# Dynamic Broker Manager instance
broker_manager = None


def get_broker_instance():
    """Dynamically fetches/initializes broker manager based on runtime config."""
    global broker_manager
    current_broker = getattr(config, "BROKER", "KOTAK_NEO")
    
    if broker_manager is None or getattr(broker_manager, "broker_name", None) != current_broker:
        broker_manager = BrokerManager(current_broker)
    
    return broker_manager


def execute_buy(symbol, qty, entry, target, stoploss):
    """
    Executes BUY order safely in either PAPER or LIVE mode.
    """
    try:
        mode = getattr(config, "MODE", "PAPER").upper().strip()
        broker_name = getattr(config, "BROKER", "DEMO")

        logging.info("=" * 50)
        logging.info(f"🟢 BUY REQUEST | Broker: {broker_name} | Mode: {mode} | Symbol: {symbol} | Qty: {qty}")
        logging.info("=" * 50)

        # ------------------------------
        # 1. PAPER TRADING MODE
        # ------------------------------
        if mode == "PAPER":
            result = demo_broker.place_buy_order(
                symbol=symbol,
                qty=qty,
                entry=entry,
                target=target,
                stoploss=stoploss
            )
            return result

        # ------------------------------
        # 2. LIVE TRADING MODE
        # ------------------------------
        elif mode == "LIVE":
            bm = get_broker_instance()
            
            # Ensure connection if not authenticated
            if hasattr(bm, "is_connected") and not bm.is_connected():
                connected = bm.connect()
                if not connected:
                    logging.error("❌ Broker connection failed during BUY execution.")
                    return False

            result = bm.buy(symbol=symbol, qty=qty, price=entry)
            logging.info(f"Broker BUY Response: {result}")
            return bool(result)

        else:
            logging.error(f"❌ Unknown Trading MODE: {mode}")
            return False

    except Exception as e:
        logging.error(f"❌ Unexpected Error in execute_buy: {e}")
        return False


def execute_sell(symbol, qty, entry, exit_price, target, stoploss):
    """
    Executes SELL order safely in either PAPER or LIVE mode.
    """
    try:
        mode = getattr(config, "MODE", "PAPER").upper().strip()
        broker_name = getattr(config, "BROKER", "DEMO")
        pnl = round((float(exit_price) - float(entry)) * int(qty), 2)

        logging.info("=" * 50)
        logging.info(f"🔴 SELL REQUEST | Broker: {broker_name} | Mode: {mode} | Symbol: {symbol} | PnL: ₹{pnl}")
        logging.info("=" * 50)

        # ------------------------------
        # 1. PAPER TRADING MODE
        # ------------------------------
        if mode == "PAPER":
            result = demo_broker.place_sell_order(
                symbol=symbol,
                qty=qty,
                entry=entry,
                exit_price=exit_price,
                target=target,
                stoploss=stoploss,
                pnl=pnl
            )
            return result

        # ------------------------------
        # 2. LIVE TRADING MODE
        # ------------------------------
        elif mode == "LIVE":
            bm = get_broker_instance()

            if hasattr(bm, "is_connected") and not bm.is_connected():
                connected = bm.connect()
                if not connected:
                    logging.error("❌ Broker connection failed during SELL execution.")
                    return False

            result = bm.sell(symbol=symbol, qty=qty, price=exit_price)
            logging.info(f"Broker SELL Response: {result}")
            return bool(result)

        else:
            logging.error(f"❌ Unknown Trading MODE: {mode}")
            return False

    except Exception as e:
        logging.error(f"❌ Unexpected Error in execute_sell: {e}")
        return False