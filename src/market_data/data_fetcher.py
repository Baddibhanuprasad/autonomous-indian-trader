"""
Data fetcher for market data with caching and persistence.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from src.market_data.angel_one_client import AngelOneClient
from src.market_data.models import OHLCVData
from src.database.repositories.market_data_repository import MarketDataRepository
from src.database.models.market_data import MarketData
from src.config.settings import Settings

logger = logging.getLogger(__name__)


class DataFetcher:
    """
    High-level interface for fetching market data.
    Handles caching, persistence, and live data streaming.
    """
    
    def __init__(
        self,
        client: AngelOneClient,
        db_session: Session,
        settings: Settings,
    ):
        """
        Initialize the data fetcher.
        """
        self.client = client
        self.db_session = db_session
        self.settings = settings
        self.repository = MarketDataRepository(db_session)
        
        logger.info("Data fetcher initialized")
    
    def fetch_historical_data(
        self,
        symbol: str,
        exchange: str = "NSE",
        interval: str = "1d",
        days: Optional[int] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        save_to_db: bool = True,
    ) -> List[OHLCVData]:
        """
        Fetch historical OHLCV data.
        """
        if days is None:
            days = self.settings.market_data.historical_lookback_days
        
        if to_date is None:
            to_date = datetime.now()
        if from_date is None:
            from_date = to_date - timedelta(days=days)
        
        logger.info(f"Fetching historical data for {symbol} ({interval})")
        
        # Fetch data from API
        ohlcv_data = self.client.get_historical_data(
            symbol=symbol,
            exchange=exchange,
            interval=interval,
            from_date=from_date,
            to_date=to_date,
        )
        
        if not ohlcv_data:
            logger.warning(f"No historical data for {symbol}")
            return []
        
        # Save to database if requested
        if save_to_db:
            self._save_ohlcv_data(ohlcv_data)
        
        logger.info(f"Fetched {len(ohlcv_data)} data points for {symbol}")
        return ohlcv_data
    
    def _save_ohlcv_data(self, ohlcv_data: List[OHLCVData]) -> None:
        """
        Save OHLCV data to the database.
        """
        saved_count = 0
        for data in ohlcv_data:
            try:
                # Check if data already exists
                existing = self.db_session.query(MarketData).filter(
                    MarketData.symbol == data.symbol,
                    MarketData.timestamp == data.timestamp,
                    MarketData.interval == data.interval,
                ).first()
                
                if not existing:
                    # Create new record
                    market_data = MarketData(
                        symbol=data.symbol,
                        timestamp=data.timestamp,
                        open=data.open,
                        high=data.high,
                        low=data.low,
                        close=data.close,
                        volume=data.volume,
                        interval=data.interval,
                        source=data.source,
                    )
                    self.db_session.add(market_data)
                    saved_count += 1
                    
            except Exception as e:
                logger.error(f"Error saving OHLCV data: {e}")
        
        try:
            self.db_session.commit()
            logger.info(f"Saved {saved_count} new data points")
        except Exception as e:
            logger.error(f"Error committing OHLCV data: {e}")
            self.db_session.rollback()
    
    def get_latest_data(self, symbol: str) -> Optional[MarketData]:
        """
        Get the latest data for a symbol from the database.
        """
        return self.repository.get_latest(symbol)
    
    def get_data_range(
        self,
        symbol: str,
        from_date: datetime,
        to_date: datetime,
    ) -> List[MarketData]:
        """
        Get historical data from the database within a date range.
        """
        return self.repository.get_by_date_range(symbol, from_date, to_date)
    
    def get_symbol_token(self, symbol: str, exchange: str = "NSE") -> Optional[str]:
        """
        Get the token for a symbol.
        """
        return self.client.get_symbol_token(symbol, exchange)
    
    def get_ltp(self, symbol: str, exchange: str = "NSE") -> Optional[float]:
        """
        Get last traded price.
        """
        return self.client.get_ltp(symbol, exchange)
    
    def search_symbols(self, query: str, exchange: str = "NSE") -> List[Dict]:
        """
        Search for symbols.
        """
        return self.client.search_symbols(query, exchange)
    
    def get_scrip_master(self) -> Optional[List[Dict]]:
        """
        Get the scrip master.
        """
        return self.client.get_scrip_master()