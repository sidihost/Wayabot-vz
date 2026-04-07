"""
Waya Bot Builder - PostgreSQL Database Module
Production-grade async database operations with connection pooling
"""

import asyncpg
import json
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager
import logging
import os

logger = logging.getLogger(__name__)

# Global database pool
_pool: Optional[asyncpg.Pool] = None


async def init_db():
    """Initialize database connection pool and schema"""
    global _pool
    
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is required")
    
    _pool = await asyncpg.create_pool(
        database_url,
        min_size=5,
        max_size=20,
        command_timeout=60,
        statement_cache_size=100
    )
    
    await _init_schema()
    logger.info("Database initialized successfully")


async def close_db():
    """Close database connection pool"""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
        logger.info("Database connection pool closed")


@asynccontextmanager
async def get_connection():
    """Get a connection from the pool"""
    async with _pool.acquire() as conn:
        yield conn


async def _init_schema():
    """Initialize complete database schema"""
    async with get_connection() as conn:
        await conn.execute('''
            -- =====================================================
            -- USERS & AUTHENTICATION
            -- =====================================================
            
            CREATE TABLE IF NOT EXISTS users (
                id BIGINT PRIMARY KEY,
                username VARCHAR(255),
                first_name VARCHAR(255),
                last_name VARCHAR(255),
                language_code VARCHAR(10) DEFAULT 'en',
                is_premium BOOLEAN DEFAULT FALSE,
                is_bot_admin BOOLEAN DEFAULT FALSE,
                is_blocked BOOLEAN DEFAULT FALSE,
                timezone VARCHAR(50) DEFAULT 'UTC',
                preferences JSONB DEFAULT '{}'::jsonb,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW(),
                last_active_at TIMESTAMPTZ DEFAULT NOW()
            );
            
            -- User statistics for gamification
            CREATE TABLE IF NOT EXISTS user_stats (
                user_id BIGINT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                total_messages INT DEFAULT 0,
                total_ai_requests INT DEFAULT 0,
                total_reminders_created INT DEFAULT 0,
                total_reminders_completed INT DEFAULT 0,
                total_notes INT DEFAULT 0,
                total_tasks_created INT DEFAULT 0,
                total_tasks_completed INT DEFAULT 0,
                total_polls_created INT DEFAULT 0,
                total_bots_created INT DEFAULT 0,
                total_bot_interactions INT DEFAULT 0,
                streak_days INT DEFAULT 0,
                longest_streak INT DEFAULT 0,
                last_streak_date DATE,
                xp_points INT DEFAULT 0,
                level INT DEFAULT 1,
                badges JSONB DEFAULT '[]'::jsonb,
                achievements JSONB DEFAULT '[]'::jsonb,
                updated_at TIMESTAMPTZ DEFAULT NOW()
            );
            
            -- User session state management
            CREATE TABLE IF NOT EXISTS user_sessions (
                user_id BIGINT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                current_state VARCHAR(100) DEFAULT 'idle',
                state_data JSONB DEFAULT '{}'::jsonb,
                active_bot_id INT,
                active_personality_id INT,
                conversation_context JSONB DEFAULT '{}'::jsonb,
                temp_data JSONB DEFAULT '{}'::jsonb,
                updated_at TIMESTAMPTZ DEFAULT NOW()
            );
            
            -- =====================================================
            -- CONVERSATIONS & AI
            -- =====================================================
            
            CREATE TABLE IF NOT EXISTS conversations (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
                content TEXT NOT NULL,
                bot_id INT,
                personality_id INT,
                metadata JSONB DEFAULT '{}'::jsonb,
                tokens_used INT DEFAULT 0,
                response_time_ms INT,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
            CREATE INDEX IF NOT EXISTS idx_conv_user ON conversations(user_id);
            CREATE INDEX IF NOT EXISTS idx_conv_created ON conversations(created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_conv_user_recent ON conversations(user_id, created_at DESC);
            
            -- AI Personalities
            CREATE TABLE IF NOT EXISTS ai_personalities (
                id SERIAL PRIMARY KEY,
                user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
                name VARCHAR(255) NOT NULL,
                description TEXT,
                avatar_emoji VARCHAR(10) DEFAULT '🤖',
                system_prompt TEXT NOT NULL,
                traits JSONB DEFAULT '[]'::jsonb,
                tone VARCHAR(50) DEFAULT 'friendly',
                language_style VARCHAR(50) DEFAULT 'casual',
                expertise_areas TEXT[] DEFAULT '{}',
                temperature DECIMAL(3,2) DEFAULT 0.7,
                max_tokens INT DEFAULT 1024,
                is_active BOOLEAN DEFAULT FALSE,
                is_default BOOLEAN DEFAULT FALSE,
                is_public BOOLEAN DEFAULT FALSE,
                usage_count INT DEFAULT 0,
                rating DECIMAL(3,2) DEFAULT 0,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            );
            CREATE INDEX IF NOT EXISTS idx_personality_user ON ai_personalities(user_id);
            CREATE INDEX IF NOT EXISTS idx_personality_public ON ai_personalities(is_public) WHERE is_public = TRUE;
            
            -- =====================================================
            -- REMINDERS SYSTEM
            -- =====================================================
            
            CREATE TABLE IF NOT EXISTS reminders (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                title VARCHAR(500) NOT NULL,
                description TEXT,
                remind_at TIMESTAMPTZ NOT NULL,
                repeat_type VARCHAR(20) DEFAULT 'none' CHECK (repeat_type IN ('none', 'daily', 'weekly', 'monthly', 'yearly', 'custom')),
                repeat_interval INT DEFAULT 0,
                repeat_end_date TIMESTAMPTZ,
                repeat_count INT DEFAULT 0,
                max_repeat_count INT,
                is_active BOOLEAN DEFAULT TRUE,
                is_completed BOOLEAN DEFAULT FALSE,
                is_snoozed BOOLEAN DEFAULT FALSE,
                snooze_until TIMESTAMPTZ,
                priority VARCHAR(10) DEFAULT 'normal' CHECK (priority IN ('low', 'normal', 'high', 'urgent')),
                category VARCHAR(100),
                tags TEXT[] DEFAULT '{}',
                notification_sent BOOLEAN DEFAULT FALSE,
                completed_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            );
            CREATE INDEX IF NOT EXISTS idx_reminder_user ON reminders(user_id);
            CREATE INDEX IF NOT EXISTS idx_reminder_due ON reminders(remind_at) WHERE is_active = TRUE AND is_completed = FALSE;
            CREATE INDEX IF NOT EXISTS idx_reminder_active ON reminders(is_active, is_completed, remind_at);
            
            -- =====================================================
            -- NOTES SYSTEM
            -- =====================================================
            
            CREATE TABLE IF NOT EXISTS notes (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                title VARCHAR(500),
                content TEXT NOT NULL,
                content_type VARCHAR(20) DEFAULT 'text' CHECK (content_type IN ('text', 'markdown', 'checklist', 'code')),
                category VARCHAR(100),
                folder_id INT,
                tags TEXT[] DEFAULT '{}',
                color VARCHAR(20) DEFAULT 'default',
                is_pinned BOOLEAN DEFAULT FALSE,
                is_archived BOOLEAN DEFAULT FALSE,
                is_locked BOOLEAN DEFAULT FALSE,
                attachments JSONB DEFAULT '[]'::jsonb,
                word_count INT DEFAULT 0,
                last_edited_at TIMESTAMPTZ DEFAULT NOW(),
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            );
            CREATE INDEX IF NOT EXISTS idx_note_user ON notes(user_id);
            CREATE INDEX IF NOT EXISTS idx_note_category ON notes(user_id, category);
            CREATE INDEX IF NOT EXISTS idx_note_pinned ON notes(user_id, is_pinned DESC, updated_at DESC);
            CREATE INDEX IF NOT EXISTS idx_note_search ON notes USING gin(to_tsvector('english', COALESCE(title, '') || ' ' || content));
            
            -- Note folders for organization
            CREATE TABLE IF NOT EXISTS note_folders (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                name VARCHAR(255) NOT NULL,
                parent_id INT REFERENCES note_folders(id) ON DELETE CASCADE,
                color VARCHAR(20) DEFAULT 'default',
                icon VARCHAR(50),
                sort_order INT DEFAULT 0,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
            
            -- =====================================================
            -- TASKS & TODOS SYSTEM
            -- =====================================================
            
            CREATE TABLE IF NOT EXISTS tasks (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                title VARCHAR(500) NOT NULL,
                description TEXT,
                due_date TIMESTAMPTZ,
                due_time TIME,
                priority VARCHAR(10) DEFAULT 'normal' CHECK (priority IN ('low', 'normal', 'high', 'urgent')),
                status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'completed', 'cancelled', 'deferred')),
                category VARCHAR(100),
                project_id INT,
                parent_task_id INT REFERENCES tasks(id) ON DELETE CASCADE,
                tags TEXT[] DEFAULT '{}',
                subtasks JSONB DEFAULT '[]'::jsonb,
                checklist JSONB DEFAULT '[]'::jsonb,
                estimated_minutes INT,
                actual_minutes INT,
                recurrence JSONB,
                reminder_before INT,
                attachments JSONB DEFAULT '[]'::jsonb,
                completed_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            );
            CREATE INDEX IF NOT EXISTS idx_task_user ON tasks(user_id);
            CREATE INDEX IF NOT EXISTS idx_task_status ON tasks(user_id, status);
            CREATE INDEX IF NOT EXISTS idx_task_due ON tasks(due_date) WHERE status NOT IN ('completed', 'cancelled');
            CREATE INDEX IF NOT EXISTS idx_task_priority ON tasks(user_id, priority DESC, due_date ASC NULLS LAST);
            
            -- Projects for task grouping
            CREATE TABLE IF NOT EXISTS projects (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                name VARCHAR(255) NOT NULL,
                description TEXT,
                color VARCHAR(20) DEFAULT 'blue',
                icon VARCHAR(50),
                status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'completed', 'archived', 'on_hold')),
                due_date TIMESTAMPTZ,
                progress INT DEFAULT 0,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            );
            
            -- =====================================================
            -- CUSTOM BOT BUILDER
            -- =====================================================
            
            CREATE TABLE IF NOT EXISTS custom_bots (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                name VARCHAR(255) NOT NULL,
                description TEXT,
                avatar_emoji VARCHAR(10) DEFAULT '🤖',
                bot_type VARCHAR(50) NOT NULL,
                category VARCHAR(100),
                
                -- AI Configuration
                system_prompt TEXT NOT NULL,
                welcome_message TEXT,
                fallback_message TEXT DEFAULT 'I''m not sure how to help with that. Try asking differently!',
                personality JSONB DEFAULT '{}'::jsonb,
                temperature DECIMAL(3,2) DEFAULT 0.7,
                max_tokens INT DEFAULT 1024,
                
                -- Commands and Triggers
                commands JSONB DEFAULT '[]'::jsonb,
                triggers JSONB DEFAULT '[]'::jsonb,
                keywords JSONB DEFAULT '[]'::jsonb,
                
                -- Responses and Flows
                responses JSONB DEFAULT '{}'::jsonb,
                conversation_flows JSONB DEFAULT '[]'::jsonb,
                quick_replies JSONB DEFAULT '[]'::jsonb,
                
                -- Settings
                settings JSONB DEFAULT '{}'::jsonb,
                features JSONB DEFAULT '{"ai_enabled": true, "learning_enabled": false}'::jsonb,
                
                -- Metadata
                is_active BOOLEAN DEFAULT TRUE,
                is_public BOOLEAN DEFAULT FALSE,
                is_verified BOOLEAN DEFAULT FALSE,
                usage_count INT DEFAULT 0,
                total_conversations INT DEFAULT 0,
                rating DECIMAL(3,2) DEFAULT 0,
                rating_count INT DEFAULT 0,
                unique_users_count INT DEFAULT 0,
                
                -- Business Bot Config (for Telegram Business accounts)
                business_config JSONB DEFAULT '{}'::jsonb,
                
                -- Channel Bot Config (for channel management)
                channel_config JSONB DEFAULT '{}'::jsonb,
                
                -- Extended config (all additional settings)
                config JSONB DEFAULT '{}'::jsonb,
                
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            );
            CREATE INDEX IF NOT EXISTS idx_bot_user ON custom_bots(user_id);
            CREATE INDEX IF NOT EXISTS idx_bot_type ON custom_bots(bot_type);
            CREATE INDEX IF NOT EXISTS idx_bot_public ON custom_bots(is_public, rating DESC) WHERE is_public = TRUE;
            
            -- Bot-specific polls (for users to add to their bots)
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
            
            -- Bot automations (triggers and actions)
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
            
            -- Bot messages tracking (for analytics)
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
            
            -- Bot templates library
            CREATE TABLE IF NOT EXISTS bot_templates (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                description TEXT NOT NULL,
                bot_type VARCHAR(50) NOT NULL,
                category VARCHAR(100) NOT NULL,
                icon VARCHAR(50) DEFAULT 'bot',
                
                system_prompt TEXT NOT NULL,
                welcome_message TEXT,
                personality JSONB DEFAULT '{}'::jsonb,
                commands JSONB DEFAULT '[]'::jsonb,
                sample_triggers JSONB DEFAULT '[]'::jsonb,
                default_settings JSONB DEFAULT '{}'::jsonb,
                
                difficulty VARCHAR(20) DEFAULT 'beginner',
                estimated_setup_minutes INT DEFAULT 5,
                
                is_featured BOOLEAN DEFAULT FALSE,
                is_new BOOLEAN DEFAULT FALSE,
                usage_count INT DEFAULT 0,
                rating DECIMAL(3,2) DEFAULT 0,
                
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            );
            CREATE INDEX IF NOT EXISTS idx_template_category ON bot_templates(category);
            CREATE INDEX IF NOT EXISTS idx_template_featured ON bot_templates(is_featured DESC, usage_count DESC);
            
            -- Bot knowledge base for custom data
            CREATE TABLE IF NOT EXISTS bot_knowledge (
                id SERIAL PRIMARY KEY,
                bot_id INT NOT NULL REFERENCES custom_bots(id) ON DELETE CASCADE,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                keywords TEXT[] DEFAULT '{}',
                category VARCHAR(100),
                priority INT DEFAULT 0,
                usage_count INT DEFAULT 0,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
            CREATE INDEX IF NOT EXISTS idx_knowledge_bot ON bot_knowledge(bot_id);
            CREATE INDEX IF NOT EXISTS idx_knowledge_search ON bot_knowledge USING gin(to_tsvector('english', question || ' ' || answer));
            
            -- =====================================================
            -- POLLS & QUIZZES
            -- =====================================================
            
            CREATE TABLE IF NOT EXISTS polls (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                telegram_poll_id VARCHAR(100),
                telegram_message_id BIGINT,
                chat_id BIGINT,
                
                question TEXT NOT NULL,
                options JSONB NOT NULL,
                poll_type VARCHAR(20) DEFAULT 'regular' CHECK (poll_type IN ('regular', 'quiz')),
                
                is_anonymous BOOLEAN DEFAULT TRUE,
                allows_multiple BOOLEAN DEFAULT FALSE,
                correct_option_id INT,
                explanation TEXT,
                
                open_period INT,
                close_date TIMESTAMPTZ,
                is_closed BOOLEAN DEFAULT FALSE,
                
                total_votes INT DEFAULT 0,
                votes_by_option JSONB DEFAULT '{}'::jsonb,
                
                created_at TIMESTAMPTZ DEFAULT NOW(),
                closed_at TIMESTAMPTZ
            );
            CREATE INDEX IF NOT EXISTS idx_poll_user ON polls(user_id);
            CREATE INDEX IF NOT EXISTS idx_poll_telegram ON polls(telegram_poll_id);
            
            -- Poll votes tracking
            CREATE TABLE IF NOT EXISTS poll_votes (
                id SERIAL PRIMARY KEY,
                poll_id INT NOT NULL REFERENCES polls(id) ON DELETE CASCADE,
                user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                option_ids INT[] NOT NULL,
                voted_at TIMESTAMPTZ DEFAULT NOW(),
                UNIQUE(poll_id, user_id)
            );
            
            -- =====================================================
            -- SCHEDULED MESSAGES & BROADCASTS
            -- =====================================================
            
            CREATE TABLE IF NOT EXISTS scheduled_messages (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                chat_id BIGINT NOT NULL,
                
                message_text TEXT NOT NULL,
                message_type VARCHAR(20) DEFAULT 'text',
                parse_mode VARCHAR(20) DEFAULT 'HTML',
                attachments JSONB DEFAULT '[]'::jsonb,
                reply_markup JSONB,
                
                send_at TIMESTAMPTZ NOT NULL,
                repeat_type VARCHAR(20) DEFAULT 'none',
                repeat_interval INT DEFAULT 0,
                repeat_end_date TIMESTAMPTZ,
                
                is_sent BOOLEAN DEFAULT FALSE,
                is_active BOOLEAN DEFAULT TRUE,
                sent_at TIMESTAMPTZ,
                error_message TEXT,
                retry_count INT DEFAULT 0,
                
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
            CREATE INDEX IF NOT EXISTS idx_scheduled_send ON scheduled_messages(send_at) WHERE is_active = TRUE AND is_sent = FALSE;
            
            -- =====================================================
            -- ANALYTICS & TRACKING
            -- =====================================================
            
            CREATE TABLE IF NOT EXISTS analytics_events (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
                event_type VARCHAR(100) NOT NULL,
                event_category VARCHAR(50),
                event_action VARCHAR(100),
                event_label VARCHAR(255),
                event_value DECIMAL(15,2),
                event_data JSONB DEFAULT '{}'::jsonb,
                session_id VARCHAR(100),
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
            CREATE INDEX IF NOT EXISTS idx_analytics_user ON analytics_events(user_id);
            CREATE INDEX IF NOT EXISTS idx_analytics_type ON analytics_events(event_type);
            CREATE INDEX IF NOT EXISTS idx_analytics_time ON analytics_events(created_at DESC);
            
            -- Daily aggregated stats
            CREATE TABLE IF NOT EXISTS daily_stats (
                id SERIAL PRIMARY KEY,
                date DATE NOT NULL,
                total_users INT DEFAULT 0,
                new_users INT DEFAULT 0,
                active_users INT DEFAULT 0,
                total_messages INT DEFAULT 0,
                total_ai_requests INT DEFAULT 0,
                total_reminders INT DEFAULT 0,
                total_notes INT DEFAULT 0,
                total_tasks INT DEFAULT 0,
                total_bots_created INT DEFAULT 0,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                UNIQUE(date)
            );
            
            -- =====================================================
            -- FEEDBACK & SUPPORT
            -- =====================================================
            
            CREATE TABLE IF NOT EXISTS feedback (
                id SERIAL PRIMARY KEY,
                user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
                feedback_type VARCHAR(50) NOT NULL CHECK (feedback_type IN ('bug', 'feature', 'general', 'complaint', 'praise')),
                subject VARCHAR(255),
                content TEXT NOT NULL,
                rating INT CHECK (rating >= 1 AND rating <= 5),
                context JSONB DEFAULT '{}'::jsonb,
                status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'reviewed', 'resolved', 'closed')),
                admin_notes TEXT,
                resolved_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
            CREATE INDEX IF NOT EXISTS idx_feedback_status ON feedback(status);
            
            -- =====================================================
            -- NOTIFICATIONS & ALERTS
            -- =====================================================
            
            CREATE TABLE IF NOT EXISTS notifications (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                type VARCHAR(50) NOT NULL,
                title VARCHAR(255) NOT NULL,
                message TEXT NOT NULL,
                action_url TEXT,
                action_data JSONB,
                is_read BOOLEAN DEFAULT FALSE,
                is_sent BOOLEAN DEFAULT FALSE,
                sent_at TIMESTAMPTZ,
                expires_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
            CREATE INDEX IF NOT EXISTS idx_notification_user ON notifications(user_id, is_read, created_at DESC);
            
            -- =====================================================
            -- VOICE AI (ELEVENLABS)
            -- =====================================================
            
            CREATE TABLE IF NOT EXISTS user_voice_preferences (
                user_id BIGINT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                voice_name VARCHAR(100) DEFAULT 'Rachel',
                voice_style VARCHAR(50) DEFAULT 'default',
                language VARCHAR(50) DEFAULT 'English',
                output_format VARCHAR(50) DEFAULT 'mp3_44100_128',
                auto_voice_replies BOOLEAN DEFAULT FALSE,
                custom_voice_id VARCHAR(100),
                custom_voice_name VARCHAR(100),
                usage_count INT DEFAULT 0,
                last_used_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            );
            
            -- Voice generation history
            CREATE TABLE IF NOT EXISTS voice_generation_history (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                voice_name VARCHAR(100) NOT NULL,
                voice_style VARCHAR(50),
                text_length INT NOT NULL,
                audio_duration_seconds DECIMAL(10,2),
                characters_used INT NOT NULL,
                generation_time_ms INT,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
            CREATE INDEX IF NOT EXISTS idx_voice_history_user ON voice_generation_history(user_id, created_at DESC);
            
            -- Cloned voices
            CREATE TABLE IF NOT EXISTS cloned_voices (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                elevenlabs_voice_id VARCHAR(100) NOT NULL UNIQUE,
                name VARCHAR(100) NOT NULL,
                description TEXT,
                sample_count INT DEFAULT 0,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
            CREATE INDEX IF NOT EXISTS idx_cloned_voices_user ON cloned_voices(user_id);
            
            -- =====================================================
            -- EMOTION AI (HUME)
            -- =====================================================
            
            CREATE TABLE IF NOT EXISTS user_emotional_history (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                dominant_emotion VARCHAR(100),
                confidence DECIMAL(5,4),
                top_emotions JSONB DEFAULT '{}'::jsonb,
                context TEXT,
                analyzed_at TIMESTAMPTZ DEFAULT NOW()
            );
            CREATE INDEX IF NOT EXISTS idx_emotion_history_user ON user_emotional_history(user_id, analyzed_at DESC);
            CREATE INDEX IF NOT EXISTS idx_emotion_history_emotion ON user_emotional_history(dominant_emotion);
            
            -- Emotion preferences (response style adjustments)
            CREATE TABLE IF NOT EXISTS user_emotion_preferences (
                user_id BIGINT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                enable_emotion_detection BOOLEAN DEFAULT TRUE,
                enable_empathic_responses BOOLEAN DEFAULT TRUE,
                emotion_sensitivity VARCHAR(20) DEFAULT 'normal' CHECK (emotion_sensitivity IN ('low', 'normal', 'high')),
                preferred_response_tone VARCHAR(50) DEFAULT 'adaptive',
                share_emotional_insights BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            );
            
            -- Emotional wellbeing tracking (daily summaries)
            CREATE TABLE IF NOT EXISTS emotional_daily_summary (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                date DATE NOT NULL,
                dominant_emotion VARCHAR(100),
                positive_ratio DECIMAL(5,4),
                negative_ratio DECIMAL(5,4),
                neutral_ratio DECIMAL(5,4),
                wellbeing_score INT,
                interaction_count INT DEFAULT 0,
                emotion_breakdown JSONB DEFAULT '{}'::jsonb,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                UNIQUE(user_id, date)
            );
            CREATE INDEX IF NOT EXISTS idx_daily_emotion_user ON emotional_daily_summary(user_id, date DESC);
            
            -- =====================================================
            -- AI AGENT FEATURES
            -- =====================================================
            
            -- Bot agent settings (per-bot AI agent configuration)
            CREATE TABLE IF NOT EXISTS bot_agent_settings (
                bot_id INT PRIMARY KEY REFERENCES custom_bots(id) ON DELETE CASCADE,
                auto_react_enabled BOOLEAN DEFAULT TRUE,
                auto_moderate_enabled BOOLEAN DEFAULT FALSE,
                auto_suggest_enabled BOOLEAN DEFAULT TRUE,
                auto_schedule_enabled BOOLEAN DEFAULT FALSE,
                reaction_style VARCHAR(50) DEFAULT 'expressive',
                moderation_level VARCHAR(20) DEFAULT 'medium',
                suggestion_count INT DEFAULT 3,
                settings JSONB DEFAULT '{}'::jsonb,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            );
            
            -- Scheduled content queue (AI-optimized posting)
            CREATE TABLE IF NOT EXISTS scheduled_content (
                id SERIAL PRIMARY KEY,
                bot_id INT REFERENCES custom_bots(id) ON DELETE CASCADE,
                user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
                chat_id BIGINT NOT NULL,
                content TEXT NOT NULL,
                content_type VARCHAR(20) DEFAULT 'text',
                media_url TEXT,
                scheduled_at TIMESTAMPTZ NOT NULL,
                optimal_score DECIMAL(5,2),
                is_sent BOOLEAN DEFAULT FALSE,
                is_cancelled BOOLEAN DEFAULT FALSE,
                sent_at TIMESTAMPTZ,
                engagement_count INT DEFAULT 0,
                error_message TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
            CREATE INDEX IF NOT EXISTS idx_scheduled_content_pending ON scheduled_content(scheduled_at) WHERE is_sent = FALSE AND is_cancelled = FALSE;
            CREATE INDEX IF NOT EXISTS idx_scheduled_content_bot ON scheduled_content(bot_id);
            
            -- Moderation logs (auto-moderation actions)
            CREATE TABLE IF NOT EXISTS moderation_logs (
                id SERIAL PRIMARY KEY,
                bot_id INT REFERENCES custom_bots(id) ON DELETE CASCADE,
                chat_id BIGINT NOT NULL,
                user_id BIGINT NOT NULL,
                message_id BIGINT,
                action_type VARCHAR(50) NOT NULL,
                reason TEXT,
                message_content TEXT,
                confidence_score DECIMAL(5,4),
                auto_action_taken VARCHAR(50),
                is_false_positive BOOLEAN DEFAULT FALSE,
                reviewed_by BIGINT,
                reviewed_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
            CREATE INDEX IF NOT EXISTS idx_moderation_bot ON moderation_logs(bot_id, created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_moderation_user ON moderation_logs(user_id);
            CREATE INDEX IF NOT EXISTS idx_moderation_chat ON moderation_logs(chat_id);
            
            -- Engagement analytics (track optimal posting times)
            CREATE TABLE IF NOT EXISTS engagement_analytics (
                id SERIAL PRIMARY KEY,
                bot_id INT REFERENCES custom_bots(id) ON DELETE CASCADE,
                chat_id BIGINT NOT NULL,
                hour_of_day INT NOT NULL CHECK (hour_of_day >= 0 AND hour_of_day < 24),
                day_of_week INT NOT NULL CHECK (day_of_week >= 0 AND day_of_week < 7),
                message_count INT DEFAULT 0,
                reaction_count INT DEFAULT 0,
                reply_count INT DEFAULT 0,
                avg_response_time_ms INT DEFAULT 0,
                engagement_score DECIMAL(5,2) DEFAULT 0,
                updated_at TIMESTAMPTZ DEFAULT NOW(),
                UNIQUE(bot_id, chat_id, hour_of_day, day_of_week)
            );
            CREATE INDEX IF NOT EXISTS idx_engagement_bot ON engagement_analytics(bot_id);
            CREATE INDEX IF NOT EXISTS idx_engagement_chat ON engagement_analytics(chat_id);
            
            -- Auto-reaction history (track what reactions were sent)
            CREATE TABLE IF NOT EXISTS auto_reactions (
                id SERIAL PRIMARY KEY,
                bot_id INT REFERENCES custom_bots(id) ON DELETE CASCADE,
                chat_id BIGINT NOT NULL,
                message_id BIGINT NOT NULL,
                user_id BIGINT NOT NULL,
                reaction_emoji VARCHAR(20) NOT NULL,
                detected_emotion VARCHAR(50),
                confidence_score DECIMAL(5,4),
                message_preview TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
            CREATE INDEX IF NOT EXISTS idx_auto_reactions_bot ON auto_reactions(bot_id, created_at DESC);
            
            -- Suggestion usage tracking (learn which suggestions work)
            CREATE TABLE IF NOT EXISTS suggestion_usage (
                id SERIAL PRIMARY KEY,
                bot_id INT REFERENCES custom_bots(id) ON DELETE CASCADE,
                chat_id BIGINT NOT NULL,
                user_id BIGINT NOT NULL,
                suggestion_text TEXT NOT NULL,
                was_used BOOLEAN DEFAULT FALSE,
                context_hash VARCHAR(64),
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
            CREATE INDEX IF NOT EXISTS idx_suggestion_bot ON suggestion_usage(bot_id);
            
            -- Spam patterns cache (learned spam patterns)
            CREATE TABLE IF NOT EXISTS spam_patterns (
                id SERIAL PRIMARY KEY,
                pattern_type VARCHAR(50) NOT NULL,
                pattern_value TEXT NOT NULL,
                severity VARCHAR(20) DEFAULT 'medium',
                match_count INT DEFAULT 0,
                is_active BOOLEAN DEFAULT TRUE,
                created_by BIGINT,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                UNIQUE(pattern_type, pattern_value)
            );
            CREATE INDEX IF NOT EXISTS idx_spam_patterns_type ON spam_patterns(pattern_type) WHERE is_active = TRUE;
            
            -- User warnings (moderation warnings per user)
            CREATE TABLE IF NOT EXISTS user_warnings (
                id SERIAL PRIMARY KEY,
                bot_id INT REFERENCES custom_bots(id) ON DELETE CASCADE,
                chat_id BIGINT NOT NULL,
                user_id BIGINT NOT NULL,
                warning_type VARCHAR(50) NOT NULL,
                reason TEXT,
                warning_count INT DEFAULT 1,
                last_warning_at TIMESTAMPTZ DEFAULT NOW(),
                expires_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                UNIQUE(bot_id, chat_id, user_id, warning_type)
            );
            CREATE INDEX IF NOT EXISTS idx_user_warnings_lookup ON user_warnings(bot_id, chat_id, user_id);
        ''')
        
        # Insert default bot templates
        await _insert_default_templates(conn)
        logger.info("Database schema initialized")


