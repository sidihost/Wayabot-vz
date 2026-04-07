"""
Waya Bot Builder - AI-Powered Content Scheduler
Determines optimal posting times and auto-schedules content based on engagement data.
"""

import asyncio
import logging
import json
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum

from ai_engine import get_groq_client, BEST_MODEL
from telegram_api import TelegramAPI, get_telegram_api
from database import get_connection

logger = logging.getLogger(__name__)


# =========================================================================
# DATA STRUCTURES
# =========================================================================

class ContentType(Enum):
    """Types of scheduled content"""
    TEXT = "text"
    PHOTO = "photo"
    VIDEO = "video"
    DOCUMENT = "document"
    POLL = "poll"
    ANIMATION = "animation"


@dataclass
class ScheduledContent:
    """A piece of scheduled content"""
    id: Optional[int] = None
    bot_id: int = 0
    user_id: int = 0
    chat_id: int = 0
    content: str = ""
    content_type: ContentType = ContentType.TEXT
    media_url: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    optimal_score: float = 0.0
    is_sent: bool = False
    is_cancelled: bool = False
    engagement_count: int = 0


@dataclass
class OptimalTimeSlot:
    """An optimal time slot for posting"""
    hour: int
    day_of_week: int  # 0 = Monday, 6 = Sunday
    score: float
    message_count: int
    reaction_count: int
    avg_response_time: int


# Day name mapping
DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


# =========================================================================
# ENGAGEMENT ANALYSIS
# =========================================================================

async def get_engagement_data(
    bot_id: int,
    chat_id: int,
    days: int = 30
) -> List[Dict[str, Any]]:
    """
    Get engagement data for analysis.
    
    Args:
        bot_id: Bot ID
        chat_id: Chat ID
        days: Number of days to look back
    
    Returns:
        List of engagement records
    """
    try:
        async with get_connection() as conn:
            rows = await conn.fetch('''
                SELECT 
                    hour_of_day, 
                    day_of_week,
                    SUM(message_count) as total_messages,
                    SUM(reaction_count) as total_reactions,
                    SUM(reply_count) as total_replies,
                    AVG(avg_response_time_ms) as avg_response_time,
                    MAX(updated_at) as last_updated
                FROM engagement_analytics
                WHERE bot_id = $1 AND chat_id = $2
                GROUP BY hour_of_day, day_of_week
                ORDER BY total_messages DESC
            ''', bot_id, chat_id)
            
            return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Failed to get engagement data: {e}")
        return []


async def calculate_optimal_times(
    bot_id: int,
    chat_id: int,
    top_n: int = 5
) -> List[OptimalTimeSlot]:
    """
    Calculate the optimal posting times based on engagement data.
    
    Args:
        bot_id: Bot ID
        chat_id: Chat ID
        top_n: Number of top slots to return
    
    Returns:
        List of optimal time slots
    """
    data = await get_engagement_data(bot_id, chat_id)
    
    if not data:
        # Return default slots if no data
        return get_default_optimal_times()
    
    # Calculate engagement score for each slot
    slots = []
    max_messages = max(d.get("total_messages", 0) for d in data) or 1
    max_reactions = max(d.get("total_reactions", 0) for d in data) or 1
    
    for d in data:
        messages = d.get("total_messages", 0)
        reactions = d.get("total_reactions", 0)
        replies = d.get("total_replies", 0)
        
        # Weighted score: messages + 2*reactions + 1.5*replies
        raw_score = (
            (messages / max_messages) * 0.4 +
            (reactions / max_reactions) * 0.4 +
            (replies / max(replies, 1)) * 0.2
        )
        
        slots.append(OptimalTimeSlot(
            hour=d.get("hour_of_day", 0),
            day_of_week=d.get("day_of_week", 0),
            score=round(raw_score * 100, 2),
            message_count=messages,
            reaction_count=reactions,
            avg_response_time=int(d.get("avg_response_time", 0))
        ))
    
    # Sort by score and return top N
    slots.sort(key=lambda x: x.score, reverse=True)
    return slots[:top_n]


