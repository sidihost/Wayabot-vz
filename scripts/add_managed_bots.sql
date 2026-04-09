-- Migration: Add Managed Bots Support (Telegram Bot API 9.6)
-- This adds support for creating real Telegram bots via the Managed Bots feature

-- Add managed bot columns to custom_bots if they don't exist
DO $$ 
BEGIN
    -- Telegram bot ID for the managed bot
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='custom_bots' AND column_name='telegram_bot_id') THEN
        ALTER TABLE custom_bots ADD COLUMN telegram_bot_id BIGINT UNIQUE;
    END IF;
    
    -- Telegram username (@username) of the managed bot
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='custom_bots' AND column_name='telegram_username') THEN
        ALTER TABLE custom_bots ADD COLUMN telegram_username VARCHAR(255);
    END IF;
    
    -- Bot token for the managed bot (encrypted in production)
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='custom_bots' AND column_name='telegram_token') THEN
        ALTER TABLE custom_bots ADD COLUMN telegram_token TEXT;
    END IF;
    
    -- Flag to indicate if this is a real Telegram bot
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='custom_bots' AND column_name='is_managed_bot') THEN
        ALTER TABLE custom_bots ADD COLUMN is_managed_bot BOOLEAN DEFAULT FALSE;
    END IF;
END $$;

-- Create index for faster lookup by telegram_bot_id
CREATE INDEX IF NOT EXISTS idx_custom_bots_telegram_id ON custom_bots(telegram_bot_id) WHERE telegram_bot_id IS NOT NULL;

-- Create index for finding active managed bots
CREATE INDEX IF NOT EXISTS idx_custom_bots_managed ON custom_bots(is_managed_bot, is_active) WHERE is_managed_bot = TRUE;

-- Print success message
DO $$
BEGIN
    RAISE NOTICE 'Migration completed successfully: Managed bots support added!';
END $$;
