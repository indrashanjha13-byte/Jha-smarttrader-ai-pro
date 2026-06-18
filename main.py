from strategy import generate_signal
from TradingSoftware.ai.ai_signal_ranker import signal_score
from TradingSoftware.ai.ai_trade_filter import trade_allowed
from TradingSoftware.ai.ai_model import model

from signals import get_signals

data = get_signals("^NSEI")
print(data)
if "error" in data:
    print(data["error"])
    exit()

signal = generate_signal(
    data["SUPERTREND"],
    data["MACD"],
    data["MACD_SIGNAL"],
    data["Volume"],
    data["AVG_VOLUME"],
)
print("SIGNAL =", signal)

print(data)
from paper_trading import PaperTrader

trader = PaperTrader()

trader.buy(
    "BANKNIFTY",
    500,
    10
)

trader.sell(530)

print(
    "Balance =",
    trader.balance
)
from config import MODE

if MODE == "PAPER":

    print(
        "Paper Trading Started"
    )

else:

    print(
        "Live Trading Started"
    )
    
from telegram_bot import send_alert

send_alert(
    "BUY NIFTY @ 25100"
) 

from signals import get_signals
from strategy import generate_signal

symbol = "RELIANCE.NS"

data = get_signals(symbol)
