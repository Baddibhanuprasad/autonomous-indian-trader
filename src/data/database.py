from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from contextlib import contextmanager
from .models import Base
from ..utils.config import config

class DatabaseManager:
    """Database manager for trading system"""
    
    def __init__(self):
        db_config = config.settings['database']
        if db_config['type'] == 'sqlite':
            db_url = f"sqlite:///{db_config['sqlite_path']}"
        else:
            db_url = db_config['postgresql_url']
        
        self.engine = create_engine(db_url, echo=False)
        Base.metadata.create_all(self.engine)
        
        self.Session = scoped_session(sessionmaker(bind=self.engine))
    
    @contextmanager
    def session(self):
        """Provide a transactional scope"""
        session = self.Session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()
    
    def save_trade(self, trade_data: dict):
        """Save trade to database"""
        with self.session() as session:
            trade = Trade(**trade_data)
            session.add(trade)
            session.flush()
            return trade.id
    
    def update_trade(self, trade_id: int, update_data: dict):
        """Update trade in database"""
        with self.session() as session:
            session.query(Trade).filter(Trade.id == trade_id).update(update_data)
    
    def get_open_trades(self):
        """Get all open trades"""
        with self.session() as session:
            return session.query(Trade).filter(Trade.status == 'OPEN').all()
    
    def get_trade_history(self, limit=100):
        """Get trade history"""
        with self.session() as session:
            return session.query(Trade).order_by(Trade.timestamp.desc()).limit(limit).all()
    
    def get_daily_pnl(self):
        """Get today's PnL"""
        from datetime import datetime, timedelta
        today = datetime.utcnow().date()
        with self.session() as session:
            trades = session.query(Trade).filter(
                Trade.timestamp >= today,
                Trade.status == 'CLOSED'
            ).all()
            return sum(trade.pnl for trade in trades if trade.pnl)