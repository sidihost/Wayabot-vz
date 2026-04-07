"""
Waya Bot Builder - Smart Auto-Reply Suggestions System
Generates contextual reply suggestions using AI and learning from user behavior.
"""

import asyncio
import hashlib
import logging
import json
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone

from ai_engine import get_groq_client, BEST_MODEL
from telegram_api import TelegramAPI, get_telegram_api
from database import get_connection

logger = logging.getLogger(__name__)


# =========================================================================
# DATA STRUCTURES
# =========================================================================

@dataclass
class Suggestion:
    """A reply suggestion"""
    text: str
    confidence: float
    category: str  # question, action, response, follow_up
    emoji: Optional[str] = None
    callback_data: Optional[str] = None


@dataclass
class SuggestionResult:
    """Result of suggestion generation"""
    suggestions: List[Suggestion]
    context_summary: str
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# =========================================================================
# COMMON SUGGESTION TEMPLATES
# =========================================================================

# Quick responses for common scenarios
QUICK_SUGGESTIONS = {
    "greeting": [
        Suggestion("Hello! How can I help?", 0.9, "response"),
        Suggestion("Hi there!", 0.85, "response"),
        Suggestion("Hey! What's up?", 0.8, "response"),
    ],
    "thanks": [
        Suggestion("You're welcome!", 0.95, "response"),
        Suggestion("Happy to help!", 0.9, "response"),
        Suggestion("No problem!", 0.85, "response"),
    ],
    "question": [
        Suggestion("Could you provide more details?", 0.85, "follow_up"),
        Suggestion("Let me look into that", 0.8, "action"),
        Suggestion("That's a great question!", 0.75, "response"),
    ],
    "problem": [
        Suggestion("I'll help you with that", 0.9, "action"),
        Suggestion("Let me troubleshoot this", 0.85, "action"),
        Suggestion("Can you describe the issue?", 0.8, "follow_up"),
    ],
    "confirmation": [
        Suggestion("Yes, that's correct", 0.9, "response"),
        Suggestion("Confirmed!", 0.85, "response"),
        Suggestion("All set!", 0.8, "response"),
    ],
    "request": [
        Suggestion("I'll get that done", 0.9, "action"),
        Suggestion("Working on it now", 0.85, "action"),
        Suggestion("Give me a moment", 0.8, "action"),
    ],
    "feedback": [
        Suggestion("Thank you for the feedback!", 0.9, "response"),
        Suggestion("I appreciate you sharing that", 0.85, "response"),
        Suggestion("That's helpful to know", 0.8, "response"),
    ],
    "goodbye": [
        Suggestion("Goodbye! Have a great day!", 0.9, "response"),
        Suggestion("Take care!", 0.85, "response"),
        Suggestion("See you later!", 0.8, "response"),
    ],
}

# Category detection keywords
CATEGORY_KEYWORDS = {
    "greeting": ["hello", "hi", "hey", "good morning", "good evening", "greetings"],
    "thanks": ["thank", "thanks", "appreciate", "grateful"],
    "question": ["?", "how", "what", "when", "where", "why", "which", "can you"],
    "problem": ["issue", "problem", "error", "doesn't work", "broken", "help", "stuck"],
    "confirmation": ["ok", "okay", "sure", "yes", "agreed", "correct"],
    "request": ["please", "could you", "would you", "can you", "need"],
    "feedback": ["feedback", "suggestion", "think", "opinion", "review"],
    "goodbye": ["bye", "goodbye", "see you", "later", "take care"],
}


# =========================================================================
# SUGGESTION GENERATION
# =========================================================================

def detect_message_category(message_text: str) -> Optional[str]:
    """
    Detect the category of a message for quick suggestions.
    
    Args:
        message_text: The message to categorize
    
    Returns:
        Category name or None
    """
    text_lower = message_text.lower()
    
    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text_lower:
                return category
    
    return None


