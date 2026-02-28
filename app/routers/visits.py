"""
Роутер управления посещениями
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, extract
from typing import List, Optional
from datetime import datetime, date, timedelta

from app.database import get_db
from app.auth import get_current_user
from app.models import User, Visit, VisitType, Subscription, Client
from app.schemas import VisitCreate, VisitUpdate, VisitResponse


router = APIRouter()


@router.get("/", response_model=List[VisitResponse], summary="Список посещений")
async def get_all_visits(
    client_id: Optional[int] = Query(None, description="Фильтр по клиенту"),
    date_from: Optional[date] = Query(None, description="Дата от"),
    date_to: Optional[date] = Query(None, description="Дата до"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Получение списка посещений с фильтрами.
    
    - **client_id**: Фильтр по ID клиента
    - **date_from**: Дата от (YYYY-MM-DD)
    - **date_to**: Дата до (YYYY-MM-DD)
    - **skip**: Пропустить N записей
    - **limit**: Количество записей
    """
    query = select(Visit)
    
    if client_id:
        query = query.where(Visit.client_id == client_id)
    
    if date_from:
        query = query.where(func.date(Visit.visit_date) >= date_from)
    
    if date_to:
        query = query.where(func.date(Visit.visit_date) <= date_to)
    
    query = query.order_by(Visit.visit_date.desc()).offset(skip).limit(limit)
    
    result = await db.execute(query)
    visits = result.scalars().all()
    
    return visits


@router.get("/today", response_model=List[VisitResponse], summary="Посещения сегодня")
async def get_today_visits(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получение всех посещений за сегодня"""
    today = date.today()
    
    query = select(Visit).where(
        func.date(Visit.visit_date) == today
    ).order_by(Visit.visit_date.desc())
    
    result = await db.execute(query)
    visits = result.scalars().all()
    
    return visits


@router.get("/{visit_id}", response_model=VisitResponse, summary="Посещение по ID")
async def get_visit(
    visit_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получение информации о посещении по ID"""
    result = await db.execute(
        select(Visit).where(Visit.id == visit_id)
    )
    visit = result.scalar_one_or_none()
    
    if not visit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Посещение не найдено"
        )
    
    return visit


@router.post("/", response_model=VisitResponse, status_code=status.HTTP_201_CREATED, summary="Добавить посещение")
async def create_visit(
    visit_data: VisitCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Добавление нового посещения.
    
    - **client_id**: ID клиента
    - **subscription_id**: ID абонемента (опционально)
    - **visit_date**: Дата и время посещения
    - **visit_type**: Тип (group, individual, trial)
    - **class_name**: Название занятия
    - **trainer**: Тренер
    - **hall**: Зал
    - **comment**: Комментарий
    """
    # Проверка существования клиента
    client_result = await db.execute(
        select(Client).where(Client.id == visit_data.client_id)
    )
    client = client_result.scalar_one_or_none()
    
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Клиент не найден"
        )
    
    # Проверка абонемента если указан
    if visit_data.subscription_id:
        subscription_result = await db.execute(
            select(Subscription).where(Subscription.id == visit_data.subscription_id)
        )
        subscription = subscription_result.scalar_one_or_none()
        
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Абонемент не найден"
            )
        
        # Проверка статуса абонемента
        if subscription.status not in [SubscriptionStatus.ACTIVE, SubscriptionStatus.FROZEN]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Абонемент не активен"
            )
        
        # Уменьшение количества посещений
        if subscription.visits_left > 0:
            subscription.visits_left -= 1
    
    # Создание посещения
    visit = Visit(**visit_data.model_dump())
    
    db.add(visit)
    await db.commit()
    await db.refresh(visit)
    
    return visit


@router.put("/{visit_id}", response_model=VisitResponse, summary="Обновить посещение")
async def update_visit(
    visit_id: int,
    visit_update: VisitUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Обновление информации о посещении"""
    result = await db.execute(
        select(Visit).where(Visit.id == visit_id)
    )
    visit = result.scalar_one_or_none()
    
    if not visit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Посещение не найдено"
        )
    
    # Обновление полей
    update_data = visit_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if isinstance(value, str) and field == "visit_type":
            value = VisitType(value)
        setattr(visit, field, value)
    
    await db.commit()
    await db.refresh(visit)
    
    return visit


@router.delete("/{visit_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Удалить посещение")
async def delete_visit(
    visit_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Удаление посещения"""
    result = await db.execute(
        select(Visit).where(Visit.id == visit_id)
    )
    visit = result.scalar_one_or_none()
    
    if not visit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Посещение не найдено"
        )
    
    await db.delete(visit)
    await db.commit()
    
    return None


@router.get("/stats/week", summary="Статистика посещений за неделю")
async def get_week_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Получение статистики посещений по дням за текущую неделю.
    
    Возвращает количество посещений для каждого дня недели.
    """
    today = date.today()
    start_of_week = today - timedelta(days=today.weekday())
    
    query = select(
        func.date(Visit.visit_date).label('visit_date'),
        func.count(Visit.id).label('count')
    ).where(
        func.date(Visit.visit_date) >= start_of_week
    ).group_by(
        func.date(Visit.visit_date)
    )
    
    result = await db.execute(query)
    stats = result.all()
    
    # Преобразование в словарь
    stats_dict = {str(row[0]): row[1] for row in stats}
    
    # Заполнение всех дней недели
    week_stats = {}
    for i in range(7):
        day = start_of_week + timedelta(days=i)
        week_stats[str(day)] = stats_dict.get(str(day), 0)
    
    return {
        "week_start": start_of_week,
        "days": week_stats
    }
