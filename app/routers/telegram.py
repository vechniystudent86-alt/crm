"""
Роутер для Telegram webhook
Интеграция с Telegram-ботом для приёма заявок
"""
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
import logging

from app.database import get_db
from app.config import settings
from app.models import Client
from app.schemas import TelegramWebhook


router = APIRouter()
logger = logging.getLogger(__name__)


async def verify_telegram_secret(
    x_telegram_secret: Optional[str] = Header(None, alias="X-Telegram-Bot-Api-Secret-Token")
):
    """Проверка секрета Telegram webhook"""
    if settings.TELEGRAM_WEBHOOK_SECRET:
        if x_telegram_secret != settings.TELEGRAM_WEBHOOK_SECRET:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Telegram secret"
            )
    return True


@router.post("/webhook", summary="Telegram Webhook")
async def telegram_webhook(
    webhook_data: dict,
    db: AsyncSession = Depends(get_db),
    secret_valid: bool = Depends(verify_telegram_secret)
):
    """
    Обработка входящих обновлений от Telegram Bot.
    
    Поддерживает:
    - /start - приветственное сообщение
    - /newclient - заявка на нового клиента
    - Текстовые сообщения - обработка контактов
    """
    logger.info(f"Telegram webhook received: {webhook_data}")
    
    # Обработка callback query (кнопки)
    if "callback_query" in webhook_data:
        return await handle_callback_query(webhook_data["callback_query"], db)
    
    # Обработка сообщений
    if "message" in webhook_data:
        return await handle_message(webhook_data["message"], db)
    
    return {"ok": True}


async def handle_message(message: dict, db: AsyncSession):
    """Обработка входящих сообщений"""
    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "")
    
    # Команда /start
    if text == "/start":
        welcome_text = (
            "👋 Привет! Это бот Zumba у залива.\n\n"
            "📝 Чтобы записаться на занятие, отправьте:\n"
            "• Ваше имя\n"
            "• Номер телефона\n\n"
            "Или нажмите кнопку ниже!"
        )
        return {
            "ok": True,
            "response": {
                "method": "sendMessage",
                "chat_id": chat_id,
                "text": welcome_text
            }
        }
    
    # Команда /newclient
    if text == "/newclient":
        return {
            "ok": True,
            "response": {
                "method": "sendMessage",
                "chat_id": chat_id,
                "text": "📝 Пожалуйста, отправьте ваш номер телефона"
            }
        }
    
    # Обработка контакта
    if "contact" in message:
        phone = message["contact"]["phone_number"]
        first_name = message["contact"]["first_name"]
        
        # Проверка существования клиента
        result = await db.execute(
            select(Client).where(Client.phone == phone)
        )
        client = result.scalar_one_or_none()
        
        if client:
            response_text = f"✅ Клиент найден: {client.full_name}"
        else:
            # Создание нового клиента
            client = Client(
                first_name=first_name,
                phone=phone,
                source="telegram",
                telegram=str(chat_id)
            )
            db.add(client)
            await db.commit()
            
            response_text = f"✅ Клиент добавлен: {first_name}\n📞 {phone}"
        
        return {
            "ok": True,
            "response": {
                "method": "sendMessage",
                "chat_id": chat_id,
                "text": response_text
            }
        }
    
    # Обработка текста (имя + телефон)
    if text:
        # Простая эвристика: если есть цифры, считаем это телефоном
        if any(char.isdigit() for char in text):
            # Извлечение телефона из текста
            import re
            phones = re.findall(r'\+?\d[\d\s-]{8,}\d', text)
            
            if phones:
                phone = phones[0].replace(" ", "").replace("-", "")
                name = text.replace(phones[0], "").strip()
                
                # Проверка существования
                result = await db.execute(
                    select(Client).where(Client.phone == phone)
                )
                client = result.scalar_one_or_none()
                
                if client:
                    response_text = f"✅ Клиент найден: {client.full_name}"
                else:
                    client = Client(
                        first_name=name or "Новый",
                        phone=phone,
                        source="telegram",
                        telegram=str(chat_id),
                        comment=f"Заявка из бота: {text}"
                    )
                    db.add(client)
                    await db.commit()
                    
                    response_text = f"✅ Заявка создана!\n👤 {name}\n📞 {phone}"
                
                return {
                    "ok": True,
                    "response": {
                        "method": "sendMessage",
                        "chat_id": chat_id,
                        "text": response_text
                    }
                }
    
    return {"ok": True}


async def handle_callback_query(callback_query: dict, db: AsyncSession):
    """Обработка нажатий на кнопки"""
    chat_id = callback_query.get("message", {}).get("chat", {}).get("id")
    data = callback_query.get("data", "")
    
    if data == "new_client":
        return {
            "ok": True,
            "response": {
                "method": "sendMessage",
                "chat_id": chat_id,
                "text": "📝 Отправьте ваш номер телефона или используйте кнопку 'Поделиться контактом'"
            }
        }
    
    return {"ok": True}


@router.get("/set-webhook", summary="Установить Telegram Webhook")
async def set_telegram_webhook():
    """
    Установка webhook для Telegram бота.
    
    Вызовите этот endpoint после деплоя для настройки webhook.
    URL webhook: https://your-domain.com/api/telegram/webhook
    """
    import httpx
    
    if not settings.TELEGRAM_BOT_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="TELEGRAM_BOT_TOKEN не настроен"
        )
    
    webhook_url = "https://your-domain.com/api/telegram/webhook"  # Заменить на актуальный домен
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/setWebhook",
            json={
                "url": webhook_url,
                "secret_token": settings.TELEGRAM_WEBHOOK_SECRET
            }
        )
    
    if response.status_code == 200:
        return {"ok": True, "message": f"Webhook установлен: {webhook_url}"}
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ошибка установки webhook: {response.text}"
        )