async def _insert_default_templates(conn):
    """Insert default bot templates if they don't exist"""
    count = await conn.fetchval("SELECT COUNT(*) FROM bot_templates")
    if count > 0:
        return
    
    templates = [
        {
            "name": "Customer Support Pro",
            "description": "Enterprise-grade customer service bot with ticket management, FAQ handling, and human escalation",
            "bot_type": "support",
            "category": "Business",
            "icon": "headphones",
            "system_prompt": """You are a professional customer support agent for a company. Your responsibilities:

1. GREETING: Always greet warmly and ask how you can help
2. UNDERSTANDING: Listen carefully and ask clarifying questions
3. RESOLUTION: Provide clear, step-by-step solutions
4. ESCALATION: Offer to escalate complex issues to human agents
5. FOLLOW-UP: Confirm the issue is resolved before closing

Communication style:
- Professional yet friendly
- Patient and empathetic
- Clear and concise
- Solution-oriented

Always acknowledge the customer's feelings and thank them for their patience.""",
            "welcome_message": "Hello! Welcome to our support center. I'm here to help you with any questions or issues. How can I assist you today?",
            "personality": {"tone": "professional", "empathy": "high", "patience": "high"},
            "commands": [
                {"command": "help", "description": "Get help with your issue"},
                {"command": "status", "description": "Check ticket status"},
                {"command": "faq", "description": "Browse frequently asked questions"},
                {"command": "escalate", "description": "Request human agent"}
            ],
            "difficulty": "beginner",
            "is_featured": True
        },
        {
            "name": "Smart FAQ Bot",
            "description": "Intelligent FAQ assistant that learns from your knowledge base and provides instant answers",
            "bot_type": "faq",
            "category": "Business",
            "icon": "help-circle",
            "system_prompt": """You are an intelligent FAQ assistant. Your role:

1. Answer questions accurately based on available information
2. Provide clear, concise responses
3. Offer related information when relevant
4. Guide users to resources when you can't answer directly
5. Learn from interactions to improve responses

When unsure:
- Acknowledge the limitation
- Suggest alternative resources
- Offer to connect with human support

Keep responses brief but comprehensive.""",
            "welcome_message": "Hi! I'm your FAQ assistant. Ask me anything and I'll find the answer for you!",
            "personality": {"tone": "helpful", "knowledge": "high"},
            "commands": [
                {"command": "search", "description": "Search for specific topics"},
                {"command": "categories", "description": "Browse FAQ categories"},
                {"command": "popular", "description": "View popular questions"}
            ],
            "difficulty": "beginner",
            "is_featured": True
        },
        {
            "name": "Quiz Master Pro",
            "description": "Interactive quiz bot with multiple formats, scoring, leaderboards, and AI-generated questions",
            "bot_type": "quiz",
            "category": "Entertainment",
            "icon": "brain",
            "system_prompt": """You are an exciting Quiz Master! Your personality:

1. ENTHUSIASM: Be energetic and make quizzes fun
2. EDUCATION: Explain answers with interesting facts
3. ENCOURAGEMENT: Celebrate correct answers, be supportive for wrong ones
4. VARIETY: Offer different topics and difficulty levels
5. COMPETITION: Track scores and create friendly competition

Quiz formats:
- Multiple choice
- True/False
- Open-ended
- Picture rounds
- Speed rounds

Always provide educational value with entertainment!""",
            "welcome_message": "🎯 Welcome to Quiz Master! Ready to test your knowledge? Choose a category and let's play!",
            "personality": {"tone": "enthusiastic", "energy": "high", "supportive": True},
            "commands": [
                {"command": "quiz", "description": "Start a new quiz"},
                {"command": "topics", "description": "Browse quiz topics"},
                {"command": "score", "description": "View your score"},
                {"command": "leaderboard", "description": "See top players"},
                {"command": "daily", "description": "Daily challenge"}
            ],
            "difficulty": "beginner",
            "is_featured": True
        },
        {
            "name": "Language Tutor",
            "description": "Patient language learning assistant with vocabulary, grammar, conversation practice, and progress tracking",
            "bot_type": "education",
            "category": "Education",
            "icon": "book-open",
            "system_prompt": """You are a patient, encouraging language tutor. Your approach:

1. ASSESSMENT: Understand the learner's current level
2. CUSTOMIZATION: Adapt lessons to their needs and goals
3. PRACTICE: Provide interactive exercises and conversations
4. CORRECTION: Gently correct mistakes with clear explanations
5. ENCOURAGEMENT: Celebrate progress and maintain motivation

Teaching methods:
- Vocabulary building with context
- Grammar explanations with examples
- Conversation practice
- Cultural insights
- Pronunciation guidance
- Spaced repetition for retention

Be patient, positive, and make learning enjoyable!""",
            "welcome_message": "Hello! 👋 I'm your language tutor. Which language would you like to learn today? I'll help you at your own pace!",
            "personality": {"tone": "encouraging", "patience": "very_high", "thoroughness": "high"},
            "commands": [
                {"command": "lesson", "description": "Start a lesson"},
                {"command": "practice", "description": "Practice exercises"},
                {"command": "vocabulary", "description": "Learn new words"},
                {"command": "grammar", "description": "Grammar lessons"},
                {"command": "conversation", "description": "Practice speaking"},
                {"command": "progress", "description": "View your progress"}
            ],
            "difficulty": "intermediate",
            "is_featured": True
        },
        {
            "name": "Code Assistant",
            "description": "Expert programming helper for debugging, code review, explanations, and learning",
            "bot_type": "coding",
            "category": "Technology",
            "icon": "code",
            "system_prompt": """You are an expert programming assistant. Your expertise:

1. LANGUAGES: Proficient in Python, JavaScript, TypeScript, Java, C++, Go, Rust, and more
2. DEBUGGING: Systematic approach to finding and fixing bugs
3. EXPLANATION: Clear explanations of code and concepts
4. BEST PRACTICES: Guidance on clean code, patterns, and architecture
5. LEARNING: Patient teaching for all skill levels

When helping:
- Ask clarifying questions
- Explain the reasoning behind solutions
- Suggest improvements and alternatives
- Consider edge cases and error handling
- Recommend relevant resources

Always format code properly and explain the 'why' behind solutions.""",
            "welcome_message": "👨‍💻 Hey there! I'm your coding buddy. Paste your code, describe your problem, or ask any programming question. Let's solve it together!",
            "personality": {"tone": "technical_friendly", "detail": "high", "patience": "high"},
            "commands": [
                {"command": "debug", "description": "Help debug code"},
                {"command": "explain", "description": "Explain code or concept"},
                {"command": "review", "description": "Code review"},
                {"command": "optimize", "description": "Optimize code"},
                {"command": "convert", "description": "Convert between languages"}
            ],
            "difficulty": "intermediate",
            "is_featured": True
        },
        {
            "name": "Fitness Coach",
            "description": "Motivating fitness assistant for personalized workouts, nutrition guidance, and goal tracking",
            "bot_type": "fitness",
            "category": "Health",
            "icon": "dumbbell",
            "system_prompt": """You are an energetic, knowledgeable fitness coach. Your approach:

1. ASSESSMENT: Understand fitness level, goals, and limitations
2. PLANNING: Create personalized workout and nutrition plans
3. MOTIVATION: Keep users engaged and motivated
4. SAFETY: Always prioritize safe exercise practices
5. TRACKING: Help monitor progress and adjust plans

Areas of expertise:
- Strength training
- Cardio and HIIT
- Flexibility and mobility
- Nutrition and meal planning
- Recovery and rest
- Mental fitness

Be energetic, supportive, and science-based!""",
            "welcome_message": "💪 Hey champion! Ready to crush your fitness goals? Tell me about yourself and what you want to achieve. Let's get started!",
            "personality": {"tone": "energetic", "motivation": "high", "supportive": True},
            "commands": [
                {"command": "workout", "description": "Get a workout"},
                {"command": "nutrition", "description": "Nutrition advice"},
                {"command": "progress", "description": "Track progress"},
                {"command": "tips", "description": "Fitness tips"},
                {"command": "challenge", "description": "Daily challenge"}
            ],
            "difficulty": "beginner"
        },
        {
            "name": "Creative Writer",
            "description": "Imaginative writing companion for stories, poetry, content creation, and overcoming writer's block",
            "bot_type": "creative",
            "category": "Creative",
            "icon": "pen-tool",
            "system_prompt": """You are a creative writing companion with a vivid imagination. Your abilities:

1. STORYTELLING: Craft engaging narratives across genres
2. POETRY: Create poems in various styles and forms
3. IDEATION: Generate creative ideas and overcome writer's block
4. EDITING: Provide constructive feedback on writing
5. COLLABORATION: Co-write and build on user ideas

Creative specialties:
- Fiction (all genres)
- Poetry and prose
- Screenwriting
- Blog posts and articles
- Marketing copy
- Creative exercises

Be imaginative, inspiring, and supportive of all creative endeavors!""",
            "welcome_message": "✨ Welcome to the creative corner! I'm here to help bring your ideas to life. What shall we create today?",
            "personality": {"tone": "creative", "imagination": "very_high", "supportive": True},
            "commands": [
                {"command": "write", "description": "Start writing"},
                {"command": "story", "description": "Create a story"},
                {"command": "poem", "description": "Write a poem"},
                {"command": "ideas", "description": "Get creative ideas"},
                {"command": "feedback", "description": "Get writing feedback"}
            ],
            "difficulty": "beginner"
        },
        {
            "name": "Personal Assistant",
            "description": "Efficient AI assistant for scheduling, reminders, organization, and daily productivity",
            "bot_type": "assistant",
            "category": "Productivity",
            "icon": "calendar",
            "system_prompt": """You are an efficient, proactive personal assistant. Your capabilities:

1. SCHEDULING: Manage appointments and calendars
2. REMINDERS: Set and track reminders
3. ORGANIZATION: Help organize tasks and priorities
4. INFORMATION: Provide quick answers and research
5. PLANNING: Assist with daily and long-term planning

Work style:
- Proactive and anticipatory
- Organized and detail-oriented
- Clear and concise communication
- Respectful of time and priorities
- Adaptable to preferences

Always confirm actions and provide helpful summaries!""",
            "welcome_message": "Good day! I'm your personal assistant. How can I help you stay organized and productive today?",
            "personality": {"tone": "professional_friendly", "efficiency": "high", "proactive": True},
            "commands": [
                {"command": "schedule", "description": "Manage schedule"},
                {"command": "remind", "description": "Set reminder"},
                {"command": "tasks", "description": "Manage tasks"},
                {"command": "summary", "description": "Daily summary"},
                {"command": "plan", "description": "Plan ahead"}
            ],
            "difficulty": "beginner",
            "is_featured": True
        },
        {
            "name": "Meditation Guide",
            "description": "Calming guide for meditation, mindfulness, breathing exercises, and stress relief",
            "bot_type": "wellness",
            "category": "Health",
            "icon": "heart",
            "system_prompt": """You are a serene meditation guide. Your approach:

1. CALM: Maintain a peaceful, soothing presence
2. GUIDANCE: Lead meditations and breathing exercises
3. MINDFULNESS: Teach mindfulness techniques
4. ADAPTATION: Adjust to user's experience level
5. SUPPORT: Provide emotional support and encouragement

Specialties:
- Guided meditations
- Breathing exercises
- Body scans
- Stress relief techniques
- Sleep meditation
- Mindful moments

Speak slowly, calmly, and with warmth. Create a safe space for relaxation.""",
            "welcome_message": "🧘 Welcome to your moment of peace. Take a deep breath... I'm here to guide you to calm and clarity. How can I help you today?",
            "personality": {"tone": "calm", "pace": "slow", "warmth": "high"},
            "commands": [
                {"command": "meditate", "description": "Start meditation"},
                {"command": "breathe", "description": "Breathing exercise"},
                {"command": "sleep", "description": "Sleep meditation"},
                {"command": "calm", "description": "Quick calm down"},
                {"command": "daily", "description": "Daily mindfulness"}
            ],
            "difficulty": "beginner"
        },
        {
            "name": "Recipe Chef",
            "description": "Culinary expert for recipes, cooking tips, meal planning, and dietary accommodations",
            "bot_type": "cooking",
            "category": "Lifestyle",
            "icon": "utensils",
            "system_prompt": """You are a friendly, knowledgeable chef. Your expertise:

1. RECIPES: Share delicious recipes for all skill levels
2. TECHNIQUES: Teach cooking methods and tips
3. PLANNING: Help with meal planning and prep
4. ADAPTATION: Modify recipes for dietary needs
5. CREATIVITY: Inspire culinary experimentation

Specialties:
- Global cuisines
- Dietary accommodations (vegan, gluten-free, etc.)
- Quick meals
- Meal prep
- Ingredient substitutions
- Kitchen hacks

Be warm, encouraging, and make cooking accessible and fun!""",
            "welcome_message": "👨‍🍳 Welcome to my kitchen! Whether you're a beginner or a seasoned cook, I'm here to help. What would you like to cook today?",
            "personality": {"tone": "warm", "creativity": "high", "patience": "high"},
            "commands": [
                {"command": "recipe", "description": "Get a recipe"},
                {"command": "ingredients", "description": "What can I make?"},
                {"command": "tips", "description": "Cooking tips"},
                {"command": "meal", "description": "Meal planning"},
                {"command": "substitute", "description": "Ingredient substitutes"}
            ],
            "difficulty": "beginner"
        },
        {
            "name": "Travel Planner",
            "description": "Adventure guide for trip planning, destination info, itineraries, and travel tips",
            "bot_type": "travel",
            "category": "Lifestyle",
            "icon": "plane",
            "system_prompt": """You are an enthusiastic travel expert. Your services:

1. PLANNING: Help plan trips and itineraries
2. DESTINATIONS: Share insights about places worldwide
3. RECOMMENDATIONS: Suggest activities, food, and experiences
4. BUDGETING: Help plan travel budgets
5. TIPS: Share practical travel advice

Knowledge areas:
- Popular and hidden gem destinations
- Local customs and culture
- Transportation options
- Accommodation advice
- Safety tips
- Packing guides

Be adventurous, knowledgeable, and inspire wanderlust!""",
            "welcome_message": "🌍 Hello, fellow traveler! Where does your wanderlust want to take you? Let's plan your next adventure!",
            "personality": {"tone": "adventurous", "enthusiasm": "high", "knowledge": "extensive"},
            "commands": [
                {"command": "plan", "description": "Plan a trip"},
                {"command": "destination", "description": "Explore destinations"},
                {"command": "itinerary", "description": "Create itinerary"},
                {"command": "tips", "description": "Travel tips"},
                {"command": "budget", "description": "Budget planning"}
            ],
            "difficulty": "beginner"
        },
        {
            "name": "Study Buddy",
            "description": "Academic assistant for studying, homework help, exam prep, and learning strategies",
            "bot_type": "education",
            "category": "Education",
            "icon": "graduation-cap",
            "system_prompt": """You are a supportive study companion. Your role:

1. TUTORING: Help understand difficult concepts
2. STUDY STRATEGIES: Teach effective learning techniques
3. EXAM PREP: Help prepare for tests and exams
4. MOTIVATION: Keep students motivated and on track
5. ORGANIZATION: Help organize study schedules

Subjects:
- Mathematics
- Sciences
- Languages
- History
- Literature
- And more!

Learning techniques:
- Spaced repetition
- Active recall
- Mind mapping
- Practice problems
- Summarization

Be patient, encouraging, and make learning enjoyable!""",
            "welcome_message": "📚 Hey there! Ready to ace your studies? Tell me what you're working on and let's tackle it together!",
            "personality": {"tone": "friendly", "patience": "high", "encouragement": "high"},
            "commands": [
                {"command": "study", "description": "Start study session"},
                {"command": "explain", "description": "Explain a concept"},
                {"command": "quiz", "description": "Test knowledge"},
                {"command": "plan", "description": "Study schedule"},
                {"command": "tips", "description": "Study tips"}
            ],
            "difficulty": "beginner"
        }
    ]
    
    for t in templates:
        await conn.execute('''
            INSERT INTO bot_templates (name, description, bot_type, category, icon, system_prompt, welcome_message, personality, commands, difficulty, is_featured)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
        ''', t["name"], t["description"], t["bot_type"], t["category"], t["icon"],
            t["system_prompt"], t.get("welcome_message"), json.dumps(t.get("personality", {})),
            json.dumps(t.get("commands", [])), t.get("difficulty", "beginner"), t.get("is_featured", False))


