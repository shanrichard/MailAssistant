"""
Logging configuration
"""
import logging
import logging.handlers
import structlog
from typing import Dict, Any
import os
import json
from pathlib import Path
from .config import settings


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter that preserves extra fields"""
    
    def format(self, record):
        log_data = {
            "timestamp": self.formatTime(record, self.datefmt),
            "name": record.name,
            "levelname": record.levelname,
            "message": record.getMessage(),
            "source": getattr(record, 'source', 'backend'),
        }
        
        # Add any extra fields from the record
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'created', 'filename', 'funcName', 
                          'levelname', 'levelno', 'lineno', 'module', 'msecs', 
                          'pathname', 'process', 'processName', 'relativeCreated', 
                          'thread', 'threadName', 'exc_info', 'exc_text', 'stack_info',
                          'getMessage', 'source', 'message']:
                log_data[key] = value
        
        # Handle exception info if present
        if record.exc_info:
            log_data['exc_info'] = self.formatException(record.exc_info)
        
        return json.dumps(log_data, ensure_ascii=False)


def setup_logging():
    """Setup structured logging with file output"""
    
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.log_level.upper()))
    
    # Remove existing handlers
    root_logger.handlers = []
    
    # Console handler (for backward compatibility)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler with rotation - JSON format for debug logs
    if settings.environment == "development":
        file_handler = logging.handlers.RotatingFileHandler(
            filename=log_dir / "app.log",
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        # Use custom JSON formatter for file logs
        file_handler.setFormatter(JSONFormatter())
        root_logger.addHandler(file_handler)
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = None) -> structlog.stdlib.BoundLogger:
    """Get structured logger"""
    return structlog.get_logger(name)


def log_frontend_error(error_data: Dict[str, Any], user_agent: str = None):
    """Log frontend error with proper structure"""
    logger = logging.getLogger("frontend")
    
    extra = {
        "source": "frontend",
        "error_type": error_data.get("type", "unknown"),
        "stack": error_data.get("stack"),
        "url": error_data.get("url"),
        "user_agent": user_agent,
        "frontend_timestamp": error_data.get("timestamp")
    }
    
    # Remove None values
    extra = {k: v for k, v in extra.items() if v is not None}
    
    logger.error(
        error_data.get("message", "Unknown frontend error"),
        extra=extra
    )


# Initialize logging
setup_logging()
logger = get_logger(__name__)