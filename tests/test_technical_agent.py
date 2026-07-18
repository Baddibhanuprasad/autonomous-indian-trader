import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from src.agents.technical_agent import TechnicalAgent

@pytest.fixture
def technical_agent():
    return TechnicalAgent()

@pytest.fixture
def sample_data():
    """Create sample OHLCV data"""
    dates = pd.date_range(end=datetime.now(), periods=100, freq='15min')
    data = {
        'open': np.random.randn(100).cumsum() + 100,
        'high': np.random.randn(100).cumsum() + 102,
        'low': np.random.randn(100).cumsum() + 98,
        'close': np.random.randn(100).cumsum() + 100,
        'volume': np.random.randint(1000, 10000, 100)
    }
    df = pd.DataFrame(data, index=dates)
    return df

def test_calculate_indicators(technical_agent, sample_data):
    """Test indicator calculation"""
    df = technical_agent.calculate_indicators(sample_data)
    
    assert 'ema_9' in df.columns
    assert 'ema_21' in df.columns
    assert 'rsi' in df.columns
    assert 'atr' in df.columns
    assert 'macd' in df.columns
    assert 'vwap' in df.columns
    
    # Check no NaN values in last row
    last_row = df.iloc[-1]
    assert not last_row['rsi'] is np.nan
    assert not last_row['atr'] is np.nan

def test_detect_support_resistance(technical_agent, sample_data):
    """Test support/resistance detection"""
    df = technical_agent.calculate_indicators(sample_data)
    support, resistance = technical_agent.detect_support_resistance(df)
    
    assert support < resistance
    assert support > 0
    assert resistance > 0

def test_generate_technical_score(technical_agent, sample_data):
    """Test technical score generation"""
    df = technical_agent.calculate_indicators(sample_data)
    analysis = technical_agent.generate_technical_score(df)
    
    assert 'score' in analysis
    assert 0 <= analysis['score'] <= 100
    assert 'signals' in analysis
    assert isinstance(analysis['signals'], list)
    assert 'support' in analysis
    assert 'resistance' in analysis

def test_analyze_complete(technical_agent):
    """Test complete analysis pipeline"""
    # Mock the fetch_ohlcv method
    technical_agent.fetch_ohlcv = lambda symbol: sample_data()
    
    result = technical_agent.analyze("RELIANCE")
    
    assert result is not None
    assert 'score' in result
    assert 'symbol' in result
    assert result['symbol'] == "RELIANCE"