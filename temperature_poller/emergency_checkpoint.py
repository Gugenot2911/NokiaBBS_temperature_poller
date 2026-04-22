#!/usr/bin/env python3
"""
Аварийный контрольный пункт (checkpoint) для сохранения прогресса опроса.

Реализует:
- Сохранение прогресса на диск каждые N хостов
- Восстановление опроса после сбоя
- Атомарную запись через временный файл
- TTL кэша (не старше 2 часов)

Используется в PollingManager для защиты от потери прогресса при длинных опросах.
"""

import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from models import TemperatureResponse

logger = logging.getLogger(__name__)


class EmergencyCheckpoint:
    """Аварийный кэш прогресса опроса на HDD"""
    
    def __init__(
        self,
        checkpoint_path: str = "emergency_checkpoint.json",
        save_interval: int = 100
    ):
        """
        Инициализация аварийного контрольного пункта.
        
        Args:
            checkpoint_path: путь к файлу контрольной точки
            save_interval: сохранять каждые N обработанных хостов
        """
        self.checkpoint_path = Path(checkpoint_path)
        self.save_interval = save_interval
        self._processed_count = 0
        self._last_save_count = 0
    
    def save_progress(
        self,
        processed_hosts: List[TemperatureResponse],
        current_index: int
    ) -> None:
        """
        Сохранение прогресса на диск.
        
        Сохраняет только каждые N хостов (save_interval) для минимизации I/O.
        Использует атомарную запись через временный файл + rename.
        
        Args:
            processed_hosts: все обработанные хосты
            current_index: текущий индекс в общем списке (0-based)
        
        Пример:
            >>> checkpoint = EmergencyCheckpoint(save_interval=100)
            >>> checkpoint.save_progress(hosts, 99)  # Не сохранит
            >>> checkpoint.save_progress(hosts, 199)  # Сохранит
        """
        self._processed_count += 1
        
        # Пропускаем сохранение, если ещё не достигнут интервал
        if self._processed_count - self._last_save_count < self.save_interval:
            return
        
        # Формируем данные контрольной точки
        checkpoint_data = {
            'timestamp': datetime.now().isoformat(),
            'current_index': current_index,
            'processed_count': current_index + 1,
            'hosts_snapshot': [
                {
                    'hostname': h.hostname,
                    'ip': h.ip,
                    # status нет в TemperatureResponse, используем availability для определения статуса
                    'status': 'success' if h.availability else 'unavailable',
                    'timestamp': h.timestamp.isoformat() if h.timestamp else None,
                    'save_status': h.save_status,
                    'error_message': h.error_message
                }
                for h in processed_hosts[:current_index + 1]
            ]
        }
        
        # Атомарная запись через temp file + rename
        temp_path = self.checkpoint_path.with_suffix('.tmp')
        try:
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(checkpoint_data, f, ensure_ascii=False, indent=2)
            
            # Атомарный rename (работает на большинстве ФС)
            temp_path.replace(self.checkpoint_path)
            self._last_save_count = self._processed_count
            
            logger.info(
                f"Checkpoint сохранён: хост {current_index + 1}, "
                f"файл: {self.checkpoint_path}"
            )
            
        except Exception as e:
            logger.error(f"Ошибка сохранения checkpoint: {e}")
            # Не прерываем опрос - продолжаем без сохранения
    
    def load_checkpoint(self) -> Optional[Dict[str, Any]]:
        """
        Загрузка аварийного кэша с диска.
        
        Returns:
            Словарь с данными контрольной точки или None если файл не найден
        
        Пример:
            >>> checkpoint = EmergencyCheckpoint()
            >>> data = checkpoint.load_checkpoint()
            >>> if data:
            ...     print(f"Восстанавливаем с хоста {data['current_index']}")
        """
        if not self.checkpoint_path.exists():
            return None
        
        try:
            with open(self.checkpoint_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Проверка валидности структуры
            required_fields = ['current_index', 'hosts_snapshot']
            if not all(field in data for field in required_fields):
                logger.warning("Невалидный checkpoint (отсутствуют поля), игнорируем")
                return None
            
            logger.info(
                f"Найден checkpoint: хост {data['current_index'] + 1}, "
                f"время: {data['timestamp']}"
            )
            
            return data
            
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка парсинга checkpoint (повреждён файл): {e}")
            return None
        except Exception as e:
            logger.error(f"Ошибка чтения checkpoint: {e}")
            return None
    
    def clear_checkpoint(self) -> None:
        """
        Очистка аварийного кэша после успешного завершения опроса.
        
        Пример:
            >>> checkpoint = EmergencyCheckpoint()
            >>> # После успешного опроса:
            >>> checkpoint.clear_checkpoint()
        """
        if self.checkpoint_path.exists():
            self.checkpoint_path.unlink()
            logger.info("Checkpoint очищен после успешного опроса")
    
    def should_resume(
        self,
        hosts: List[TemperatureResponse],
        max_age_hours: float = 2.0
    ) -> bool:
        """
        Проверка, нужно ли восстанавливать опрос из контрольной точки.
        
        Возвращает True если:
        - Есть валидный checkpoint файл
        - Предыдущий опрос не был завершён
        - Checkpoint не старше max_age_hours
        
        Args:
            hosts: полный список хостов для опроса
            max_age_hours: максимальный возраст checkpoint в часах
        
        Returns:
            True если нужно продолжить опрос, False если начать заново
        
        Пример:
            >>> checkpoint = EmergencyCheckpoint()
            >>> if checkpoint.should_resume(hosts):
            ...     data = checkpoint.load_checkpoint()
            ...     start_index = data['current_index'] + 1
        """
        checkpoint = self.load_checkpoint()
        if not checkpoint:
            return False
        
        # Проверка: совпадает ли количество хостов
        checkpoint_count = checkpoint.get('processed_count', 0)
        if checkpoint_count >= len(hosts):
            logger.info(
                f"Предыдущий опрос уже завершён ({checkpoint_count} >= {len(hosts)}), "
                "начинаем заново"
            )
            self.clear_checkpoint()
            return False
        
        # Проверка TTL checkpoint
        try:
            checkpoint_time = datetime.fromisoformat(checkpoint['timestamp'])
            age = datetime.now() - checkpoint_time
            
            if age > timedelta(hours=max_age_hours):
                logger.warning(
                    f"Checkpoint старше {max_age_hours} часов ({age}), "
                    "начинаем заново"
                )
                self.clear_checkpoint()
                return False
                
        except Exception as e:
            logger.warning(f"Ошибка проверки возраста checkpoint: {e}")
            return False
        
        logger.info(
            f"Восстановление опроса: "
            f"пройдено {checkpoint_count} из {len(hosts)} хостов"
        )
        return True
    
    def get_checkpoint_status(self) -> Dict[str, Any]:
        """
        Получение статуса контрольной точки без изменения состояния.
        
        Returns:
            Словарь со статусом checkpoint
        """
        if not self.checkpoint_path.exists():
            return {
                'exists': False,
                'message': 'Checkpoint не найден'
            }
        
        try:
            data = self.load_checkpoint()
            if not data:
                return {
                    'exists': True,
                    'valid': False,
                    'message': 'Checkpoint повреждён'
                }
            
            age = datetime.now() - datetime.fromisoformat(data['timestamp'])
            
            return {
                'exists': True,
                'valid': True,
                'current_index': data['current_index'],
                'processed_count': data['processed_count'],
                'timestamp': data['timestamp'],
                'age_seconds': age.total_seconds(),
                'is_fresh': age < timedelta(hours=2)
            }
            
        except Exception as e:
            return {
                'exists': True,
                'valid': False,
                'message': f'Ошибка: {e}'
            }