# =====================================================
# USER OPERATIONS
# =====================================================

async def get_or_create_user(
    user_id: int,
    username: str = None,
    first_name: str = None,
    last_name: str = None,
    language_code: str = "en",
    is_premium: bool = False
) -> Dict[str, Any]:
    """Get or create a user, returns user data with is_new flag"""
    async with get_connection() as conn:
        user = await conn.fetchrow("SELECT * FROM users WHERE id = $1", user_id)
        
        if user:
            # Update existing user
            await conn.execute('''
                UPDATE users SET
                    username = COALESCE($2, username),
                    first_name = COALESCE($3, first_name),
                    last_name = COALESCE($4, last_name),
                    language_code = COALESCE($5, language_code),
                    is_premium = $6,
                    last_active_at = NOW(),
                    updated_at = NOW()
                WHERE id = $1
            ''', user_id, username, first_name, last_name, language_code, is_premium)
            
            result = dict(user)
            result["is_new"] = False
            return result
        
        # Create new user
        await conn.execute('''
            INSERT INTO users (id, username, first_name, last_name, language_code, is_premium)
            VALUES ($1, $2, $3, $4, $5, $6)
        ''', user_id, username, first_name, last_name, language_code, is_premium)
        
        # Create related records
        await conn.execute("INSERT INTO user_stats (user_id) VALUES ($1)", user_id)
        await conn.execute("INSERT INTO user_sessions (user_id) VALUES ($1)", user_id)
        
        return {
            "id": user_id,
            "username": username,
            "first_name": first_name,
            "last_name": last_name,
            "language_code": language_code,
            "is_premium": is_premium,
            "is_new": True
        }


