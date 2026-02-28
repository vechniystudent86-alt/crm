"""
Pydantic-схемы для валидации данных API
"""
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from datetime import datetime
from typing import Optional, List
from enum import Enum


# === ENUM Schemas ===
class UserRoleEnum(str, Enum):
    ADMIN = "admin"
    TRAINER = "trainer"


class SubscriptionStatusEnum(str, Enum):
    ACTIVE = "active"
    FROZEN = "frozen"
    EXPIRED = "expired"
    ARCHIVED = "archived"


class VisitTypeEnum(str, Enum):
    GROUP = "group"
    INDIVIDUAL = "individual"
    TRIAL = "trial"


class PaymentStatusEnum(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class PaymentMethodEnum(str, Enum):
    CASH = "cash"
    CARD = "card"
    ONLINE = "online"
    TRANSFER = "transfer"


class ExpenseCategoryEnum(str, Enum):
    RENT = "rent"
    SALARY = "salary"
    UTILITIES = "utilities"
    MARKETING = "marketing"
    EQUIPMENT = "equipment"
    SUPPLIES = "supplies"
    TAXES = "taxes"
    OTHER = "other"


class ScheduleStatusEnum(str, Enum):
    ACTIVE = "active"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class FeedbackTypeEnum(str, Enum):
    RATING = "rating"
    NPS = "nps"
    COMPLAINT = "complaint"
    SUGGESTION = "suggestion"


class EnrollmentStatusEnum(str, Enum):
    ENROLLED = "enrolled"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    WAITLIST = "waitlist"


# === User Schemas ===
class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    full_name: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    role: UserRoleEnum = UserRoleEnum.TRAINER


class UserCreate(UserBase):
    password: str = Field(..., min_length=6)


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[UserRoleEnum] = None
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool
    created_at: datetime


class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None


# === Client Schemas ===
class ClientBase(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: Optional[str] = Field(None, max_length=50)
    phone: str = Field(..., min_length=10, max_length=20)
    telegram: Optional[str] = Field(None, max_length=50)
    whatsapp: Optional[str] = Field(None, max_length=50)
    email: Optional[EmailStr] = None
    comment: Optional[str] = None
    source: Optional[str] = Field("website", max_length=50)


class ClientCreate(ClientBase):
    pass


class ClientUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    telegram: Optional[str] = None
    whatsapp: Optional[str] = None
    email: Optional[EmailStr] = None
    comment: Optional[str] = None
    is_active: Optional[bool] = None


class ClientResponse(ClientBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    created_by_id: Optional[int] = None


class ClientWithSubscriptions(ClientResponse):
    subscriptions: List["SubscriptionResponse"] = []
    visits_count: int = 0


# === Subscription Schemas ===
class SubscriptionBase(BaseModel):
    name: str = Field(..., max_length=100)
    visits_total: int = Field(..., ge=1)
    price: float = Field(..., ge=0)  # Исправлено: price теперь обязательный float
    comment: Optional[str] = None


class SubscriptionCreate(SubscriptionBase):
    client_id: int
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class SubscriptionUpdate(BaseModel):
    name: Optional[str] = None
    visits_left: Optional[int] = None
    status: Optional[SubscriptionStatusEnum] = None
    comment: Optional[str] = None
    frozen_at: Optional[datetime] = None
    unfrozen_at: Optional[datetime] = None


class SubscriptionResponse(SubscriptionBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    client_id: int
    visits_left: int
    status: SubscriptionStatusEnum
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    frozen_at: Optional[datetime] = None
    created_at: datetime


# === Visit Schemas ===
class VisitBase(BaseModel):
    visit_date: datetime
    visit_type: VisitTypeEnum = VisitTypeEnum.GROUP
    class_name: Optional[str] = Field(None, max_length=100)
    trainer: Optional[str] = Field(None, max_length=100)
    hall: Optional[str] = Field(None, max_length=50)
    comment: Optional[str] = None


class VisitCreate(VisitBase):
    client_id: int
    subscription_id: Optional[int] = None


class VisitUpdate(BaseModel):
    visit_type: Optional[VisitTypeEnum] = None
    class_name: Optional[str] = None
    trainer: Optional[str] = None
    hall: Optional[str] = None
    comment: Optional[str] = None


class VisitResponse(VisitBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    client_id: int
    subscription_id: Optional[int] = None
    created_at: datetime


# === Dashboard Schemas ===
class DashboardStats(BaseModel):
    total_clients: int
    active_clients: int
    active_subscriptions: int
    visits_today: int
    visits_this_week: int
    revenue_today: float
    revenue_this_month: float


# === Telegram Schemas ===
class TelegramWebhook(BaseModel):
    update_id: int
    message: Optional[dict] = None
    callback_query: Optional[dict] = None


# ============================================
# НОВЫЕ СХЕМЫ: Финансы, Расписание, Обратная связь, Аналитика
# ============================================

# === Payment Schemas ===
class PaymentBase(BaseModel):
    amount: float = Field(..., gt=0)
    method: PaymentMethodEnum = PaymentMethodEnum.CASH
    comment: Optional[str] = None


class PaymentCreate(PaymentBase):
    client_id: int
    subscription_id: Optional[int] = None


class PaymentUpdate(BaseModel):
    status: Optional[PaymentStatusEnum] = None
    comment: Optional[str] = None


class PaymentResponse(PaymentBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    client_id: int
    subscription_id: Optional[int] = None
    status: PaymentStatusEnum
    payment_date: datetime
    created_at: datetime


# === Expense Schemas ===
class ExpenseBase(BaseModel):
    category: ExpenseCategoryEnum
    amount: float = Field(..., gt=0)
    description: str = Field(..., min_length=1, max_length=500)
    expense_date: Optional[datetime] = None
    receipt_number: Optional[str] = Field(None, max_length=100)


class ExpenseCreate(ExpenseBase):
    pass


class ExpenseUpdate(BaseModel):
    category: Optional[ExpenseCategoryEnum] = None
    amount: Optional[float] = Field(None, gt=0)
    description: Optional[str] = None
    receipt_number: Optional[str] = None


class ExpenseResponse(ExpenseBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_by_id: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


# === Schedule Schemas ===
class ScheduleBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    hall: str = Field(..., min_length=1, max_length=50)
    start_time: datetime
    end_time: datetime
    max_participants: int = Field(default=15, ge=1)
    price: Optional[float] = Field(None, ge=0)


class ScheduleCreate(ScheduleBase):
    trainer_id: Optional[int] = None


class ScheduleUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    hall: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    max_participants: Optional[int] = Field(None, ge=1)
    status: Optional[ScheduleStatusEnum] = None
    price: Optional[float] = None


class ScheduleResponse(ScheduleBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    trainer_id: Optional[int] = None
    trainer_name: Optional[str] = None
    status: ScheduleStatusEnum
    enrolled_count: int = 0
    has_waitlist: bool = False
    created_at: datetime
    updated_at: Optional[datetime] = None


# === Enrollment Schemas ===
class EnrollmentBase(BaseModel):
    status: EnrollmentStatusEnum = EnrollmentStatusEnum.ENROLLED


class EnrollmentCreate(EnrollmentBase):
    schedule_id: int
    client_id: int
    subscription_id: Optional[int] = None


class EnrollmentUpdate(BaseModel):
    status: Optional[EnrollmentStatusEnum] = None
    attended: Optional[bool] = None


class EnrollmentResponse(EnrollmentBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    schedule_id: int
    client_id: int
    subscription_id: Optional[int] = None
    attended: bool
    created_at: datetime
    updated_at: Optional[datetime] = None


class EnrollmentWithDetails(EnrollmentResponse):
    schedule_title: Optional[str] = None
    schedule_start_time: Optional[datetime] = None
    client_name: Optional[str] = None


# === Feedback Schemas ===
class FeedbackBase(BaseModel):
    feedback_type: FeedbackTypeEnum
    rating: Optional[int] = Field(None, ge=1, le=5)
    nps_score: Optional[int] = Field(None, ge=0, le=10)
    title: Optional[str] = Field(None, max_length=200)
    comment: Optional[str] = None


class FeedbackCreate(FeedbackBase):
    client_id: int
    schedule_id: Optional[int] = None


class FeedbackUpdate(BaseModel):
    is_resolved: Optional[bool] = None
    comment: Optional[str] = None


class FeedbackResponse(FeedbackBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    client_id: int
    schedule_id: Optional[int] = None
    is_resolved: Optional[bool] = None
    resolved_at: Optional[datetime] = None
    created_at: datetime


class FeedbackWithDetails(FeedbackResponse):
    client_name: Optional[str] = None
    schedule_title: Optional[str] = None


# === Notification Schemas ===
class NotificationBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    message: str = Field(..., min_length=1)
    notification_type: str = "info"


class NotificationCreate(NotificationBase):
    client_id: int


class NotificationResponse(NotificationBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    client_id: int
    is_sent: bool
    sent_at: Optional[datetime] = None
    created_at: datetime


# === Analytics & Reports Schemas ===
class RevenueReport(BaseModel):
    """Отчёт по доходам"""
    total_revenue: float
    total_expenses: float
    profit: float
    period_start: datetime
    period_end: datetime
    by_payment_method: dict = {}
    by_expense_category: dict = {}


class TrainerPerformance(BaseModel):
    """Эффективность тренера"""
    trainer_id: int
    trainer_name: str
    total_classes: int
    total_clients: int
    average_rating: Optional[float] = None
    total_revenue: float = 0


class ClientChurnReport(BaseModel):
    """Отчёт по оттоку клиентов"""
    client_id: int
    client_name: str
    phone: str
    last_visit_date: Optional[datetime] = None
    days_since_last_visit: int
    total_visits: int
    has_active_subscription: bool


class RFMClient(BaseModel):
    """RFM-сегментация клиента"""
    client_id: int
    client_name: str
    recency_score: int  # 1-5
    frequency_score: int  # 1-5
    monetary_score: int  # 1-5
    rfm_segment: str  # Champions, Loyal, At Risk, etc.
    total_visits: int
    total_spent: float
    last_visit_date: Optional[datetime] = None


class DashboardMetrics(BaseModel):
    """Расширенные метрики дашборда"""
    # Основные метрики
    total_clients: int
    active_clients: int
    new_clients_today: int
    total_revenue_today: float
    total_expenses_today: float
    
    # Подписки
    active_subscriptions: int
    expiring_soon: int  # Истекают в ближайшие 7 дней
    
    # Посещения
    visits_today: int
    visits_this_week: int
    average_attendance_rate: float  # Средний % посещаемости
    
    # Расписание
    upcoming_classes: int
    waitlist_count: int  # Всего в листах ожидания
    
    # Финансы
    revenue_this_week: float
    revenue_this_month: float
    expenses_this_week: float
    expenses_this_month: float
    profit_this_month: float
    
    # Конверсия
    conversion_rate: float  # Заявка -> покупка


class SubscriptionSalesReport(BaseModel):
    """Отчёт по продажам абонементов"""
    subscription_name: str
    total_sold: int
    total_revenue: float
    average_price: float
    period_start: datetime
    period_end: datetime


# === Lead Schemas (Заявки с сайта) ===
class LeadCreate(BaseModel):
    """Создание заявки с сайта"""
    name: str = Field(..., min_length=2, max_length=100)
    phone: str = Field(..., min_length=10, max_length=20)
    program: Optional[str] = "classic"
    message: Optional[str] = None
    source: Optional[str] = "website"


class LeadUpdate(BaseModel):
    """Обновление заявки"""
    status: Optional[str] = None  # new, contacted, converted, rejected
    message: Optional[str] = None
    client_id: Optional[int] = None


class LeadResponse(BaseModel):
    """Ответ с данными заявки"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    phone: str
    program: Optional[str] = None
    message: Optional[str] = None
    source: Optional[str] = None
    status: str
    client_id: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


# === Update all forward references ===
ClientWithSubscriptions.model_rebuild()
