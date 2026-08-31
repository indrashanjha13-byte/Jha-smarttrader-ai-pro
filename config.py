import os
import logging
from dotenv import load_dotenv

# Load sensitive environment variables from .env file if available
load_dotenv()

# ==============================
# Risk Management (Validated)
# ==============================
STOP_LOSS = float(os.getenv("STOP_LOSS", 20.0))
TARGET = float(os.getenv("TARGET", 40.0))
LOT_SIZE = int(os.getenv("LOT_SIZE", 75))

# Validation Checks
if STOP_LOSS <= 0 or TARGET <= 0 or LOT_SIZE <= 0:
    logging.warning("⚠️ Invalid Risk Management constants. Resetting to defaults.")
    STOP_LOSS = 20.0
    TARGET = 40.0
    LOT_SIZE = 75

# ==============================
# Trading Mode & Active Broker
# ==============================
# PAPER / LIVE
MODE = os.getenv("TRADING_MODE", "PAPER").upper().strip()

# Options: KOTAK_NEO, DHAN, ZERODHA, ANGEL_ONE, UPSTOX, DEMO
BROKER = os.getenv("ACTIVE_BROKER", "KOTAK_NEO").upper().strip().replace(" ", "_")

# ==============================
# Telegram Notifications
# ==============================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
CHAT_ID = os.getenv("CHAT_ID", "")

# ==============================
# Kotak Neo API Credentials
# ==============================
KOTAK_CONSUMER_KEY = os.getenv("KOTAK_CONSUMER_KEY", "")
KOTAK_MOBILE_NUMBER = os.getenv("KOTAK_MOBILE_NUMBER", "")
KOTAK_UCC = os.getenv("KOTAK_UCC", "")
KOTAK_TOTP_SECRET = os.getenv("KOTAK_TOTP_SECRET", "")
KOTAK_MPIN = os.getenv("KOTAK_MPIN", "")

# ==============================
# Dhan API Credentials
# ==============================
DHAN_CLIENT_ID = os.getenv("DHAN_CLIENT_ID", "")
DHAN_ACCESS_TOKEN = os.getenv("DHAN_ACCESS_TOKEN", "")

# ==============================
# Zerodha API Credentials
# ==============================
ZERODHA_API_KEY = os.getenv("ZERODHA_API_KEY", "")
ZERODHA_ACCESS_TOKEN = os.getenv("ZERODHA_ACCESS_TOKEN", "")

# ==============================
# Angel One API Credentials
# ==============================
ANGEL_API_KEY = os.getenv("ANGEL_API_KEY", "")
ANGEL_CLIENT_CODE = os.getenv("ANGEL_CLIENT_CODE", "")

# ==============================
# Upstox API Credentials
# ==============================
UPSTOX_API_KEY = os.getenv("UPSTOX_API_KEY", "")
UPSTOX_ACCESS_TOKEN = os.getenv("UPSTOX_ACCESS_TOKEN", "")