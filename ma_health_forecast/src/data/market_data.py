from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional

class MarketDataProvider(ABC):
    """
    Abstract Interface for fetching financial data.
    Ensures that all downstream logic (Strategic Radar, Forecasting)
    is decoupled from the specific data source (yfinance, Bloomberg, etc).
    """

    @abstractmethod
    def get_fundamentals(self, ticker: str) -> Dict[str, Any]:
        """
        Returns fundamental data (Cash, Debt, EBITDA, etc).
        Must include a 'provenance' key with source metadata.
        """
        pass

    @abstractmethod
    def get_snapshot(self, tickers: List[str]) -> Dict[str, Dict]:
        """
        Returns real-time price/volume snapshot for a list of tickers.
        """
        pass

    @abstractmethod
    def get_sparkline(self, ticker: str, days: int = 90) -> List[float]:
        """
        Returns a list of closing prices for the last N days.
        """
        pass
