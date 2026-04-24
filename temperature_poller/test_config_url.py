#!/usr/bin/env python3
"""Тест конфигурации URL API"""

import os
import sys

# Проверяем app_config
from app_config import get_config

config = get_config()
print("=" * 70)
print("ТЕСТ КОНФИГУРАЦИИ URL API")
print("=" * 70)
print(f"\n[OK] app_config.py:")
print(f"     Base URL: {config.api.base_url}")
print(f"     Hosts Endpoint: {config.api.hosts_endpoint}")
print(f"     Full URL: {config.get_hosts_api_url()}")

# Проверяем функцию _get_default_api_url из api/config
print(f"\n[OK] api/config.py _get_default_api_url():")
try:
    from api.config import _get_default_api_url
    api_url = _get_default_api_url()
    print(f"     API URL: {api_url}")
except Exception as e:
    print(f"     Ошибка: {e}")

# Проверяем polling_manager
print(f"\n[OK] polling_manager.py create_polling_manager():")
try:
    # Импортируем только функцию, не загружая все зависимости
    import importlib.util
    spec = importlib.util.spec_from_file_location("polling_manager_partial", "polling_manager.py", 
                                                   submodule_search_locations=[])
    # Не загружаем полностью, только проверяем код
    with open("polling_manager.py", "r", encoding="utf-8") as f:
        content = f.read()
        if "get_hosts_api_url()" in content:
            print("     Использует app_config.get_hosts_api_url()")
        else:
            print("     WARNING: Не использует app_config!")
except Exception as e:
    print(f"     Ошибка: {e}")

print("\n" + "=" * 70)
print("ИТОГ: URL API должен быть WSNS-LAVROV2:8001")
print("=" * 70)
