# Database Migrations

Эта папка содержит SQL миграции для обновления структуры базы данных.

---

## 📊 Список миграций

| # | Файл | Описание | Дата |
|---|------|---------|------|
| 1 | `001_rename_referral_fields.sql` | Переименование `referral_earnings_level*` → `referral_earnings_tier*` | 2026-01-15 |

---

## ❓ Когда запускать миграции?

**Миграции нужно запускать в следующих случаях:**

1. ✅ **При обновлении структуры БД**
   - Изменение названий колонок
   - Добавление новых колонок в существующие таблицы
   - Изменение типов данных

2. ❌ **НЕ нужно запускать**
   - При создании новых таблиц (их создаёт `init_db()`)
   - При первом запуске бота

---

## 🚀 Как применить миграцию?

### Способ 1: Через psql (для PostgreSQL)

```bash
# 1. Подключитесь к базе данных
psql -U postgres -d bearsmoney

# 2. Запустите миграцию
\i migrations/001_rename_referral_fields.sql

# 3. Проверьте результат
SELECT column_name 
FROM information_schema.columns 
WHERE table_name = 'users' 
AND column_name LIKE 'referral_earnings_%'
ORDER BY column_name;
```

### Способ 2: Прямой запуск

```bash
psql -U postgres -d bearsmoney -f migrations/001_rename_referral_fields.sql
```

### Способ 3: Через Python скрипт

```python
import asyncio
from app.database.db import engine

async def run_migration():
    with open('migrations/001_rename_referral_fields.sql', 'r') as f:
        sql = f.read()
    
    async with engine.begin() as conn:
        await conn.execute(sql)
    
    print("✅ Migration completed!")

asyncio.run(run_migration())
```

---

## ✅ Как проверить?

### 1. Проверить структуру таблицы:

```sql
\d users
```

Или:

```sql
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'users'
ORDER BY ordinal_position;
```

### 2. Проверить конкретные колонки:

```sql
SELECT 
    referral_earnings_tier1,
    referral_earnings_tier2,
    referral_earnings_tier3
FROM users
LIMIT 1;
```

Если команда выполняется без ошибок - миграция применена ✅

---

## ⚠️ Откат миграции (Rollback)

Если нужно отменить изменения:

```sql
ALTER TABLE users RENAME COLUMN referral_earnings_tier1 TO referral_earnings_level1;
ALTER TABLE users RENAME COLUMN referral_earnings_tier2 TO referral_earnings_level2;
ALTER TABLE users RENAME COLUMN referral_earnings_tier3 TO referral_earnings_level3;
```

---

## 📝 Создание новой миграции

1. Создайте файл: `migrations/002_your_migration_name.sql`
2. Добавьте комментарии:
   ```sql
   -- Migration: Описание
   -- Date: YYYY-MM-DD
   -- Description: Что изменяется
   ```
3. Напишите SQL команды
4. Добавьте в таблицу выше

---

## 🛡️ Рекомендации

✅ **DO:**
- Создавайте резервную копию БД перед миграцией
- Тестируйте на тестовой БД сначала
- Добавляйте проверки `IF EXISTS`

❌ **DON'T:**
- Не запускайте миграции на продакшене без теста
- Не удаляйте старые миграции
- Не изменяйте применённые миграции

---

## 📞 Помощь

Если возникли проблемы:

1. Проверьте логи PostgreSQL
2. Проверьте права доступа к БД
3. Создайте issue в репозитории
