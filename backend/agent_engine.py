"""
Waya Bot Builder - AI Agent Engine
Handles auto-reactions, intelligent message processing, and autonomous bot behavior.
"""

import asyncio
import random
import logging
import json
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timezone

from ai_engine import get_groq_client, chat_completion, BEST_MODEL
from telegram_api import TelegramAPI, get_telegram_api, ReactionEmoji
from database import get_connection

logger = logging.getLogger(__name__)


# =========================================================================
# EMOTION TO REACTION MAPPING
# =========================================================================

class EmotionCategory(Enum):
    """Categories of emotions for reaction mapping"""
    JOY = "joy"
    GRATITUDE = "gratitude"
    EXCITEMENT = "excitement"
    QUESTION = "question"
    AGREEMENT = "agreement"
    SURPRISE = "surprise"
    SADNESS = "sadness"
    CELEBRATION = "celebration"
    LOVE = "love"
    ANGER = "anger"
    HUMOR = "humor"
    SUPPORT = "support"
    NEUTRAL = "neutral"
    ACHIEVEMENT = "achievement"
    FEAR = "fear"


# Mapping emotions to appropriate reaction emojis
EMOTION_REACTIONS: Dict[str, List[str]] = {
    "joy": ["😂", "😊", "🎉", "😄"],
    "gratitude": ["❤", "🙏", "💯", "🤗"],
    "excitement": ["🔥", "🚀", "⚡", "🎉"],
    "question": ["🤔", "👀", "🧐"],
    "agreement": ["👍", "💯", "✍"],
    "surprise": ["😮", "🤯", "😱"],
    "sadness": ["😢", "💔", "🫂"],
    "celebration": ["🎉", "🏆", "🍾", "👏"],
    "love": ["❤", "😍", "💕", "💋"],
    "anger": ["😡", "💢"],
    "humor": ["😂", "🤣", "😆", "🤡"],
    "support": ["🤗", "💪", "👏", "🙏"],
    "neutral": ["👀", "👍"],
    "achievement": ["🏆", "🎯", "💯", "⭐"],
    "fear": ["😱", "👻", "💀"],
}

# Reaction styles with different emoji selection strategies
REACTION_STYLES = {
    "expressive": {"variety": 1.0, "intensity": "high"},
    "minimal": {"variety": 0.3, "intensity": "low"},
    "professional": {"variety": 0.5, "intensity": "medium"},
    "playful": {"variety": 0.8, "intensity": "high"},
    "supportive": {"variety": 0.6, "intensity": "medium"},
}


@dataclass
class EmotionAnalysis:
    """Result of emotion analysis"""
    emotion: str
    confidence: float
    secondary_emotions: List[str]
    sentiment: str  # positive, negative, neutral
    intensity: str  # low, medium, high
    keywords: List[str]


@dataclass
class ReactionResult:
    """Result of auto-reaction"""
    success: bool
    emoji: Optional[str]
    emotion: Optional[str]
    confidence: float
    error: Optional[str] = None


# =========================================================================
# EMOTION ANALYSIS
# =========================================================================

