"""
Waya Bot Builder - Auto-Moderation System
Intelligent content moderation for group bots with spam detection,
inappropriate content filtering, and automated actions.
"""

import asyncio
import re
import hashlib
import logging
import json
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timezone, timedelta
from collections import defaultdict

from ai_engine import get_groq_client, BEST_MODEL
from telegram_api import TelegramAPI, get_telegram_api, ChatPermissions
from database import get_connection

logger = logging.getLogger(__name__)


# =========================================================================
# MODERATION TYPES AND ENUMS
# =========================================================================

class ModerationLevel(Enum):
    """Moderation strictness levels"""
    LOW = "low"           # Only obvious spam/abuse
    MEDIUM = "medium"     # Standard moderation
    HIGH = "high"         # Strict moderation
    CUSTOM = "custom"     # Custom rules


class ViolationType(Enum):
    """Types of content violations"""
    SPAM = "spam"
    FLOOD = "flood"
    INAPPROPRIATE = "inappropriate"
    HARASSMENT = "harassment"
    SCAM = "scam"
    LINK_SPAM = "link_spam"
    MEDIA_SPAM = "media_spam"
    CAPS_ABUSE = "caps_abuse"
    PROFANITY = "profanity"
    SELF_PROMOTION = "self_promotion"
    ADULT_CONTENT = "adult_content"
    VIOLENCE = "violence"
    HATE_SPEECH = "hate_speech"


class ModerationAction(Enum):
    """Actions to take on violations"""
    WARN = "warn"
    DELETE = "delete"
    MUTE = "mute"
    KICK = "kick"
    BAN = "ban"
    REPORT = "report"
    IGNORE = "ignore"


@dataclass
class ModerationResult:
    """Result of content moderation check"""
    is_violation: bool
    violation_type: Optional[ViolationType] = None
    confidence: float = 0.0
    reason: str = ""
    recommended_action: ModerationAction = ModerationAction.IGNORE
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UserWarningState:
    """Track warnings for a user"""
    warning_count: int = 0
    last_warning_at: Optional[datetime] = None
    violations: List[str] = field(default_factory=list)
    is_muted: bool = False
    mute_until: Optional[datetime] = None


# =========================================================================
# SPAM DETECTION PATTERNS
# =========================================================================

# Common spam patterns (regex)
SPAM_PATTERNS = [
    r'(?i)make\s*\$?\d+\s*(per|a)\s*(day|hour|week)',
    r'(?i)earn\s*\$?\d+\s*(daily|weekly|monthly)',
    r'(?i)click\s*(here|this|link)',
    r'(?i)free\s*(bitcoin|crypto|money|gift)',
    r'(?i)join\s*(my|our)\s*(channel|group)',
    r'(?i)100%\s*(guarantee|profit|win)',
    r'(?i)limited\s*time\s*offer',
    r'(?i)act\s*now|hurry\s*up',
    r'(?i)dm\s*(me|for)\s*(more|details)',
    r'(?i)send\s*\d+\s*(btc|eth|usdt)',
    r'(?i)investment\s*opportunity',
    r'(?i)(telegram|whatsapp)\s*@?\w+',
    r'(?i)get\s*rich\s*quick',
    r'(?i)casino|betting|gambling',
]

# Compiled patterns for efficiency
COMPILED_SPAM_PATTERNS = [re.compile(p) for p in SPAM_PATTERNS]

# Link patterns
LINK_PATTERN = re.compile(
    r'https?://[^\s<>"{}|\\^`\[\]]+|'
    r'(?:t\.me|telegram\.me)/[^\s]+'
)

# Caps abuse (more than 70% uppercase)
def is_caps_abuse(text: str, threshold: float = 0.7) -> bool:
    """Check if text has excessive caps"""
    if len(text) < 10:
        return False
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return False
    upper_count = sum(1 for c in letters if c.isupper())
    return upper_count / len(letters) > threshold


# =========================================================================
# FLOOD DETECTION
# =========================================================================

# Message cache for flood detection (in-memory, should use Redis in production)
_message_cache: Dict[str, List[Tuple[datetime, str]]] = defaultdict(list)
_cache_lock = asyncio.Lock()


