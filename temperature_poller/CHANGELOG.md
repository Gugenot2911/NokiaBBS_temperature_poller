# Changelog

Все заметные изменения проекта будут документироваться в этом файле.

Формат основан на [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [1.0.0] - 2024-01-15

### Добавлено

#### Конфигурация
- **config.json** - Основной конфигурационный файл с префиксом региона
- **app_config.py** - Загрузчик конфигурации с поддержкой переменных окружения
- **CONFIG.md** - Подробное руководство по конфигурации
- **config.eu.json** - Пример конфигурации для Европы

#### API Микросервис
- FastAPI сервер с REST API
- Swagger UI и ReDoc документация
- CORS поддержка

#### Endpoints

**System**
- `GET /health` - Проверка здоровья сервиса
- `GET /` - Информация о сервисе

**Polling**
- `POST /api/v1/poll/mass` - Запуск массового опроса
- `POST /api/v1/poll/manual` - Ручной опрос хостов
- `POST /api/v1/poll/hosts/refresh` - Обновление списка хостов

**Temperature Data**
- `GET /api/v1/temperature/level1` - Список станций с аномалиями
- `GET /api/v1/temperature/level2/{hostname}` - Бинарная тепловая шкала
- `GET /api/v1/temperature/level3/{hostname}` - Детальные спарклайны
- `GET /api/v1/temperature/hosts` - Список всех станций

**Status**
- `GET /api/v1/status` - Текущий статус системы
- `GET /api/v1/status/stats` - Статистика последнего опроса
- `GET /api/v1/status/databases` - Статус баз данных

#### Конфигурация
- Поддержка переменных окружения через `.env`
- `api/config.py` - Централизованная конфигурация
- `api/.env.example` - Пример конфигурации

#### Документация
- `api/README.md` - Полная документация API
- `README.md` - Главный README проекта
- Примеры использования (cURL, Python, JavaScript)

#### Утилиты
- `run_api.py` - Скрипт для запуска API
- `test_api.py` - Тестовый скрипт для проверки API
- `.gitignore` - Файл игнорирования Git

### Изменения

#### Оптимизация
- Использование фоновых задач для массового опроса
- Защита от параллельных запусков опроса
- Блокировка `asyncio.Lock` для предотвращения гонок

#### Логирование
- Интеграция с существующей системой логирования
- Детальное логирование жизненного цикла API

### Технические детали

**Зависимости**
- fastapi>=0.104.0
- uvicorn[standard]>=0.24.0
- pydantic>=2.5.0
- requests>=2.31.0

**Структура проекта**
```
.
├── api/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── requirements.txt
│   ├── README.md
│   └── .env.example
├── run_api.py
├── test_api.py
├── README.md
├── CHANGELOG.md
└── .gitignore
```

---

## [Unreleased]

### В планах

- [ ] Добавление аутентификации (JWT / API keys)
- [ ] WebSocket для real-time обновлений
- [ ] Экспорт данных в CSV/JSON
- [ ] Массовый опрос по расписанию (Celery / APScheduler)
- [ ] Интеграция с Prometheus / Grafana
- [ ] Микросервисная архитектура (разделение API и polling)
- [ ] Docker контейнеризация
- [ ] CI/CD пайплайны
