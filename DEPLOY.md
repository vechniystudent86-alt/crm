# 🚀 Деплой Zumba CRM на Beget VPS

## 📋 Требования

- Аккаунт на [Beget.com](https://beget.com)
- VPS тариф (от 210₽/мес)
- Домен (опционально, можно использовать IP)

---

## 1️⃣ Создание VPS на Beget

### Шаг 1.1: Регистрация и вход
1. Зарегистрируйтесь на [beget.com](https://beget.com)
2. Войдите в панель управления

### Шаг 1.2: Создание VPS
1. Перейдите в раздел **VPS/VDS**
2. Нажмите **Создать VPS**
3. Выберите конфигурацию:
   - **CPU**: 1 ядро
   - **RAM**: 1 ГБ
   - **Диск**: 10 ГБ NVMe
   - **ОС**: Ubuntu 24.04
4. Нажмите **Создать** (~10 секунд)

### Шаг 1.3: Получение доступа
1. После создания запишите:
   - **IP-адрес сервера**
   - **Логин**: `root`
   - **Пароль** (придёт на email или отобразится в панели)

---

## 2️⃣ Подготовка сервера

### Шаг 2.1: Подключение по SSH

**Windows (PowerShell):**
```powershell
ssh root@ваш-ip-адрес
```

**Linux/Mac:**
```bash
ssh root@ваш-ip-адрес
```

Введите пароль при подключении.

### Шаг 2.2: Обновление системы
```bash
apt update && apt upgrade -y
```

### Шаг 2.3: Установка Docker
```bash
# Установка Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Добавление пользователя в группу docker
usermod -aG docker $USER

# Установка Docker Compose
apt install docker-compose -y
```

**Переподключитесь к SSH для применения изменений:**
```bash
exit
# Снова подключитесь
ssh root@ваш-ip-адрес
```

### Шаг 2.4: Установка Git
```bash
apt install git -y
```

---

## 3️⃣ Развёртывание приложения

### Шаг 3.1: Клонирование репозитория

**Вариант A: GitHub**
```bash
cd /root
git clone https://github.com/your-username/zumba-crm.git
cd zumba-crm
```

**Вариант B: Загрузка файлов**
```bash
# Создайте директорию
mkdir -p /root/zumba-crm
# Загрузите файлы через SFTP (FileZilla, WinSCP)
```

### Шаг 3.2: Настройка окружения
```bash
cd /root/zumba-crm

# Копирование примера
cp .env.example .env

# Редактирование
nano .env
```

**Заполните .env:**
```env
# Приложение
APP_NAME=Zumba CRM
DEBUG=False

# База данных
DATABASE_URL=sqlite+aiosqlite:///./data/crm.db

# JWT (сгенерируйте случайные строки!)
SECRET_KEY=your-super-secret-key-min-32-chars
JWT_SECRET_KEY=your-jwt-secret-key-min-32-chars
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Админ по умолчанию
ADMIN_USERNAME=admin
ADMIN_PASSWORD=YourSecurePassword123!

# Telegram Bot (получите у @BotFather)
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_WEBHOOK_SECRET=your-webhook-secret
```

**Сохранение в nano:**
- `Ctrl+O` → `Enter` (сохранить)
- `Ctrl+X` (выйти)

### Шаг 3.3: Создание директорий
```bash
mkdir -p data ssl
```

### Шаг 3.4: Запуск через Docker Compose
```bash
docker compose up -d
```

**Проверка статуса:**
```bash
docker compose ps
```

**Просмотр логов:**
```bash
docker compose logs -f app
```

---

## 4️⃣ Настройка HTTPS (SSL)

### Вариант A: Let's Encrypt (бесплатно)

```bash
# Установка Certbot
apt install certbot python3-certbot-nginx -y

# Получение сертификата
certbot certonly --standalone -d ваш-домен.ru

# Копирование сертификатов
cp /etc/letsencrypt/live/ваш-домен.ru/fullchain.pem /root/zumba-crm/ssl/
cp /etc/letsencrypt/live/ваш-домен.ru/privkey.pem /root/zumba-crm/ssl/

# Перезапуск Nginx
docker compose restart nginx
```

### Вариант B: Самоподписанный сертификат (для тестов)
```bash
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /root/zumba-crm/ssl/privkey.pem \
  -out /root/zumba-crm/ssl/fullchain.pem \
  -subj "/C=RU/ST=Saint Petersburg/L=SPb/O=Zumba/CN=ваш-ip"

docker compose restart nginx
```

---

## 5️⃣ Проверка работы

### Шаг 5.1: Открытие в браузере
```
http://ваш-ip-адрес
http://ваш-ip-аpecies:8000/docs
```

### Шаг 5.2: Вход в систему
- **Логин**: `admin`
- **Пароль**: тот, что указали в `.env`

---

## 6️⃣ Настройка Telegram Webhook

### Шаг 6.1: Получение токена бота
1. Откройте @BotFather в Telegram
2. Создайте нового бота: `/newbot`
3. Скопируйте токен

### Шаг 6.2: Установка webhook
```bash
# Замените на ваш домен/IP
WEBHOOK_URL="https://ваш-домен.ru/api/telegram/webhook"

curl -X POST "https://api.telegram.org/botВАШ_ТОКЕН/setWebhook" \
  -d "url=$WEBHOOK_URL"
```

---

## 7️⃣ Автоматический перезапуск

Docker Compose уже настроил автоматический перезапуск:
```yaml
restart: unless-stopped
```

**Проверка:**
```bash
docker update --restart=unless-stopped zumba-crm-app zumba-crm-nginx
```

---

## 8️⃣ Резервное копирование

### Создание бэкапа
```bash
# Бэкап базы данных
docker exec zumba-crm-app cp /app/data/crm.db /tmp/crm.db
docker cp zumba-crm-app:/tmp/crm.db ./backups/crm-$(date +%Y%m%d).db

# Бэкап .env
cp .env ./backups/env-$(date +%Y%m%d).bak
```

### Автоматизация (cron)
```bash
crontab -e

# Добавить строку (бэкап каждый день в 3:00)
0 3 * * * cd /root/zumba-crm && docker exec zumba-crm-app cp /app/data/crm.db /tmp/crm.db && docker cp zumba-crm-app:/tmp/crm.db ./backups/crm-$(date +\%Y\%m\%d).db
```

---

## 9️⃣ Мониторинг

### Просмотр логов
```bash
# Логи приложения
docker compose logs -f app

# Логи Nginx
docker compose logs -f nginx

# Использование ресурсов
docker stats
```

### Проверка доступности
```bash
curl http://localhost:8000
curl http://localhost:8000/docs
```

---

## 🔗 Полезные команды

| Команда | Описание |
|---------|----------|
| `docker compose up -d` | Запуск контейнеров |
| `docker compose down` | Остановка контейнеров |
| `docker compose restart` | Перезапуск |
| `docker compose logs -f` | Просмотр логов |
| `docker compose ps` | Статус контейнеров |
| `docker exec -it zumba-crm-app bash` | Вход в контейнер |
| `docker system prune -a` | Очистка места |

---

## ⚠️ Решение проблем

### Ошибка: "Address already in use"
```bash
# Проверка занятых портов
netstat -tulpn | grep :80

# Остановка конфликтующего сервиса
systemctl stop apache2
# или
docker stop $(docker ps -q)
```

### Ошибка: "Cannot connect to Docker daemon"
```bash
systemctl restart docker
```

### Приложение не запускается
```bash
# Проверка логов
docker compose logs app

# Проверка .env
cat .env

# Пересоздание контейнера
docker compose down
docker compose up -d --build
```

---

## 📞 Поддержка Beget

- **Телефон**: 8 (800) 700-06-08
- **Email**: sales@beget.com
- **Чат**: в панели управления

---

## 🎯 Следующие шаги

1. ✅ Настроить домен (если есть)
2. ✅ Подключить Telegram-бота
3. ✅ Добавить первых клиентов
4. ✅ Обучить персонал
5. ✅ Настроить автоматические бэкапы

**Готово! Ваша CRM работает! 🎉**
