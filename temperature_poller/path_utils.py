#!/usr/bin/env python3
"""
Утилиты для кроссплатформенной работы с путями и файлами.

Обеспечивает совместимость между Windows, Linux и macOS.
"""

import os
import sys
from pathlib import Path
from typing import Optional, Union


# =============================================================================
# Кроссплатформенные пути
# =============================================================================

def get_script_dir() -> Path:
    """
    Получить директорию текущего скрипта.
    
    Работает корректно в PyInstaller и обычном запуске.
    
    Returns:
        Path: абсолютный путь к директории скрипта
    """
    if getattr(sys, 'frozen', False):
        # Запуск через PyInstaller
        return Path(sys.executable).parent
    else:
        # Обычный запуск
        return Path(__file__).parent.resolve()


def get_project_root() -> Path:
    """
    Получить корневую директорию проекта.
    
    Ищет директорию с .git или requirements.txt вверх по дереву.
    
    Returns:
        Path: корневая директория проекта
    """
    current = get_script_dir()
    
    # Ищем вверх по дереву
    for _ in range(10):
        if (current / '.git').exists() or (current / 'requirements.txt').exists():
            return current
        parent = current.parent
        if parent == current:
            break
        current = parent
    
    # Если не нашли, возвращаем текущую директорию
    return get_script_dir()


def normalize_path(path: Union[str, Path]) -> Path:
    """
    Нормализовать путь к кроссплатформенному виду.
    
    Преобразует все разделители в системные и разрешает относительные пути.
    
    Args:
        path: путь для нормализации
    
    Returns:
        Path: нормализованный абсолютный путь
    """
    if isinstance(path, str):
        # Заменяем все разделители на системные
        path = path.replace('/', os.sep).replace('\\', os.sep)
    
    return Path(path).resolve()


def join_paths(*parts: Union[str, Path]) -> Path:
    """
    Кроссплатформенное соединение путей.
    
    Аналог os.path.join() но возвращает Path.
    
    Args:
        *parts: части пути
    
    Returns:
        Path: соединённый путь
    """
    result = Path(parts[0])
    for part in parts[1:]:
        result = result / part
    return result.resolve()


def get_app_data_dir(app_name: str = "temperature_poller") -> Path:
    """
    Получить директорию для данных приложения.
    
    Windows: C:\Users\...\AppData\Roaming\app_name
    Linux: ~/.local/share/app_name
    macOS: ~/Library/Application Support/app_name
    
    Args:
        app_name: имя приложения
    
    Returns:
        Path: директория для данных
    """
    if sys.platform == 'win32':
        # Windows
        base = Path(os.environ.get('APPDATA', Path.home() / 'AppData' / 'Roaming'))
    elif sys.platform == 'darwin':
        # macOS
        base = Path.home() / 'Library' / 'Application Support'
    else:
        # Linux и другие
        base = Path.home() / '.local' / 'share'
    
    app_dir = base / app_name
    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir


def get_cache_dir(app_name: str = "temperature_poller") -> Path:
    """
    Получить директорию для кэша.
    
    Windows: C:\Users\...\AppData\Local\app_name\cache
    Linux: ~/.cache/app_name
    macOS: ~/Library/Caches/app_name
    
    Args:
        app_name: имя приложения
    
    Returns:
        Path: директория для кэша
    """
    if sys.platform == 'win32':
        # Windows
        base = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData' / 'Local'))
        cache_dir = base / app_name / 'cache'
    elif sys.platform == 'darwin':
        # macOS
        base = Path.home() / 'Library' / 'Caches'
        cache_dir = base / app_name
    else:
        # Linux
        base = Path.home() / '.cache'
        cache_dir = base / app_name
    
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def get_log_dir(app_name: str = "temperature_poller") -> Path:
    """
    Получить директорию для логов.
    
    Windows: C:\Users\...\AppData\Local\app_name\logs
    Linux: ~/.local/share/app_name/logs
    macOS: ~/Library/Logs/app_name
    
    Args:
        app_name: имя приложения
    
    Returns:
        Path: директория для логов
    """
    if sys.platform == 'win32':
        # Windows
        base = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData' / 'Local'))
        log_dir = base / app_name / 'logs'
    elif sys.platform == 'darwin':
        # macOS
        base = Path.home() / 'Library' / 'Logs'
        log_dir = base / app_name
    else:
        # Linux
        base = Path.home() / '.local' / 'share' / app_name
        log_dir = base / 'logs'
    
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


# =============================================================================
# Кроссплатформенные команды
# =============================================================================

def get_cli_script_path(script_name: str = "admin-cli") -> Optional[Path]:
    """
    Найти путь к CLI-скрипту для текущей платформы.
    
    Windows: script_nokia\admin-cli.bat
    Linux/macOS: script_nokia/admin-cli.sh
    
    Args:
        script_name: имя скрипта без расширения
    
    Returns:
        Path: путь к скрипту или None если не найден
    """
    script_dir = get_project_root() / "script_nokia"
    
    # Определяем расширение в зависимости от платформы
    if sys.platform == 'win32':
        extensions = ['.bat', '.cmd', '.exe', '']
    else:
        extensions = ['.sh', '']
    
    for ext in extensions:
        script_path = script_dir / f"{script_name}{ext}"
        if script_path.exists():
            return script_path
    
    return None


def is_windows() -> bool:
    """Проверить, что код выполняется на Windows."""
    return sys.platform == 'win32'


def is_macos() -> bool:
    """Проверить, что код выполняется на macOS."""
    return sys.platform == 'darwin'


def is_linux() -> bool:
    """Проверить, что код выполняется на Linux."""
    return sys.platform == 'linux'


# =============================================================================
# Утилиты для файлов
# =============================================================================

def ensure_dir(path: Union[str, Path]) -> Path:
    """
    Создать директорию если она не существует.
    
    Args:
        path: путь к директории
    
    Returns:
        Path: созданный/существующий путь
    """
    path = normalize_path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def safe_remove(path: Union[str, Path]) -> bool:
    """
    Безопасно удалить файл.
    
    Args:
        path: путь к файлу
    
    Returns:
        bool: True если файл удалён или не существовал
    """
    path = normalize_path(path)
    if path.exists():
        try:
            path.unlink()
            return True
        except Exception:
            return False
    return True


def get_file_size(path: Union[str, Path]) -> int:
    """
    Получить размер файла в байтах.
    
    Args:
        path: путь к файлу
    
    Returns:
        int: размер файла или 0 если файл не существует
    """
    path = normalize_path(path)
    if path.exists():
        return path.stat().st_size
    return 0


# =============================================================================
# Пример использования
# =============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("КРОССПЛАТФОРМЕННЫЕ УТИЛИТЫ - ТЕСТ")
    print("=" * 70)
    
    print(f"\nПлатформа: {sys.platform}")
    print(f"Python: {sys.version}")
    
    print(f"\n📁 Директория скрипта: {get_script_dir()}")
    print(f"📁 Корень проекта: {get_project_root()}")
    print(f"📁 AppData: {get_app_data_dir()}")
    print(f"📁 Cache: {get_cache_dir()}")
    print(f"📁 Logs: {get_log_dir()}")
    
    cli_path = get_cli_script_path("admin-cli")
    print(f"\n🔧 CLI скрипт: {cli_path}")
    
    print(f"\n🪟 Windows: {is_windows()}")
    print(f"🍎 macOS: {is_macos()}")
    print(f"🐧 Linux: {is_linux()}")
    
    print("\n✅ Тест завершён")