async def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    """Get user by ID"""
    async with get_connection() as conn:
        user = await conn.fetchrow("SELECT * FROM users WHERE id = $1", user_id)
        return dict(user) if user else None


async def get_user_stats(user_id: int) -> Optional[Dict[str, Any]]:
    """Get user statistics"""
    async with get_connection() as conn:
        stats = await conn.fetchrow("SELECT * FROM user_stats WHERE user_id = $1", user_id)
        return dict(stats) if stats else None


async def increment_stat(user_id: int, stat_name: str, amount: int = 1):
    """Increment a user statistic"""
    valid_stats = [
        "total_messages", "total_ai_requests", "total_reminders_created",
        "total_reminders_completed", "total_notes", "total_tasks_created",
        "total_tasks_completed", "total_polls_created", "total_bots_created",
        "total_bot_interactions"
    ]
    if stat_name not in valid_stats:
        return
    
    async with get_connection() as conn:
        await conn.execute(f'''
            UPDATE user_stats SET {stat_name} = {stat_name} + $2, updated_at = NOW()
            WHERE user_id = $1
        ''', user_id, amount)


async def add_xp(user_id: int, xp: int) -> Dict[str, Any]:
    """Add XP and check for level up"""
    async with get_connection() as conn:
        old_stats = await conn.fetchrow("SELECT xp_points, level FROM user_stats WHERE user_id = $1", user_id)
        if not old_stats:
            return {"xp_added": 0, "level_up": False}
        
        new_xp = old_stats["xp_points"] + xp
        new_level = int((new_xp / 100) ** 0.5) + 1
        level_up = new_level > old_stats["level"]
        
        await conn.execute('''
            UPDATE user_stats SET xp_points = $2, level = $3, updated_at = NOW()
            WHERE user_id = $1
        ''', user_id, new_xp, new_level)
        
        return {
            "xp_added": xp,
            "total_xp": new_xp,
            "level": new_level,
            "level_up": level_up
        }


