"""
Роутер для управления расписанием занятий
"""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional

from app.database import get_db
from app.models import Schedule, ScheduleStatus, Enrollment, User, Client
from app.schemas import (
    ScheduleCreate,
    ScheduleUpdate,
    ScheduleResponse,
    ScheduleStatusEnum,
    EnrollmentCreate,
    EnrollmentResponse,
    EnrollmentStatusEnum,
)
from app.auth import get_current_user


router = APIRouter()


@router.get("/", response_model=List[ScheduleResponse], summary="Список занятий")
async def get_schedules(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    hall: Optional[str] = None,
    trainer_id: Optional[int] = None,
    status_filter: Optional[ScheduleStatusEnum] = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Получить расписание занятий с фильтрацией"""
    query = select(Schedule)

    if start_date:
        query = query.where(Schedule.start_time >= start_date)

    if end_date:
        query = query.where(Schedule.start_time <= end_date)

    if hall:
        query = query.where(Schedule.hall == hall)

    if trainer_id:
        query = query.where(Schedule.trainer_id == trainer_id)

    if status_filter:
        query = query.where(Schedule.status == ScheduleStatus(status_filter.value))

    query = query.order_by(Schedule.start_time.asc()).offset(skip).limit(limit)

    result = await db.execute(query)
    schedules = result.scalars().all()

    # Для каждого занятия получаем количество записанных и лист ожидания
    response_data = []
    for schedule in schedules:
        # Количество записанных
        enrolled_query = select(func.count(Enrollment.id)).where(
            Enrollment.schedule_id == schedule.id,
            Enrollment.status == "enrolled"
        )
        enrolled_result = await db.execute(enrolled_query)
        enrolled_count = enrolled_result.scalar() or 0

        # Количество в листе ожидания
        waitlist_query = select(func.count(Enrollment.id)).where(
            Enrollment.schedule_id == schedule.id,
            Enrollment.status == "waitlist"
        )
        waitlist_result = await db.execute(waitlist_query)
        waitlist_count = waitlist_result.scalar() or 0

        # Добавляем имя тренера
        trainer_name = None
        if schedule.trainer_id:
            trainer_result = await db.execute(
                select(User.full_name).where(User.id == schedule.trainer_id)
            )
            trainer_name = trainer_result.scalar_one_or_none()

        # Создаём ответ с дополнительными полями
        schedule_dict = {
            "id": schedule.id,
            "title": schedule.title,
            "description": schedule.description,
            "hall": schedule.hall,
            "start_time": schedule.start_time,
            "end_time": schedule.end_time,
            "max_participants": schedule.max_participants,
            "price": schedule.price,
            "trainer_id": schedule.trainer_id,
            "trainer_name": trainer_name,
            "status": schedule.status,
            "enrolled_count": enrolled_count,
            "has_waitlist": waitlist_count > 0,
            "created_at": schedule.created_at,
            "updated_at": schedule.updated_at,
        }
        response_data.append(schedule_dict)

    return response_data


@router.get("/{schedule_id}", response_model=ScheduleResponse, summary="Занятие по ID")
async def get_schedule(
    schedule_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Получить информацию о занятии"""
    result = await db.execute(
        select(Schedule).where(Schedule.id == schedule_id)
    )
    schedule = result.scalar_one_or_none()

    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Занятие не найдено"
        )

    # Получаем количество записанных
    enrolled_query = select(func.count(Enrollment.id)).where(
        Enrollment.schedule_id == schedule.id,
        Enrollment.status == "enrolled"
    )
    enrolled_result = await db.execute(enrolled_query)
    enrolled_count = enrolled_result.scalar() or 0

    # Получаем количество в листе ожидания
    waitlist_query = select(func.count(Enrollment.id)).where(
        Enrollment.schedule_id == schedule.id,
        Enrollment.status == "waitlist"
    )
    waitlist_result = await db.execute(waitlist_query)
    waitlist_count = waitlist_result.scalar() or 0

    # Получаем имя тренера
    trainer_name = None
    if schedule.trainer_id:
        trainer_result = await db.execute(
            select(User.full_name).where(User.id == schedule.trainer_id)
        )
        trainer_name = trainer_result.scalar_one_or_none()

    return {
        "id": schedule.id,
        "title": schedule.title,
        "description": schedule.description,
        "hall": schedule.hall,
        "start_time": schedule.start_time,
        "end_time": schedule.end_time,
        "max_participants": schedule.max_participants,
        "price": schedule.price,
        "trainer_id": schedule.trainer_id,
        "trainer_name": trainer_name,
        "status": schedule.status,
        "enrolled_count": enrolled_count,
        "has_waitlist": waitlist_count > 0,
        "created_at": schedule.created_at,
        "updated_at": schedule.updated_at,
    }


