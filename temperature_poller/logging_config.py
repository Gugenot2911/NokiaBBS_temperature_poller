#!/usr/bin/env python3
"""
Конфигурация логирования для Temperature Poller.

Предоставляет единую систему логирования для всего проекта.
"""

import logging
import sys
from datetime import datetime
from typing import Optional


class ColoredFormatter(logging.Formatter):
    """Колорированный форматтер для консоли"""
    
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
    }
    RESET = '\033[0m'
    BOLD = '\033[1m'
    
    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{log_color}{self.BOLD}{record.levelname}{self.RESET}"
        record.msg = f"{record.msg}"
        return super().format(record)


def setup_logging(
    level: str = "info",
    log_file: Optional[str] = None,
    use_colors: bool = True
) -> logging.Logger:
    """
    Настройка системы логирования.
    
    Args:
        level: уровень логирования (debug, info, warning, error, critical)
        log_file: путь к файлу логов (опционально)
        use_colors: использовать цвета в консоли
    
    Returns:
        Корневой логгер
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    
    # Очистка старых обработчиков
    root_logger.handlers.clear()
    
    # Форматтер для консоли
    console_format = "%(asctime)s | %(levelname)-8s | %(message)s"
    console_formatter = ColoredFormatter(console_format, datefmt="%H:%M:%S") if use_colors else logging.Formatter(console_format, datefmt="%H:%M:%S")
    
    # Обработчик консоли
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # Обработчик файла (если указан)
    if log_file:
        file_format = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
        file_formatter = logging.Formatter(file_format, datefmt="%Y-%m-%d %H:%M:%S")
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
    
    return root_logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Получение именованного логгера.
    
    Args:
        name: имя логгера (например, __name__)
    
    Returns:
        Логгер с указанным именем
    """
    return logging.getLogger(name)


# Инициализация по умолчанию
if __name__ == "__main__":
    logger = setup_logging(level="debug")
    logger.debug("Debug message")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")
    logger.critical("Critical message")
