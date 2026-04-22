# Конфигурация приложения

Подробное руководство по конфигурации Temperature Poller.

## 📋 Файлы конфигурации

Проект использует два файла конфигурации:

1. **`config.json`** - Основная конфигурация региона и API
2. **`api/.env`** - Настройки API сервера (FastAPI/Uvicorn)

---

## 🔧 config.json

### Расположение

Файл `config.json` находится в корне проекта.

### Структура

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

### Параметры

#### region (Обязательно)

| Поле | Тип | Описание | По умолчанию |
|------|-----|----------|--------------|
| `prefix` | string | Префикс региона (влияет на URL API) | `"NS"` |
| `name` | string | Название региона для логов | `"North Station"` |

**Примеры префиксов:**
- `"NS"` - North Station
- `"EU"` - Europe Station  
- `"AS"` - Asia Station
- `"TEST"` - Test environment

#### api (Обязательно)

| Поле | Тип | Описание | По умолчанию |
|------|-----|----------|--------------|
| `base_url` | string | Базовый URL API | `"http://localhost:8001"` |
| `hosts_endpoint` | string | Эндпоинт для получения хостов | `"/api/v1/hosts"` |

**Формирование URL:**
```
{base_url}{hosts_endpoint}?prefix={region.prefix}
```

Пример: `http://localhost:8001/api/v1/hosts?prefix=NS`

#### polling (Опционально)

| Поле | Тип | Описание | По умолчанию |
|------|-----|----------|--------------|
| `chunk_size` | int | Размер чанка опроса (1-50) | `10` |
| `checkpoint_interval` | int | Интервал сохранения checkpoint (хостов) | `100` |
| `poll_interval_hours` | int | Интервал массового опроса (часы) | `1` |
| `hosts_ttl_hours` | int | TTL кэша хостов (часы) | `24` |
| `max_checkpoint_age_hours` | float | Макс. возраст checkpoint (часы) | `2.0` |

#### database (Опционально)

| Поле | Тип | Описание | По умолчанию |
|------|-----|----------|--------------|
| `base_dir` | string | Директория для БД | `"databases"` |
| `auto_cleanup_days` | int | Автоочистка данных (дней) | `60` |

#### checkpoint (Опционально)

| Поле | Тип | Описание | По умолчанию |
|------|-----|----------|--------------|
| `path` | string | Путь к файлу checkpoint | `"emergency_checkpoint.json"` |

---

## 🌍 Использование разных регионов

### Переключение региона

Измените `config.json`:

```json
{
  "region": {
    "prefix": "EU",
    "name": "Europe Station"
  }
}
```

API автоматически будет использовать: `http://localhost:8001/api/v1/hosts?prefix=EU`

### Несколько конфигураций

Создайте отдельные файлы конфигурации:

```bash
config.json      # Основной (NS)
config.eu.json   # Европа (EU)
config.as.json   # Азия (AS)
config.test.json # Тестовая среда
```

Использование:

```bash
# Копирование конфигурации
cp config.eu.json config.json

# Запуск
python run_api.py
```

### Примеры конфигураций

**Тестовая среда:**
```json
{
  "region": {
    "prefix": "TEST",
    "name": "Test Environment"
  },
  "api": {
    "base_url": "http://test-api.local",
    "hosts_endpoint": "/api/hosts"
  },
  "polling": {
    "chunk_size": 5,
    "checkpoint_interval": 50,
    "poll_interval_hours": 1,
    "hosts_ttl_hours": 1,
    "max_checkpoint_age_hours": 0.5
  },
  "database": {
    "base_dir": "test_databases",
    "auto_cleanup_days": 7
  },
  "checkpoint": {
    "path": "test_checkpoint.json"
  }
}
```

