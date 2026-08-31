from abc import ABC, abstractmethod
import logging


class BaseBroker(ABC):
    """
    Abstract Base Class defining the blueprint for all Broker API Integrations.
    Ensures consistent implementation across Zerodha, Kotak, Upstox, Dhan, etc.
    """

    @abstractmethod
    def login(self) -> bool:
        """Authenticate with the broker API."""
        pass

    @abstractmethod
    def buy(self, symbol: str, qty: int, price: float = 0.0, order_type: str = "MARKET", **kwargs) -> dict:
        """Execute a BUY order."""
        pass

    @abstractmethod
    def sell(self, symbol: str, qty: int, price: float = 0.0, order_type: str = "MARKET", **kwargs) -> dict:
        """Execute a SELL order."""
        pass

    @abstractmethod
    def get_positions(self) -> list:
        """Retrieve current open positions."""
        pass

    @abstractmethod
    def get_balance(self) -> float:
        """Retrieve available margin/funds balance."""
        pass

    def cancel_order(self, order_id: str) -> bool:
        """Optional override: Cancel an open order."""
        logging.warning("⚠️ BaseBroker: cancel_order not implemented for this broker.")
        return False