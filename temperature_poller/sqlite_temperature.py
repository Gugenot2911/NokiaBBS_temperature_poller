#!/usr/bin/env python3
"""
Модуль для работы с температурными данными базовых станций.
Реализует трехэтапный алгоритм получения данных для фронтенда:
- Уровень 1: Флаги аномалий (1 бит на хост) - быстрая загрузка таблицы
- Уровень 2: Бинарная тепловая шкала (48 бит) - при разворачивании строки
- Уровень 3: Полные спарклайны (48 значений) - при клике для детального просмотра

Аномалия определяется по ЛЮБОМУ из параметров (max, min, avg):
- Температура < 15°C (ниже нормы)
- Температура >= 60°C (выше нормы, включая 60)
"""

import sqlite3
import os
import re
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Any
from pathlib import Path
from dataclasses import dataclass
import threading
import time


# Настройка логирования
logger = logging.getLogger(__name__)


# ============================================================================
# Конфигурация
# ============================================================================

@dataclass
class DatabaseConfig:
    """Конфигурация БД"""
    base_dir: str = "databases"
    prefix: Optional[str] = None
    digits: int = 4
    auto_cleanup_days: int = 60
    min_normal_temp: int = 15
    max_normal_temp: int = 60
    anomaly_window_hours: int = 48
    
    def is_anomaly(self, max_temp: Optional[int], min_temp: Optional[int], avg_temp: Optional[int]) -> bool:
        """
        Проверка температуры на аномалию.
        Аномалия: ЛЮБОЕ значение (max/min/avg) выходит за пределы нормы.
        
        Норма: 15°C <= temp < 60°C
        Аномалия: temp < 15°C ИЛИ temp >= 60°C
        
        Args:
            max_temp: максимальная температура
            min_temp: минимальная температура
            avg_temp: средняя температура
        
        Returns:
            True если есть аномалия, False если всё в норме или значения None
        """
        def is_out_of_range(temp: Optional[int]) -> bool:
            # ✅ Защита от None: пропускаем проверку для None значений
            if temp is None:
                return False
            return temp < self.min_normal_temp or temp >= self.max_normal_temp
        
        return (is_out_of_range(max_temp) or 
                is_out_of_range(min_temp) or 
                is_out_of_range(avg_temp))
    
    def is_anomaly_single(self, temp: Optional[int]) -> bool:
        """Проверка одного значения на аномалию"""
        if temp is None:
            return False
        return temp < self.min_normal_temp or temp >= self.max_normal_temp
        
    def get_bit_position(self, hour: int) -> int:
        """
        Вычисление позиции бита для данного часа.
        
        Окно: 48 часов (двое суток), биты от 0 до 47
        Бит 47 = самый старый час (current_hour - 47)
        Бит 0 = текущий час (current_hour)
        
        Args:
            hour: абсолютный номер часа (timestamp // 3600)
        
        Returns:
            позиция бита (0-47)
        """
        return self.anomaly_window_hours - 1 - (hour % self.anomaly_window_hours)


# ============================================================================
# Основной класс БД
# ============================================================================

