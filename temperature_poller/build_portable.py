#!/usr/bin/env python3
"""
Скрипт сборки портативной версии Temperature Poller для Windows 10.

Не требует прав администратора.
Создаёт полностью автономную папку с Python и всеми зависимостями.

Использование:
    python build_portable.py
"""

import os
import sys
import subprocess
import shutil
import urllib.request
import zipfile
from pathlib import Path
from typing import Optional


# Конфигурация
PYTHON_VERSION = "3.11.9"
PYTHON_ARCH = "amd64"
PYTHON_URL = f"https://www.python.org/ftp/python/{PYTHON_VERSION}/python-{PYTHON_VERSION}-embed-{PYTHON_ARCH}.zip"
PROJECT_ROOT = Path(__file__).parent
OUTPUT_DIR = PROJECT_ROOT / "temperature-poller-portable"


def print_header():
    """Вывод заголовка"""
    print("=" * 70)
    print("ТЕМПЕРАТУРНЫЙ МОНИТОРИНГ - ПОРТАТИВНАЯ ВЕРСИЯ")
    print("=" * 70)
    print(f"Python: {PYTHON_VERSION} {PYTHON_ARCH}")
    print(f"Выходная папка: {OUTPUT_DIR.absolute()}")
    print("=" * 70)
    print()


def download_file(url: str, dest: Path) -> bool:
    """Скачивание файла с прогрессом"""
    print(f"Скачивание: {Path(url).name}...")
    try:
        def progress(block_num, block_size, total_size):
            downloaded = block_num * block_size
            percent = min(100, (downloaded / total_size) * 100)
            print(f"\r   [{percent:5.1f}%]", end="")
        
        urllib.request.urlretrieve(url, dest, progress)
        print("\r   [100.0%] OK")
        return True
    except Exception as e:
        print(f"\nОшибка скачивания: {e}")
        return False


def extract_zip(zip_path: Path, extract_to: Path) -> bool:
    """Распаковка ZIP архива"""
    print(f"Распаковка: {zip_path.name}...")
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_to)
        print("   OK: Распаковано")
        return True
    except Exception as e:
        print(f"   Ошибка распаковки: {e}")
        return False


def create_pip_ini(python_dir: Path) -> bool:
    """Создание pip.ini для работы без кэша"""
    pip_ini = python_dir / "pip.ini"
    try:
        with open(pip_ini, 'w', encoding='utf-8') as f:
            f.write("""[global]
timeout = 60
default-timeout = 60
disable-pip-version-check = true
no-cache-dir = true

[install]
no-warn-script-location = true
""")
        print("   OK: Создан pip.ini")
        return True
    except Exception as e:
        print(f"   Ошибка создания pip.ini: {e}")
        return False


def install_pip(python_dir: Path) -> bool:
    """Установка pip в embedded Python"""
    print("Установка pip...")
    pip_script = python_dir / "get-pip.py"
    
    try:
        # Скачивание get-pip.py
        urllib.request.urlretrieve(
            "https://bootstrap.pypa.io/get-pip.py",
            str(pip_script)
        )
        
        # Запуск установки
        python_exe = python_dir / "python.exe"
        subprocess.run(
            [str(python_exe), str(pip_script)],
            cwd=python_dir,
            check=True,
            capture_output=True
        )
        
        pip_script.unlink()  # Удалить get-pip.py
        print("   OK: pip установлен")
        return True
    except Exception as e:
        print(f"   Ошибка установки pip: {e}")
        return False


def install_dependencies(python_dir: Path) -> bool:
    """Установка зависимостей проекта"""
    print("Установка зависимостей проекта...")
    
    python_exe = python_dir / "python.exe"
    pip_exe = python_dir / "Scripts" / "pip.exe"
    
    dependencies = [
        "fastapi",
        "uvicorn[standard]",
        "pydantic",
        "pydantic-settings",
        "python-multipart",
        "requests",
        "python-json-logger",
        "python-dateutil",
        "anyio",
    ]
    
    try:
        # Установка через pip
        result = subprocess.run(
            [str(pip_exe), "install"] + dependencies,
            cwd=python_dir,
            check=True,
            capture_output=False
        )
        
        if result.returncode == 0:
            print("   OK: Зависимости установлены")
            return True
        else:
            print("   Ошибка установки зависимостей")
            return False
    except subprocess.CalledProcessError as e:
        print(f"   Ошибка: {e}")
        return False


def copy_project_files(dest_dir: Path) -> bool:
    """Копирование файлов проекта"""
    print("Копирование файлов проекта...")
    
    # Файлы в корне
    root_files = [
        "logging_config.py",
        "models.py",
        "polling_manager.py",
        "sqlite_temperature.py",
        "emergency_checkpoint.py",
        "app_config.py",
        "directory_config.py",
        "path_utils.py",
        "__init__.py",
        "config.json",
        "run_api.py",
    ]
    
    try:
        # Копирование файлов
        for filename in root_files:
            src = PROJECT_ROOT / filename
            if src.exists():
                shutil.copy2(src, dest_dir / filename)
                print(f"   {filename}")
        
        # Копирование директорий
        dirs_to_copy = ["api", "nokia_polling"]
        for dirname in dirs_to_copy:
            src_dir = PROJECT_ROOT / dirname
            if src_dir.exists():
                shutil.copytree(src_dir, dest_dir / dirname, dirs_exist_ok=True)
                print(f"   {dirname}/")
        
        # Копирование .env.example
        env_example = PROJECT_ROOT / "api" / ".env.example"
        if env_example.exists():
            env_dest = dest_dir / "api" / ".env.example"
            shutil.copy2(env_example, env_dest)
            # Создать .env если нет
            env_file = dest_dir / "api" / ".env"
            if not env_file.exists():
                shutil.copy2(env_example, env_file)
        
        print("   OK: Файлы скопированы")
        return True
    except Exception as e:
        print(f"   Ошибка копирования: {e}")
        return False