async def update_streak(user_id: int) -> Dict[str, Any]:
    """Update user streak"""
    async with get_connection() as conn:
        stats = await conn.fetchrow(
            "SELECT streak_days, longest_streak, last_streak_date FROM user_stats WHERE user_id = $1",
            user_id
        )
        if not stats:
            return {"streak": 0}
        
        today = datetime.now(timezone.utc).date()
        last_date = stats["last_streak_date"]
        
        if last_date == today:
            return {"streak": stats["streak_days"], "continued": False}
        
        if last_date == today - timedelta(days=1):
            new_streak = stats["streak_days"] + 1
        else:
            new_streak = 1
        
        longest = max(new_streak, stats["longest_streak"])
        
        await conn.execute('''
            UPDATE user_stats SET streak_days = $2, longest_streak = $3, last_streak_date = $4, updated_at = NOW()
            WHERE user_id = $1
        ''', user_id, new_streak, longest, today)
        
        return {"streak": new_streak, "longest": longest, "continued": True}


# =====================================================
# SESSION OPERATIONS
# =====================================================

async def get_session(user_id: int) -> Optional[Dict[str, Any]]:
    """Get user session state"""
    async with get_connection() as conn:
        session = await conn.fetchrow("SELECT * FROM user_sessions WHERE user_id = $1", user_id)
        if session:
            result = dict(session)
            result["state_data"] = json.loads(result["state_data"]) if isinstance(result["state_data"], str) else result["state_data"]
            return result
        return None


