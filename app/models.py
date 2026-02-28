"""
ORM-модели для базы данных Zumba CRM
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Enum, Float, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.database import Base


class UserRole(str, enum.Enum):
    """Роли пользователей"""
    ADMIN = "admin"
    TRAINER = "trainer"


class SubscriptionStatus(str, enum.Enum):
    """Статусы абонемента"""
    ACTIVE = "active"
    FROZEN = "frozen"
    EXPIRED = "expired"
    ARCHIVED = "archived"


class VisitType(str, enum.Enum):
    """Типы посещений"""
    GROUP = "group"  # Групповое занятие
    INDIVIDUAL = "individual"  # Индивидуальное занятие
    TRIAL = "trial"  # Пробное занятие


class PaymentStatus(str, enum.Enum):
    """Статусы платежа"""
    PENDING = "pending"  # Ожидает оплаты
    COMPLETED = "completed"  # Оплачен
    FAILED = "failed"  # Не удался
    REFUNDED = "refunded"  # Возвращён


class PaymentMethod(str, enum.Enum):
    """Способ оплаты"""
    CASH = "cash"  # Наличные
    CARD = "card"  # Карта
    ONLINE = "online"  # Онлайн
    TRANSFER = "transfer"  # Перевод


class ExpenseCategory(str, enum.Enum):
    """Категории расходов"""
    RENT = "rent"  # Аренда
    SALARY = "salary"  # Зарплаты
    UTILITIES = "utilities"  # Коммунальные услуги
    MARKETING = "marketing"  # Маркетинг
    EQUIPMENT = "equipment"  # Оборудование
    SUPPLIES = "supplies"  # Расходные материалы
    TAXES = "taxes"  # Налоги
    OTHER = "other"  # Прочее


class ScheduleStatus(str, enum.Enum):
    """Статус расписания"""
    ACTIVE = "active"  # Активно
    CANCELLED = "cancelled"  # Отменено
    COMPLETED = "completed"  # Завершено


class FeedbackType(str, enum.Enum):
    """Типы обратной связи"""
    RATING = "rating"  # Оценка
    NPS = "nps"  # NPS опрос
    COMPLAINT = "complaint"  # Жалоба
    SUGGESTION = "suggestion"  # Предложение


class User(Base):
    """Пользователь системы (админ или тренер)"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.TRAINER, nullable=False)
    full_name = Column(String(100), nullable=True)
    phone = Column(String(20), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    
    # Связи
    created_clients = relationship("Client", back_populates="created_by", foreign_keys="Client.created_by_id")
    
    def __repr__(self):
        return f"<User {self.username}>"


class Client(Base):
    """Клиент фитнес-студии"""
    __tablename__ = "clients"
    
    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=True)
    phone = Column(String(20), unique=True, index=True, nullable=False)
    telegram = Column(String(50), nullable=True)
    whatsapp = Column(String(50), nullable=True)
    email = Column(String(100), nullable=True)
    comment = Column(Text, nullable=True)
    source = Column(String(50), default="website", nullable=True)  # website, telegram, instagram
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Связи
    subscriptions = relationship("Subscription", back_populates="client", cascade="all, delete-orphan")
    visits = relationship("Visit", back_populates="client", cascade="all, delete-orphan")
    created_by = relationship("User", back_populates="created_clients", foreign_keys=[created_by_id])
    
    @property
    def full_name(self):
        """Полное имя клиента"""
        return f"{self.last_name} {self.first_name}".strip()
    
    def __repr__(self):
        return f"<Client {self.full_name}>"


class Subscription(Base):
    """Абонемент клиента"""
    __tablename__ = "subscriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    name = Column(String(100), nullable=False)  # "4 занятия", "8 занятий", "Безлимит"
    visits_total = Column(Integer, nullable=False)  # Общее количество занятий
    visits_left = Column(Integer, nullable=False)  # Осталось занятий
    price = Column(Float, nullable=True)  # Цена абонемента
    status = Column(Enum(SubscriptionStatus), default=SubscriptionStatus.ACTIVE, nullable=False)
    start_date = Column(DateTime(timezone=True), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=True)
    frozen_at = Column(DateTime(timezone=True), nullable=True)
    unfrozen_at = Column(DateTime(timezone=True), nullable=True)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    
    # Связи
    client = relationship("Client", back_populates="subscriptions")
    visits = relationship("Visit", back_populates="subscription", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Subscription {self.name} for Client {self.client_id}>"


class Visit(Base):
    """Посещение занятия клиентом"""
    __tablename__ = "visits"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=True)
    visit_date = Column(DateTime(timezone=True), nullable=False)
    visit_type = Column(Enum(VisitType), default=VisitType.GROUP, nullable=False)
    class_name = Column(String(100), nullable=True)  # Название занятия
    trainer = Column(String(100), nullable=True)  # Тренер
    hall = Column(String(50), nullable=True)  # Зал
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Связи
    client = relationship("Client", back_populates="visits")
    subscription = relationship("Subscription", back_populates="visits")

    def __repr__(self):
        return f"<Visit {self.client_id} on {self.visit_date}>"


