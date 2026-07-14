from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import json

Base = declarative_base()

class Trade(Base):
    __tablename__ = 'trades'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    symbol = Column(String(50), nullable=False)
    trade_type = Column(String(10), nullable=False)  # BUY or SELL
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float, nullable=True)
    quantity = Column(Integer, nullable=False)
    stoploss = Column(Float, nullable=False)
    target = Column(Float, nullable=False)
    pnl = Column(Float, nullable=True)
    status = Column(String(20), default='OPEN')  # OPEN, CLOSED, CANCELLED
    news_sentiment = Column(String(20), nullable=True)  # Bullish, Bearish, Neutral
    news_confidence = Column(Float, nullable=True)
    technical_score = Column(Float, nullable=True)
    ai_reasoning = Column(Text, nullable=True)
    
class NewsItem(Base):
    __tablename__ = 'news_items'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    source = Column(String(100))
    title = Column(String(500))
    content = Column(Text)
    url = Column(String(500))
    symbols = Column(String(500))  # JSON array of symbols
    sentiment = Column(String(20))
    confidence = Column(Float)
    summary = Column(Text)
    
class MarketData(Base):
    __tablename__ = 'market_data'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    symbol = Column(String(50), nullable=False)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Integer)
    ema_9 = Column(Float)
    ema_21 = Column(Float)
    ema_50 = Column(Float)
    rsi = Column(Float)
    atr = Column(Float)
    vwap = Column(Float)
    macd = Column(Float)
    macd_signal = Column(Float)
    support = Column(Float)
    resistance = Column(Float)
    technical_score = Column(Float)