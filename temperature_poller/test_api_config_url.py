#!/usr/bin/env python3
"""Тест функции _get_default_api_url"""

import os
import sys

# Проверяем функцию напрямую, без импорта всего api.config
def _get_default_api_url_test() -> str:
    """Тестовая версия функции"""
    # Сначала проверяем переменную окружения
    if os.environ.get('API_BASE_URL'):
        region_prefix = os.environ.get('REGION_PREFIX', 'NS')
        return f"{os.environ['API_BASE_URL']}/api/v1/hosts?prefix={region_prefix}"
    
    # Пытаемся получить из app_config
    try:
        from app_config import get_hosts_api_url
        return get_hosts_api_url()
    except (ImportError, Exception) as e:
        print(f"app_config import error: {e}")
        pass
    
    # Fallback
    return "http://localhost:8001/api/v1/hosts?prefix=NS"

print("Тест _get_default_api_url():")
result = _get_default_api_url_test()
print(f"Result: {result}")
print(f"Expected: http://WSNS-LAVROV2:8001/api/v1/hosts?prefix=NS")
print(f"Match: {result == 'http://WSNS-LAVROV2:8001/api/v1/hosts?prefix=NS'}")
