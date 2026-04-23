# Temperature Poller System

Система мониторинга температурных данных сетевого оборудования Nokia.

## 📋 Описание

Автоматизированная система для:
- **Массового опроса** температурных датчиков на базовых станциях
- **Аварийного восстановления** при прерывании длительных опросов
- **Трёхуровневого доступа** к данным для фронтенда
- **REST API** для интеграции с внешними системами
- **Портативная версия** для Windows 10 без прав администратора

## 🚀 **НОВАЯ: Портативная версия Windows 10**

Полностью автономная версия, не требующая установки Python или прав администратора:

```bash
# Сборка портативной версии (требуется Python 3.11+)
python build_portable.py

# Результат: папка temperature-poller-portable/
# Копируйте на любой ПК с Windows 10 и запускайте
```

**Преимущества портативной версии:**
- ✅ Не требует прав администратора
- ✅ Не требует установки Python
- ✅ Работает с флешки
- ✅ Кроссплатформенная сборка (Windows 10+)
- ✅ Размер: ~150 MB

**Подробная инструкция:** [BUILD_INSTRUCTIONS.txt](BUILD_INSTRUCTIONS.txt)

## 🏗️ Архитектура

```
┌──────────────────────────────────────────────────────────────────┐
│                        Temperature Poller                         │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────────┐     ┌─────────────────┐     ┌────────────┐ │
│  │  PollingManager │────▶│  Nokia Devices  │     │  API       │ │
│  │  - Host Cache   │     │  (Nokia)        │     │  Gateway   │ │
│  │  - Orchestrator │     │                 │     │            │ │
│  │  - Checkpoint   │     └─────────────────┘     └────────────┘ │
│  └────────┬────────┘                                              │
│           │                                                       │
│           ▼                                                       │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    SQLite Databases                       │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │    │
│  │  │   Level 1   │  │   Level 2   │  │   Level 3   │      │    │
│  │  │  (Flags)    │  │   (Bits)    │  │  (Sparklines)│      │    │
│  │  └─────────────┘  └─────────────┘  └─────────────┘      │    │
│  └─────────────────────────────────────────────────────────┘    │
│           │                                                       │
│           ▼                                                       │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    FastAPI Server                         │    │
│  │  /api/v1/poll/        - Управление опросом               │    │
│  │  /api/v1/temperature/ - Температурные данные              │    │
│  │  /api/v1/status/      - Статус системы                    │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```

## 📁 Структура проекта

```
.
├── api/                        # FastAPI микросервис
│   ├── __init__.py
│   ├── main.py                 # Основной файл API
│   ├── config.py               # Конфигурация FastAPI из .env
│   ├── requirements.txt        # Зависимости API
│   ├── README.md               # Документация API
│   └── .env.example            # Пример конфигурации
│
├── build_portable.py           # Скрипт сборки портативной версии ⭐
├── START.bat                   # Запуск портативной версии ⭐
├── requirements.txt            # Зависимости проекта
├── logging_config.py           # Конфигурация логирования
├── app_config.py               # Конфигурация приложения (config.json)
├── config.json                 # Конфигурация региона и API
├── models.py                   # Pydantic модели
├── polling_manager.py          # Менеджер опроса
├── sqlite_temperature.py       # Работа с БД
├── emergency_checkpoint.py     # Аварийное сохранение
├── directory_config.py         # Конфигурация директорий
├── path_utils.py               # Утилиты путей
├── run_api.py                  # Скрипт запуска API
├── test_api.py                 # Тестовый скрипт
├── BUILD_INSTRUCTIONS.txt      # Инструкция по сборке ⭐
├── Makefile                    # Удобные команды
└── README.md                   # Этот файл
```

⭐ — файлы для портативной версии

## 🚀 Быстрый старт

### Портативная версия (Windows 10) ⭐

**Без прав администратора, без установки Python:**

```bash
# 1. Сборка (на машине с Python)
python build_portable.py

# 2. Результат: папка temperature-poller-portable/
#    Скопируйте на любой ПК с Windows 10

# 3. Запуск
cd temperature-poller-portable
START.bat
```

