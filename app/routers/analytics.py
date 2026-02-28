"""
Роутер для аналитики и отчётов
"""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, distinct, case
from sqlalchemy.sql import literal_column
from typing import List, Optional
from sqlalchemy.orm import aliased

from app.database import get_db
from app.models import (
    Client, Subscription, Visit, Payment, Expense,
    Schedule, Enrollment, Feedback, User,
    SubscriptionStatus, PaymentStatus,
)
from app.schemas import (
    DashboardMetrics,
    RevenueReport,
    TrainerPerformance,
    ClientChurnReport,
    RFMClient,
    SubscriptionSalesReport,
)
from app.auth import get_current_user


router = APIRouter()


@router.get("/dashboard", response_model=DashboardMetrics, summary="Метрики дашборда")
async def get_dashboard_metrics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Получить основные метрики для дашборда"""
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=now.weekday())
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # === Клиенты ===
    total_clients_query = select(func.count(Client.id))
    total_clients_result = await db.execute(total_clients_query)
    total_clients = total_clients_result.scalar() or 0

    active_clients_query = select(func.count(Client.id)).where(Client.is_active == True)
    active_clients_result = await db.execute(active_clients_query)
    active_clients = active_clients_result.scalar() or 0

    new_clients_today_query = select(func.count(Client.id)).where(
        Client.created_at >= today_start
    )
    new_clients_today_result = await db.execute(new_clients_today_query)
    new_clients_today = new_clients_today_result.scalar() or 0

    # === Подписки ===
    active_subscriptions_query = select(func.count(Subscription.id)).where(
        Subscription.status == SubscriptionStatus.ACTIVE
    )
    active_subscriptions_result = await db.execute(active_subscriptions_query)
    active_subscriptions = active_subscriptions_result.scalar() or 0

    # Истекающие в ближайшие 7 дней
    expiring_soon_query = select(func.count(Subscription.id)).where(
        Subscription.status == SubscriptionStatus.ACTIVE,
        Subscription.end_date <= now + timedelta(days=7),
        Subscription.end_date >= now
    )
    expiring_soon_result = await db.execute(expiring_soon_query)
    expiring_soon = expiring_soon_result.scalar() or 0

    # === Посещения ===
    visits_today_query = select(func.count(Visit.id)).where(
        Visit.visit_date >= today_start
    )
    visits_today_result = await db.execute(visits_today_query)
    visits_today = visits_today_result.scalar() or 0

    visits_this_week_query = select(func.count(Visit.id)).where(
        Visit.visit_date >= week_start
    )
    visits_this_week_result = await db.execute(visits_this_week_query)
    visits_this_week = visits_this_week_result.scalar() or 0

    # === Финансы ===
    # Доходы сегодня
    revenue_today_query = select(func.sum(Payment.amount)).where(
        Payment.status == PaymentStatus.COMPLETED,
        Payment.payment_date >= today_start
    )
    revenue_today_result = await db.execute(revenue_today_query)
    revenue_today = revenue_today_result.scalar() or 0.0

    # Доходы за неделю
    revenue_week_query = select(func.sum(Payment.amount)).where(
        Payment.status == PaymentStatus.COMPLETED,
        Payment.payment_date >= week_start
    )
    revenue_week_result = await db.execute(revenue_week_query)
    revenue_this_week = revenue_week_result.scalar() or 0.0

    # Доходы за месяц
    revenue_month_query = select(func.sum(Payment.amount)).where(
        Payment.status == PaymentStatus.COMPLETED,
        Payment.payment_date >= month_start
    )
    revenue_month_result = await db.execute(revenue_month_query)
    revenue_this_month = revenue_month_result.scalar() or 0.0

    # Расходы за неделю
    expenses_week_query = select(func.sum(Expense.amount)).where(
        Expense.expense_date >= week_start
    )
    expenses_week_result = await db.execute(expenses_week_query)
    expenses_this_week = expenses_week_result.scalar() or 0.0

    # Расходы за месяц
    expenses_month_query = select(func.sum(Expense.amount)).where(
        Expense.expense_date >= month_start
    )
    expenses_month_result = await db.execute(expenses_month_query)
    expenses_this_month = expenses_month_result.scalar() or 0.0

    # Прибыль за месяц
    profit_this_month = revenue_this_month - expenses_this_month

    # === Расписание ===
    upcoming_classes_query = select(func.count(Schedule.id)).where(
        Schedule.start_time >= now,
        Schedule.status == ScheduleStatus.ACTIVE
    )
    upcoming_classes_result = await db.execute(upcoming_classes_query)
    upcoming_classes = upcoming_classes_result.scalar() or 0

    # Лист ожидания
    waitlist_count_query = select(func.count(Enrollment.id)).where(
        Enrollment.status == "waitlist"
    )
    waitlist_count_result = await db.execute(waitlist_count_query)
    waitlist_count = waitlist_count_result.scalar() or 0

    # === Конверсия (упрощённо) ===
    # Отношение клиентов с активными подписками к общему числу
    conversion_rate = (active_clients / total_clients * 100) if total_clients > 0 else 0

    # === Средняя посещаемость ===
    avg_attendance_query = select(
        func.count(distinct(Enrollment.id)).label("attended"),
        func.count(Enrollment.id).label("total")
    ).where(Enrollment.attended == True)
    avg_attendance_result = await db.execute(avg_attendance_query)
    avg_attendance_row = avg_attendance_result.first()
    
    if avg_attendance_row and avg_attendance_row.total > 0:
        average_attendance_rate = (avg_attendance_row.attended / avg_attendance_row.total) * 100
    else:
        average_attendance_rate = 0

    return DashboardMetrics(
        total_clients=total_clients,
        active_clients=active_clients,
        new_clients_today=new_clients_today,
        total_revenue_today=revenue_today,
        total_expenses_today=0,  # Можно добавить если нужно
        active_subscriptions=active_subscriptions,
        expiring_soon=expiring_soon,
        visits_today=visits_today,
        visits_this_week=visits_this_week,
        average_attendance_rate=round(average_attendance_rate, 2),
        upcoming_classes=upcoming_classes,
        waitlist_count=waitlist_count,
        revenue_this_week=revenue_this_week,
        revenue_this_month=revenue_this_month,
        expenses_this_week=expenses_this_week,
        expenses_this_month=expenses_this_month,
        profit_this_month=profit_this_month,
        conversion_rate=round(conversion_rate, 2),
    )


@router.get("/reports/trainer-performance", response_model=List[TrainerPerformance], summary="Эффективность тренеров")
async def get_trainer_performance_report(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Отчёт по эффективности тренеров"""
    if not start_date:
        start_date = datetime.utcnow() - timedelta(days=30)
    if not end_date:
        end_date = datetime.utcnow()

    # Получаем всех тренеров
    trainers_query = select(User).where(User.role == "trainer")
    trainers_result = await db.execute(trainers_query)
    trainers = trainers_result.scalars().all()

    report = []
    for trainer in trainers:
        # Количество занятий
        classes_query = select(func.count(Schedule.id)).where(
            Schedule.trainer_id == trainer.id,
            Schedule.start_time >= start_date,
            Schedule.start_time <= end_date,
        )
        classes_result = await db.execute(classes_query)
        total_classes = classes_result.scalar() or 0

        # Количество уникальных клиентов
        clients_query = select(func.count(distinct(Enrollment.client_id))).join(
            Schedule, Enrollment.schedule_id == Schedule.id
        ).where(
            Schedule.trainer_id == trainer.id,
            Schedule.start_time >= start_date,
            Schedule.start_time <= end_date,
        )
        clients_result = await db.execute(clients_query)
        total_clients = clients_result.scalar() or 0

        # Средняя оценка
        rating_query = select(func.avg(Feedback.rating)).join(
            Schedule, Feedback.schedule_id == Schedule.id
        ).where(
            Schedule.trainer_id == trainer.id,
            Feedback.feedback_type == FeedbackType.RATING,
            Feedback.created_at >= start_date,
            Feedback.created_at <= end_date,
        )
        rating_result = await db.execute(rating_query)
        average_rating = rating_result.scalar()

        # Доход (если занятия платные)
        revenue_query = select(func.sum(Schedule.price)).join(
            Enrollment, Enrollment.schedule_id == Schedule.id
        ).where(
            Schedule.trainer_id == trainer.id,
            Schedule.price != None,
            Schedule.start_time >= start_date,
            Schedule.start_time <= end_date,
        )
        revenue_result = await db.execute(revenue_query)
        total_revenue = revenue_result.scalar() or 0

        report.append(TrainerPerformance(
            trainer_id=trainer.id,
            trainer_name=trainer.full_name or trainer.username,
            total_classes=total_classes,
            total_clients=total_clients,
            average_rating=round(float(average_rating), 2) if average_rating else None,
            total_revenue=total_revenue,
        ))

    return report


