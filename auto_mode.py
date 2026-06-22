AUTO_TRADING = False

def enable_auto():
    global AUTO_TRADING
    AUTO_TRADING = True

def disable_auto():
    global AUTO_TRADING
    AUTO_TRADING = False

def is_enabled():
    return AUTO_TRADING
