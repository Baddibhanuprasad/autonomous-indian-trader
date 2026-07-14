"""
Angel One SmartAPI client wrapper using the official SmartAPI library.
"""

import logging
import json
import requests
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from SmartApi import SmartConnect
import pyotp

from src.market_data.models import OHLCVData, SymbolInfo
from src.config.settings import Settings

logger = logging.getLogger(__name__)


class AngelOneClient:
    """
    Wrapper for Angel One SmartAPI using the official SmartAPI library.
    Handles authentication, token management, and API calls.
    """
    
    def __init__(self, settings: Settings):
        """
        Initialize the Angel One client.
        """
        self.settings = settings
        self.api_key = settings.market_data.api_key
        self.client_id = settings.market_data.client_id
        self.password = settings.market_data.password
        self.totp_secret = settings.market_data.totp
        
        self.obj: Optional[SmartConnect] = None
        self.is_authenticated = False
        self.token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.feed_token: Optional[str] = None
        
        # Scrip master cache
        self.scrip_master = None
        self.scrip_master_loaded = False
        
        logger.info(f"Angel One client initialized for client: {self.client_id}")
    
    def login(self) -> bool:
        """
        Authenticate with Angel One SmartAPI using the official library.
        """
        if self.is_authenticated and self.obj:
            logger.info("Already authenticated")
            return True
        
        try:
            # Generate TOTP
            totp = pyotp.TOTP(self.totp_secret).now() if self.totp_secret else ""
            
            logger.info(f"Attempting login for client: {self.client_id}")
            
            # Initialize SmartConnect
            self.obj = SmartConnect(api_key=self.api_key)
            
            # Generate session
            data = self.obj.generateSession(
                clientCode=self.client_id,
                password=self.password,
                totp=totp
            )
            
            logger.debug(f"Login response: {data}")
            
            if data.get('status'):
                self.is_authenticated = True
                self.token = data.get('jwtToken')
                self.refresh_token = data.get('refreshToken')
                self.feed_token = data.get('feedToken')
                
                logger.info(f"Login successful for client: {self.client_id}")
                return True
            else:
                logger.error(f"Login failed: {data.get('message', 'Unknown error')}")
                return False
                
        except Exception as e:
            logger.error(f"Login error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _load_scrip_master(self) -> bool:
        """
        Load the scrip master from Angel One.
        """
        if self.scrip_master_loaded:
            return True
        
        try:
            url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
            logger.info("Downloading scrip master...")
            response = requests.get(url, timeout=30)
            
            if response.status_code == 200:
                self.scrip_master = response.json()
                self.scrip_master_loaded = True
                logger.info(f"Loaded {len(self.scrip_master)} symbols from scrip master")
                return True
            else:
                logger.error(f"Failed to download scrip master: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error loading scrip master: {e}")
            return False
    
    def get_symbol_token(self, symbol: str, exchange: str = "NSE") -> Optional[str]:
        """
        Get the token for a symbol from scrip master.
        """
        if not self.is_authenticated:
            if not self.login():
                return None
        
        if not self._load_scrip_master():
            return None
        
        try:
            # Search for the symbol
            results = []
            for scrip in self.scrip_master:
                if scrip.get('symbol') == symbol and scrip.get('exch_seg') == exchange:
                    results.append(scrip)
            
            if results:
                # Return the first match (or nearest expiry for options)
                token = results[0].get('token')
                logger.debug(f"Found token for {symbol}: {token}")
                return token
            else:
                logger.warning(f"Symbol {symbol} not found in scrip master")
                return None
                
        except Exception as e:
            logger.error(f"Error getting symbol token: {e}")
            return None
    
    def get_ltp(self, symbol: str, exchange: str = "NSE") -> Optional[float]:
        """
        Get last traded price for a symbol.
        """
        if not self.is_authenticated or not self.obj:
            if not self.login():
                return None
        
        try:
            # Get the symbol token
            symbol_token = self.get_symbol_token(symbol, exchange)
            if not symbol_token:
                logger.warning(f"Could not get token for {symbol}")
                return None
            
            # Get LTP
            data = self.obj.ltpData(exchange, symbol, symbol_token)
            
            if data.get('status'):
                ltp_data = data.get('data', {})
                return float(ltp_data.get('ltp', 0.0))
            else:
                logger.error(f"LTP fetch failed: {data.get('message', 'Unknown error')}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting LTP: {e}")
            return None
    
    def get_historical_data(
        self,
        symbol: str,
        exchange: str = "NSE",
        interval: str = "1d",
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        limit: Optional[int] = 100,
    ) -> List[OHLCVData]:
        """
        Fetch historical OHLCV data for a symbol using SmartAPI.
        """
        if not self.is_authenticated or not self.obj:
            if not self.login():
                return []
        
        if to_date is None:
            to_date = datetime.now()
        if from_date is None:
            from_date = to_date - timedelta(days=30)
        
        try:
            # Get the symbol token
            symbol_token = self.get_symbol_token(symbol, exchange)
            if not symbol_token:
                logger.warning(f"Could not get token for {symbol}")
                return []
            
            # Format dates
            from_str = from_date.strftime("%Y-%m-%d %H:%M")
            to_str = to_date.strftime("%Y-%m-%d %H:%M")
            
            # Map interval to SmartAPI format
            interval_map = {
                "1m": "ONE_MINUTE",
                "5m": "FIVE_MINUTE",
                "15m": "FIFTEEN_MINUTE",
                "30m": "THIRTY_MINUTE",
                "1h": "ONE_HOUR",
                "1d": "ONE_DAY",
                "1w": "ONE_WEEK",
                "1M": "ONE_MONTH",
            }
            smart_interval = interval_map.get(interval, "ONE_DAY")
            
            logger.info(f"Fetching historical data for {symbol} from {from_str} to {to_str}")
            
            # Get historical data
            data = self.obj.getCandleData(
                exchange=exchange,
                symboltoken=symbol_token,
                interval=smart_interval,
                fromdate=from_str,
                todate=to_str
            )
            
            if data.get('status'):
                ohlcv_data = []
                raw_data = data.get('data', [])
                
                for item in raw_data:
                    try:
                        # Format: [timestamp, open, high, low, close, volume]
                        if len(item) >= 6:
                            timestamp = datetime.strptime(item[0], "%Y-%m-%d %H:%M")
                            ohlcv = OHLCVData(
                                symbol=symbol,
                                timestamp=timestamp,
                                open=float(item[1]),
                                high=float(item[2]),
                                low=float(item[3]),
                                close=float(item[4]),
                                volume=float(item[5]),
                                interval=interval,
                            )
                            ohlcv_data.append(ohlcv)
                    except (ValueError, IndexError) as e:
                        logger.warning(f"Error parsing OHLCV item: {e}")
                        continue
                
                logger.info(f"Fetched {len(ohlcv_data)} data points for {symbol}")
                return ohlcv_data
            else:
                logger.error(f"Historical data fetch failed: {data.get('message', 'Unknown error')}")
                return []
                
        except Exception as e:
            logger.error(f"Error fetching historical data: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def get_feed_token(self) -> Optional[str]:
        """
        Get the feed token for WebSocket connection.
        """
        if not self.is_authenticated:
            return None
        return self.feed_token
    
    def logout(self) -> bool:
        """
        Logout from Angel One.
        """
        try:
            if self.obj:
                self.obj.logout()
            self.is_authenticated = False
            self.token = None
            logger.info("Logged out successfully")
            return True
        except Exception as e:
            logger.error(f"Error during logout: {e}")
            return False
    
    def get_scrip_master(self) -> Optional[List[Dict]]:
        """
        Get the scrip master.
        """
        if self._load_scrip_master():
            return self.scrip_master
        return None
    
    def search_symbols(self, query: str, exchange: str = "NSE") -> List[Dict]:
        """
        Search for symbols in the scrip master.
        """
        if not self._load_scrip_master():
            return []
        
        results = []
        query_lower = query.lower()
        
        for scrip in self.scrip_master:
            symbol = scrip.get('symbol', '')
            name = scrip.get('name', '')
            scrip_exchange = scrip.get('exch_seg', '')
            
            if scrip_exchange == exchange and (
                query_lower in symbol.lower() or 
                query_lower in name.lower()
            ):
                results.append(scrip)
        
        return results[:10]  # Limit results
    
    def is_token_valid(self) -> bool:
        """
        Check if the current token is valid.
        """
        return self.is_authenticated and self.token is not None