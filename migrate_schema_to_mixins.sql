-- Migration: Update auction_items schema to match refactored model with Mixins
-- Date: January 14, 2026
-- Purpose: Add new columns from BiddingMixin and LocationMixin refactoring

-- Start transaction
BEGIN;

-- ============================================================
-- 1. Add BiddingMixin columns (if they don't exist)
-- ============================================================

-- Add currency column (for multi-country support)
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='auction_items' AND column_name='currency') THEN
        ALTER TABLE auction_items ADD COLUMN currency VARCHAR(10) DEFAULT 'USD';
        RAISE NOTICE 'Added currency column';
    ELSE
        RAISE NOTICE 'currency column already exists';
    END IF;
END $$;

-- Change monetary columns from FLOAT to NUMERIC(12,2) for precision
DO $$ 
BEGIN
    -- current_bid
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name='auction_items' AND column_name='current_bid' 
               AND data_type='double precision') THEN
        ALTER TABLE auction_items ALTER COLUMN current_bid TYPE NUMERIC(12,2);
        RAISE NOTICE 'Changed current_bid to NUMERIC(12,2)';
    ELSIF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                      WHERE table_name='auction_items' AND column_name='current_bid') THEN
        ALTER TABLE auction_items ADD COLUMN current_bid NUMERIC(12,2) DEFAULT 0.0;
        RAISE NOTICE 'Added current_bid column';
    END IF;

    -- minimum_bid
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name='auction_items' AND column_name='minimum_bid' 
               AND data_type='double precision') THEN
        ALTER TABLE auction_items ALTER COLUMN minimum_bid TYPE NUMERIC(12,2);
        RAISE NOTICE 'Changed minimum_bid to NUMERIC(12,2)';
    ELSIF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                      WHERE table_name='auction_items' AND column_name='minimum_bid') THEN
        ALTER TABLE auction_items ADD COLUMN minimum_bid NUMERIC(12,2);
        RAISE NOTICE 'Added minimum_bid column';
    END IF;

    -- bid_increment
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name='auction_items' AND column_name='bid_increment' 
               AND data_type='double precision') THEN
        ALTER TABLE auction_items ALTER COLUMN bid_increment TYPE NUMERIC(12,2);
        RAISE NOTICE 'Changed bid_increment to NUMERIC(12,2)';
    ELSIF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                      WHERE table_name='auction_items' AND column_name='bid_increment') THEN
        ALTER TABLE auction_items ADD COLUMN bid_increment NUMERIC(12,2);
        RAISE NOTICE 'Added bid_increment column';
    END IF;

    -- next_minimum_bid
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name='auction_items' AND column_name='next_minimum_bid' 
               AND data_type='double precision') THEN
        ALTER TABLE auction_items ALTER COLUMN next_minimum_bid TYPE NUMERIC(12,2);
        RAISE NOTICE 'Changed next_minimum_bid to NUMERIC(12,2)';
    ELSIF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                      WHERE table_name='auction_items' AND column_name='next_minimum_bid') THEN
        ALTER TABLE auction_items ADD COLUMN next_minimum_bid NUMERIC(12,2);
        RAISE NOTICE 'Added next_minimum_bid column';
    END IF;
END $$;