def get_default_optimal_times() -> List[OptimalTimeSlot]:
    """Get default optimal times when no data is available"""
    # Default to common engagement peaks
    defaults = [
        OptimalTimeSlot(hour=9, day_of_week=1, score=80, message_count=0, reaction_count=0, avg_response_time=0),   # Tuesday 9am
        OptimalTimeSlot(hour=12, day_of_week=2, score=75, message_count=0, reaction_count=0, avg_response_time=0),  # Wednesday noon
        OptimalTimeSlot(hour=17, day_of_week=3, score=70, message_count=0, reaction_count=0, avg_response_time=0),  # Thursday 5pm
        OptimalTimeSlot(hour=10, day_of_week=0, score=65, message_count=0, reaction_count=0, avg_response_time=0),  # Monday 10am
        OptimalTimeSlot(hour=14, day_of_week=4, score=60, message_count=0, reaction_count=0, avg_response_time=0),  # Friday 2pm
    ]
    return defaults


async def suggest_best_posting_time(
    bot_id: int,
    chat_id: int,
    from_time: Optional[datetime] = None
) -> datetime:
    """
    Suggest the best next posting time.
    
    Args:
        bot_id: Bot ID
        chat_id: Chat ID
        from_time: Start time to look from (default: now)
    
    Returns:
        Suggested datetime for posting
    """
    if from_time is None:
        from_time = datetime.now(timezone.utc)
    
    optimal_slots = await calculate_optimal_times(bot_id, chat_id, top_n=10)
    
    if not optimal_slots:
        # Default to next hour
        return from_time + timedelta(hours=1)
    
    # Find the next available optimal slot
    current_day = from_time.weekday()
    current_hour = from_time.hour
    
    best_slot = None
    min_wait = timedelta(days=7)
    
    for slot in optimal_slots:
        # Calculate days until this slot
        days_until = (slot.day_of_week - current_day) % 7
        
        # If same day but hour passed, add a week
        if days_until == 0 and slot.hour <= current_hour:
            days_until = 7
        
        slot_time = from_time.replace(
            hour=slot.hour, 
            minute=0, 
            second=0, 
            microsecond=0
        ) + timedelta(days=days_until)
        
        wait_time = slot_time - from_time
        
        # Prefer slots with good score and reasonable wait time
        if wait_time < min_wait and slot.score >= 50:
            min_wait = wait_time
            best_slot = slot_time
    
    return best_slot or (from_time + timedelta(hours=1))


# =========================================================================
# CONTENT SCHEDULING
# =========================================================================

async def schedule_content(
    bot_id: int,
    user_id: int,
    chat_id: int,
    content: str,
    content_type: ContentType = ContentType.TEXT,
    media_url: Optional[str] = None,
    scheduled_at: Optional[datetime] = None,
    auto_optimize: bool = True
) -> Optional[int]:
    """
    Schedule content for posting.
    
    Args:
        bot_id: Bot ID
        user_id: User who created the content
        chat_id: Chat to post to
        content: Content text
        content_type: Type of content
        media_url: URL for media (if applicable)
        scheduled_at: When to post (None = auto-optimize)
        auto_optimize: Whether to use optimal time if scheduled_at is None
    
    Returns:
        Scheduled content ID or None
    """
    # Determine posting time
    if scheduled_at is None and auto_optimize:
        scheduled_at = await suggest_best_posting_time(bot_id, chat_id)
    elif scheduled_at is None:
        scheduled_at = datetime.now(timezone.utc) + timedelta(hours=1)
    
    # Calculate optimal score
    optimal_slots = await calculate_optimal_times(bot_id, chat_id)
    optimal_score = 0.0
    scheduled_hour = scheduled_at.hour
    scheduled_day = scheduled_at.weekday()
    
    for slot in optimal_slots:
        if slot.hour == scheduled_hour and slot.day_of_week == scheduled_day:
            optimal_score = slot.score
            break
    
    try:
        async with get_connection() as conn:
            row = await conn.fetchrow('''
                INSERT INTO scheduled_content
                (bot_id, user_id, chat_id, content, content_type, media_url, 
                 scheduled_at, optimal_score)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING id
            ''', bot_id, user_id, chat_id, content, content_type.value, 
                media_url, scheduled_at, optimal_score)
            
            return row['id'] if row else None
    except Exception as e:
        logger.error(f"Failed to schedule content: {e}")
        return None


