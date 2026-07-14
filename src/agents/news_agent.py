import feedparser
import requests
from typing import List, Dict, Optional
from datetime import datetime
import json
from langchain_community.llms import Ollama
from langchain.prompts import PromptTemplate
from ..utils.config import config
from ..utils.logger import setup_logger
from ..data.database import DatabaseManager

logger = setup_logger(__name__)

class NewsAgent:
    """Agent for collecting and analyzing news"""
    
    def __init__(self):
        self.llm = Ollama(
            model=config.get('ollama.model'),
            base_url=config.get('ollama.base_url')
        )
        self.db = DatabaseManager()
        self.news_feeds = config.get('news.rss_feeds', [])
        
    def fetch_rss_news(self) -> List[Dict]:
        """Fetch news from RSS feeds"""
        news_items = []
        
        for feed_url in self.news_feeds:
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries[:5]:  # Get latest 5 entries
                    news_items.append({
                        'source': feed.feed.title if 'title' in feed.feed else feed_url,
                        'title': entry.title,
                        'content': entry.get('summary', entry.get('description', '')),
                        'url': entry.link,
                        'timestamp': datetime.utcnow()
                    })
            except Exception as e:
                logger.error(f"Error fetching feed {feed_url}: {e}")
                
        return news_items
    
    def fetch_nse_announcements(self, symbol: str) -> List[Dict]:
        """Fetch NSE corporate announcements"""
        try:
            url = config.get('news.nse_announcements_url')
            # Note: NSE API requires specific headers and cookies
            headers = {
                'User-Agent': 'Mozilla/5.0',
                'Accept': 'application/json'
            }
            # This is a simplified version - real implementation needs session management
            response = requests.get(f"{url}?symbol={symbol}", headers=headers)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.error(f"Error fetching NSE announcements for {symbol}: {e}")
        return []
    
    def analyze_sentiment(self, text: str) -> Dict:
        """Analyze sentiment using Ollama"""
        prompt_template = PromptTemplate(
            input_variables=["text"],
            template="""
            Analyze the following financial news and provide:
            1. Sentiment (Bullish/Bearish/Neutral)
            2. Confidence score (0-100)
            3. Key points summary
            4. Impact on stock price (Positive/Negative/Neutral)
            
            News: {text}
            
            Respond in JSON format:
            {{
                "sentiment": "Bullish/Bearish/Neutral",
                "confidence": 0-100,
                "summary": "brief summary",
                "impact": "Positive/Negative/Neutral"
            }}
            """
        )
        
        try:
            response = self.llm.invoke(prompt_template.format(text=text[:2000]))
            # Parse JSON response
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            if start_idx != -1 and end_idx != 0:
                json_str = response[start_idx:end_idx]
                return json.loads(json_str)
        except Exception as e:
            logger.error(f"Error analyzing sentiment: {e}")
        
        return {
            "sentiment": "Neutral",
            "confidence": 50,
            "summary": "Unable to analyze",
            "impact": "Neutral"
        }
    
    def process_news_for_symbol(self, symbol: str) -> Dict:
        """Process all news for a symbol"""
        all_news = self.fetch_rss_news()
        all_news.extend(self.fetch_nse_announcements(symbol))
        
        # Filter news related to symbol
        relevant_news = [
            news for news in all_news 
            if symbol.lower() in news['title'].lower() or 
               symbol.lower() in news['content'].lower()
        ]
        
        if not relevant_news:
            return {
                "sentiment": "Neutral",
                "confidence": 0,
                "summary": "No relevant news found",
                "articles": []
            }
        
        # Analyze sentiment for each news item
        sentiments = []
        for news in relevant_news:
            analysis = self.analyze_sentiment(news['title'] + " " + news['content'])
            sentiments.append(analysis)
            
            # Save to database
            news_data = {
                'source': news['source'],
                'title': news['title'],
                'content': news['content'],
                'url': news['url'],
                'symbols': json.dumps([symbol]),
                'sentiment': analysis['sentiment'],
                'confidence': analysis['confidence'],
                'summary': analysis['summary']
            }
            with self.db.session() as session:
                session.add(NewsItem(**news_data))
        
        # Aggregate sentiment
        bullish_count = sum(1 for s in sentiments if s['sentiment'] == 'Bullish')
        bearish_count = sum(1 for s in sentiments if s['sentiment'] == 'Bearish')
        
        if bullish_count > bearish_count:
            overall_sentiment = "Bullish"
            confidence = sum(s['confidence'] for s in sentiments if s['sentiment'] == 'Bullish') / max(bullish_count, 1)
        elif bearish_count > bullish_count:
            overall_sentiment = "Bearish"
            confidence = sum(s['confidence'] for s in sentiments if s['sentiment'] == 'Bearish') / max(bearish_count, 1)
        else:
            overall_sentiment = "Neutral"
            confidence = 50
        
        return {
            "sentiment": overall_sentiment,
            "confidence": confidence,
            "summary": f"Analyzed {len(relevant_news)} news articles. {bullish_count} bullish, {bearish_count} bearish",
            "articles": sentiments
        }