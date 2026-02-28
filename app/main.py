"""
Zumba CRM - Асинхронное веб-приложение на FastAPI
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from app.config import settings
from app.database import init_db
from app.routers import (
    auth,
    clients,
    subscriptions,
    visits,
    telegram,
    users,
    payments,
    expenses,
    schedules,
    feedback,
    analytics,
    leads,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения"""
    # При запуске
    await init_db()
    
    # Создание администратора по умолчанию
    from app.auth import create_user_with_role
    try:
        await create_user_with_role(
            username=settings.ADMIN_USERNAME,
            password=settings.ADMIN_PASSWORD,
            role="admin"
        )
    except Exception:
        pass  # Пользователь уже существует
    
    # Запуск фоновых задач
    from app.services.notifications import (
        process_scheduled_notifications,
        process_class_reminders,
        process_expiring_subscriptions,
    )
    import asyncio
    
    async def background_tasks():
        while True:
            await asyncio.sleep(300)  # Каждые 5 минут
            try:
                await process_scheduled_notifications()
                await process_class_reminders()
            except Exception as e:
                print(f"Ошибка фоновой задачи: {e}")
    
    # Запускаем фоновую задачу
    background_task = asyncio.create_task(background_tasks())
    
    yield
    
    # При остановке
    background_task.cancel()
    try:
        await background_task
    except asyncio.CancelledError:
        pass


# Создание приложения FastAPI
app = FastAPI(
    title=settings.APP_NAME,
    description="CRM-система для фитнес-студии Zumba",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS middleware (для фронтенда на другом домене)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В production заменить на конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Монтирование роутеров
app.include_router(auth.router, prefix="/api/auth", tags=["Аутентификация"])
app.include_router(users.router, prefix="/api/users", tags=["Пользователи"])
app.include_router(clients.router, prefix="/api/clients", tags=["Клиенты"])
app.include_router(subscriptions.router, prefix="/api/subscriptions", tags=["Абонементы"])
app.include_router(visits.router, prefix="/api/visits", tags=["Посещения"])
app.include_router(telegram.router, prefix="/api/telegram", tags=["Telegram"])

# Новые роутеры v2.0
app.include_router(payments.router, prefix="/api/payments", tags=["Финансы: Платежи"])
app.include_router(expenses.router, prefix="/api/expenses", tags=["Финансы: Расходы"])
app.include_router(schedules.router, prefix="/api/schedules", tags=["Расписание"])
app.include_router(feedback.router, prefix="/api/feedback", tags=["Обратная связь"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["Аналитика"])
app.include_router(leads.router, prefix="/api/leads", tags=["Заявки с сайта"])


# Раздача статики и фронтенда
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")


@app.get("/")
async def root():
    """Главная страница - редирект на дашборд"""
    index_path = os.path.join(frontend_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Zumba CRM API v2.0", "docs": "/docs"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
    )