-- ============================================================
-- 2. Add LocationMixin columns (if they don't exist)
-- ============================================================

DO $$ 
BEGIN
    -- country
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='auction_items' AND column_name='country') THEN
        ALTER TABLE auction_items ADD COLUMN country VARCHAR(100);
        RAISE NOTICE 'Added country column';
    ELSE
        RAISE NOTICE 'country column already exists';
    END IF;

    -- city (check if location_city exists and migrate data)
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='auction_items' AND column_name='city') THEN
        IF EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='auction_items' AND column_name='location_city') THEN
            -- Rename location_city to city
            ALTER TABLE auction_items RENAME COLUMN location_city TO city;
            RAISE NOTICE 'Renamed location_city to city';
        ELSE
            -- Add new city column
            ALTER TABLE auction_items ADD COLUMN city VARCHAR(200);
            RAISE NOTICE 'Added city column';
        END IF;
    ELSE
        RAISE NOTICE 'city column already exists';
    END IF;

    -- region (check if location_province or location_state exists)
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='auction_items' AND column_name='region') THEN
        IF EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='auction_items' AND column_name='location_province') THEN
            -- Rename location_province to region
            ALTER TABLE auction_items RENAME COLUMN location_province TO region;
            RAISE NOTICE 'Renamed location_province to region';
        ELSIF EXISTS (SELECT 1 FROM information_schema.columns 
                      WHERE table_name='auction_items' AND column_name='location_state') THEN
            -- Rename location_state to region
            ALTER TABLE auction_items RENAME COLUMN location_state TO region;
            RAISE NOTICE 'Renamed location_state to region';
        ELSE
            -- Add new region column
            ALTER TABLE auction_items ADD COLUMN region VARCHAR(100);
            RAISE NOTICE 'Added region column';
        END IF;
    ELSE
        RAISE NOTICE 'region column already exists';
    END IF;

    -- postal_code
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='auction_items' AND column_name='postal_code') THEN
        ALTER TABLE auction_items ADD COLUMN postal_code VARCHAR(20);
        RAISE NOTICE 'Added postal_code column';
    ELSE
        RAISE NOTICE 'postal_code column already exists';
    END IF;

    -- address_raw (check if location_address exists)
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='auction_items' AND column_name='address_raw') THEN
        IF EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='auction_items' AND column_name='location_address') THEN
            -- Rename location_address to address_raw
            ALTER TABLE auction_items RENAME COLUMN location_address TO address_raw;
            RAISE NOTICE 'Renamed location_address to address_raw';
        ELSE
            -- Add new address_raw column
            ALTER TABLE auction_items ADD COLUMN address_raw TEXT;
            RAISE NOTICE 'Added address_raw column';
        END IF;
    ELSE
        RAISE NOTICE 'address_raw column already exists';
    END IF;
END $$;

-- ============================================================
-- 3. Drop deprecated columns
-- ============================================================

DO $$ 
BEGIN
    -- Drop time_remaining (if exists)
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name='auction_items' AND column_name='time_remaining') THEN
        ALTER TABLE auction_items DROP COLUMN time_remaining;
        RAISE NOTICE 'Dropped time_remaining column';
    ELSE
        RAISE NOTICE 'time_remaining column does not exist';
    END IF;

    -- Drop any remaining old location columns after migration
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name='auction_items' AND column_name='location_city') THEN
        ALTER TABLE auction_items DROP COLUMN location_city;
        RAISE NOTICE 'Dropped old location_city column';
    END IF;

    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name='auction_items' AND column_name='location_province') THEN
        ALTER TABLE auction_items DROP COLUMN location_province;
        RAISE NOTICE 'Dropped old location_province column';
    END IF;

    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name='auction_items' AND column_name='location_state') THEN
        ALTER TABLE auction_items DROP COLUMN location_state;
        RAISE NOTICE 'Dropped old location_state column';
    END IF;

    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name='auction_items' AND column_name='location_address') THEN
        ALTER TABLE auction_items DROP COLUMN location_address;
        RAISE NOTICE 'Dropped old location_address column';
    END IF;
END $$;

-- ============================================================
-- 4. Create indexes for new columns
-- ============================================================

DO $$ 
BEGIN
    -- Index on country
    IF NOT EXISTS (SELECT 1 FROM pg_indexes 
                   WHERE tablename='auction_items' AND indexname='idx_country') THEN
        CREATE INDEX idx_country ON auction_items(country);
        RAISE NOTICE 'Created index on country';
    END IF;

    -- Index on city
    IF NOT EXISTS (SELECT 1 FROM pg_indexes 
                   WHERE tablename='auction_items' AND indexname='idx_city') THEN
        CREATE INDEX idx_city ON auction_items(city);
        RAISE NOTICE 'Created index on city';
    END IF;
END $$;

-- ============================================================
-- 5. Set default values for existing data
-- ============================================================

-- Set default country for existing US data (GSA, Treasury)
UPDATE auction_items 
SET country = 'United States' 
WHERE source IN ('gsa', 'treasury') AND country IS NULL;

-- Set default country for existing Canadian data (GCSurplus)
UPDATE auction_items 
SET country = 'Canada' 
WHERE source = 'gcsurplus' AND country IS NULL;

-- Set default currency for existing data
UPDATE auction_items 
SET currency = 'USD' 
WHERE currency IS NULL OR currency = '';

-- Commit transaction
COMMIT;

-- ============================================================
-- 6. Verify schema
-- ============================================================

SELECT 
    column_name, 
    data_type,
    character_maximum_length,
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'auction_items' 
ORDER BY ordinal_position;