async def update_session_state(user_id: int, state: str, state_data: Dict = None):
    """Update user session state"""
    async with get_connection() as conn:
        await conn.execute('''
            INSERT INTO user_sessions (user_id, current_state, state_data, updated_at)
            VALUES ($1, $2, $3, NOW())
            ON CONFLICT (user_id) DO UPDATE SET
                current_state = $2, state_data = $3, updated_at = NOW()
        ''', user_id, state, json.dumps(state_data or {}))


async def clear_session_state(user_id: int):
    """Clear user session state"""
    await update_session_state(user_id, "idle", {})


async def set_active_bot(user_id: int, bot_id: int = None):
    """Set active custom bot for user"""
    async with get_connection() as conn:
        await conn.execute('''
            UPDATE user_sessions SET active_bot_id = $2, updated_at = NOW()
            WHERE user_id = $1
        ''', user_id, bot_id)


# =====================================================
# CONVERSATION OPERATIONS
# =====================================================

async def add_conversation(user_id: int, role: str, content: str, metadata: Dict = None):
    """Add message to conversation history"""
    async with get_connection() as conn:
        await conn.execute('''
            INSERT INTO conversations (user_id, role, content, metadata)
            VALUES ($1, $2, $3, $4)
        ''', user_id, role, content, json.dumps(metadata or {}))


async def get_conversation_history(user_id: int, limit: int = 20) -> List[Dict[str, Any]]:
    """Get recent conversation history"""
    async with get_connection() as conn:
        rows = await conn.fetch('''
            SELECT role, content, metadata, created_at
            FROM conversations
            WHERE user_id = $1
            ORDER BY created_at DESC
            LIMIT $2
        ''', user_id, limit)
        return [dict(row) for row in reversed(rows)]


async def clear_conversation_history(user_id: int):
    """Clear conversation history"""
    async with get_connection() as conn:
        await conn.execute("DELETE FROM conversations WHERE user_id = $1", user_id)


# =====================================================
# REMINDER OPERATIONS
# =====================================================

async def create_reminder(
    user_id: int,
    title: str,
    remind_at: datetime,
    description: str = None,
    repeat_type: str = "none",
    repeat_interval: int = 0,
    priority: str = "normal",
    category: str = None,
    tags: List[str] = None
) -> int:
    """Create a reminder"""
    async with get_connection() as conn:
        reminder_id = await conn.fetchval('''
            INSERT INTO reminders (user_id, title, description, remind_at, repeat_type, repeat_interval, priority, category, tags)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            RETURNING id
        ''', user_id, title, description, remind_at, repeat_type, repeat_interval, priority, category, tags or [])
        
        await increment_stat(user_id, "total_reminders_created")
        return reminder_id


async def get_user_reminders(user_id: int, active_only: bool = True, limit: int = 50) -> List[Dict[str, Any]]:
    """Get user's reminders"""
    async with get_connection() as conn:
        if active_only:
            rows = await conn.fetch('''
                SELECT * FROM reminders
                WHERE user_id = $1 AND is_active = TRUE AND is_completed = FALSE
                ORDER BY remind_at ASC
                LIMIT $2
            ''', user_id, limit)
        else:
            rows = await conn.fetch('''
                SELECT * FROM reminders
                WHERE user_id = $1
                ORDER BY remind_at DESC
                LIMIT $2
            ''', user_id, limit)
        return [dict(row) for row in rows]