async def analyze_message_emotion(
    message_text: str,
    context: Optional[str] = None
) -> EmotionAnalysis:
    """
    Analyze the emotion in a message using AI.
    
    Args:
        message_text: The message to analyze
        context: Optional conversation context
    
    Returns:
        EmotionAnalysis with detected emotions
    """
    client = get_groq_client()
    
    system_prompt = """You are an emotion analyzer. Analyze the given message and return a JSON object with:
{
    "emotion": "primary emotion (joy, gratitude, excitement, question, agreement, surprise, sadness, celebration, love, anger, humor, support, neutral, achievement, fear)",
    "confidence": 0.0-1.0,
    "secondary_emotions": ["list", "of", "other", "emotions"],
    "sentiment": "positive/negative/neutral",
    "intensity": "low/medium/high",
    "keywords": ["emotion", "triggering", "words"]
}

Be precise and consider context. Return ONLY valid JSON."""

    user_prompt = f"Analyze this message: \"{message_text}\""
    if context:
        user_prompt += f"\n\nConversation context: {context}"
    
    try:
        response = await client.chat.completions.create(
            model=BEST_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=200
        )
        
        result_text = response.choices[0].message.content.strip()
        
        # Parse JSON response
        # Handle potential markdown code blocks
        if "```json" in result_text:
            result_text = result_text.split("```json")[1].split("```")[0]
        elif "```" in result_text:
            result_text = result_text.split("```")[1].split("```")[0]
        
        data = json.loads(result_text)
        
        return EmotionAnalysis(
            emotion=data.get("emotion", "neutral"),
            confidence=float(data.get("confidence", 0.5)),
            secondary_emotions=data.get("secondary_emotions", []),
            sentiment=data.get("sentiment", "neutral"),
            intensity=data.get("intensity", "medium"),
            keywords=data.get("keywords", [])
        )
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse emotion analysis JSON: {e}")
        return EmotionAnalysis(
            emotion="neutral",
            confidence=0.3,
            secondary_emotions=[],
            sentiment="neutral",
            intensity="low",
            keywords=[]
        )
    except Exception as e:
        logger.error(f"Emotion analysis failed: {e}")
        return EmotionAnalysis(
            emotion="neutral",
            confidence=0.0,
            secondary_emotions=[],
            sentiment="neutral",
            intensity="low",
            keywords=[]
        )


def quick_emotion_detect(message_text: str) -> Tuple[str, float]:
    """
    Quick rule-based emotion detection for common patterns.
    Falls back to AI analysis for ambiguous cases.
    
    Args:
        message_text: The message to analyze
    
    Returns:
        Tuple of (emotion, confidence)
    """
    text_lower = message_text.lower()
    
    # Quick patterns with high confidence
    patterns = {
        # Joy indicators
        ("haha", "lol", "lmao", "rofl", "😂", "🤣"): ("humor", 0.9),
        ("thank", "thanks", "thx", "appreciate", "grateful"): ("gratitude", 0.9),
        ("love", "❤", "💕", "😍", "adore"): ("love", 0.85),
        ("yay", "woohoo", "awesome", "amazing", "🎉"): ("celebration", 0.85),
        ("wow", "omg", "whoa", "🤯", "😱"): ("surprise", 0.85),
        ("yes", "exactly", "agree", "right", "true", "👍"): ("agreement", 0.8),
        ("sad", "😢", "😭", "unfortunately", "miss"): ("sadness", 0.8),
        ("congrats", "congratulations", "well done", "🏆"): ("achievement", 0.9),
        ("excited", "can't wait", "🔥", "🚀"): ("excitement", 0.85),
        ("help", "please", "need", "how do"): ("support", 0.7),
        ("?",): ("question", 0.7),
        ("angry", "mad", "frustrated", "😡"): ("anger", 0.8),
    }
    
    for keywords, (emotion, confidence) in patterns.items():
        for keyword in keywords:
            if keyword in text_lower:
                return (emotion, confidence)
    
    # No clear pattern - return neutral with low confidence
    return ("neutral", 0.3)


# =========================================================================
# AUTO-REACTION ENGINE
# =========================================================================

