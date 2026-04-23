# Управление сервером Temperature Poller

## 🎮 Обзор функционала

Сервер поддерживает несколько способов управления состоянием:

| Способ | Описание | Платформа |
|--------|----------|-----------|
| **API Endpoints** | Программное управление через HTTP | Все |
| **Клавиатурные сочетания** | Ctrl+Z, fg | Unix/Linux/macOS |
| **Сигналы ОС** | SIGHUP, SIGINT, SIGTERM | Unix/Linux |
| **Process Managers** | systemd, supervisor, pm2 | Все |

---

## 📡 API Endpoints

### 1. Получение статуса системы

```bash
GET /api/v1/system/status
```

**Ответ:**
```json
{
  "server_state": "running",
  "is_polling": false,
  "uptime_seconds": 3600.5,
  "paused_since": null
}
```

**Поля:**
- `server_state` — текущее состояние (`running`, `paused`, `stopped`)
- `is_polling` — выполняется ли сейчас опрос
- `uptime_seconds` — время работы в секундах
- `paused_since` — время начала паузы (если применимо)

---

### 2. Приостановка опросов

```bash
POST /api/v1/system/pause
```

**Ответ:**
```json
{
  "success": true,
  "message": "Сервер приостановлен. Новые опросы не будут запускаться.",
  "server_state": "paused",
  "resume_command": "POST /api/v1/system/resume"
}
```

**Что происходит:**
- ✅ Сервер продолжает работать
- ✅ API для чтения данных доступны (температуры, статус)
- ❌ Новые опросы не запускаются
- ⏸️ Активные опросы завершаются нормально

**Использование:**
- Временное обслуживание системы
- Резервное копирование БД
- Обновление конфигурации
- Диагностика проблем

---

### 3. Возобновление опросов

```bash
POST /api/v1/system/resume
```

**Ответ:**
```json
{
  "success": true,
  "message": "Сервер возобновлён. Опросы продолжаются.",
  "server_state": "running"
}
```

**Что происходит:**
- ✅ Массовые опросы продолжаются по расписанию
- ✅ Ручные опросы доступны
- ✅ Логирование恢复正常

---

### 4. Перезапуск сервера

```bash
POST /api/v1/system/restart
```

**Параметры:**
```json
{
  "delay_seconds": 5,    // Задержка перед перезапуском (0-300 сек)
  "notify": true         // Уведомить перед перезапуском
}
```

**Ответ:**
```json
{
  "success": true,
  "message": "Перезапуск запланирован через 5 сек",
  "pid": 12345,
  "delay_seconds": 5,
  "restart_signal": "SIGHUP"
}
```

**⚠️ Важно:** Для работы требуется, чтобы сервер был запущен через процесс-менеджер (systemd, supervisor, pm2).

**Альтернатива:** Используйте `kill -HUP <pid>` для мягкого перезапуска.

---

### 5. Перезагрузка конфигурации

```bash
POST /api/v1/system/reload-config
```

**Ответ:**
```json
{
  "success": true,
  "message": "Конфигурация перезапущена",
  "config": {
    "region": {
      "prefix": "NS",
      "name": "North Station"
    },
    "polling": {
      "chunk_size": 10,
      "poll_interval_hours": 1
    }
  }
}
```

**Что происходит:**
- ✅ Перечитывает `config.json`
- ✅ Переинициализирует менеджер опроса
- ⚠️ Текущие опросы могут быть прерваны

**Использование:**
- Изменение региона
- Настройка интервалов опроса
- Обновление API URL

---

## ⌨️ Клавиатурные сочетания (Unix/Linux/macOS)

### Ctrl+Z (SIGTSTP)

**Приостановка процесса:**
```bash
# Сервер запущен в терминале
python run_api.py

# Нажать Ctrl+Z
[1]+  Стоп                python run_api.py
```

**Что происходит:**
- Процесс переходит в фоновый режим (stopped)
- Память сохраняется
- Можно возобновить через `fg` или API

### Возобновление через `fg`

```bash
# Вернуть процесс в foreground
fg

# Или возобновить в фоне
bg
```

### SIGHUP (мягкий перезапуск)

```bash
# Получить PID процесса
ps aux | grep run_api.py

# Отправить сигнал перезапуска
kill -HUP <pid>
```

**Что происходит:**
- Сервер плавно останавливается
- Перезапускается с новой конфигурацией
- Не прерывает активные запросы

---

## 🖥️ Process Managers

### systemd

**Файл сервиса:** `/etc/systemd/system/temperature-poller.service`

```ini
[Unit]
Description=Temperature Poller API Server
After=network.target

[Service]
Type=simple
User=poller
WorkingDirectory=/opt/temperature-poller
ExecStart=/opt/temperature-poller/venv/bin/python run_api.py
Restart=on-failure
RestartSec=10
KillSignal=SIGINT
KillMode=process

# Сигналы управления
ExecReload=/bin/kill -HUP $MAINPID

[Install]
WantedBy=multi-user.target
```