**Подробная инструкция:** [BUILD_INSTRUCTIONS.txt](BUILD_INSTRUCTIONS.txt)

### Классическая установка (с Python)

```bash
# Клонирование репозитория
git clone <repository-url>
cd temperature-poller

# Создание виртуального окружения
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/macOS

# Установка зависимостей
pip install -r api/requirements.txt
```

### Конфигурация

```bash
# Копирование примера конфигурации
cp api/.env.example api/.env

# Редактирование конфигурации
# Редактируйте api/.env под ваши нужды
```

### Запуск API сервера

```bash
# Способ 1: Через скрипт запуска
python run_api.py

# Способ 2: Через uvicorn напрямую
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

# Способ 3: Через модуль
python -m api.main
```

### Доступ к документации

После запуска откройте в браузере:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health check**: http://localhost:8000/health

## 📡 API Endpoints

### Управление опросом

| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| `POST` | `/api/v1/poll/mass` | Запуск массового опроса |
| `POST` | `/api/v1/poll/manual` | Ручной опрос хостов |
| `POST` | `/api/v1/poll/hosts/refresh` | Обновление списка хостов |

### Управление сервером 🆕

| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| `GET` | `/api/v1/system/status` | Текущий статус системы |
| `POST` | `/api/v1/system/pause` | Приостановка опросов |
| `POST` | `/api/v1/system/resume` | Возобновление опросов |
| `POST` | `/api/v1/system/restart` | Перезапуск сервера |
| `POST` | `/api/v1/system/reload-config` | Перезагрузка конфигурации |

### Температурные данные

| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| `GET` | `/api/v1/temperature/level1` | Список станций с аномалиями |
| `GET` | `/api/v1/temperature/level2/{hostname}` | Бинарная тепловая шкала |
| `GET` | `/api/v1/temperature/level3/{hostname}` | Детальные спарклайны |
| `GET` | `/api/v1/temperature/hosts` | Список всех станций |

### Статус системы

| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| `GET` | `/api/v1/status` | Текущий статус опроса |
| `GET` | `/api/v1/status/stats` | Статистика последнего опроса |
| `GET` | `/api/v1/status/databases` | Статус баз данных |

## 💡 Примеры использования

### Управление состоянием сервера 🆕

#### Получение статуса системы

```bash
curl http://localhost:8000/api/v1/system/status
# {
#   "server_state": "running",
#   "is_polling": false,
#   "uptime_seconds": 3600.5,
#   "paused_since": null
# }
```

#### Приостановка опросов (для обслуживания)

```bash
# Приостановить
curl -X POST http://localhost:8000/api/v1/system/pause
# {"success": true, "server_state": "paused"}

# Проверить статус
curl http://localhost:8000/health
# {"status": "paused", "server_state": "paused"}

# Возобновить
curl -X POST http://localhost:8000/api/v1/system/resume
# {"success": true, "server_state": "running"}
```

#### Перезапуск сервера

```bash
# Перезапуск с задержкой 5 секунд
curl -X POST http://localhost:8000/api/v1/system/restart \
  -H "Content-Type: application/json" \
  -d '{"delay_seconds": 5, "notify": true}'

# Перезагрузка конфигурации без перезапуска
curl -X POST http://localhost:8000/api/v1/system/reload-config
```

#### Клавиатурные сочетания (Unix/Linux)

```bash
# Пауза процесса (аналог API pause)
Ctrl+Z

# Возобновление (аналог API resume)
fg

# Сигнал для мягкого перезапуска
kill -HUP <pid>
```

### Запуск массового опроса

```bash
curl -X POST http://localhost:8000/api/v1/poll/mass
```

### Ручной опрос хостов

```bash
curl -X POST http://localhost:8000/api/v1/poll/manual \
  -H "Content-Type: application/json" \
  -d '{"hostnames": ["NS0830", "NS1120"], "force": false}'
```

### Получить температурные данные

