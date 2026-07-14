from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np
from ..data.database import DatabaseManager
from ..utils.config import config
from ..utils.logger import setup_logger

logger = setup_logger(__name__)

class RiskAgent:
    """Agent for risk management"""
    
    def __init__(self):
        self.db = DatabaseManager()
        self.max_risk_pct = config.get('risk.max_risk_per_trade_pct', 1.0) / 100
        self.max_daily_loss_pct = config.get('risk.max_daily_loss_pct', 3.0) / 100
        self.min_rr_ratio = config.get('risk.min_risk_reward_ratio', 2.0)
        self.atr_multiplier = config.get('risk.atr_multiplier_stoploss', 2.0)
        self.max_positions = config.get('risk.max_positions', 5)
        self.initial_capital = 1000000  # 10 lakhs paper trading capital
        
    def check_daily_loss_limit(self) -> bool:
        """Check if daily loss limit has been hit"""
        today = datetime.utcnow().date()
        with self.db.session() as session:
            trades = session.query(Trade).filter(
                Trade.timestamp >= today,
                Trade.status == 'CLOSED'
            ).all()
            
            total_pnl = sum(trade.pnl for trade in trades if trade.pnl)
            
            if total_pnl < -self.initial_capital * self.max_daily_loss_pct:
                logger.warning(f"Daily loss limit hit. PnL: {total_pnl}")
                return False
            
            return True
    
    def calculate_position_size(self, capital: float, entry_price: float, 
                               stoploss: float) -> int:
        """Calculate position size based on risk parameters"""
        risk_amount = capital * self.max_risk_pct
        risk_per_share = abs(entry_price - stoploss)
        
        if risk_per_share == 0:
            return 0
        
        quantity = int(risk_amount / risk_per_share)
        
        # Round down to nearest lot size (for F&O) or 1 for equities
        return max(1, quantity)
    
    def calculate_stoploss_target(self, entry_price: float, atr: float, 
                                 trade_type: str) -> Tuple[float, float]:
        """Calculate dynamic stoploss and target"""
        if trade_type == 'BUY':
            stoploss = entry_price - (self.atr_multiplier * atr)
            target = entry_price + (self.atr_multiplier * self.min_rr_ratio * atr)
        else:  # SELL
            stoploss = entry_price + (self.atr_multiplier * atr)
            target = entry_price - (self.atr_multiplier * self.min_rr_ratio * atr)
        
        return stoploss, target
    
    def get_current_capital(self) -> float:
        """Calculate current available capital"""
        with self.db.session() as session:
            # Start with initial capital
            capital = self.initial_capital
            
            # Subtract open positions value
            open_trades = session.query(Trade).filter(Trade.status == 'OPEN').all()
            for trade in open_trades:
                capital -= trade.quantity * trade.entry_price
            
            # Add closed PnL
            closed_trades = session.query(Trade).filter(Trade.status == 'CLOSED').all()
            for trade in closed_trades:
                if trade.pnl:
                    capital += trade.pnl
            
            return capital
    
    def can_take_trade(self) -> bool:
        """Check if we can take new trades"""
        # Check daily loss limit
        if not self.check_daily_loss_limit():
            return False
        
        # Check number of open positions
        with self.db.session() as session:
            open_positions = session.query(Trade).filter(Trade.status == 'OPEN').count()
            if open_positions >= self.max_positions:
                logger.info(f"Maximum positions reached: {open_positions}")
                return False
        
        # Check available capital
        capital = self.get_current_capital()
        if capital < self.initial_capital * 0.1:  # At least 10% capital available
            logger.warning("Insufficient capital")
            return False
        
        return True
    
    def evaluate_trade(self, entry_price: float, atr: float, 
                      trade_type: str, technical_score: float) -> Dict:
        """Evaluate if trade meets risk criteria"""
        stoploss, target = self.calculate_stoploss_target(entry_price, atr, trade_type)
        capital = self.get_current_capital()
        quantity = self.calculate_position_size(capital, entry_price, stoploss)
        
        # Check risk-reward
        risk = abs(entry_price - stoploss)
        reward = abs(target - entry_price)
        rr_ratio = reward / risk if risk > 0 else 0
        
        # Check if technical score meets minimum threshold
        min_tech_score = 60
        
        approved = (
            self.can_take_trade() and
            rr_ratio >= self.min_rr_ratio and
            technical_score >= min_tech_score
        )
        
        return {
            "approved": approved,
            "quantity": quantity,
            "stoploss": stoploss,
            "target": target,
            "risk_reward_ratio": rr_ratio,
            "max_risk_amount": capital * self.max_risk_pct,
            "rejection_reason": None if approved else self._get_rejection_reason(
                rr_ratio, technical_score, min_tech_score
            )
        }
    
    def _get_rejection_reason(self, rr_ratio: float, tech_score: float, 
                             min_score: float) -> str:
        """Get reason for trade rejection"""
        reasons = []
        if not self.can_take_trade():
            reasons.append("Trading limits reached")
        if rr_ratio < self.min_rr_ratio:
            reasons.append(f"Poor risk-reward ratio: {rr_ratio:.2f}")
        if tech_score < min_score:
            reasons.append(f"Low technical score: {tech_score:.0f}")
        return ", ".join(reasons) if reasons else "Unknown reason"