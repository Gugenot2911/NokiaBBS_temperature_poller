# Temperature Poller API

REST API микросервис для управления опросом температурных данных оборудования Nokia.

## 📋 Содержание

- [Быстрый старт](#быстрый-старт)
- [Архитектура](#архитектура)
- [API Endpoints](#api-endpoints)
- [Примеры использования](#примеры-использования)
- [Конфигурация](#конфигурация)
- [Обработка ошибок](#обработка-ошибок)

## 🚀 Быстрый старт

### Установка зависимостей

```bash
pip install fastapi uvicorn pydantic
```

### Запуск сервера

```bash
# Из корня проекта
python -m api.main

# Или через uvicorn напрямую
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

### Доступ к документации

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health check**: http://localhost:8000/health

## 🏗️ Архитектура

```
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Server                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │   Polling    │  │  Temperature │  │   Status     │       │
│  │   Endpoints  │  │   Endpoints  │  │   Endpoints  │       │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘       │
│         │                 │                 │                │
│         ▼                 ▼                 ▼                │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              API State (Global)                      │   │
│  │  - PollingManager                                   │   │
│  │  - TemperatureDBManager                             │   │
│  │  - Background Tasks Queue                           │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
         │                      │                      │
         ▼                      ▼                      ▼
┌──────────────┐       ┌──────────────┐       ┌──────────────┐
│PollingManager│       │TemperatureDB │       │   SQLite     │
│ - HostCache  │       │ - Level 1    │       │  Databases   │
│ - Orchestrator       │ - Level 2    │       │  (per region)│
│ - Checkpoint │       │ - Level 3    │       │              │
└──────────────┘       └──────────────┘       └──────────────┘
```

## 📡 API Endpoints

### System

#### `GET /health`
Проверка здоровья сервиса.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00",
  "version": "1.0.0"
}
```

#### `GET /`
Информация о сервисе и доступных эндпоинтах.

---

### Polling

#### `POST /api/v1/poll/mass`
Запуск массового опроса всех хостов.

**Response:**
```json
{
  "success": true,
  "success_count": 0,
  "error_count": 0,
  "skipped_count": 0,
  "message": "Массовый опрос запущен в фоновом режиме"
}
```

**Возвращает:**
- `409` - Опрос уже выполняется
- `503` - Сервис недоступен

#### `POST /api/v1/poll/manual`
Ручной опрос выбранных хостов.

**Request Body:**
```json
{
  "hostnames": ["NS0830", "NS1120"],
  "force": false
}
```

**Response:**
```json
{
  "success": true,
  "success_count": 2,
  "error_count": 0,
  "skipped_count": 0,
  "message": "Опрос завершён: 2 успешно, 0 ошибок"
}
```

#### `POST /api/v1/poll/hosts/refresh`
Принудительное обновление списка хостов из API.

**Response:**
```json
{
  "success": true,
  "message": "Список хостов успешно обновлён"
}
```

---

### Temperature Data

#### `GET /api/v1/temperature/level1`
Получение списка станций с флагами аномалий (Уровень 1).

**Query Parameters:**
- `page` (int, default=1) - Номер страницы
- `page_size` (int, default=10, max=100) - Размер страницы

**Response:**
```json
{
  "level": 1,
  "page": 1,
  "page_size": 10,
  "total_pages": 5,
  "total_stations": 45,
  "data": [
    {
      "hostname": "NS0830",
      "has_anomaly": true,
      "rru_bits": "101010...",
      "bbu_bits": "010101..."
    }
  ]
}
```

**Время выполнения:** 1-5 мс

#### `GET /api/v1/temperature/level2/{hostname}`
Бинарная тепловая шкала для хоста (Уровень 2).

**Path Parameters:**
- `hostname` (string) - Имя хоста (например, `NS0830`)

**Response:**
```json
{
  "level": 2,
  "hostname": "NS0830",
  "rru_bits": "101010101010101010101010101010101010101010101010",
  "bbu_bits": "010101010101010101010101010101010101010101010101",
  "rru_anomaly_count": 24,
  "bbu_anomaly_count": 24
}
```

**Время выполнения:** 1-2 мс

#### `GET /api/v1/temperature/level3/{hostname}`
Полные спарклайны для хоста (Уровень 3).

**Path Parameters:**
- `hostname` (string) - Имя хоста

**Query Parameters:**
- `hours` (int, default=48, max=168) - Количество часов

**Response:**
```json
{
  "level": 3,
  "hostname": "NS0830",
  "rru_max": [57, 55, 58, ...],
  "rru_min": [19, 20, 18, ...],
  "rru_avg": [36, 35, 37, ...],
  "bbu_max": [34, 32, 35, ...],
  "bbu_min": [25, 24, 26, ...],
  "bbu_avg": [30, 29, 31, ...],
  "hours": [1705312800, 1705316400, ...]
}
```

**Время выполнения:** 20-50 мс

#### `GET /api/v1/temperature/hosts`
Получение списка всех станций.

**Response:**
```json
{
  "hosts": ["NS0830", "NS1120", "NS1111", ...],
  "total": 45
}
```

---

### Status

#### `GET /api/v1/status`
Текущий статус системы опроса.

**Response:**
```json
{
  "is_polling": false,
  "hosts_count": 45,
  "hosts_cache_fresh": true,
  "last_poll_stats": {
    "start_time": "2024-01-15T10:00:00",
    "duration_seconds": 120.5,
    "total_hosts": 45,
    "success_count": 43,
    "error_count": 2,
    "success_rate": 95.56
  },
  "checkpoint_status": {
    "exists": false,
    "age_hours": null
  }
}
```

#### `GET /api/v1/status/stats`
Статистика последнего опроса.

#### `GET /api/v1/status/databases`
Статус всех баз данных.

**Response:**
```json
{
  "databases": [
    {
      "prefix": "NS",
      "path": "databases/NS_temperature_eNode.db",
      "size_mb": 15.7,
      "stations": 45,
      "total_stations": 45,
      "stations_with_anomaly": 12,
      "anomaly_percentage": 26.7
    }
  ],
  "total": 1
}
```

---

## 💡 Примеры использования

### cURL

```bash
# Проверка здоровья
curl http://localhost:8000/health

# Запуск массового опроса
curl -X POST http://localhost:8000/api/v1/poll/mass

# Ручной опрос хостов
curl -X POST http://localhost:8000/api/v1/poll/manual \
  -H "Content-Type: application/json" \
  -d '{"hostnames": ["NS0830", "NS1120"], "force": false}'

# Получить Level 1 данные
curl "http://localhost:8000/api/v1/temperature/level1?page=1&page_size=20"

# Получить Level 2 для хоста
curl http://localhost:8000/api/v1/temperature/level2/NS0830

# Получить Level 3 для хоста (72 часа)
curl "http://localhost:8000/api/v1/temperature/level3/NS0830?hours=72"

# Получить статус системы
curl http://localhost:8000/api/v1/status

# Обновить список хостов
curl -X POST http://localhost:8000/api/v1/poll/hosts/refresh
```

### Python

```python
import requests

BASE_URL = "http://localhost:8000"

# Проверка здоровья
response = requests.get(f"{BASE_URL}/health")
print(response.json())

# Запуск массового опроса
response = requests.post(f"{BASE_URL}/api/v1/poll/mass")
print(response.json())

# Ручной опрос
response = requests.post(
    f"{BASE_URL}/api/v1/poll/manual",
    json={"hostnames": ["NS0830", "NS1120"], "force": False}
)
print(response.json())

# Получить температурные данные
response = requests.get(f"{BASE_URL}/api/v1/temperature/level2/NS0830")
level2_data = response.json()
print(f"RRU аномалии: {level2_data['rru_anomaly_count']}")

# Получить детальные данные
response = requests.get(
    f"{BASE_URL}/api/v1/temperature/level3/NS0830",
    params={"hours": 48}
)
level3_data = response.json()
print(f"Средняя температура RRU: {sum(level3_data['rru_avg']) / len(level3_data['rru_avg']):.1f}°C")

# Получить статус
response = requests.get(f"{BASE_URL}/api/v1/status")
status = response.json()
print(f"Успешность последнего опроса: {status['last_poll_stats']['success_rate']}%")
```

### JavaScript (Fetch)

```javascript
const BASE_URL = "http://localhost:8000";

// Запуск массового опроса
async function startMassPoll() {
  const response = await fetch(`${BASE_URL}/api/v1/poll/mass`, {
    method: 'POST'
  });
  return response.json();
}

// Получить Level 2 данные
async function getTemperatureLevel2(hostname) {
  const response = await fetch(`${BASE_URL}/api/v1/temperature/level2/${hostname}`);
  return response.json();
}

// Пример использования
(async () => {
  const result = await startMassPoll();
  console.log(result.message);
  
  const level2 = await getTemperatureLevel2('NS0830');
  console.log(`RRU аномалии: ${level2.rru_anomaly_count}`);
})();
```

---

## ⚙️ Конфигурация

### config.json (Основная конфигурация)

Файл `config.json` в корне проекта содержит конфигурацию региона и API:

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

**Как работает префикс региона:**

При запуске API автоматически формирует URL для получения списка хостов:

```
{api.base_url}{api.hosts_endpoint}?prefix={region.prefix}
```

Пример для `config.json` выше:
```
http://localhost:8001/api/v1/hosts?prefix=NS
```

**Изменение региона:**

Чтобы переключиться на другой регион, измените `config.json`:

```json
{
  "region": {
    "prefix": "EU",
    "name": "Europe Station"
  }
}
```

URL автоматически станет: `http://localhost:8001/api/v1/hosts?prefix=EU`

### Переменные окружения (api/.env)

Настройки API сервера (порт, логирование и т.д.) задаются в `api/.env`:

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `HOST` | Хост сервера | `0.0.0.0` |
| `PORT` | Порт сервера | `8000` |
| `RELOAD` | Автоперезагрузка | `false` |
| `LOG_LEVEL` | Уровень логирования | `info` |

**Переопределение config.json через окружение:**

| Переменная | Описание |
|------------|----------|
| `REGION_PREFIX` | Префикс региона (переопределяет config.json) |
| `API_BASE_URL` | Базовый URL API |
| `DB_BASE_DIR` | Директория БД |

Пример:
```bash
export REGION_PREFIX="TEST"
python run_api.py
# URL будет: http://localhost:8001/api/v1/hosts?prefix=TEST
```

### Порядок загрузки конфигурации

1. Значения по умолчанию (в коде)
2. Значения из `config.json`
3. Переопределение через переменные окружения

### Параметры сервера

```bash
# Порт сервера
uvicorn api.main:app --host 0.0.0.0 --port 8000

# Логирование
uvicorn api.main:app --log-level debug

# Количество workers
uvicorn api.main:app --workers 4
```

---

## ❌ Обработка ошибок

API использует стандартные HTTP статус коды:

| Код | Описание |
|-----|----------|
| `200` | Успешный запрос |
| `202` | Запрос принят (фоновая задача) |
| `400` | Неверный запрос (невалидные параметры) |
| `404` | Ресурс не найден |
| `409` | Конфликт (опрос уже выполняется) |
| `500` | Внутренняя ошибка сервера |
| `503` | Сервис недоступен |

**Формат ответа ошибки:**

```json
{
  "detail": "Описание ошибки"
}
```

**Пример:**

```bash
curl http://localhost:8000/api/v1/temperature/level2/INVALID
# Response: {"detail": "Invalid hostname format: INVALID. Expected format: PREFIX+4digits"}
```

---

## 🔒 Безопасность

На данный момент аутентификация не реализована (предполагается локальное использование).

Для защиты в production среде рекомендуется:
- Использовать nginx/reverse proxy с TLS
- Добавить API ключи или JWT аутентификацию
- Ограничить доступ по IP через firewall

---

## 📝 Лицензия

NLP-Core-Team © 2024
