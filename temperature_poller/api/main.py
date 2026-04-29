#!/usr/bin/env python3
"""
FastAPI микросервис для управления опросом сетевых устройств.

REST API для:
- Запуска массового и ручного опроса
- Получения температурных данных (уровни 1, 2, 3)
- Мониторинга статуса системы
- Управление хостами

Автор: NLP-Core-Team
"""

import asyncio
import logging
import signal
import os
import sys
from contextlib import asynccontextmanager
from typing import Optional, List
from datetime import datetime
from enum import Enum

from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from polling_manager import PollingManager, PollingManagerConfig, create_polling_manager
from sqlite_temperature import DatabaseConfig, TemperatureDBManager
from logging_config import setup_logging, get_logger
from api.config import settings
from app_config import get_config


# Настройка логирования
logger = get_logger()

# Загрузка конфигурации приложения
app_config = get_config()


# =============================================================================
# Управление состоянием сервера
# =============================================================================

class ServerState(str, Enum):
    """Состояние сервера"""
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"


class APIState:
    """Глобальное состояние API"""
    manager: Optional[PollingManager] = None
    db_manager: Optional[TemperatureDBManager] = None
    background_tasks: asyncio.Queue = None
    is_shutting_down: bool = False
    server_state: ServerState = ServerState.RUNNING
    pause_event: asyncio.Event = None
    start_time: Optional[datetime] = None

    def __init__(self):
        """Инициализация событий паузы"""
        self.pause_event = asyncio.Event()
        self.pause_event.set()  # По умолчанию не приостановлено


state = APIState()


# =============================================================================
# Обработка сигналов клавиатуры
# =============================================================================

def setup_signal_handlers():
    """Настройка обработчиков сигналов для паузы/возобновления"""
    
    def handle_pause_signal(signum, frame):
        """Обработчик сигнала SIGTSTP (Ctrl+Z)"""
        if state.server_state == ServerState.RUNNING:
            logger.warning("⏸️  Получен сигнал паузы (SIGTSTP)")
            state.server_state = ServerState.PAUSED
            state.pause_event.clear()
            logger.warning("Сервер приостановлен. Используйте /api/v1/system/resume для продолжения")
        elif state.server_state == ServerState.PAUSED:
            logger.warning("▶️  Получен сигнал возобновления")
            state.server_state = ServerState.RUNNING
            state.pause_event.set()
            logger.warning("Сервер возобновлён")
    
    # Поддержка только на Unix-системах
    if hasattr(signal, 'SIGTSTP'):
        signal.signal(signal.SIGTSTP, handle_pause_signal)
        logger.info("Обработчик Ctrl+Z (SIGTSTP) установлен")


# =============================================================================
# Жизненный цикл приложения
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения"""
    
    # Startup
    logger.info("🚀 Запуск API сервера...")
    logger.info(f"📡 Host: {settings.host}, Port: {settings.port}")
    logger.info(f"📍 Регион: {app_config.region.prefix} - {app_config.region.name}")
    
    # Использование конфигурации из config.json
    hosts_api_url = app_config.get_hosts_api_url()
    logger.info(f"🔗 API URL для хостов: {hosts_api_url}")
    
    # Инициализация менеджера опроса с конфигурацией
    config = PollingManagerConfig(
        api_url=hosts_api_url,  # URL с учётом префикса региона
        db_base_dir=app_config.database.base_dir,
        checkpoint_path=app_config.checkpoint.path,
        chunk_size=app_config.polling.chunk_size,
        checkpoint_interval=app_config.polling.checkpoint_interval,
        poll_interval_hours=app_config.polling.poll_interval_hours,
        hosts_ttl_hours=app_config.polling.hosts_ttl_hours
    )

    state.manager = create_polling_manager(config=config)
    state.db_manager = TemperatureDBManager(base_dir=app_config.database.base_dir)
    state.background_tasks = asyncio.Queue()
    state.start_time = datetime.now()

    # Настройка обработчиков сигналов
    setup_signal_handlers()
    
    logger.info("✅ API сервер готов к работе")
    logger.info("🎮 Управление:")
    logger.info("   - Ctrl+Z: Пауза/возобновление")
    logger.info("   - POST /api/v1/system/pause: Приостановить опросы")
    logger.info("   - POST /api/v1/system/resume: Возобновить опросы")
    
    yield
    
    # Shutdown
    logger.info("🛑 Остановка API сервера...")
    state.is_shutting_down = True
    
    # Ожидание завершения фоновых задач
    while not state.background_tasks.empty():
        await asyncio.sleep(1)
    
    logger.info("✅ API сервер остановлен")


# =============================================================================
# FastAPI приложение
# =============================================================================

app = FastAPI(
    title="Temperature Poller API",
    description="""
