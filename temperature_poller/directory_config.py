#!/usr/bin/env python3
"""
Кроссплатформенная конфигурация директорий.

Определяет стандартные пути для данных, кэша и логов на всех платформах.
"""

import os
import sys
import tempfile
from pathlib import Path
from typing import Optional


class DirectoryConfig:
    """Конфигурация директорий приложения"""
    
    def __init__(self, app_name: str = "temperature_poller"):
        """
        Инициализация конфигурации директорий.
        
        Args:
            app_name: имя приложения
        """
        self.app_name = app_name
        self._init_directories()
    
    def _init_directories(self) -> None:
        """Инициализация путей к директориям"""
        
        # ✅ КРОССПЛАТФОРМЕННО: определяем базовую директорию
        if sys.platform == 'win32':
            # Windows
            self._app_data = Path(os.environ.get('APPDATA', Path.home() / 'AppData' / 'Roaming'))
            self._local_app_data = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData' / 'Local'))
            self._platform = 'windows'
        elif sys.platform == 'darwin':
            # macOS
            self._app_data = Path.home() / 'Library' / 'Application Support'
            self._local_app_data = Path.home() / 'Library' / 'Caches'
            self._platform = 'macos'
        else:
            # Linux и другие
            self._app_data = Path.home() / '.local' / 'share'
            self._local_app_data = Path.home() / '.cache'
            self._platform = 'linux'
        
        # Основные директории
        self.base_dir = self._app_data / self.app_name
        self.db_dir = self.base_dir / "databases"
        self.cache_dir = self._local_app_data / self.app_name / "cache"
        self.log_dir = self._get_log_dir()
        self.checkpoint_dir = self.base_dir / "checkpoints"
        self.temp_dir = Path(tempfile.gettempdir()) / self.app_name
    
    def _get_log_dir(self) -> Path:
        """Определение директории для логов"""
        if sys.platform == 'win32':
            return self._local_app_data / self.app_name / "logs"
        elif sys.platform == 'darwin':
            return Path.home() / 'Library' / 'Logs' / self.app_name
        else:
            return self.base_dir / "logs"
    
    def ensure_directories(self) -> None:
        """Создание всех директорий если они не существуют"""
        import tempfile
        
        dirs = [
            self.base_dir,
            self.db_dir,
            self.cache_dir,
            self.log_dir,
            self.checkpoint_dir,
            self.temp_dir
        ]
        
        for dir_path in dirs:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    # -------------------------------------------------------------------------
    # Геттеры для директорий
    # -------------------------------------------------------------------------
    
    @property
    def databases(self) -> Path:
        """Директория для баз данных"""
        return self.db_dir
    
    @property
    def cache(self) -> Path:
        """Директория для кэша"""
        return self.cache_dir
    
    @property
    def logs(self) -> Path:
        """Директория для логов"""
        return self.log_dir
    
    @property
    def checkpoints(self) -> Path:
        """Директория для checkpoint файлов"""
        return self.checkpoint_dir
    
    @property
    def temp(self) -> Path:
        """Временная директория"""
        return self.temp_dir
    
    @property
    def platform(self) -> str:
        """Текущая платформа"""
        return self._platform
    
    # -------------------------------------------------------------------------
    # Методы для получения путей
    # -------------------------------------------------------------------------
    
    def get_db_path(self, prefix: str) -> Path:
        """
        Получить путь к БД для региона.
        
        Args:
            prefix: префикс региона (например, "NS")
        
        Returns:
            Path: путь к файлу БД
        """
        return self.db_dir / f"{prefix}_temperature_eNode.db"
    
    def get_checkpoint_path(self, name: str = "checkpoint") -> Path:
        """
        Получить путь к checkpoint файлу.
        
        Args:
            name: имя checkpoint
        
        Returns:
            Path: путь к файлу
        """
        return self.checkpoint_dir / f"{name}.json"
    
    def get_log_path(self, name: str = "app") -> Path:
        """
        Получить путь к файлу лога.
        
        Args:
            name: имя лога
        
        Returns:
            Path: путь к файлу
        """
        return self.log_dir / f"{name}.log"


# =============================================================================
# Глобальный экземпляр
# =============================================================================

_config: Optional[DirectoryConfig] = None


def get_config(app_name: str = "temperature_poller") -> DirectoryConfig:
    """
    Получить глобальный экземпляр конфигурации.
    
    Args:
        app_name: имя приложения
    
    Returns:
        DirectoryConfig: экземпляр конфигурации
    """
    global _config
    if _config is None or _config.app_name != app_name:
        _config = DirectoryConfig(app_name)
        _config.ensure_directories()
    return _config


def reset_config() -> None:
    """Сброс глобальной конфигурации (для тестов)"""
    global _config
    _config = None


# =============================================================================
# Пример использования
# =============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("КРОССПЛАТФОРМЕННАЯ КОНФИГУРАЦИЯ ДИРЕКТОРИЙ")
    print("=" * 70)
    
    config = get_config()
    
    print(f"\nПлатформа: {config.platform}")
    print(f"\n📁 Базовая директория: {config.base_dir}")
    print(f"📁 Базы данных: {config.databases}")
    print(f"📁 Кэш: {config.cache}")
    print(f"📁 Логи: {config.logs}")
    print(f"📁 Checkpoints: {config.checkpoints}")
    print(f"📁 Temp: {config.temp}")
    
    print(f"\n🔧 Путь к БД для NS: {config.get_db_path('NS')}")
    print(f"🔧 Путь к checkpoint: {config.get_checkpoint_path()}")
    print(f"🔧 Путь к логу: {config.get_log_path()}")
    
    print("\n✅ Директории созданы")
