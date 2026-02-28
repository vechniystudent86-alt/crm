"""
Роутер для управления платежами клиентов
"""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional

from app.database import get_db
from app.models import Payment, PaymentStatus, PaymentMethod, Client, Subscription
from app.schemas import (
    PaymentCreate,
    PaymentUpdate,
    PaymentResponse,
    PaymentStatusEnum,
)
from app.auth import get_current_user
from app.models import User


router = APIRouter()


@router.get("/", response_model=List[PaymentResponse], summary="Список платежей")
async def get_payments(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    client_id: Optional[int] = None,
    status_filter: Optional[PaymentStatusEnum] = Query(None, alias="status"),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Получить список платежей с фильтрацией"""
    query = select(Payment)

    if client_id:
        query = query.where(Payment.client_id == client_id)

    if status_filter:
        query = query.where(Payment.status == PaymentStatus(status_filter.value))

    if start_date:
        query = query.where(Payment.payment_date >= start_date)

    if end_date:
        query = query.where(Payment.payment_date <= end_date)

    query = query.order_by(Payment.payment_date.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    payments = result.scalars().all()

    return payments


@router.get("/{payment_id}", response_model=PaymentResponse, summary="Платеж по ID")
async def get_payment(
    payment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Получить информацию о платеже"""
    result = await db.execute(
        select(Payment).where(Payment.id == payment_id)
    )
    payment = result.scalar_one_or_none()

    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Платеж не найден"
        )

    return payment


@router.post("/", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED, summary="Создать платеж")
async def create_payment(
    payment_data: PaymentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Создать новый платеж"""
    # Проверка существования клиента
    client_result = await db.execute(
        select(Client).where(Client.id == payment_data.client_id)
    )
    client = client_result.scalar_one_or_none()

    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Клиент не найден"
        )

    # Проверка подписки если указана
    if payment_data.subscription_id:
        sub_result = await db.execute(
            select(Subscription).where(Subscription.id == payment_data.subscription_id)
        )
        subscription = sub_result.scalar_one_or_none()

        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Абонемент не найден"
            )

        if subscription.client_id != payment_data.client_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Абонемент принадлежит другому клиенту"
            )

    # Создание платежа
    payment = Payment(
        client_id=payment_data.client_id,
        subscription_id=payment_data.subscription_id,
        amount=payment_data.amount,
        method=PaymentMethod(payment_data.method.value),
        status=PaymentStatus.COMPLETED,  # Автоматически помечаем как оплаченный
        comment=payment_data.comment,
    )

    db.add(payment)
    await db.commit()
    await db.refresh(payment)

    return payment


@router.patch("/{payment_id}", response_model=PaymentResponse, summary="Обновить платеж")
async def update_payment(
    payment_id: int,
    payment_data: PaymentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Обновить информацию о платеже (только для администратора)"""
    if current_user.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Требуется роль администратора"
        )

    result = await db.execute(
        select(Payment).where(Payment.id == payment_id)
    )
    payment = result.scalar_one_or_none()

    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Платеж не найден"
        )

    # Обновление полей
    update_data = payment_data.model_dump(exclude_unset=True)

    if "status" in update_data:
        update_data["status"] = PaymentStatus(update_data["status"].value)

    for field, value in update_data.items():
        setattr(payment, field, value)

    await db.commit()
    await db.refresh(payment)

    return payment


@router.delete("/{payment_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Удалить платеж")
async def delete_payment(
    payment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Удалить платеж (только для администратора)"""
    if current_user.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Требуется роль администратора"
        )

    result = await db.execute(
        select(Payment).where(Payment.id == payment_id)
    )
    payment = result.scalar_one_or_none()

    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Платеж не найден"
        )

    await db.delete(payment)
    await db.commit()

    return None