# ============================================
# НОВЫЕ МОДЕЛИ: Финансы, Расписание, Обратная связь
# ============================================

class Payment(Base):
    """Платеж клиента"""
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=True)
    amount = Column(Float, nullable=False)  # Сумма платежа
    method = Column(Enum(PaymentMethod), default=PaymentMethod.CASH, nullable=False)
    status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False)
    payment_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Связи
    client = relationship("Client", backref="payments")
    subscription = relationship("Subscription", backref="payments")

    def __repr__(self):
        return f"<Payment {self.amount} for Client {self.client_id}>"


class Expense(Base):
    """Расход студии"""
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(Enum(ExpenseCategory), nullable=False)
    amount = Column(Float, nullable=False)
    description = Column(Text, nullable=False)
    expense_date = Column(DateTime(timezone=True), nullable=False)
    receipt_number = Column(String(100), nullable=True)  # Номер чека/документа
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    # Связи
    created_by = relationship("User", backref="expenses")

    def __repr__(self):
        return f"<Expense {self.amount} - {self.category}>"


class Schedule(Base):
    """Расписание занятий"""
    __tablename__ = "schedules"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(100), nullable=False)  # Название занятия
    description = Column(Text, nullable=True)
    trainer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    hall = Column(String(50), nullable=False)  # Зал
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    max_participants = Column(Integer, default=15, nullable=False)  # Максимум участников
    status = Column(Enum(ScheduleStatus), default=ScheduleStatus.ACTIVE, nullable=False)
    price = Column(Float, nullable=True)  # Цена за занятие (если разовое)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    # Связи
    trainer = relationship("User", backref="scheduled_classes")
    enrollments = relationship("Enrollment", back_populates="schedule", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Schedule {self.title} at {self.start_time}>"


class Enrollment(Base):
    """Запись клиента на занятие"""
    __tablename__ = "enrollments"

    id = Column(Integer, primary_key=True, index=True)
    schedule_id = Column(Integer, ForeignKey("schedules.id"), nullable=False)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=True)
    status = Column(String(20), default="enrolled", nullable=False)  # enrolled, cancelled, completed, waitlist
    attended = Column(Boolean, default=False, nullable=False)  # Посетил ли занятие
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    # Связи
    schedule = relationship("Schedule", back_populates="enrollments")
    client = relationship("Client", backref="enrollments")
    subscription = relationship("Subscription", backref="enrollments")

    def __repr__(self):
        return f"<Enrollment Client {self.client_id} for Schedule {self.schedule_id}>"


class Feedback(Base):
    """Обратная связь от клиентов"""
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    schedule_id = Column(Integer, ForeignKey("schedules.id"), nullable=True)
    feedback_type = Column(Enum(FeedbackType), nullable=False)
    rating = Column(Integer, nullable=True)  # Оценка 1-5
    nps_score = Column(Integer, nullable=True)  # NPS 0-10
    title = Column(String(200), nullable=True)  # Заголовок (для жалоб/предложений)
    comment = Column(Text, nullable=True)
    is_resolved = Column(Boolean, default=False, nullable=True)  # Для жалоб/предложений
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Связи
    client = relationship("Client", backref="feedback")
    schedule = relationship("Schedule", backref="feedback")

    def __repr__(self):
        return f"<Feedback {self.feedback_type} from Client {self.client_id}>"


class Notification(Base):
    """Уведомления для клиентов"""
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    notification_type = Column(String(50), default="info", nullable=False)  # info, reminder, promo, birthday
    is_sent = Column(Boolean, default=False, nullable=False)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Связи
    client = relationship("Client", backref="notifications")

    def __repr__(self):
        return f"<Notification for Client {self.client_id}>"


class Lead(Base):
    """Заявка с сайта"""
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=False)
    program = Column(String(50), default="classic", nullable=True)  # classic, gold
    message = Column(Text, nullable=True)
    source = Column(String(50), default="website", nullable=True)  # website, instagram, vk
    status = Column(String(20), default="new", nullable=False)  # new, contacted, converted, rejected
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    # Связи
    client = relationship("Client", backref="leads")

    def __repr__(self):
        return f"<Lead {self.name} - {self.phone}>"