def create_start_script(dest_dir: Path) -> bool:
    """Создание скрипта запуска"""
    print("Создание скрипта запуска...")
    
    start_bat = dest_dir / "START.bat"
    try:
        with open(start_bat, 'w', encoding='cp1251') as f:
            f.write("""@echo off
chcp 65001 >nul
title Temperature Poller API

echo ==========================================
echo Temperature Poller API Server
echo ==========================================
echo.

cd /d %%~dp0

REM Настройки по умолчанию
set HOST=0.0.0.0
set PORT=8000
set LOG_LEVEL=info

python run_api.py %%*

echo.
echo ==========================================
echo Сервер остановлен
echo Нажмите любую клавишу для выхода...
pause >nul
""")
        print("   OK: START.bat создан")
        return True
    except Exception as e:
        print(f"   Ошибка создания START.bat: {e}")
        return False


def create_readme(dest_dir: Path) -> bool:
    """Создание README для портативной версии"""
    print("Создание README...")
    
    readme = dest_dir / "README.txt"
    try:
        with open(readme, 'w', encoding='cp1251') as f:
            f.write("""==========================================
TEMPERATURE POLLER API - ПОРТАТИВНАЯ ВЕРСИЯ
==========================================

ЗАПУСК:
   Двойной клик на START.bat
   ИЛИ: START.bat --port 8080

ДОКУМЕНТАЦИЯ:
   http://localhost:8000/docs
   http://localhost:8000/redoc

НАСТРОЙКА:
   - config.json - конфигурация проекта
   - api/.env - настройки сервера (HOST, PORT, LOG_LEVEL)

ПАРАМЕТРЫ ЗАПУСКА:
   START.bat --port 8080           # Изменить порт
   START.bat --host 0.0.0.0        # Изменить хост
   START.bat --log-level debug     # Уровень логирования

СТРУКТУРА:
   temperature-poller-portable/
   ├── START.bat              <- Запуск
   ├── config.json            <- Конфигурация
   ├── run_api.py             <- Скрипт запуска
   ├── api/                   <- FastAPI сервер
   │   ├── main.py
   │   ├── config.py
   │   └── .env               <- Настройки сервера
   └── databases/             <- Базы данных (создаётся)

ПРИМЕЧАНИЯ:
   - Не требует прав администратора
   - Не требует установки Python
   - Все данные в папке databases/

==========================================
""")
        print("   OK: README.txt создан")
        return True
    except Exception as e:
        print(f"   Ошибка создания README: {e}")
        return False


def cleanup(zip_path: Path) -> None:
    """Очистка временных файлов"""
    print("Очистка временных файлов...")
    if zip_path.exists():
        zip_path.unlink()
        print("   OK: Временные файлы удалены")


def main():
    """Основная функция сборки"""
    print_header()
    
    # Шаг 1: Очистка выходной директории
    if OUTPUT_DIR.exists():
        print("Очистка старой сборки...")
        shutil.rmtree(OUTPUT_DIR)
    
    OUTPUT_DIR.mkdir(parents=True)
    print(f"   OK: Создана папка: {OUTPUT_DIR.name}")
    
    # Шаг 2: Создание папки для Python
    python_dir = OUTPUT_DIR / "python"
    python_dir.mkdir()
    
    # Шаг 3: Скачивание Embedded Python
    zip_path = PROJECT_ROOT / "python_embedded.zip"
    if not download_file(PYTHON_URL, zip_path):
        sys.exit(1)
    
    # Шаг 4: Распаковка
    if not extract_zip(zip_path, python_dir):
        cleanup(zip_path)
        sys.exit(1)
    
    # Шаг 5: Настройка pip
    if not create_pip_ini(python_dir):
        cleanup(zip_path)
        sys.exit(1)
    
    cleanup(zip_path)
    
    # Шаг 6: Установка pip
    if not install_pip(python_dir):
        sys.exit(1)
    
    # Шаг 7: Установка зависимостей
    if not install_dependencies(python_dir):
        sys.exit(1)
    
    # Шаг 8: Копирование проекта
    if not copy_project_files(OUTPUT_DIR):
        sys.exit(1)
    
    # Шаг 9: Создание скрипта запуска
    if not create_start_script(OUTPUT_DIR):
        sys.exit(1)
    
    # Шаг 10: Создание README
    if not create_readme(OUTPUT_DIR):
        sys.exit(1)
    
    # Финал
    print()
    print("=" * 70)
    print("СБОРКА ЗАВЕРШЕНА УСПЕШНО!")
    print("=" * 70)
    print()
    print(f"Портативная версия: {OUTPUT_DIR.absolute()}")
    print()
    print("Запуск:")
    print(f"   1. Откройте папку: {OUTPUT_DIR}")
    print("   2. Запустите: START.bat")
    print("   3. Откройте: http://localhost:8000/docs")
    print()
    print("=" * 70)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nСборка прервана пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nКритическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