**Команды управления:**

```bash
# Запуск
sudo systemctl start temperature-poller

# Остановка
sudo systemctl stop temperature-poller

# Перезапуск
sudo systemctl restart temperature-poller

# Перезагрузка конфигурации
sudo systemctl reload temperature-poller

# Статус
sudo systemctl status temperature-poller

# Пауза (системная)
sudo systemctl stop temperature-poller

# Возобновление
sudo systemctl start temperature-poller
```

### supervisor

**Файл конфига:** `/etc/supervisor/conf.d/temperature-poller.conf`

```ini
[program:temperature-poller]
command=/opt/temperature-poller/venv/bin/python run_api.py
directory=/opt/temperature-poller
user=poller
autostart=true
autorestart=true
stopasgroup=true
killasgroup=true
stopsignal=INT
```

**Команды:**

```bash
# Перезапуск
sudo supervisorctl restart temperature-poller

# Пауза
sudo supervisorctl stop temperature-poller

# Возобновление
sudo supervisorctl start temperature-poller

# Перезагрузка конфига
sudo supervisorctl reread
sudo supervisorctl update
```

### pm2 (Node.js-style для Python)

```bash
# Установка
npm install -g pm2

# Запуск
pm2 start run_api.py --name temperature-poller

# Перезапуск
pm2 restart temperature-poller

# Пауза (остановка)
pm2 stop temperature-poller

# Возобновление
pm2 start temperature-poller

# Перезагрузка конфига без простоя
pm2 reload temperature-poller
```

---

## 🐳 Docker

### Запуск контейнера

```bash
docker run -d \
  --name temperature-poller \
  -p 8000:8000 \
  -v $(pwd)/config.json:/app/config.json \
  -v $(pwd)/databases:/app/databases \
  temperature-poller:latest
```

### Управление через Docker

```bash
# Пауза контейнера
docker pause temperature-poller

# Возобновление
docker unpause temperature-poller

# Перезапуск
docker restart temperature-poller

# Перезагрузка конфигурации
docker exec temperature-poller python -c "from app_config import reload_config; reload_config()"
docker restart temperature-poller
```

### Health check в Docker Compose

```yaml
version: '3.8'

services:
  temperature-poller:
    image: temperature-poller:latest
    ports:
      - "8000:8000"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

---

## 🔧 Сценарии использования

### 1. Временное обслуживание

```bash
#!/bin/bash
# maintenance.sh — обслуживание системы

echo "🔧 Начало обслуживания..."

# Приостановить опросы
curl -X POST http://localhost:8000/api/v1/system/pause

