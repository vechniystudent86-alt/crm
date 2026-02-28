"""
Роутер для управления заявками с сайта (Leads)
"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional

from app.database import get_db
from app.models import Lead, Client
from app.schemas import (
    LeadCreate,
    LeadUpdate,
    LeadResponse,
)
from app.auth import get_current_user
from app.models import User


router = APIRouter()


@router.get("/", response_model=List[LeadResponse], summary="Список заявок")
async def get_leads(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status_filter: Optional[str] = Query(None, alias="status"),
    source: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Получить список заявок с фильтрацией"""
    query = select(Lead)

    if status_filter:
        query = query.where(Lead.status == status_filter)

    if source:
        query = query.where(Lead.source == source)

    query = query.order_by(Lead.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    leads = result.scalars().all()

    return leads


@router.get("/{lead_id}", response_model=LeadResponse, summary="Заявка по ID")
async def get_lead(
    lead_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Получить информацию о заявке"""
    result = await db.execute(
        select(Lead).where(Lead.id == lead_id)
    )
    lead = result.scalar_one_or_none()

    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Заявка не найдена"
        )

    return lead


@router.post("/", response_model=LeadResponse, status_code=status.HTTP_201_CREATED, summary="Создать заявку (с сайта)")
async def create_lead(
    lead_data: LeadCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Создать новую заявку с сайта.
    Этот endpoint НЕ требует аутентификации!
    """
    # Проверка: не существует ли уже клиент с таким телефоном
    client_result = await db.execute(
        select(Client).where(Client.phone == lead_data.phone)
    )
    existing_client = client_result.scalar_one_or_none()

    client_id = None
    if not existing_client:
        # Создаём нового клиента автоматически
        phone_clean = lead_data.phone.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
        client = Client(
            first_name=lead_data.name,
            last_name="",
            phone=lead_data.phone,
            source=lead_data.source or "website",
            is_active=True,
        )
        db.add(client)
        await db.flush()  # Чтобы получить ID
        client_id = client.id
    else:
        client_id = existing_client.id

    # Создаём заявку
    lead = Lead(
        name=lead_data.name,
        phone=lead_data.phone,
        program=lead_data.program or "classic",
        message=lead_data.message,
        source=lead_data.source or "website",
        status="new",
        client_id=client_id,
    )

    db.add(lead)
    await db.commit()
    await db.refresh(lead)

    # Отправляем уведомление в Telegram (если настроено)
    # Это можно сделать через фоновую задачу
    from app.services.notifications import notification_service
    try:
        await notification_service.create_notification(
            client_id=client_id,
            title="🔔 Новая заявка с сайта!",
            message=f"{lead_data.name} оставил(а) заявку на пробную тренировку.\nТелефон: {lead_data.phone}",
            notification_type="info",
            db=db,
        )
    except Exception:
        pass  # Игнорируем ошибки уведомлений

    return lead


@router.patch("/{lead_id}", response_model=LeadResponse, summary="Обновить заявку")
async def update_lead(
    lead_id: int,
    lead_data: LeadUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Обновить заявку (только для администратора)"""
    if current_user.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Требуется роль администратора"
        )

    result = await db.execute(
        select(Lead).where(Lead.id == lead_id)
    )
    lead = result.scalar_one_or_none()

    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Заявка не найдена"
        )

    # Обновление полей
    update_data = lead_data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(lead, field, value)

    await db.commit()
    await db.refresh(lead)

    return lead


@router.delete("/{lead_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Удалить заявку")
async def delete_lead(
    lead_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Удалить заявку (только для администратора)"""
    if current_user.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Требуется роль администратора"
        )

    result = await db.execute(
        select(Lead).where(Lead.id == lead_id)
    )
    lead = result.scalar_one_or_none()

    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Заявка не найдена"
        )

    await db.delete(lead)
    await db.commit()

    return None


@router.get("/stats/summary", summary="Статистика заявок")
async def get_lead_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Получить сводную статистику по заявкам"""
    from sqlalchemy import func

    # Общее количество
    total_query = select(func.count(Lead.id))
    total_result = await db.execute(total_query)
    total_count = total_result.scalar() or 0

    # По статусам
    status_query = select(
        Lead.status,
        func.count(Lead.id).label("count")
    ).group_by(Lead.status)
    status_result = await db.execute(status_query)
    by_status = {row.status: row.count for row in status_result.all()}

    # По источникам
    source_query = select(
        Lead.source,
        func.count(Lead.id).label("count")
    ).group_by(Lead.source)
    source_result = await db.execute(source_query)
    by_source = {row.source or "unknown": row.count for row in source_result.all()}

    # Новые за сегодня
    from datetime import datetime, timedelta
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    new_today_query = select(func.count(Lead.id)).where(
        Lead.created_at >= today_start
    )
    new_today_result = await db.execute(new_today_query)
    new_today = new_today_result.scalar() or 0

    return {
        "total_count": total_count,
        "by_status": by_status,
        "by_source": by_source,
        "new_today": new_today,
    }
