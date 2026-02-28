"""
Роутер для управления обратной связью от клиентов
"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional

from app.database import get_db
from app.models import Feedback, FeedbackType, Client, User, Schedule
from app.schemas import (
    FeedbackCreate,
    FeedbackUpdate,
    FeedbackResponse,
    FeedbackWithDetails,
    FeedbackTypeEnum,
)
from app.auth import get_current_user


router = APIRouter()


@router.get("/", response_model=List[FeedbackWithDetails], summary="Список отзывов")
async def get_feedback(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    feedback_type: Optional[FeedbackTypeEnum] = None,
    client_id: Optional[int] = None,
    schedule_id: Optional[int] = None,
    is_resolved: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Получить список отзывов с фильтрацией"""
    query = select(Feedback)

    if feedback_type:
        query = query.where(Feedback.feedback_type == FeedbackType(feedback_type.value))

    if client_id:
        query = query.where(Feedback.client_id == client_id)

    if schedule_id:
        query = query.where(Feedback.schedule_id == schedule_id)

    if is_resolved is not None:
        query = query.where(Feedback.is_resolved == is_resolved)

    query = query.order_by(Feedback.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    feedback_list = result.scalars().all()

    # Добавляем имена клиентов и названия занятий
    response_data = []
    for fb in feedback_list:
        client_name = None
        schedule_title = None

        if fb.client_id:
            client_result = await db.execute(
                select(Client.first_name, Client.last_name).where(Client.id == fb.client_id)
            )
            client_data = client_result.first()
            if client_data:
                client_name = f"{client_data.last_name} {client_data.first_name}".strip()

        if fb.schedule_id:
            schedule_result = await db.execute(
                select(Schedule.title).where(Schedule.id == fb.schedule_id)
            )
            schedule_title = schedule_result.scalar_one_or_none()

        response_data.append({
            "id": fb.id,
            "client_id": fb.client_id,
            "client_name": client_name,
            "schedule_id": fb.schedule_id,
            "schedule_title": schedule_title,
            "feedback_type": fb.feedback_type,
            "rating": fb.rating,
            "nps_score": fb.nps_score,
            "title": fb.title,
            "comment": fb.comment,
            "is_resolved": fb.is_resolved,
            "resolved_at": fb.resolved_at,
            "created_at": fb.created_at,
        })

    return response_data


@router.get("/{feedback_id}", response_model=FeedbackWithDetails, summary="Отзыв по ID")
async def get_feedback_item(
    feedback_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Получить информацию об отзыве"""
    result = await db.execute(
        select(Feedback).where(Feedback.id == feedback_id)
    )
    feedback = result.scalar_one_or_none()

    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Отзыв не найден"
        )

    # Получаем имя клиента
    client_result = await db.execute(
        select(Client.first_name, Client.last_name).where(Client.id == feedback.client_id)
    )
    client_data = client_result.first()
    client_name = f"{client_data.last_name} {client_data.first_name}".strip() if client_data else None

    # Получаем название занятия
    schedule_title = None
    if feedback.schedule_id:
        schedule_result = await db.execute(
            select(Schedule.title).where(Schedule.id == feedback.schedule_id)
        )
        schedule_title = schedule_result.scalar_one_or_none()

    return {
        "id": feedback.id,
        "client_id": feedback.client_id,
        "client_name": client_name,
        "schedule_id": feedback.schedule_id,
        "schedule_title": schedule_title,
        "feedback_type": feedback.feedback_type,
        "rating": feedback.rating,
        "nps_score": feedback.nps_score,
        "title": feedback.title,
        "comment": feedback.comment,
        "is_resolved": feedback.is_resolved,
        "resolved_at": feedback.resolved_at,
        "created_at": feedback.created_at,
    }


@router.post("/", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED, summary="Создать отзыв")
async def create_feedback(
    feedback_data: FeedbackCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Создать новый отзыв (оценка занятия, жалоба, предложение)"""
    # Проверка клиента
    client_result = await db.execute(
        select(Client).where(Client.id == feedback_data.client_id)
    )
    client = client_result.scalar_one_or_none()

    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Клиент не найден"
        )

    # Проверка занятия если указано
    if feedback_data.schedule_id:
        schedule_result = await db.execute(
            select(Schedule).where(Schedule.id == feedback_data.schedule_id)
        )
        schedule = schedule_result.scalar_one_or_none()

        if not schedule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Занятие не найдено"
            )

    # Валидация оценок
    if feedback_data.feedback_type == FeedbackTypeEnum.RATING:
        if feedback_data.rating is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Для оценки занятия необходимо указать рейтинг (1-5)"
            )

    if feedback_data.feedback_type == FeedbackTypeEnum.NPS:
        if feedback_data.nps_score is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Для NPS опроса необходимо указать оценку (0-10)"
            )

    feedback = Feedback(**feedback_data.model_dump())
    db.add(feedback)
    await db.commit()
    await db.refresh(feedback)

    return feedback