async def check_flood(
    chat_id: int,
    user_id: int,
    message_text: str,
    max_messages: int = 5,
    time_window_seconds: int = 10,
    similarity_threshold: float = 0.8
) -> Tuple[bool, str]:
    """
    Check if a user is flooding the chat.
    
    Args:
        chat_id: Chat ID
        user_id: User ID
        message_text: Message content
        max_messages: Max messages allowed in time window
        time_window_seconds: Time window in seconds
        similarity_threshold: Threshold for similar message detection
    
    Returns:
        Tuple of (is_flooding, reason)
    """
    cache_key = f"{chat_id}:{user_id}"
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(seconds=time_window_seconds)
    
    async with _cache_lock:
        # Clean old messages
        _message_cache[cache_key] = [
            (ts, msg) for ts, msg in _message_cache[cache_key]
            if ts > cutoff
        ]
        
        recent_messages = _message_cache[cache_key]
        
        # Check message count
        if len(recent_messages) >= max_messages:
            return True, f"Sent {len(recent_messages)} messages in {time_window_seconds}s"
        
        # Check for duplicate messages
        message_hash = hashlib.md5(message_text.lower().encode()).hexdigest()
        duplicate_count = sum(
            1 for _, msg in recent_messages
            if hashlib.md5(msg.lower().encode()).hexdigest() == message_hash
        )
        
        if duplicate_count >= 3:
            return True, "Sending duplicate messages"
        
        # Check for similar messages
        similar_count = 0
        for _, prev_msg in recent_messages:
            if _similarity_ratio(message_text, prev_msg) > similarity_threshold:
                similar_count += 1
        
        if similar_count >= 3:
            return True, "Sending similar messages repeatedly"
        
        # Add current message to cache
        _message_cache[cache_key].append((now, message_text))
    
    return False, ""


def _similarity_ratio(text1: str, text2: str) -> float:
    """Calculate similarity ratio between two texts"""
    if not text1 or not text2:
        return 0.0
    
    # Simple character-level similarity
    text1 = text1.lower()
    text2 = text2.lower()
    
    if text1 == text2:
        return 1.0
    
    # Jaccard similarity on words
    words1 = set(text1.split())
    words2 = set(text2.split())
    
    if not words1 or not words2:
        return 0.0
    
    intersection = len(words1 & words2)
    union = len(words1 | words2)
    
    return intersection / union if union > 0 else 0.0


# =========================================================================
# AI-POWERED CONTENT ANALYSIS
# =========================================================================

async def analyze_content_ai(
    message_text: str,
    context: Optional[str] = None
) -> ModerationResult:
    """
    Use AI to analyze content for violations.
    
    Args:
        message_text: The message to analyze
        context: Optional conversation context
    
    Returns:
        ModerationResult with analysis
    """
    client = get_groq_client()
    
    system_prompt = """You are a content moderator. Analyze the message and return a JSON object:
{
    "is_violation": true/false,
    "violation_type": "spam|flood|inappropriate|harassment|scam|link_spam|media_spam|caps_abuse|profanity|self_promotion|adult_content|violence|hate_speech|none",
    "confidence": 0.0-1.0,
    "reason": "brief explanation",
    "severity": "low|medium|high",
    "recommended_action": "ignore|warn|delete|mute|kick|ban"
}

Be fair but thorough. Consider context if provided. Return ONLY valid JSON."""

    user_prompt = f"Analyze this message for moderation:\n\"{message_text}\""
    if context:
        user_prompt += f"\n\nContext: {context}"
    
    try:
        response = await client.chat.completions.create(
            model=BEST_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2,
            max_tokens=200
        )
        
        result_text = response.choices[0].message.content.strip()
        
        # Handle code blocks
        if "```json" in result_text:
            result_text = result_text.split("```json")[1].split("```")[0]
        elif "```" in result_text:
            result_text = result_text.split("```")[1].split("```")[0]
        
        data = json.loads(result_text)
        
        violation_type = None
        if data.get("violation_type") and data["violation_type"] != "none":
            try:
                violation_type = ViolationType(data["violation_type"])
            except ValueError:
                violation_type = ViolationType.INAPPROPRIATE
        
        action_map = {
            "ignore": ModerationAction.IGNORE,
            "warn": ModerationAction.WARN,
            "delete": ModerationAction.DELETE,
            "mute": ModerationAction.MUTE,
            "kick": ModerationAction.KICK,
            "ban": ModerationAction.BAN,
        }
        
        return ModerationResult(
            is_violation=data.get("is_violation", False),
            violation_type=violation_type,
            confidence=float(data.get("confidence", 0.5)),
            reason=data.get("reason", ""),
            recommended_action=action_map.get(
                data.get("recommended_action", "ignore"),
                ModerationAction.IGNORE
            ),
            details={"severity": data.get("severity", "low")}
        )
        
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse moderation AI response: {e}")
        return ModerationResult(is_violation=False)
    except Exception as e:
        logger.error(f"AI content analysis failed: {e}")
        return ModerationResult(is_violation=False)


