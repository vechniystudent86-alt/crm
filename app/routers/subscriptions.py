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
from app.services.subscription_templates import get_all_templates, get_template_by_name

router = APIRouter()


# ============================================
# Шаблоны абонементов (должны быть перед {subscription_id})
# ============================================

@router.get("/templates", response_model=List[dict], summary="Шаблоны абонементов")
async def get_subscription_templates():
    """
    Получение списка стандартных шаблонов абонементов.

    Возвращает предустановленные тарифы:
    - Пробная тренировка (500₽)
    - Разовое посещение (750₽)
    - 4 занятия (2800₽)
    - 6 занятий (3900₽)
    - 8 занятий (4800₽)
    """
    templates = get_all_templates()

    # Добавляем стоимость за занятие
    for template in templates:
        template["price_per_visit"] = round(template["price"] / template["visits_total"], 2)

    return templates


@router.get("/templates/{template_name}", response_model=dict, summary="Шаблон по названию")
async def get_subscription_template(template_name: str):
    """
    Получение шаблона по названию.

    Примеры названий:
    - "Пробная тренировка"
    - "Разовое посещение"
    - "4 занятия"
    - "6 занятий"
    - "8 занятий"
    """
    import urllib.parse
    decoded_name = urllib.parse.unquote(template_name)

    template = get_template_by_name(decoded_name)

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Шаблон '{decoded_name}' не найден"
        )

    result = template.copy()
    result["price_per_visit"] = round(result["price"] / result["visits_total"], 2)

    return result


@router.post("/from-template", response_model=SubscriptionResponse, status_code=status.HTTP_201_CREATED, summary="Создать абонемент из шаблона")
async def create_subscription_from_template(
    template_name: str = Query(..., description="Название шаблона"),
    client_id: int = Query(..., description="ID клиента"),
    comment: Optional[str] = Query(None, description="Комментарий к абонементу"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Создание абонемента для клиента на основе шаблона.

    - **template_name**: Название шаблона (например, "8 занятий")
    - **client_id**: ID клиента
    - **comment**: Опциональный комментарий
    """
    template = get_template_by_name(template_name)

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Шаблон '{template_name}' не найден. Доступные: {', '.join([t['name'] for t in get_all_templates()])}"
        )

    client_result = await db.execute(
        select(Client).where(Client.id == client_id)
    )
    client = client_result.scalar_one_or_none()

    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Клиент не найден"
        )

    subscription = Subscription(
        client_id=client_id,
        name=template["name"],
        visits_total=template["visits_total"],
        visits_left=template["visits_total"],
        price=template["price"],
        comment=comment or template.get("description"),
        status=SubscriptionStatus.ACTIVE
    )

    if "validity_days" in template:
        from datetime import timedelta
        subscription.start_date = datetime.utcnow()
        subscription.end_date = subscription.start_date + timedelta(days=template["validity_days"])

    db.add(subscription)
    await db.commit()
    await db.refresh(subscription)

    return subscription


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

    # Создание абонемента с явным указанием всех полей
    subscription = Subscription(
        client_id=int(subscription_data.client_id),
        name=str(subscription_data.name),
        visits_total=int(subscription_data.visits_total),
        visits_left=int(subscription_data.visits_total),
        price=float(subscription_data.price) if subscription_data.price else 0.0,
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
