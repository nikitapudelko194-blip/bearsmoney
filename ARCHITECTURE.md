# 🏑 Архитектура Проекта

## Основные Компоненты

```
┌──────────────────────┐
│  Telegram User                      │
│  📱 Chat                         │
└──────────────────────┘
           ⬑
           ⬇⬇⬇
     ┌────────┐
     │ Telegram  │
     │ Bot API   │
     └────────┘
           ⬇
     ┌────────┐
     │  Bot App  │
     │ (aiogram)  │
     └────────┘
           ⬇
     ┌────────┐
     │  Handlers  │
     │  & FSM     │
     └────────┘
           ⬇
     ┌────────┐
     │ Services  │ (Бизнес-логика)
     │ & Logic   │
     └────────┘
       ⬇ ⬇ ⬇
    ──── ─ ────
   │           │
 ┌─────┐  ┌─────┐
 │   DB    │  │ Cache  │
 │  (PgSQL) │  │ (Redis) │
 └─────┘  └─────┘
    ⬇
 ┌─────┐
 │  TON    │ (Крипто)
 │ Wallet  │
 └─────┘
```

## Нижние Уровни (Лаяры)

### 1. **Презентационный слой** (Presentation Layer)

**Местоположение:** `app/handlers/`, `app/keyboards/`, `app/texts/`

- **Handlers** - обработка всех пользовательских вводов
- **Keyboards** - ответы с кнопками
- **Texts** - темплаты сообщений и текста

### 2. **Бизнес-логика** (Business Logic Layer)

**Местоположение:** `app/services/`

```
services/
├── economy.py             # Основная жидкость и доходы
├── wallet_service.py      # Управление кошельком
├── crypto_service.py      # TON интеграция
├── payment_service.py     # Обработка платежей
├── quest_service.py       # Квесты
├── referral_service.py    # Реферральная программа
├── notification_service.py# Уведомления
└── scheduler.py           # Крон и расписание
```

**Ответственности:**
- Економические расчеты
- Математика балансов
- Наноситель и бнес-логика

### 3. **Данные** (Data Layer)

**Местоположение:** `app/database/`

```
database/
├── models.py             # SQLAlchemy орм-модели
├── db.py                 # Управление соединениями
└── repositories/         # Данные (АН паттерн)
   ├── user_repo.py
   ├── bear_repo.py
   ├── coin_repo.py
   ├── transaction_repo.py
   ├── subscription_repo.py
   └── quest_repo.py
```

**Ответственности:**
- Праям к БД
- ОПРОвание данных
- Миграции схемы

### 4. **Модели Данных**

```python
# Пю основные объекты:

User            # Картамыца (1 о многим)
  └─ Bear    # Медведи пользователя
  └─ CoinTransaction  # Цена на коины
  └─ Subscription    # Подписка на подрэботки
  └─ Withdrawal      # Выводы крипто
```

## Поток Команды

```
1. User /start
   ⬇
2. Telegram Bot API Нарывает вебкук
   ⬇
3. aiogram ротер проводит к нужному хендлеру
   ⬇
4. Handler (контроллер)
   ⬇
5. Service (бизнес-логика)
   ⬇
6. Repository (работа с данными)
   ⬇
7. Database
   ⬇
8. Response к напознанию и ответ
```

## Кнопки и Менюцы

- **`reply_keyboard`** - Нижние кнопки в чате (ReplyKeyboardMarkup)
- **`inline_keyboard`** - Кнопки на сообщения (InlineKeyboardMarkup)

### Поток Клика:

```
User Клик На Кнопку
   ⬇
Inline Callback Query (callback_data)
   ⬇
Callback Handler (@router.callback_query())
   ⬇
Logic
   ⬇
Answer или Edit Message
```

## Фазовые Автоматы (FSM)

**Местоположение:** `app/state/states.py`

```python
class UserStates(StatesGroup):
    waiting_for_wallet_address = State()  # Ожидание адреса кошеля
    waiting_for_withdrawal_amount = State()  # Ожидание суммы вывода
    # ... другие состояния
```

## Арахиватура и Деплой

### Развертывание:

```
┌───────────────┐
│    GitHub Repository    │
└───────────────┘
        ⬇ git pull
┌───────────────┐
│      VPS/Server        │
│   (Docker Container)  │
└───────────────┘
        ⬇ docker-compose
        ⬇ up -d
┌───────────────┐
│   Bot По Человекенных  │
│   PostgreSQL          │
│   Redis               │
└───────────────┘
```

## Конрюоритность

- Асинхронные операции (async/await)
- asyncio для параллельного выполнения
- Celery для фоновых задач

## Оптимизация

- **Кэширование** данных в Redis
- **ОоООО** выражений в стартовую датабасу
- **Ундексы** на ключевых столбцах
- **Полинг** однорва для проверки на данных

## Безопасность

- Отделение секретов в `.env`
- SQL табиры через ORM
- Валидация всех вводов
- Токены и авторизация

---

Отличная архитектура достаточна для масштабирования графс тысячи онлайн пользователей!