@router.patch("/{feedback_id}", response_model=FeedbackWithDetails, summary="Обновить отзыв")
async def update_feedback(
    feedback_id: int,
    feedback_data: FeedbackUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Обновить отзыв (например, отметить как решённый)"""
    if current_user.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Требуется роль администратора"
        )

    result = await db.execute(
        select(Feedback).where(Feedback.id == feedback_id)
    )
    feedback = result.scalar_one_or_none()

    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Отзыв не найден"
        )

    # Обновление полей
    update_data = feedback_data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(feedback, field, value)

    # Если отмечаем как решённый, ставим дату
    if update_data.get("is_resolved") is True and not feedback.resolved_at:
        feedback.resolved_at = datetime.utcnow()

    await db.commit()
    await db.refresh(feedback)

    # Получаем имя клиента и название занятия
    client_result = await db.execute(
        select(Client.first_name, Client.last_name).where(Client.id == feedback.client_id)
    )
    client_data = client_result.first()
    client_name = f"{client_data.last_name} {client_data.first_name}".strip() if client_data else None

    schedule_title = None
    if feedback.schedule_id:
        schedule_result = await db.execute(
            select(Schedule.title).where(Schedule.id == feedback.schedule_id)
        )
        schedule_title = schedule_result.scalar_one_or_none()

    return {
        "id": feedback.id,
        "client_id": feedback.client_id,
        "client_name": client_name,
        "schedule_id": feedback.schedule_id,
        "schedule_title": schedule_title,
        "feedback_type": feedback.feedback_type,
        "rating": feedback.rating,
        "nps_score": feedback.nps_score,
        "title": feedback.title,
        "comment": feedback.comment,
        "is_resolved": feedback.is_resolved,
        "resolved_at": feedback.resolved_at,
        "created_at": feedback.created_at,
    }


@router.delete("/{feedback_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Удалить отзыв")
async def delete_feedback(
    feedback_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Удалить отзыв"""
    if current_user.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Требуется роль администратора"
        )

    result = await db.execute(
        select(Feedback).where(Feedback.id == feedback_id)
    )
    feedback = result.scalar_one_or_none()

    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Отзыв не найден"
        )

    await db.delete(feedback)
    await db.commit()

    return None


@router.get("/stats/summary", summary="Статистика отзывов")
async def get_feedback_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Получить сводную статистику по отзывам"""
    # Общее количество
    total_query = select(func.count(Feedback.id))
    total_result = await db.execute(total_query)
    total_count = total_result.scalar() or 0

    # По типам
    type_query = select(
        Feedback.feedback_type,
        func.count(Feedback.id).label("count")
    ).group_by(Feedback.feedback_type)
    type_result = await db.execute(type_query)
    by_type = {str(row.feedback_type): row.count for row in type_result.all()}

    # Средний рейтинг
    rating_query = select(func.avg(Feedback.rating)).where(
        Feedback.feedback_type == FeedbackType.RATING
    )
    rating_result = await db.execute(rating_query)
    average_rating = rating_result.scalar() or 0

    # Средний NPS
    nps_query = select(func.avg(Feedback.nps_score)).where(
        Feedback.feedback_type == FeedbackType.NPS
    )
    nps_result = await db.execute(nps_query)
    average_nps = nps_result.scalar() or 0

    # Нерешённые жалобы
    unresolved_query = select(func.count(Feedback.id)).where(
        Feedback.feedback_type == FeedbackType.COMPLAINT,
        Feedback.is_resolved == False
    )
    unresolved_result = await db.execute(unresolved_query)
    unresolved_count = unresolved_result.scalar() or 0

    return {
        "total_count": total_count,
        "by_type": by_type,
        "average_rating": round(float(average_rating), 2) if average_rating else 0,
        "average_nps": round(float(average_nps), 2) if average_nps else 0,
        "unresolved_complaints": unresolved_count,
    }