@router.get("/reports/client-churn", response_model=List[ClientChurnReport], summary="Отток клиентов")
async def get_client_churn_report(
    days_threshold: int = Query(30, ge=7, le=90),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Отчёт по клиентам, которые не ходят больше N дней.
    
    - **days_threshold**: Количество дней для определения оттока (по умолчанию 30)
    """
    now = datetime.utcnow()
    threshold_date = now - timedelta(days=days_threshold)

    # Клиенты у которых последнее посещение было больше threshold дней назад
    query = """
    SELECT 
        c.id,
        c.first_name,
        c.last_name,
        c.phone,
        MAX(v.visit_date) as last_visit_date,
        COUNT(v.id) as total_visits,
        CASE WHEN s.status = 'active' THEN 1 ELSE 0 END as has_active_subscription
    FROM clients c
    LEFT JOIN visits v ON c.id = v.client_id
    LEFT JOIN subscriptions s ON c.id = s.client_id AND s.status = 'active'
    WHERE c.is_active = true
    GROUP BY c.id, c.first_name, c.last_name, c.phone, s.status
    HAVING MAX(v.visit_date) < :threshold_date OR MAX(v.visit_date) IS NULL
    ORDER BY last_visit_date ASC NULLS FIRST
    LIMIT 100
    """

    result = await db.execute(
        literal_column(query),
        {"threshold_date": threshold_date}
    )
    rows = result.all()

    report = []
    for row in rows:
        last_visit = row.last_visit_date
        days_since = (now - last_visit).days if last_visit else 999

        report.append(ClientChurnReport(
            client_id=row.id,
            client_name=f"{row.last_name} {row.first_name}".strip(),
            phone=row.phone,
            last_visit_date=last_visit,
            days_since_last_visit=days_since,
            total_visits=row.total_visits or 0,
            has_active_subscription=bool(row.has_active_subscription),
        ))

    return report


@router.get("/reports/rfm-segmentation", response_model=List[RFMClient], summary="RFM-сегментация")
async def get_rfm_segmentation(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    RFM-сегментация клиентов.
    
    - **Recency**: Как давно был последний визит
    - **Frequency**: Как часто ходит
    - **Monetary**: Сколько потратил
    """
    now = datetime.utcnow()

    # Получаем данные по всем клиентам
    query = """
    SELECT 
        c.id,
        c.first_name,
        c.last_name,
        MAX(v.visit_date) as last_visit,
        COUNT(v.id) as visit_count,
        COALESCE(SUM(p.amount), 0) as total_spent
    FROM clients c
    LEFT JOIN visits v ON c.id = v.client_id
    LEFT JOIN payments p ON c.id = p.client_id AND p.status = 'completed'
    WHERE c.is_active = true
    GROUP BY c.id, c.first_name, c.last_name
    HAVING COUNT(v.id) > 0
    LIMIT 200
    """

    result = await db.execute(literal_column(query))
    rows = result.all()

    if not rows:
        return []

    # Считаем квантили для scoring
    recencies = [(now - r.last_visit).days if r.last_visit else 999 for r in rows]
    frequencies = [r.visit_count for r in rows]
    monetaries = [r.total_spent for r in rows]

    def get_score(value, values, higher_is_better=True):
        """Присвоить score 1-5 на основе квантилей"""
        if not values:
            return 3
        
        sorted_values = sorted(set(values))
        if len(sorted_values) < 5:
            return 3
        
        step = len(sorted_values) // 5
        try:
            if higher_is_better:
                for i in range(5, 0, -1):
                    idx = min((i - 1) * step, len(sorted_values) - 1)
                    if value >= sorted_values[idx]:
                        return i
            else:
                for i in range(1, 6):
                    idx = min((i - 1) * step, len(sorted_values) - 1)
                    if value <= sorted_values[idx]:
                        return i
        except:
            pass
        return 3

    report = []
    for row in rows:
        recency_days = (now - row.last_visit).days if row.last_visit else 999
        frequency = row.visit_count
        monetary = row.total_spent

        r_score = get_score(recency_days, recencies, higher_is_better=False)
        f_score = get_score(frequency, frequencies, higher_is_better=True)
        m_score = get_score(monetary, monetaries, higher_is_better=True)

        # Определяем сегмент
        rfm_sum = r_score + f_score + m_score
        if rfm_sum >= 12:
            segment = "Champions"
        elif rfm_sum >= 10:
            segment = "Loyal"
        elif rfm_sum >= 8:
            segment = "Potential Loyalist"
        elif rfm_sum >= 6:
            segment = "At Risk"
        else:
            segment = "Lost"

        report.append(RFMClient(
            client_id=row.id,
            client_name=f"{row.last_name} {row.first_name}".strip(),
            recency_score=r_score,
            frequency_score=f_score,
            monetary_score=m_score,
            rfm_segment=segment,
            total_visits=frequency,
            total_spent=monetary,
            last_visit_date=row.last_visit,
        ))

    return report


@router.get("/reports/subscription-sales", response_model=List[SubscriptionSalesReport], summary="Продажи абонементов")
async def get_subscription_sales_report(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Отчёт по продажам абонементов"""
    if not start_date:
        start_date = datetime.utcnow() - timedelta(days=30)
    if not end_date:
        end_date = datetime.utcnow()

    query = """
    SELECT 
        s.name as subscription_name,
        COUNT(s.id) as total_sold,
        COALESCE(SUM(s.price), 0) as total_revenue,
        COALESCE(AVG(s.price), 0) as average_price
    FROM subscriptions s
    WHERE s.created_at >= :start_date
      AND s.created_at <= :end_date
    GROUP BY s.name
    ORDER BY total_sold DESC
    """

    result = await db.execute(
        literal_column(query),
        {"start_date": start_date, "end_date": end_date}
    )
    rows = result.all()

    report = []
    for row in rows:
        report.append(SubscriptionSalesReport(
            subscription_name=row.subscription_name,
            total_sold=row.total_sold,
            total_revenue=row.total_revenue,
            average_price=row.average_price,
            period_start=start_date,
            period_end=end_date,
        ))

    return report
