"""
Waya Bot Builder - Proactive Engine
Anticipates user needs with smart suggestions, daily briefings, and reminders.
The bot doesn't just respond - it proactively helps.
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta, time
from enum import Enum
from typing import Optional, List, Dict, Any, Tuple
import random

logger = logging.getLogger(__name__)


class ProactiveActionType(str, Enum):
    """Types of proactive actions"""
    DAILY_BRIEFING = "daily_briefing"
    SMART_SUGGESTION = "smart_suggestion"
    FOLLOW_UP = "follow_up"
    REMINDER_PROMPT = "reminder_prompt"
    PATTERN_INSIGHT = "pattern_insight"
    CHECK_IN = "check_in"
    TIP_OF_DAY = "tip_of_day"
    CONVERSATION_PROMPT = "conversation_prompt"


@dataclass
class ProactiveAction:
    """A proactive action to take"""
    action_type: ProactiveActionType
    title: str
    message: str
    priority: int = 5  # 1-10, higher = more important
    trigger_time: Optional[datetime] = None
    context: Dict[str, Any] = field(default_factory=dict)
    expires_at: Optional[datetime] = None
    
    def is_expired(self) -> bool:
        if not self.expires_at:
            return False
        return datetime.now(timezone.utc) > self.expires_at


@dataclass 
class DailyBriefing:
    """Morning briefing content"""
    user_id: int
    greeting: str
    date: datetime
    
    # Tasks and reminders
    pending_tasks: List[Dict] = field(default_factory=list)
    upcoming_reminders: List[Dict] = field(default_factory=list)
    
    # External info
    weather: Optional[Dict] = None
    news_headlines: List[str] = field(default_factory=list)
    
    # Personal insights
    streak_info: Optional[str] = None
    pattern_insight: Optional[str] = None
    motivation_quote: Optional[str] = None
    
    # Follow-ups from past conversations
    follow_up_items: List[str] = field(default_factory=list)
    
    def to_message(self) -> str:
        """Convert briefing to formatted message"""
        parts = [self.greeting, ""]
        
        # Date
        parts.append(f"**{self.date.strftime('%A, %B %d, %Y')}**\n")
        
        # Weather
        if self.weather:
            parts.append(f"**Weather:** {self.weather.get('conditions', 'N/A')}, {self.weather.get('temperature', 'N/A')}\n")
        
        # Tasks
        if self.pending_tasks:
            parts.append("**Today's Tasks:**")
            for task in self.pending_tasks[:5]:
                status = "[ ]" if task.get('status') != 'completed' else "[x]"
                parts.append(f"  {status} {task.get('title', 'Task')}")
            parts.append("")
        
        # Reminders
        if self.upcoming_reminders:
            parts.append("**Upcoming Reminders:**")
            for rem in self.upcoming_reminders[:3]:
                time_str = rem.get('remind_at', '')
                if isinstance(time_str, datetime):
                    time_str = time_str.strftime('%H:%M')
                parts.append(f"  - {rem.get('title', 'Reminder')} ({time_str})")
            parts.append("")
        
        # Follow-ups
        if self.follow_up_items:
            parts.append("**Follow-ups from our conversations:**")
            for item in self.follow_up_items[:3]:
                parts.append(f"  - {item}")
            parts.append("")
        
        # Motivation
        if self.motivation_quote:
            parts.append(f"\n*{self.motivation_quote}*")
        
        # Pattern insight
        if self.pattern_insight:
            parts.append(f"\n{self.pattern_insight}")
        
        return "\n".join(parts)


class SuggestionGenerator:
    """Generates contextual suggestions based on conversation"""
    
    # Quick reply templates by context
    QUICK_REPLIES = {
        "greeting": [
            "How can I help you today?",
            "What's on your mind?",
            "Ready when you are!"
        ],
        "task_created": [
            "Set a reminder",
            "Add more tasks",
            "Show my tasks"
        ],
        "reminder_set": [
            "Set another",
            "Show reminders",
            "Thank you!"
        ],
        "question_answered": [
            "Tell me more",
            "Thanks!",
            "I have another question"
        ],
        "ai_response": [
            "Explain more",
            "Got it, thanks!",
            "That's not quite right"
        ],
        "general": [
            "Help",
            "Show tasks",
            "Create reminder"
        ]
    }
    
    # Follow-up prompts
    FOLLOW_UP_PROMPTS = [
        "Is there anything else you'd like help with?",
        "Let me know if you need anything else!",
        "I'm here if you have more questions.",
        "Feel free to ask if you need clarification."
    ]
    
    @classmethod
    def get_quick_replies(
        cls,
        context: str = "general",
        conversation_topics: List[str] = None
    ) -> List[str]:
        """Get contextual quick reply suggestions"""
        replies = cls.QUICK_REPLIES.get(context, cls.QUICK_REPLIES["general"]).copy()
        
        # Add topic-specific suggestions
        if conversation_topics:
            for topic in conversation_topics[:2]:
                if topic == "technology":
                    replies.append("Tell me about tech news")
                elif topic == "business":
                    replies.append("Help me plan my day")
                elif topic == "health":
                    replies.append("Motivate me!")
        
        return replies[:4]  # Return max 4 suggestions
    
    @classmethod
    def get_follow_up_prompt(cls) -> str:
        """Get a random follow-up prompt"""
        return random.choice(cls.FOLLOW_UP_PROMPTS)


class ProactiveEngine:
    """
    Engine for proactive bot behavior.
    
    Features:
    1. Daily Briefings - Morning summaries with tasks, weather, insights
    2. Smart Suggestions - Context-aware quick replies
    3. Follow-ups - Remember and ask about past topics
    4. Pattern Insights - Notice user patterns and comment
    5. Check-ins - Periodic check-ins for inactive users
    """
    
    def __init__(self, db_pool):
        self.db_pool = db_pool
        self.suggestion_generator = SuggestionGenerator()
        self._briefing_times: Dict[int, time] = {}  # user_id -> preferred briefing time
    
    async def init_schema(self):
        """Initialize proactive engine tables"""
        async with self.db_pool.acquire() as conn:
            await conn.execute('''
                -- Proactive actions queue
                CREATE TABLE IF NOT EXISTS proactive_actions (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    action_type VARCHAR(50) NOT NULL,
                    title VARCHAR(255),
                    message TEXT,
                    priority INT DEFAULT 5,
                    trigger_time TIMESTAMPTZ,
                    context JSONB DEFAULT '{}',
                    expires_at TIMESTAMPTZ,
                    sent BOOLEAN DEFAULT FALSE,
                    sent_at TIMESTAMPTZ,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    
                    CONSTRAINT fk_proactive_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );
                
                CREATE INDEX IF NOT EXISTS idx_proactive_user ON proactive_actions(user_id);
                CREATE INDEX IF NOT EXISTS idx_proactive_pending ON proactive_actions(sent, trigger_time) WHERE sent = FALSE;
                
                -- Follow-up items (things to remember to ask about)
                CREATE TABLE IF NOT EXISTS follow_up_items (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    topic TEXT NOT NULL,
                    original_context TEXT,
                    follow_up_date DATE,
                    is_resolved BOOLEAN DEFAULT FALSE,
                    resolved_at TIMESTAMPTZ,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    
                    CONSTRAINT fk_followup_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );
                
                CREATE INDEX IF NOT EXISTS idx_followup_user ON follow_up_items(user_id, is_resolved);
                
                -- User proactive preferences
                CREATE TABLE IF NOT EXISTS user_proactive_settings (
                    user_id BIGINT PRIMARY KEY,
                    daily_briefing_enabled BOOLEAN DEFAULT TRUE,
                    briefing_time TIME DEFAULT '08:00',
                    check_in_enabled BOOLEAN DEFAULT TRUE,
                    check_in_after_hours INT DEFAULT 48,
                    smart_suggestions_enabled BOOLEAN DEFAULT TRUE,
                    follow_ups_enabled BOOLEAN DEFAULT TRUE,
                    pattern_insights_enabled BOOLEAN DEFAULT TRUE,
                    timezone VARCHAR(50) DEFAULT 'UTC',
                    
                    CONSTRAINT fk_proactive_settings FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );
            ''')
            logger.info("Proactive engine schema initialized")
    
    async def get_user_settings(self, user_id: int) -> Dict[str, Any]:
        """Get user's proactive settings"""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow('''
                SELECT * FROM user_proactive_settings WHERE user_id = $1
            ''', user_id)
            
            if row:
                return dict(row)
            
            # Create default settings
            await conn.execute('''
                INSERT INTO user_proactive_settings (user_id)
                VALUES ($1)
                ON CONFLICT (user_id) DO NOTHING
            ''', user_id)
            
            return {
                "daily_briefing_enabled": True,
                "briefing_time": time(8, 0),
                "check_in_enabled": True,
                "check_in_after_hours": 48,
                "smart_suggestions_enabled": True,
                "follow_ups_enabled": True,
                "pattern_insights_enabled": True,
                "timezone": "UTC"
            }
    
    async def generate_daily_briefing(
        self,
        user_id: int,
        weather_data: Optional[Dict] = None
    ) -> DailyBriefing:
        """Generate a personalized daily briefing"""
        now = datetime.now(timezone.utc)
        
        # Get pending tasks
        tasks = await self._get_user_tasks(user_id)
        
        # Get upcoming reminders
        reminders = await self._get_upcoming_reminders(user_id)
        
        # Get follow-up items
        follow_ups = await self._get_follow_up_items(user_id)
        
        # Get user's streak
        streak_info = await self._get_streak_info(user_id)
        
        # Generate greeting based on time
        hour = now.hour
        if hour < 12:
            greeting = "Good morning!"
        elif hour < 17:
            greeting = "Good afternoon!"
        else:
            greeting = "Good evening!"
        
        # Get motivation quote
        quotes = [
            "Every day is a fresh start.",
            "Small progress is still progress.",
            "You've got this!",
            "Focus on what matters most today.",
            "Make today amazing!",
            "One step at a time.",
            "Your potential is endless.",
            "Believe in yourself today."
        ]
        
        briefing = DailyBriefing(
            user_id=user_id,
            greeting=greeting,
            date=now,
            pending_tasks=tasks[:5],
            upcoming_reminders=reminders[:3],
            weather=weather_data,
            streak_info=streak_info,
            follow_up_items=follow_ups[:3],
            motivation_quote=random.choice(quotes)
        )
        
        return briefing
    
    async def get_smart_suggestions(
        self,
        user_id: int,
        last_message: str,
        last_response: str,
        context: str = "general"
    ) -> List[str]:
        """Get smart suggestions based on conversation context"""
        settings = await self.get_user_settings(user_id)
        
        if not settings.get("smart_suggestions_enabled", True):
            return []
        
        # Detect context from message
        detected_context = self._detect_conversation_context(last_message, last_response)
        
        # Get topic-based suggestions
        topics = await self._get_user_topics(user_id)
        
        return self.suggestion_generator.get_quick_replies(
            context=detected_context or context,
            conversation_topics=topics
        )
    
    async def create_follow_up(
        self,
        user_id: int,
        topic: str,
        original_context: str = "",
        follow_up_days: int = 7
    ):
        """Create a follow-up item to check on later"""
        follow_up_date = datetime.now(timezone.utc).date() + timedelta(days=follow_up_days)
        
        async with self.db_pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO follow_up_items (user_id, topic, original_context, follow_up_date)
                VALUES ($1, $2, $3, $4)
            ''', user_id, topic, original_context, follow_up_date)
    
    async def detect_follow_up_opportunities(
        self,
        user_id: int,
        message: str
    ) -> Optional[str]:
        """Detect if the message mentions something to follow up on"""
        follow_up_triggers = [
            ("interview", "How did your interview go?", 3),
            ("exam", "How did your exam go?", 2),
            ("meeting", "How did your meeting go?", 1),
            ("deadline", "Did you meet your deadline?", 1),
            ("doctor", "How did your appointment go?", 1),
            ("trip", "How was your trip?", 7),
            ("presentation", "How did your presentation go?", 1),
            ("date", "How did your date go?", 1),
            ("birthday", "Hope you had a great birthday!", 1)
        ]
        
        message_lower = message.lower()
        
        for trigger, follow_up_question, days in follow_up_triggers:
            if trigger in message_lower:
                # Check if it's about future (not past)
                future_indicators = ["tomorrow", "next", "upcoming", "soon", "later", "going to", "will"]
                if any(ind in message_lower for ind in future_indicators):
                    await self.create_follow_up(
                        user_id,
                        follow_up_question,
                        message[:200],
                        days
                    )
                    return trigger
        
        return None
    
    async def get_pending_actions(
        self,
        user_id: Optional[int] = None,
        limit: int = 10
    ) -> List[ProactiveAction]:
        """Get pending proactive actions"""
        async with self.db_pool.acquire() as conn:
            if user_id:
                rows = await conn.fetch('''
                    SELECT * FROM proactive_actions
                    WHERE user_id = $1 
                    AND sent = FALSE
                    AND (trigger_time IS NULL OR trigger_time <= NOW())
                    AND (expires_at IS NULL OR expires_at > NOW())
                    ORDER BY priority DESC, created_at
                    LIMIT $2
                ''', user_id, limit)
            else:
                rows = await conn.fetch('''
                    SELECT * FROM proactive_actions
                    WHERE sent = FALSE
                    AND (trigger_time IS NULL OR trigger_time <= NOW())
                    AND (expires_at IS NULL OR expires_at > NOW())
                    ORDER BY priority DESC, created_at
                    LIMIT $1
                ''', limit)
            
            actions = []
            for row in rows:
                actions.append(ProactiveAction(
                    action_type=ProactiveActionType(row['action_type']),
                    title=row['title'] or "",
                    message=row['message'] or "",
                    priority=row['priority'],
                    trigger_time=row['trigger_time'],
                    context=row['context'] or {},
                    expires_at=row['expires_at']
                ))
            
            return actions
    
    async def queue_action(self, user_id: int, action: ProactiveAction):
        """Queue a proactive action"""
        async with self.db_pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO proactive_actions
                (user_id, action_type, title, message, priority, trigger_time, context, expires_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            ''',
                user_id,
                action.action_type.value,
                action.title,
                action.message,
                action.priority,
                action.trigger_time,
                json.dumps(action.context),
                action.expires_at
            )
    
    async def mark_action_sent(self, action_id: int):
        """Mark a proactive action as sent"""
        async with self.db_pool.acquire() as conn:
            await conn.execute('''
                UPDATE proactive_actions
                SET sent = TRUE, sent_at = NOW()
                WHERE id = $1
            ''', action_id)
    
    async def generate_check_in_message(self, user_id: int) -> Optional[str]:
        """Generate a check-in message for inactive user"""
        settings = await self.get_user_settings(user_id)
        
        if not settings.get("check_in_enabled", True):
            return None
        
        # Get last activity
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow('''
                SELECT last_active_at FROM users WHERE id = $1
            ''', user_id)
            
            if not row:
                return None
            
            last_active = row['last_active_at']
            hours_inactive = (datetime.now(timezone.utc) - last_active).total_seconds() / 3600
            
            if hours_inactive < settings.get("check_in_after_hours", 48):
                return None
        
        # Generate check-in message
        check_ins = [
            "Hey! Just checking in. How are things going?",
            "It's been a while! Is there anything I can help you with?",
            "Hi there! I noticed we haven't chatted in a bit. Everything okay?",
            "Hello! Ready to help whenever you need me.",
            "Hey! Just wanted to say hi. Let me know if you need anything!"
        ]
        
        return random.choice(check_ins)
    
    async def generate_pattern_insight(self, user_id: int) -> Optional[str]:
        """Generate an insight based on user patterns"""
        async with self.db_pool.acquire() as conn:
            # Get user's activity patterns
            row = await conn.fetchrow('''
                SELECT active_hours, active_days, total_interactions
                FROM user_learning_profiles
                WHERE user_id = $1
            ''', user_id)
            
            if not row or row['total_interactions'] < 20:
                return None
            
            active_hours = row['active_hours'] or []
            
            if not active_hours:
                return None
            
            # Find most common hour
            hour_counts = {}
            for h in active_hours:
                hour_counts[h] = hour_counts.get(h, 0) + 1
            
            if not hour_counts:
                return None
            
            most_common_hour = max(hour_counts.items(), key=lambda x: x[1])[0]
            
            # Generate insight
            if most_common_hour < 6:
                return "I notice you're often up early! Early bird gets the worm."
            elif most_common_hour < 12:
                return "Morning seems to be your productive time! Great for tackling important tasks."
            elif most_common_hour < 17:
                return "You're most active in the afternoon. Perfect for creative work!"
            elif most_common_hour < 21:
                return "Evening productivity! Some people do their best thinking at this time."
            else:
                return "Night owl! Don't forget to get some rest though."
        
        return None
    
    # Private helper methods
    
    async def _get_user_tasks(self, user_id: int) -> List[Dict]:
        """Get user's pending tasks"""
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch('''
                SELECT id, title, status, priority, due_date
                FROM tasks
                WHERE user_id = $1
                AND status NOT IN ('completed', 'cancelled')
                ORDER BY priority DESC, due_date ASC NULLS LAST
                LIMIT 10
            ''', user_id)
            
            return [dict(row) for row in rows]
    
    async def _get_upcoming_reminders(self, user_id: int) -> List[Dict]:
        """Get user's upcoming reminders"""
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch('''
                SELECT id, title, remind_at
                FROM reminders
                WHERE user_id = $1
                AND is_active = TRUE
                AND is_completed = FALSE
                AND remind_at > NOW()
                AND remind_at < NOW() + INTERVAL '24 hours'
                ORDER BY remind_at
                LIMIT 5
            ''', user_id)
            
            return [dict(row) for row in rows]
    
    async def _get_follow_up_items(self, user_id: int) -> List[str]:
        """Get follow-up items for user"""
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch('''
                SELECT topic FROM follow_up_items
                WHERE user_id = $1
                AND is_resolved = FALSE
                AND follow_up_date <= CURRENT_DATE
                ORDER BY created_at
                LIMIT 5
            ''', user_id)
            
            return [row['topic'] for row in rows]
    
    async def _get_streak_info(self, user_id: int) -> Optional[str]:
        """Get user's streak information"""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow('''
                SELECT streak_days, longest_streak
                FROM user_stats
                WHERE user_id = $1
            ''', user_id)
            
            if row and row['streak_days'] > 0:
                streak = row['streak_days']
                if streak == row['longest_streak'] and streak > 3:
                    return f"You're on a {streak}-day streak - your longest ever!"
                elif streak > 1:
                    return f"You're on a {streak}-day streak. Keep it going!"
            
            return None
    
    async def _get_user_topics(self, user_id: int) -> List[str]:
        """Get user's topics of interest"""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow('''
                SELECT topics_of_interest
                FROM user_learning_profiles
                WHERE user_id = $1
            ''', user_id)
            
            return row['topics_of_interest'] if row else []
    
    def _detect_conversation_context(self, message: str, response: str) -> str:
        """Detect the context of a conversation"""
        msg_lower = message.lower()
        resp_lower = response.lower()
        
        # Greeting detection
        greetings = ["hi", "hello", "hey", "good morning", "good evening", "good night"]
        if any(g in msg_lower for g in greetings) and len(message) < 50:
            return "greeting"
        
        # Task/reminder context
        if any(w in resp_lower for w in ["task created", "added task", "task saved"]):
            return "task_created"
        if any(w in resp_lower for w in ["reminder set", "will remind", "reminder created"]):
            return "reminder_set"
        
        # Question context
        if "?" in message:
            return "question_answered"
        
        return "ai_response"
    
    async def run_scheduled_checks(self):
        """
        Run scheduled proactive checks.
        Should be called periodically (e.g., every hour).
        """
        now = datetime.now(timezone.utc)
        current_hour = now.hour
        
        async with self.db_pool.acquire() as conn:
            # Get users who should receive daily briefing
            rows = await conn.fetch('''
                SELECT ups.user_id, ups.briefing_time, ups.timezone
                FROM user_proactive_settings ups
                JOIN users u ON u.id = ups.user_id
                WHERE ups.daily_briefing_enabled = TRUE
                AND NOT EXISTS (
                    SELECT 1 FROM proactive_actions pa
                    WHERE pa.user_id = ups.user_id
                    AND pa.action_type = 'daily_briefing'
                    AND pa.created_at > NOW() - INTERVAL '20 hours'
                )
            ''')
            
            for row in rows:
                briefing_hour = row['briefing_time'].hour if row['briefing_time'] else 8
                
                # Check if it's briefing time for this user
                if current_hour == briefing_hour:
                    briefing = await self.generate_daily_briefing(row['user_id'])
                    
                    action = ProactiveAction(
                        action_type=ProactiveActionType.DAILY_BRIEFING,
                        title="Daily Briefing",
                        message=briefing.to_message(),
                        priority=7,
                        expires_at=now + timedelta(hours=12)
                    )
                    
                    await self.queue_action(row['user_id'], action)
            
            # Check for users needing check-in
            inactive_rows = await conn.fetch('''
                SELECT u.id, ups.check_in_after_hours
                FROM users u
                JOIN user_proactive_settings ups ON ups.user_id = u.id
                WHERE ups.check_in_enabled = TRUE
                AND u.last_active_at < NOW() - INTERVAL '1 hour' * ups.check_in_after_hours
                AND NOT EXISTS (
                    SELECT 1 FROM proactive_actions pa
                    WHERE pa.user_id = u.id
                    AND pa.action_type = 'check_in'
                    AND pa.created_at > NOW() - INTERVAL '24 hours'
                )
                LIMIT 50
            ''')
            
            for row in inactive_rows:
                check_in_msg = await self.generate_check_in_message(row['id'])
                if check_in_msg:
                    action = ProactiveAction(
                        action_type=ProactiveActionType.CHECK_IN,
                        title="Check-in",
                        message=check_in_msg,
                        priority=3,
                        expires_at=now + timedelta(hours=24)
                    )
                    await self.queue_action(row['id'], action)
        
        logger.info("Completed scheduled proactive checks")


# Global proactive engine instance
_proactive_engine: Optional[ProactiveEngine] = None


async def init_proactive_engine(db_pool) -> ProactiveEngine:
    """Initialize the global proactive engine"""
    global _proactive_engine
    _proactive_engine = ProactiveEngine(db_pool)
    await _proactive_engine.init_schema()
    return _proactive_engine


def get_proactive_engine() -> Optional[ProactiveEngine]:
    """Get the global proactive engine"""
    return _proactive_engine
