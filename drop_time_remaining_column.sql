-- Migration: Drop time_remaining column from auction_items table
-- Reason: Time-based countdown should be calculated client-side from closing_date (UTC)
-- This prevents storing stale values in the database

-- Drop the column if it exists
ALTER TABLE auction_items 
DROP COLUMN IF EXISTS time_remaining;

-- Verify the change
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'auction_items' 
ORDER BY ordinal_position;
