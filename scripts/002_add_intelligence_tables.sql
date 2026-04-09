-- Waya Bot Builder v2.0.0 - Intelligence Core Database Migration
-- This migration adds tables for Memory, Learning, Cognitive, and Proactive engines

-- ============================================================================
-- MEMORY ENGINE TABLES
-- ============================================================================

-- Long-term memory storage
CREATE TABLE IF NOT EXISTS user_memories (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    memory_type VARCHAR(50) NOT NULL DEFAULT 'fact',  -- fact, event, preference, relationship, skill
    content TEXT NOT NULL,
    embedding VECTOR(1536),  -- For semantic search (if pgvector is available)
    importance FLOAT DEFAULT 0.5,  -- 0.0 to 1.0
    access_count INTEGER DEFAULT 0,
    last_accessed TIMESTAMP WITH TIME ZONE,
    source VARCHAR(100),  -- 'conversation', 'explicit', 'inferred'
    context JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE  -- NULL = never expires
);

CREATE INDEX IF NOT EXISTS idx_user_memories_user ON user_memories(user_id);
CREATE INDEX IF NOT EXISTS idx_user_memories_type ON user_memories(user_id, memory_type);
CREATE INDEX IF NOT EXISTS idx_user_memories_importance ON user_memories(user_id, importance DESC);

-- Memory consolidation log (for memory decay and reinforcement)
CREATE TABLE IF NOT EXISTS memory_consolidation_log (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    memory_id INTEGER REFERENCES user_memories(id) ON DELETE CASCADE,
    action VARCHAR(50) NOT NULL,  -- 'reinforce', 'decay', 'merge', 'archive'
    old_importance FLOAT,
    new_importance FLOAT,
    reason TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- LEARNING ENGINE TABLES
-- ============================================================================

-- User preferences and learned patterns
CREATE TABLE IF NOT EXISTS user_preferences (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    preference_key VARCHAR(100) NOT NULL,
    preference_value JSONB NOT NULL,
    confidence FLOAT DEFAULT 0.5,  -- How confident we are about this preference
    source VARCHAR(50) DEFAULT 'inferred',  -- 'explicit', 'inferred', 'default'
    evidence_count INTEGER DEFAULT 1,  -- How many times this was observed
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, preference_key)
);

CREATE INDEX IF NOT EXISTS idx_user_preferences_user ON user_preferences(user_id);