async def get_due_reminders() -> List[Dict[str, Any]]:
    """Get all due reminders"""
    async with get_connection() as conn:
        rows = await conn.fetch('''
            SELECT r.*, u.first_name, u.timezone
            FROM reminders r
            JOIN users u ON r.user_id = u.id
            WHERE r.is_active = TRUE
            AND r.is_completed = FALSE
            AND r.notification_sent = FALSE
            AND r.remind_at <= NOW()
            ORDER BY r.remind_at ASC
        ''')
        return [dict(row) for row in rows]


async def mark_reminder_sent(reminder_id: int):
    """Mark reminder notification as sent"""
    async with get_connection() as conn:
        await conn.execute('''
            UPDATE reminders SET notification_sent = TRUE, updated_at = NOW()
            WHERE id = $1
        ''', reminder_id)


async def complete_reminder(reminder_id: int, user_id: int) -> bool:
    """Mark reminder as completed"""
    async with get_connection() as conn:
        result = await conn.execute('''
            UPDATE reminders SET is_completed = TRUE, completed_at = NOW(), updated_at = NOW()
            WHERE id = $1 AND user_id = $2
        ''', reminder_id, user_id)
        
        if "UPDATE 1" in result:
            await increment_stat(user_id, "total_reminders_completed")
            return True
        return False


async def snooze_reminder(reminder_id: int, user_id: int, snooze_minutes: int) -> bool:
    """Snooze a reminder"""
    async with get_connection() as conn:
        new_time = datetime.now(timezone.utc) + timedelta(minutes=snooze_minutes)
        result = await conn.execute('''
            UPDATE reminders SET
                remind_at = $3,
                notification_sent = FALSE,
                is_snoozed = TRUE,
                snooze_until = $3,
                updated_at = NOW()
            WHERE id = $1 AND user_id = $2
        ''', reminder_id, user_id, new_time)
        return "UPDATE 1" in result


async def delete_reminder(reminder_id: int, user_id: int) -> bool:
    """Delete a reminder"""
    async with get_connection() as conn:
        result = await conn.execute(
            "DELETE FROM reminders WHERE id = $1 AND user_id = $2",
            reminder_id, user_id
        )
        return "DELETE 1" in result


# =====================================================
# NOTE OPERATIONS
# =====================================================

async def create_note(
    user_id: int,
    content: str,
    title: str = None,
    category: str = None,
    tags: List[str] = None,
    color: str = "default"
) -> int:
    """Create a note"""
    async with get_connection() as conn:
        word_count = len(content.split())
        note_id = await conn.fetchval('''
            INSERT INTO notes (user_id, title, content, category, tags, color, word_count)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING id
        ''', user_id, title, content, category, tags or [], color, word_count)
        
        await increment_stat(user_id, "total_notes")
        return note_id


