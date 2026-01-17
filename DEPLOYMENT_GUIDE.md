# 🚀 BearsMoney - Полное руководство по развёртыванию

## 🎯 Статус реализации

### ✅ **РЕАЛИЗОВАНО:**

1. **✅ Ежедневные награды** (`app/handlers/daily_rewards.py`)
   - Система стриков (1-30 дней)
   - Увеличивающиеся награды
   - Колесо фортуны (раз в день)
   - Календарь наград

2. **✅ Premium подписка** (`app/handlers/premium.py`)
   - 3 тарифа: Basic, Premium, VIP
   - Бонусы: +50%/+100% доход, 0% комиссии
   - Авто-продление
   - Специальные бейджи

3. **✅ Реферальная система** (в models.py)
   - 3 уровня: 20%, 10%, 5%
   - Трекинг заработка
   - Статистика рефералов

4. **✅ Комиссия на обмен** (`app/handlers/exchange.py`)
   - 2% комиссия на Coins ↔ TON
   - Отображение в расчётах
   - Логирование транзакций

---

### 🚧 **ТРЕБУЕТ РЕАЛИЗАЦИИ:**

5. **🚧 NFT интеграция** (`app/handlers/nft.py` - не создан)
   - Конвертация медведей в NFT (TON)
   - P2P marketplace
   - Royalty 5%

6. **🚧 Внутриигровая реклама** (`app/handlers/ads.py` - не создан)
   - Просмотр видео за 100 Coins
   - Telegram Ads интеграция
   - Лимит 10/день

7. **🚧 Улучшения медведей** (`app/handlers/bear_upgrades.py` - не создан)
   - Апгрейды +10% за 1000 Coins
   - Специальные навыки (2x coins)
   - Эволюция (5 стадий)
   - Слияние (10 common = 1 rare)

8. **🚧 PvP батлы** (`app/handlers/pvp.py` - не создан)
   - Соревнования медведей
   - Ставки в Coins
   - Ранговая система
   - Лидерборд

9. **🚧 Аналитика** (`app/services/analytics.py` - не создан)
   - Tracking событий
   - Когортный анализ
   - A/B тестирование

10. **🚧 Пуш-уведомления** (`app/services/notifications.py` - не создан)
    - Уведомления о сборе Coins
    - Напоминания
    - Smart timing

11. **🚧 Backup система** (`scripts/backup.py` - не создан)
    - Автобэкапы каждые 6ч
    - Restore функционал

12. **🚧 Onboarding** (`app/handlers/tutorial.py` - не создан)
    - Интерактивный туториал
    - Награды за прохождение

13. **🚧 Партнёрства** (`app/handlers/partnerships.py` - не создан)
    - Кросс-промо
    - Спонсорские кейсы

---

## 🛠️ Критические исправления

### 1️⃣ **Регистрация handlers в bot.py**

**Проблема:** Новые handlers не зарегистрированы

**Решение:**

```python
# app/bot.py

def setup_handlers():
    from app.handlers import (
        start, bears, shop, profile, admin, 
        cases, exchange, payment,
        daily_rewards,  # ✅ НОВОЕ
        premium,        # ✅ НОВОЕ
    )
    
    dp.include_router(start.router)
    dp.include_router(bears.router)
    dp.include_router(shop.router)
    dp.include_router(profile.router)
    dp.include_router(exchange.router)
    dp.include_router(payment.router)
    dp.include_router(daily_rewards.router)  # ✅ НОВОЕ
    dp.include_router(premium.router)        # ✅ НОВОЕ
    dp.include_router(admin.router)
    dp.include_router(cases.router)
```

---

### 2️⃣ **Реферальные ссылки в start.py**

**Проблема:** Нет обработки `/start ref_12345`

**Решение:**

```python
# app/handlers/start.py

from aiogram.filters import CommandStart, CommandObject

@router.message(CommandStart(deep_link=True))
async def start_with_referral(message: Message, command: CommandObject):
    """
    Handle /start with referral code.
    """
    referral_code = command.args  # ref_12345
    
    if referral_code and referral_code.startswith('ref_'):
        referrer_id = int(referral_code.split('_')[1])
        
        # Check if referrer exists
        referrer = await session.execute(
            select(User).where(User.telegram_id == referrer_id)
        )
        referrer = referrer.scalar_one_or_none()
        
        if referrer and user.referred_by is None:
            user.referred_by = referrer.telegram_id
            referrer.referred_count += 1
            
            # Give bonus
            user.coins += 500
            referrer.coins += 500
            
            await session.commit()
```

---

### 3️⃣ **Миграция базы данных**

**Проблема:** Новые модели в models.py, но таблиц нет

**Решение:**

