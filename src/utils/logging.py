"""
Logging configuration for the AI Case Conference system.
"""

import logging
import os
import sys
from pathlib import Path


def setup_logging(
    level: str = None,
    log_file: str = None,
) -> logging.Logger:
    """
    Set up logging for the application.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR). Defaults to env var or INFO.
        log_file: Optional file path to write logs to.
    
    Returns:
        Configured logger instance
    """
    # Get level from environment or parameter
    level = level or os.getenv("LOG_LEVEL", "INFO")
    level_num = getattr(logging, level.upper(), logging.INFO)
    
    # Create logger
    logger = logging.getLogger("dialectic")
    logger.setLevel(level_num)
    
    # Clear any existing handlers
    logger.handlers = []
    
    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level_num)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (optional)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_path)
        file_handler.setLevel(level_num)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str = None) -> logging.Logger:
    """
    Get a logger instance.
    
    Args:
        name: Optional name suffix for the logger
    
    Returns:
        Logger instance
    """
    if name:
        return logging.getLogger(f"dialectic.{name}")
    return logging.getLogger("dialectic")

