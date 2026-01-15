-- Migration: Add ton_balance field to users table
-- Date: 2026-01-15
-- Description: Добавление поля для хранения баланса TON криптовалюты

-- =============================================================================
-- FORWARD MIGRATION (Apply changes)
-- =============================================================================

-- For PostgreSQL:
DO $$
BEGIN
    -- Add ton_balance column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='users' AND column_name='ton_balance'
    ) THEN
        ALTER TABLE users ADD COLUMN ton_balance FLOAT DEFAULT 0;
        RAISE NOTICE 'Added ton_balance column';
    ELSE
        RAISE NOTICE 'Column ton_balance already exists';
    END IF;
END
$$;

-- Set default value for existing rows
UPDATE users SET ton_balance = 0 WHERE ton_balance IS NULL;

-- Set NOT NULL constraint
ALTER TABLE users ALTER COLUMN ton_balance SET DEFAULT 0;

-- =============================================================================
-- ROLLBACK (Undo changes)
-- =============================================================================

-- Uncomment to rollback:
/*
ALTER TABLE users DROP COLUMN IF EXISTS ton_balance;
*/

-- =============================================================================
-- FOR SQLite (if using SQLite instead of PostgreSQL)
-- =============================================================================

/*
-- SQLite doesn't support ADD COLUMN IF NOT EXISTS directly
-- But it supports ADD COLUMN which will fail if column exists

ALTER TABLE users ADD COLUMN ton_balance FLOAT DEFAULT 0;
*/

-- =============================================================================
-- VERIFICATION
-- =============================================================================

-- Check if migration was successful:
SELECT column_name, data_type, column_default
FROM information_schema.columns 
WHERE table_name = 'users' 
AND column_name = 'ton_balance';

-- Expected result:
-- column_name | data_type      | column_default
-- ton_balance | double precision | 0

-- Check sample data:
SELECT id, telegram_id, coins, ton_balance 
FROM users 
LIMIT 5;
