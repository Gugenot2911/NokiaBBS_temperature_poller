"""
Модуль для проверки доступности хостов с помощью ping.
"""

from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor


def ping_host(ip: str, timeout: float = 1, count: int = 1) -> bool:
    """
    Синхронная проверка доступности хоста.

    :param ip: IP-адрес хоста
    :param timeout: Таймаут ping в секундах
    :param count: Количество ping-пакетов
    :return: True если хост доступен, иначе False
    """
    try:
        from pythonping import ping
        response = ping(ip, count=count, timeout=timeout)
        return response.success()
    except Exception:
        return False


def check_availability_batch(
        sites: List[Dict[str, Any]],
        timeout: float = 1,
        count: int = 1,
        max_workers: int = 20
) -> List[Dict[str, Any]]:
    """
    Параллельная проверка доступности хостов в батче.
    Изменяет исходные словари, добавляя ключ 'availability'.

    :param sites: Список сайтов для проверки (должны содержать ключ 'ip')
    :param timeout: Таймаут ping в секундах
    :param count: Количество ping-пакетов
    :param max_workers: Максимальное количество параллельных потоков
    :return: Тот же список с добавленным полем availability

    Пример:
        >>> sites = [{"ip": "8.8.8.8"}, {"ip": "192.168.1.1"}]
        >>> check_availability_batch(sites)
        >>> print(sites)
        [{"ip": "8.8.8.8", "availability": True}, {"ip": "192.168.1.1", "availability": False}]
    """
    if not sites:
        return sites

    # Отбираем хосты с IP
    valid_indices = []
    for i, site in enumerate(sites):
        ip = site.get('ip')
        if ip:
            valid_indices.append((i, ip))
        else:
            site['availability'] = False

    if not valid_indices:
        return sites

    # Параллельный ping
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(ping_host, ip, timeout, count): idx
            for idx, ip in valid_indices
        }

        for future in futures:
            idx = futures[future]
            try:
                sites[idx]['availability'] = future.result()
            except Exception:
                sites[idx]['availability'] = False

    return sites


def check_availability_single(site: Dict[str, Any], timeout: float = 1, count: int = 1) -> Dict[str, Any]:
    """
    Проверка доступности одного хоста.
    Изменяет исходный словарь, добавляя ключ 'availability'.

    :param site: Словарь с данными сайта (должен содержать ключ 'ip')
    :param timeout: Таймаут ping в секундах
    :param count: Количество ping-пакетов
    :return: Тот же словарь с добавленным полем availability
    """
    ip = site.get('ip')
    if ip:
        site['availability'] = ping_host(ip, timeout, count)
    else:
        site['availability'] = False
    return site