async def get_pending_content(
    bot_id: Optional[int] = None,
    limit: int = 100
) -> List[ScheduledContent]:
    """
    Get content that is due to be sent.
    
    Args:
        bot_id: Optional bot ID filter
        limit: Maximum items to return
    
    Returns:
        List of pending scheduled content
    """
    try:
        async with get_connection() as conn:
            now = datetime.now(timezone.utc)
            
            if bot_id:
                rows = await conn.fetch('''
                    SELECT * FROM scheduled_content
                    WHERE bot_id = $1 
                    AND scheduled_at <= $2
                    AND is_sent = FALSE
                    AND is_cancelled = FALSE
                    ORDER BY scheduled_at ASC
                    LIMIT $3
                ''', bot_id, now, limit)
            else:
                rows = await conn.fetch('''
                    SELECT * FROM scheduled_content
                    WHERE scheduled_at <= $1
                    AND is_sent = FALSE
                    AND is_cancelled = FALSE
                    ORDER BY scheduled_at ASC
                    LIMIT $2
                ''', now, limit)
            
            return [
                ScheduledContent(
                    id=row['id'],
                    bot_id=row['bot_id'],
                    user_id=row['user_id'],
                    chat_id=row['chat_id'],
                    content=row['content'],
                    content_type=ContentType(row['content_type']),
                    media_url=row['media_url'],
                    scheduled_at=row['scheduled_at'],
                    optimal_score=float(row['optimal_score'] or 0),
                    is_sent=row['is_sent'],
                    is_cancelled=row['is_cancelled'],
                    engagement_count=row['engagement_count']
                )
                for row in rows
            ]
    except Exception as e:
        logger.error(f"Failed to get pending content: {e}")
        return []


async def mark_content_sent(
    content_id: int,
    success: bool = True,
    error_message: Optional[str] = None
) -> None:
    """Mark content as sent"""
    try:
        async with get_connection() as conn:
            if success:
                await conn.execute('''
                    UPDATE scheduled_content
                    SET is_sent = TRUE, sent_at = NOW()
                    WHERE id = $1
                ''', content_id)
            else:
                await conn.execute('''
                    UPDATE scheduled_content
                    SET error_message = $2
                    WHERE id = $1
                ''', content_id, error_message)
    except Exception as e:
        logger.error(f"Failed to mark content sent: {e}")


async def cancel_scheduled_content(content_id: int) -> bool:
    """Cancel scheduled content"""
    try:
        async with get_connection() as conn:
            await conn.execute('''
                UPDATE scheduled_content
                SET is_cancelled = TRUE
                WHERE id = $1 AND is_sent = FALSE
            ''', content_id)
            return True
    except Exception as e:
        logger.error(f"Failed to cancel content: {e}")
        return False


async def get_user_scheduled_content(
    bot_id: int,
    user_id: int,
    include_sent: bool = False,
    limit: int = 50
) -> List[ScheduledContent]:
    """Get scheduled content for a user"""
    try:
        async with get_connection() as conn:
            query = '''
                SELECT * FROM scheduled_content
                WHERE bot_id = $1 AND user_id = $2
            '''
            
            if not include_sent:
                query += ' AND is_sent = FALSE AND is_cancelled = FALSE'
            
            query += ' ORDER BY scheduled_at ASC LIMIT $3'
            
            rows = await conn.fetch(query, bot_id, user_id, limit)
            
            return [
                ScheduledContent(
                    id=row['id'],
                    bot_id=row['bot_id'],
                    user_id=row['user_id'],
                    chat_id=row['chat_id'],
                    content=row['content'],
                    content_type=ContentType(row['content_type']),
                    media_url=row['media_url'],
                    scheduled_at=row['scheduled_at'],
                    optimal_score=float(row['optimal_score'] or 0),
                    is_sent=row['is_sent'],
                    is_cancelled=row['is_cancelled'],
                    engagement_count=row['engagement_count']
                )
                for row in rows
            ]
    except Exception as e:
        logger.error(f"Failed to get user scheduled content: {e}")
        return []