```bash
# Уровень 1 (список с аномалиями)
curl http://localhost:8000/api/v1/temperature/level1

# Уровень 2 (бинарная шкала)
curl http://localhost:8000/api/v1/temperature/level2/NS0830

# Уровень 3 (детальные данные)
curl "http://localhost:8000/api/v1/temperature/level3/NS0830?hours=48"
```

### Python пример

```python
import requests

BASE_URL = "http://localhost:8000"

# Запустить опрос
requests.post(f"{BASE_URL}/api/v1/poll/mass")

# Получить данные
response = requests.get(f"{BASE_URL}/api/v1/temperature/level2/NS0830")
data = response.json()
print(f"RRU аномалии: {data['rru_anomaly_count']}")
```

## ⚙️ Конфигурация

### Файл config.json

Основной конфигурационный файл проекта:

```json
{
  "region": {
    "prefix": "NS",
    "name": "North Station"
  },
  "api": {
    "base_url": "http://localhost:8001",
    "hosts_endpoint": "/api/v1/hosts"
  },
  "polling": {
    "chunk_size": 10,
    "checkpoint_interval": 100,
    "poll_interval_hours": 1,
    "hosts_ttl_hours": 24,
    "max_checkpoint_age_hours": 2.0
  },
  "database": {
    "base_dir": "databases",
    "auto_cleanup_days": 60
  },
  "checkpoint": {
    "path": "emergency_checkpoint.json"
  }
}
```

**Ключевые настройки:**

| Параметр | Описание | По умолчанию |
|----------|----------|--------------|
| `region.prefix` | Префикс региона (влияет на URL API) | `NS` |
| `region.name` | Название региона | `North Station` |
| `api.base_url` | Базовый URL API | `http://localhost:8001` |
| `api.hosts_endpoint` | Эндпоинт для получения хостов | `/api/v1/hosts` |
| `polling.chunk_size` | Размер чанка опроса | `10` |
| `polling.poll_interval_hours` | Интервал массовых опросов (часов) | `1` |
| `database.base_dir` | Директория БД | `databases` |
| `checkpoint.path` | Путь к файлу checkpoint | `emergency_checkpoint.json` |

**URL API формируется автоматически:**
```
{api.base_url}{api.hosts_endpoint}?prefix={region.prefix}
```

Пример: `http://localhost:8001/api/v1/hosts?prefix=NS`

### Переменные окружения

Переопределение настроек через переменные окружения:

| Переменная | Описание |
|------------|----------|
| `REGION_PREFIX` | Префикс региона (переопределяет config.json) |
| `API_BASE_URL` | Базовый URL API |
| `DB_BASE_DIR` | Директория БД |

Пример:
```bash
export REGION_PREFIX="TEST"
export API_BASE_URL="http://api.example.com"
python run_api.py
```

### Подробная документация

Полное руководство по конфигурации: [CONFIG.md](CONFIG.md)

### Конфигурация FastAPI (api/.env)

Дополнительные настройки API сервера:

```bash
# Копирование примера
cp api/.env.example api/.env

# Редактирование
HOST=0.0.0.0
PORT=8000
RELOAD=false
LOG_LEVEL=info
```

Полная документация API: [api/README.md](api/README.md)

## 📊 Работа с данными

### Трёхуровневая модель

1. **Уровень 1**: Флаги аномалий (1 бит на хост) - быстрая загрузка таблицы
2. **Уровень 2**: Бинарная тепловая шкала (48 бит) - при разворачивании строки
3. **Уровень 3**: Полные спарклайны (48 значений) - детальный просмотр

### Аномалии

Температура считается аномальной если:
- `< 15°C` (ниже нормы)
- `>= 60°C` (выше нормы)

## 🛠️ Разработка

### Запуск в режиме разработки

```bash
python run_api.py --reload
# или
uvicorn api.main:app --reload --log-level debug
```

### Тестирование

```bash
# Проверка здоровья
curl http://localhost:8000/health

# Список эндпоинтов
curl http://localhost:8000/
```

## 🔌 Заглушки (Mock) для тестирования

