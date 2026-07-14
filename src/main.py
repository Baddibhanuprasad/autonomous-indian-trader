import time
import schedule
from typing import List
from datetime import datetime
import threading
from .agents.decision_agent import DecisionAgent
from .agents.execution_agent import ExecutionAgent
from .data.database import DatabaseManager
from .dashboard.app import run_dashboard
from .utils.config import config
from .utils.logger import setup_logger

logger = setup_logger(__name__)

class TradingSystem:
    """Main trading system orchestrator"""
    
    def __init__(self):
        self.decision_agent = DecisionAgent()
        self.execution_agent = ExecutionAgent()
        self.db = DatabaseManager()
        self.symbols = config.get('trading.symbols', [])
        self.is_running = False
        self.dashboard_thread = None
        
    def start(self):
        """Start the trading system"""
        logger.info("Starting Autonomous Indian Trading System")
        self.is_running = True
        
        # Start dashboard in separate thread
        self.dashboard_thread = threading.Thread(target=run_dashboard, daemon=True)
        self.dashboard_thread.start()
        logger.info("Dashboard started on http://localhost:8501")
        
        # Schedule tasks
        schedule.every(config.get('trading.scan_interval_seconds', 300)).seconds.do(
            self.scan_stocks
        )
        schedule.every(10).seconds.do(self.manage_positions)
        
        # Main loop
        logger.info("Trading system running...")
        while self.is_running:
            schedule.run_pending()
            time.sleep(1)
    
    def stop(self):
        """Stop the trading system"""
        logger.info("Stopping trading system")
        self.is_running = False
    
    def scan_stocks(self):
        """Scan all configured stocks"""
        logger.info(f"Scanning {len(self.symbols)} stocks")
        
        for symbol in self.symbols:
            try:
                # Make trading decision
                decision = self.decision_agent.make_decision(symbol)
                
                # Execute if BUY/SELL
                if decision['action'] in ['BUY', 'SELL']:
                    self.execution_agent.execute_trade(decision)
                    
            except Exception as e:
                logger.error(f"Error processing {symbol}: {e}")
    
    def manage_positions(self):
        """Manage open positions"""
        try:
            self.execution_agent.manage_exits()
        except Exception as e:
            logger.error(f"Error managing positions: {e}")

if __name__ == "__main__":
    system = TradingSystem()
    try:
        system.start()
    except KeyboardInterrupt:
        system.stop()
        logger.info("Trading system stopped by user")