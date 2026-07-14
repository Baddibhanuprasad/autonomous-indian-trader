from typing import Dict
from datetime import datetime
import json
from langchain_community.llms import Ollama
from langchain.prompts import PromptTemplate
from ..utils.config import config
from ..utils.logger import setup_logger
from ..agents.news_agent import NewsAgent
from ..agents.technical_agent import TechnicalAgent
from ..agents.risk_agent import RiskAgent

logger = setup_logger(__name__)

class DecisionAgent:
    """Agent for making trading decisions"""
    
    def __init__(self):
        self.llm = Ollama(
            model=config.get('ollama.model'),
            base_url=config.get('ollama.base_url')
        )
        self.news_agent = NewsAgent()
        self.technical_agent = TechnicalAgent()
        self.risk_agent = RiskAgent()
        
    def make_decision(self, symbol: str) -> Dict:
        """Make trading decision for a symbol"""
        try:
            # Gather all inputs
            logger.info(f"Making decision for {symbol}")
            
            # 1. Get news sentiment
            news_analysis = self.news_agent.process_news_for_symbol(symbol)
            logger.info(f"News sentiment for {symbol}: {news_analysis['sentiment']}")
            
            # 2. Get technical analysis
            technical_analysis = self.technical_agent.analyze(symbol)
            logger.info(f"Technical score for {symbol}: {technical_analysis['score']}")
            
            # 3. Generate AI reasoning
            decision = self._ai_decision(symbol, news_analysis, technical_analysis)
            
            # 4. Validate with risk management
            if decision['action'] in ['BUY', 'SELL']:
                risk_evaluation = self.risk_agent.evaluate_trade(
                    entry_price=technical_analysis['current_price'],
                    atr=technical_analysis['atr'],
                    trade_type=decision['action'],
                    technical_score=technical_analysis['score']
                )
                
                if not risk_evaluation['approved']:
                    decision['action'] = 'HOLD'
                    decision['reasoning'] += f"\nRisk rejected: {risk_evaluation['rejection_reason']}"
                else:
                    decision.update(risk_evaluation)
            
            decision['symbol'] = symbol
            decision['timestamp'] = datetime.utcnow()
            decision['news_sentiment'] = news_analysis['sentiment']
            decision['technical_score'] = technical_analysis['score']
            
            return decision
            
        except Exception as e:
            logger.error(f"Error making decision for {symbol}: {e}")
            return {
                'symbol': symbol,
                'action': 'HOLD',
                'reasoning': f"Error in decision process: {str(e)}",
                'confidence': 0,
                'timestamp': datetime.utcnow()
            }
    
    def _ai_decision(self, symbol: str, news: Dict, technical: Dict) -> Dict:
        """Use AI to make trading decision"""
        prompt_template = PromptTemplate(
            input_variables=["symbol", "news_sentiment", "news_confidence", 
                           "tech_score", "tech_signals", "current_price"],
            template="""
            You are an expert Indian stock market trader. Based on the following information, 
            decide whether to BUY, SELL, or HOLD the stock.
            
            Stock: {symbol}
            Current Price: {current_price}
            
            News Analysis:
            - Sentiment: {news_sentiment}
            - Confidence: {news_confidence}%
            
            Technical Analysis:
            - Score: {tech_score}/100
            - Signals: {tech_signals}
            
            Decision Rules:
            - BUY if both news is Bullish AND technical score > 60
            - SELL if both news is Bearish AND technical score < 40
            - HOLD in all other cases
            
            Provide your decision in JSON format:
            {{
                "action": "BUY/SELL/HOLD",
                "confidence": 0-100,
                "reasoning": "detailed explanation"
            }}
            """
        )
        
        try:
            response = self.llm.invoke(prompt_template.format(
                symbol=symbol,
                news_sentiment=news['sentiment'],
                news_confidence=news['confidence'],
                tech_score=technical['score'],
                tech_signals=", ".join(technical.get('signals', [])),
                current_price=technical['current_price']
            ))
            
            # Parse JSON response
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            if start_idx != -1 and end_idx != 0:
                json_str = response[start_idx:end_idx]
                decision = json.loads(json_str)
                return decision
                
        except Exception as e:
            logger.error(f"Error in AI decision: {e}")
        
        # Fallback to simple rules
        action = 'HOLD'
        confidence = 50
        
        if news['sentiment'] == 'Bullish' and technical['score'] > 60:
            action = 'BUY'
            confidence = min(news['confidence'], technical['score'])
        elif news['sentiment'] == 'Bearish' and technical['score'] < 40:
            action = 'SELL'
            confidence = min(news['confidence'], 100 - technical['score'])
        
        return {
            "action": action,
            "confidence": confidence,
            "reasoning": f"Fallback decision based on rules. News: {news['sentiment']}, Technical Score: {technical['score']}"
        }