import os
import yaml
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv

class Config:
    """Configuration manager for the trading system"""
    
    def __init__(self, config_path: str = "config/settings.yaml"):
        load_dotenv()
        
        with open(config_path, 'r') as file:
            self.settings = yaml.safe_load(file)
        
        # Load API credentials from environment
        self.credentials = {
            'angel_one': {
                'api_key': os.getenv('ANGEL_ONE_API_KEY'),
                'client_id': os.getenv('ANGEL_ONE_CLIENT_ID'),
                'password': os.getenv('ANGEL_ONE_PASSWORD'),
                'totp_secret': os.getenv('ANGEL_ONE_TOTP_SECRET')
            },
            'dhan': {
                'client_id': os.getenv('DHAN_CLIENT_ID'),
                'access_token': os.getenv('DHAN_ACCESS_TOKEN')
            },
            'ollama': {
                'base_url': os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434'),
                'model': os.getenv('OLLAMA_MODEL', 'qwen2.5:7b')
            }
        }
    
    def get(self, key: str, default=None) -> Any:
        """Get configuration value using dot notation"""
        keys = key.split('.')
        value = self.settings
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
        return value if value is not None else default

config = Config()