**Продакшн (Europe):**
```json
{
  "region": {
    "prefix": "EU",
    "name": "Europe Production"
  },
  "api": {
    "base_url": "https://api.production.example.com",
    "hosts_endpoint": "/api/v1/hosts"
  },
  "polling": {
    "chunk_size": 20,
    "checkpoint_interval": 200,
    "poll_interval_hours": 1,
    "hosts_ttl_hours": 24,
    "max_checkpoint_age_hours": 2.0
  },
  "database": {
    "base_dir": "/var/lib/temperature/databases",
    "auto_cleanup_days": 90
  },
  "checkpoint": {
    "path": "/var/lib/temperature/checkpoints/emergency.json"
  }
}
```

---

## 🔐 Переменные окружения

Переменные окружения имеют наивысший приоритет и переопределяют `config.json`.

### Доступные переменные

| Переменная | Описание | Пример |
|------------|----------|--------|
| `REGION_PREFIX` | Префикс региона | `export REGION_PREFIX=EU` |
| `API_BASE_URL` | Базовый URL API | `export API_BASE_URL=http://api.example.com` |
| `DB_BASE_DIR` | Директория БД | `export DB_BASE_DIR=/data/databases` |

### Пример использования

```bash
# Переопределение префикса региона
export REGION_PREFIX=TEST
python run_api.py
# URL будет: http://localhost:8001/api/v1/hosts?prefix=TEST

# Полное переопределение
export REGION_PREFIX=EU
export API_BASE_URL=https://api.eu.example.com
export DB_BASE_DIR=/var/lib/eu_databases
python run_api.py
```

---

## 📊 Порядок загрузки конфигурации

Конфигурация загружается в следующем порядке приоритета (от низкого к высокому):

```
1. Значения по умолчанию (в коде)
   ↓
2. config.json
   ↓
3. Переменные окружения
```

**Пример:**

```json
// config.json
{
  "region": {
    "prefix": "NS"
  }
}
```

```bash
# Переменная окружения
export REGION_PREFIX=EU
```

Результат: `prefix = "EU"` (переменная окружения переопределяет config.json)

---

## 🐳 Docker конфигурация

### Использование volume для конфигурации

```dockerfile
# Dockerfile
COPY config.json /app/config.json
```

```bash
# Mount конфигурации из хоста
docker run -v $(pwd)/config.json:/app/config.json temperature-poller
```

### Использование переменных окружения в Docker

```bash
docker run \
  -e REGION_PREFIX=EU \
  -e API_BASE_URL=http://api.example.com \
  temperature-poller
```

---

## 🧪 Тестирование конфигурации

### Проверка загруженной конфигурации

```bash
# Запуск скрипта конфигурации
python app_config.py
```

Вывод:
```
======================================================================
 🔧 КОНФИГУРАЦИЯ ПРИЛОЖЕНИЯ
======================================================================

📍 Регион:
   Префикс: NS
   Название: North Station

📡 API:
   Base URL: http://localhost:8001
   Hosts URL: http://localhost:8001/api/v1/hosts?prefix=NS

🔄 Опрос:
   Размер чанка: 10
   Интервал сохранения checkpoint: 100
   Интервал опроса: 1ч
   TTL кэша хостов: 24ч

💾 База данных:
   Директория: databases
   Автоочистка: 60д

🔒 Checkpoint:
   Путь: emergency_checkpoint.json
======================================================================
```

### Использование в коде

```python
from app_config import get_config

config = get_config()
print(f"Префикс: {config.region.prefix}")
print(f"URL API: {config.get_hosts_api_url()}")
```

---

## 📝 Best Practices

### 1. Не коммитьте secrets

```json
// ❌ Плохо
{
  "api": {
    "base_url": "http://user:password@api.example.com"
  }
}

// ✅ Хорошо
{
  "api": {
    "base_url": "${API_BASE_URL}"
  }
}
```

Используйте переменные окружения для чувствительных данных.

### 2. Разные конфигурации для сред

```bash
config.dev.json    # Разработка
config.staging.json # Тестирование
config.prod.json   # Продакшн
```

### 3. Валидация конфигурации

```bash
# Проверка JSON перед запуском
python -c "import json; json.load(open('config.json'))"
```

---

## 📚 Дополнительные ресурсы

- [Основная документация](README.md)
- [API документация](api/README.md)
- [Изменения](CHANGELOG.md)
