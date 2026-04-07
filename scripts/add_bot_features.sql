-- Migration: Add Bot Builder Advanced Features
-- This adds support for business bots, channel bots, polls, and automations

-- Add new columns to custom_bots if they don't exist
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='custom_bots' AND column_name='business_config') THEN
        ALTER TABLE custom_bots ADD COLUMN business_config JSONB DEFAULT '{}'::jsonb;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='custom_bots' AND column_name='channel_config') THEN
        ALTER TABLE custom_bots ADD COLUMN channel_config JSONB DEFAULT '{}'::jsonb;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='custom_bots' AND column_name='config') THEN
        ALTER TABLE custom_bots ADD COLUMN config JSONB DEFAULT '{}'::jsonb;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='custom_bots' AND column_name='unique_users_count') THEN
        ALTER TABLE custom_bots ADD COLUMN unique_users_count INT DEFAULT 0;
    END IF;
END $$;

-- Create bot_polls table for user-created polls within their bots
CREATE TABLE IF NOT EXISTS bot_polls (
    id SERIAL PRIMARY KEY,
    bot_id INT NOT NULL REFERENCES custom_bots(id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    question TEXT NOT NULL,
    options JSONB NOT NULL,
    config JSONB DEFAULT '{}'::jsonb,
    poll_type VARCHAR(20) DEFAULT 'regular' CHECK (poll_type IN ('regular', 'quiz')),
    is_active BOOLEAN DEFAULT TRUE,
    usage_count INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_bot_polls_bot ON bot_polls(bot_id);

-- Create bot_automations table for triggers and actions
CREATE TABLE IF NOT EXISTS bot_automations (
    id SERIAL PRIMARY KEY,
    bot_id INT NOT NULL REFERENCES custom_bots(id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    trigger_word VARCHAR(255) NOT NULL,
    action_type VARCHAR(50) NOT NULL,
    action_data JSONB NOT NULL,
    conditions JSONB DEFAULT '{}'::jsonb,
    enabled BOOLEAN DEFAULT TRUE,
    usage_count INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_bot_automations_bot ON bot_automations(bot_id);

-- Create bot_messages table for analytics tracking
CREATE TABLE IF NOT EXISTS bot_messages (
    id BIGSERIAL PRIMARY KEY,
    bot_id INT NOT NULL REFERENCES custom_bots(id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    message_type VARCHAR(50) DEFAULT 'text',
    direction VARCHAR(10) DEFAULT 'in' CHECK (direction IN ('in', 'out')),
    content_length INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_bot_messages_bot ON bot_messages(bot_id, created_at DESC);

-- Add total_polls_created to user_stats if not exists
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='user_stats' AND column_name='total_polls_created') THEN
        ALTER TABLE user_stats ADD COLUMN total_polls_created INT DEFAULT 0;
    END IF;
END $$;

-- Print success message
DO $$
BEGIN
    RAISE NOTICE 'Migration completed successfully: Bot builder advanced features added!';
END $$;