async def get_user_notes(
    user_id: int,
    category: str = None,
    include_archived: bool = False,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """Get user's notes"""
    async with get_connection() as conn:
        conditions = ["user_id = $1"]
        params = [user_id]
        
        if not include_archived:
            conditions.append("is_archived = FALSE")
        
        if category:
            params.append(category)
            conditions.append(f"category = ${len(params)}")
        
        params.append(limit)
        query = f'''
            SELECT * FROM notes
            WHERE {" AND ".join(conditions)}
            ORDER BY is_pinned DESC, updated_at DESC
            LIMIT ${len(params)}
        '''
        
        rows = await conn.fetch(query, *params)
        return [dict(row) for row in rows]


async def search_notes(user_id: int, query: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Search notes"""
    async with get_connection() as conn:
        rows = await conn.fetch('''
            SELECT *, ts_rank(to_tsvector('english', COALESCE(title, '') || ' ' || content), plainto_tsquery($2)) as rank
            FROM notes
            WHERE user_id = $1
            AND to_tsvector('english', COALESCE(title, '') || ' ' || content) @@ plainto_tsquery($2)
            ORDER BY rank DESC, updated_at DESC
            LIMIT $3
        ''', user_id, query, limit)
        return [dict(row) for row in rows]


async def update_note(note_id: int, user_id: int, **kwargs) -> bool:
    """Update a note"""
    allowed = ["title", "content", "category", "tags", "is_pinned", "is_archived", "color"]
    updates = {k: v for k, v in kwargs.items() if k in allowed and v is not None}
    
    if not updates:
        return False
    
    if "content" in updates:
        updates["word_count"] = len(updates["content"].split())
    
    async with get_connection() as conn:
        set_parts = [f"{k} = ${i+3}" for i, k in enumerate(updates.keys())]
        query = f'''
            UPDATE notes SET {", ".join(set_parts)}, updated_at = NOW(), last_edited_at = NOW()
            WHERE id = $1 AND user_id = $2
        '''
        result = await conn.execute(query, note_id, user_id, *updates.values())
        return "UPDATE 1" in result


async def delete_note(note_id: int, user_id: int) -> bool:
    """Delete a note"""
    async with get_connection() as conn:
        result = await conn.execute(
            "DELETE FROM notes WHERE id = $1 AND user_id = $2",
            note_id, user_id
        )
        return "DELETE 1" in result


# =====================================================
# TASK OPERATIONS
# =====================================================

async def create_task(
    user_id: int,
    title: str,
    description: str = None,
    due_date: datetime = None,
    priority: str = "normal",
    category: str = None,
    tags: List[str] = None
) -> int:
    """Create a task"""
    async with get_connection() as conn:
        task_id = await conn.fetchval('''
            INSERT INTO tasks (user_id, title, description, due_date, priority, category, tags)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING id
        ''', user_id, title, description, due_date, priority, category, tags or [])
        
        await increment_stat(user_id, "total_tasks_created")
        return task_id


async def get_user_tasks(
    user_id: int,
    status: str = None,
    priority: str = None,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """Get user's tasks"""
    async with get_connection() as conn:
        conditions = ["user_id = $1"]
        params = [user_id]
        
        if status:
            params.append(status)
            conditions.append(f"status = ${len(params)}")
        
        if priority:
            params.append(priority)
            conditions.append(f"priority = ${len(params)}")
        
        params.append(limit)
        query = f'''
            SELECT * FROM tasks
            WHERE {" AND ".join(conditions)}
            ORDER BY 
                CASE status WHEN 'pending' THEN 1 WHEN 'in_progress' THEN 2 ELSE 3 END,
                CASE priority WHEN 'urgent' THEN 1 WHEN 'high' THEN 2 WHEN 'normal' THEN 3 ELSE 4 END,
                due_date ASC NULLS LAST
            LIMIT ${len(params)}
        '''
        
        rows = await conn.fetch(query, *params)
        return [dict(row) for row in rows]


async def update_task_status(task_id: int, user_id: int, status: str) -> bool:
    """Update task status"""
    async with get_connection() as conn:
        completed_at = datetime.now(timezone.utc) if status == "completed" else None
        result = await conn.execute('''
            UPDATE tasks SET status = $3, completed_at = $4, updated_at = NOW()
            WHERE id = $1 AND user_id = $2
        ''', task_id, user_id, status, completed_at)
        
        if "UPDATE 1" in result and status == "completed":
            await increment_stat(user_id, "total_tasks_completed")
            return True
        return "UPDATE 1" in result


async def delete_task(task_id: int, user_id: int) -> bool:
    """Delete a task"""
    async with get_connection() as conn:
        result = await conn.execute(
            "DELETE FROM tasks WHERE id = $1 AND user_id = $2",
            task_id, user_id
        )
        return "DELETE 1" in result


# =====================================================
# CUSTOM BOT OPERATIONS
# =====================================================

async def create_custom_bot(
    user_id: int,
    name: str,
    bot_type: str = "custom",
    system_prompt: str = "",
    description: str = None,
    category: str = None,
    welcome_message: str = None,
    personality: Dict = None,
    commands: List[Dict] = None,
    settings: Dict = None,
    config: Dict = None
) -> int:
    """Create a custom bot with full configuration support"""
    async with get_connection() as conn:
        bot_id = await conn.fetchval('''
            INSERT INTO custom_bots (user_id, name, description, bot_type, category, system_prompt, welcome_message, personality, commands, settings, config)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            RETURNING id
        ''', user_id, name, description, bot_type, category, system_prompt, welcome_message,
            json.dumps(personality or {}), json.dumps(commands or []), json.dumps(settings or {}), json.dumps(config or {}))
        
        await increment_stat(user_id, "total_bots_created")
        return bot_id


async def get_user_bots(user_id: int, active_only: bool = False) -> List[Dict[str, Any]]:
    """Get user's custom bots"""
    async with get_connection() as conn:
        if active_only:
            rows = await conn.fetch('''
                SELECT * FROM custom_bots WHERE user_id = $1 AND is_active = TRUE
                ORDER BY updated_at DESC
            ''', user_id)
        else:
            rows = await conn.fetch('''
                SELECT * FROM custom_bots WHERE user_id = $1
                ORDER BY updated_at DESC
            ''', user_id)
        return [dict(row) for row in rows]


async def get_bot(bot_id: int) -> Optional[Dict[str, Any]]:
    """Get a bot by ID"""
    async with get_connection() as conn:
        bot = await conn.fetchrow("SELECT * FROM custom_bots WHERE id = $1", bot_id)
        return dict(bot) if bot else None


async def get_bot_templates(category: str = None, featured_only: bool = False) -> List[Dict[str, Any]]:
    """Get bot templates"""
    async with get_connection() as conn:
        conditions = []
        params = []
        
        if category:
            params.append(category)
            conditions.append(f"category = ${len(params)}")
        
        if featured_only:
            conditions.append("is_featured = TRUE")
        
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        query = f'''
            SELECT * FROM bot_templates
            {where}
            ORDER BY is_featured DESC, usage_count DESC, name ASC
        '''
        
        rows = await conn.fetch(query, *params) if params else await conn.fetch(query)
        return [dict(row) for row in rows]


async def update_bot(bot_id: int, user_id: int, **kwargs) -> bool:
    """Update a custom bot"""
    allowed = ["name", "description", "system_prompt", "welcome_message", "personality",
               "commands", "triggers", "responses", "settings", "is_active"]
    updates = {}
    
    for k, v in kwargs.items():
        if k in allowed and v is not None:
            if k in ["personality", "commands", "triggers", "responses", "settings"]:
                updates[k] = json.dumps(v) if isinstance(v, (dict, list)) else v
            else:
                updates[k] = v
    
    if not updates:
        return False
    
    async with get_connection() as conn:
        set_parts = [f"{k} = ${i+3}" for i, k in enumerate(updates.keys())]
        query = f'''
            UPDATE custom_bots SET {", ".join(set_parts)}, updated_at = NOW()
            WHERE id = $1 AND user_id = $2
        '''
        result = await conn.execute(query, bot_id, user_id, *updates.values())
        return "UPDATE 1" in result


async def delete_bot(bot_id: int, user_id: int) -> bool:
    """Delete a custom bot"""
    async with get_connection() as conn:
        result = await conn.execute(
            "DELETE FROM custom_bots WHERE id = $1 AND user_id = $2",
            bot_id, user_id
        )
        return "DELETE 1" in result


async def increment_bot_usage(bot_id: int):
    """Increment bot usage count"""
    async with get_connection() as conn:
        await conn.execute('''
            UPDATE custom_bots SET usage_count = usage_count + 1, total_conversations = total_conversations + 1
            WHERE id = $1
        ''', bot_id)


async def add_bot_knowledge(bot_id: int, question: str, answer: str, keywords: List[str] = None, category: str = None) -> int:
    """Add a knowledge base entry to a bot"""
    async with get_connection() as conn:
        knowledge_id = await conn.fetchval('''
            INSERT INTO bot_knowledge (bot_id, question, answer, keywords, category)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id
        ''', bot_id, question, answer, keywords or [], category)
        return knowledge_id


async def get_bot_knowledge(bot_id: int, search_query: str = None) -> List[Dict[str, Any]]:
    """Get knowledge base entries for a bot, optionally filtered by search"""
    async with get_connection() as conn:
        if search_query:
            rows = await conn.fetch('''
                SELECT * FROM bot_knowledge 
                WHERE bot_id = $1 AND (
                    question ILIKE $2 OR answer ILIKE $2 OR $3 = ANY(keywords)
                )
                ORDER BY priority DESC, usage_count DESC
            ''', bot_id, f'%{search_query}%', search_query.lower())
        else:
            rows = await conn.fetch('''
                SELECT * FROM bot_knowledge WHERE bot_id = $1
                ORDER BY priority DESC, usage_count DESC
            ''', bot_id)
        return [dict(row) for row in rows]


async def search_bot_knowledge(bot_id: int, query: str) -> Optional[Dict[str, Any]]:
    """Search for the best matching knowledge entry"""
    async with get_connection() as conn:
        # Full text search
        row = await conn.fetchrow('''
            SELECT *, ts_rank(to_tsvector('english', question || ' ' || answer), plainto_tsquery($2)) as rank
            FROM bot_knowledge 
            WHERE bot_id = $1 AND to_tsvector('english', question || ' ' || answer) @@ plainto_tsquery($2)
            ORDER BY rank DESC, priority DESC
            LIMIT 1
        ''', bot_id, query)
        
        if row:
            # Increment usage count
            await conn.execute(
                "UPDATE bot_knowledge SET usage_count = usage_count + 1 WHERE id = $1",
                row['id']
            )
            return dict(row)
        return None


# =====================================================
# AI PERSONALITY OPERATIONS
# =====================================================

async def create_personality(
    user_id: int,
    name: str,
    system_prompt: str,
    description: str = None,
    traits: List[str] = None,
    tone: str = "friendly",
    expertise_areas: List[str] = None
) -> int:
    """Create an AI personality"""
    async with get_connection() as conn:
        personality_id = await conn.fetchval('''
            INSERT INTO ai_personalities (user_id, name, description, system_prompt, traits, tone, expertise_areas)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING id
        ''', user_id, name, description, system_prompt, json.dumps(traits or []), tone, expertise_areas or [])
        return personality_id


async def get_user_personalities(user_id: int) -> List[Dict[str, Any]]:
    """Get user's AI personalities"""
    async with get_connection() as conn:
        rows = await conn.fetch('''
            SELECT * FROM ai_personalities WHERE user_id = $1
            ORDER BY is_default DESC, is_active DESC, name ASC
        ''', user_id)
        return [dict(row) for row in rows]


async def get_active_personality(user_id: int) -> Optional[Dict[str, Any]]:
    """Get user's active personality"""
    async with get_connection() as conn:
        personality = await conn.fetchrow('''
            SELECT * FROM ai_personalities WHERE user_id = $1 AND is_active = TRUE
        ''', user_id)
        return dict(personality) if personality else None


async def set_active_personality(user_id: int, personality_id: int) -> bool:
    """Set active personality"""
    async with get_connection() as conn:
        await conn.execute(
            "UPDATE ai_personalities SET is_active = FALSE WHERE user_id = $1",
            user_id
        )
        result = await conn.execute('''
            UPDATE ai_personalities SET is_active = TRUE WHERE id = $1 AND user_id = $2
        ''', personality_id, user_id)
        
        await conn.execute('''
            UPDATE user_sessions SET active_personality_id = $2 WHERE user_id = $1
        ''', user_id, personality_id)
        
        return "UPDATE 1" in result


# =====================================================
# POLL OPERATIONS
# =====================================================

async def create_poll(
    user_id: int,
    question: str,
    options: List[str],
    poll_type: str = "regular",
    is_anonymous: bool = True,
    allows_multiple: bool = False,
    correct_option_id: int = None,
    explanation: str = None
) -> int:
    """Create a poll"""
    async with get_connection() as conn:
        poll_id = await conn.fetchval('''
            INSERT INTO polls (user_id, question, options, poll_type, is_anonymous, allows_multiple, correct_option_id, explanation)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING id
        ''', user_id, question, json.dumps(options), poll_type, is_anonymous, allows_multiple, correct_option_id, explanation)
        
        await increment_stat(user_id, "total_polls_created")
        return poll_id


async def get_user_polls(user_id: int, include_closed: bool = False, limit: int = 20) -> List[Dict[str, Any]]:
    """Get user's polls"""
    async with get_connection() as conn:
        if include_closed:
            rows = await conn.fetch('''
                SELECT * FROM polls WHERE user_id = $1
                ORDER BY created_at DESC LIMIT $2
            ''', user_id, limit)
        else:
            rows = await conn.fetch('''
                SELECT * FROM polls WHERE user_id = $1 AND is_closed = FALSE
                ORDER BY created_at DESC LIMIT $2
            ''', user_id, limit)
        return [dict(row) for row in rows]


# =====================================================
# ANALYTICS OPERATIONS
# =====================================================

async def log_event(user_id: int, event_type: str, event_data: Dict = None, category: str = None):
    """Log an analytics event"""
    async with get_connection() as conn:
        await conn.execute('''
            INSERT INTO analytics_events (user_id, event_type, event_category, event_data)
            VALUES ($1, $2, $3, $4)
        ''', user_id, event_type, category, json.dumps(event_data or {}))


async def get_user_activity(user_id: int, days: int = 7) -> Dict[str, Any]:
    """Get user activity summary"""
    async with get_connection() as conn:
        events = await conn.fetch('''
            SELECT event_type, COUNT(*) as count
            FROM analytics_events
            WHERE user_id = $1 AND created_at >= NOW() - INTERVAL '%s days'
            GROUP BY event_type
        ''' % days, user_id)
        
        daily = await conn.fetch('''
            SELECT DATE(created_at) as date, COUNT(*) as count
            FROM analytics_events
            WHERE user_id = $1 AND created_at >= NOW() - INTERVAL '%s days'
            GROUP BY DATE(created_at)
            ORDER BY date
        ''' % days, user_id)
        
        return {
            "events_by_type": {row["event_type"]: row["count"] for row in events},
            "daily_activity": [{"date": str(row["date"]), "count": row["count"]} for row in daily]
        }
