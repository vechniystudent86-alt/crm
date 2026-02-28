# Интеграция формы с сайтом и CRM

## 📋 Обзор

Заявки с сайта теперь:
1. **Отправляются в Telegram** — мгновенное уведомление
2. **Сохраняются в CRM** — для последующей обработки менеджерами
3. **Автоматически создают клиента** — если телефон новый

---

## 🔧 Настройка на сайте

### 1. Конфигурационные файлы

Создайте/обновите файлы в папке `zumba-site/config/`:

```bash
zumba-site/config/
├── telegram_token.txt    # Токен Telegram бота
├── telegram_chat_id.txt  # Ваш Chat ID для уведомлений
└── crm_url.txt          # URL CRM API для заявок
```

### 2. CRM URL

**Для локальной разработки:**
```
http://localhost:8000/api/leads
```

**Для продакшена:**
```
https://crm.zumba-spb.ru/api/leads
```

### 3. Проверка работы

1. Откройте сайт: `http://localhost/zumba-site/`
2. Заполните форму заявки
3. Проверьте:
   - Сообщение в Telegram
   - Заявку в CRM: `http://localhost:8000/docs` → `POST /api/leads`

---

## 🎯 Как это работает

### Поток заявки:

```
[Клиент заполняет форму на сайте]
         ↓
[send-form.php обрабатывает данные]
         ↓
    ┌────┴────┐
    ↓         ↓
[Telegram]  [CRM API]
    ↓         ↓
[Уведомление] [Сохранение в БД + создание клиента]
```

### Автоматическое создание клиента

Если телефон клиента не найден в базе:
- ✅ Создаётся новый клиент в таблице `clients`
- ✅ Заявка связывается с клиентом через `client_id`
- ✅ Источник указывается `website`

Если клиент уже существует:
- ✅ Заявка привязывается к существующему клиенту

---

## 📊 API Endpoints

### Создать заявку (без аутентификации)

**POST** `/api/leads`

```json
{
  "name": "Иван Иванов",
  "phone": "+79991234567",
  "program": "classic",
  "message": "Хочу на пробное занятие",
  "source": "website"
}
```

**Ответ:**
```json
{
  "id": 1,
  "name": "Иван Иванов",
  "phone": "+79991234567",
  "program": "classic",
  "message": "Хочу на пробное занятие",
  "source": "website",
  "status": "new",
  "client_id": 42,
  "created_at": "2026-02-28T10:00:00Z"
}
```

### Получить все заявки (требуется авторизация)

**GET** `/api/leads/?skip=0&limit=50&status=new`

Параметры:
- `skip` — пропустить N записей
- `limit` — количество записей (макс. 200)
- `status` — фильтр по статусу (`new`, `contacted`, `converted`, `rejected`)
- `source` — фильтр по источнику (`website`, `instagram`, `vk`)

### Обновить заявку

**PATCH** `/api/leads/{id}`

```json
{
  "status": "contacted"
}
```

Статусы:
- `new` — новая заявка
- `contacted` — связались с клиентом
- `converted` — клиент купил абонемент
- `rejected` — отказ/недозвон

### Статистика по заявкам

**GET** `/api/leads/stats/summary`

```json
{
  "total_count": 150,
  "by_status": {
    "new": 10,
    "contacted": 5,
    "converted": 130,
    "rejected": 5
  },
  "by_source": {
    "website": 120,
    "instagram": 20,
    "vk": 10
  },
  "new_today": 5
}
```

---

## 💡 Обработка заявок в CRM

### 1. Просмотр новых заявок

1. Откройте Swagger UI: `http://localhost:8000/docs`
2. Авторизуйтесь (`/api/auth/login`)
3. Перейдите к `/api/leads/`
4. Отфильтруйте по `status=new`

### 2. Обработка заявки

1. Позвоните клиенту
2. Обновите статус: `PATCH /api/leads/{id}`
   - Установите `status: "contacted"`
3. После покупки абонемента:
   - Создайте клиента (если нет)
   - Создайте абонемент
   - Обновите заявку: `status: "converted"`

### 3. Конвертация в клиента

Заявка автоматически создаёт клиента при первом обращении.

Для связи заявки с существующим клиентом:
```json
PATCH /api/leads/{id}
{
  "client_id": 42
}
```

---

## 🔍 Отладка

### Логи PHP

```bash
# Linux/Mac
tail -f /var/log/php/form_errors.log

# Windows (если настроено)
C:\path\to\php\logs\php_error_log
```

### Проверка CRM логов

```bash
# В консоли сервера
docker logs crm-backend

# Или напрямую
tail -f crm-backend/logs/app.log
```

### Тестирование отправки

```bash
# Тестовый запрос в CRM
curl -X POST http://localhost:8000/api/leads \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Тест Тестов",
    "phone": "+79990000000",
    "program": "classic",
    "message": "Тестовая заявка"
  }'
```

---

## 🚀 Деплой на продакшен

### 1. Обновите `config/crm_url.txt`

```
https://crm.zumba-spb.ru/api/leads
```

### 2. Настройте CORS в CRM

В `app/main.py`:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://zumba-spb.ru"],  # Ваш домен
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 3. Проверьте права доступа

Убедитесь, что PHP имеет доступ к:
- `config/` файлам
- Логам

### 4. Тестирование

1. Заполните форму на реальном сайте
2. Проверьте Telegram
3. Проверьте CRM

---

## 📈 Метрики и аналитика

### Конверсия по заявкам

```sql
-- Процент конверсии из заявки в клиента
SELECT 
    COUNT(*) as total_leads,
    SUM(CASE WHEN status = 'converted' THEN 1 ELSE 0 END) as converted,
    ROUND(SUM(CASE WHEN status = 'converted' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as conversion_rate
FROM leads;
```

### Заявки по источникам

```sql
SELECT 
    source,
    COUNT(*) as count,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM leads), 2) as percentage
FROM leads
GROUP BY source;
```

---

## ❓ FAQ

### Заявки не приходят в CRM

1. Проверьте `config/crm_url.txt`
2. Убедитесь, что CRM сервер запущен
3. Проверьте логи PHP

### Клиент дублируется

Проверьте уникальность телефона в базе:
```sql
SELECT phone, COUNT(*) 
FROM clients 
GROUP BY phone 
HAVING COUNT(*) > 1;
```

### Как изменить статусы заявок?

В `app/models.py` найдите `Lead.status` и обновите допустимые значения.

---

## 📞 Поддержка

При проблемах:
1. Проверьте логи
2. Протестируйте API через Swagger
3. Убедитесь, что токены Telegram актуальны
