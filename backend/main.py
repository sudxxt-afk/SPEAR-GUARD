from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
from datetime import datetime
from sqlalchemy import text

from database import engine, Base
from redis_client import redis_client
from elasticsearch_client import es_client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan event handler for startup and shutdown events
    """
    # Startup
    logger.info("Starting SPEAR-GUARD Backend...")

    # Initialize database tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("✓ Database tables created")

    # Test Redis connection
    try:
        await redis_client.ping()
        logger.info("✓ Redis connection successful")
    except Exception as e:
        logger.error(f"✗ Redis connection failed: {e}")

    # Test Elasticsearch connection
    try:
        await es_client.ping()
        logger.info("✓ Elasticsearch connection successful")
    except Exception as e:
        logger.error(f"✗ Elasticsearch connection failed: {e}")

    # Start WebSocket heartbeat task
    import asyncio
    from websocket_manager import heartbeat_task
    heartbeat_task_handle = asyncio.create_task(heartbeat_task())
    logger.info("✓ WebSocket heartbeat task started")

    logger.info("SPEAR-GUARD Backend is ready!")

    yield

    # Shutdown
    logger.info("Shutting down SPEAR-GUARD Backend...")
    
    # Cancel heartbeat task
    heartbeat_task_handle.cancel()
    try:
        await heartbeat_task_handle
    except asyncio.CancelledError:
        pass
    
    await redis_client.close()
    await es_client.close()
    logger.info("✓ Connections closed")


# Create FastAPI application
app = FastAPI(
    title="🛡️ SPEAR-GUARD API",
    description="""
    **Интеллектуальная антифишинговая платформа** для государственного сектора

    ## 🎯 Основные возможности

    ### 📋 Реестр доверенных отправителей
    - Управление доверенными email адресами
    - 4 уровня доверия (MAX → LOW)
    - Автоматическое одобрение для Security Officers
    - Статистика и аналитика

    ### 🔍 Проверка входящих писем
    - ⚡ **Fast Track** для доверенных отправителей (~50ms)
    - 🔬 **Full Check** для неизвестных отправителей (~200ms)
    - Валидация SPF/DKIM/IP
    - Поведенческий анализ
    - Кэширование результатов (Redis)

    ### 📊 Анализ email заголовков
    - 🔐 SPF (Sender Policy Framework) проверка
    - 🔑 DKIM (DomainKeys Identified Mail) верификация
    - 📋 DMARC (Domain-based Message Authentication) политики
    - 🎭 Обнаружение подмены Display Name
    - 🛤️ Анализ маршрутизации писем
    - ⚠️ Детектирование аномалий заголовков

    ### 🤖 Автоматизация
    - Автоматическое заполнение реестра из email истории
    - Интеграция с Active Directory
    - Интеграция с ЕГРЮЛ
    - Celery задачи для фоновой обработки

    ## 🔐 Аутентификация

    Используйте заголовок `Authorization: Bearer {token}` для доступа к API.

    **Тестовый токен:** `test-token` (только для разработки)

    ## 📚 Документация

    - **Swagger UI:** `/docs` (эта страница)
    - **ReDoc:** `/redoc`
    - **Health Check:** `/health`

    ---

    🚀 **Version 1.0.0** | 🏢 Разработано для государственного сектора РФ
    """,
    version="1.0.0",
    lifespan=lifespan,
    contact={
        "name": "SPEAR-GUARD Support",
        "email": "support@spear-guard.gov.ru"
    },
    license_info={
        "name": "Proprietary"
    }
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React dev server (legacy)
        "http://localhost:5173",  # Vite dev server (default)
        "http://localhost:8000",  # Backend
        "https://spear-guard.gov.ru",  # Production
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc),
            "timestamp": datetime.utcnow().isoformat()
        }
    )


# Health check endpoint
@app.get("/health", tags=["💊 Система"], summary="🏥 Проверка здоровья системы")
async def health_check():
    """
    **Health check** для мониторинга состояния сервисов

    Проверяет доступность:
    - 🗄️ PostgreSQL база данных
    - 🔴 Redis кэш
    - 🔍 Elasticsearch (опционально)
    """
    health_status = {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {}
    }

    # Check Redis
    try:
        await redis_client.ping()
        health_status["services"]["redis"] = "healthy"
    except Exception as e:
        health_status["services"]["redis"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"

    # Check Elasticsearch
    try:
        await es_client.ping()
        health_status["services"]["elasticsearch"] = "healthy"
    except Exception as e:
        health_status["services"]["elasticsearch"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"

    # Check Database
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        health_status["services"]["database"] = "healthy"
    except Exception as e:
        health_status["services"]["database"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"

    return health_status


# Root endpoint
@app.get("/", tags=["💊 Система"], summary="🏠 Главная страница API")
async def root():
    """
    **Главная страница API** с информацией о системе

    Возвращает базовую информацию и ссылки на документацию.
    """
    return {
        "name": "SPEAR-GUARD API",
        "version": "1.0.0",
        "description": "Intelligent anti-phishing platform for government sector",
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/health"
    }


# Import API routers
from api.registry import router as registry_router
from api.tasks import router as tasks_router
from api.check import router as check_router
from api.analyze import router as analyze_router
from api.auth import router as auth_router
from api.alerts_v1 import router as alerts_router
from api.analysis_read import router as analysis_read_router
from api.websocket import router as websocket_router
from api.dashboard_analytics import router as dashboard_analytics_router
from api.system import router as system_router
from api.mail_accounts import router as mail_accounts_router
from api.organizations import router as organizations_router
from api.users import router as users_router
from api.employees import router as employees_router
from api.attachments import router as attachments_router

# Include API routers
app.include_router(auth_router)
app.include_router(alerts_router)
app.include_router(analysis_read_router)
app.include_router(registry_router)
app.include_router(tasks_router)
app.include_router(check_router)
app.include_router(analyze_router)
app.include_router(websocket_router)
app.include_router(dashboard_analytics_router, prefix="/api/v1/dashboard", tags=["dashboard-analytics"])
app.include_router(system_router)
app.include_router(mail_accounts_router)
app.include_router(organizations_router)
app.include_router(users_router)
app.include_router(employees_router, prefix="/api/v1/employees", tags=["employees"])
app.include_router(attachments_router, prefix="/api/v1/analyze", tags=["🔬 Анализ вложений и URL"])


# API v1 endpoints placeholder
@app.get("/api/v1/status", tags=["💊 Система"], summary="📊 Статус API v1")
async def api_status():
    """
    **Статус API версии 1**

    Проверка работоспособности API эндпоинтов.
    """
    return {
        "api_version": "1.0.0",
        "status": "operational",
        "timestamp": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
