#!/usr/bin/env python3
"""
Конфигурация API сервиса.

Читает настройки из переменных окружения с дефолтными значениями.
Приоритет:
1. Переменные окружения
2. app_config.py (config.json)
3. Значения по умолчанию
"""

import os
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings


def _get_default_api_url() -> str:
    """
    Получение URL API по умолчанию.
    
    Приоритет:
    1. Переменная окружения API_BASE_URL
    2. app_config.py (config.json)
    3. Hardcoded fallback
    """
    # Сначала проверяем переменную окружения
    if os.environ.get('API_BASE_URL'):
        region_prefix = os.environ.get('REGION_PREFIX', 'NS')
        return f"{os.environ['API_BASE_URL']}/api/v1/hosts?prefix={region_prefix}"
    
    # Пытаемся получить из app_config
    try:
        from app_config import get_hosts_api_url
        return get_hosts_api_url()
    except (ImportError, Exception):
        pass
    
    # Fallback
    return "http://localhost:8001/api/v1/hosts?prefix=NS"


class APISettings(BaseSettings):
    """Настройки API сервиса"""
    
    # Сервер
    host: str = Field(default="0.0.0.0", description="Хост для绑定")
    port: int = Field(default=8000, ge=1, le=65535, description="Порт для绑定")
    reload: bool = Field(default=False, description="Перезагрузка при изменении кода")
    log_level: str = Field(default="info", description="Уровень логирования")
    
    # Polling Manager
    api_url: str = Field(
        default_factory=_get_default_api_url,
        description="URL API для получения списка хостов"
    )
    db_base_dir: str = Field(default="databases", description="Директория баз данных")
    checkpoint_path: str = Field(default="emergency_checkpoint.json", description="Путь к checkpoint")
    chunk_size: int = Field(default=10, ge=1, le=50, description="Размер чанка опроса")
    checkpoint_interval: int = Field(default=100, ge=10, description="Интервал сохранения checkpoint")
    poll_interval_hours: int = Field(default=1, ge=1, description="Интервал массового опроса (часы)")
    hosts_ttl_hours: int = Field(default=24, ge=1, description="TTL кэша хостов (часы)")
    max_checkpoint_age_hours: float = Field(default=2.0, description="Макс. возраст checkpoint (часы)")
    
    # CORS
    cors_origins: str = Field(default="*", description="Разрешённые origins (через запятую)")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Глобальный экземпляр
settings = APISettings()


def print_config():
    """Вывод текущей конфигурации"""
    print("=" * 70)
    print("🔧 КОНФИГУРАЦИЯ API СЕРВЕРА")
    print("=" * 70)
    print(f"\n📡 Сервер:")
    print(f"   Host: {settings.host}")
    print(f"   Port: {settings.port}")
    print(f"   Reload: {settings.reload}")
    print(f"   Log level: {settings.log_level}")
    print(f"\n🔄 Polling:")
    print(f"   API URL: {settings.api_url}")
    print(f"   Chunk size: {settings.chunk_size}")
    print(f"   Poll interval: {settings.poll_interval_hours}h")
    print(f"   Hosts TTL: {settings.hosts_ttl_hours}h")
    print(f"\n💾 Storage:")
    print(f"   DB dir: {settings.db_base_dir}")
    print(f"   Checkpoint: {settings.checkpoint_path}")
    print(f"   Checkpoint interval: {settings.checkpoint_interval}")
    print("=" * 70)


if __name__ == "__main__":
    print_config()
