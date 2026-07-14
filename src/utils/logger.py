import logging
import colorlog
from pathlib import Path
from ..utils.config import config

def setup_logger(name: str) -> logging.Logger:
    """Setup logger with colored output"""
    
    # Create logger
    logger = logging.getLogger(name)
    
    # Get configuration
    log_config = config.settings.get('logging', {})
    log_level = getattr(logging, log_config.get('level', 'INFO'))
    log_file = log_config.get('file', 'logs/trading.log')
    log_format = log_config.get('format', 
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Set level
    logger.setLevel(log_level)
    
    # Create formatters
    file_formatter = logging.Formatter(log_format)
    
    color_formatter = colorlog.ColoredFormatter(
        "%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        }
    )
    
    # File handler
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(log_level)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(color_formatter)
    console_handler.setLevel(log_level)
    
    # Add handlers
    if not logger.handlers:
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
    
    return logger