# =========================================================================
# RULE-BASED CONTENT CHECK
# =========================================================================

def check_content_rules(
    message_text: str,
    moderation_level: ModerationLevel = ModerationLevel.MEDIUM
) -> ModerationResult:
    """
    Check content against rule-based patterns.
    
    Args:
        message_text: The message to check
        moderation_level: Strictness level
    
    Returns:
        ModerationResult
    """
    # Skip very short messages
    if len(message_text.strip()) < 3:
        return ModerationResult(is_violation=False)
    
    text = message_text.lower()
    
    # Check spam patterns
    for pattern in COMPILED_SPAM_PATTERNS:
        if pattern.search(text):
            return ModerationResult(
                is_violation=True,
                violation_type=ViolationType.SPAM,
                confidence=0.85,
                reason="Message matches spam pattern",
                recommended_action=ModerationAction.DELETE
            )
    
    # Check link spam (multiple links)
    links = LINK_PATTERN.findall(message_text)
    if len(links) >= 3:
        return ModerationResult(
            is_violation=True,
            violation_type=ViolationType.LINK_SPAM,
            confidence=0.8,
            reason=f"Message contains {len(links)} links",
            recommended_action=ModerationAction.DELETE
        )
    
    # Check caps abuse
    if is_caps_abuse(message_text):
        severity = ModerationLevel.HIGH if moderation_level == ModerationLevel.HIGH else ModerationLevel.MEDIUM
        return ModerationResult(
            is_violation=moderation_level in [ModerationLevel.MEDIUM, ModerationLevel.HIGH],
            violation_type=ViolationType.CAPS_ABUSE,
            confidence=0.9,
            reason="Excessive use of capital letters",
            recommended_action=ModerationAction.WARN if severity == ModerationLevel.MEDIUM else ModerationAction.DELETE
        )
    
    # Single link with suspicious domains
    suspicious_domains = ['bit.ly', 'tinyurl', 'goo.gl', 't.co', 'ow.ly']
    for link in links:
        for domain in suspicious_domains:
            if domain in link.lower():
                return ModerationResult(
                    is_violation=True,
                    violation_type=ViolationType.SCAM,
                    confidence=0.6,
                    reason="Contains shortened/suspicious link",
                    recommended_action=ModerationAction.WARN
                )
    
    return ModerationResult(is_violation=False)


# =========================================================================
# MAIN MODERATION FUNCTION
# =========================================================================

