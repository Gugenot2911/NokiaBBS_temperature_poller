#!/usr/bin/env python3
"""
Тестовый скрипт для проверки API Temperature Poller.

Запускается после старта API сервера.

Использование:
    python test_api.py
"""

import requests
import json
import sys

BASE_URL = "http://localhost:8000"


def print_section(title):
    """Вывод разделителя"""
    print("\n" + "=" * 70)
    print(f" {title}")
    print("=" * 70)


def test_health():
    """Тест health check"""
    print_section("HEALTH CHECK")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False


def test_root():
    """Тест корневой страницы"""
    print_section("ROOT ENDPOINT")
    try:
        response = requests.get(f"{BASE_URL}/", timeout=5)
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False


def test_status():
    """Тест статуса системы"""
    print_section("SYSTEM STATUS")
    try:
        response = requests.get(f"{BASE_URL}/api/v1/status", timeout=5)
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False


def test_databases():
    """Тест статуса БД"""
    print_section("DATABASE STATUS")
    try:
        response = requests.get(f"{BASE_URL}/api/v1/status/databases", timeout=5)
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False


def test_hosts_list():
    """Тест списка хостов"""
    print_section("HOSTS LIST")
    try:
        response = requests.get(f"{BASE_URL}/api/v1/temperature/hosts", timeout=5)
        print(f"Status: {response.status_code}")
        data = response.json()
        print(f"Total hosts: {data.get('total', 0)}")
        print(f"Response: {json.dumps(data, indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False


def test_level1():
    """Тест Level 1 данных"""
    print_section("TEMPERATURE LEVEL 1")
    try:
        response = requests.get(f"{BASE_URL}/api/v1/temperature/level1", timeout=5)
        print(f"Status: {response.status_code}")
        data = response.json()
        print(f"Page: {data.get('page')}/{data.get('total_pages')}")
        print(f"Total stations: {data.get('total_stations')}")
        print(f"Items on page: {len(data.get('data', []))}")
        if data.get('data'):
            print(f"First item: {json.dumps(data['data'][0], indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False


def test_mass_poll():
    """Тест запуска массового опроса"""
    print_section("MASS POLL (ASYNC)")
    try:
        response = requests.post(f"{BASE_URL}/api/v1/poll/mass", timeout=5)
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code in [200, 409]  # 409 = already polling
    except Exception as e:
        print(f"Error: {e}")
        return False


def test_manual_poll():
    """Тест ручного опроса"""
    print_section("MANUAL POLL")
    try:
        payload = {
            "hostnames": ["NS0830"],
            "force": False
        }
        response = requests.post(
            f"{BASE_URL}/api/v1/poll/manual",
            json=payload,
            timeout=30
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False


def test_refresh_hosts():
    """Тест обновления хостов"""
    print_section("REFRESH HOSTS")
    try:
        response = requests.post(f"{BASE_URL}/api/v1/poll/hosts/refresh", timeout=30)
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False


def main():
    """Запуск всех тестов"""
    print("\n" + "=" * 70)
    print(" TEMPERATURE POLLER API TEST SUITE")
    print("=" * 70)
    print(f"Base URL: {BASE_URL}")
    
    tests = [
        ("Health Check", test_health),
        ("Root Endpoint", test_root),
        ("System Status", test_status),
        ("Database Status", test_databases),
        ("Hosts List", test_hosts_list),
        ("Temperature Level 1", test_level1),
        ("Mass Poll", test_mass_poll),
        ("Refresh Hosts", test_refresh_hosts),
        ("Manual Poll", test_manual_poll),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success))
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            results.append((name, False))
    
    # Итоговый отчёт
    print_section("TEST SUMMARY")
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