async def auto_react_to_message(
    bot_token: str,
    chat_id: int,
    message_id: int,
    message_text: str,
    bot_id: Optional[int] = None,
    reaction_style: str = "expressive",
    use_ai: bool = True
) -> ReactionResult:
    """
    Automatically react to a message with an appropriate emoji.
    
    Args:
        bot_token: The bot's Telegram token
        chat_id: Chat ID where the message was sent
        message_id: ID of the message to react to
        message_text: Text content of the message
        bot_id: Optional bot ID for logging
        reaction_style: Style of reactions (expressive, minimal, etc.)
        use_ai: Whether to use AI for emotion analysis
    
    Returns:
        ReactionResult with the outcome
    """
    try:
        # Get the Telegram API instance
        api = get_telegram_api(bot_token)
        
        # Skip very short messages
        if len(message_text.strip()) < 2:
            return ReactionResult(
                success=False,
                emoji=None,
                emotion=None,
                confidence=0.0,
                error="Message too short"
            )
        
        # Analyze emotion
        if use_ai and len(message_text) > 10:
            analysis = await analyze_message_emotion(message_text)
            emotion = analysis.emotion
            confidence = analysis.confidence
        else:
            emotion, confidence = quick_emotion_detect(message_text)
        
        # Get style configuration
        style = REACTION_STYLES.get(reaction_style, REACTION_STYLES["expressive"])
        
        # Skip reaction if confidence is too low based on style
        min_confidence = 0.5 if style["intensity"] == "high" else 0.7
        if confidence < min_confidence:
            return ReactionResult(
                success=False,
                emoji=None,
                emotion=emotion,
                confidence=confidence,
                error="Confidence too low"
            )
        
        # Select emoji based on emotion and style
        emojis = EMOTION_REACTIONS.get(emotion, EMOTION_REACTIONS["neutral"])
        
        # Style affects emoji selection
        if style["variety"] < 0.5:
            # Low variety - always use first emoji
            emoji = emojis[0]
        else:
            # Higher variety - random selection
            emoji = random.choice(emojis)
        
        # Send the reaction
        success = await api.set_message_reaction(
            chat_id=chat_id,
            message_id=message_id,
            reaction=emoji,
            is_big=style["intensity"] == "high" and confidence > 0.8
        )
        
        # Log the reaction if bot_id provided
        if bot_id and success:
            await log_auto_reaction(
                bot_id=bot_id,
                chat_id=chat_id,
                message_id=message_id,
                user_id=0,  # Will be filled by caller
                reaction_emoji=emoji,
                detected_emotion=emotion,
                confidence=confidence,
                message_preview=message_text[:100]
            )
        
        return ReactionResult(
            success=success,
            emoji=emoji if success else None,
            emotion=emotion,
            confidence=confidence,
            error=None if success else "Failed to set reaction"
        )
        
    except Exception as e:
        logger.error(f"Auto-reaction failed: {e}")
        return ReactionResult(
            success=False,
            emoji=None,
            emotion=None,
            confidence=0.0,
            error=str(e)
        )


async def log_auto_reaction(
    bot_id: int,
    chat_id: int,
    message_id: int,
    user_id: int,
    reaction_emoji: str,
    detected_emotion: str,
    confidence: float,
    message_preview: str
) -> None:
    """Log an auto-reaction to the database"""
    try:
        async with get_connection() as conn:
            await conn.execute('''
                INSERT INTO auto_reactions 
                (bot_id, chat_id, message_id, user_id, reaction_emoji, 
                 detected_emotion, confidence_score, message_preview)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            ''', bot_id, chat_id, message_id, user_id, reaction_emoji,
                detected_emotion, confidence, message_preview)
    except Exception as e:
        logger.error(f"Failed to log auto-reaction: {e}")


# =========================================================================
# AGENT SETTINGS MANAGEMENT
# =========================================================================

@dataclass
class AgentSettings:
    """Settings for a bot's AI agent features"""
    auto_react_enabled: bool = True
    auto_moderate_enabled: bool = False
    auto_suggest_enabled: bool = True
    auto_schedule_enabled: bool = False
    reaction_style: str = "expressive"
    moderation_level: str = "medium"
    suggestion_count: int = 3
    settings: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.settings is None:
            self.settings = {}


async def get_agent_settings(bot_id: int) -> AgentSettings:
    """Get agent settings for a bot"""
    try:
        async with get_connection() as conn:
            row = await conn.fetchrow('''
                SELECT auto_react_enabled, auto_moderate_enabled, 
                       auto_suggest_enabled, auto_schedule_enabled,
                       reaction_style, moderation_level, suggestion_count, settings
                FROM bot_agent_settings
                WHERE bot_id = $1
            ''', bot_id)
            
            if row:
                return AgentSettings(
                    auto_react_enabled=row['auto_react_enabled'],
                    auto_moderate_enabled=row['auto_moderate_enabled'],
                    auto_suggest_enabled=row['auto_suggest_enabled'],
                    auto_schedule_enabled=row['auto_schedule_enabled'],
                    reaction_style=row['reaction_style'],
                    moderation_level=row['moderation_level'],
                    suggestion_count=row['suggestion_count'],
                    settings=row['settings'] or {}
                )
            
            # Return defaults if no settings exist
            return AgentSettings()
    except Exception as e:
        logger.error(f"Failed to get agent settings: {e}")
        return AgentSettings()