@router.post("/", response_model=ScheduleResponse, status_code=status.HTTP_201_CREATED, summary="Создать занятие")
async def create_schedule(
    schedule_data: ScheduleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Создать новое занятие в расписании"""
    if current_user.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Требуется роль администратора"
        )

    # Проверка тренера если указан
    if schedule_data.trainer_id:
        trainer_result = await db.execute(
            select(User).where(User.id == schedule_data.trainer_id)
        )
        trainer = trainer_result.scalar_one_or_none()

        if not trainer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Тренер не найден"
            )

    schedule = Schedule(**schedule_data.model_dump())
    db.add(schedule)
    await db.commit()
    await db.refresh(schedule)

    return schedule


@router.patch("/{schedule_id}", response_model=ScheduleResponse, summary="Обновить занятие")
async def update_schedule(
    schedule_id: int,
    schedule_data: ScheduleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Обновить информацию о занятии"""
    if current_user.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Требуется роль администратора"
        )

    result = await db.execute(
        select(Schedule).where(Schedule.id == schedule_id)
    )
    schedule = result.scalar_one_or_none()

    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Занятие не найдено"
        )

    # Обновление полей
    update_data = schedule_data.model_dump(exclude_unset=True)

    if "status" in update_data:
        update_data["status"] = ScheduleStatus(update_data["status"].value)

    for field, value in update_data.items():
        setattr(schedule, field, value)

    await db.commit()
    await db.refresh(schedule)

    return schedule


@router.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Удалить занятие")
async def delete_schedule(
    schedule_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Удалить занятие из расписания"""
    if current_user.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Требуется роль администратора"
        )

    result = await db.execute(
        select(Schedule).where(Schedule.id == schedule_id)
    )
    schedule = result.scalar_one_or_none()

    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Занятие не найдено"
        )

    await db.delete(schedule)
    await db.commit()

    return None


# ============================================
# Запись клиентов на занятия (Enrollments)
# ============================================

@router.post("/{schedule_id}/enroll", response_model=EnrollmentResponse, summary="Записаться на занятие")
async def enroll_to_class(
    schedule_id: int,
    enrollment_data: EnrollmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Записать клиента на занятие (с автоматическим листом ожидания)"""
    # Проверка занятия
    schedule_result = await db.execute(
        select(Schedule).where(Schedule.id == schedule_id)
    )
    schedule = schedule_result.scalar_one_or_none()

    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Занятие не найдено"
        )

    if schedule.status != ScheduleStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Запись на это занятие закрыта"
        )

    # Проверка клиента
    client_result = await db.execute(
        select(Client).where(Client.id == enrollment_data.client_id)
    )
    client = client_result.scalar_one_or_none()

    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Клиент не найден"
        )

    # Проверка: не записан ли уже клиент
    existing_enrollment = await db.execute(
        select(Enrollment).where(
            Enrollment.schedule_id == schedule_id,
            Enrollment.client_id == enrollment_data.client_id,
            Enrollment.status.in_(["enrolled", "waitlist"])
        )
    )
    if existing_enrollment.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Клиент уже записан на это занятие"
        )

    # Считаем количество записанных
    enrolled_query = select(func.count(Enrollment.id)).where(
        Enrollment.schedule_id == schedule_id,
        Enrollment.status == "enrolled"
    )
    enrolled_result = await db.execute(enrolled_query)
    enrolled_count = enrolled_result.scalar() or 0

    # Определяем статус: enrolled или waitlist
    if enrolled_count < schedule.max_participants:
        enrollment_status = "enrolled"
    else:
        enrollment_status = "waitlist"

    # Создаём запись
    enrollment = Enrollment(
        schedule_id=schedule_id,
        client_id=enrollment_data.client_id,
        subscription_id=enrollment_data.subscription_id,
        status=enrollment_status,
    )

    db.add(enrollment)
    await db.commit()
    await db.refresh(enrollment)

    return enrollment


@router.get("/{schedule_id}/enrollments", response_model=List[EnrollmentResponse], summary="Список записавшихся")
async def get_enrollments(
    schedule_id: int,
    status_filter: Optional[EnrollmentStatusEnum] = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Получить список всех записавшихся на занятие"""
    query = select(Enrollment).where(Enrollment.schedule_id == schedule_id)

    if status_filter:
        query = query.where(Enrollment.status == status_filter.value)

    query = query.order_by(Enrollment.created_at.asc())

    result = await db.execute(query)
    enrollments = result.scalars().all()

    return enrollments


@router.delete("/enrollments/{enrollment_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Отменить запись")
async def cancel_enrollment(
    enrollment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Отменить запись на занятие"""
    result = await db.execute(
        select(Enrollment).where(Enrollment.id == enrollment_id)
    )
    enrollment = result.scalar_one_or_none()

    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Запись не найдена"
        )

    # Обновляем статус
    enrollment.status = "cancelled"
    await db.commit()

    return None