async def moderate_message(
    bot_token: str,
    bot_id: int,
    chat_id: int,
    message_id: int,
    user_id: int,
    message_text: str,
    moderation_level: ModerationLevel = ModerationLevel.MEDIUM,
    use_ai: bool = True
) -> ModerationResult:
    """
    Main function to moderate a message.
    
    Args:
        bot_token: Bot's Telegram token
        bot_id: Bot ID
        chat_id: Chat ID
        message_id: Message ID
        user_id: User who sent the message
        message_text: Message content
        moderation_level: Strictness level
        use_ai: Whether to use AI analysis
    
    Returns:
        ModerationResult with final decision
    """
    # First check flood
    is_flooding, flood_reason = await check_flood(chat_id, user_id, message_text)
    if is_flooding:
        result = ModerationResult(
            is_violation=True,
            violation_type=ViolationType.FLOOD,
            confidence=0.95,
            reason=flood_reason,
            recommended_action=ModerationAction.MUTE
        )
        await take_moderation_action(
            bot_token, bot_id, chat_id, message_id, user_id,
            message_text, result
        )
        return result
    
    # Rule-based check (fast)
    rule_result = check_content_rules(message_text, moderation_level)
    if rule_result.is_violation and rule_result.confidence > 0.8:
        await take_moderation_action(
            bot_token, bot_id, chat_id, message_id, user_id,
            message_text, rule_result
        )
        return rule_result
    
    # AI analysis for uncertain cases
    if use_ai and len(message_text) > 10:
        ai_result = await analyze_content_ai(message_text)
        
        if ai_result.is_violation:
            # Combine rule and AI confidence
            final_confidence = max(
                rule_result.confidence if rule_result.is_violation else 0,
                ai_result.confidence
            )
            
            # Only act if confidence is high enough based on level
            min_confidence = {
                ModerationLevel.LOW: 0.9,
                ModerationLevel.MEDIUM: 0.75,
                ModerationLevel.HIGH: 0.6,
            }.get(moderation_level, 0.75)
            
            if final_confidence >= min_confidence:
                ai_result.confidence = final_confidence
                await take_moderation_action(
                    bot_token, bot_id, chat_id, message_id, user_id,
                    message_text, ai_result
                )
                return ai_result
    
    return ModerationResult(is_violation=False)


# =========================================================================
# MODERATION ACTIONS
# =========================================================================

async def take_moderation_action(
    bot_token: str,
    bot_id: int,
    chat_id: int,
    message_id: int,
    user_id: int,
    message_text: str,
    result: ModerationResult
) -> bool:
    """
    Execute moderation action based on result.
    
    Args:
        bot_token: Bot's Telegram token
        bot_id: Bot ID
        chat_id: Chat ID
        message_id: Message ID
        user_id: User ID
        message_text: Original message
        result: Moderation result
    
    Returns:
        True if action was taken successfully
    """
    api = get_telegram_api(bot_token)
    action_taken = False
    action_name = result.recommended_action.value
    
    try:
        if result.recommended_action == ModerationAction.DELETE:
            success = await api.delete_message(chat_id, message_id)
            if success:
                action_taken = True
                # Send notification
                await api._request("sendMessage", {
                    "chat_id": chat_id,
                    "text": f"Message removed: {result.reason}",
                    "reply_to_message_id": None
                })
        
        elif result.recommended_action == ModerationAction.WARN:
            # Get/update warning count
            warning_state = await get_user_warnings(bot_id, chat_id, user_id)
            warning_state.warning_count += 1
            warning_state.last_warning_at = datetime.now(timezone.utc)
            warning_state.violations.append(result.violation_type.value if result.violation_type else "unknown")
            
            await update_user_warnings(bot_id, chat_id, user_id, warning_state)
            
            # Send warning message
            warning_text = f"Warning ({warning_state.warning_count}/3): {result.reason}"
            if warning_state.warning_count >= 3:
                warning_text += "\n\nNext violation will result in a mute."
            
            await api._request("sendMessage", {
                "chat_id": chat_id,
                "text": warning_text,
                "reply_to_message_id": message_id
            })
            action_taken = True
            
            # Auto-escalate after 3 warnings
            if warning_state.warning_count >= 3:
                await api.mute_user(chat_id, user_id, duration_seconds=3600)  # 1 hour
                action_name = "mute_auto"
        
        elif result.recommended_action == ModerationAction.MUTE:
            # Delete the offending message
            await api.delete_message(chat_id, message_id)
            
            # Mute for 1 hour
            success = await api.mute_user(chat_id, user_id, duration_seconds=3600)
            if success:
                await api._request("sendMessage", {
                    "chat_id": chat_id,
                    "text": f"User muted for 1 hour: {result.reason}"
                })
                action_taken = True
        
        elif result.recommended_action == ModerationAction.KICK:
            await api.delete_message(chat_id, message_id)
            
            # Kick = ban then unban
            await api.ban_chat_member(chat_id, user_id)
            await asyncio.sleep(1)
            await api.unban_chat_member(chat_id, user_id)
            
            await api._request("sendMessage", {
                "chat_id": chat_id,
                "text": f"User removed: {result.reason}"
            })
            action_taken = True
        
        elif result.recommended_action == ModerationAction.BAN:
            await api.delete_message(chat_id, message_id)
            
            success = await api.ban_chat_member(chat_id, user_id, revoke_messages=True)
            if success:
                await api._request("sendMessage", {
                    "chat_id": chat_id,
                    "text": f"User banned: {result.reason}"
                })
                action_taken = True
        
        # Log the action
        await log_moderation_action(
            bot_id=bot_id,
            chat_id=chat_id,
            user_id=user_id,
            message_id=message_id,
            action_type=result.violation_type.value if result.violation_type else "unknown",
            reason=result.reason,
            message_content=message_text[:500],
            confidence_score=result.confidence,
            auto_action_taken=action_name
        )
        
        return action_taken
        
    except Exception as e:
        logger.error(f"Failed to take moderation action: {e}")
        return False


