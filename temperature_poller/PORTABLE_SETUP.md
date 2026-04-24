# Настройка портативной версии

## Быстрый старт

### 1. Запуск
Двойной клик на `START.bat` или:
```batch
START.bat
```

### 2. Настройка URL API

#### Способ 1: Через config.json (рекомендуется)
Откройте `config.json` в текстовом редакторе:
```json
{
  "region": {
    "prefix": "NS",
    "name": "North Station"
  },
  "api": {
    "base_url": "http://WSNS-LAVROV2:8001",
    "hosts_endpoint": "/api/v1/hosts"
  },
  ...
}
```

Измените `base_url` на нужный:
- Production: `http://WSNS-LAVROV2:8001`
- Тестовая среда: `http://localhost:8001`
- Другой сервер: `http://your-server:8001`

#### Способ 2: Через переменные окружения
Откройте `START.bat` в текстовом редакторе и раскомментируйте строки:
```batch
REM Для production:
set API_BASE_URL=http://WSNS-LAVROV2:8001
set REGION_PREFIX=NS

REM Для тестовой среды:
REM set API_BASE_URL=http://localhost:8001
REM set REGION_PREFIX=NS
```

### 3. Проверка конфигурации
Запустите проверку URL:
```batch
python -c "from app_config import get_config; c = get_config(); print('API URL:', c.get_hosts_api_url())"
```

Ожидаемый вывод:
```
API URL: http://WSNS-LAVROV2:8001/api/v1/hosts?prefix=NS
```

## Приоритет конфигурации

Конфигурация загружается в следующем порядке (от высшего к низшему):

1. **Переменные окружения в START.bat**
   ```batch
   set API_BASE_URL=http://your-server:8001
   set REGION_PREFIX=NS
   ```

2. **Файл config.json**
   ```json
   {
     "api": {
       "base_url": "http://WSNS-LAVROV2:8001"
     }
   }
   ```

3. **Значения по умолчанию** (только если ничего не настроено)
   ```
   http://localhost:8001/api/v1/hosts?prefix=NS
   ```

## Примеры конфигурации

### Production (WSNS-LAVROV2)
**config.json:**
```json
{
  "api": {
    "base_url": "http://WSNS-LAVROV2:8001",
    "hosts_endpoint": "/api/v1/hosts"
  }
}
```

### Тестовая среда (localhost)
**config.json:**
```json
{
  "api": {
    "base_url": "http://localhost:8001",
    "hosts_endpoint": "/api/v1/hosts"
  }
}
```

### Кастомный сервер
**START.bat:**
```batch
set API_BASE_URL=http://192.168.1.100:8001
set REGION_PREFIX=EU
```

**config.json:**
```json
{
  "region": {
    "prefix": "EU",
    "name": "European Station"
  }
}
```

## Обновление конфигурации без перезапуска

После изменения `config.json`:
```batch
curl -X POST http://localhost:8000/api/v1/system/reload-config
```

## Диагностика

### Проверка статуса сервера
```batch
curl http://localhost:8000/health
```

### Проверка URL API
```batch
python -c "from app_config import get_config; print(get_config().get_hosts_api_url())"
```

### Просмотр логов
Логи выводятся в консоль при запуске через `START.bat`. Ищите строку:
```
🔗 API URL для хостов: http://WSNS-LAVROV2:8001/api/v1/hosts?prefix=NS
```

## Частые проблемы

### Ошибка: "Cannot fetch hosts from API"
**Причина:** Неправильный URL API или сервер недоступен

**Решение:**
1. Проверьте `config.json`
2. Убедитесь, что сервер API доступен:
   ```batch
   curl http://WSNS-LAVROV2:8001/health
   ```

### Ошибка: "Кэш хостов пуст"
**Причина:** API вернул пустой список или недоступен

**Решение:**
1. Проверьте соединение
2. Проверьте префикс региона в `config.json`
3. Используйте `manual_poll` для тестирования

### Сервер не запускается
**Причина:** Порт занят или ошибка конфигурации

**Решение:**
1. Измените порт в `START.bat`:
   ```batch
   python run_api.py --port 8080
   ```
2. Проверьте логи на наличие ошибок

## Обновление портативной версии

1. Остановите сервер (Ctrl+C в окне START.bat)
2. Замените файлы в папке портативной версии
3. Перезапустите `START.bat`

Данные в `databases/` сохраняются при обновлении.

## Поддержка

При обращении за помощью предоставьте:
1. Вывод команды проверки конфигурации
2. Логи запуска сервера
3. Версию Python (вывод `python --version`)