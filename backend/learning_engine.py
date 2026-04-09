"""
Waya Bot Builder - Learning Engine
Continuous learning and personalization system.
Learns from interactions to improve responses and adapt to user preferences.
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Optional, List, Dict, Any, Tuple
import re

logger = logging.getLogger(__name__)


class CommunicationStyle(str, Enum):
    """User communication style preferences"""
    FORMAL = "formal"
    CASUAL = "casual"
    TECHNICAL = "technical"
    SIMPLE = "simple"
    VERBOSE = "verbose"
    CONCISE = "concise"
    FRIENDLY = "friendly"
    PROFESSIONAL = "professional"


class ExpertiseLevel(str, Enum):
    """User expertise level in various topics"""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class FeedbackType(str, Enum):
    """Types of feedback"""
    THUMBS_UP = "thumbs_up"
    THUMBS_DOWN = "thumbs_down"
    REACTION = "reaction"
    CORRECTION = "correction"
    FOLLOW_UP = "follow_up"
    NO_RESPONSE = "no_response"
    LONG_RESPONSE = "long_response"


@dataclass
class UserProfile:
    """Comprehensive user profile for personalization"""
    user_id: int
    
    # Communication preferences
    preferred_style: CommunicationStyle = CommunicationStyle.FRIENDLY
    preferred_response_length: str = "medium"  # short, medium, long
    preferred_language: str = "en"
    use_emojis: bool = True
    formality_level: float = 0.5  # 0 = very casual, 1 = very formal
    
    # Expertise and interests
    expertise_levels: Dict[str, ExpertiseLevel] = field(default_factory=dict)
    topics_of_interest: List[str] = field(default_factory=list)
    topics_to_avoid: List[str] = field(default_factory=list)
    
    # Behavioral patterns
    typical_message_length: int = 50
    avg_response_time_hours: float = 0.0
    active_hours: List[int] = field(default_factory=list)  # 0-23
    active_days: List[int] = field(default_factory=list)  # 0-6
    
    # Engagement metrics
    total_interactions: int = 0
    positive_feedback_count: int = 0
    negative_feedback_count: int = 0
    engagement_score: float = 0.5
    
    # Learning metadata
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    confidence_score: float = 0.5
    
    def to_context_string(self) -> str:
        """Convert profile to context string for AI"""
        parts = []
        
        # Communication style
        parts.append(f"- Prefers {self.preferred_style.value} communication")
        parts.append(f"- Likes {self.preferred_response_length} responses")
        
        if self.formality_level > 0.7:
            parts.append("- Prefers formal language")
        elif self.formality_level < 0.3:
            parts.append("- Prefers casual language")
        
        # Expertise
        if self.expertise_levels:
            expert_topics = [t for t, l in self.expertise_levels.items() if l in [ExpertiseLevel.ADVANCED, ExpertiseLevel.EXPERT]]
            if expert_topics:
                parts.append(f"- Expert in: {', '.join(expert_topics[:3])}")
        
        # Interests
        if self.topics_of_interest:
            parts.append(f"- Interested in: {', '.join(self.topics_of_interest[:5])}")
        
        return "\n".join(parts)


@dataclass
class InteractionFeedback:
    """Feedback from a single interaction"""
    user_id: int
    message_id: Optional[int]
    feedback_type: FeedbackType
    user_message: str
    bot_response: str
    feedback_data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class LearningSignal:
    """A signal that indicates something to learn from"""
    signal_type: str
    content: str
    strength: float  # -1 to 1 (negative = bad, positive = good)
    topic: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class LearningEngine:
    """
    Learns from user interactions to improve personalization.
    
    Learning sources:
    1. Explicit feedback (thumbs up/down, corrections)
    2. Implicit feedback (follow-up questions, response time)
    3. Behavioral patterns (message length, timing, topics)
    4. Conversation outcomes (resolved vs unresolved)
    """
    
    def __init__(self, db_pool):
        self.db_pool = db_pool
        self._profile_cache: Dict[int, UserProfile] = {}
        self._cache_ttl: Dict[int, datetime] = {}
        self.cache_duration = timedelta(minutes=30)
    
    async def init_schema(self):
        """Initialize learning tables"""
        async with self.db_pool.acquire() as conn:
            await conn.execute('''
                -- User learning profiles
                CREATE TABLE IF NOT EXISTS user_learning_profiles (
                    user_id BIGINT PRIMARY KEY,
                    preferred_style VARCHAR(50) DEFAULT 'friendly',
                    preferred_response_length VARCHAR(20) DEFAULT 'medium',
                    preferred_language VARCHAR(10) DEFAULT 'en',
                    use_emojis BOOLEAN DEFAULT TRUE,
                    formality_level FLOAT DEFAULT 0.5,
                    expertise_levels JSONB DEFAULT '{}',
                    topics_of_interest TEXT[] DEFAULT '{}',
                    topics_to_avoid TEXT[] DEFAULT '{}',
                    typical_message_length INT DEFAULT 50,
                    avg_response_time_hours FLOAT DEFAULT 0,
                    active_hours INT[] DEFAULT '{}',
                    active_days INT[] DEFAULT '{}',
                    total_interactions INT DEFAULT 0,
                    positive_feedback_count INT DEFAULT 0,
                    negative_feedback_count INT DEFAULT 0,
                    engagement_score FLOAT DEFAULT 0.5,
                    confidence_score FLOAT DEFAULT 0.5,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW(),
                    
                    CONSTRAINT fk_user_learning FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );
                
                -- Interaction feedback history
                CREATE TABLE IF NOT EXISTS interaction_feedback (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    message_id BIGINT,
                    feedback_type VARCHAR(50) NOT NULL,
                    user_message TEXT,
                    bot_response TEXT,
                    feedback_data JSONB DEFAULT '{}',
                    processed BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    
                    CONSTRAINT fk_feedback_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );
                
                CREATE INDEX IF NOT EXISTS idx_feedback_user ON interaction_feedback(user_id);
                CREATE INDEX IF NOT EXISTS idx_feedback_unprocessed ON interaction_feedback(processed) WHERE processed = FALSE;
                
                -- Learning signals (aggregated patterns)
                CREATE TABLE IF NOT EXISTS learning_signals (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    signal_type VARCHAR(50) NOT NULL,
                    content TEXT,
                    strength FLOAT DEFAULT 0,
                    topic VARCHAR(100),
                    metadata JSONB DEFAULT '{}',
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    
                    CONSTRAINT fk_signal_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );
                
                CREATE INDEX IF NOT EXISTS idx_signal_user ON learning_signals(user_id, created_at DESC);
            ''')
            logger.info("Learning engine schema initialized")
    
    async def get_user_profile(self, user_id: int) -> UserProfile:
        """Get or create user learning profile"""
        # Check cache
        if user_id in self._profile_cache:
            cache_time = self._cache_ttl.get(user_id)
            if cache_time and datetime.now(timezone.utc) - cache_time < self.cache_duration:
                return self._profile_cache[user_id]
        
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow('''
                SELECT * FROM user_learning_profiles WHERE user_id = $1
            ''', user_id)
            
            if row:
                profile = UserProfile(
                    user_id=user_id,
                    preferred_style=CommunicationStyle(row['preferred_style']),
                    preferred_response_length=row['preferred_response_length'],
                    preferred_language=row['preferred_language'],
                    use_emojis=row['use_emojis'],
                    formality_level=row['formality_level'],
                    expertise_levels={k: ExpertiseLevel(v) for k, v in (row['expertise_levels'] or {}).items()},
                    topics_of_interest=row['topics_of_interest'] or [],
                    topics_to_avoid=row['topics_to_avoid'] or [],
                    typical_message_length=row['typical_message_length'],
                    avg_response_time_hours=row['avg_response_time_hours'],
                    active_hours=row['active_hours'] or [],
                    active_days=row['active_days'] or [],
                    total_interactions=row['total_interactions'],
                    positive_feedback_count=row['positive_feedback_count'],
                    negative_feedback_count=row['negative_feedback_count'],
                    engagement_score=row['engagement_score'],
                    confidence_score=row['confidence_score'],
                    last_updated=row['updated_at']
                )
            else:
                # Create default profile
                profile = UserProfile(user_id=user_id)
                await self._create_profile(profile)
        
        # Update cache
        self._profile_cache[user_id] = profile
        self._cache_ttl[user_id] = datetime.now(timezone.utc)
        
        return profile
    
    async def _create_profile(self, profile: UserProfile):
        """Create a new user learning profile"""
        async with self.db_pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO user_learning_profiles (user_id)
                VALUES ($1)
                ON CONFLICT (user_id) DO NOTHING
            ''', profile.user_id)
    
    async def process_interaction(
        self,
        user_id: int,
        user_message: str,
        bot_response: str,
        metadata: Optional[Dict] = None
    ) -> List[LearningSignal]:
        """
        Process an interaction and extract learning signals.
        This is called after every conversation turn.
        """
        signals = []
        profile = await self.get_user_profile(user_id)
        
        # Analyze message characteristics
        signals.extend(self._analyze_message_style(user_message, profile))
        
        # Analyze topics
        signals.extend(self._analyze_topics(user_message))
        
        # Update activity patterns
        await self._update_activity_patterns(user_id)
        
        # Store signals
        for signal in signals:
            await self._store_signal(user_id, signal)
        
        # Update profile incrementally
        await self._update_profile_from_signals(user_id, signals)
        
        # Increment interaction count
        async with self.db_pool.acquire() as conn:
            await conn.execute('''
                UPDATE user_learning_profiles
                SET total_interactions = total_interactions + 1,
                    updated_at = NOW()
                WHERE user_id = $1
            ''', user_id)
        
        # Invalidate cache
        self._invalidate_cache(user_id)
        
        return signals
    
    async def record_feedback(
        self,
        user_id: int,
        feedback_type: FeedbackType,
        user_message: str = "",
        bot_response: str = "",
        feedback_data: Optional[Dict] = None
    ):
        """Record explicit or implicit feedback"""
        async with self.db_pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO interaction_feedback
                (user_id, feedback_type, user_message, bot_response, feedback_data)
                VALUES ($1, $2, $3, $4, $5)
            ''',
                user_id,
                feedback_type.value,
                user_message,
                bot_response,
                json.dumps(feedback_data or {})
            )
        
        # Update feedback counts
        if feedback_type == FeedbackType.THUMBS_UP:
            await self._increment_positive_feedback(user_id)
        elif feedback_type == FeedbackType.THUMBS_DOWN:
            await self._increment_negative_feedback(user_id)
        
        # Invalidate cache
        self._invalidate_cache(user_id)
    
    async def learn_from_correction(
        self,
        user_id: int,
        original_response: str,
        correction_message: str
    ):
        """Learn from user corrections"""
        # Record as negative feedback with correction data
        await self.record_feedback(
            user_id,
            FeedbackType.CORRECTION,
            correction_message,
            original_response,
            {"correction_type": "user_corrected"}
        )
        
        # Extract what went wrong
        signal = LearningSignal(
            signal_type="correction",
            content=f"User corrected: {correction_message[:200]}",
            strength=-0.3,  # Negative signal
            metadata={"original": original_response[:200]}
        )
        await self._store_signal(user_id, signal)
    
    async def get_personalization_context(self, user_id: int) -> str:
        """
        Get personalization context to inject into AI prompts.
        This shapes how the bot responds to this specific user.
        """
        profile = await self.get_user_profile(user_id)
        
        context_parts = ["### User Personalization:"]
        context_parts.append(profile.to_context_string())
        
        # Add recent feedback patterns
        feedback_summary = await self._get_feedback_summary(user_id)
        if feedback_summary:
            context_parts.append(f"\n### Recent feedback patterns:\n{feedback_summary}")
        
        return "\n".join(context_parts)
    
    async def adapt_response(
        self,
        user_id: int,
        response: str,
        profile: Optional[UserProfile] = None
    ) -> str:
        """
        Adapt a response based on user preferences.
        Post-processes the AI response to match user style.
        """
        if not profile:
            profile = await self.get_user_profile(user_id)
        
        adapted = response
        
        # Adjust length if needed
        if profile.preferred_response_length == "short" and len(adapted) > 300:
            # Try to shorten (this is a simple heuristic)
            sentences = adapted.split('. ')
            if len(sentences) > 3:
                adapted = '. '.join(sentences[:3]) + '.'
        
        # Remove or add emojis based on preference
        if not profile.use_emojis:
            # Remove common emojis
            import re
            adapted = re.sub(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF]', '', adapted)
        
        # Adjust formality (very basic)
        if profile.formality_level > 0.7:
            # Make more formal
            adapted = adapted.replace("gonna", "going to")
            adapted = adapted.replace("wanna", "want to")
            adapted = adapted.replace("kinda", "kind of")
        
        return adapted.strip()
    
    def _analyze_message_style(self, message: str, profile: UserProfile) -> List[LearningSignal]:
        """Analyze user message style"""
        signals = []
        
        # Message length
        msg_len = len(message)
        if msg_len < 20:
            signals.append(LearningSignal(
                signal_type="style",
                content="short_messages",
                strength=0.1
            ))
        elif msg_len > 200:
            signals.append(LearningSignal(
                signal_type="style",
                content="long_messages",
                strength=0.1
            ))
        
        # Formality indicators
        formal_indicators = ["please", "thank you", "could you", "would you", "kindly"]
        casual_indicators = ["hey", "yo", "lol", "haha", "btw", "gonna", "wanna"]
        
        msg_lower = message.lower()
        formal_count = sum(1 for f in formal_indicators if f in msg_lower)
        casual_count = sum(1 for c in casual_indicators if c in msg_lower)
        
        if formal_count > casual_count:
            signals.append(LearningSignal(
                signal_type="formality",
                content="formal",
                strength=0.05 * formal_count
            ))
        elif casual_count > formal_count:
            signals.append(LearningSignal(
                signal_type="formality",
                content="casual",
                strength=-0.05 * casual_count
            ))
        
        # Emoji usage
        emoji_pattern = re.compile(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF]')
        emoji_count = len(emoji_pattern.findall(message))
        if emoji_count > 0:
            signals.append(LearningSignal(
                signal_type="emoji_usage",
                content=f"uses_emojis",
                strength=0.1 * min(emoji_count, 3)
            ))
        
        return signals
    
    def _analyze_topics(self, message: str) -> List[LearningSignal]:
        """Analyze topics mentioned in message"""
        signals = []
        msg_lower = message.lower()
        
        # Topic keywords (simplified)
        topic_keywords = {
            "technology": ["code", "programming", "software", "app", "computer", "tech"],
            "business": ["business", "work", "meeting", "project", "company", "client"],
            "health": ["health", "exercise", "diet", "doctor", "medical", "workout"],
            "education": ["learn", "study", "course", "school", "university", "exam"],
            "entertainment": ["movie", "music", "game", "book", "show", "netflix"],
            "finance": ["money", "budget", "invest", "stock", "crypto", "bank"],
            "travel": ["travel", "trip", "vacation", "flight", "hotel", "destination"],
            "food": ["food", "recipe", "cook", "restaurant", "meal", "eat"]
        }
        
        for topic, keywords in topic_keywords.items():
            if any(kw in msg_lower for kw in keywords):
                signals.append(LearningSignal(
                    signal_type="topic_interest",
                    content=topic,
                    strength=0.1,
                    topic=topic
                ))
        
        return signals
    
    async def _update_activity_patterns(self, user_id: int):
        """Update user activity patterns"""
        now = datetime.now(timezone.utc)
        hour = now.hour
        day = now.weekday()
        
        async with self.db_pool.acquire() as conn:
            # Update active hours (running list)
            await conn.execute('''
                UPDATE user_learning_profiles
                SET active_hours = array_append(
                    (SELECT active_hours[2:24] FROM user_learning_profiles WHERE user_id = $1),
                    $2::INT
                ),
                active_days = array_append(
                    (SELECT active_days[2:7] FROM user_learning_profiles WHERE user_id = $1),
                    $3::INT
                )
                WHERE user_id = $1
            ''', user_id, hour, day)
    
    async def _store_signal(self, user_id: int, signal: LearningSignal):
        """Store a learning signal"""
        async with self.db_pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO learning_signals
                (user_id, signal_type, content, strength, topic, metadata)
                VALUES ($1, $2, $3, $4, $5, $6)
            ''',
                user_id,
                signal.signal_type,
                signal.content,
                signal.strength,
                signal.topic,
                json.dumps(signal.metadata)
            )
    
    async def _update_profile_from_signals(self, user_id: int, signals: List[LearningSignal]):
        """Update user profile based on learning signals"""
        if not signals:
            return
        
        profile = await self.get_user_profile(user_id)
        
        for signal in signals:
            # Update formality level
            if signal.signal_type == "formality":
                adjustment = signal.strength * 0.1
                profile.formality_level = max(0, min(1, profile.formality_level + adjustment))
            
            # Update topics of interest
            if signal.signal_type == "topic_interest" and signal.topic:
                if signal.topic not in profile.topics_of_interest:
                    profile.topics_of_interest.append(signal.topic)
                    # Keep only top 10 topics
                    if len(profile.topics_of_interest) > 10:
                        profile.topics_of_interest = profile.topics_of_interest[-10:]
            
            # Update emoji preference
            if signal.signal_type == "emoji_usage":
                profile.use_emojis = signal.strength > 0
        
        # Save updated profile
        async with self.db_pool.acquire() as conn:
            await conn.execute('''
                UPDATE user_learning_profiles
                SET formality_level = $2,
                    topics_of_interest = $3,
                    use_emojis = $4,
                    updated_at = NOW()
                WHERE user_id = $1
            ''',
                user_id,
                profile.formality_level,
                profile.topics_of_interest,
                profile.use_emojis
            )
    
    async def _increment_positive_feedback(self, user_id: int):
        """Increment positive feedback count"""
        async with self.db_pool.acquire() as conn:
            await conn.execute('''
                UPDATE user_learning_profiles
                SET positive_feedback_count = positive_feedback_count + 1,
                    engagement_score = LEAST(engagement_score + 0.05, 1.0)
                WHERE user_id = $1
            ''', user_id)
    
    async def _increment_negative_feedback(self, user_id: int):
        """Increment negative feedback count"""
        async with self.db_pool.acquire() as conn:
            await conn.execute('''
                UPDATE user_learning_profiles
                SET negative_feedback_count = negative_feedback_count + 1,
                    engagement_score = GREATEST(engagement_score - 0.05, 0.0)
                WHERE user_id = $1
            ''', user_id)
    
    async def _get_feedback_summary(self, user_id: int) -> str:
        """Get summary of recent feedback"""
        async with self.db_pool.acquire() as conn:
            # Count recent feedback by type
            rows = await conn.fetch('''
                SELECT feedback_type, COUNT(*) as count
                FROM interaction_feedback
                WHERE user_id = $1
                AND created_at > NOW() - INTERVAL '7 days'
                GROUP BY feedback_type
            ''', user_id)
            
            if not rows:
                return ""
            
            parts = []
            for row in rows:
                parts.append(f"- {row['feedback_type']}: {row['count']}")
            
            return "\n".join(parts)
    
    def _invalidate_cache(self, user_id: int):
        """Invalidate profile cache for user"""
        if user_id in self._profile_cache:
            del self._profile_cache[user_id]
        if user_id in self._cache_ttl:
            del self._cache_ttl[user_id]
    
    async def run_batch_learning(self):
        """
        Run batch learning on unprocessed feedback.
        Should be run periodically (e.g., daily).
        """
        async with self.db_pool.acquire() as conn:
            # Get unprocessed feedback
            rows = await conn.fetch('''
                SELECT DISTINCT user_id FROM interaction_feedback
                WHERE processed = FALSE
                LIMIT 100
            ''')
            
            for row in rows:
                user_id = row['user_id']
                
                # Process feedback for user
                feedback_rows = await conn.fetch('''
                    SELECT * FROM interaction_feedback
                    WHERE user_id = $1 AND processed = FALSE
                    ORDER BY created_at
                ''', user_id)
                
                # Analyze patterns
                positive = sum(1 for f in feedback_rows if f['feedback_type'] == 'thumbs_up')
                negative = sum(1 for f in feedback_rows if f['feedback_type'] == 'thumbs_down')
                
                # Update confidence score
                if positive + negative > 0:
                    ratio = positive / (positive + negative)
                    await conn.execute('''
                        UPDATE user_learning_profiles
                        SET confidence_score = (confidence_score + $2) / 2
                        WHERE user_id = $1
                    ''', user_id, ratio)
                
                # Mark as processed
                await conn.execute('''
                    UPDATE interaction_feedback
                    SET processed = TRUE
                    WHERE user_id = $1 AND processed = FALSE
                ''', user_id)
            
            logger.info(f"Batch learning completed for {len(rows)} users")


# Global learning engine instance
_learning_engine: Optional[LearningEngine] = None


async def init_learning_engine(db_pool) -> LearningEngine:
    """Initialize the global learning engine"""
    global _learning_engine
    _learning_engine = LearningEngine(db_pool)
    await _learning_engine.init_schema()
    return _learning_engine


def get_learning_engine() -> Optional[LearningEngine]:
    """Get the global learning engine"""
    return _learning_engine