class TemperatureDatabase:
    """
    Основной класс для работы с БД температурных данных.
    Реализует запись и трехэтапное чтение.
    """
    
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.db_path: Optional[str] = None
        self._local = threading.local()
    
    # ------------------------------------------------------------------------
    # Инициализация и подключение
    # ------------------------------------------------------------------------
    
    def init_from_data(self, raw_data: List[Dict]) -> bool:
        """Инициализация БД на основе сырых данных (автоопределение префикса)"""
        prefix = self._extract_prefix(raw_data)
        if not prefix:
            print("Ошибка: не удалось определить префикс региона")
            return False
        
        self.config.prefix = prefix
        self.db_path = self._get_db_path(prefix)
        
        Path(self.config.base_dir).mkdir(parents=True, exist_ok=True)
        self._init_tables()
        return True
    
    def _get_db_path(self, prefix: str) -> str:
        """Формирование пути к файлу БД"""
        return os.path.join(self.config.base_dir, f"{prefix}_temperature_eNode.db")
    
    def _extract_prefix(self, raw_data: List[Dict]) -> Optional[str]:
        """Извлечение префикса региона из сырых данных"""
        prefixes = set()
        for station in raw_data:
            hostname = station.get('hostname')
            if hostname:
                match = re.match(r'^([A-Za-z]+)\d+', hostname)
                if match:
                    prefixes.add(match.group(1).upper())
        return list(prefixes)[0] if prefixes else None
    
    def _get_connection(self):
        """Получение потокобезопасного соединения с обработкой ошибок"""
        if not hasattr(self._local, 'connection') or self._local.connection is None:
            try:
                self._local.connection = sqlite3.connect(
                    self.db_path, timeout=30.0, isolation_level=None, cached_statements=100
                )
                self._local.connection.execute("PRAGMA journal_mode = WAL")
                self._local.connection.execute("PRAGMA synchronous = NORMAL")
                self._local.connection.execute("PRAGMA cache_size = -20000")
                # Проверка работоспособности
                self._local.connection.execute("SELECT 1")
            except sqlite3.Error as e:
                self._local.connection = None
                logger.error(f"Ошибка подключения к БД {self.db_path}: {e}")
                raise ConnectionError(f"Database connection failed: {e}")
        return self._local.connection
    
    def _init_tables(self):
        """Инициализация таблиц БД"""
        conn = self._get_connection()
        
        # Таблица 1: основная (полная история)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS temps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bs INTEGER NOT NULL,
                dt INTEGER NOT NULL,
                mx SMALLINT NOT NULL,
                mn SMALLINT NOT NULL,
                av SMALLINT NOT NULL,
                ts INTEGER NOT NULL,
                hour INTEGER NOT NULL,
                UNIQUE(bs, dt, ts)
            )
        ''')
        
        # Индексы для основной таблицы
        conn.execute('CREATE INDEX IF NOT EXISTS idx_bs_hour ON temps(bs, hour)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_hour ON temps(hour)')
        # Индекс для быстрых запросов по времени (get_level3)
        conn.execute('CREATE INDEX IF NOT EXISTS idx_bs_hour_time ON temps(bs, hour, dt)')
        
        # Таблица 2: битовый кэш аномалий (для уровней 1 и 2)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS anomaly_flags (
                bs INTEGER PRIMARY KEY,
                rru_bits INTEGER NOT NULL DEFAULT 0,
                bbu_bits INTEGER NOT NULL DEFAULT 0,
                updated_at INTEGER NOT NULL
            )
        ''')
        
        # Таблица 3: метаданные
        conn.execute('''
            CREATE TABLE IF NOT EXISTS meta (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated INTEGER
            )
        ''')
        
        now_ts = int(datetime.now().timestamp())
        conn.execute('INSERT OR REPLACE INTO meta VALUES (?, ?, ?)', 
                     ('prefix', self.config.prefix, now_ts))
        conn.execute('INSERT OR REPLACE INTO meta VALUES (?, ?, ?)', 
                     ('digits', str(self.config.digits), now_ts))
        
        conn.commit()
    
    # ------------------------------------------------------------------------
    # Запись данных (уровень 0 - опрос устройств)
    # ------------------------------------------------------------------------
    
    def write_batch(self, stations: List[Dict], custom_timestamp: Optional[int] = None) -> int:
        """
        Запись пакета данных от устройств.
        При записи выполняется анализ аномалий по ВСЕМ параметрам (max/min/avg)
        и обновление битового кэша.
        
        Args:
            stations: список станций в формате [{'id': 830, 'rru': (48,2,24), 'bbu': (34,28,32)}]
            custom_timestamp: пользовательский timestamp (для тестов)
        
        Returns:
            количество вставленных записей
        """
        if not stations or not self.db_path:
            return 0
        
        conn = self._get_connection()
        conn.execute("PRAGMA synchronous = OFF")
        
        timestamp = custom_timestamp or int(datetime.now().timestamp())
        current_hour = timestamp // 3600
        
        batch_temps = []
        anomaly_updates = {}
        inserted = 0
        
        logger.info(f"Запись {len(stations)} станций, час={current_hour}")
        
        for station in stations:
            bs_id = station.get('id')
            if not bs_id:
                continue
            
            # RRU (dt=1)
            rru = station.get('rru')
            if rru and isinstance(rru, (tuple, list)) and len(rru) == 3:
                max_t, min_t, avg_t = rru
                
                # Сохраняем в основную таблицу
                batch_temps.append((bs_id, 1, max_t, min_t, avg_t, timestamp, current_hour))
                inserted += 1
                
                # ✅ Проверка аномалии по ВСЕМ параметрам (max, min, avg)
                is_anomaly = self.config.is_anomaly(max_t, min_t, avg_t)
                
                if is_anomaly:
                    logger.warning(f"Аномалия RRU BS{bs_id}: max={max_t}°C, min={min_t}°C, avg={avg_t}°C")
                
                if bs_id not in anomaly_updates:
                    anomaly_updates[bs_id] = {'rru': 0, 'bbu': 0}
                
                bit_pos = self.config.get_bit_position(current_hour)
                if is_anomaly:
                    anomaly_updates[bs_id]['rru'] |= (1 << bit_pos)
            
            # BBU (dt=2)
            bbu = station.get('bbu')
            if bbu and isinstance(bbu, (tuple, list)) and len(bbu) == 3:
                max_t, min_t, avg_t = bbu
                
                batch_temps.append((bs_id, 2, max_t, min_t, avg_t, timestamp, current_hour))
                inserted += 1
                
                # ✅ Проверка аномалии по ВСЕМ параметрам (max, min, avg)
                is_anomaly = self.config.is_anomaly(max_t, min_t, avg_t)
                
                if is_anomaly:
                    logger.warning(f"Аномалия BBU BS{bs_id}: max={max_t}°C, min={min_t}°C, avg={avg_t}°C")
                
                if bs_id not in anomaly_updates:
                    anomaly_updates[bs_id] = {'rru': 0, 'bbu': 0}
                
                bit_pos = self.config.get_bit_position(current_hour)
                if is_anomaly:
                    anomaly_updates[bs_id]['bbu'] |= (1 << bit_pos)
            
            # Пакетная вставка
            if len(batch_temps) >= 1000:
                self._insert_batch_temps(conn, batch_temps)
                batch_temps = []
        
        # Вставка остатка
        if batch_temps:
            self._insert_batch_temps(conn, batch_temps)
        
        # Обновление битового кэша
        self._update_anomaly_flags(conn, anomaly_updates, current_hour, timestamp)
        
        # Очистка старых данных
        self._cleanup_old_data(conn, current_hour)
        
        conn.execute("PRAGMA synchronous = NORMAL")
        
        return inserted
    
    def _insert_batch_temps(self, conn, batch: List):
        """Пакетная вставка в основную таблицу с защитой от дубликатов"""
        conn.executemany('''
            INSERT INTO temps (bs, dt, mx, mn, av, ts, hour)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(bs, dt, ts) DO UPDATE SET
                mx = excluded.mx,
                mn = excluded.mn,
                av = excluded.av
        ''', batch)
    
    def _update_anomaly_flags(self, conn, updates: Dict, current_hour: int, timestamp: int):
        """Обновление битового кэша аномалий с обработкой NULL-битов"""
        for bs_num, bits in updates.items():
            # Получаем текущие биты
            row = conn.execute('SELECT rru_bits, bbu_bits FROM anomaly_flags WHERE bs = ?', 
                               (bs_num,)).fetchone()
            
            # ✅ Исправлено: обработка NULL через 'or 0'
            if row:
                new_rru = (row[0] or 0) | (bits['rru'] or 0)
                new_bbu = (row[1] or 0) | (bits['bbu'] or 0)
            else:
                new_rru = bits['rru'] or 0
                new_bbu = bits['bbu'] or 0
            
            conn.execute('''
                INSERT OR REPLACE INTO anomaly_flags (bs, rru_bits, bbu_bits, updated_at)
                VALUES (?, ?, ?, ?)
            ''', (bs_num, new_rru, new_bbu, timestamp))
    
    def _cleanup_old_data(self, conn, current_hour: int):
        """
        Очистка устаревших данных:
        1. Биты в anomaly_flags старше 48 часов
        2. Записи в temps старше auto_cleanup_days (60 дней по умолчанию)
        
        Args:
            conn: подключение к БД
            current_hour: текущий час (timestamp // 3600)
        """
        start_time = time.perf_counter()
        
        # 1. Очистка битов в anomaly_flags (окно 48 часов)
        mask = (1 << self.config.anomaly_window_hours) - 1
        bits_cleaned = 0
        
        with conn:
            for row in conn.execute('SELECT bs, rru_bits, bbu_bits FROM anomaly_flags'):
                bs_num, rru_bits, bbu_bits = row
                new_rru = (rru_bits or 0) & mask
                new_bbu = (bbu_bits or 0) & mask
                
                if new_rru != (rru_bits or 0) or new_bbu != (bbu_bits or 0):
                    conn.execute('''
                        UPDATE anomaly_flags SET rru_bits = ?, bbu_bits = ?, updated_at = ?
                        WHERE bs = ?
                    ''', (new_rru, new_bbu, int(datetime.now().timestamp()), bs_num))
                    bits_cleaned += 1
            
            # 2. Очистка старых записей из temps (старше auto_cleanup_days)
            cutoff_hour = current_hour - (self.config.auto_cleanup_days * 24)
            deleted = conn.execute('''
                DELETE FROM temps WHERE hour < ?
            ''', (cutoff_hour,)).rowcount
            
            if deleted > 0:
                logger.info(f"Удалено {deleted} записей из temps старше {self.config.auto_cleanup_days} дней (hour < {cutoff_hour})")
            
            # VACUUM только раз в сутки (при current_hour кратном 24)
            if current_hour % 24 == 0 and deleted > 1000:
                logger.debug("Выполнение VACUUM для освобождения места...")
                conn.execute("VACUUM")
        
        elapsed = time.perf_counter() - start_time
        if bits_cleaned > 0 or deleted > 0:
            logger.debug(f"Очистка завершена: битов={bits_cleaned}, записей={deleted}, время={elapsed*1000:.2f} мс")
    
    # ------------------------------------------------------------------------
    # Чтение данных (уровни 1, 2, 3 для фронтенда)
    # ------------------------------------------------------------------------

    def get_level1(self, page: int = 1, page_size: int = 10) -> Dict:
        """
        Уровень 1: получение флагов аномалий для таблицы.
        Время выполнения: 1-5 мс.

        Returns:
            Dict с данными уровня 1
        """
        if not self.db_path:
            return {
                "level": 1,
                "page": page,
                "page_size": page_size,
                "total_pages": 0,
                "total_stations": 0,
                "data": []
            }

        conn = self._get_connection()
        offset = (page - 1) * page_size
        
        rows = conn.execute('''
            SELECT bs, rru_bits, bbu_bits,
                   (rru_bits > 0 OR bbu_bits > 0) as has_anomaly
            FROM anomaly_flags
            ORDER BY bs
            LIMIT ? OFFSET ?
        ''', (page_size, offset)).fetchall()

        total = conn.execute('SELECT COUNT(*) FROM anomaly_flags').fetchone()[0]

        data = []
        for row in rows:
            data.append({
                "hostname": f"NS{row[0]:04d}",
                "has_anomaly": bool(row[3]),
                "rru_bits": row[1],
                "bbu_bits": row[2]
            })

        return {
            "level": 1,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size if total > 0 else 0,
            "total_stations": total,
            "data": data
        }
    
    def get_level2(self, hostname: str):
        """
        Уровень 2: получение бинарной тепловой шкалы (48 бит) для хоста.
        Время выполнения: 1-2 мс.
        
        Args:
            hostname: имя хоста (например, "NS0830")
        
        Returns:
            dict с битовыми строками
        
        Raises:
            ValueError: если формат hostname некорректен
        """
        # ✅ Исправлено: валидация ДО проверки db_path
        if not re.match(r'^[A-Z]+\d{4}$', hostname):
            raise ValueError(f"Invalid hostname format: {hostname}. Expected format: PREFIX+4digits (e.g., NS0830)")
        
        if not self.db_path:
            return {"hostname": hostname, "rru_bits": "0"*48, "bbu_bits": "0"*48,
                    "rru_anomaly_count": 0, "bbu_anomaly_count": 0}
        
        try:
            # Извлекаем номер станции после префикса (TEST1111 → 1111)
            match = re.match(r'^[A-Z]+(\d{4})$', hostname)
            bs_num = int(match.group(1))
        except (ValueError, AttributeError):
            raise ValueError(f"Invalid hostname: {hostname}")
        
        start_time = time.perf_counter()
        conn = self._get_connection()
        row = conn.execute('SELECT rru_bits, bbu_bits FROM anomaly_flags WHERE bs = ?', 
                           (bs_num,)).fetchone()
        elapsed = time.perf_counter() - start_time
        logger.debug(f"get_level2 для {hostname}: {elapsed*1000:.2f} мс")
        
        if not row:
            return {"hostname": hostname, "rru_bits": "0"*48, "bbu_bits": "0"*48,
                    "rru_anomaly_count": 0, "bbu_anomaly_count": 0}
        
        # ✅ Исправлено: обработка NULL через 'or 0'
        rru_bits = row[0] or 0
        bbu_bits = row[1] or 0
        
        return {
            "level": 2,
            "hostname": hostname,
            "rru_bits": format(rru_bits, '048b'),
            "bbu_bits": format(bbu_bits, '048b'),
            "rru_anomaly_count": bin(rru_bits).count('1'),
            "bbu_anomaly_count": bin(bbu_bits).count('1')
        }
    
    def get_level3(self, hostname: str, hours: int = 48):
        """
        Уровень 3: получение полных спарклайнов (48 значений) для детального просмотра.
        Время выполнения: 20-50 мс.
        
        Args:
            hostname: имя хоста (например, "NS0830")
            hours: количество часов для извлечения (по умолчанию 48)
        
        Returns:
            dict с массивами температур
        
        Raises:
            ValueError: если формат hostname некорректен
        """
        # ✅ Исправлено: валидация ДО проверки db_path
        if not re.match(r'^[A-Z]+\d{4}$', hostname):
            raise ValueError(f"Invalid hostname format: {hostname}")
        
        if not self.db_path:
            return {"hostname": hostname, "rru_values": [], "bbu_values": [], "hours": []}
        
        try:
            # Извлекаем номер станции после префикса (TEST1111 → 1111)
            match = re.match(r'^[A-Z]+(\d{4})$', hostname)
            bs_num = int(match.group(1))
        except (ValueError, AttributeError):
            raise ValueError(f"Invalid hostname: {hostname}")
        
        start_time = time.perf_counter()
        conn = self._get_connection()
        
        current_hour = int(datetime.now().timestamp()) // 3600
        start_hour = current_hour - hours
        
        rows = conn.execute('''
            SELECT hour, dt, mx, mn, av
            FROM temps
            WHERE bs = ? AND hour >= ?
            ORDER BY hour
        ''', (bs_num, start_hour)).fetchall()
        
        # Формируем массивы фиксированной длины
        rru_max = [None] * hours
        rru_min = [None] * hours
        rru_avg = [None] * hours
        bbu_max = [None] * hours
        bbu_min = [None] * hours
        bbu_avg = [None] * hours
        timestamps = []
        
        for row in rows:
            hour = row[0]
            idx = hours - 1 - (current_hour - hour)
            if 0 <= idx < hours:
                if row[1] == 1:  # RRU
                    rru_max[idx] = row[2]
                    rru_min[idx] = row[3]
                    rru_avg[idx] = row[4]
                else:  # BBU
                    bbu_max[idx] = row[2]
                    bbu_min[idx] = row[3]
                    bbu_avg[idx] = row[4]
        
        # Заполняем метки времени
        for i in range(hours):
            hour_ts = (current_hour - (hours - 1 - i)) * 3600
            timestamps.append(hour_ts)
        
        elapsed = time.perf_counter() - start_time
        logger.debug(f"get_level3 для {hostname}: {elapsed*1000:.2f} мс, записей={len(rows)}")
        
        return {
            "level": 3,
            "hostname": hostname,
            "rru_max": rru_max,
            "rru_min": rru_min,
            "rru_avg": rru_avg,
            "bbu_max": bbu_max,
            "bbu_min": bbu_min,
            "bbu_avg": bbu_avg,
            "hours": timestamps
        }

    def get_stations_list(self) -> List[str]:
        """Получение списка всех станций с префиксом"""
        if not self.db_path:
            return []
        conn = self._get_connection()
        rows = conn.execute('SELECT bs FROM anomaly_flags ORDER BY bs').fetchall()
        return [f"NS{row[0]:04d}" for row in rows]

    def get_statistics(self) -> Dict:
        """Получение общей статистики"""
        if not self.db_path:
            return {}
        conn = self._get_connection()
        
        total_stations = conn.execute('SELECT COUNT(*) FROM anomaly_flags').fetchone()[0]
        total_with_anomaly = conn.execute(
            'SELECT COUNT(*) FROM anomaly_flags WHERE rru_bits > 0 OR bbu_bits > 0'
        ).fetchone()[0]
        
        return {
            'total_stations': total_stations,
            'stations_with_anomaly': total_with_anomaly,
            'anomaly_percentage': round(total_with_anomaly / total_stations * 100, 1) if total_stations else 0
        }

    def cleanup_old_data(self, days: Optional[int] = None) -> Dict:
        """
        Ручная очистка старых данных из БД.
        
        Удаляет записи из таблицы temps старше указанного количества дней.
        Автоматически вызывается при каждой записи новых данных (через _cleanup_old_data).
        
        Args:
            days: количество дней для сохранения (по умолчанию auto_cleanup_days=60)
        
        Returns:
            Dict со статистикой удалённых данных:
            {
                'deleted': int,      # количество удалённых записей
                'remaining': int,    # количество оставшихся записей
                'cutoff_hour': int,  # пороговое значение hour
                'days': int          # использованное количество дней
            }
        
        Пример:
            >>> db = TemperatureDatabase(config)
            >>> result = db.cleanup_old_data(days=90)
            >>> print(f"Удалено {result['deleted']} записей")
        """
        if not self.db_path:
            return {'deleted': 0, 'remaining': 0, 'cutoff_hour': 0, 'days': 0}
        
        if days is None:
            days = self.config.auto_cleanup_days
        
        current_hour = int(datetime.now().timestamp()) // 3600
        cutoff_hour = current_hour - (days * 24)
        
        conn = self._get_connection()
        
        # Подсчёт записей до удаления
        total_before = conn.execute('SELECT COUNT(*) FROM temps').fetchone()[0]
        
        # Удаление старых записей
        with conn:
            deleted = conn.execute('''
                DELETE FROM temps WHERE hour < ?
            ''', (cutoff_hour,)).rowcount
            
            # VACUUM для освобождения места (если удалено много записей)
            if deleted > 1000:
                logger.info(f"Выполнение VACUUM после удаления {deleted} записей...")
                conn.execute("VACUUM")
        
        # Подсчёт после удаления
        total_after = conn.execute('SELECT COUNT(*) FROM temps').fetchone()[0]
        
        logger.info(f"Очистка данных: удалено {deleted} записей старше {days} дней, осталось {total_after}")
        
        return {
            'deleted': deleted,
            'remaining': total_after,
            'cutoff_hour': cutoff_hour,
            'days': days
        }
    
    def get_db_size_info(self) -> Dict:
        """
        Получение информации о размере БД и количестве записей.
        
        Returns:
            Dict со статистикой:
            {
                'path': str,              # путь к файлу БД
                'size_mb': float,         # размер файла в МБ
                'temps_count': int,       # количество записей в temps
                'anomaly_flags_count': int,  # количество станций в anomaly_flags
                'oldest_hour': int,       # самый старый час в БД
                'newest_hour': int,       # самый новый час в БД
                'data_range_days': float  # диапазон данных в днях
            }
        """
        if not self.db_path:
            return {}
        
        conn = self._get_connection()
        
        # Размер файла
        size_mb = round(os.path.getsize(self.db_path) / 1024 / 1024, 2) if os.path.exists(self.db_path) else 0
        
        # Количество записей
        temps_count = conn.execute('SELECT COUNT(*) FROM temps').fetchone()[0]
        anomaly_flags_count = conn.execute('SELECT COUNT(*) FROM anomaly_flags').fetchone()[0]
        
        # Диапазон данных
        hour_range = conn.execute('SELECT MIN(hour), MAX(hour) FROM temps').fetchone()
        oldest_hour = hour_range[0] or 0
        newest_hour = hour_range[1] or 0
        data_range_days = round((newest_hour - oldest_hour) / 24, 1) if oldest_hour and newest_hour else 0
        
        return {
            'path': self.db_path,
            'size_mb': size_mb,
            'temps_count': temps_count,
            'anomaly_flags_count': anomaly_flags_count,
            'oldest_hour': oldest_hour,
            'newest_hour': newest_hour,
            'data_range_days': data_range_days
        }


