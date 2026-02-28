"""
Сервис уведомлений для CRM
Отправка уведомлений через Telegram бота
"""
from datetime import datetime, timedelta
from typing import List, Optional
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from aiogram import Bot
from aiogram.exceptions import TelegramUnauthorizedError

from app.config import settings
from app.models import Notification, Client, Schedule, Enrollment, Subscription, SubscriptionStatus
from app.database import async_session_maker

logger = logging.getLogger(__name__)


class NotificationService:
    """Сервис для отправки уведомлений клиентам"""

    def __init__(self, bot: Optional[Bot] = None):
        self.bot = bot

    async def send_telegram_message(self, telegram_id: str, message: str) -> bool:
        """Отправить сообщение в Telegram"""
        if not self.bot:
            logger.warning("Telegram bot не инициализирован")
            return False

        try:
            await self.bot.send_message(
                chat_id=telegram_id,
                text=message,
                parse_mode="HTML"
            )
            return True
        except TelegramUnauthorizedError:
            logger.error(f"Бот не авторизован для пользователя {telegram_id}")
            return False
        except Exception as e:
            logger.error(f"Ошибка отправки Telegram: {e}")
            return False

    async def create_notification(
        self,
        client_id: int,
        title: str,
        message: str,
        notification_type: str = "info",
        db: Optional[AsyncSession] = None,
    ) -> Notification:
        """Создать уведомление в базе"""
        close_db = False
        if db is None:
            db = async_session_maker()
            close_db = True

        try:
            notification = Notification(
                client_id=client_id,
                title=title,
                message=message,
                notification_type=notification_type,
                is_sent=False,
            )
            db.add(notification)
            await db.commit()
            await db.refresh(notification)
            return notification
        finally:
            if close_db:
                await db.close()

    async def send_notification(
        self,
        notification: Notification,
        db: AsyncSession,
    ) -> bool:
        """Отправить уведомление клиенту"""
        # Получаем клиента
        client_result = await db.execute(
            select(Client).where(Client.id == notification.client_id)
        )
        client = client_result.scalar_one_or_none()

        if not client:
            logger.error(f"Клиент {notification.client_id} не найден")
            return False

        if not client.telegram:
            logger.info(f"У клиента {client.full_name} нет Telegram")
            notification.is_sent = True
            notification.sent_at = datetime.utcnow()
            await db.commit()
            return False

        # Отправляем сообщение
        full_message = f"<b>{notification.title}</b>\n\n{notification.message}"
        success = await self.send_telegram_message(client.telegram, full_message)

        if success:
            notification.is_sent = True
            notification.sent_at = datetime.utcnow()
            await db.commit()
            logger.info(f"Уведомление отправлено клиенту {client.full_name}")
        else:
            logger.warning(f"Не удалось отправить уведомление клиенту {client.full_name}")

        return success

    async def send_reminder_for_class(
        self,
        enrollment: Enrollment,
        db: AsyncSession,
    ):
        """Отправить напоминание о занятии"""
        schedule_result = await db.execute(
            select(Schedule).where(Schedule.id == enrollment.schedule_id)
        )
        schedule = schedule_result.scalar_one_or_none()

        if not schedule:
            return

        client_result = await db.execute(
            select(Client).where(Client.id == enrollment.client_id)
        )
        client = client_result.scalar_one_or_none()

        if not client:
            return

        # Формируем сообщение
        hours_until_class = (schedule.start_time - datetime.utcnow()).total_seconds() / 3600

        message = (
            f"🔔 <b>Напоминание о занятии</b>\n\n"
            f"Занятие: {schedule.title}\n"
            f"Время: {schedule.start_time.strftime('%d.%m.%Y в %H:%M')}\n"
            f"Зал: {schedule.hall}\n"
            f"Тренер: {schedule.trainer.full_name if schedule.trainer else 'Тренер уточняется'}\n\n"
            f"До начала осталось примерно {int(hours_until_class)} ч."
        )

        await self.create_notification(
            client_id=client.id,
            title="Напоминание о занятии",
            message=message,
            notification_type="reminder",
            db=db,
        )

    async def send_subscription_expiring_soon(
        self,
        subscription: Subscription,
        db: AsyncSession,
    ):
        """Отправить уведомление об окончании абонемента"""
        client_result = await db.execute(
            select(Client).where(Client.id == subscription.client_id)
        )
        client = client_result.scalar_one_or_none()

        if not client:
            return

        days_left = (subscription.end_date - datetime.utcnow()).days if subscription.end_date else 0

        message = (
            f"⚠️ <b>Абонемент заканчивается</b>\n\n"
            f"Абонемент: {subscription.name}\n"
            f"Осталось занятий: {subscription.visits_left}\n"
            f"Действует до: {subscription.end_date.strftime('%d.%m.%Y') if subscription.end_date else 'Не указано'}\n\n"
            f"Осталось дней: {days_left}\n\n"
            f"Пора продлить абонемент! 🏋️‍♀️"
        )

        await self.create_notification(
            client_id=client.id,
            title="Абонемент заканчивается",
            message=message,
            notification_type="reminder",
            db=db,
        )

    async def send_birthday_greeting(
        self,
        client: Client,
        db: AsyncSession,
    ):
        """Отправить поздравление с днём рождения"""
        # Пока нет поля birthday в модели Client, заглушка
        logger.info(f"День рождения у клиента {client.full_name}")


# Глобальный экземпляр сервиса
notification_service = NotificationService()


async def get_notification_service() -> NotificationService:
    """Получить сервис уведомлений"""
    return notification_service


async def process_scheduled_notifications():
    """
    Фоновая задача для обработки запланированных уведомлений.
    Запускается каждые 5 минут.
    """
    async with async_session_maker() as db:
        # Находим несent уведомления
        result = await db.execute(
            select(Notification).where(Notification.is_sent == False)
        )
        notifications = result.scalars().all()

        for notification in notifications:
            await notification_service.send_notification(notification, db)


async def process_class_reminders():
    """
    Фоновая задача для отправки напоминаний о занятиях.
    Запускается каждые 30 минут.
    Отправляет напоминания за 2-4 часа до занятия.
    """
    now = datetime.utcnow()
    reminder_window_start = now + timedelta(hours=2)
    reminder_window_end = now + timedelta(hours=4)

    async with async_session_maker() as db:
        # Находим занятия в окне напоминаний
        result = await db.execute(
            select(Enrollment)
            .join(Schedule, Enrollment.schedule_id == Schedule.id)
            .where(
                Schedule.start_time >= reminder_window_start,
                Schedule.start_time <= reminder_window_end,
                Enrollment.status == "enrolled",
            )
        )
        enrollments = result.scalars().all()

        for enrollment in enrollments:
            await notification_service.send_reminder_for_class(enrollment, db)


async def process_expiring_subscriptions():
    """
    Фоновая задача для уведомлений об истекающих абонементах.
    Запускается раз в день.
    """
    now = datetime.utcnow()
    expiry_threshold = now + timedelta(days=7)

    async with async_session_maker() as db:
        result = await db.execute(
            select(Subscription).where(
                Subscription.status == SubscriptionStatus.ACTIVE,
                Subscription.end_date <= expiry_threshold,
                Subscription.end_date >= now,
            )
        )
        subscriptions = result.scalars().all()

        for subscription in subscriptions:
            await notification_service.send_subscription_expiring_soon(subscription, db)
