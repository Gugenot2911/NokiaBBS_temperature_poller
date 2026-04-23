#!/usr/bin/env python3
"""
Менеджер опроса сетевых устройств.

Оркестрирует процесс опроса температурных данных с оборудования Nokia:
- Массовый опрос по расписанию (раз в час)
- Ручной опрос выбранных хостов
- Обновление списка хостов из API (раз в сутки)
- Аварийное сохранение прогресса при длинных опросах
- Автоматическая пауза между опросами

Архитектура:
┌─────────────────────────────────────────────────────────┐
│                    PollingManager                        │
│  ┌──────────────────────────────────────────────────┐   │
│  │  HostCache (RAM)                                  │   │
│  │  - Список хостов с TTL                            │   │
│  │  - Обновление из API раз в сутки                  │   │
│  └──────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────┐   │
│  │  PollingOrchestrator                              │   │
│  │  - Разбивка на чанки (10 хостов)                  │   │
│  │  - Вызов get_nokia_measurements.py                │   │
│  │  - Аварийный checkpoint на HDD                    │   │
│  │  - Расчёт wait_time                               │   │
│  └──────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────┐   │
│  │  DatabaseWriter                                   │   │
│  │  - Запись в sqlite_temperature.py                 │   │
│  │  - Пакетная вставка                               │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘

Пример использования:
    >>> from polling_manager import PollingManager
    >>>
    >>> manager = PollingManager(
    ...     api_url="http://api.example.com/hosts",
    ...     db_base_dir="databases",
    ...     checkpoint_path="emergency_checkpoint.json"
    ... )
    >>>
    >>> # Массовый опрос
    >>> asyncio.run(manager.start_mass_poll())
    >>>
    >>> # Ручной опрос
    >>> result = await manager.manual_poll(["NS0830", "NS1120"])
    >>> print(f"Успешно: {result.success_count}")
    >>>
    >>> # Автоматический цикл
    >>> asyncio.run(manager.run_automatic())
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from pathlib import Path

# Pydantic может быть не установлен в некоторых окружениях
try:
    from pydantic import BaseModel, Field
    from pydantic import ConfigDict
except ImportError:
    # Fallback для окружений без pydantic
    BaseModel = object  # type: ignore
    ConfigDict = None  # type: ignore
    
    def Field(default=None, **kwargs):
        return default

from models import TemperatureResponse, PollingResult
from nokia_polling.get_nokia_measurements import nokia_polling_module
from sqlite_temperature import (
    TemperatureDatabase,
    DatabaseConfig,
    DataPreprocessor,
    TemperatureDBManager
)

from emergency_checkpoint import EmergencyCheckpoint
from logging_config import setup_logging, get_logger


logger = get_logger()


# =============================================================================
# Конфигурация менеджера
# =============================================================================

class PollingManagerConfig(BaseModel):
    """
    Конфигурация менеджера опроса.
    
    Attributes:
        api_url: URL API для получения списка хостов
        db_base_dir: директория для баз данных
        checkpoint_path: путь к файлу аварийного контрольной точки
        chunk_size: размер чанка для опроса (по умолчанию 10)
        checkpoint_interval: сохранять прогресс каждые N хостов
        poll_interval_hours: интервал между массовыми опросами в часах
        hosts_ttl_hours: TTL кэша хостов в часах
        max_checkpoint_age_hours: максимальный возраст checkpoint
    """
    model_config = ConfigDict(frozen=True)
    
    api_url: str = Field(..., description="URL API для получения списка хостов")
    db_base_dir: str = Field(default="databases", description="Директория БД")
    checkpoint_path: str = Field(default="emergency_checkpoint.json", description="Файл checkpoint")
    chunk_size: int = Field(default=10, ge=1, le=50, description="Размер чанка опроса")
    checkpoint_interval: int = Field(default=100, ge=10, description="Интервал сохранения checkpoint")
    poll_interval_hours: int = Field(default=1, ge=1, description="Интервал опроса в часах")
    hosts_ttl_hours: int = Field(default=24, ge=1, description="TTL кэша хостов")
    max_checkpoint_age_hours: float = Field(default=2.0, description="Макс. возраст checkpoint")
    

# =============================================================================
# Хранение хостов в памяти
# =============================================================================

class HostCache:
    """
    Кэш списка хостов в оперативной памяти.
    
    Хранит актуальный список хостов с TTL. При истечении TTL возвращает
    устаревшие данные с предупреждением, но продолжает работу.
    
    Пример:
        >>> cache = HostCache(ttl_hours=24)
        >>> hosts, is_fresh = cache.get_hosts()
        >>> if not is_fresh:
        ...     logger.warning("Используется устаревший кэш")
    """
    
    def __init__(self, ttl_hours: int = 24):
        """
        Инициализация кэша хостов.
        
        Args:
            ttl_hours: время жизни кэша в часах
        """
        self.ttl = timedelta(hours=ttl_hours)
        self._hosts: List[TemperatureResponse] = []
        self._last_update: Optional[datetime] = None
    
    def set_hosts(self, hosts: List[TemperatureResponse]) -> None:
        """
        Установка списка хостов.
        
        Args:
            hosts: список хостов
        """
        self._hosts = hosts
        self._last_update = datetime.now()
        logger.info(f"Кэш хостов обновлён: {len(hosts)} хостов")
    
    def get_hosts(self, force_refresh: bool = False) -> tuple[List[TemperatureResponse], bool]:
        """
        Получение списка хостов.
        
        Args:
            force_refresh: Force обновление кэша (игнорирует TTL)
        
        Returns:
            (hosts, is_fresh) - список хостов и флаг актуальности
        """
        if force_refresh or not self._hosts or not self._last_update:
            return self._hosts, False
        
        if datetime.now() - self._last_update > self.ttl:
            logger.warning(
                f"TTL истёк: кэш старше {self.ttl}, "
                f"возраст: {datetime.now() - self._last_update}"
            )
            return self._hosts, False
        
        return self._hosts, True
    
    def update_host(self, hostname: str, updated_data: Dict[str, Any]) -> bool:
        """
        Обновление данных одного хоста.
        
        Args:
            hostname: имя хоста
            updated_data: новые данные хоста
        
        Returns:
            True если хост найден и обновлён
        """
        for i, host in enumerate(self._hosts):
            if host.hostname == hostname:
                try:
                    merged = host.model_dump() | updated_data
                    self._hosts[i] = TemperatureResponse(**merged)
                    logger.debug(f"Хост {hostname} обновлён")
                    return True
                except Exception as e:
                    logger.error(f"Ошибка обновления хоста {hostname}: {e}")
                    return False
        
        logger.warning(f"Хост {hostname} не найден в кэше")
        return False
    
    def get_host(self, hostname: str) -> Optional[TemperatureResponse]:
        """Получение одного хоста по имени"""
        for host in self._hosts:
            if host.hostname == hostname:
                return host
        return None
    
    @property
    def count(self) -> int:
        """Количество хостов в кэше"""
        return len(self._hosts)
    
    @property
    def is_empty(self) -> bool:
        """Пуст ли кэш"""
        return len(self._hosts) == 0
    
    @property
    def age(self) -> Optional[timedelta]:
        """Возраст кэша"""
        if not self._last_update:
            return None
        return datetime.now() - self._last_update


# =============================================================================
# Менеджер опроса
# =============================================================================

class PollingManager:
    """
    Основной менеджер опроса сетевых устройств.
    
    Оркестрирует весь процесс опроса:
    1. Получение списка хостов из API (раз в сутки)
    2. Массовый опрос по расписанию (раз в час)
    3. Ручной опрос выбранных хостов
    4. Запись результатов в БД
    5. Аварийное сохранение прогресса
    
    Пример:
        >>> manager = PollingManager(
        ...     api_url="http://api.example.com/hosts"
        ... )
        >>>
        >>> # Ручной опрос
        >>> result = asyncio.run(manager.manual_poll(["NS0830"]))
        >>>
        >>> # Автоматический цикл
        >>> asyncio.run(manager.run_automatic())
    """
    
    def __init__(self, config: PollingManagerConfig):
        """
        Инициализация менеджера опроса.
        
        Args:
            config: конфигурация менеджера
        
        Raises:
            ValueError: если конфигурация невалидна
        """
        self.config = config
        self._config_dict = config.model_dump()
        
        # Кэш хостов в RAM
        self._host_cache = HostCache(ttl_hours=config.hosts_ttl_hours)
        
        # Аварийный контрольный пункт
        self._checkpoint = EmergencyCheckpoint(
            checkpoint_path=config.checkpoint_path,
            save_interval=config.checkpoint_interval
        )
        
        # Менеджер БД
        self._db_manager: Optional[TemperatureDBManager] = None
        
        # Блокировка для предотвращения параллельных опросов
        self._polling_lock = asyncio.Lock()
        self._is_polling = False
        
        # Статистика последнего опроса
        self._last_poll_stats: Dict[str, Any] = {}
        
        logger.info(
            "Менеджер опроса инициализирован",
            extra={
                'api_url': config.api_url,
                'chunk_size': config.chunk_size,
                'poll_interval_hours': config.poll_interval_hours
            }
        )
    
    # -------------------------------------------------------------------------
    # Массовый опрос
    # -------------------------------------------------------------------------
    
    async def start_mass_poll(self) -> bool:
        """
        Запуск массового опроса всех хостов.
        
        Защита от параллельных запусков через asyncio.Lock.
        
        Returns:
            True если опрос успешно запущен, False если уже запущен
        
        Пример:
            >>> manager = PollingManager(config)
            >>> success = await manager.start_mass_poll()
            >>> if success:
            ...     print("Опрос запущен")
        """
        async with self._polling_lock:
            if self._is_polling:
                logger.warning("Опрос уже запущен, пропуск")
                return False
            
            self._is_polling = True
        
        try:
            return await self._do_mass_poll()
        finally:
            self._is_polling = False
    
    async def _do_mass_poll(self) -> bool:
        """
        Выполнение массового опроса.
        
        1. Получение списка хостов из кэша
        2. Проверка аварийного checkpoint
        3. Опрос чанками по chunk_size хостов
        4. Сохранение прогресса каждые checkpoint_interval хостов
        5. Запись в БД
        6. Очистка checkpoint после успешного завершения
        
        Returns:
            True если опрос завершён успешно
        
        Raises:
            RuntimeError: если кэш хостов пуст и API недоступен
        """
        start_time = time.perf_counter()
        logger.info("=" * 80)
        logger.info("НАЧАЛО МАССОВОГО ОПРОСА")
        logger.info("=" * 80)
        
        # Получение списка хостов
        hosts, is_fresh = self._host_cache.get_hosts()
        
        if not hosts:
            logger.error("Кэш хостов пуст! Попытка обновления из API...")
            self.refresh_hosts_from_api()
            hosts, is_fresh = self._host_cache.get_hosts()
        
        if not hosts:
            logger.critical("Не удалось получить список хостов из API и кэша!")
            raise RuntimeError("Cannot fetch hosts from API")
        
        logger.info(f"Всего хостов для опроса: {len(hosts)}")
        logger.info(f"Актуальность кэша: {'актуален' if is_fresh else 'устарел'}")
        
        # Проверка аварийного checkpoint
        start_index = 0
        if self._checkpoint.should_resume(hosts, max_age_hours=self.config.max_checkpoint_age_hours):
            checkpoint = self._checkpoint.load_checkpoint()
            if checkpoint:
                start_index = checkpoint['current_index'] + 1
                logger.warning(f"ВОССТАНОВЛЕНИЕ опроса с хоста {start_index}")
        
        # Обработка чанками
        all_results: List[Dict[str, Any]] = []
        total_success = 0
        total_errors = 0
        
        for i in range(start_index, len(hosts), self.config.chunk_size):
            chunk = hosts[i:i + self.config.chunk_size]
            chunk_start = time.perf_counter()
            
            logger.info(
                f"Чанк {i // self.config.chunk_size + 1}: "
                f"хосты {i + 1}-{min(i + self.config.chunk_size, len(hosts))}"
            )
            
            # ✅ ИСПРАВЛЕНО: обёртка для синхронного вызова в async контексте
            # Используем run_in_executor для предотвращения блокировки event loop
            loop = asyncio.get_running_loop()
            chunk_results = await loop.run_in_executor(
                None,
                lambda: nokia_polling_module(
                    sites=[h.model_dump() for h in chunk],
                    fields={"temperature"},
                    batch_size=self.config.chunk_size,
                    check_availability=True,
                    ping_timeout=1
                )
            )

        
            chunk_elapsed = time.perf_counter() - chunk_start
            logger.info(f"Чанк завершён за {chunk_elapsed:.2f}с")
            
            # Статистика чанка
            chunk_success = len([r for r in chunk_results if r.get('status') == 'success'])
            chunk_errors = len([r for r in chunk_results if r.get('status') == 'error'])
            total_success += chunk_success
            total_errors += chunk_errors
            
            all_results.extend(chunk_results)
            
            # Сохранение прогресса на HDD
            self._checkpoint.save_progress(
                [TemperatureResponse(**r) for r in all_results],
                i + len(chunk_results) - 1
            )
            
            # Запись в БД
            await self._save_results_to_db(chunk_results)
        
        # Очистка аварийного checkpoint
        self._checkpoint.clear_checkpoint()
        
        elapsed = time.perf_counter() - start_time
        
        # Итоговая статистика
        self._last_poll_stats = {
            'start_time': datetime.now().isoformat(),
            'duration_seconds': round(elapsed, 2),
            'total_hosts': len(hosts),
            'success_count': total_success,
            'error_count': total_errors,
            'success_rate': round(total_success / len(hosts) * 100, 2) if hosts else 0
        }
        
        logger.info("=" * 80)
        logger.info("ИТОГИ МАССОВОГО ОПРОСА")
        logger.info(f"Всего хостов: {self._last_poll_stats['total_hosts']}")
        logger.info(f"Успешно: {self._last_poll_stats['success_count']}")
        logger.info(f"Ошибки: {self._last_poll_stats['error_count']}")
        logger.info(f"Успешность: {self._last_poll_stats['success_rate']}%")
        logger.info(f"Время: {self._last_poll_stats['duration_seconds']}с")
        logger.info("=" * 80)
        
        return True
    
    # -------------------------------------------------------------------------
    # Ручной опрос
    # -------------------------------------------------------------------------
    
    async def manual_poll(self, hostnames: List[str], force: bool = False) -> PollingResult:
        """
        Ручной опрос выбранных хостов.
        
        Независим от массового опроса. Перезаписывает данные только для
        указанных хостов.
        
        Args:
            hostnames: список имён хостов для опроса
            force: Force перезапись даже если есть данные за этот час
        
        Returns:
            PollingResult со статистикой опроса
        
        Пример:
            >>> manager = PollingManager(config)
            >>> result = await manager.manual_poll(["NS0830", "NS1120"])
            >>> print(f"Успех: {result.success_count}, Ошибки: {result.error_count}")
        """
        logger.info(f"НАЧАЛО РУЧНОГО ОПРОСА: {len(hostnames)} хостов")
        logger.info(f"Хосты: {', '.join(hostnames)}")
        
        # Поиск хостов в кэше
        targets = []
        not_found = []
        
        for hostname in hostnames:
            host = self._host_cache.get_host(hostname)
            if host:
                targets.append(host)
            else:
                not_found.append(hostname)
        
        if not_found:
            logger.warning(f"Хосты не найдены в кэше: {not_found}")
        
        if not targets:
            logger.error("Нет хостов для опроса!")
            return PollingResult(skipped_count=len(hostnames))
        
        # Проверка наличия данных за текущий час (если не force)
        if not force:
            current_hour = int(datetime.now().timestamp()) // 3600
            has_data = await self._has_data_for_hour(targets, current_hour)
            
            if has_data:
                logger.info(
                    f"Данные за этот час уже есть, пропускаем. "
                    f"Используйте force=True для перезаписи"
                )
                return PollingResult(skipped_count=len(targets))
        
        # ✅ ИСПРАВЛЕНО: обёртка для синхронного вызова в async контексте
        loop = asyncio.get_running_loop()
        results = await loop.run_in_executor(
            None,
            lambda: nokia_polling_module(
                sites=[h.model_dump() for h in targets],
                fields={"temperature"},
                batch_size=min(len(targets), 10),
                check_availability=True
            )
        )
        
        # Запись в БД
        await self._save_results_to_db(results)
        
        # Обновление кэша
        for result in results:
            if result.get('status') == 'success':
                self._host_cache.update_host(
                    result['hostname'],
                    {
                        'temperature': result.get('temperature'),
                        'timestamp': result.get('timestamp'),
                        'status': result.get('status')
                    }
                )
        
        # Статистика
        success_count = len([r for r in results if r.get('status') == 'success'])
        error_count = len([r for r in results if r.get('status') == 'error'])
        skipped_count = len([r for r in results if r.get('status') == 'skipped_vendor'])
        
        logger.info(
            f"РУЧНОЙ ОПРОС ЗАВЕРШЁН: "
            f"успех={success_count}, ошибки={error_count}, пропущено={skipped_count}"
        )
        
        return PollingResult(
            success_count=success_count,
            error_count=error_count,
            skipped_count=skipped_count,
            results=[TemperatureResponse(**r) for r in results]
        )
    
    # -------------------------------------------------------------------------
    # Обновление хостов из API
    # -------------------------------------------------------------------------
    
    def refresh_hosts_from_api(self) -> bool:
        """
        Обновление списка хостов из API.
        
        Вызывается раз в сутки (00:00) или по требованию.
        При недоступности API использует кэш с предупреждением.
        
        Returns:
            True если успешно обновлено, False если использован кэш
        
        Пример:
            >>> manager = PollingManager(config)
            >>> success = manager.refresh_hosts_from_api()
            >>> if not success:
            ...     logger.warning("Используется устаревший кэш")
        """
        logger.info(f"ОБНОВЛЕНИЕ ХОСТОВ ИЗ API: {self.config.api_url}")
        
        try:
            # Импортируем requests здесь, чтобы не зависеть от него при импорте
            import requests
            
            response = requests.get(self.config.api_url, timeout=30)
            response.raise_for_status()
            
            raw_data = response.json()
            
            # Преобразование в TemperatureResponse
            hosts = []
            for item in raw_data:
                try:
                    # Адаптация формата API к модели
                    # ✅ ИСПРАВЛЕНО: используем master_site как hostname (API возвращает master_site, а не hostname)
                    host = TemperatureResponse(
                        hostname=item.get('master_site') or item.get('hostname'),  # Сначала master_site, потом hostname
                        ip=item.get('ip_4g'),  # Только 4G IP
                        vendor=item.get('vendor', 'nokia'),
                        availability=item.get('availability', True)
                    )
                    hosts.append(host)
                except Exception as e:
                    logger.warning(f"Ошибка парсинга хоста {item}: {e}")
            
            if not hosts:
                logger.error("API вернул пустой список хостов!")
                return False
            
            self._host_cache.set_hosts(hosts)
            logger.info(f"Список хостов обновлён: {len(hosts)} хостов")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка API: {e}")
            
            if not self._host_cache.is_empty:
                age = self._host_cache.age
                logger.warning(
                    f"Использование кэшированных данных (возраст: {age})",
                    extra={'error': str(e)}
                )
                return False
            else:
                logger.critical("Нет кэша и API недоступен!")
                raise RuntimeError("Cannot fetch hosts from API")
    
    # -------------------------------------------------------------------------
    # Работа с БД
    # -------------------------------------------------------------------------
    
    def _is_valid_temperature_record(self, record: Dict[str, Any]) -> bool:
        """
        Быстрая проверка валидности записи температуры.
        
        Args:
            record: сырая запись от nokia_polling_module
        
        Returns:
            True если запись валидна и может быть записана в БД
        """
        # Ошибки и skipped тоже сохраняем для отслеживания проблем
        status = record.get('status')
        if status in ('error', 'skipped_vendor', 'unavailable'):
            return True
        
        # Проверяем наличие температуры
        temp = record.get('temperature')
        if temp is None:
            return False
        
        # Проверяем 'error' в temperature (хост недоступен)
        if isinstance(temp, dict) and 'error' in temp:
            return True
        
        # Проверяем наличие хотя бы одного валидного значения температуры
        for component in ['RRU', 'BBU']:
            if component in temp and isinstance(temp[component], dict):
                comp = temp[component]
                if any(comp.get(k) is not None for k in ['max', 'min', 'avg']):
                    return True
        
        return False
    
    async def _save_results_to_db(self, results: List[Dict[str, Any]]) -> None:
        """
        Запись результатов опроса в БД с многоуровневой валидацией.
        
        Args:
            results: список результатов опроса
        
        Пример:
            >>> results = nokia_polling_module(...)
            >>> await manager._save_results_to_db(results)
        """
        if not results:
            return
        
        # Уровень 1: Фильтрация валидных записей
        valid_results = [r for r in results if self._is_valid_temperature_record(r)]
        
        if not valid_results:
            logger.warning("Нет валидных данных для записи в БД")
            return
        
        # Уровень 2: Предобработка
        try:
            preprocessed, validation_errors = DataPreprocessor.preprocess(valid_results)
            
            if validation_errors:
                logger.debug(f"Ошибки предобработки ({len(validation_errors)}): {validation_errors[:3]}")
            
            if not preprocessed:
                logger.warning("DataPreprocessor не вернул валидных данных")
                return
        except Exception as e:
            logger.error(f"Ошибка предобработки данных: {e}", exc_info=True)
            return
        
        # Уровень 3: Инициализация БД
        if self._db_manager is None:
            try:
                self._db_manager = TemperatureDBManager(
                    base_dir=self.config.db_base_dir
                )
            except Exception as e:
                logger.error(f"Ошибка инициализации менеджера БД: {e}", exc_info=True)
                return
        
        # Уровень 4: Запись с защитой в БД
        try:
            db = self._db_manager.get_db(raw_data=valid_results)
            inserted = db.write_batch(preprocessed)
            skipped = len(valid_results) - len(preprocessed)
            logger.debug(f"Записано {inserted} записей в БД, пропущено {skipped}")
            
        except Exception as e:
            logger.error(f"Ошибка записи в БД: {e}", exc_info=True)
            # Не прерываем опрос
    
    async def _has_data_for_hour(
        self,
        hosts: List[TemperatureResponse],
        hour: Optional[int] = None
    ) -> bool:
        """
        Проверка наличия данных за указанный час.
        
        Args:
            hosts: список хостов для проверки
            hour: час для проверки (по умолчанию текущий)
        
        Returns:
            True если есть данные хотя бы для одного хоста
        """
        if hour is None:
            hour = int(datetime.now().timestamp()) // 3600
        
        if not hosts:
            return False
        
        # Получаем префикс из первого хоста для инициализации БД
        try:
            print(_)
            _ = hosts[0].hostname[:2].upper()
        except (IndexError, AttributeError):
            return False
        
        # Инициализация БД
        if self._db_manager is None:
            self._db_manager = TemperatureDBManager(
                base_dir=self.config.db_base_dir
            )
        
        # Создаём тестовые данные для определения БД
        test_data = [{'hostname': hosts[0].hostname, 'temperature': {}}]
        db = self._db_manager.get_db(test_data)
        
        # Проверка наличия данных
        conn = db._get_connection()
        count = conn.execute(
            'SELECT COUNT(*) FROM temps WHERE hour = ?',
            (hour,)
        ).fetchone()[0]
        
        return count > 0
    
    # -------------------------------------------------------------------------
    # Расчёт времени ожидания
    # -------------------------------------------------------------------------
    
    def calculate_wait_time(self, poll_duration: timedelta) -> timedelta:
        """
        Расчёт времени ожидания перед следующим опросом.
        
        Логика (ТЗ п.3):
        - Если опрос < 1 часа: ждать (60 минут - время опроса)
        - Если опрос >= 1 часа: ждать 0 минут (следующий опрос сразу)
          но с предупреждением о необходимости оптимизации
        
        Args:
            poll_duration: длительность завершённого опроса
        
        Returns:
            Время ожидания в минутах
        
        Пример:
            >>> manager = PollingManager(config)
            >>> wait = manager.calculate_wait_time(timedelta(minutes=30))
            >>> print(f"Ждём {wait} минут")  # 30 минут
        """
        hour = timedelta(hours=1)
        
        if poll_duration >= hour:
            logger.warning(
                f"Опрос занял {poll_duration}, требуется оптимизация",
                extra={'poll_duration_seconds': poll_duration.total_seconds()}
            )
            return timedelta(minutes=0)  # Запускать сразу
        else:
            wait_time = hour - poll_duration
            logger.info(f"Пауза перед следующим опросом: {wait_time}")
            return wait_time
    
    # -------------------------------------------------------------------------
    # Автоматический цикл
    # -------------------------------------------------------------------------
    
    async def run_automatic(self) -> None:
        """
        Запуск автоматического цикла опроса.
        
        Основной цикл менеджера:
        1. Обновление хостов из API (если TTL истёк)
        2. Массовый опрос
        3. Пауза (расчитанная по длительности опроса)
        4. Повтор
        
        Пример:
            >>> manager = PollingManager(config)
            >>> await manager.run_automatic()  # Бесконечный цикл
        """
        logger.info("ЗАПУСК АВТОМАТИЧЕСКОГО ЦИКЛА ОПРОСА")
        
        while True:
            try:
                # Проверка TTL хостов (обновление раз в сутки)
                if self._host_cache.is_empty or \
                   (self._host_cache.age and self._host_cache.age > timedelta(hours=23)):
                    self.refresh_hosts_from_api()
                
                # Массовый опрос
                start_time = time.perf_counter()
                await self.start_mass_poll()
                poll_duration = timedelta(seconds=time.perf_counter() - start_time)
                
                # Расчёт паузы
                wait_time = self.calculate_wait_time(poll_duration)
                
                if wait_time.total_seconds() > 0:
                    logger.info(f"Пауза {wait_time} перед следующим опросом")
                    await asyncio.sleep(wait_time.total_seconds())
                
            except KeyboardInterrupt:
                logger.info("Остановка по сигналу пользователя")
                break
            except Exception as e:
                logger.critical(f"Критическая ошибка в цикле: {e}", exc_info=True)
                # Пауза перед повтором
                await asyncio.sleep(60)
    
    # -------------------------------------------------------------------------
    # Статистика и состояние
    # -------------------------------------------------------------------------
    
    def get_status(self) -> Dict[str, Any]:
        """
        Получение текущего статуса менеджера.
        
        Returns:
            Словарь со статусом
        """
        return {
            'is_polling': self._is_polling,
            'hosts_count': self._host_cache.count,
            'hosts_cache_fresh': not self._host_cache.is_empty and 
                                self._host_cache.age is not None and 
                                self._host_cache.age < timedelta(hours=self.config.hosts_ttl_hours),
            'last_poll_stats': self._last_poll_stats,
            'checkpoint_status': self._checkpoint.get_checkpoint_status()
        }
    
    def get_last_poll_stats(self) -> Optional[Dict[str, Any]]:
        """Получение статистики последнего опроса"""
        return self._last_poll_stats.copy() if self._last_poll_stats else None


# =============================================================================
# Конфигурация и запуск
# =============================================================================

def create_polling_manager(
    api_url: Optional[str] = None,
    db_base_dir: str = "databases",
    checkpoint_path: str = "emergency_checkpoint.json",
    chunk_size: int = 10,
    checkpoint_interval: int = 100,
    poll_interval_hours: int = 1,
    hosts_ttl_hours: int = 24,
    config: Optional[PollingManagerConfig] = None
) -> PollingManager:
    """
    Фабрика для создания менеджера опроса.
    
    Args:
        api_url: URL API для получения списка хостов
        db_base_dir: директория для баз данных
        checkpoint_path: путь к файлу checkpoint
        chunk_size: размер чанка опроса
        checkpoint_interval: интервал сохранения checkpoint
        poll_interval_hours: интервал между опросами
        hosts_ttl_hours: TTL кэша хостов
        config: готовый объект конфигурации (альтернатива параметрам выше)
    
    Returns:
        PollingManager
    
    Пример:
        >>> manager = create_polling_manager(
        ...     api_url="http://api.example.com/hosts",
        ...     chunk_size=10
        ... )
        >>>
        >>> # Или с готовым config:
        >>> config = PollingManagerConfig(api_url="...")
        >>> manager = create_polling_manager(config=config)
    """
    if config is not None:
        # Использовать готовый config
        return PollingManager(config)
    
    config = PollingManagerConfig(
        api_url=api_url or "http://localhost:8001/api/v1/hosts?prefix=NS",
        db_base_dir=db_base_dir,
        checkpoint_path=checkpoint_path,
        chunk_size=chunk_size,
        checkpoint_interval=checkpoint_interval,
        poll_interval_hours=poll_interval_hours,
        hosts_ttl_hours=hosts_ttl_hours
    )
    
    return PollingManager(config)


# =============================================================================
# Пример использования
# =============================================================================

if __name__ == "__main__":
    # Настройка логирования
    logger = setup_logging(level=logging.INFO)
    #
    # # Создание менеджера (с тестовым API)
    manager = create_polling_manager(
        api_url="http://localhost:8001/api/v1/hosts?prefix=NS",
        chunk_size=10,
        checkpoint_interval=100
    )
    
    # Запуск автоматического цикла

    asyncio.run(manager.run_automatic())
    
    # Или ручной опрос
    # result = asyncio.run(manager.manual_poll(["NS0830", "NS1120"]))
    # print(result)
    # #
    # print("Менеджер опроса готов к работе")
    # print("Раскомментируйте вызов run_automatic() или manual_poll()")



    # data = [{'hostname': 'NS0002', 'ip': '10.8.234.129', 'temperature': {'RRU': {'max': 57, 'min': 19, 'avg': 36}, 'BBU': {'max': 34, 'min': 25, 'avg': 30}}, 'timestamp': None, 'save_status': None, 'vendor': 'nokia', 'availability': True, 'error_message': None, 'status': 'success'}, {'hostname': 'NS0003', 'ip': '10.8.234.157', 'temperature': {'RRU': {'max': 46, 'min': 16, 'avg': 33}, 'BBU': {'max': 30, 'min': 25, 'avg': 28}}, 'timestamp': None, 'save_status': None, 'vendor': 'nokia', 'availability': True, 'error_message': None, 'status': 'success'}, {'hostname': 'NS0004', 'ip': '10.8.231.201', 'temperature': {'RRU': {'max': 46, 'min': 28, 'avg': 34}, 'BBU': {'max': 32, 'min': 27, 'avg': 29}}, 'timestamp': None, 'save_status': None, 'vendor': 'nokia', 'availability': True, 'error_message': None, 'status': 'success'}, {'hostname': 'NS0005', 'ip': '10.8.224.5', 'temperature': {'RRU': {'max': 54, 'min': 46, 'avg': 49}, 'BBU': {'max': 40, 'min': 32, 'avg': 36}}, 'timestamp': None, 'save_status': None, 'vendor': 'nokia', 'availability': True, 'error_message': None, 'status': 'success'}, {'hostname': 'NS0007', 'ip': '10.8.224.9', 'temperature': {'RRU': {'max': 52, 'min': 29, 'avg': 38}, 'BBU': {'max': 30, 'min': 17, 'avg': 24}}, 'timestamp': None, 'save_status': None, 'vendor': 'nokia', 'availability': True, 'error_message': None, 'status': 'success'}, {'hostname': 'NS0008', 'ip': '10.8.231.225', 'temperature': {'RRU': {'max': 58, 'min': 19, 'avg': 33}, 'BBU': {'max': 38, 'min': 24, 'avg': 31}}, 'timestamp': None, 'save_status': None, 'vendor': 'nokia', 'availability': True, 'error_message': None, 'status': 'success'}, {'hostname': 'NS0010', 'ip': '10.8.234.57', 'temperature': {'RRU': {'max': 49, 'min': 31, 'avg': 41}, 'BBU': {'max': 48, 'min': 40, 'avg': 45}}, 'timestamp': None, 'save_status': None, 'vendor': 'nokia', 'availability': True, 'error_message': None, 'status': 'success'}, {'hostname': 'NS0011', 'ip': '10.8.224.13', 'temperature': {'RRU': {'max': 57, 'min': 20, 'avg': 35}, 'BBU': {'max': 45, 'min': 33, 'avg': 37}}, 'timestamp': None, 'save_status': None, 'vendor': 'nokia', 'availability': True, 'error_message': None, 'status': 'success'}, {'hostname': 'NS0012', 'ip': '10.8.233.105', 'temperature': {'RRU': {'max': 55, 'min': 14, 'avg': 35}, 'BBU': {'max': 35, 'min': 26, 'avg': 31}}, 'timestamp': None, 'save_status': None, 'vendor': 'nokia', 'availability': True, 'error_message': None, 'status': 'success'}, {'hostname': 'NS0013', 'ip': '10.8.233.177', 'temperature': {'RRU': {'max': 51, 'min': 26, 'avg': 38}, 'BBU': {'max': 46, 'min': 31, 'avg': 39}}, 'timestamp': None, 'save_status': None, 'vendor': 'nokia', 'availability': True, 'error_message': None, 'status': 'success'}]
    # preprocessed, _ = DataPreprocessor.preprocess(raw_data=data)
    # print(_)