# =========================================================================
# CONTENT SENDING
# =========================================================================

async def send_scheduled_content(
    api: TelegramAPI,
    content: ScheduledContent
) -> bool:
    """
    Send scheduled content.
    
    Args:
        api: TelegramAPI instance
        content: The content to send
    
    Returns:
        True if sent successfully
    """
    try:
        result = None
        
        if content.content_type == ContentType.TEXT:
            result = await api._request("sendMessage", {
                "chat_id": content.chat_id,
                "text": content.content,
                "parse_mode": "HTML"
            })
        
        elif content.content_type == ContentType.PHOTO:
            result = await api._request("sendPhoto", {
                "chat_id": content.chat_id,
                "photo": content.media_url,
                "caption": content.content,
                "parse_mode": "HTML"
            })
        
        elif content.content_type == ContentType.VIDEO:
            result = await api._request("sendVideo", {
                "chat_id": content.chat_id,
                "video": content.media_url,
                "caption": content.content,
                "parse_mode": "HTML"
            })
        
        elif content.content_type == ContentType.DOCUMENT:
            result = await api._request("sendDocument", {
                "chat_id": content.chat_id,
                "document": content.media_url,
                "caption": content.content,
                "parse_mode": "HTML"
            })
        
        elif content.content_type == ContentType.ANIMATION:
            result = await api._request("sendAnimation", {
                "chat_id": content.chat_id,
                "animation": content.media_url,
                "caption": content.content,
                "parse_mode": "HTML"
            })
        
        success = result.get("ok", False) if result else False
        
        if success:
            await mark_content_sent(content.id, True)
        else:
            error = result.get("description", "Unknown error") if result else "No response"
            await mark_content_sent(content.id, False, error)
        
        return success
        
    except Exception as e:
        logger.error(f"Failed to send scheduled content: {e}")
        await mark_content_sent(content.id, False, str(e))
        return False


# =========================================================================
# SCHEDULER JOB
# =========================================================================

async def process_scheduled_content(
    bot_tokens: Dict[int, str]
) -> Dict[str, int]:
    """
    Process all pending scheduled content.
    
    Args:
        bot_tokens: Mapping of bot_id to bot_token
    
    Returns:
        Summary of processed content
    """
    results = {
        "processed": 0,
        "sent": 0,
        "failed": 0,
        "skipped": 0
    }
    
    pending = await get_pending_content()
    
    for content in pending:
        results["processed"] += 1
        
        bot_token = bot_tokens.get(content.bot_id)
        if not bot_token:
            results["skipped"] += 1
            continue
        
        api = get_telegram_api(bot_token)
        success = await send_scheduled_content(api, content)
        
        if success:
            results["sent"] += 1
        else:
            results["failed"] += 1
        
        # Small delay between sends
        await asyncio.sleep(0.5)
    
    return results


# =========================================================================
# AI-POWERED CONTENT SUGGESTIONS
# =========================================================================