# ============================================================================
# Предобработчик сырых данных
# ============================================================================

class DataPreprocessor:
    """Предобработчик сырых данных перед записью в БД"""
    
    @staticmethod
    def preprocess(raw_data: List[Dict]) -> Tuple[List[Dict], List[str]]:
        """
        Преобразование сырых данных в формат для записи.
        
        Args:
            raw_data: сырые данные от устройств
        
        Returns:
            tuple: (optimized_data, errors) - оптимизированные данные и список ошибок валидации
        """
        prefix = None
        optimized = []
        errors = []
        
        for i, station in enumerate(raw_data):
            hostname = station.get('hostname')
            temp_data = station.get('temperature')
            
            if not hostname:
                errors.append(f"Запись {i}: отсутствует hostname")
                continue
            
            if not temp_data:
                # Проверяем статус - ошибки тоже сохраняем
                if station.get('status') not in ('error', 'unavailable', 'skipped_vendor'):
                    errors.append(f"Запись {i} ({hostname}): отсутствует температура")
                continue
            
            if isinstance(temp_data, dict) and 'error' in temp_data:
                # Хост недоступен, но сохраняем для статистики
                optimized.append({'id': 0, 'hostname': hostname, 'unavailable': True})
                continue
            
            if station.get('status') != 'success' or not station.get('availability', False):
                continue
            
            # Определяем префикс
            if prefix is None:
                match = re.match(r'^([A-Za-z]+)\d+', hostname)
                if match:
                    prefix = match.group(1).upper()
            
            if prefix and not hostname.startswith(prefix):
                continue
            
            try:
                bs_num = int(hostname[len(prefix):] if prefix else hostname[2:])
            except (ValueError, IndexError):
                errors.append(f"Запись {i} ({hostname}): ошибка парсинга номера станции")
                continue
            
            record = {'id': bs_num}
            
            # ✅ Валидация температуры с защитой от None
            has_valid_temp = False
            
            if 'RRU' in temp_data:
                rru = temp_data['RRU']
                if isinstance(rru, dict):
                    # Защита от None значений
                    max_val = rru.get('max')
                    min_val = rru.get('min')
                    avg_val = rru.get('avg')
                    
                    # Проверяем, что хотя бы одно значение валидно
                    if any(isinstance(v, (int, float)) for v in [max_val, min_val, avg_val]):
                        record['rru'] = (max_val, min_val, avg_val)
                        has_valid_temp = True
                    else:
                        errors.append(f"Запись {i} ({hostname}): RRU содержит только None значения")
            
            if 'BBU' in temp_data:
                bbu = temp_data['BBU']
                if isinstance(bbu, dict):
                    # Защита от None значений
                    max_val = bbu.get('max')
                    min_val = bbu.get('min')
                    avg_val = bbu.get('avg')
                    
                    # Проверяем, что хотя бы одно значение валидно
                    if any(isinstance(v, (int, float)) for v in [max_val, min_val, avg_val]):
                        record['bbu'] = (max_val, min_val, avg_val)
                        has_valid_temp = True
                    else:
                        errors.append(f"Запись {i} ({hostname}): BBU содержит только None значения")
            
            if not has_valid_temp and 'rru' not in record and 'bbu' not in record:
                errors.append(f"Запись {i} ({hostname}): нет валидных данных температуры")
                continue
            
            if 'rru' in record or 'bbu' in record:
                optimized.append(record)
        
        return optimized, errors


