from threading import Lock
import logging

# Thread-safe Lock for Configuration State
_config_lock = Lock()

# Default Configuration State
_config = {
    "AUTO_TRADING": False,
    "SCAN_INTERVAL": 15  # seconds
}


def enable_auto():
    """Thread-safe activation of auto trading."""
    with _config_lock:
        _config["AUTO_TRADING"] = True
        logging.info("🤖 Auto-Trading Status: ENABLED")


def disable_auto():
    """Thread-safe deactivation of auto trading."""
    with _config_lock:
        _config["AUTO_TRADING"] = False
        logging.info("🛑 Auto-Trading Status: DISABLED")


def is_enabled():
    """Returns current auto-trading state safely."""
    with _config_lock:
        return _config["AUTO_TRADING"]


def set_scan_interval(seconds):
    """Dynamically sets scan interval with safe boundary checks."""
    if not isinstance(seconds, (int, float)) or seconds < 1:
        logging.warning("⚠️ Invalid scan interval. Must be at least 1 second.")
        return False

    with _config_lock:
        _config["SCAN_INTERVAL"] = int(seconds)
        logging.info(f"⏱️ Scan Interval updated to {_config['SCAN_INTERVAL']} seconds.")
        return True


def get_scan_interval():
    """Returns current scan interval safely."""
    with _config_lock:
        return _config["SCAN_INTERVAL"]