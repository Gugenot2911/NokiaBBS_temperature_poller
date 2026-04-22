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
| `database.base_dir` | Директория БД | `databases` |

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

## 📝 Лицензия

NLP-Core-Team © 2024

## 👥 Контакты

Команда NLP-Core-Team
