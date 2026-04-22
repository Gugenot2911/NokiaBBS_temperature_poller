from datetime import datetime
from typing import Optional, Dict, Any, List

# Pydantic fallback для окружений без pydantic
try:
    from pydantic import BaseModel, Field, TypeAdapter
    from pydantic import ConfigDict
except ImportError:
    # Минимальная эмуляция Pydantic для базовой работы
    class BaseModel:
        @classmethod
        def model_dump(cls):
            return {}
        
        @classmethod
        def model_validate(cls, data):
            return cls()
    
    def Field(default=None, **kwargs):
        return default
    
    TypeAdapter = None  # type: ignore
    ConfigDict = None  # type: ignore


class HostInfo(BaseModel):
    """Модель хоста из API (внутреннее использование)"""
    master_site: str
    module_name: str
    ip_4g: str
    ip_3g: Optional[str] = None  # Опционально, для обратной совместимости с API


class TemperatureResponse(BaseModel):
    """
    Модель ответа после опроса температуры.
    
    Содержит данные только об IP 4G (ip_3g исключён из модели).
    """
    model_config = ConfigDict(json_encoders={
        datetime: lambda v: v.isoformat()
    })
    
    hostname: str = Field(..., description="Имя хоста (master_site)")
    ip: str = Field(..., description="IP адрес для опроса (только 4G)")
    temperature: Optional[Dict[str, Any]] = Field(default=None, description="Сырые данные температуры из CLI")
    timestamp: Optional[datetime] = Field(default=None, description="Время опроса")
    save_status: Optional[str] = Field(default=None, description="Статус сохранения в БД")
    vendor: str = Field(default="nokia", description="Вендор оборудования")
    availability: bool = Field(default=None, description="Доступность хоста (ping)")
    error_message: Optional[str] = Field(default=None, description="Сообщение об ошибке")


class PollingResult(BaseModel):
    """Модель результата опроса батча"""
    success_count: int = 0
    error_count: int = 0
    skipped_count: int = 0
    results: List[TemperatureResponse] = Field(default_factory=list)