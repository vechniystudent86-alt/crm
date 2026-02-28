"""
Роутер для управления расходами студии
"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional

from app.database import get_db
from app.models import Expense, ExpenseCategory, User as UserModel, Payment, PaymentStatus
from app.schemas import (
    ExpenseCreate,
    ExpenseUpdate,
    ExpenseResponse,
    ExpenseCategoryEnum,
    RevenueReport,
)
from app.auth import get_current_user


router = APIRouter()


@router.get("/", response_model=List[ExpenseResponse], summary="Список расходов")
async def get_expenses(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    category: Optional[ExpenseCategoryEnum] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """Получить список расходов с фильтрацией"""
    query = select(Expense)

    if category:
        query = query.where(Expense.category == ExpenseCategory(category.value))

    if start_date:
        query = query.where(Expense.expense_date >= start_date)

    if end_date:
        query = query.where(Expense.expense_date <= end_date)

    query = query.order_by(Expense.expense_date.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    expenses = result.scalars().all()

    return expenses


@router.get("/{expense_id}", response_model=ExpenseResponse, summary="Расход по ID")
async def get_expense(
    expense_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """Получить информацию о расходе"""
    result = await db.execute(
        select(Expense).where(Expense.id == expense_id)
    )
    expense = result.scalar_one_or_none()

    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Расход не найден"
        )

    return expense


@router.post("/", response_model=ExpenseResponse, status_code=status.HTTP_201_CREATED, summary="Создать расход")
async def create_expense(
    expense_data: ExpenseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """Создать новый расход"""
    if current_user.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Требуется роль администратора"
        )

    expense = Expense(
        category=ExpenseCategory(expense_data.category.value),
        amount=expense_data.amount,
        description=expense_data.description,
        expense_date=expense_data.expense_date or datetime.utcnow(),
        receipt_number=expense_data.receipt_number,
        created_by_id=current_user.id,
    )

    db.add(expense)
    await db.commit()
    await db.refresh(expense)

    return expense


@router.patch("/{expense_id}", response_model=ExpenseResponse, summary="Обновить расход")
async def update_expense(
    expense_id: int,
    expense_data: ExpenseUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """Обновить информацию о расходе"""
    if current_user.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Требуется роль администратора"
        )

    result = await db.execute(
        select(Expense).where(Expense.id == expense_id)
    )
    expense = result.scalar_one_or_none()

    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Расход не найден"
        )

    # Обновление полей
    update_data = expense_data.model_dump(exclude_unset=True)

    if "category" in update_data:
        update_data["category"] = ExpenseCategory(update_data["category"].value)

    for field, value in update_data.items():
        setattr(expense, field, value)

    await db.commit()
    await db.refresh(expense)

    return expense


@router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Удалить расход")
async def delete_expense(
    expense_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """Удалить расход"""
    if current_user.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Требуется роль администратора"
        )

    result = await db.execute(
        select(Expense).where(Expense.id == expense_id)
    )
    expense = result.scalar_one_or_none()

    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Расход не найден"
        )

    await db.delete(expense)
    await db.commit()

    return None


@router.get("/reports/profit-loss", response_model=RevenueReport, summary="Отчёт P&L")
async def get_profit_loss_report(
    start_date: datetime,
    end_date: datetime,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """
    Отчёт о прибылях и убытках (P&L) за период.
    
    - **start_date**: Начало периода
    - **end_date**: Конец периода
    """
    # Получаем доходы
    revenue_query = select(func.sum(Payment.amount)).where(
        Payment.status == PaymentStatus.COMPLETED,
        Payment.payment_date >= start_date,
        Payment.payment_date <= end_date,
    )
    revenue_result = await db.execute(revenue_query)
    total_revenue = revenue_result.scalar() or 0.0

    # Получаем расходы
    expense_query = select(func.sum(Expense.amount)).where(
        Expense.expense_date >= start_date,
        Expense.expense_date <= end_date,
    )
    expense_result = await db.execute(expense_query)
    total_expenses = expense_result.scalar() or 0.0

    # Детализация по методам оплаты
    method_query = select(
        Payment.method,
        func.sum(Payment.amount).label("total")
    ).where(
        Payment.status == PaymentStatus.COMPLETED,
        Payment.payment_date >= start_date,
        Payment.payment_date <= end_date,
    ).group_by(Payment.method)

    method_result = await db.execute(method_query)
    by_payment_method = {
        str(row.method): float(row.total)
        for row in method_result.all()
    }

    # Детализация по категориям расходов
    category_query = select(
        Expense.category,
        func.sum(Expense.amount).label("total")
    ).where(
        Expense.expense_date >= start_date,
        Expense.expense_date <= end_date,
    ).group_by(Expense.category)

    category_result = await db.execute(category_query)
    by_expense_category = {
        str(row.category): float(row.total)
        for row in category_result.all()
    }

    return RevenueReport(
        total_revenue=float(total_revenue),
        total_expenses=float(total_expenses),
        profit=float(total_revenue) - float(total_expenses),
        period_start=start_date,
        period_end=end_date,
        by_payment_method=by_payment_method,
        by_expense_category=by_expense_category,
    )
