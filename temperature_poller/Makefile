# Temperature Poller API Makefile
# Использование: make <command>

.PHONY: help install start test docs clean

# Переменные
PYTHON := python
VENV := venv
API_PORT := 8000
API_HOST := 0.0.0.0

# =============================================================================
# Help
# =============================================================================

help:
	@echo "Temperature Poller API - Makefile Commands"
	@echo "==========================================="
	@echo ""
	@echo "Установка и настройка:"
	@echo "  make install    - Установка зависимостей"
	@echo "  make venv       - Создание виртуального окружения"
	@echo ""
	@echo "Конфигурация:"
	@echo "  make config     - Показать текущую конфигурацию"
	@echo ""
	@echo "Запуск:"
	@echo "  make start      - Запуск API сервера"
	@echo "  make dev        - Запуск в режиме разработки (с автоперезагрузкой)"
	@echo ""
	@echo "Тестирование:"
	@echo "  make test       - Запуск тестов API"
	@echo "  make health     - Проверка здоровья сервиса"
	@echo ""
	@echo "Документация:"
	@echo "  make docs       - Открытие Swagger UI"
	@echo ""
	@echo "Очистка:"
	@echo "  make clean      - Очистка временных файлов"
	@echo "  make clean-all  - Очистка всех генерируемых файлов"

# =============================================================================
# Configuration
# =============================================================================

config:
	@echo "🔧 Проверка конфигурации..."
	$(PYTHON) app_config.py

# =============================================================================
# Installation
# =============================================================================

venv:
	@echo "📦 Создание виртуального окружения..."
	$(PYTHON) -m venv $(VENV)
	@echo "✅ Виртуальное окружение создано"

install:
	@echo "📦 Установка зависимостей..."
	pip install -r api/requirements.txt
	@echo "✅ Зависимости установлены"

install-dev: install
	@echo "📦 Установка зависимостей для разработки..."
	pip install black flake8 pytest mypy

# =============================================================================
# Run
# =============================================================================

start:
	@echo "🚀 Запуск API сервера..."
	$(PYTHON) run_api.py

dev:
	@echo "🚀 Запуск API сервера в режиме разработки..."
	uvicorn api.main:app --host $(API_HOST) --port $(API_PORT) --reload

# =============================================================================
# Test
# =============================================================================

test:
	@echo "🧪 Запуск тестов API..."
	$(PYTHON) test_api.py

health:
	@echo "🏥 Проверка здоровья сервиса..."
	curl -s http://localhost:$(API_PORT)/health | python -m json.tool

# =============================================================================
# Documentation
# =============================================================================

docs:
	@echo "📚 Открытие Swagger UI..."
	@echo "Откройте: http://localhost:$(API_PORT)/docs"
	@echo "Или ReDoc: http://localhost:$(API_PORT)/redoc"

# =============================================================================
# Cleanup
# =============================================================================

clean:
	@echo "🧹 Очистка временных файлов..."
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type f -name ".DS_Store" -delete
	@echo "✅ Очистка завершена"

clean-all: clean
	@echo "🧹 Полная очистка (включая БД и логи)..."
	rm -rf venv/
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .mypy_cache/
	rm -rf databases/*.db
	rm -rf databases/*.db-*
	rm -rf *.log
	rm -rf emergency_checkpoint.json
	@echo "✅ Полная очистка завершена"