async def generate_suggestions_ai(
    message_text: str,
    conversation_context: Optional[List[Dict[str, str]]] = None,
    bot_persona: Optional[str] = None,
    count: int = 3
) -> SuggestionResult:
    """
    Generate smart reply suggestions using AI.
    
    Args:
        message_text: The message to respond to
        conversation_context: Recent conversation history
        bot_persona: Bot's personality/role description
        count: Number of suggestions to generate
    
    Returns:
        SuggestionResult with suggestions
    """
    client = get_groq_client()
    
    persona_context = ""
    if bot_persona:
        persona_context = f"\nYou are a {bot_persona}."
    
    context_text = ""
    if conversation_context:
        recent = conversation_context[-5:]
        context_text = "\nRecent conversation:\n" + "\n".join([
            f"{msg['role']}: {msg['content']}" for msg in recent
        ])
    
    system_prompt = f"""You are a smart reply suggestion generator.{persona_context}

Given a message, generate {count} natural reply suggestions that the user might want to send.

Requirements:
- Suggestions should be natural and conversational
- Each suggestion should be different in approach
- Keep suggestions concise (under 50 characters ideally)
- Include a variety: direct response, question, action

Return a JSON object:
{{
    "suggestions": [
        {{"text": "reply text", "confidence": 0.0-1.0, "category": "response|question|action|follow_up", "emoji": "optional emoji"}},
        ...
    ],
    "context_summary": "brief summary of conversation context"
}}

Return ONLY valid JSON."""

    user_prompt = f"Generate reply suggestions for this message:\n\"{message_text}\""
    if context_text:
        user_prompt += f"\n{context_text}"
    
    try:
        response = await client.chat.completions.create(
            model=BEST_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=400
        )
        
        result_text = response.choices[0].message.content.strip()
        
        # Handle code blocks
        if "```json" in result_text:
            result_text = result_text.split("```json")[1].split("```")[0]
        elif "```" in result_text:
            result_text = result_text.split("```")[1].split("```")[0]
        
        data = json.loads(result_text)
        
        suggestions = []
        for s in data.get("suggestions", [])[:count]:
            suggestions.append(Suggestion(
                text=s.get("text", "")[:100],  # Limit length
                confidence=float(s.get("confidence", 0.7)),
                category=s.get("category", "response"),
                emoji=s.get("emoji")
            ))
        
        return SuggestionResult(
            suggestions=suggestions,
            context_summary=data.get("context_summary", "")
        )
        
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse suggestions JSON: {e}")
        # Fall back to quick suggestions
        return await generate_quick_suggestions(message_text, count)
    except Exception as e:
        logger.error(f"AI suggestion generation failed: {e}")
        return await generate_quick_suggestions(message_text, count)


async def generate_quick_suggestions(
    message_text: str,
    count: int = 3
) -> SuggestionResult:
    """
    Generate quick suggestions without AI.
    
    Args:
        message_text: The message to respond to
        count: Number of suggestions
    
    Returns:
        SuggestionResult with quick suggestions
    """
    category = detect_message_category(message_text)
    
    if category and category in QUICK_SUGGESTIONS:
        suggestions = QUICK_SUGGESTIONS[category][:count]
    else:
        # Default suggestions
        suggestions = [
            Suggestion("I understand", 0.7, "response"),
            Suggestion("Tell me more", 0.6, "follow_up"),
            Suggestion("Let me check", 0.6, "action"),
        ][:count]
    
    return SuggestionResult(
        suggestions=suggestions,
        context_summary=f"Category: {category or 'general'}"
    )


async def generate_suggestions(
    message_text: str,
    conversation_context: Optional[List[Dict[str, str]]] = None,
    bot_persona: Optional[str] = None,
    count: int = 3,
    use_ai: bool = True
) -> SuggestionResult:
    """
    Main function to generate reply suggestions.
    
    Args:
        message_text: The message to respond to
        conversation_context: Recent conversation history
        bot_persona: Bot's personality description
        count: Number of suggestions
        use_ai: Whether to use AI generation
    
    Returns:
        SuggestionResult
    """
    # Skip for very short messages
    if len(message_text.strip()) < 3:
        return SuggestionResult(suggestions=[], context_summary="Message too short")
    
    if use_ai and len(message_text) > 10:
        return await generate_suggestions_ai(
            message_text, conversation_context, bot_persona, count
        )
    else:
        return await generate_quick_suggestions(message_text, count)


# =========================================================================
# TELEGRAM INTEGRATION
# =========================================================================

