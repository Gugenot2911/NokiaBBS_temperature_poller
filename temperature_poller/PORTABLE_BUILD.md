# Создание портативной версии

## Предварительные требования

- Python 3.11+ (для запуска build_portable.py)
- Интернет-соединение (для скачивания Python и зависимостей)
- Windows 10 (для создания .bat скриптов)

## Процесс сборки

### 1. Запуск скрипта сборки
```batch
python build_portable.py
```

Скрипт выполнит следующие шаги:
1. Очистка выходной директории
2. Скачивание Embedded Python 3.11.9
3. Распаковка Python
4. Установка pip
5. Установка зависимостей проекта
6. Копирование файлов проекта
7. Создание START.bat
8. Создание README.txt

### 2. Результат
После успешной сборки будет создана папка `temperature-poller-portable`:
```
temperature-poller-portable/
├── START.bat              <- Запуск сервера
├── README.txt             <- Инструкция по использованию
├── config.json            <- Конфигурация (URL API, регион)
├── PORTABLE_SETUP.md      <- Подробная инструкция по настройке
├── run_api.py             <- Скрипт запуска
├── app_config.py          <- Загрузчик конфигурации
├── polling_manager.py     <- Менеджер опроса
├── api/                   <- FastAPI сервер
│   ├── main.py
│   ├── config.py
│   └── .env
├── nokia_polling/         <- Модуль опроса Nokia
└── databases/             <- Базы данных (создаётся при запуске)
```

## Конфигурация URL API

### Важное изменение
После последних изменений портативная версия **поддерживает настройку URL API** через:

1. **config.json** (рекомендуется)
   ```json
   {
     "api": {
       "base_url": "http://WSNS-LAVROV2:8001"
     }
   }
   ```

2. **Переменные окружения** в START.bat
   ```batch
   set API_BASE_URL=http://WSNS-LAVROV2:8001
   set REGION_PREFIX=NS
   ```

### Проверка после сборки
```batch
cd temperature-poller-portable
python -c "from app_config import get_config; print(get_config().get_hosts_api_url())"
```

Ожидаемый результат:
```
http://WSNS-LAVROV2:8001/api/v1/hosts?prefix=NS
```

## Распространение

### Подготовка к распространению
1. Отредактируйте `config.json` с нужным URL API
2. Запустите `build_portable.py`
3. Скопируйте папку `temperature-poller-portable` на USB-накопитель или сеть

### Минимальный размер
- Python embedded: ~25 МБ
- Зависимости: ~50 МБ
- Проект: ~5 МБ
- **Итого: ~80 МБ**

## Обновление портативной версии

### Полная пересборка
```batch
python build_portable.py
```

### Частичное обновление (только код)
1. Замените файлы проекта в `temperature-poller-portable/`
2. Сохраните `databases/` (данные пользователей)
3. Перезапустите сервер

## Известные ограничения

### Windows только
Портативная версия создаёт `.bat` скрипты для Windows. Для Linux/Mac используйте обычный запуск через Docker или pip.

### Нет автоматического обновления
Для обновления необходимо пересобрать портативную версию или вручную обновить файлы.

### Размер
~80 МБ может быть много для некоторых сред. Можно уменьшить, исключив ненужные зависимости.

## Настройка для production

### Перед сборкой
1. Отредактируйте `config.json`:
   ```json
   {
     "api": {
       "base_url": "http://WSNS-LAVROV2:8001"
     }
   }
   ```

2. Убедитесь, что все переменные окружения в `START.bat` раскомментированы:
   ```batch
   set API_BASE_URL=http://WSNS-LAVROV2:8001
   set REGION_PREFIX=NS
   ```

### После сборки
1. Скопируйте портативную версию на целевой сервер
2. Запустите `START.bat`
3. Проверьте логи на наличие правильных URL

## Тестирование портативной версии

### 1. Проверка конфигурации
```batch
python -c "from app_config import get_config; c = get_config(); print(c.get_hosts_api_url())"
```

### 2. Запуск сервера
```batch
START.bat
```

### 3. Проверка API
```batch
curl http://localhost:8000/health
```

### 4. Тестовый опрос
```batch
curl -X POST http://localhost:8000/api/v1/poll/manual ^
  -H "Content-Type: application/json" ^
  -d "{\"hostnames\": [\"NS0002\"], \"force\": true}"
```

## Автоматизация сборки

### Создать файл `build.bat`:
```batch
@echo off
echo ========================================
echo Сборка портативной версии
echo ========================================
python build_portable.py
if %ERRORLEVEL% EQU 0 (
    echo.
    echo Сборка завершена успешно!
    echo Папка: temperature-poller-portable
) else (
    echo.
    echo Ошибка сборки!
)
pause
```

## Частые проблемы

### Ошибка: "ModuleNotFoundError: No module named 'nokia_polling'"
**Причина:** Папка `nokia_polling` отсутствует в проекте

**Решение:**
1. Проверьте, что папка существует в исходном проекте
2. Добавьте её в список в `build_portable.py`

### Ошибка: "Cannot download Python"
**Причина:** Нет интернета или блокировка firewall

**Решение:**
1. Скачайте Python вручную с https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip
2. Распакуйте в `python_embeded.zip` рядом со скриптом

### Ошибка: "pip install failed"
**Причина:** Нет доступа к PyPI

**Решение:**
1. Проверьте интернет-соединение
2. Используйте корпоративный proxy:
   ```batch
   set HTTP_PROXY=http://proxy.company.com:8080
   set HTTPS_PROXY=http://proxy.company.com:8080
   ```

## Поддержка

При проблемах со сборкой предоставьте:
1. Версию Python (`python --version`)
2. Логи сборки
3. ОС и версию Windows

## См. также

- [PORTABLE_SETUP.md](PORTABLE_SETUP.md) - Настройка портативной версии
- [CONFIGURATION_URL.md](CONFIGURATION_URL.md) - Конфигурация URL API
- [README.md](README.md) - Общая документация