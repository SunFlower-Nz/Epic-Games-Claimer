# -*- coding: utf-8 -*-
"""
Enhanced logging for Epic Games Claimer.

Provides structured logging with:
- Console and file output
- Date-organized log files (YYYY/MM/DD.txt)
- Detailed context for debugging
- Emoji indicators for quick scanning
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, Any


class Logger:
    """Enhanced logger with context support and organized file output."""
    
    def __init__(self, log_base_dir: Optional[str] = None, name: str = 'EpicGamesClaimer'):
        """
        Initialize the logger.
        
        Args:
            log_base_dir: Base directory for log files (default: logs/).
            name: Logger name for identification.
        """
        self.log_base_dir = Path(log_base_dir) if log_base_dir else Path('logs')
        self.name = name
        self._logger = self._setup_logger()
    
    def _get_log_file_path(self) -> Path:
        """
        Get log file path organized by date (YYYY/MM/DD.txt).
        
        Returns:
            Path to today's log file.
        """
        now = datetime.now()
        log_dir = self.log_base_dir / now.strftime('%Y') / now.strftime('%m')
        log_dir.mkdir(parents=True, exist_ok=True)
        return log_dir / f"{now.strftime('%d')}.txt"
    
    def _setup_logger(self) -> logging.Logger:
        """
        Configure logger with file and console handlers.
        
        Returns:
            Configured logger instance.
        """
        # Create logger
        logger = logging.getLogger(self.name)
        logger.setLevel(logging.DEBUG)
        
        # Clear existing handlers
        logger.handlers.clear()
        
        # Log format with timestamp and level
        formatter = logging.Formatter(
            fmt='%(asctime)s [%(levelname)-8s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Console handler (INFO and above)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # File handler (DEBUG and above for detailed logs)
        try:
            file_handler = logging.FileHandler(
                self._get_log_file_path(),
                encoding='utf-8',
                mode='a'
            )
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            logger.warning(f"⚠️  Could not create log file: {e}")
        
        return logger
    
    @property
    def logger(self) -> logging.Logger:
        """Get the underlying logger instance."""
        return self._logger
    
    # -------------------------------------------------------------------------
    # Convenience methods with context
    # -------------------------------------------------------------------------
    
    def header(self, title: str) -> None:
        """Log a section header."""
        separator = "=" * 70
        self._logger.info(separator)
        self._logger.info(f"  {title}")
        self._logger.info(separator)
    
    def subheader(self, title: str) -> None:
        """Log a subsection header."""
        self._logger.info(f"\n{'─' * 50}")
        self._logger.info(f"  {title}")
        self._logger.info(f"{'─' * 50}")
    
    def success(self, message: str, **context: Any) -> None:
        """Log a success message with optional context."""
        ctx = self._format_context(context)
        self._logger.info(f"✅ {message}{ctx}")
    
    def info(self, message: str, **context: Any) -> None:
        """Log an info message with optional context."""
        ctx = self._format_context(context)
        self._logger.info(f"ℹ️  {message}{ctx}")
    
    def warning(self, message: str, **context: Any) -> None:
        """Log a warning message with optional context."""
        ctx = self._format_context(context)
        self._logger.warning(f"⚠️  {message}{ctx}")
    
    def error(self, message: str, exc: Optional[Exception] = None, **context: Any) -> None:
        """Log an error message with optional exception and context.
        When `exc` is provided, logs full stacktrace for easier reproduction.
        """
        ctx = self._format_context(context)
        if exc:
            # .exception logs the traceback automatically
            self._logger.exception(f"❌ {message}{ctx}")
        else:
            self._logger.error(f"❌ {message}{ctx}")
    
    def debug(self, message: str, **context: Any) -> None:
        """Log a debug message (file only by default)."""
        ctx = self._format_context(context)
        self._logger.debug(f"🔍 {message}{ctx}")
    
    def game(self, action: str, title: str, **context: Any) -> None:
        """Log a game-related action with context."""
        ctx = self._format_context(context)
        self._logger.info(f"🎮 {action}: {title}{ctx}")
    
    def auth(self, message: str, **context: Any) -> None:
        """Log authentication-related message."""
        ctx = self._format_context(context)
        self._logger.info(f"🔐 {message}{ctx}")
    
    def network(self, method: str, url: str, status: Optional[int] = None, **context: Any) -> None:
        """Log network request details."""
        status_str = f" → {status}" if status else ""
        ctx = self._format_context(context)
        self._logger.debug(f"🌐 {method} {url}{status_str}{ctx}")
    
    def _format_context(self, context: dict) -> str:
        """Format context dictionary for log output."""
        if not context:
            return ""
        parts = [f"{k}={v}" for k, v in context.items() if v is not None]
        return f" [{', '.join(parts)}]" if parts else ""
    
    def summary(self, claimed: int, failed: int, already_owned: int = 0) -> None:
        """Log execution summary."""
        self._logger.info("")
        self.subheader("📊 RESUMO DA EXECUÇÃO")
        self._logger.info(f"   ✅ Resgatados:   {claimed}")
        self._logger.info(f"   📦 Já possuídos: {already_owned}")
        self._logger.info(f"   ❌ Falhas:       {failed}")
        self._logger.info("─" * 50)
