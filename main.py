import logging

# Standard Project Imports (Safe Paths)
try:
    from signals import get_signals
    from strategy import generate_signal
    from ai_signal_ranker import signal_score
    from ai_trade_filter import trade_allowed
    from paper_trading import PaperTrader
    from config import MODE
    from telegram_bot import send_alert
except ImportError as e:
    logging.error(f"❌ Import Failure in test_runner: {e}")


def run_trading_pipeline(symbol="^NSEI"):
    """
    Executes an end-to-end signal analysis and trade execution pipeline safely.
    """
    logging.info(f"🚀 Starting Trading Pipeline for {symbol}...")

    # 1. Fetch Market Data & Signals
    data = get_signals(symbol)

    if not data or "error" in data:
        logging.error(f"❌ Signal Retrieval Failed for {symbol}: {data.get('error', 'Unknown Error')}")
        return False

    # 2. Strategy Signal Generation
    signal = generate_signal(
        data.get("SUPERTREND", 0),
        data.get("MACD", 0),
        data.get("MACD_SIGNAL", 0),
        data.get("Volume", 0),
        data.get("AVG_VOLUME", 0)
    )
    logging.info(f"📊 Signal Generated for {symbol}: {signal}")

    # 3. Paper Trader Execution Validation
    trader = PaperTrader()

    if signal == "BUY":
        current_price = data.get("Close", 25000.0)
        qty = 15

        # Execute Buy Order Safely
        buy_success = trader.buy(symbol=symbol, price=current_price, qty=qty)

        if buy_success:
            logging.info(f"✅ Paper Trade Opened. Balance: ₹{getattr(trader, 'balance', 100000)}")
            
            # Send Telegram Alert
            try:
                send_alert(f"🟢 BUY SIGNAL: {symbol} @ ₹{current_price} | Qty: {qty}")
            except Exception as e:
                logging.error(f"⚠️ Telegram Notification Error: {e}")

    # 4. Mode Status Check
    logging.info(f"🤖 Active System Trading Mode: {MODE}")
    return True


if __name__ == "__main__":
    # Test execution for default symbol
    run_trading_pipeline("^NSEI")