## Микросервис для управления опросом температурных данных Nokia

### Возможности:
- **Опрос устройств**: массовый и ручной опрос температур
- **Данные**: трехуровневый доступ к температурным данным
- **Мониторинг**: статус системы и статистика
- **Управление хостами**: обновление списка хостов
- **Управление сервером**: пауза, продолжение, перезапуск

### Управление состоянием:
- **Ctrl+Z**: Приостановка/возобновление процесса
- **API endpoints**: Программное управление

### Перезапуск сервера:
**POST /api/v1/system/restart** - Graceful restart сервера.

**Процесс перезапуска:**
1. Устанавливаем состояние `SHUTDOWN`
2. Ждём завершения текущего опроса (макс. 60 сек)
3. Останавливаем фоновые задачи
4. Перезапускаем процесс через `os.execv()`

⚠️ **Внимание**: Restart требует права на выполнение процесса.
В production рекомендуется использовать systemd/docker restart.

**Пример использования:**
```bash
# Через curl
curl -X POST http://localhost:8000/api/v1/system/restart

# Через PowerShell
Invoke-WebRequest -Uri http://localhost:8000/api/v1/system/restart -Method POST
```

### Аутентификация:
На данный момент аутентификация не требуется (локальный сервис).
    """,
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
cors_origins = [origin.strip() for origin in settings.cors_origins.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Ответы Pydantic
# =============================================================================

from pydantic import BaseModel, Field


class HostResponse(BaseModel):
    hostname: str
    ip: Optional[str] = None
    vendor: str = "nokia"
    availability: bool = True


class PollingStatusResponse(BaseModel):
    is_polling: bool
    hosts_count: int
    hosts_cache_fresh: bool
    last_poll_stats: Optional[dict] = None
    checkpoint_status: dict = {}


class ManualPollRequest(BaseModel):
    hostnames: List[str] = Field(..., description="Список имён хостов")
    force: bool = Field(False, description="Принудительная перезапись")


class SitesPollRequest(BaseModel):
    master_sites: List[str] = Field(..., description="Список master_site для опроса")


class ManualPollResponse(BaseModel):
    success: bool
    success_count: int
    error_count: int
    skipped_count: int
    message: str


class TemperatureLevel1Response(BaseModel):
    level: int
    page: int
    page_size: int
    total_pages: int
    total_stations: int
    data: list


class TemperatureLevel2Response(BaseModel):
    level: int
    hostname: str
    rru_bits: str
    bbu_bits: str
    rru_anomaly_count: int
    bbu_anomaly_count: int


class TemperatureLevel3Response(BaseModel):
    level: int
    hostname: str
    rru_max: list
    rru_min: list
    rru_avg: list
    bbu_max: list
    bbu_min: list
    bbu_avg: list
    hours: list


class APIHealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str = "1.0.0"
    server_state: str = "running"


class SystemStatusResponse(BaseModel):
    server_state: str
    is_polling: bool
    uptime_seconds: Optional[float] = None
    paused_since: Optional[str] = None


class ServerRestartResponse(BaseModel):
    success: bool
    message: str
    restart_initiated: bool


# =============================================================================
# Health Check
# =============================================================================

@app.get("/health", response_model=APIHealthResponse, tags=["System"])
async def health_check():
    """Проверка здоровья API"""
    return APIHealthResponse(
        status="healthy" if state.server_state == ServerState.RUNNING else "paused",
        timestamp=datetime.now().isoformat(),
        server_state=state.server_state.value
    )


@app.get("/", tags=["System"])
async def root():
    """Корневой эндпоинт с информацией о API"""
    return {
        "service": "Temperature Poller API",
        "version": "1.0.0",
        "server_state": state.server_state.value,
        "docs": "/docs",
        "endpoints": {
            "polling": "/api/v1/poll/",
            "hosts": "/api/v1/hosts/",
            "temperature": "/api/v1/temperature/",
            "status": "/api/v1/status/",
            "system": "/api/v1/system/"
        },
        "polling_endpoints": {
            "mass_poll": "POST /api/v1/poll/mass",
            "manual_poll": "POST /api/v1/poll/manual",
            "poll_sites": "POST /api/v1/poll/sites"
        },
        "system_endpoints": {
            "status": "GET /api/v1/system/status",
            "pause": "POST /api/v1/system/pause",
            "resume": "POST /api/v1/system/resume",
            "restart": "POST /api/v1/system/restart"
        }
    }


# =============================================================================
# Эндпоинты управления системой (System Control)
# =============================================================================

@app.get(
    "/api/v1/system/status",
    response_model=SystemStatusResponse,
    tags=["System Control"]
)
async def get_system_status():
    """
    Получение текущего статуса системы.
    
    Возвращает состояние сервера (running/paused/stopped),
    информацию об опросе и время работы.
    """
    import time
    
    uptime = None
    if state.start_time:
        uptime = (datetime.now() - state.start_time).total_seconds()
    
    return SystemStatusResponse(
        server_state=state.server_state.value,
        is_polling=state.manager._is_polling if state.manager else False,
        uptime_seconds=round(uptime, 2) if uptime else None
    )


@app.post(
    "/api/v1/system/pause",
    tags=["System Control"]
)
async def pause_server():
    """
    Приостановка опросов.
    
    Сервер продолжает работать, но не запускает новые опросы.
    Активные опросы завершатся нормально.
    
    **Аналог Ctrl+Z для процесса.**
    """
    if state.server_state == ServerState.PAUSED:
        return {
            "success": False,
            "message": "Сервер уже приостановлен",
            "server_state": state.server_state.value
        }
    
    state.server_state = ServerState.PAUSED
    state.pause_event.clear()
    
    logger.warning("⏸️  Сервер приостановлен через API")
    
    return {
        "success": True,
        "message": "Сервер приостановлен. Новые опросы не будут запускаться.",
        "server_state": state.server_state.value,
        "resume_command": "POST /api/v1/system/resume"
    }


@app.post(
    "/api/v1/system/resume",
    tags=["System Control"]
)
async def resume_server():
    """
    Возобновление опросов.
    
    Возвращает сервер в нормальное состояние.
    
    **Аналог `fg` после Ctrl+Z.**
    """
    if state.server_state == ServerState.RUNNING:
        return {
            "success": False,
            "message": "Сервер уже работает",
            "server_state": state.server_state.value
        }
    
    state.server_state = ServerState.RUNNING
    state.pause_event.set()
    
    logger.info("▶️  Сервер возобновлён")
    
    return {
        "success": True,
        "message": "Сервер возобновлён. Опросы продолжаются.",
        "server_state": state.server_state.value
    }


@app.post(
    "/api/v1/system/restart",
    response_model=ServerRestartResponse,
    tags=["System Control"]
)
async def restart_server():
    """
    Перезапуск сервера.
    
    Graceful restart с ожиданием завершения текущего опроса.
    
    **Процесс перезапуска:**
    1. Устанавливаем состояние `SHUTDOWN`
    2. Ждём завершения текущего опроса (макс. 60 сек)
    3. Останавливаем фоновые задачи
    4. Перезапускаем процесс через `os.execv()`
    
    **Аналог:** `systemctl restart temperature-poller`
    
    **Пример использования:**
    ```bash
    # Через curl
    curl -X POST http://localhost:8000/api/v1/system/restart
    
    # Через PowerShell
    Invoke-WebRequest -Uri http://localhost:8000/api/v1/system/restart -Method POST
    
    # Через Python
    import requests
    response = requests.post('http://localhost:8000/api/v1/system/restart')
    print(response.json())
    ```
    
    **Внимание:** Требует прав на выполнение процесса.
    В production используйте systemd/docker restart.
    """
    if state.is_shutting_down:
        return ServerRestartResponse(
            success=False,
            message="Сервер уже перезапускается",
            restart_initiated=False
        )
    
    if state.manager and state.manager._is_polling:
        logger.warning("🔄 Текущий опрос в процессе, ожидаем завершения...")
    
    state.is_shutting_down = True
    state.server_state = ServerState.STOPPED
    
    # Ожидание завершения опроса (макс. 60 сек)
    max_wait = 60
    waited = 0
    while state.manager and state.manager._is_polling and waited < max_wait:
        await asyncio.sleep(1)
        waited += 1
    
    if state.manager and state.manager._is_polling:
        logger.warning(f"⚠️ Опрос не завершился за {max_wait}сек, принудительное завершение")
    
    # Ожидание фоновых задач
    while not state.background_tasks.empty() and waited < max_wait:
        await asyncio.sleep(1)
        waited += 1
    
    logger.info(f"🔄 Инициация перезапуска сервера (ожидание: {waited}сек)")
    
    # Перезапуск процесса
    try:
        import sys
        logger.info("🚀 Выполнение перезапуска процесса...")
        
        # Получаем путь к Python и скрипту
        python = sys.executable
        script = os.path.abspath(__file__)
        
        # Восстанавливаем состояние для успешного старта
        state.is_shutting_down = False
        state.server_state = ServerState.RUNNING
        
        # Перезапуск через execv (заменяет текущий процесс)
        os.execv(python, [python, script])
        
    except Exception as e:
        logger.error(f"❌ Ошибка перезапуска: {e}", exc_info=True)
        # Восстанавливаем состояние при ошибке
        state.is_shutting_down = False
        state.server_state = ServerState.RUNNING
        
        return ServerRestartResponse(
            success=False,
            message=f"Ошибка перезапуска: {e}",
            restart_initiated=False
        )
    
    # Если execv успешен, этот код не достигнется
    return ServerRestartResponse(
        success=True,
        message="Перезапуск инициирован",
        restart_initiated=True
    )


# =============================================================================
# Эндпоинты опроса (Polling)
# =============================================================================

@app.post(
    "/api/v1/poll/mass",
    response_model=ManualPollResponse,
    tags=["Polling"]
)
async def start_mass_poll(background_tasks: BackgroundTasks):
    """
    Запуск массового опроса всех хостов.
    
    Асинхронная операция. Возвращает подтверждение запуска.
    
    **Проверяет состояние паузы.**
    """
    if state.manager is None:
        raise HTTPException(status_code=503, detail="Менеджер опроса не инициализирован")
    
    if state.server_state == ServerState.PAUSED:
        raise HTTPException(
            status_code=423, 
            detail="Сервер приостановлен. Используйте /api/v1/system/resume"
        )
        
    if state.is_shutting_down:
        raise HTTPException(status_code=503, detail="Сервис останавливается")
    
    # Проверка параллельного опроса
    status = state.manager.get_status()
    if status['is_polling']:
        raise HTTPException(status_code=409, detail="Опрос уже выполняется")
    
    # Запуск в фоне
    background_tasks.add_task(
        _run_mass_poll_task,
        state.manager
    )

    return ManualPollResponse(
        success=True,
        success_count=0,
        error_count=0,
        skipped_count=0,
        message="Массовый опрос запущен в фоновом режиме"
    )


async def _run_mass_poll_task(manager: PollingManager):
    """Фоновая задача массового опроса"""
    try:
        logger.info("🔄 Фоновый массовый опрос начат")
        result = await manager.start_mass_poll()
        logger.info(f"✅ Фоновый массовый опрос завершён: {result}")
    except Exception as e:
        logger.error(f"❌ Ошибка фонового опроса: {e}", exc_info=True)


@app.post(
    "/api/v1/poll/manual",
    response_model=ManualPollResponse,
    tags=["Polling"]
)
async def manual_poll(request: ManualPollRequest):
    """
    Ручной опрос выбранных хостов.
    
    Пример:
    ```json
    {
        "hostnames": ["NS0830", "NS1120"],
        "force": false
    }
    ```
    """
    if state.manager is None:
        raise HTTPException(status_code=503, detail="Менеджер опроса не инициализирован")
    
    if not request.hostnames:
        raise HTTPException(status_code=400, detail="Список хостов не может быть пустым")
    
    try:
        result = await state.manager.manual_poll(
            hostnames=request.hostnames,
            force=request.force
        )
        
        return ManualPollResponse(
            success=True,
            success_count=result.success_count,
            error_count=result.error_count,
            skipped_count=result.skipped_count,
            message=f"Опрос завершён: {result.success_count} успешно, {result.error_count} ошибок"
        )
    except Exception as e:
        logger.error(f"Ошибка ручного опроса: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post(
    "/api/v1/poll/sites",
    response_model=ManualPollResponse,
    tags=["Polling"]
)
async def poll_sites_from_api(request: SitesPollRequest):
    """
    Точечный опрос через API сайтов (без кэширования).
    
    Получает информацию о сайтах из http://wsns-lavrov2:8001/api/v1/sites
    и опрашивает их.
    
    Пример:
    ```json
    {
        "master_sites": ["NS1120", "NS0830"]
    }
    ```
    
    **Не использует кэш хостов - всегда запрашивает свежие данные из API.**
    """
    if state.manager is None:
        raise HTTPException(status_code=503, detail="Менеджер опроса не инициализирован")
    
    if not request.master_sites:
        raise HTTPException(status_code=400, detail="Список master_site не может быть пустым")
    
    try:
        result = await state.manager.fetch_and_poll_sites(
            master_sites=request.master_sites
        )
    
        return ManualPollResponse(
            success=True,
            success_count=result.success_count,
            error_count=result.error_count,
            skipped_count=result.skipped_count,
            message=f"Опрос завершён: {result.success_count} успешно, {result.error_count} ошибок"
        )
    except Exception as e:
        logger.error(f"Ошибка опроса через API сайтов: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post(
    "/api/v1/poll/hosts/refresh",
    tags=["Polling"]
)
async def refresh_hosts():
    """
    Принудительное обновление списка хостов из API.
    """
    if state.manager is None:
        raise HTTPException(status_code=503, detail="Менеджер опроса не инициализирован")
    
    try:
        success = state.manager.refresh_hosts_from_api()
        
        if success:
            return {"success": True, "message": "Список хостов успешно обновлён"}
        else:
            return {"success": False, "message": "Использован кэш или ошибка API"}
            
    except Exception as e:
        logger.error(f"Ошибка обновления хостов: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Эндпоинты температурных данных (Temperature)
# =============================================================================

@app.get(
    "/api/v1/temperature/level1",
    response_model=TemperatureLevel1Response,
    tags=["Temperature Data"]
)
async def get_temperature_level1(
    page: int = Query(1, ge=1, description="Номер страницы"),
    page_size: int = Query(10, ge=1, le=100, description="Размер страницы")
):
    """
    Получение списка станций с флагами аномалий (Уровень 1).
    
    Быстрый эндпоинт (1-5 мс) для загрузки таблицы.
    """
    # Получить префикс из первого доступного БД
    if state.db_manager is None:
        raise HTTPException(status_code=503, detail="Менеджер БД не инициализирован")
    
    databases = state.db_manager.list_databases()
    if not databases:
        return TemperatureLevel1Response(
            level=1,
            page=page,
            page_size=page_size,
            total_pages=0,
            total_stations=0,
            data=[]
        )
    
    # Используем первую доступную БД
    prefix = databases[0]['prefix']
    db = state.db_manager.get_db_by_prefix(prefix)
    
    if db is None:
        raise HTTPException(status_code=503, detail=f"БД для региона {prefix} недоступна")
    
    try:
        result = db.get_level1(page=page, page_size=page_size)
        return TemperatureLevel1Response(**result)
    except Exception as e:
        logger.error(f"Ошибка получения Level 1 данных: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/api/v1/temperature/level2/{hostname}",
    response_model=TemperatureLevel2Response,
    tags=["Temperature Data"]
)
async def get_temperature_level2(hostname: str):
    """
    Получение бинарной тепловой шкалы для хоста (Уровень 2).
    
    Возвращает 48 бит аномалий для RRU и BBU.
    
    Пример: `/api/v1/temperature/level2/NS0830`
    """
    if state.db_manager is None:
        raise HTTPException(status_code=503, detail="Менеджер БД не инициализирован")
    
    # Найти БД для хоста
    prefix = hostname[:2].upper()
    db = state.db_manager.get_db_by_prefix(prefix)
    
    if db is None:
        # Попытка инициализировать БД
        try:
            dummy_data = [{'hostname': hostname, 'temperature': {}}]
            db = state.db_manager.get_db(dummy_data)
        except Exception as e:
            raise HTTPException(status_code=404, detail=f"БД для региона {prefix} не найдена")
    
    try:
        result = db.get_level2(hostname)
        return TemperatureLevel2Response(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Ошибка получения Level 2 данных для {hostname}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/api/v1/temperature/level3/{hostname}",
    response_model=TemperatureLevel3Response,
    tags=["Temperature Data"]
)
async def get_temperature_level3(
    hostname: str,
    hours: int = Query(48, ge=1, le=168, description="Количество часов (1-168)")
):
    """
    Получение полных спарклайнов для хоста (Уровень 3).
    
    Возвращает 48 (или меньше) значений температур для детального просмотра.
    
    Пример: `/api/v1/temperature/level3/NS0830?hours=48`
    """
    if state.db_manager is None:
        raise HTTPException(status_code=503, detail="Менеджер БД не инициализирован")
    
    # Найти БД для хоста
    prefix = hostname[:2].upper()
    db = state.db_manager.get_db_by_prefix(prefix)
    
    if db is None:
        try:
            dummy_data = [{'hostname': hostname, 'temperature': {}}]
            db = state.db_manager.get_db(dummy_data)
        except Exception as e:
            raise HTTPException(status_code=404, detail=f"БД для региона {prefix} не найдена")
    
    try:
        result = db.get_level3(hostname, hours=hours)
        return TemperatureLevel3Response(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Ошибка получения Level 3 данных для {hostname}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/api/v1/temperature/hosts",
    tags=["Temperature Data"]
)
async def get_hosts_list():
    """Получение списка всех станций"""
    if state.db_manager is None:
        raise HTTPException(status_code=503, detail="Менеджер БД не инициализирован")
    
    databases = state.db_manager.list_databases()
    all_hosts = []
    
    for db_info in databases:
        db = state.db_manager.get_db_by_prefix(db_info['prefix'])
        if db:
            hosts = db.get_stations_list()
            all_hosts.extend(hosts)
    
    return {"hosts": sorted(all_hosts), "total": len(all_hosts)}


# =============================================================================
# Эндпоинты статуса (Status)
# =============================================================================

@app.get(
    "/api/v1/status",
    response_model=PollingStatusResponse,
    tags=["Status"]
)
async def get_polling_status():
    """Получение текущего статуса системы опроса"""
    if state.manager is None:
        raise HTTPException(status_code=503, detail="Менеджер опроса не инициализирован")
    
    status = state.manager.get_status()
    return PollingStatusResponse(**status)


@app.get(
    "/api/v1/status/stats",
    tags=["Status"]
)
async def get_polling_stats():
    """Получение статистики последнего опроса"""
    if state.manager is None:
        raise HTTPException(status_code=503, detail="Менеджер опроса не инициализирован")
    
    stats = state.manager.get_last_poll_stats()
    if stats is None:
        return {"message": "Опросы ещё не выполнялись"}
    
    return stats


@app.get(
    "/api/v1/status/databases",
    tags=["Status"]
)
async def get_databases_status():
    """Получение статуса всех баз данных"""
    if state.db_manager is None:
        raise HTTPException(status_code=503, detail="Менеджер БД не инициализирован")
    
    databases = state.db_manager.list_databases()
    detailed = []
    
    for db_info in databases:
        db = state.db_manager.get_db_by_prefix(db_info['prefix'])
        if db:
            size_info = db.get_db_size_info()
            stats = db.get_statistics()
            detailed.append({
                **db_info,
                **size_info,
                **stats
            })
    
    return {"databases": detailed, "total": len(databases)}


# =============================================================================
# Обработчики ошибок
# =============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Глобальный обработчик исключений"""
    logger.error(f"Критическая ошибка: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Внутренняя ошибка сервера", "path": request.url.path}
    )


# =============================================================================
# Запуск
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    
    logger.info("🚀 Запуск API сервера в режиме разработчика")
    
    uvicorn.run(
        "api.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level=settings.log_level
    )
