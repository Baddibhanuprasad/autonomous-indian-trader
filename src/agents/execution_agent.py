from typing import Dict, Optional
from datetime import datetime
from ..api.dhan import DhanHQPaperTrading
from ..data.database import DatabaseManager
from ..utils.logger import setup_logger
from ..utils.config import config

logger = setup_logger(__name__)

class ExecutionAgent:
    """Agent for executing paper trades"""
    
    def __init__(self):
        self.broker = DhanHQPaperTrading()
        self.db = DatabaseManager()
        
    def execute_trade(self, decision: Dict) -> Optional[int]:
        """Execute a trade based on decision"""
        if decision['action'] == 'HOLD':
            logger.info(f"HOLD decision for {decision['symbol']}, no action taken")
            return None
        
        try:
            # Place paper trade
            order = self.broker.place_order(
                symbol=decision['symbol'],
                transaction_type=decision['action'],
                quantity=decision.get('quantity', 1),
                price=decision.get('current_price', 0),
                stoploss=decision.get('stoploss'),
                target=decision.get('target')
            )
            
            if order and order.get('status') == 'success':
                # Save to database
                trade_data = {
                    'symbol': decision['symbol'],
                    'trade_type': decision['action'],
                    'entry_price': decision.get('current_price', 0),
                    'quantity': decision.get('quantity', 1),
                    'stoploss': decision.get('stoploss', 0),
                    'target': decision.get('target', 0),
                    'news_sentiment': decision.get('news_sentiment', 'Neutral'),
                    'news_confidence': decision.get('news_confidence', 0),
                    'technical_score': decision.get('technical_score', 0),
                    'ai_reasoning': decision.get('reasoning', ''),
                    'timestamp': datetime.utcnow()
                }
                
                trade_id = self.db.save_trade(trade_data)
                logger.info(f"Trade executed: {decision['action']} {decision['symbol']} "
                          f"Qty: {decision.get('quantity')} at {decision.get('current_price')}")
                
                return trade_id
            else:
                logger.error(f"Order placement failed: {order}")
                return None
                
        except Exception as e:
            logger.error(f"Error executing trade for {decision['symbol']}: {e}")
            return None
    
    def manage_exits(self):
        """Check and manage exits for open positions"""
        open_trades = self.db.get_open_trades()
        
        for trade in open_trades:
            try:
                # Get current price from broker
                current_price = self.broker.get_current_price(trade.symbol)
                
                if current_price is None:
                    continue
                
                # Check stoploss and target
                if trade.trade_type == 'BUY':
                    if current_price <= trade.stoploss:
                        self._close_position(trade, current_price, "Stoploss hit")
                    elif current_price >= trade.target:
                        self._close_position(trade, current_price, "Target achieved")
                else:  # SELL
                    if current_price >= trade.stoploss:
                        self._close_position(trade, current_price, "Stoploss hit")
                    elif current_price <= trade.target:
                        self._close_position(trade, current_price, "Target achieved")
                        
            except Exception as e:
                logger.error(f"Error managing exit for {trade.symbol}: {e}")
    
    def _close_position(self, trade, exit_price: float, reason: str):
        """Close a position"""
        pnl = (exit_price - trade.entry_price) * trade.quantity
        if trade.trade_type == 'SELL':
            pnl = -pnl
        
        self.db.update_trade(trade.id, {
            'exit_price': exit_price,
            'pnl': pnl,
            'status': 'CLOSED'
        })
        
        logger.info(f"Position closed: {trade.symbol} {trade.trade_type} "
                   f"Exit: {exit_price} PnL: {pnl:.2f} Reason: {reason}")