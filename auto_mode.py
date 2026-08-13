AUTO_TRADING = False

SCAN_INTERVAL = 15   # seconds

def enable_auto():
    global AUTO_TRADING
    AUTO_TRADING = True

def disable_auto():
    global AUTO_TRADING
    AUTO_TRADING = False

def is_enabled():
    return AUTO_TRADING

def get_scan_interval():
    return SCAN_INTERVAL