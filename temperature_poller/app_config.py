#!/usr/bin/env python3
"""
Конфигурация приложения.

Читает настройки из config.json и переопределяет переменными окружения.
"""

import json
import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field


@dataclass
class RegionConfig:
    """Конфигурация региона"""
    prefix: str = "NS"
    name: str = "North Station"


@dataclass
class APIConfig:
    """Конфигурация API"""
    base_url: str = "http://localhost:8001"
    hosts_endpoint: str = "/api/v1/hosts"
    
    @property
    def hosts_url(self) -> str:
        """Полный URL для получения списка хостов"""
        return f"{self.base_url}{self.hosts_endpoint}"


@dataclass
class PollingConfig:
    """Конфигурация опроса"""
    chunk_size: int = 10
    checkpoint_interval: int = 100
    poll_interval_hours: int = 1
    hosts_ttl_hours: int = 24
    max_checkpoint_age_hours: float = 2.0


@dataclass
class DatabaseConfig:
    """Конфигурация базы данных"""
    base_dir: str = "databases"
    auto_cleanup_days: int = 60


@dataclass
class CheckpointConfig:
    """Конфигурация checkpoint"""
    path: str = "emergency_checkpoint.json"


@dataclass
class AppConfig:
    """Полная конфигурация приложения"""
    region: RegionConfig = field(default_factory=RegionConfig)
    api: APIConfig = field(default_factory=APIConfig)
    polling: PollingConfig = field(default_factory=PollingConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    checkpoint: CheckpointConfig = field(default_factory=CheckpointConfig)
    
    def get_hosts_api_url(self) -> str:
        """Получение URL API для получения хостов с учётом префикса региона"""
        # Добавляем параметр prefix к URL
        base_url = self.api.hosts_url
        separator = "&" if "?" in base_url else "?"
        return f"{base_url}{separator}prefix={self.region.prefix}"


class ConfigLoader:
    """Загрузчик конфигурации"""
    
    def __init__(self, config_path: str = "config.json"):
        """
        Инициализация загрузчика конфигурации.
        
        Args:
            config_path: путь к файлу конфигурации
        """
        self.config_path = Path(config_path)
        self._config: Optional[AppConfig] = None
    
    def load(self) -> AppConfig:
        """
        Загрузка конфигурации из файла.
        
        Чтение происходит в следующем порядке приоритета:
        1. Значения по умолчанию
        2. Значения из config.json
        3. Переопределение через переменные окружения
        
        Returns:
            AppConfig: загруженная конфигурация
        
        Raises:
            FileNotFoundError: если файл конфигурации не найден
            json.JSONDecodeError: если файл содержит невалидный JSON
        """
        # По умолчанию
        config = AppConfig()
        
        # Загрузка из файла
        if self.config_path.exists():
            with open(self.config_path, 'r', encoding='utf-8') as f:
                file_config = json.load(f)
            
            # Область региона
            if 'region' in file_config:
                region = file_config['region']
                config.region.prefix = region.get('prefix', config.region.prefix)
                config.region.name = region.get('name', config.region.name)
            
            # Область API
            if 'api' in file_config:
                api = file_config['api']
                config.api.base_url = api.get('base_url', config.api.base_url)
                config.api.hosts_endpoint = api.get('hosts_endpoint', config.api.hosts_endpoint)
            
            # Область опроса
            if 'polling' in file_config:
                polling = file_config['polling']
                config.polling.chunk_size = polling.get('chunk_size', config.polling.chunk_size)
                config.polling.checkpoint_interval = polling.get('checkpoint_interval', config.polling.checkpoint_interval)
                config.polling.poll_interval_hours = polling.get('poll_interval_hours', config.polling.poll_interval_hours)
                config.polling.hosts_ttl_hours = polling.get('hosts_ttl_hours', config.polling.hosts_ttl_hours)
                config.polling.max_checkpoint_age_hours = polling.get('max_checkpoint_age_hours', config.polling.max_checkpoint_age_hours)
            
            # Область БД
            if 'database' in file_config:
                database = file_config['database']
                config.database.base_dir = database.get('base_dir', config.database.base_dir)
                config.database.auto_cleanup_days = database.get('auto_cleanup_days', config.database.auto_cleanup_days)
            
            # Область checkpoint
            if 'checkpoint' in file_config:
                checkpoint = file_config['checkpoint']
                config.checkpoint.path = checkpoint.get('path', config.checkpoint.path)
        
        # Переопределение через переменные окружения
        if os.environ.get('REGION_PREFIX'):
            config.region.prefix = os.environ['REGION_PREFIX']
        
        if os.environ.get('API_BASE_URL'):
            config.api.base_url = os.environ['API_BASE_URL']
        
        if os.environ.get('DB_BASE_DIR'):
            config.database.base_dir = os.environ['DB_BASE_DIR']
        
        # Сохранение в кэш
        self._config = config
        
        return config
    
    def get(self) -> AppConfig:
        """
        Получить конфигурацию (с кэшированием).
        
        Returns:
            AppConfig: конфигурация приложения
        """
        if self._config is None:
            self._config = self.load()
        return self._config
    
    def reload(self) -> AppConfig:
        """
        Принудительная перезагрузка конфигурации.
        
        Returns:
            AppConfig: обновлённая конфигурация
        """
        self._config = None
        return self.load()
    
    def print_config(self):
        """Вывод текущей конфигурации"""
        config = self.get()
        
        print("=" * 70)
        print("🔧 КОНФИГУРАЦИЯ ПРИЛОЖЕНИЯ")
        print("=" * 70)
        print(f"\n📍 Регион:")
        print(f"   Префикс: {config.region.prefix}")
        print(f"   Название: {config.region.name}")
        print(f"\n📡 API:")
        print(f"   Base URL: {config.api.base_url}")
        print(f"   Hosts URL: {config.get_hosts_api_url()}")
        print(f"\n🔄 Опрос:")
        print(f"   Размер чанка: {config.polling.chunk_size}")
        print(f"   Интервал сохранения checkpoint: {config.polling.checkpoint_interval}")
        print(f"   Интервал опроса: {config.polling.poll_interval_hours}ч")
        print(f"   TTL кэша хостов: {config.polling.hosts_ttl_hours}ч")
        print(f"\n💾 База данных:")
        print(f"   Директория: {config.database.base_dir}")
        print(f"   Автоочистка: {config.database.auto_cleanup_days}д")
        print(f"\n🔒 Checkpoint:")
        print(f"   Путь: {config.checkpoint.path}")
        print("=" * 70)


# =============================================================================
# Глобальный экземпляр
# =============================================================================

_config_loader: Optional[ConfigLoader] = None


def get_config(config_path: str = "config.json") -> AppConfig:
    """
    Получить глобальный экземпляр конфигурации.
    
    Args:
        config_path: путь к файлу конфигурации
    
    Returns:
        AppConfig: конфигурация приложения
    """
    global _config_loader
    if _config_loader is None or _config_loader.config_path != Path(config_path):
        _config_loader = ConfigLoader(config_path)
    return _config_loader.get()


def reload_config() -> AppConfig:
    """
    Перезагрузить конфигурацию.
    
    Returns:
        AppConfig: обновлённая конфигурация
    """
    global _config_loader
    if _config_loader is not None:
        return _config_loader.reload()
    return get_config()


def get_hosts_api_url() -> str:
    """
    Получить URL API для получения хостов.
    
    Returns:
        str: URL с параметром prefix региона
    """
    config = get_config()
    return config.get_hosts_api_url()


# =============================================================================
# Пример использования
# =============================================================================

if __name__ == "__main__":
    loader = ConfigLoader()
    loader.print_config()
    
    print("\n🔧 Примеры использования в коде:")
    print(f"   from app_config import get_config")
    config = get_config()
    print(f"   config = get_config()")
    print(f"   print(config.region.prefix)  # '{config.region.prefix}'")
    print(f"   print(config.get_hosts_api_url())  # '{config.get_hosts_api_url()}'")
