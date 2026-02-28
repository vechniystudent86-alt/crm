# Zumba CRM

CRM-система для фитнес-студии Zumba.

## Функционал

- 📊 Дашборд с посещаемостью и заявками
- 👥 База клиентов с абонементами
- 📅 Расписание занятий
- 💬 Интеграция с Telegram-ботом
- 🔐 Разграничение прав (админ/тренер)
- ✅ Соответствие 152-ФЗ

## Быстрый старт

### 1. Установка зависимостей

```bash
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
```

### 2. Настройка окружения

```bash
cp .env.example .env
# Отредактируйте .env, установите SECRET_KEY и TELEGRAM_BOT_TOKEN
```

### 3. Миграции БД

```bash
alembic upgrade head
```

### 4. Запуск

```bash
uvicorn app.main:app --reload
```

Откройте http://localhost:8000/docs для Swagger UI.

## Деплой на Beget VPS

См. инструкцию в [DEPLOY.md](DEPLOY.md)

## Структура проекта

```
crm-backend/
├── app/
│   ├── main.py           # Точка входа
│   ├── config.py         # Настройки
│   ├── database.py       # Подключение к БД
│   ├── models.py         # ORM-модели
│   ├── schemas.py        # Pydantic-схемы
│   ├── auth.py           # Аутентификация
│   └── routers/
│       ├── auth.py       # Логин/регистрация
│       ├── clients.py    # CRUD клиентов
│       ├── subscriptions.py # Абонементы
│       ├── visits.py     # Посещения
│       └── telegram.py   # Telegram webhook
├── frontend/
│   ├── index.html        # Дашборд
│   ├── clients.html      # Клиенты
│   └── ...
├── alembic/              # Миграции БД
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## API Endpoints

| Метод | Endpoint | Описание |
|-------|----------|----------|
| POST | /api/login | Аутентификация |
| GET | /api/users/me | Текущий пользователь |
| GET | /api/clients | Список клиентов |
| POST | /api/clients | Добавить клиента |
| GET | /api/clients/{id} | Карточка клиента |
| PUT | /api/clients/{id} | Редактировать клиента |
| GET | /api/subscriptions | Список абонементов |
| POST | /api/subscriptions | Создать абонемент |
| GET | /api/visits | Журнал посещений |
| POST | /api/visits | Добавить посещение |
| POST | /api/telegram/webhook | Telegram webhook |

## Технологии

- **Backend:** Python 3.11+, FastAPI, SQLAlchemy 2.0
- **Frontend:** HTML, HTMX, Alpine.js, Tailwind CSS
- **Database:** SQLite (dev) / PostgreSQL (prod)
- **Auth:** JWT, bcrypt
- **Deploy:** Docker, Docker Compose

## Лицензия

MIT
