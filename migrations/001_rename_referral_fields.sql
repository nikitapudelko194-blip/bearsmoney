-- Migration: Rename referral earnings fields from 'level' to 'tier'
-- Date: 2026-01-15
-- Description: Consistency fix for referral system naming

-- =============================================================================
-- FORWARD MIGRATION (Apply changes)
-- =============================================================================

-- Check if old columns exist and rename them
-- Note: SQLite doesn't support RENAME COLUMN directly, need to use ALTER TABLE

-- For PostgreSQL:
DO $$
BEGIN
    -- Rename referral_earnings_level1 to referral_earnings_tier1
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='users' AND column_name='referral_earnings_level1'
    ) THEN
        ALTER TABLE users RENAME COLUMN referral_earnings_level1 TO referral_earnings_tier1;
        RAISE NOTICE 'Renamed referral_earnings_level1 → referral_earnings_tier1';
    END IF;
    
    -- Rename referral_earnings_level2 to referral_earnings_tier2
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='users' AND column_name='referral_earnings_level2'
    ) THEN
        ALTER TABLE users RENAME COLUMN referral_earnings_level2 TO referral_earnings_tier2;
        RAISE NOTICE 'Renamed referral_earnings_level2 → referral_earnings_tier2';
    END IF;
    
    -- Rename referral_earnings_level3 to referral_earnings_tier3
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='users' AND column_name='referral_earnings_level3'
    ) THEN
        ALTER TABLE users RENAME COLUMN referral_earnings_level3 TO referral_earnings_tier3;
        RAISE NOTICE 'Renamed referral_earnings_level3 → referral_earnings_tier3';
    END IF;
END
$$;

-- Ensure columns have default values
ALTER TABLE users ALTER COLUMN referral_earnings_tier1 SET DEFAULT 0;
ALTER TABLE users ALTER COLUMN referral_earnings_tier2 SET DEFAULT 0;
ALTER TABLE users ALTER COLUMN referral_earnings_tier3 SET DEFAULT 0;

-- If columns don't exist at all (fresh install), create them
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='users' AND column_name='referral_earnings_tier1'
    ) THEN
        ALTER TABLE users ADD COLUMN referral_earnings_tier1 FLOAT DEFAULT 0;
        RAISE NOTICE 'Created referral_earnings_tier1';
    END IF;
    
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='users' AND column_name='referral_earnings_tier2'
    ) THEN
        ALTER TABLE users ADD COLUMN referral_earnings_tier2 FLOAT DEFAULT 0;
        RAISE NOTICE 'Created referral_earnings_tier2';
    END IF;
    
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='users' AND column_name='referral_earnings_tier3'
    ) THEN
        ALTER TABLE users ADD COLUMN referral_earnings_tier3 FLOAT DEFAULT 0;
        RAISE NOTICE 'Created referral_earnings_tier3';
    END IF;
END
$$;

-- =============================================================================
-- ROLLBACK (Undo changes)
-- =============================================================================

-- Uncomment to rollback:
/*
ALTER TABLE users RENAME COLUMN referral_earnings_tier1 TO referral_earnings_level1;
ALTER TABLE users RENAME COLUMN referral_earnings_tier2 TO referral_earnings_level2;
ALTER TABLE users RENAME COLUMN referral_earnings_tier3 TO referral_earnings_level3;
*/

-- =============================================================================
-- FOR SQLite (if using SQLite instead of PostgreSQL)
-- =============================================================================

-- SQLite doesn't support RENAME COLUMN before version 3.25.0
-- For older SQLite versions, you need to recreate the table:

/*
-- 1. Create new table with correct column names
CREATE TABLE users_new (
    -- Copy all columns from original users table
    -- Replace referral_earnings_level* with referral_earnings_tier*
    ...
);

-- 2. Copy data
INSERT INTO users_new SELECT * FROM users;

-- 3. Drop old table
DROP TABLE users;

-- 4. Rename new table
ALTER TABLE users_new RENAME TO users;
*/

-- =============================================================================
-- VERIFICATION
-- =============================================================================

-- Check if migration was successful:
SELECT column_name 
FROM information_schema.columns 
WHERE table_name = 'users' 
AND column_name LIKE 'referral_earnings_%'
ORDER BY column_name;

-- Expected result:
-- referral_earnings_tier1
-- referral_earnings_tier2
-- referral_earnings_tier3
