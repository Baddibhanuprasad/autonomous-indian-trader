import requests
from typing import Dict, Optional
from datetime import datetime
from ..utils.config import config
from ..utils.logger import setup_logger

logger = setup_logger(__name__)

class DhanHQPaperTrading:
    """DhanHQ Paper Trading API"""
    
    def __init__(self):
        self.client_id = config.credentials['dhan']['client_id']
        self.access_token = config.credentials['dhan']['access_token']
        self.base_url = "https://api.dhan.co"
        
    def place_order(self, symbol: str, transaction_type: str, 
                   quantity: int, price: float, stoploss: float = None,
                   target: float = None) -> Dict:
        """Place a paper trade order"""
        try:
            # Paper trading - simulate order placement
            order_id = f"PAPER_{datetime.utcnow().timestamp()}"
            
            order = {
                "order_id": order_id,
                "status": "success",
                "symbol": symbol,
                "transaction_type": transaction_type,
                "quantity": quantity,
                "price": price,
                "stoploss": stoploss,
                "target": target,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            logger.info(f"Paper trade placed: {order}")
            return order
            
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return {"status": "error", "message": str(e)}
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price for a symbol"""
        # Paper trading - simulate price
        import random
        base_price = 1000  # Base price for simulation
        return base_price + random.uniform(-50, 50)