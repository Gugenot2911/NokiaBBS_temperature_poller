# Единая конфигурация URL API

## Проблема
В проекте был конфликт конфигурации URL API в нескольких файлах:
- `app_config.py` - правильно читал из `config.json`
- `polling_manager.py` - имел hardcoded fallback на `localhost:8001`
- `api/config.py` - имел hardcoded default на `localhost:8001`

Это приводило к тому, что при запуске сервер пытался подключиться к `localhost:8000` (тестовая среда) вместо `WSNS-LAVROV2:8001` (production).

## Решение
Организована единая точка конфигурации через `app_config.py` с последовательным приоритетом:

### Приоритет конфигурации
1. **Переменные окружения** (максимальный приоритет)
   - `API_BASE_URL` - базовый URL API
   - `REGION_PREFIX` - префикс региона

2. **Файл config.json** (средний приоритет)
   - Читается через `app_config.py`
   - Позволяет централизованно управлять настройками

3. **Значения по умолчанию** (минимальный приоритет)
   - Только как fallback, если нет ни переменных окружения, ни config.json

## Изменённые файлы

### 1. `config.json`
Обновлён для production-среды:
```json
{
  "api": {
    "base_url": "http://WSNS-LAVROV2:8001",
    "hosts_endpoint": "/api/v1/hosts"
  }
}
```

### 2. `polling_manager.py`
Функция `create_polling_manager()` теперь использует `app_config`:
```python
# Если api_url не передан, используем значение из app_config
if api_url is None:
    try:
        from app_config import get_hosts_api_url
        api_url = get_hosts_api_url()
    except ImportError:
        # Fallback только если app_config недоступен
        api_url = "http://localhost:8001/api/v1/hosts?prefix=NS"
```

### 3. `api/config.py`
Добавлена функция `_get_default_api_url()` с приоритетом:
```python
def _get_default_api_url() -> str:
    # 1. Переменная окружения
    if os.environ.get('API_BASE_URL'):
        region_prefix = os.environ.get('REGION_PREFIX', 'NS')
        return f"{os.environ['API_BASE_URL']}/api/v1/hosts?prefix={region_prefix}"
    
    # 2. app_config.py (config.json)
    try:
        from app_config import get_hosts_api_url
        return get_hosts_api_url()
    except (ImportError, Exception):
        pass
    
    # 3. Fallback
    return "http://localhost:8001/api/v1/hosts?prefix=NS"
```

## Как использовать

### Вариант 1: Через config.json (рекомендуется)
Просто отредактируйте `config.json`:
```json
{
  "api": {
    "base_url": "http://WSNS-LAVROV2:8001",
    "hosts_endpoint": "/api/v1/hosts"
  }
}
```

### Вариант 2: Через переменные окружения
```bash
# Windows PowerShell
$env:API_BASE_URL="http://WSNS-LAVROV2:8001"
$env:REGION_PREFIX="NS"
python run_api.py

# Linux/Mac
export API_BASE_URL="http://WSNS-LAVROV2:8001"
export REGION_PREFIX="NS"
python run_api.py
```

### Вариант 3: Программно
```python
from polling_manager import create_polling_manager

# Автоматически использует config.json
manager = create_polling_manager()

# Или явно передать URL
manager = create_polling_manager(
    api_url="http://WSNS-LAVROV2:8001/api/v1/hosts?prefix=NS"
)
```

## Проверка конфигурации
```bash
# Проверка app_config
python -c "from app_config import get_config; c = get_config(); print(c.get_hosts_api_url())"

# Ожидаемый результат:
# http://WSNS-LAVROV2:8001/api/v1/hosts?prefix=NS
```

## Архитектура
```
┌─────────────────────────────────────────────────────┐
│                  Configuration                       │
│  ┌──────────────────────────────────────────────┐   │
│  │ 1. Environment Variables (highest priority)  │   │
│  │    - API_BASE_URL                            │   │
│  │    - REGION_PREFIX                           │   │
│  └──────────────────────────────────────────────┘   │
│                    ↓ ↓ ↓                             │
│  ┌──────────────────────────────────────────────┐   │
│  │ 2. config.json (via app_config.py)           │   │
│  │    - api.base_url                            │   │
│  │    - api.hosts_endpoint                      │   │
│  │    - region.prefix                           │   │
│  └──────────────────────────────────────────────┘   │
│                    ↓ ↓ ↓                             │
│  ┌──────────────────────────────────────────────┐   │
│  │ 3. Hardcoded defaults (fallback only)        │   │
│  │    - http://localhost:8001                   │   │
│  └──────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
                    ↓
         ┌──────────────────────┐
         │ All modules use:     │
         │ - app_config.get_    │
         │   hosts_api_url()    │
         └──────────────────────┘
```

## Тестирование
Запустите тесты конфигурации:
```bash
python test_config_url.py
python test_api_config_url.py
```

## Миграция
Если у вас были hardcoded URL в коде:
1. Удалите hardcoded URL
2. Используйте `create_polling_manager()` без параметров
3. Настройте `config.json` или переменные окружения

## Обратная совместимость
Все изменения обратно совместимы:
- Старый код с явным передаванием `api_url` продолжит работать
- Fallback на `localhost:8001` остаётся для совместимости
- Нет breaking changes в API