# ============================================================================
# Менеджер для работы с несколькими регионами
# ============================================================================

class TemperatureDBManager:
    """Менеджер для работы с БД разных регионов"""
    
    def __init__(self, base_dir: str = "databases"):
        self.base_dir = base_dir
        self._databases: Dict[str, TemperatureDatabase] = {}
    
    def _extract_prefix(self, raw_data: List[Dict]) -> Optional[str]:
        """Извлечение префикса региона из данных"""
        for station in raw_data:
            hostname = station.get('hostname')
            # hostname = station.get('id')
            if hostname:
                match = re.match(r'^([A-Za-z]+)\d+', hostname)
                if match:
                    return match.group(1).upper()
        return None
    
    def get_db(self, raw_data: List[Dict]) -> TemperatureDatabase:
        """Получить или создать БД для региона на основе данных"""
        prefix = self._extract_prefix(raw_data)
        if not prefix:
            raise ValueError("Cannot detect region prefix from data")

        if prefix not in self._databases:
            config = DatabaseConfig(base_dir=self.base_dir, prefix=prefix)
            db = TemperatureDatabase(config)
            db.init_from_data(raw_data)
            self._databases[prefix] = db
        
        return self._databases[prefix]
    
    def get_db_by_prefix(self, prefix: str) -> Optional[TemperatureDatabase]:
        """Получение БД по префиксу региона"""
        return self._databases.get(prefix)
    
    def list_databases(self) -> List[Dict]:
        """Список всех БД в директории"""
        databases = []
        if not os.path.exists(self.base_dir):
            return databases
        
        for filename in os.listdir(self.base_dir):
            if filename.endswith("_temperature_eNode.db"):
                prefix = filename.replace("_temperature_eNode.db", "")
                db_path = os.path.join(self.base_dir, filename)
                
                try:
                    conn = sqlite3.connect(db_path)
                    total = conn.execute("SELECT COUNT(*) FROM anomaly_flags").fetchone()[0]
                    conn.close()
                    databases.append({
                        'prefix': prefix,
                        'path': db_path,
                        'size_mb': round(os.path.getsize(db_path) / 1024 / 1024, 2),
                        'stations': total
                    })
                except Exception:
                    databases.append({
                        'prefix': prefix,
                        'path': db_path,
                        'size_mb': round(os.path.getsize(db_path) / 1024 / 1024, 2),
                        'stations': 0
                    })
        return databases

if __name__ == "__main__":

    data = [
        {"id": "NS1120", "ip": "10.8.227ав", "vendor": "nokia", "voltage": None, "alarms": None,
         "temperature": None, "status": ""},
        {"hostname": "NS1111", "ip": "10.8.227.209", "vendor": "nokia", "voltage": None, "alarms": None,
         "temperature": None, "status": ""},
        {"hostname": "NS0830", "ip": "10.8.239.189", "vendor": "nokia", "voltage": None, "alarms": None,
         "temperature": None, "status": ""},
        {"hostname": "NS1830", "ip": "10.148.233.137", "vendor": "nokia", "voltage": None, "alarms": None,
         "temperature": None, "status": ""}
    ]

    temp = TemperatureDBManager
    pref = temp()._extract_prefix(raw_data=data)

    print(pref)