-- User interaction patterns
CREATE TABLE IF NOT EXISTS user_patterns (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    pattern_type VARCHAR(50) NOT NULL,  -- 'time_active', 'topic_interest', 'communication_style', 'response_preference'
    pattern_data JSONB NOT NULL,
    confidence FLOAT DEFAULT 0.5,
    sample_count INTEGER DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_user_patterns_user ON user_patterns(user_id);
CREATE INDEX IF NOT EXISTS idx_user_patterns_type ON user_patterns(user_id, pattern_type);

-- Feedback log for learning
CREATE TABLE IF NOT EXISTS user_feedback (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    message_id BIGINT,
    feedback_type VARCHAR(50) NOT NULL,  -- 'positive', 'negative', 'correction', 'explicit'
    feedback_data JSONB,
    original_response TEXT,
    processed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_user_feedback_user ON user_feedback(user_id);
CREATE INDEX IF NOT EXISTS idx_user_feedback_unprocessed ON user_feedback(processed) WHERE processed = FALSE;

-- ============================================================================
-- COGNITIVE ENGINE TABLES
-- ============================================================================

-- Reasoning traces for debugging and learning
CREATE TABLE IF NOT EXISTS reasoning_traces (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    message_id BIGINT,
    trace_type VARCHAR(50) NOT NULL,  -- 'react', 'chain_of_thought', 'reflection'
    steps JSONB NOT NULL,  -- Array of reasoning steps
    final_action TEXT,
    success BOOLEAN,
    execution_time_ms INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_reasoning_traces_user ON reasoning_traces(user_id);

-- Tool usage history
CREATE TABLE IF NOT EXISTS tool_usage (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    tool_name VARCHAR(50) NOT NULL,
    tool_input JSONB,
    tool_output JSONB,
    success BOOLEAN DEFAULT TRUE,
    execution_time_ms INTEGER,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_tool_usage_user ON tool_usage(user_id);
CREATE INDEX IF NOT EXISTS idx_tool_usage_tool ON tool_usage(tool_name);

-- ============================================================================
-- PROACTIVE ENGINE TABLES
-- ============================================================================

-- Proactive suggestions queue
CREATE TABLE IF NOT EXISTS proactive_suggestions (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    suggestion_type VARCHAR(50) NOT NULL,  -- 'reminder', 'insight', 'recommendation', 'briefing'
    content TEXT NOT NULL,
    priority INTEGER DEFAULT 5,  -- 1-10, higher = more important
    context JSONB DEFAULT '{}',
    scheduled_for TIMESTAMP WITH TIME ZONE,
    sent BOOLEAN DEFAULT FALSE,
    sent_at TIMESTAMP WITH TIME ZONE,
    dismissed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_proactive_suggestions_user ON proactive_suggestions(user_id);
CREATE INDEX IF NOT EXISTS idx_proactive_suggestions_pending ON proactive_suggestions(user_id, sent, scheduled_for) WHERE sent = FALSE;

-- User briefing preferences
CREATE TABLE IF NOT EXISTS briefing_preferences (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL UNIQUE,
    enabled BOOLEAN DEFAULT FALSE,
    preferred_time TIME DEFAULT '09:00:00',
    timezone VARCHAR(50) DEFAULT 'UTC',
    include_weather BOOLEAN DEFAULT TRUE,
    include_tasks BOOLEAN DEFAULT TRUE,
    include_reminders BOOLEAN DEFAULT TRUE,
    include_news BOOLEAN DEFAULT FALSE,
    custom_topics JSONB DEFAULT '[]',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Pattern detection results
CREATE TABLE IF NOT EXISTS detected_patterns (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    pattern_name VARCHAR(100) NOT NULL,
    pattern_description TEXT,
    confidence FLOAT DEFAULT 0.5,
    supporting_evidence JSONB DEFAULT '[]',
    actioned BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_detected_patterns_user ON detected_patterns(user_id);

-- ============================================================================
-- PROFILE ANALYSIS CACHE
-- ============================================================================

-- Cache for analyzed Telegram profiles
CREATE TABLE IF NOT EXISTS profile_analysis_cache (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,
    user_id_telegram BIGINT,
    profile_data JSONB NOT NULL,
    ai_analysis TEXT,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    access_count INTEGER DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_profile_cache_username ON profile_analysis_cache(username);

-- ============================================================================
-- UPDATE FUNCTIONS
-- ============================================================================

-- Function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply triggers to tables with updated_at
DO $$
BEGIN
    -- user_memories
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_user_memories_updated_at') THEN
        CREATE TRIGGER update_user_memories_updated_at
            BEFORE UPDATE ON user_memories
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
    
    -- user_preferences
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_user_preferences_updated_at') THEN
        CREATE TRIGGER update_user_preferences_updated_at
            BEFORE UPDATE ON user_preferences
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
    
    -- user_patterns
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_user_patterns_updated_at') THEN
        CREATE TRIGGER update_user_patterns_updated_at
            BEFORE UPDATE ON user_patterns
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
    
    -- briefing_preferences
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_briefing_preferences_updated_at') THEN
        CREATE TRIGGER update_briefing_preferences_updated_at
            BEFORE UPDATE ON briefing_preferences
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
END
$$;

-- ============================================================================
-- MIGRATION COMPLETE
-- ============================================================================
-- Tables created:
-- - user_memories: Long-term memory storage
-- - memory_consolidation_log: Memory reinforcement tracking
-- - user_preferences: Learned user preferences
-- - user_patterns: Detected behavioral patterns
-- - user_feedback: Feedback for learning
-- - reasoning_traces: Cognitive reasoning logs
-- - tool_usage: Tool execution history
-- - proactive_suggestions: Smart suggestion queue
-- - briefing_preferences: Daily briefing settings
-- - detected_patterns: Pattern detection results
-- - profile_analysis_cache: Telegram profile cache
