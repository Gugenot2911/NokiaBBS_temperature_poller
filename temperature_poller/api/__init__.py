"""
Temperature Poller API Package

REST API микросервис для управления опросом температурных данных.
"""

from api.main import app, state
from api.config import settings

__version__ = "1.0.0"
__all__ = ["app", "state", "settings"]