```bash
# На сервере
cd /path/to/bearsmoney

# Инициализация Alembic (если ещё не сделано)
pip install alembic
alembic init migrations

# Создать миграцию
alembic revision --autogenerate -m "Add daily_rewards and premium models"

# Применить
alembic upgrade head
```

**ИЛИ простой способ (для SQLite):**

```python
# В Python консоли на сервере
import asyncio
from app.database.models import Base
from app.database.db import engine

async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

asyncio.run(create_tables())
```

---

### 4️⃣ **Обработка ошибок в exchange.py**

**Проблема:** При сбое транзакция не откатывается

**Решение:**

```python
# app/handlers/exchange.py

try:
    async with get_session() as session:
        # ... вся логика обмена
        
        user.coins -= amount
        user.ton_balance += ton_amount
        
        await session.commit()
        
except Exception as e:
    await session.rollback()  # ✅ ОТКАТ ИЗМЕНЕНИЙ
    logger.error(f"❌ Exchange error: {e}", exc_info=True)
    await query.answer("❌ Ошибка обмена", show_alert=True)
```

---

### 5️⃣ **Rate Limiting**

**Проблема:** Спам запросов

**Решение:**

```python
# app/middlewares/rate_limit.py (новый файл)

from aiogram import BaseMiddleware
from typing import Callable, Awaitable, Dict, Any
from aiogram.types import Message, CallbackQuery
from datetime import datetime, timedelta

class RateLimitMiddleware(BaseMiddleware):
    def __init__(self, rate_limit: int = 3):
        self.rate_limit = rate_limit
        self.user_requests = {}
    
    async def __call__(
        self,
        handler: Callable[[Message | CallbackQuery, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        user_id = event.from_user.id
        now = datetime.now()
        
        # Check rate limit
        if user_id in self.user_requests:
            last_request, count = self.user_requests[user_id]
            if now - last_request < timedelta(seconds=1):
                if count >= self.rate_limit:
                    return  # Блокируем
                self.user_requests[user_id] = (last_request, count + 1)
            else:
                self.user_requests[user_id] = (now, 1)
        else:
            self.user_requests[user_id] = (now, 1)
        
        return await handler(event, data)

# В bot.py
from app.middlewares.rate_limit import RateLimitMiddleware

dp.message.middleware(RateLimitMiddleware(rate_limit=3))
dp.callback_query.middleware(RateLimitMiddleware(rate_limit=5))
```

---

## 🚀 Быстрый деплой

```bash
# 1. Получить обновления
cd /path/to/bearsmoney
git pull origin main

# 2. Установить зависимости (если есть новые)
pip install -r requirements.txt

# 3. Создать новые таблицы
python3 -c "import asyncio; from app.database.models import Base; from app.database.db import engine; asyncio.run(engine.begin().run_sync(Base.metadata.create_all))"

# 4. Перезапустить бота
sudo systemctl restart bearsmoney

# 5. Проверить логи
sudo journalctl -u bearsmoney -f
```

---

## 📊 Проверка работы

### Ежедневные награды:
1. Открыть бота
2. Нажать "🎉 Ежедневные награды"
3. Забрать награду
4. Крутить колесо фортуны

### Premium:
1. Нажать "⭐ Premium"
2. Выбрать Premium или VIP
3. Оплатить Coins или TON
4. Проверить бонусы в профиле

---

## 🔧 Трублшутинг

### Проблема: "Кнопки не работают"

```bash
# Проверить логи
sudo journalctl -u bearsmoney | grep "ERROR"

# Проверить регистрацию handlers
python3 -c "from app.bot import dp; print([r.name for r in dp.sub_routers])"
```

### Проблема: "БД не обновляется"

```bash
# Удалить старую БД (ОСТОРОЖНО!)
rm bearsmoney.db

# Создать новую
python3 -c "import asyncio; from app.database.models import Base; from app.database.db import engine; asyncio.run(engine.begin().run_sync(Base.metadata.create_all))"

# Перезапустить
sudo systemctl restart bearsmoney
```

---

## 📝 TODO List

### Критические (сделать первым):
- [x] Ежедневные награды
- [x] Premium подписка
- [ ] Регистрация handlers в bot.py
- [ ] Реферальные ссылки в start.py
- [ ] Миграция БД

### Важные:
- [ ] NFT интеграция
- [ ] Улучшения медведей
- [ ] PvP батлы
- [ ] Реклама

### Дополнительные:
- [ ] Аналитика
- [ ] Пуш-уведомления
- [ ] Backup система
- [ ] Onboarding
- [ ] Партнёрства

---

## 💬 Поддержка

Если возникли вопросы:
1. Проверьте логи: `sudo journalctl -u bearsmoney -f`
2. Проверьте БД: `sqlite3 bearsmoney.db ".tables"`
3. Перезапустите: `sudo systemctl restart bearsmoney`

🎉 **Удачи с запуском!**