### 📦 Что заглушено

В проекте используется заглушка `nokia_polling` для тестирования без реального оборудования:

**Файл:** `nokia_polling/get_nokia_measurements.py`

**Что делает:**
- Возвращает тестовые данные температур вместо реального опроса
- Генерирует случайные значения для RRU и BBU (15-60°C)
- Не требует сетевого доступа к устройствам
- Имитирует задержки сети (50-200 мс)

**Пример данных заглушки:**
```json
{
  "hostname": "NS0002",
  "ip": "10.8.234.129",
  "temperature": {
    "RRU": {"max": 45, "min": 25, "avg": 35},
    "BBU": {"max": 38, "min": 28, "avg": 33}
  },
  "status": "success"
}
```

### 🚀 Как отключить заглушки в продакшене

#### Шаг 1: Удалить или переместить заглушку

```bash
# Вариант 1: Удалить (безвозвратно)
rm -rf nokia_polling/

# Вариант 2: Переместить (для возможности восстановления)
mv nokia_polling nokia_polling_disabled

# Вариант 3: Переименовать (Git-friendly)
git mv nokia_polling nokia_polling_mock
```

#### Шаг 2: Подключить реальный модуль опроса

Создайте `nokia_polling/` с реальной реализацией:

```
nokia_polling/
├── __init__.py
└── get_nokia_measurements.py  # Реальная реализация
```

**Требования к реальной реализации:**

```python
#!/usr/bin/env python3
"""
Реальный модуль опроса Nokia устройств.
Заменяет заглушку в production.
"""

from typing import List, Dict, Any

def nokia_polling_module(
    sites: List[Dict[str, Any]],
    fields: set = None,
    batch_size: int = 10,
    check_availability: bool = True,
    ping_timeout: int = 1
) -> List[Dict[str, Any]]:
    """
    Опрос реальных устройств Nokia.
    
    Args:
        sites: список хостов для опроса
        fields: поля для опроса (temperature)
        batch_size: размер батча
        check_availability: проверять доступность (ping)
        ping_timeout: таймаут ping в секундах
    
    Returns:
        Список результатов опроса в формате:
        [
            {
                "hostname": "NS0002",
                "ip": "10.8.234.129",
                "temperature": {
                    "RRU": {"max": 45, "min": 25, "avg": 35},
                    "BBU": {"max": 38, "min": 28, "avg": 33}
                },
                "status": "success",
                "availability": True
            }
        ]
    """
    # Реализация через SNMP/CLI/SSH
    # Примеры библиотек:
    # - netmiko (SSH)
    # - pysnmp (SNMP)
    # - paramiko (SSH)
    # - subprocess (CLI)
    pass
```

**Пример реальной реализации через SNMP:**

```python
from pysnmp.hlapi import *

def nokia_polling_module(sites, **kwargs):
    results = []
    
    for site in sites:
        hostname = site['hostname']
        ip = site['ip']
        
        # SNMP опрос температурных OID
        error_ind, error_status, error_index, var_binds = next(
            getCmd(SnmpEngine(),
                   CommunityData('public'),
                   UdpTransportTarget((ip, 161)),
                   ContextData(),
                   ObjectType(ObjectIdentity('1.3.6.1.4.1.56297.1.1'))  # Nokia temp OID
            )
        )
        
        if not error_ind:
            temp_data = parse_nokia_snmp(var_binds)
            results.append({
                "hostname": hostname,
                "ip": ip,
                "temperature": temp_data,
                "status": "success",
                "availability": True
            })
    
    return results
```

#### Шаг 3: Проверка подключения

```bash
# Запустить тестовый опрос
curl -X POST http://localhost:8000/api/v1/poll/manual \
  -H "Content-Type: application/json" \
  -d '{"hostnames": ["NS0002"], "force": true}'

# Проверить логи сервера
# Если заглушка удалена — будут ошибки импорта
# Если подключён реальный модуль — успешный опрос
```

#### 🔍 Автоматическая проверка режима