# Проверить статус
sleep 2
STATUS=$(curl -s http://localhost:8000/api/v1/system/status)
echo "Статус: $(echo $STATUS | jq -r '.server_state')"

# Выполнить обслуживание
echo "📦 Резервное копирование БД..."
tar -czf /backup/databases-$(date +%Y%m%d).tar.gz databases/

# Возобновить
echo "▶️ Возобновление работы..."
curl -X POST http://localhost:8000/api/v1/system/resume

echo "✅ Обслуживание завершено"
```

### 2. Мониторинг uptime

```bash
#!/bin/bash
# monitor_uptime.sh — мониторинг времени работы

while true; do
  STATUS=$(curl -s http://localhost:8000/api/v1/system/status)
  UPTIME=$(echo $STATUS | jq -r '.uptime_seconds')
  STATE=$(echo $STATUS | jq -r '.server_state')
  
  if [ "$STATE" = "paused" ]; then
    echo "⏸️ [$(date)] Приостановлен"
  else
    HOURS=$(echo "scale=2; $UPTIME / 3600" | bc)
    echo "▶️ [$(date)] Работает ${HOURS} часов"
  fi
  
  sleep 60
done
```

### 3. Автоматическое возобновление после сбоя

```python
#!/usr/bin/env python3
# auto_resume.py — автоматическое возобновление

import requests
import time

BASE_URL = "http://localhost:8000"

def check_and_resume():
    """Проверка статуса и автоматическое возобновление"""
    try:
        status = requests.get(f"{BASE_URL}/api/v1/system/status", timeout=5)
        if status.json()['server_state'] == 'paused':
            print("⚠️  Сервер приостановлен, возобновляю...")
            resume = requests.post(f"{BASE_URL}/api/v1/system/resume")
            if resume.json()['success']:
                print("✅ Сервер возобновлён")
            else:
                print("❌ Ошибка возобновления:", resume.json())
    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка проверки: {e}")

if __name__ == "__main__":
    check_and_resume()
```

**Запуск через cron:**
```bash
# /etc/cron.d/temperature-poller-monitor
*/5 * * * * root /usr/bin/python3 /opt/temperature-poller/auto_resume.py >> /var/log/poller-monitor.log 2>&1
```

### 4. Graceful shutdown перед деплоем

```bash
#!/bin/bash
# deploy.sh — деплой с graceful shutdown

echo "🚀 Подготовка к деплою..."

# Приостановить новые опросы
curl -X POST http://localhost:8000/api/v1/system/pause

# Дождаться завершения текущего опроса
echo "⏳ Ожидание завершения опроса..."
while true; do
  STATUS=$(curl -s http://localhost:8000/api/v1/status)
  IS_POLLING=$(echo $STATUS | jq -r '.is_polling')
  
  if [ "$IS_POLLING" = "false" ]; then
    echo "✅ Опрос завершён"
    break
  fi
  
  sleep 5
done

# Остановить сервер
curl -X POST http://localhost:8000/api/v1/system/restart \
  -H "Content-Type: application/json" \
  -d '{"delay_seconds": 0}'

# Обновить код
git pull origin main

# Перезапустить
python run_api.py &

echo "✅ Деплой завершён"
```

---

## 📊 Состояния сервера

### Диаграмма состояний

```
                    ┌─────────────┐
                    │   START     │
                    └──────┬──────┘
                           │
                           ▼
                    ┌─────────────┐
             ┌──────│  RUNNING    │──────┐
             │      └──────┬──────┘      │
             │             │             │
      pause  │             │             │  stop
      (API)  │             │             │  (API)
             │             │             │
             ▼             │             ▼
      ┌─────────────┐      │      ┌─────────────┐
      │   PAUSED    │──────┘      │  STOPPED    │
      └─────────────┘ resume      └─────────────┘
```

### Таблица состояний

| Состояние | Опросы | API Чтение | API Запись | Описание |
|-----------|--------|------------|------------|----------|
| `running` | ✅ Да | ✅ Доступно | ✅ Доступно | Нормальная работа |
| `paused` | ❌ Нет | ✅ Доступно | ⚠️ Частично | Приостановлен |
| `stopped` | ❌ Нет | ❌ Недоступно | ❌ Недоступно | Остановлен |

**Примечание:** В состоянии `paused` эндпоинты чтения (температуры, статус) доступны, но опросы не запускаются.

---

## 🛠️ Диагностика

### Проверка состояния

```bash
#!/bin/bash
# check_status.sh — быстрая проверка состояния

echo "🔍 Проверка состояния сервера..."
echo ""

# Health check
HEALTH=$(curl -s http://localhost:8000/health)
echo "Health: $(echo $HEALTH | jq -r '.status')"
echo "State:  $(echo $HEALTH | jq -r '.server_state')"
echo ""

# System status
STATUS=$(curl -s http://localhost:8000/api/v1/system/status)
echo "Uptime:  $(echo $STATUS | jq -r '.uptime_seconds') сек"
echo "Polling: $(echo $STATUS | jq -r '.is_polling')"
echo ""

# Process check
if pgrep -f "run_api.py" > /dev/null; then
  echo "✅ Процесс запущен"
  PID=$(pgrep -f "run_api.py")
  echo "PID: $PID"
else
  echo "❌ Процесс не запущен"
fi
```

### Логи

**Где искать логи:**
- Консоль: stdout/stderr
- systemd: `journalctl -u temperature-poller -f`
- supervisor: `/var/log/supervisor/temperature-poller.out`
- pm2: `pm2 logs temperature-poller`

**Ключевые сообщения:**
```
🚀 Запуск API сервера...
✅ API сервер готов к работе
🎮 Управление:
   - Ctrl+Z: Пауза/возобновление
   - POST /api/v1/system/pause: Приостановить опросы
   - POST /api/v1/system/resume: Возобновить опросы
⏸️  Сервер приостановлен через API
▶️  Сервер возобновлён
🛑 Остановка API сервера...
```

---

## ⚠️ Важные замечания

1. **Пауза не останавливает активные опросы** — они завершатся нормально
2. **База данных доступна во время паузы** для чтения
3. **Health check возвращает `status: paused`** — можно использовать для мониторинга
4. **Перезагрузка конфигурации** может прервать текущие операции
5. **SIGHUP поддерживается только на Unix** — на Windows используйте API restart
6. **Для production рекомендуется** использовать process managers (systemd, supervisor)

---

## 📚 Дополнительные ресурсы

- [README.md](README.md) — основная документация
- [api/README.md](api/README.md) — детальная документация API
- [CONFIG.md](CONFIG.md) — конфигурация приложения
- [BUILD_INSTRUCTIONS.txt](BUILD_INSTRUCTIONS.txt) — сборка Windows

---

**Автор:** NLP-Core-Team  
**Версия:** 1.0.0  
**Дата:** 2024