async def send_message_with_suggestions(
    api: TelegramAPI,
    chat_id: int,
    response_text: str,
    suggestions: List[Suggestion],
    bot_id: Optional[int] = None,
    parse_mode: str = "HTML"
) -> Optional[Dict[str, Any]]:
    """
    Send a message with suggestion buttons.
    
    Args:
        api: TelegramAPI instance
        chat_id: Chat ID
        response_text: Main message text
        suggestions: List of suggestions
        bot_id: Bot ID for tracking
        parse_mode: Parse mode for message
    
    Returns:
        Message result or None
    """
    if not suggestions:
        return await api._request("sendMessage", {
            "chat_id": chat_id,
            "text": response_text,
            "parse_mode": parse_mode
        })
    
    # Build keyboard
    buttons = []
    for i, suggestion in enumerate(suggestions):
        # Create callback data
        text_hash = hashlib.md5(suggestion.text.encode()).hexdigest()[:8]
        callback_data = f"sug:{i}:{text_hash}"
        
        # Button text with optional emoji
        button_text = suggestion.text[:32]
        if suggestion.emoji:
            button_text = f"{suggestion.emoji} {button_text}"
        
        buttons.append({
            "text": button_text,
            "callback_data": callback_data
        })
    
    # Arrange buttons (2 per row for mobile friendliness)
    keyboard = []
    for i in range(0, len(buttons), 2):
        keyboard.append(buttons[i:i+2])
    
    result = await api._request("sendMessage", {
        "chat_id": chat_id,
        "text": response_text,
        "parse_mode": parse_mode,
        "reply_markup": {
            "inline_keyboard": keyboard
        }
    })
    
    # Track suggestions if bot_id provided
    if bot_id and result.get("ok"):
        for suggestion in suggestions:
            await track_suggestion(
                bot_id=bot_id,
                chat_id=chat_id,
                user_id=0,  # Will be filled when used
                suggestion_text=suggestion.text
            )
    
    return result


async def handle_suggestion_callback(
    api: TelegramAPI,
    chat_id: int,
    user_id: int,
    message_id: int,
    callback_data: str,
    bot_id: Optional[int] = None
) -> Optional[str]:
    """
    Handle when user clicks a suggestion.
    
    Args:
        api: TelegramAPI instance
        chat_id: Chat ID
        user_id: User who clicked
        message_id: Message with suggestions
        callback_data: Callback data from button
        bot_id: Bot ID for tracking
    
    Returns:
        The suggestion text that was selected
    """
    try:
        parts = callback_data.split(":")
        if len(parts) < 2 or parts[0] != "sug":
            return None
        
        suggestion_index = int(parts[1])
        
        # Remove the keyboard from the message
        await api.edit_message_reply_markup(chat_id, message_id, None)
        
        # Track that suggestion was used
        if bot_id:
            await mark_suggestion_used(bot_id, chat_id, user_id)
        
        # Return a placeholder - actual suggestion text should be stored
        return f"Suggestion {suggestion_index} selected"
        
    except Exception as e:
        logger.error(f"Suggestion callback failed: {e}")
        return None


# =========================================================================
# LEARNING & TRACKING
# =========================================================================

async def track_suggestion(
    bot_id: int,
    chat_id: int,
    user_id: int,
    suggestion_text: str
) -> None:
    """Track a suggestion that was shown"""
    try:
        context_hash = hashlib.md5(f"{chat_id}:{suggestion_text}".encode()).hexdigest()
        
        async with get_connection() as conn:
            await conn.execute('''
                INSERT INTO suggestion_usage
                (bot_id, chat_id, user_id, suggestion_text, context_hash)
                VALUES ($1, $2, $3, $4, $5)
            ''', bot_id, chat_id, user_id, suggestion_text, context_hash)
    except Exception as e:
        logger.error(f"Failed to track suggestion: {e}")


async def mark_suggestion_used(
    bot_id: int,
    chat_id: int,
    user_id: int
) -> None:
    """Mark the most recent suggestion as used"""
    try:
        async with get_connection() as conn:
            await conn.execute('''
                UPDATE suggestion_usage
                SET was_used = TRUE
                WHERE id = (
                    SELECT id FROM suggestion_usage
                    WHERE bot_id = $1 AND chat_id = $2
                    ORDER BY created_at DESC
                    LIMIT 1
                )
            ''', bot_id, chat_id)
    except Exception as e:
        logger.error(f"Failed to mark suggestion used: {e}")


async def get_suggestion_stats(
    bot_id: int
) -> Dict[str, Any]:
    """Get suggestion usage statistics"""
    try:
        async with get_connection() as conn:
            total = await conn.fetchval('''
                SELECT COUNT(*) FROM suggestion_usage WHERE bot_id = $1
            ''', bot_id)
            
            used = await conn.fetchval('''
                SELECT COUNT(*) FROM suggestion_usage 
                WHERE bot_id = $1 AND was_used = TRUE
            ''', bot_id)
            
            # Most used suggestions
            popular = await conn.fetch('''
                SELECT suggestion_text, COUNT(*) as count
                FROM suggestion_usage
                WHERE bot_id = $1 AND was_used = TRUE
                GROUP BY suggestion_text
                ORDER BY count DESC
                LIMIT 10
            ''', bot_id)
            
            return {
                "total_shown": total,
                "total_used": used,
                "usage_rate": (used / total * 100) if total > 0 else 0,
                "popular_suggestions": [dict(row) for row in popular]
            }
    except Exception as e:
        logger.error(f"Failed to get suggestion stats: {e}")
        return {
            "total_shown": 0,
            "total_used": 0,
            "usage_rate": 0,
            "popular_suggestions": []
        }