# =========================================================================
# WARNING MANAGEMENT
# =========================================================================

async def get_user_warnings(
    bot_id: int,
    chat_id: int,
    user_id: int
) -> UserWarningState:
    """Get warning state for a user"""
    try:
        async with get_connection() as conn:
            row = await conn.fetchrow('''
                SELECT warning_count, last_warning_at, expires_at
                FROM user_warnings
                WHERE bot_id = $1 AND chat_id = $2 AND user_id = $3
                AND warning_type = 'general'
            ''', bot_id, chat_id, user_id)
            
            if row:
                # Check if warnings expired (24h)
                if row['last_warning_at']:
                    last_warning = row['last_warning_at']
                    if datetime.now(timezone.utc) - last_warning > timedelta(hours=24):
                        # Reset warnings
                        return UserWarningState()
                
                return UserWarningState(
                    warning_count=row['warning_count'],
                    last_warning_at=row['last_warning_at']
                )
            
            return UserWarningState()
    except Exception as e:
        logger.error(f"Failed to get user warnings: {e}")
        return UserWarningState()


async def update_user_warnings(
    bot_id: int,
    chat_id: int,
    user_id: int,
    state: UserWarningState
) -> None:
    """Update warning state for a user"""
    try:
        async with get_connection() as conn:
            await conn.execute('''
                INSERT INTO user_warnings 
                (bot_id, chat_id, user_id, warning_type, warning_count, last_warning_at)
                VALUES ($1, $2, $3, 'general', $4, $5)
                ON CONFLICT (bot_id, chat_id, user_id, warning_type)
                DO UPDATE SET 
                    warning_count = $4,
                    last_warning_at = $5
            ''', bot_id, chat_id, user_id, state.warning_count, state.last_warning_at)
    except Exception as e:
        logger.error(f"Failed to update user warnings: {e}")


async def reset_user_warnings(
    bot_id: int,
    chat_id: int,
    user_id: int
) -> None:
    """Reset all warnings for a user"""
    try:
        async with get_connection() as conn:
            await conn.execute('''
                DELETE FROM user_warnings
                WHERE bot_id = $1 AND chat_id = $2 AND user_id = $3
            ''', bot_id, chat_id, user_id)
    except Exception as e:
        logger.error(f"Failed to reset user warnings: {e}")


# =========================================================================
# LOGGING
# =========================================================================

async def log_moderation_action(
    bot_id: int,
    chat_id: int,
    user_id: int,
    message_id: int,
    action_type: str,
    reason: str,
    message_content: str,
    confidence_score: float,
    auto_action_taken: str
) -> None:
    """Log moderation action to database"""
    try:
        async with get_connection() as conn:
            await conn.execute('''
                INSERT INTO moderation_logs
                (bot_id, chat_id, user_id, message_id, action_type,
                 reason, message_content, confidence_score, auto_action_taken)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            ''', bot_id, chat_id, user_id, message_id, action_type,
                reason, message_content, confidence_score, auto_action_taken)
    except Exception as e:
        logger.error(f"Failed to log moderation action: {e}")


