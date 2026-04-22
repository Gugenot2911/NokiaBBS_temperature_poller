#!/usr/bin/env python3
"""
Скрипт для запуска Temperature Poller API.

Использование:
    python run_api.py
    python run_api.py --port 8080
    python run_api.py --host 0.0.0.0 --port 8080 --reload
"""

import argparse
import sys
import os

# Добавляем корень проекта в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    """Точка входа"""
    parser = argparse.ArgumentParser(
        description="Temperature Poller API Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  python run_api.py                           # Запуск с настройками из .env
  python run_api.py --port 8080               # Запуск на порту 8080
  python run_api.py --host 0.0.0.0 --reload   # Запуск с автоперезагрузкой
        """
    )
    
    parser.add_argument(
        "--host",
        type=str,
        default=None,
        help="Хост для绑定 (по умолчанию из .env)"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Порт для绑定 (по умолчанию из .env)"
    )
    
    parser.add_argument(
        "--reload",
        action="store_true",
        default=None,
        help="Включить автоперезагрузку (разработка)"
    )
    
    parser.add_argument(
        "--log-level",
        type=str,
        default=None,
        choices=["debug", "info", "warning", "error", "critical"],
        help="Уровень логирования"
    )
    
    args = parser.parse_args()
    
    # Импортируем после парсинга аргументов
    from api.config import settings
    from api.main import app
    import uvicorn
    
    # Показываем конфигурацию
    print("=" * 70)
    print("🚀 Temperature Poller API")
    print("=" * 70)
    
    # Показываем конфигурацию региона
    print(f"\n📍 Регион:")
    print(f"   Префикс: {settings.REGION_PREFIX if settings.REGION_PREFIX else 'NS (default)'}")
    
    # Переопределяем настройки из аргументов командной строки
    host = args.host or settings.HOST if hasattr(settings, 'HOST') and settings.HOST else "0.0.0.0"
    port = args.port or settings.PORT if hasattr(settings, 'PORT') and settings.PORT else 8000
    reload = args.reload if args.reload is not None else (settings.RELOAD if hasattr(settings, 'RELOAD') else False)
    log_level = args.log_level or settings.LOG_LEVEL if hasattr(settings, 'LOG_LEVEL') and settings.LOG_LEVEL else "info"
    
    print(f"\n📡 Сервер:")
    print(f"   Host: {host}")
    print(f"   Port: {port}")
    print(f"   Reload: {reload}")
    print(f"   Log level: {log_level}")
    
    print(f"\n🔄 Polling:")
    print(f"   API URL: {settings.api_url}")
    print(f"   Chunk size: {settings.chunk_size}")
    print(f"   DB dir: {settings.db_base_dir}")
    
    print("\n" + "=" * 70)
    print("🌐 API Documentation: http://localhost:{port}/docs".format(port=port))
    print("📚 ReDoc: http://localhost:{port}/redoc".format(port=port))
    print("=" * 70)
    print()
    
    # Запуск сервера
    uvicorn.run(
        app,
        host=host,
        port=port,
        reload=reload,
        log_level=log_level
    )


if __name__ == "__main__":
    main()
