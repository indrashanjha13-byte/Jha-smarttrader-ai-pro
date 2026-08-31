import logging


class MarketFeed:
    """
    Handles real-time market feed connection and tick event callbacks.
    """

    def __init__(self):
        self.is_connected = False

    def connect(self):
        """Establishes connection to the market data feed source."""
        try:
            # Add broker specific WebSocket connection logic here if needed
            self.is_connected = True
            logging.info("🟢 Market Feed Connected Successfully.")
            print("Market Feed Connected")
        except Exception as e:
            self.is_connected = False
            logging.error(f"❌ Failed to connect market feed: {e}")

    def on_tick(self, data):
        """
        Callback triggered on receiving every new market tick.
        """
        try:
            if not data:
                return
            
            # Process incoming tick data (e.g., LTP, volume, timestamp)
            # You can route this tick data to your strategy or exit manager check loops here.
            
            # For debugging/logging
            # logging.debug(f"Tick received: {data}")
            print(data)

        except Exception as e:
            logging.error(f"❌ Error processing market tick: {e}")