async def get_moderation_logs(
    bot_id: int,
    chat_id: Optional[int] = None,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """Get recent moderation logs"""
    try:
        async with get_connection() as conn:
            if chat_id:
                rows = await conn.fetch('''
                    SELECT * FROM moderation_logs
                    WHERE bot_id = $1 AND chat_id = $2
                    ORDER BY created_at DESC
                    LIMIT $3
                ''', bot_id, chat_id, limit)
            else:
                rows = await conn.fetch('''
                    SELECT * FROM moderation_logs
                    WHERE bot_id = $1
                    ORDER BY created_at DESC
                    LIMIT $2
                ''', bot_id, limit)
            
            return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Failed to get moderation logs: {e}")
        return []


# =========================================================================
# SPAM PATTERN MANAGEMENT
# =========================================================================

async def add_spam_pattern(
    pattern_type: str,
    pattern_value: str,
    severity: str = "medium",
    created_by: Optional[int] = None
) -> bool:
    """Add a new spam pattern"""
    try:
        async with get_connection() as conn:
            await conn.execute('''
                INSERT INTO spam_patterns
                (pattern_type, pattern_value, severity, created_by)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (pattern_type, pattern_value) DO NOTHING
            ''', pattern_type, pattern_value, severity, created_by)
            return True
    except Exception as e:
        logger.error(f"Failed to add spam pattern: {e}")
        return False


async def get_spam_patterns(
    pattern_type: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Get active spam patterns"""
    try:
        async with get_connection() as conn:
            if pattern_type:
                rows = await conn.fetch('''
                    SELECT * FROM spam_patterns
                    WHERE pattern_type = $1 AND is_active = TRUE
                ''', pattern_type)
            else:
                rows = await conn.fetch('''
                    SELECT * FROM spam_patterns
                    WHERE is_active = TRUE
                ''')
            
            return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Failed to get spam patterns: {e}")
        return []


# =========================================================================
# NEW MEMBER VERIFICATION
# =========================================================================

async def verify_new_member(
    api: TelegramAPI,
    chat_id: int,
    user_id: int,
    username: Optional[str] = None
) -> bool:
    """
    Send verification challenge to new member.
    
    Args:
        api: TelegramAPI instance
        chat_id: Chat ID
        user_id: New member's user ID
        username: New member's username
    
    Returns:
        True if verification sent
    """
    # Generate simple math challenge
    import random
    a = random.randint(1, 10)
    b = random.randint(1, 10)
    answer = a + b
    
    mention = f"@{username}" if username else f"User"
    
    # Create verification keyboard
    wrong_answers = [answer + random.randint(-3, 3) for _ in range(3)]
    wrong_answers = [x for x in wrong_answers if x != answer and x > 0][:3]
    
    options = wrong_answers + [answer]
    random.shuffle(options)
    
    keyboard = {
        "inline_keyboard": [[
            {"text": str(opt), "callback_data": f"verify:{user_id}:{opt}:{answer}"}
            for opt in options
        ]]
    }
    
    result = await api._request("sendMessage", {
        "chat_id": chat_id,
        "text": f"Welcome {mention}! Please verify you're human.\n\nWhat is {a} + {b}?",
        "reply_markup": keyboard
    })
    
    return result.get("ok", False)


async def handle_verification_callback(
    api: TelegramAPI,
    chat_id: int,
    message_id: int,
    user_id: int,
    callback_data: str
) -> bool:
    """
    Handle verification callback.
    
    Args:
        api: TelegramAPI instance
        chat_id: Chat ID
        message_id: Verification message ID
        user_id: User who clicked
        callback_data: Callback data
    
    Returns:
        True if verification passed
    """
    try:
        parts = callback_data.split(":")
        if len(parts) != 4 or parts[0] != "verify":
            return False
        
        target_user_id = int(parts[1])
        selected = int(parts[2])
        correct = int(parts[3])
        
        # Only the target user can verify
        if user_id != target_user_id:
            await api.answer_callback_query(
                callback_query_id="",  # Will be passed by caller
                text="This verification is not for you!",
                show_alert=True
            )
            return False
        
        if selected == correct:
            # Verification passed
            await api._request("editMessageText", {
                "chat_id": chat_id,
                "message_id": message_id,
                "text": "Verification passed! Welcome to the group."
            })
            return True
        else:
            # Wrong answer - kick user
            await api.ban_chat_member(chat_id, user_id)
            await asyncio.sleep(1)
            await api.unban_chat_member(chat_id, user_id)
            
            await api._request("editMessageText", {
                "chat_id": chat_id,
                "message_id": message_id,
                "text": "Verification failed. Please rejoin and try again."
            })
            return False
            
    except Exception as e:
        logger.error(f"Verification callback failed: {e}")
        return False
