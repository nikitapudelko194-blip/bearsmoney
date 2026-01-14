# 🚀 Быстрый Старт - BearsMoney Bot

## За 5 Минут До Первого Запуска

### 1️⃣ Создайте Telegram Бота

```
1. Откройте @BotFather в Telegram
2. Напишите: /newbot
3. Следуйте инструкциям и получите BOT_TOKEN
4. Сохраните токен - он нужен для .env файла
```

### 2️⃣ Найдите Ваш Admin ID

```
1. Откройте @userinfobot в Telegram
2. Отправьте сообщение
3. Скопируйте Your user id - это ADMIN_ID
```

### 3️⃣ Установите PostgreSQL (Локально)

**Linux/Mac:**
```bash
brew install postgresql
psql -U postgres
CREATE DATABASE bearsmoney;
```

**Windows:**
- Скачайте установщик: https://www.postgresql.org/download/windows/
- Установите с паролем по умолчанию: `postgres`
- Откройте pgAdmin и создайте БД `bearsmoney`

**Docker:**
```bash
docker run -d \
  --name bearsmoney_db \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=bearsmoney \
  -p 5432:5432 \
  postgres:15-alpine
```

### 4️⃣ Установите Redis

**Linux/Mac:**
```bash
brew install redis
redis-server
```

**Docker:**
```bash
docker run -d \
  --name bearsmoney_redis \
  -p 6379:6379 \
  redis:7-alpine
```

### 5️⃣ Клонируйте и Настройте

```bash
# Клонируйте репозиторий
git clone https://github.com/nikitapudelko194-blip/bearsmoney.git
cd bearsmoney

# Создайте виртуальное окружение
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows

# Установите зависимости
pip install -r requirements.txt

# Создайте .env файл
cp .env.example .env
```

### 6️⃣ Отредактируйте .env

```env
# Обязательные параметры
BOT_TOKEN=123456789:ABCdEfGhIjKlMnOpQrStUvWxYz
ADMIN_ID=123456789

# Если используете локальный PostgreSQL
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/bearsmoney

# Если используете локальный Redis  
REDIS_URL=redis://localhost:6379

# Остальное можно оставить по умолчанию
DEBUG=True
LOG_LEVEL=INFO
```

### 7️⃣ Запустите Бота

```bash
python main.py
```

✅ Готово! Бот должен быть запущен!

---

## 🐳 Альтернатива: Docker Compose (Все Сразу)

```bash
# Скопируйте .env
cp .env.example .env

# Отредактируйте .env (добавьте BOT_TOKEN и ADMIN_ID)

# Запустите все сервисы
docker-compose -f docker/docker-compose.yml up -d

# Проверьте логи
docker-compose -f docker/docker-compose.yml logs -f bot
```

---

## 📱 Тестирование Бота

```
1. Откройте Telegram
2. Найдите своего бота
3. Напишите /start
4. Бот должен зарегистрировать вас и дать 100 коинов
5. Используйте кнопки меню для навигации
```

---

## 🔧 Основные Команды для Разработки

```bash
# Просмотреть логи
tail -f logs/bot.log

# Запустить тесты
pytest tests/

# Форматировать код
black app/

# Проверить линтер
flake8 app/

# Остановить бота
Ctrl+C

# Деактивировать виртуальное окружение
deactivate
```

---

## 🐛 Типичные Ошибки

### "No module named 'sqlalchemy'"
```bash
# Забыли установить зависимости
pip install -r requirements.txt
```

### "Connection refused" (PostgreSQL)
```bash
# PostgreSQL не запущен
psql -U postgres  # Если не подключиться, БД не работает
# или
docker ps  # Если используете Docker
```

### "redis.exceptions.ConnectionError"
```bash
# Redis не запущен
redis-cli ping  # Должен вернуть PONG
```

### "BOT_TOKEN not found"
```bash
# Забыли добавить BOT_TOKEN в .env
cat .env | grep BOT_TOKEN  # Проверить наличие
```

---

## 📚 Дальнейшие Шаги

1. **Изучите код:**
   - `app/handlers/start.py` - пример обработчика команды
   - `app/database/models.py` - структура БД
   - `app/services/economy.py` - бизнес-логика

2. **Добавьте новые команды:**
   - Создайте файл в `app/handlers/`
   - Определите обработчик
   - Зарегистрируйте в `app/bot.py`

3. **Развертывание на сервер:**
   - Используйте VPS (DigitalOcean, Linode, etc.)
   - Установите Docker
   - Используйте Docker Compose

---

## 📞 Поддержка

Если что-то не сработало:
1. Проверьте файл `.env`
2. Посмотрите в `logs/bot.log`
3. Создайте issue на GitHub

---

**Успехов в разработке! 🚀**