async def update_agent_settings(
    bot_id: int,
    **kwargs
) -> bool:
    """Update agent settings for a bot"""
    try:
        async with get_connection() as conn:
            # Check if settings exist
            exists = await conn.fetchval(
                'SELECT 1 FROM bot_agent_settings WHERE bot_id = $1',
                bot_id
            )
            
            if exists:
                # Build update query dynamically
                set_clauses = []
                values = [bot_id]
                param_num = 2
                
                allowed_fields = {
                    'auto_react_enabled', 'auto_moderate_enabled',
                    'auto_suggest_enabled', 'auto_schedule_enabled',
                    'reaction_style', 'moderation_level', 'suggestion_count', 'settings'
                }
                
                for key, value in kwargs.items():
                    if key in allowed_fields:
                        set_clauses.append(f"{key} = ${param_num}")
                        values.append(value)
                        param_num += 1
                
                if set_clauses:
                    set_clauses.append(f"updated_at = NOW()")
                    query = f'''
                        UPDATE bot_agent_settings 
                        SET {", ".join(set_clauses)}
                        WHERE bot_id = $1
                    '''
                    await conn.execute(query, *values)
            else:
                # Insert new settings
                await conn.execute('''
                    INSERT INTO bot_agent_settings 
                    (bot_id, auto_react_enabled, auto_moderate_enabled,
                     auto_suggest_enabled, auto_schedule_enabled,
                     reaction_style, moderation_level, suggestion_count, settings)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                ''',
                    bot_id,
                    kwargs.get('auto_react_enabled', True),
                    kwargs.get('auto_moderate_enabled', False),
                    kwargs.get('auto_suggest_enabled', True),
                    kwargs.get('auto_schedule_enabled', False),
                    kwargs.get('reaction_style', 'expressive'),
                    kwargs.get('moderation_level', 'medium'),
                    kwargs.get('suggestion_count', 3),
                    kwargs.get('settings', {})
                )
            
            return True
    except Exception as e:
        logger.error(f"Failed to update agent settings: {e}")
        return False


async def initialize_agent_settings(bot_id: int) -> bool:
    """Initialize default agent settings for a new bot"""
    return await update_agent_settings(
        bot_id,
        auto_react_enabled=True,
        auto_moderate_enabled=False,
        auto_suggest_enabled=True,
        auto_schedule_enabled=False,
        reaction_style='expressive',
        moderation_level='medium',
        suggestion_count=3,
        settings={}
    )


# =========================================================================
# BATCH PROCESSING
# =========================================================================

async def process_message_batch(
    bot_token: str,
    bot_id: int,
    messages: List[Dict[str, Any]],
    settings: AgentSettings
) -> Dict[str, Any]:
    """
    Process a batch of messages with agent features.
    
    Args:
        bot_token: Bot's Telegram token
        bot_id: Bot ID
        messages: List of message dicts with chat_id, message_id, text, user_id
        settings: Agent settings
    
    Returns:
        Summary of processing results
    """
    results = {
        "total": len(messages),
        "reactions_sent": 0,
        "reactions_failed": 0,
        "errors": []
    }
    
    for msg in messages:
        try:
            if settings.auto_react_enabled:
                result = await auto_react_to_message(
                    bot_token=bot_token,
                    chat_id=msg["chat_id"],
                    message_id=msg["message_id"],
                    message_text=msg["text"],
                    bot_id=bot_id,
                    reaction_style=settings.reaction_style
                )
                
                if result.success:
                    results["reactions_sent"] += 1
                else:
                    results["reactions_failed"] += 1
            
            # Small delay to avoid rate limits
            await asyncio.sleep(0.1)
            
        except Exception as e:
            results["errors"].append(str(e))
    
    return results


