# Менеджер опроса сетевых устройств

Система автоматического опроса температурных данных с сетевого оборудования Nokia с поддержкой аварийного восстановления и ручного управления.

## 📋 Содержание

- [Архитектура](#архитектура)
- [Компоненты](#компоненты)
- [Установка](#установка)
- [Использование](#использование)
- [Конфигурация](#конфигурация)
- [Тестирование](#тестирование)
- [Логирование](#логирование)
- [Аварийное восстановление](#аварийное-восстановление)

---

## 🏗️ Архитектура

```
┌─────────────────────────────────────────────────────────┐
│                    PollingManager                        │
│  ┌──────────────────────────────────────────────────┐   │
│  │  HostCache (RAM)                                  │   │
│  │  - Список хостов с TTL (24 часа)                  │   │
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
```

---

## 📦 Компоненты

| Файл | Описание |
|------|----------|
| `polling_manager.py` | Основной менеджер опроса |
| `emergency_checkpoint.py` | Аварийное сохранение прогресса |
| `logging_config.py` | Конфигурация логирования |
| `test_polling_manager.py` | Тесты с МОК-данными |
| `models.py` | Pydantic модели данных |
| `get_nokia_measurements.py` | Модуль опроса оборудования |
| `sqlite_temperature.py` | Работа с базой данных |

---

## 🚀 Установка

### Требования

- Python 3.10+
- Pydantic 2.x
- requests
- pytest (для тестов)
- pytest-asyncio (для асинхронных тестов)

### Установка зависимостей

```bash
pip install pydantic requests pytest pytest-asyncio
```

---

## 💻 Использование

### Быстрый старт

```python
import asyncio
from polling_manager import create_polling_manager

# Создание менеджера
manager = create_polling_manager(
    api_url="http://api.example.com/hosts",
    chunk_size=10,
    checkpoint_interval=100
)

# Запуск автоматического цикла (бесконечно)
asyncio.run(manager.run_automatic())
```

### Ручной опрос

```python
import asyncio
from polling_manager import create_polling_manager

manager = create_polling_manager(api_url="http://api.example.com/hosts")

# Опрос конкретных хостов
result = asyncio.run(manager.manual_poll(["NS0830", "NS1120"]))

print(f"Успешно: {result.success_count}")
print(f"Ошибки: {result.error_count}")
```

### Обновление списка хостов

```python
manager = create_polling_manager(api_url="http://api.example.com/hosts")

# Принудительное обновление из API
success = manager.refresh_hosts_from_api()

if not success:
    print("Используется кэш хостов")
```

### Получение статуса

```python
status = manager.get_status()

print(f"Текущий опрос: {status['is_polling']}")
print(f"Хостов в кэше: {status['hosts_count']}")
print(f"Статистика: {status['last_poll_stats']}")
```

---

## ⚙️ Конфигурация

### Параметры конфигурации

```python
from polling_manager import PollingManagerConfig

config = PollingManagerConfig(
    api_url="http://api.example.com/hosts",      # URL API для получения хостов
    db_base_dir="databases",                      # Директория для БД
    checkpoint_path="emergency_checkpoint.json",  # Файл контрольной точки
    chunk_size=10,                                # Размер чанка опроса
    checkpoint_interval=100,                      # Сохранять каждые N хостов
    poll_interval_hours=1,                        # Интервал опроса (часы)
    hosts_ttl_hours=24                            # TTL кэша хостов (часы)
)

manager = PollingManager(config)
```

### Описание параметров

| Параметр | Тип | По умолчанию | Описание |
|----------|-----|--------------|----------|
| `api_url` | str | **обязательный** | URL API для получения списка хостов |
| `db_base_dir` | str | `"databases"` | Директория для файлов БД |
| `checkpoint_path` | str | `"emergency_checkpoint.json"` | Путь к файлу контрольной точки |
| `chunk_size` | int | `10` | Количество хостов в одном чанке (1-50) |
| `checkpoint_interval` | int | `100` | Сохранять прогресс каждые N хостов |
| `poll_interval_hours` | int | `1` | Интервал между массовыми опросами (часы) |
| `hosts_ttl_hours` | int | `24` | Время жизни кэша хостов (часы) |

---

## 🧪 Тестирование

### Запуск всех тестов

```bash
pytest test_polling_manager.py -v
```

### Запуск конкретного теста

```bash
pytest test_polling_manager.py -v -k test_manual_poll
```

### Запуск с покрытием кода

```bash
pytest test_polling_manager.py -v --cov=polling_manager --cov-report=term-missing
```

### Тесты с МОК-данными

Все тесты используют МОК-данные и не требуют доступа к:
- Реальному API
- Сетевому оборудованию
- Определённой подсети

Пример МОК-данных в `test_polling_manager.py`:

```python
TEST_HOSTS_DATA = [
    {
        "hostname": "NS0830",
        "ip": "10.8.239.189",
        "vendor": "nokia",
        "availability": True
    },
    # ... ещё хосты
]
```

---

## 📝 Логирование

### Настройка

```python
from logging_config import setup_logging

logger = setup_logging(
    log_dir="logs",
    level=logging.INFO,
    console_enabled=True,
    json_file_enabled=True,
    error_file_enabled=True
)
```

### Типы логов

| Тип | Файл | Формат | Описание |
|-----|------|--------|----------|
| Console | stdout | Человекочитаемый | Вывод в консоль |
| JSON | `logs/polling_YYYYMMDD.log` | JSON | Для автоматического анализа |
| Errors | `logs/errors_YYYYMMDD.log` | JSON | Только ошибки |

### Примеры использования

```python
logger.info("Опрос запущен")
logger.warning("TTL кэша истёк", extra={'age': '25h'})
logger.error("Ошибка подключения", extra={'host': 'NS0830', 'error_code': 500})
logger.debug("Детали чанка", extra={'chunk_size': 10, 'hosts': ['NS0830']})
```

---

## 🛡️ Аварийное восстановление

### Как работает

1. **Сохранение прогресса**: каждые `checkpoint_interval` хостов (по умолчанию 100)
2. **Атомарная запись**: через временный файл + rename
3. **Проверка при запуске**: если есть валидный checkpoint (не старше 2 часов), продолжается с последнего места
4. **Очистка**: после успешного завершения опроса

### Файл контрольной точки

```json
{
  "timestamp": "2024-01-15T10:30:00",
  "current_index": 99,
  "processed_count": 100,
  "hosts_snapshot": [
    {
      "hostname": "NS0830",
      "ip": "10.8.239.189",
      "status": "success",
      "timestamp": "2024-01-15T10:25:00"
    }
  ]
}
```

### Использование при сбое

```python
manager = create_polling_manager(api_url="http://api.example.com/hosts")

# При запуске автоматически проверяет checkpoint
# Если есть валидный checkpoint, продолжает с последнего места
await manager.start_mass_poll()
```

### Ручная проверка статуса

```python
status = manager._checkpoint.get_checkpoint_status()

print(f"Exists: {status['exists']}")
print(f"Valid: {status['valid']}")
print(f"Current index: {status.get('current_index')}")
```

---

## 📊 Логика работы

### Массовый опрос

```
1. Проверка блокировки (нет параллельных опросов)
2. Получение списка хостов из кэша
3. Проверка аварийного checkpoint
   ├─ Есть валидный checkpoint → восстановление с последнего места
   └─ Нет checkpoint → начало с первого хоста
4. Обработка чанками (chunk_size хостов)
   ├─ Опрос через get_nokia_measurements.py
   ├─ Сохранение прогресса на HDD (каждые checkpoint_interval)
   └─ Запись в БД
5. Очистка checkpoint
6. Расчёт паузы перед следующим опросом
   ├─ Опрос < 1 часа → ждать (60 - duration) минут
   └─ Опрос ≥ 1 часа → ждать 0 минут (с алертом)
7. Повтор с шага 1
```

### Ручной опрос

```
1. Поиск хостов в кэше
2. Проверка наличия данных за текущий час
   ├─ Есть данные и force=False → пропуск
   └─ Нет данных или force=True → продолжить
3. Опрос через get_nokia_measurements.py
4. Запись в БД
5. Обновление кэша хостов
6. Возврат статистики
```

### Обновление хостов из API

```
1. Запрос к API (timeout=30s)
2. Парсинг ответа в TemperatureResponse
3. Установка в кэш (с меткой времени)
4. При ошибке:
   ├─ Есть кэш → использовать с предупреждением
   └─ Нет кэша → ошибка RuntimeError
```

---

## 🔧 Расширение функциональности

### Добавление нового поля для опроса

```python
# В get_nokia_measurements.py
AVAILABLE_COMMANDS = {
    "voltage": "getRealTimeMeasurements",
    "alarms": "getActiveAlarms",
    "temperature": "sfpData",
    "new_field": "newCommand"  # Добавить новое поле
}
```

### Изменение интервала опроса

```python
config = PollingManagerConfig(
    poll_interval_hours=2  # Опрос раз в 2 часа
)
```

### Настройка частоты checkpoint

```python
config = PollingManagerConfig(
    checkpoint_interval=50  # Сохранять каждые 50 хостов
)
```

---

## 🐛 Устранение проблем

### Ошибка: "Cannot fetch hosts from API"

**Причина**: API недоступен и нет кэша хостов

**Решение**:
1. Проверить доступность API
2. Создать кэш хостов вручную (если возможно)
3. Увеличить TTL кэша

### Ошибка: "Checkpoint старше 2 часов"

**Причина**: Долгий простой между запусками

**Решение**: Начать опрос заново (checkpoint автоматически очищается)

### Медленный опрос

**Причины**:
- Большой список хостов
- Маленький `chunk_size`
- Медленная сеть

**Решение**:
- Увеличить `chunk_size` (до 50)
- Оптимизировать сеть
- Проверить доступность хостов

---

## 📞 Поддержка

При возникновении проблем:
1. Проверить логи в `logs/`
2. Проверить статус checkpoint
3. Проверить доступность API

---

## 📄 Лицензия

Внутреннее использование.