# =========================================================================
# CONTEXTUAL SUGGESTIONS
# =========================================================================

async def generate_contextual_suggestions(
    bot_id: int,
    chat_id: int,
    message_text: str,
    user_history: Optional[List[str]] = None,
    count: int = 3
) -> SuggestionResult:
    """
    Generate suggestions based on user history and context.
    
    Args:
        bot_id: Bot ID
        chat_id: Chat ID
        message_text: Current message
        user_history: User's previous messages
        count: Number of suggestions
    
    Returns:
        SuggestionResult with contextual suggestions
    """
    # Get previously used suggestions for this user
    popular = await get_popular_suggestions_for_context(bot_id, chat_id)
    
    # If we have popular suggestions, include them
    if popular and len(popular) >= count:
        suggestions = [
            Suggestion(text=s["text"], confidence=0.9, category="learned")
            for s in popular[:count]
        ]
        return SuggestionResult(
            suggestions=suggestions,
            context_summary="Based on your previous choices"
        )
    
    # Otherwise, generate new suggestions
    return await generate_suggestions(
        message_text,
        count=count,
        use_ai=True
    )


async def get_popular_suggestions_for_context(
    bot_id: int,
    chat_id: int,
    limit: int = 5
) -> List[Dict[str, Any]]:
    """Get popular suggestions for this chat context"""
    try:
        async with get_connection() as conn:
            rows = await conn.fetch('''
                SELECT suggestion_text as text, COUNT(*) as usage_count
                FROM suggestion_usage
                WHERE bot_id = $1 AND chat_id = $2 AND was_used = TRUE
                GROUP BY suggestion_text
                ORDER BY usage_count DESC
                LIMIT $3
            ''', bot_id, chat_id, limit)
            
            return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Failed to get popular suggestions: {e}")
        return []


# =========================================================================
# FOLLOW-UP SUGGESTIONS
# =========================================================================

FOLLOW_UP_TEMPLATES = {
    "order": [
        "Where's my order?",
        "Track my package",
        "Cancel my order",
        "Change my address"
    ],
    "support": [
        "I need more help",
        "Talk to a human",
        "This didn't solve my issue",
        "Open a ticket"
    ],
    "info": [
        "Tell me more",
        "What are the features?",
        "How much does it cost?",
        "What's included?"
    ],
    "action": [
        "Yes, proceed",
        "No, cancel",
        "Give me options",
        "I'll think about it"
    ]
}


async def generate_follow_up_suggestions(
    last_bot_message: str,
    context_type: Optional[str] = None,
    count: int = 3
) -> List[Suggestion]:
    """
    Generate follow-up suggestions based on the bot's last message.
    
    Args:
        last_bot_message: The bot's previous response
        context_type: Type of context (order, support, info, action)
        count: Number of suggestions
    
    Returns:
        List of follow-up suggestions
    """
    # Try to detect context type from message
    if not context_type:
        msg_lower = last_bot_message.lower()
        if any(w in msg_lower for w in ["order", "shipping", "delivery", "package"]):
            context_type = "order"
        elif any(w in msg_lower for w in ["help", "support", "issue", "problem"]):
            context_type = "support"
        elif any(w in msg_lower for w in ["feature", "plan", "price", "offer"]):
            context_type = "info"
        elif any(w in msg_lower for w in ["confirm", "proceed", "continue", "would you"]):
            context_type = "action"
    
    if context_type and context_type in FOLLOW_UP_TEMPLATES:
        templates = FOLLOW_UP_TEMPLATES[context_type][:count]
        return [
            Suggestion(text=t, confidence=0.8, category="follow_up")
            for t in templates
        ]
    
    # Default follow-ups
    return [
        Suggestion("Tell me more", 0.7, "follow_up"),
        Suggestion("That's all for now", 0.6, "follow_up"),
        Suggestion("I have another question", 0.6, "follow_up"),
    ][:count]