```bash
#!/bin/bash
# check_mode.sh — определить режим работы

if [ -d "nokia_polling" ]; then
    if grep -q "MOCK" nokia_polling/get_nokia_measurements.py 2>/dev/null; then
        echo "⚠️  РЕЖИМ: ЗАГЛУШКА (MOCK)"
        echo "   Заглушка обнаружена! Удалите её для production."
        exit 1
    else
        echo "✅ РЕЖИМ: PRODUCTION"
        echo "   Реальный модуль опроса подключён."
        exit 0
    fi
else
    echo "❌ ОШИБКА: Модуль nokia_polling не найден!"
    echo "   Создайте модуль или восстановите заглушку для тестирования."
    exit 2
fi
```

#### 🔧 Использование переменных окружения

```bash
# Принудительное использование заглушки (для тестирования)
export USE_MOCK=true
python run_api.py

# Принудительное использование реального модуля
export USE_MOCK=false
python run_api.py
```

### 🔄 Переключение между режимами

**Разработка (заглушка):**
```bash
# Ветка с заглушкой
git checkout mock
python run_api.py

# Логирование:
# "⚠️  MOCK: Опрос 10 хостов (заглушка)"
```

**Production (реальный опрос):**
```bash
# Ветка production
git checkout production

# Проверка:
./check_mode.sh
# Вывод: "✅ РЕЖИМ: PRODUCTION"

python run_api.py
```

**Гибридный подход (рекомендуется):**

```bash
# Хранить заглушку в отдельной директории
mkdir -p mocks/
mv nokia_polling mocks/nokia_polling_mock

# Создать скрипт переключения
cat > switch_mode.sh << 'EOF'
#!/bin/bash
case "$1" in
    mock)
        mv mocks/nokia_polling_mock nokia_polling
        echo "✅ Переключено в режим MOCK"
        ;;
    production)
        mv nokia_polling mocks/nokia_polling_mock
        echo "✅ Переключено в режим PRODUCTION"
        ;;
    *)
        echo "Usage: $0 {mock|production}"
        exit 1
        ;;
esac
EOF

chmod +x switch_mode.sh

# Использование:
./switch_mode.sh mock      # Тестирование
./switch_mode.sh production # Production
```

### 📋 Чек-лист перед деплоем в Production

```markdown
- [ ] Заглушка `nokia_polling/` удалена или перемещена
- [ ] Реальный модуль опроса подключён и протестирован
- [ ] Проверены сетевые права (SNMP/SSH доступ)
- [ ] Настроены credentials (SNMP community, SSH keys)
- [ ] Протестирован опрос хотя бы одного устройства
- [ ] Проверены логи на наличие ошибок
- [ ] Настроено логирование в production (file, syslog)
- [ ] Настроен мониторинг (health check, uptime)
- [ ] Протестирована обработка ошибок (timeout, unreachable hosts)
- [ ] Настроено резервное копирование БД
```

### ⚠️ Важные замечания

1. **Заглушка не требует прав root** — работает без сетевых прав
2. **Реальный модуль может требовать:**
   - Доступ к сетевым устройствам по SNMP/SSH
   - SNMP community strings (обычно `public` для read-only)
   - SSH credentials (username/password или keys)
   - Открытые порты: 161 (SNMP), 22 (SSH)
3. **Всегда тестируйте с заглушкой перед деплоем**
4. **Используйте feature flags для переключения:**
   ```bash
   export USE_MOCK=true  # или false
   ```
5. **Проверяйте режим перед запуском в production:**
   ```bash
   ./check_mode.sh || exit 1
   python run_api.py
   ```
6. **Заглушка генерирует случайные данные** — не используйте для отчётности

### 📚 Дополнительные ресурсы

- [API Документация](api/README.md)
- [Конфигурация](CONFIG.md)
- [Системное управление](SYSTEM_CONTROL.md) ⭐
- [Инструкция по сборке Windows](BUILD_INSTRUCTIONS.txt)

## 📝 Лицензия

NLP-Core-Team © 2024

## 👥 Контакты

Команда NLP-Core-Team