async def suggest_content_timing(
    content: str,
    chat_type: str = "group"
) -> Dict[str, Any]:
    """
    Use AI to suggest optimal timing for content.
    
    Args:
        content: The content to be posted
        chat_type: Type of chat (group, channel, private)
    
    Returns:
        Timing suggestions
    """
    client = get_groq_client()
    
    system_prompt = """You are a social media timing expert. Given content, suggest the best times to post for maximum engagement.

Return a JSON object:
{
    "recommended_day": "Monday-Sunday",
    "recommended_hour": 0-23,
    "reasoning": "brief explanation",
    "alternative_times": [
        {"day": "...", "hour": ...}
    ],
    "content_type": "informational|promotional|engaging|educational|entertainment",
    "audience_type": "professional|casual|mixed"
}

Return ONLY valid JSON."""

    user_prompt = f"Suggest optimal posting time for this {chat_type} content:\n\n{content[:500]}"
    
    try:
        response = await client.chat.completions.create(
            model=BEST_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.5,
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
        logger.error(f"AI timing suggestion failed: {e}")
        return {
            "recommended_day": "Tuesday",
            "recommended_hour": 10,
            "reasoning": "Default recommendation",
            "alternative_times": [],
            "content_type": "general",
            "audience_type": "mixed"
        }


async def generate_content_variations(
    original_content: str,
    count: int = 3
) -> List[str]:
    """
    Generate variations of content for A/B testing.
    
    Args:
        original_content: The original content
        count: Number of variations to generate
    
    Returns:
        List of content variations
    """
    client = get_groq_client()
    
    system_prompt = f"""Generate {count} variations of the given content. Each should:
- Convey the same message
- Use different wording/tone
- Be engaging and natural

Return a JSON array of strings:
["variation 1", "variation 2", ...]

Return ONLY valid JSON array."""

    try:
        response = await client.chat.completions.create(
            model=BEST_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Generate variations for:\n\n{original_content}"}
            ],
            temperature=0.8,
            max_tokens=500
        )
        
        result_text = response.choices[0].message.content.strip()
        
        # Handle code blocks
        if "```json" in result_text:
            result_text = result_text.split("```json")[1].split("```")[0]
        elif "```" in result_text:
            result_text = result_text.split("```")[1].split("```")[0]
        
        variations = json.loads(result_text)
        return variations[:count] if isinstance(variations, list) else [original_content]
        
    except Exception as e:
        logger.error(f"Content variation generation failed: {e}")
        return [original_content]


# =========================================================================
# ANALYTICS
# =========================================================================

async def get_scheduling_analytics(
    bot_id: int,
    days: int = 30
) -> Dict[str, Any]:
    """
    Get scheduling analytics for a bot.
    
    Args:
        bot_id: Bot ID
        days: Days to analyze
    
    Returns:
        Analytics summary
    """
    try:
        async with get_connection() as conn:
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            
            # Total scheduled
            total = await conn.fetchval('''
                SELECT COUNT(*) FROM scheduled_content
                WHERE bot_id = $1 AND created_at >= $2
            ''', bot_id, cutoff)
            
            # Sent successfully
            sent = await conn.fetchval('''
                SELECT COUNT(*) FROM scheduled_content
                WHERE bot_id = $1 AND created_at >= $2 AND is_sent = TRUE
            ''', bot_id, cutoff)
            
            # Average optimal score
            avg_score = await conn.fetchval('''
                SELECT AVG(optimal_score) FROM scheduled_content
                WHERE bot_id = $1 AND created_at >= $2 AND is_sent = TRUE
            ''', bot_id, cutoff)
            
            # Best performing hours
            best_hours = await conn.fetch('''
                SELECT 
                    EXTRACT(HOUR FROM scheduled_at) as hour,
                    COUNT(*) as count,
                    AVG(engagement_count) as avg_engagement
                FROM scheduled_content
                WHERE bot_id = $1 AND created_at >= $2 AND is_sent = TRUE
                GROUP BY EXTRACT(HOUR FROM scheduled_at)
                ORDER BY avg_engagement DESC
                LIMIT 5
            ''', bot_id, cutoff)
            
            return {
                "total_scheduled": total,
                "total_sent": sent,
                "success_rate": (sent / total * 100) if total > 0 else 0,
                "average_optimal_score": float(avg_score or 0),
                "best_hours": [dict(row) for row in best_hours]
            }
    except Exception as e:
        logger.error(f"Failed to get scheduling analytics: {e}")
        return {
            "total_scheduled": 0,
            "total_sent": 0,
            "success_rate": 0,
            "average_optimal_score": 0,
            "best_hours": []
        }