# =========================================================================
# ENGAGEMENT TRACKING
# =========================================================================

async def track_engagement(
    bot_id: int,
    chat_id: int,
    message_count: int = 1,
    reaction_count: int = 0,
    reply_count: int = 0,
    response_time_ms: int = 0
) -> None:
    """Track engagement metrics for optimal scheduling"""
    try:
        now = datetime.now(timezone.utc)
        hour = now.hour
        day = now.weekday()
        
        async with get_connection() as conn:
            await conn.execute('''
                INSERT INTO engagement_analytics 
                (bot_id, chat_id, hour_of_day, day_of_week, 
                 message_count, reaction_count, reply_count, avg_response_time_ms)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ON CONFLICT (bot_id, chat_id, hour_of_day, day_of_week)
                DO UPDATE SET
                    message_count = engagement_analytics.message_count + $5,
                    reaction_count = engagement_analytics.reaction_count + $6,
                    reply_count = engagement_analytics.reply_count + $7,
                    avg_response_time_ms = (engagement_analytics.avg_response_time_ms + $8) / 2,
                    updated_at = NOW()
            ''', bot_id, chat_id, hour, day, 
                message_count, reaction_count, reply_count, response_time_ms)
    except Exception as e:
        logger.error(f"Failed to track engagement: {e}")


async def get_optimal_posting_hours(
    bot_id: int,
    chat_id: int,
    limit: int = 5
) -> List[Dict[str, Any]]:
    """Get the optimal hours for posting based on engagement data"""
    try:
        async with get_connection() as conn:
            rows = await conn.fetch('''
                SELECT hour_of_day, day_of_week, 
                       SUM(message_count) as total_messages,
                       SUM(reaction_count) as total_reactions,
                       AVG(avg_response_time_ms) as avg_response_time
                FROM engagement_analytics
                WHERE bot_id = $1 AND chat_id = $2
                GROUP BY hour_of_day, day_of_week
                ORDER BY total_messages DESC, total_reactions DESC
                LIMIT $3
            ''', bot_id, chat_id, limit)
            
            return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Failed to get optimal posting hours: {e}")
        return []


# =========================================================================
# MESSAGE CONTEXT ANALYSIS
# =========================================================================

async def analyze_conversation_context(
    messages: List[Dict[str, str]],
    max_messages: int = 10
) -> Dict[str, Any]:
    """
    Analyze the context of a conversation for better responses.
    
    Args:
        messages: List of messages with 'role' and 'content'
        max_messages: Maximum messages to analyze
    
    Returns:
        Context analysis with topic, mood, engagement level
    """
    client = get_groq_client()
    
    # Format recent messages
    recent = messages[-max_messages:] if len(messages) > max_messages else messages
    formatted = "\n".join([f"{m['role']}: {m['content']}" for m in recent])
    
    system_prompt = """Analyze this conversation and return a JSON object:
{
    "topic": "main topic being discussed",
    "mood": "overall conversation mood (positive/negative/neutral/mixed)",
    "engagement_level": "low/medium/high",
    "user_intent": "what the user seems to want",
    "suggested_tone": "recommended response tone",
    "key_entities": ["important", "named", "entities"],
    "context_summary": "brief summary of conversation context"
}

Return ONLY valid JSON."""
    
    try:
        response = await client.chat.completions.create(
            model=BEST_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Conversation:\n{formatted}"}
            ],
            temperature=0.3,
            max_tokens=300
        )
        
        result_text = response.choices[0].message.content.strip()
        
        # Handle code blocks
        if "```json" in result_text:
            result_text = result_text.split("```json")[1].split("```")[0]
        elif "```" in result_text:
            result_text = result_text.split("```")[1].split("```")[0]
        
        return json.loads(result_text)
    except Exception as e:
        logger.error(f"Context analysis failed: {e}")
        return {
            "topic": "unknown",
            "mood": "neutral",
            "engagement_level": "medium",
            "user_intent": "unknown",
            "suggested_tone": "friendly",
            "key_entities": [],
            "context_summary": ""
        }
