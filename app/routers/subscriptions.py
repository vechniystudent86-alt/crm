"""
Роутер управления абонементами
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from datetime import datetime

from app.database import get_db
from app.auth import get_current_user
from app.models import User, Subscription, SubscriptionStatus, Client
from app.schemas import SubscriptionCreate, SubscriptionUpdate, SubscriptionResponse


router = APIRouter()


@router.get("/", response_model=List[SubscriptionResponse], summary="Список абонементов")
async def get_all_subscriptions(
    client_id: Optional[int] = Query(None, description="Фильтр по клиенту"),
    status_filter: Optional[str] = Query(None, description="Фильтр по статусу"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Получение списка абонементов с фильтрами.
    
    - **client_id**: Фильтр по ID клиента
    - **status**: Фильтр по статусу (active, frozen, expired, archived)
    - **skip**: Пропустить N записей
    - **limit**: Количество записей
    """
    query = select(Subscription)
    
    if client_id:
        query = query.where(Subscription.client_id == client_id)
    
    if status_filter:
        try:
            status_enum = SubscriptionStatus(status_filter)
            query = query.where(Subscription.status == status_enum)
        except ValueError:
            pass
    
    query = query.order_by(Subscription.created_at.desc()).offset(skip).limit(limit)
    
    result = await db.execute(query)
    subscriptions = result.scalars().all()
    
    return subscriptions


@router.get("/{subscription_id}", response_model=SubscriptionResponse, summary="Абонемент по ID")
async def get_subscription(
    subscription_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получение информации об абонементе по ID"""
    result = await db.execute(
        select(Subscription).where(Subscription.id == subscription_id)
    )
    subscription = result.scalar_one_or_none()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Абонемент не найден"
        )
    
    return subscription


@router.post("/", response_model=SubscriptionResponse, status_code=status.HTTP_201_CREATED, summary="Создать абонемент")
async def create_subscription(
    subscription_data: SubscriptionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Создание нового абонемента для клиента.
    
    - **client_id**: ID клиента
    - **name**: Название абонемента (например, "4 занятия")
    - **visits_total**: Общее количество занятий
    - **visits_left**: Осталось занятий (по умолчанию = visits_total)
    - **price**: Цена
    - **start_date**: Дата начала
    - **end_date**: Дата окончания
    - **comment**: Комментарий
    """
    # Проверка существования клиента
    client_result = await db.execute(
        select(Client).where(Client.id == subscription_data.client_id)
    )
    client = client_result.scalar_one_or_none()
    
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Клиент не найден"
        )
    
    # Создание абонемента
    subscription = Subscription(
        **subscription_data.model_dump(),
        visits_left=subscription_data.visits_total if subscription_data.visits_left is None else subscription_data.visits_left,
        status=SubscriptionStatus.ACTIVE
    )
    
    db.add(subscription)
    await db.commit()
    await db.refresh(subscription)
    
    return subscription


@router.put("/{subscription_id}", response_model=SubscriptionResponse, summary="Обновить абонемент")
async def update_subscription(
    subscription_id: int,
    subscription_update: SubscriptionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Обновление информации об абонементе"""
    result = await db.execute(
        select(Subscription).where(Subscription.id == subscription_id)
    )
    subscription = result.scalar_one_or_none()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Абонемент не найден"
        )
    
    # Обновление полей
    update_data = subscription_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if isinstance(value, str) and field == "status":
            value = SubscriptionStatus(value)
        setattr(subscription, field, value)
    
    await db.commit()
    await db.refresh(subscription)
    
    return subscription


@router.post("/{subscription_id}/freeze", response_model=SubscriptionResponse, summary="Заморозить абонемент")
async def freeze_subscription(
    subscription_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Заморозка абонемента"""
    result = await db.execute(
        select(Subscription).where(Subscription.id == subscription_id)
    )
    subscription = result.scalar_one_or_none()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Абонемент не найден"
        )
    
    if subscription.status != SubscriptionStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Можно заморозить только активный абонемент"
        )
    
    subscription.status = SubscriptionStatus.FROZEN
    subscription.frozen_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(subscription)
    
    return subscription


@router.post("/{subscription_id}/unfreeze", response_model=SubscriptionResponse, summary="Разморозить абонемент")
async def unfreeze_subscription(
    subscription_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Разморозка абонемента"""
    result = await db.execute(
        select(Subscription).where(Subscription.id == subscription_id)
    )
    subscription = result.scalar_one_or_none()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Абонемент не найден"
        )
    
    if subscription.status != SubscriptionStatus.FROZEN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Можно разморозить только замороженный абонемент"
        )
    
    subscription.status = SubscriptionStatus.ACTIVE
    subscription.unfrozen_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(subscription)
    
    return subscription


@router.delete("/{subscription_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Архивировать абонемент")
async def delete_subscription(
    subscription_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Архивирование абонемента (мягкое удаление).
    
    Устанавливает статус в ARCHIVED.
    """
    result = await db.execute(
        select(Subscription).where(Subscription.id == subscription_id)
    )
    subscription = result.scalar_one_or_none()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Абонемент не найден"
        )
    
    subscription.status = SubscriptionStatus.ARCHIVED
    await db.commit()
    
    return None
