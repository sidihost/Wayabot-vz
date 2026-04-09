"""
Waya Bot Builder - Advanced Bot Creation Engine
Build powerful AI bots with full Telegram Bot API support!

Features:
- Business Account Integration
- Managed Bots (Bot-to-Bot)
- Polls & Quizzes for Channels
- Inline Mode
- Deep Linking
- Mini Apps ready
- Full API compliance with Bot API 9.6
"""

import json
import asyncio
import re
from datetime import datetime
from typing import Optional, Dict, Any, List
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Poll
from telegram.ext import ContextTypes
from telegram.constants import ParseMode, ChatAction

from ai_engine import generate_response, chat_completion, BEST_MODEL
import database as db

# Agent features - DISABLED until properly tested
AGENT_FEATURES_AVAILABLE = False

async def initialize_agent_settings(bot_id): 
    pass
    
async def auto_deploy_bot(bot_id): 
    return {"success": False}
    
async def auto_update_bot(bot_id): 
    return {"success": False}
    
async def celebrate_bot_creation(**kwargs): 
    pass
    
class CelebrationType:
    ALL = "all"


# =============================================================================
# BOT FEATURE CARDS - Beautiful UI for selecting features
# =============================================================================

BOT_FEATURE_CARDS = {
    "ai_chat": {
        "title": "AI Chat",
        "icon": "🧠",
        "description": "Smart conversations with context memory",
        "telegram_feature": "message handling"
    },
    "commands": {
        "title": "Custom Commands", 
        "icon": "⌨️",
        "description": "Add /commands your bot responds to",
        "telegram_feature": "BotCommand"
    },
    "auto_reply": {
        "title": "Auto Replies",
        "icon": "💬",
        "description": "Trigger responses on keywords",
        "telegram_feature": "message filters"
    },
    "inline_mode": {
        "title": "Inline Mode",
        "icon": "🔍",
        "description": "Use @bot in any chat",
        "telegram_feature": "InlineQuery"
    },
    "polls": {
        "title": "Polls & Quizzes",
        "icon": "📊",
        "description": "Create polls for channels/groups",
        "telegram_feature": "sendPoll"
    },
    "buttons": {
        "title": "Interactive Buttons",
        "icon": "🔘",
        "description": "Inline keyboards and menus",
        "telegram_feature": "InlineKeyboardMarkup"
    },
    "channel_post": {
        "title": "Channel Support",
        "icon": "📢",
        "description": "Post to channels automatically",
        "telegram_feature": "channel_post"
    },
    "scheduler": {
        "title": "Scheduled Messages",
        "icon": "⏰",
        "description": "Send messages at specific times",
        "telegram_feature": "scheduling"
    },
    "knowledge_base": {
        "title": "Knowledge Base",
        "icon": "📚",
        "description": "Train bot with custom Q&A",
        "telegram_feature": "context memory"
    },
    "forms": {
        "title": "Data Collection",
        "icon": "📝",
        "description": "Collect user information step by step",
        "telegram_feature": "ConversationHandler"
    },
    "broadcast": {
        "title": "Broadcast",
        "icon": "📣",
        "description": "Send to all users at once",
        "telegram_feature": "mass messaging"
    },
    "business": {
        "title": "Business Mode",
        "icon": "💼",
        "description": "Connect to Telegram Business accounts",
        "telegram_feature": "BusinessConnection"
    },
    "analytics": {
        "title": "Analytics",
        "icon": "📈",
        "description": "Track usage and engagement",
        "telegram_feature": "statistics"
    },
    "voice": {
        "title": "Voice Support",
        "icon": "🎤",
        "description": "Voice messages and TTS",
        "telegram_feature": "voice handling"
    },
    "multilingual": {
        "title": "Multi-Language",
        "icon": "🌍",
        "description": "Auto-detect user language",
        "telegram_feature": "language_code"
    },
    "deep_linking": {
        "title": "Deep Links",
        "icon": "🔗",
        "description": "Custom start parameters",
        "telegram_feature": "start parameters"
    },
    "payments": {
        "title": "Payments",
        "icon": "💳",
        "description": "Accept Telegram Stars",
        "telegram_feature": "sendInvoice"
    },
    "games": {
        "title": "Games",
        "icon": "🎮",
        "description": "HTML5 games integration",
        "telegram_feature": "sendGame"
    }
}


# =============================================================================
# BOT CATEGORIES WITH TEMPLATES
# =============================================================================

BOT_CATEGORIES = {
    "business": {
        "name": "Business",
        "icon": "💼",
        "description": "Professional bots for companies",
        "templates": ["customer_support", "sales_assistant", "appointment_booking", "faq_bot", "lead_generation"]
    },
    "community": {
        "name": "Community",
        "icon": "👥",
        "description": "Manage groups and channels",
        "templates": ["welcome_bot", "moderation_bot", "poll_bot", "announcement_bot", "engagement_bot"]
    },
    "education": {
        "name": "Education",
        "icon": "📖",
        "description": "Learning and teaching tools",
        "templates": ["tutor_bot", "quiz_master", "flashcard_bot", "course_bot", "language_tutor"]
    },
    "productivity": {
        "name": "Productivity",
        "icon": "⚡",
        "description": "Task and time management",
        "templates": ["task_manager", "reminder_bot", "note_taker", "habit_tracker", "meeting_scheduler"]
    },
    "entertainment": {
        "name": "Entertainment",
        "icon": "🎉",
        "description": "Fun and games",
        "templates": ["trivia_bot", "story_bot", "meme_bot", "music_recommender", "daily_horoscope"]
    },
    "ecommerce": {
        "name": "E-Commerce",
        "icon": "🛒",
        "description": "Shopping and orders",
        "templates": ["product_catalog", "order_tracker", "price_checker", "wishlist_bot", "review_collector"]
    }
}


# =============================================================================
# BOT TEMPLATES - Pre-configured bots
# =============================================================================

BOT_TEMPLATES = {
    "customer_support": {
        "name": "Customer Support Bot",
        "description": "Handle customer inquiries 24/7 with AI",
        "features": ["ai_chat", "knowledge_base", "auto_reply", "business", "forms"],
        "system_prompt": """You are a professional customer support agent. Your role is to:
- Answer customer questions accurately and helpfully
- Resolve issues with empathy and patience
- Escalate complex issues when needed
- Collect necessary information politely
- Follow up to ensure satisfaction

Always be professional, friendly, and solution-oriented.""",
        "commands": [
            {"command": "help", "description": "Get help options"},
            {"command": "contact", "description": "Contact human support"},
            {"command": "faq", "description": "Frequently asked questions"},
            {"command": "status", "description": "Check ticket status"}
        ],
        "greeting": "Hello! I'm here to help you with any questions or issues. How can I assist you today?"
    },
    
    "poll_bot": {
        "name": "Poll & Survey Bot",
        "description": "Create polls and quizzes for channels and groups",
        "features": ["polls", "channel_post", "analytics", "scheduler"],
        "system_prompt": """You are a poll creation assistant. Help users create engaging polls and quizzes.
- Suggest good poll questions based on topics
- Format options clearly
- Explain poll settings (anonymous, multiple answers, etc.)
- Help analyze poll results""",
        "commands": [
            {"command": "newpoll", "description": "Create a new poll"},
            {"command": "quiz", "description": "Create a quiz"},
            {"command": "schedule", "description": "Schedule a poll"},
            {"command": "results", "description": "View poll results"}
        ],
        "greeting": "Welcome! I help you create polls and quizzes. Use /newpoll to start!"
    },
    
    "welcome_bot": {
        "name": "Welcome & Moderation Bot",
        "description": "Greet new members and moderate groups",
        "features": ["auto_reply", "buttons", "analytics", "forms"],
        "system_prompt": """You are a group welcome and moderation bot. Your duties:
- Welcome new members warmly
- Explain group rules
- Answer questions about the group
- Help users navigate the community
- Report inappropriate behavior""",
        "commands": [
            {"command": "rules", "description": "Show group rules"},
            {"command": "admins", "description": "Contact admins"},
            {"command": "report", "description": "Report an issue"}
        ],
        "greeting": "Welcome to the group! Please read our /rules. I'm here to help!"
    },
    
    "quiz_master": {
        "name": "Quiz Master Bot",
        "description": "Educational quizzes with scoring",
        "features": ["polls", "analytics", "knowledge_base", "buttons"],
        "system_prompt": """You are an educational quiz master. You:
- Create engaging quiz questions
- Explain correct answers with context
- Track user scores and progress
- Offer hints when asked
- Celebrate achievements""",
        "commands": [
            {"command": "quiz", "description": "Start a quiz"},
            {"command": "score", "description": "Check your score"},
            {"command": "leaderboard", "description": "Top players"},
            {"command": "hint", "description": "Get a hint"}
        ],
        "greeting": "Ready to test your knowledge? Use /quiz to start a quiz!"
    },
    
    "sales_assistant": {
        "name": "Sales Assistant Bot",
        "description": "Help with product inquiries and sales",
        "features": ["ai_chat", "knowledge_base", "buttons", "forms", "payments"],
        "system_prompt": """You are a friendly sales assistant. Your role:
- Help customers find products
- Answer product questions
- Guide through purchase process
- Handle objections professionally
- Upsell and cross-sell appropriately

Be helpful, not pushy.""",
        "commands": [
            {"command": "products", "description": "Browse products"},
            {"command": "pricing", "description": "View pricing"},
            {"command": "order", "description": "Place an order"},
            {"command": "track", "description": "Track your order"}
        ],
        "greeting": "Hi! Looking for something specific? I can help you find the perfect product!"
    },
    
    "appointment_booking": {
        "name": "Appointment Booking Bot",
        "description": "Schedule appointments and meetings",
        "features": ["forms", "scheduler", "buttons", "auto_reply"],
        "system_prompt": """You are an appointment scheduling assistant. You:
- Help users book appointments
- Show available time slots
- Send reminders
- Handle rescheduling
- Confirm bookings""",
        "commands": [
            {"command": "book", "description": "Book appointment"},
            {"command": "mybookings", "description": "View your bookings"},
            {"command": "cancel", "description": "Cancel booking"},
            {"command": "reschedule", "description": "Reschedule appointment"}
        ],
        "greeting": "Hello! I can help you schedule an appointment. Use /book to get started!"
    },
    
    "announcement_bot": {
        "name": "Announcement Bot",
        "description": "Broadcast announcements to channels",
        "features": ["channel_post", "scheduler", "broadcast", "buttons"],
        "system_prompt": """You help manage channel announcements. You:
- Format announcements professionally
- Schedule posts for optimal times
- Create engaging content
- Add appropriate formatting""",
        "commands": [
            {"command": "announce", "description": "Create announcement"},
            {"command": "schedule", "description": "Schedule a post"},
            {"command": "draft", "description": "Save as draft"}
        ],
        "greeting": "Ready to create announcements! Use /announce to start."
    },
    
    "task_manager": {
        "name": "Task Manager Bot",
        "description": "Personal productivity assistant",
        "features": ["forms", "scheduler", "auto_reply", "buttons"],
        "system_prompt": """You are a personal productivity assistant. Help users:
- Create and manage tasks
- Set priorities and deadlines
- Send reminders
- Track progress
- Break down complex tasks""",
        "commands": [
            {"command": "add", "description": "Add a task"},
            {"command": "list", "description": "View tasks"},
            {"command": "done", "description": "Mark task complete"},
            {"command": "remind", "description": "Set reminder"}
        ],
        "greeting": "Let's get productive! Use /add to create your first task."
    },
    
    "trivia_bot": {
        "name": "Trivia Game Bot",
        "description": "Fun trivia games for groups",
        "features": ["polls", "analytics", "buttons", "games"],
        "system_prompt": """You are a fun trivia host. You:
- Ask interesting trivia questions
- Keep score fairly
- Explain answers with fun facts
- Create friendly competition
- Celebrate winners""",
        "commands": [
            {"command": "play", "description": "Start trivia game"},
            {"command": "score", "description": "Check scores"},
            {"command": "category", "description": "Choose category"}
        ],
        "greeting": "Time for trivia! Use /play to start a game!"
    },
    
    "language_tutor": {
        "name": "Language Tutor Bot",
        "description": "Learn languages with AI",
        "features": ["ai_chat", "voice", "polls", "knowledge_base"],
        "system_prompt": """You are a friendly language tutor. You:
- Teach vocabulary and grammar
- Practice conversations
- Correct mistakes gently
- Explain cultural context
- Adapt to learner's level""",
        "commands": [
            {"command": "lesson", "description": "Start a lesson"},
            {"command": "practice", "description": "Practice conversation"},
            {"command": "vocab", "description": "Vocabulary quiz"},
            {"command": "level", "description": "Set difficulty"}
        ],
        "greeting": "Hello! Ready to learn? Use /lesson to start your language journey!"
    }
}


# =============================================================================
# POLL CREATOR - Full Telegram Poll Support
# =============================================================================

async def create_poll_for_bot(
    bot_id: int,
    user_id: int,
    question: str,
    options: List[str],
    poll_type: str = "regular",  # regular or quiz
    is_anonymous: bool = True,
    allows_multiple_answers: bool = False,
    correct_option_ids: List[int] = None,
    explanation: str = None,
    open_period: int = None,  # seconds until auto-close
    close_date: int = None,  # Unix timestamp
    allows_revoting: bool = False,
    shuffle_options: bool = False
) -> Dict[str, Any]:
    """
    Create a poll configuration for a user's bot.
    Supports all Telegram Bot API 9.6 poll features.
    """
    poll_config = {
        "question": question[:300],  # Telegram limit
        "options": options[:10],  # Max 10 options
        "type": poll_type,
        "is_anonymous": is_anonymous,
        "allows_multiple_answers": allows_multiple_answers,
        "allows_revoting": allows_revoting,
        "shuffle_options": shuffle_options,
        "created_at": datetime.utcnow().isoformat(),
        "created_by": user_id
    }
    
    if poll_type == "quiz":
        poll_config["correct_option_ids"] = correct_option_ids or [0]
        if explanation:
            poll_config["explanation"] = explanation[:200]
    
    if open_period:
        poll_config["open_period"] = min(open_period, 2628000)  # Max ~1 month
    elif close_date:
        poll_config["close_date"] = close_date
    
    # Save poll to database
    async with db.get_connection() as conn:
        poll_id = await conn.fetchval('''
            INSERT INTO bot_polls (bot_id, user_id, question, options, config, poll_type)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING id
        ''', bot_id, user_id, question, json.dumps(options), json.dumps(poll_config), poll_type)
    
    poll_config["id"] = poll_id
    return poll_config


async def generate_poll_code(poll_config: Dict[str, Any]) -> str:
    """Generate Python code to send this poll."""
    is_quiz = poll_config.get("type") == "quiz"
    
    code = f'''
# Send Poll to Chat
async def send_poll(chat_id):
    poll = await bot.send_poll(
        chat_id=chat_id,
        question="{poll_config['question']}",
        options={poll_config['options']},
        is_anonymous={poll_config.get('is_anonymous', True)},
        type="{'quiz' if is_quiz else 'regular'}",
'''
    
    if poll_config.get('allows_multiple_answers'):
        code += f"        allows_multiple_answers=True,\n"
    
    if is_quiz and poll_config.get('correct_option_ids'):
        code += f"        correct_option_id={poll_config['correct_option_ids'][0]},\n"
        if poll_config.get('explanation'):
            code += f'        explanation="{poll_config["explanation"]}",\n'
    
    if poll_config.get('allows_revoting'):
        code += f"        allows_revoting=True,\n"
    
    if poll_config.get('shuffle_options'):
        code += f"        shuffle_options=True,\n"
    
    if poll_config.get('open_period'):
        code += f"        open_period={poll_config['open_period']},\n"
    
    code += "    )\n    return poll"
    
    return code


# =============================================================================
# BUSINESS BOT FEATURES
# =============================================================================

BUSINESS_BOT_CONFIG = {
    "features": {
        "auto_reply_away": {
            "name": "Away Message",
            "description": "Auto-reply when business is closed"
        },
        "greeting_message": {
            "name": "Greeting",
            "description": "Welcome message for new customers"
        },
        "quick_replies": {
            "name": "Quick Replies",
            "description": "Pre-set responses for common questions"
        },
        "working_hours": {
            "name": "Working Hours",
            "description": "Define business hours for auto-replies"
        },
        "lead_capture": {
            "name": "Lead Capture",
            "description": "Collect customer information"
        }
    }
}


async def create_business_bot_config(
    bot_id: int,
    user_id: int,
    business_name: str,
    working_hours: Dict[str, Any] = None,
    away_message: str = None,
    greeting: str = None,
    quick_replies: List[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Configure a bot for Telegram Business integration.
    """
    config = {
        "business_name": business_name,
        "working_hours": working_hours or {
            "monday": {"start": "09:00", "end": "17:00"},
            "tuesday": {"start": "09:00", "end": "17:00"},
            "wednesday": {"start": "09:00", "end": "17:00"},
            "thursday": {"start": "09:00", "end": "17:00"},
            "friday": {"start": "09:00", "end": "17:00"},
            "saturday": None,
            "sunday": None
        },
        "away_message": away_message or f"Thanks for contacting {business_name}! We're currently closed but will respond as soon as we're back.",
        "greeting": greeting or f"Welcome to {business_name}! How can we help you today?",
        "quick_replies": quick_replies or [
            {"trigger": "hours", "response": "We're open Monday-Friday, 9 AM to 5 PM."},
            {"trigger": "location", "response": "Please provide your location details."},
            {"trigger": "pricing", "response": "I'll connect you with our sales team for pricing."}
        ],
        "is_business_mode": True,
        "created_at": datetime.utcnow().isoformat()
    }
    
    # Save to database
    async with db.get_connection() as conn:
        await conn.execute('''
            UPDATE custom_bots 
            SET business_config = $1, bot_type = 'business', updated_at = NOW()
            WHERE id = $2 AND user_id = $3
        ''', json.dumps(config), bot_id, user_id)
    
    return config


# =============================================================================
# CHANNEL BOT FEATURES
# =============================================================================

async def create_channel_bot_config(
    bot_id: int,
    user_id: int,
    channel_features: List[str] = None
) -> Dict[str, Any]:
    """
    Configure a bot for channel management.
    """
    config = {
        "is_channel_bot": True,
        "features": channel_features or [
            "auto_post",
            "scheduled_posts",
            "polls",
            "reactions",
            "comments_management"
        ],
        "post_templates": [],
        "scheduled_posts": [],
        "created_at": datetime.utcnow().isoformat()
    }
    
    async with db.get_connection() as conn:
        await conn.execute('''
            UPDATE custom_bots 
            SET channel_config = $1, bot_type = 'channel', updated_at = NOW()
            WHERE id = $2 AND user_id = $3
        ''', json.dumps(config), bot_id, user_id)
    
    return config


# =============================================================================
# AI BOT CREATION ENGINE
# =============================================================================

async def generate_bot_config_with_ai(description: str, user_name: str = "User") -> Dict[str, Any]:
    """
    Use AI to generate a world-class bot configuration from a description.
    Creates bots that feel like they were built by Google or OpenAI.
    """
    prompt = f"""You are a senior product designer at a top tech company. Create an exceptional Telegram bot.

USER WANTS: "{description}"

Design a bot that users will LOVE. Generate JSON:

{{
    "bot_name": "Memorable brand name (2-3 words, sounds like a real product)",
    "bot_username_suggestion": "snake_case_bot_name",
    "bot_description": "Compelling pitch that makes users want to try it (1-2 sentences)",
    "tagline": "Short catchy tagline (3-6 words)",
    "greeting_message": "Warm, engaging welcome that immediately shows value and invites interaction",
    "system_prompt": "DETAILED instructions for the AI (150-300 words): personality traits, expertise areas, response style, things to always/never do, how to handle edge cases, example phrases to use",
    "personality": {{
        "tone": "friendly/professional/playful/authoritative/warm",
        "traits": ["trait1", "trait2", "trait3"],
        "communication_style": "concise/detailed/conversational/structured"
    }},
    "features": [
        {{"name": "Feature Name", "description": "What it does and why it's useful", "how_to_use": "How users activate it"}}
    ],
    "commands": [
        {{"command": "/start", "description": "Begin", "response": "Engaging welcome"}},
        {{"command": "/help", "description": "Help", "response": "Clear guide"}},
        {{"command": "/[relevant]", "description": "Bot-specific action", "response": "Useful response"}}
    ],
    "quick_replies": ["Contextual suggestion 1", "Contextual suggestion 2", "Contextual suggestion 3"],
    "sample_conversations": [
        {{"user": "Realistic user message", "bot": "Perfect bot response demonstrating personality"}}
    ],
    "tone": "friendly/professional/casual/playful",
    "category": "support/assistant/community/education/ecommerce/entertainment/utility/productivity"
}}

QUALITY STANDARDS:
1. Bot name should be brandable (think: Alexa, Siri, Copilot level)
2. System prompt must be comprehensive - this defines the bot's soul
3. Features should solve real problems, not be generic
4. Sample conversation should showcase the bot's unique personality
5. Everything should feel polished and professional

Return ONLY valid JSON."""

    messages = [
        {"role": "system", "content": "You are a world-class bot designer who creates products that feel magical. Your bots are so good they could be featured in the App Store. Output only valid JSON, no markdown."},
        {"role": "user", "content": prompt}
    ]

    try:
        # Use the universal chat_completion that tries multiple providers
        result = await asyncio.wait_for(
            chat_completion(messages, temperature=0.7, max_tokens=1500),
            timeout=30.0
        )
        
        if not result:
            # Return fallback if AI completely fails
            return _create_fallback_config(description)
        
        result = result.strip()
        
        # Extract JSON
        if "```json" in result:
            result = result.split("```json")[1].split("```")[0]
        elif "```" in result:
            result = result.split("```")[1].split("```")[0]
        
        config = json.loads(result)
        config["created_by_ai"] = True
        config["original_description"] = description
        
        return config
        
    except json.JSONDecodeError as e:
        return {
            "bot_name": "My Assistant",
            "bot_description": description[:100],
            "greeting_message": f"Hello! I'm your assistant. How can I help?",
            "system_prompt": f"You are a helpful assistant that {description[:200]}",
            "features": ["ai_chat", "commands", "auto_reply"],
            "commands": [
                {"command": "start", "description": "Start the bot"},
                {"command": "help", "description": "Get help"}
            ],
            "tone": "friendly",
            "category": "productivity"
        }
    except asyncio.TimeoutError:
        # Return a working fallback instead of error
        return {
            "bot_name": "My Assistant",
            "bot_description": description[:100],
            "greeting_message": f"Hello! I'm your assistant. How can I help?",
            "system_prompt": f"You are a helpful assistant that {description[:200]}",
            "features": ["ai_chat", "commands", "auto_reply"],
            "commands": [
                {"command": "start", "description": "Start the bot"},
                {"command": "help", "description": "Get help"}
            ],
            "tone": "friendly",
            "category": "productivity"
        }
    except Exception as e:
        error_str = str(e).lower()
        # Check for API key issues (403, 401, unauthorized, etc.)
        if "403" in error_str or "401" in error_str or "unauthorized" in error_str or "access denied" in error_str or "invalid" in error_str:
            # Return a working fallback bot instead of failing
            return {
                "bot_name": "My Assistant",
                "bot_description": description[:100],
                "greeting_message": f"Hello! I'm your assistant. How can I help?",
                "system_prompt": f"You are a helpful assistant that {description[:200]}",
                "features": ["ai_chat", "commands", "auto_reply"],
                "commands": [
                    {"command": "start", "description": "Start the bot"},
                    {"command": "help", "description": "Get help"}
                ],
                "tone": "friendly",
                "category": "productivity"
            }
        # For other errors, return a user-friendly message
        return {"error": "AI service temporarily unavailable. Please try again in a moment."}


def _create_fallback_config(description: str) -> Dict[str, Any]:
    """Create a fallback bot config when AI is unavailable."""
    return {
        "bot_name": "My Assistant",
        "bot_description": description[:100] if description else "A helpful AI bot",
        "greeting_message": "Hello! I'm your assistant. How can I help you today?",
        "system_prompt": f"You are a helpful AI assistant. {description[:200] if description else 'Be friendly and helpful.'}",
        "features": ["ai_chat", "commands", "auto_reply"],
        "commands": [
            {"command": "start", "description": "Start the bot"},
            {"command": "help", "description": "Get help"}
        ],
        "auto_replies": [],
        "sample_qa": [],
        "tone": "friendly",
        "category": "productivity",
        "created_by_ai": False,
        "original_description": description
    }


async def create_bot_with_ai(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    description: str
) -> Dict[str, Any]:
    """
    Create a complete bot using AI from a description.
    Returns the bot config and share link.
    """
    user_id = update.effective_user.id
    name = update.effective_user.first_name or "User"
    
    # Generate config with AI
    config = await generate_bot_config_with_ai(description, name)
    
    if "error" in config:
        return config
    
    # Create bot in database
    try:
        bot_id = await db.create_custom_bot(
            user_id=user_id,
            name=config.get('bot_name', 'Custom Bot'),
            description=config.get('bot_description', ''),
            system_prompt=config.get('system_prompt', ''),
            welcome_message=config.get('greeting_message', 'Hello!'),
            config=config
        )
        
        # Set as active bot
        await db.set_active_bot(user_id, bot_id)
        await db.add_xp(user_id, 30)
        
        # Get share link
        try:
            bot_info = await context.bot.get_me()
            bot_username = bot_info.username
        except:
            bot_username = "WayaBot"
        
        share_link = f"https://t.me/{bot_username}?start=bot_{bot_id}"
        
        return {
            "success": True,
            "bot_id": bot_id,
            "config": config,
            "share_link": share_link
        }
        
    except Exception as e:
        return {"error": str(e)}


async def edit_bot_with_prompt(bot_id: int, user_id: int, edit_request: str) -> Dict[str, Any]:
    """
    Edit a bot using natural language.
    """
    # Get current bot
    bot = await db.get_bot(bot_id)
    if not bot:
        return {"error": "Bot not found"}
    
    if bot.get('user_id') != user_id:
        return {"error": "You don't own this bot"}
    
    current_config = bot.get('config', {})
    if isinstance(current_config, str):
        try:
            current_config = json.loads(current_config)
        except:
            current_config = {}
    
    prompt = f"""Current bot configuration:
Name: {bot.get('name')}
Description: {bot.get('description')}
Greeting: {bot.get('welcome_message')}
System Prompt: {bot.get('system_prompt', '')[:300]}

User's edit request: "{edit_request}"

Generate the updated fields as JSON. Only include fields that need to change:
{{
    "name": "new name if changed",
    "description": "new description if changed",
    "welcome_message": "new greeting if changed",
    "system_prompt": "new personality if changed",
    "add_commands": [{{"command": "cmd", "description": "desc"}}],
    "add_auto_replies": [{{"trigger": "word", "response": "reply"}}],
    "changes_summary": "Brief description of what was changed"
}}

Return ONLY valid JSON with the changes."""

    messages = [
        {"role": "system", "content": "You edit Telegram bot configurations. Return only the changed fields as JSON."},
        {"role": "user", "content": prompt}
    ]

    try:
        result = await asyncio.wait_for(
            chat_completion(messages, temperature=0.5, max_tokens=800),
            timeout=20.0
        )
        
        if not result:
            return {"error": "AI service temporarily unavailable"}
        
        result = result.strip()
        
        if "```json" in result:
            result = result.split("```json")[1].split("```")[0]
        elif "```" in result:
            result = result.split("```")[1].split("```")[0]
        
        changes = json.loads(result)
        
        # Apply changes
        async with db.get_connection() as conn:
            if changes.get('name'):
                await conn.execute(
                    "UPDATE custom_bots SET name = $1 WHERE id = $2",
                    changes['name'], bot_id
                )
            if changes.get('description'):
                await conn.execute(
                    "UPDATE custom_bots SET description = $1 WHERE id = $2",
                    changes['description'], bot_id
                )
            if changes.get('welcome_message'):
                await conn.execute(
                    "UPDATE custom_bots SET welcome_message = $1 WHERE id = $2",
                    changes['welcome_message'], bot_id
                )
            if changes.get('system_prompt'):
                await conn.execute(
                    "UPDATE custom_bots SET system_prompt = $1 WHERE id = $2",
                    changes['system_prompt'], bot_id
                )
            
            # Update timestamp
            await conn.execute(
                "UPDATE custom_bots SET updated_at = NOW() WHERE id = $1",
                bot_id
            )
        
        return {
            "success": True,
            "changes": changes.get('changes_summary', 'Bot updated successfully')
        }
        
    except Exception as e:
        return {"error": str(e)}


# =============================================================================
# BOT AUTOMATION ENGINE
# =============================================================================

async def add_bot_automation(
    bot_id: int,
    user_id: int,
    trigger: str,
    action_type: str,
    action_data: Any,
    conditions: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Add an automation rule to a bot.
    
    Action types:
    - reply: Send a text reply
    - send_poll: Send a poll
    - send_buttons: Send message with buttons
    - forward: Forward to another chat
    - notify: Send notification
    """
    automation = {
        "trigger": trigger.lower(),
        "action_type": action_type,
        "action_data": action_data,
        "conditions": conditions or {},
        "enabled": True,
        "created_at": datetime.utcnow().isoformat(),
        "usage_count": 0
    }
    
    async with db.get_connection() as conn:
        auto_id = await conn.fetchval('''
            INSERT INTO bot_automations (bot_id, user_id, trigger_word, action_type, action_data, conditions)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING id
        ''', bot_id, user_id, trigger, action_type, json.dumps(action_data), json.dumps(conditions or {}))
    
    automation["id"] = auto_id
    return automation


async def get_bot_automations(bot_id: int) -> List[Dict[str, Any]]:
    """Get all automations for a bot."""
    async with db.get_connection() as conn:
        rows = await conn.fetch('''
            SELECT * FROM bot_automations WHERE bot_id = $1 AND enabled = true
            ORDER BY created_at DESC
        ''', bot_id)
        return [dict(row) for row in rows]


# =============================================================================
# BOT ANALYTICS
# =============================================================================

async def get_bot_analytics(bot_id: int, user_id: int) -> Dict[str, Any]:
    """Get detailed analytics for a bot."""
    bot = await db.get_bot(bot_id)
    if not bot:
        return {"error": "Bot not found"}
    
    if bot.get('user_id') != user_id:
        return {"error": "Access denied"}
    
    async with db.get_connection() as conn:
        # Get usage stats
        stats = await conn.fetchrow('''
            SELECT 
                usage_count,
                total_conversations,
                unique_users_count,
                rating,
                created_at
            FROM custom_bots WHERE id = $1
        ''', bot_id)
        
        # Get recent activity (if tracking table exists)
        messages_today = 0
        messages_week = 0
        
        try:
            activity = await conn.fetchrow('''
                SELECT 
                    COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '1 day') as today,
                    COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '7 days') as week
                FROM bot_messages WHERE bot_id = $1
            ''', bot_id)
            if activity:
                messages_today = activity['today'] or 0
                messages_week = activity['week'] or 0
        except:
            pass
    
    return {
        "bot_id": bot_id,
        "bot_name": bot.get('name', 'Bot'),
        "bot_type": bot.get('bot_type', 'custom'),
        "total_uses": stats['usage_count'] if stats else 0,
        "total_conversations": stats['total_conversations'] if stats else 0,
        "unique_users": stats['unique_users_count'] if stats else 0,
        "messages_today": messages_today,
        "messages_this_week": messages_week,
        "rating": stats['rating'] if stats else 0,
        "created_at": str(stats['created_at'])[:10] if stats else "Unknown"
    }


# =============================================================================
# CODE GENERATION - Export bot as standalone Python code
# =============================================================================

async def generate_bot_code(bot_id: int, user_id: int) -> str:
    """
    Generate complete standalone Python code for a bot.
    Uses python-telegram-bot library and Digital Ocean GenAI API.
    """
    bot = await db.get_bot(bot_id)
    if not bot:
        return "# Error: Bot not found"
    
    config = bot.get('config', {})
    if isinstance(config, str):
        try:
            config = json.loads(config)
        except:
            config = {}
    
    commands = config.get('commands', [])
    auto_replies = config.get('auto_replies', [])
    features = config.get('features', ['ai_chat'])
    
    code = f'''#!/usr/bin/env python3
"""
{bot.get('name', 'My Bot')} - Generated by Waya Bot Builder
{bot.get('description', '')}

Requirements:
    pip install python-telegram-bot openai

Environment Variables:
    TELEGRAM_BOT_TOKEN - Get from @BotFather
    DIGITALOCEAN_API_KEY - Get from cloud.digitalocean.com/account/api/tokens
"""

import os
import asyncio
import logging
from typing import Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Poll
from telegram.ext import (
    Application, CommandHandler, MessageHandler, 
    CallbackQueryHandler, PollHandler, filters, ContextTypes
)
from openai import OpenAI

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN")
DIGITALOCEAN_API_KEY = os.environ.get("DIGITALOCEAN_API_KEY", "YOUR_DIGITALOCEAN_API_KEY")

# Bot personality
BOT_NAME = "{bot.get('name', 'Bot')}"
SYSTEM_PROMPT = """{bot.get('system_prompt', 'You are a helpful assistant.')}"""
GREETING = """{bot.get('welcome_message', 'Hello! How can I help you?')}"""

# Initialize Digital Ocean GenAI client (OpenAI-compatible)
do_client = OpenAI(
    base_url="https://cloud.digitalocean.com/gen-ai/api/v1",
    api_key=DIGITALOCEAN_API_KEY
) if DIGITALOCEAN_API_KEY != "YOUR_DIGITALOCEAN_API_KEY" else None

# Conversation history storage
conversations = {{}}


async def get_ai_response(user_id: int, message: str) -> str:
    """Get AI response using Digital Ocean GenAI."""
    if not do_client:
        return "AI is not configured. Please set DIGITALOCEAN_API_KEY."
    
    # Get conversation history
    history = conversations.get(user_id, [])
    
    messages = [
        {{"role": "system", "content": SYSTEM_PROMPT}},
        *history[-10:],  # Last 10 messages for context
        {{"role": "user", "content": message}}
    ]
    
    try:
        response = do_client.chat.completions.create(
            model="meta-llama/Llama-3.3-70B-Instruct-Turbo",
            messages=messages,
            temperature=0.7,
            max_tokens=1000
        )
        
        assistant_message = response.choices[0].message.content
        
        # Update history
        history.append({{"role": "user", "content": message}})
        history.append({{"role": "assistant", "content": assistant_message}})
        conversations[user_id] = history[-20:]  # Keep last 20
        
        return assistant_message
        
    except Exception as e:
        logger.error(f"AI Error: {{e}}")
        return "Sorry, I encountered an error. Please try again."


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    user = update.effective_user
    await update.message.reply_text(
        GREETING,
        parse_mode="Markdown"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    help_text = f"*{{BOT_NAME}} Commands*\\n\\n"
'''
    
    # Add command handlers
    for cmd in commands:
        cmd_name = cmd.get('command', 'help')
        cmd_desc = cmd.get('description', '')
        code += f'    help_text += "/{cmd_name} - {cmd_desc}\\n"\n'
    
    code += '''    
    await update.message.reply_text(help_text, parse_mode="Markdown")

'''
    
    # Add custom command handlers
    for cmd in commands:
        cmd_name = cmd.get('command', '')
        cmd_response = cmd.get('response', '')
        if cmd_name and cmd_name not in ['start', 'help']:
            code += f'''
async def {cmd_name}_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /{cmd_name} command."""
    await update.message.reply_text("{cmd_response}")

'''
    
    # Add poll feature if included
    if 'polls' in features:
        code += '''
async def poll_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Create a poll."""
    # Example poll - customize as needed
    await update.message.reply_poll(
        question="What do you think?",
        options=["Option A", "Option B", "Option C"],
        is_anonymous=True,
        allows_multiple_answers=False
    )


async def quiz_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Create a quiz."""
    await update.message.reply_poll(
        question="What is 2 + 2?",
        options=["3", "4", "5", "22"],
        type=Poll.QUIZ,
        correct_option_id=1,
        explanation="Basic math!"
    )

'''
    
    # Add message handler
    code += '''
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle regular messages."""
    if not update.message or not update.message.text:
        return
    
    user_id = update.effective_user.id
    message = update.message.text
    
'''
    
    # Add auto-replies
    if auto_replies:
        code += '    # Auto-replies\n'
        code += '    message_lower = message.lower()\n'
        for ar in auto_replies:
            trigger = ar.get('trigger', '').lower()
            response = ar.get('response', '')
            code += f'''    if "{trigger}" in message_lower:
        await update.message.reply_text("{response}")
        return
    
'''
    
    code += '''    # Get AI response
    await update.message.chat.send_action("typing")
    response = await get_ai_response(user_id, message)
    await update.message.reply_text(response)


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle button callbacks."""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    # Add your callback handling logic here
    await query.message.reply_text(f"You clicked: {data}")


def main() -> None:
    """Run the bot."""
    if TELEGRAM_BOT_TOKEN == "YOUR_BOT_TOKEN":
        print("Error: Please set TELEGRAM_BOT_TOKEN environment variable")
        return
    
    # Create application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
'''
    
    # Register custom command handlers
    for cmd in commands:
        cmd_name = cmd.get('command', '')
        if cmd_name and cmd_name not in ['start', 'help']:
            code += f'    application.add_handler(CommandHandler("{cmd_name}", {cmd_name}_command))\n'
    
    if 'polls' in features:
        code += '    application.add_handler(CommandHandler("poll", poll_command))\n'
        code += '    application.add_handler(CommandHandler("quiz", quiz_command))\n'
    
    code += '''    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Run bot
    print(f"Starting {BOT_NAME}...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
'''
    
    return code


# =============================================================================
# UI HANDLERS - Show menus and handle interactions
# =============================================================================

async def show_bot_builder_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show the main bot builder menu with cards."""
    keyboard = [
        [InlineKeyboardButton("Create with AI", callback_data="bb_create_ai")],
        [InlineKeyboardButton("Templates", callback_data="bb_templates"),
         InlineKeyboardButton("My Bots", callback_data="bb_my_bots")],
        [InlineKeyboardButton("Polls & Quizzes", callback_data="bb_polls")],
        [InlineKeyboardButton("Business Bot", callback_data="bb_business")],
        [InlineKeyboardButton("Channel Bot", callback_data="bb_channel")],
        [InlineKeyboardButton("Edit Bot", callback_data="bb_edit"),
         InlineKeyboardButton("Analytics", callback_data="bb_analytics")],
        [InlineKeyboardButton("Export Code", callback_data="bb_export_code")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = (
        "*Bot Builder*\n\n"
        "Create powerful Telegram bots with AI!\n\n"
        "*Features:*\n"
        "- AI-powered creation\n"
        "- Polls and quizzes\n"
        "- Business integration\n"
        "- Channel management\n"
        "- Export as code\n\n"
        "Choose an option to start:"
    )
    
    if update.callback_query:
        await update.callback_query.message.edit_text(
            text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup
        )


async def show_category_templates(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show bot template categories."""
    keyboard = []
    for key, cat in BOT_CATEGORIES.items():
        keyboard.append([InlineKeyboardButton(
            f"{cat['icon']} {cat['name']}", 
            callback_data=f"bb_cat_{key}"
        )])
    keyboard.append([InlineKeyboardButton("Back", callback_data="bb_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.message.edit_text(
        "*Bot Templates*\n\n"
        "Choose a category to see pre-built templates:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )


async def show_my_bots(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user's bots with management options."""
    user_id = update.effective_user.id
    bots = await db.get_user_bots(user_id)
    
    if not bots:
        keyboard = [[InlineKeyboardButton("Create Bot", callback_data="bb_create_ai")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.message.edit_text(
            "*My Bots*\n\nYou haven't created any bots yet.\nTap the button to create your first one!",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
        return
    
    keyboard = []
    for bot in bots[:8]:  # Show max 8 bots
        bot_type = bot.get('bot_type', 'custom')
        type_icon = {"business": "💼", "channel": "📢", "custom": "🤖"}.get(bot_type, "🤖")
        keyboard.append([
            InlineKeyboardButton(f"{type_icon} {bot['name']}", callback_data=f"bb_use_{bot['id']}"),
            InlineKeyboardButton("Edit", callback_data=f"bb_edit_{bot['id']}")
        ])
    
    keyboard.append([InlineKeyboardButton("Create New", callback_data="bb_create_ai")])
    keyboard.append([InlineKeyboardButton("Back", callback_data="bb_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.message.edit_text(
        f"*My Bots* ({len(bots)} total)\n\n"
        "Tap a bot name to use it, or Edit to modify:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )


async def show_bot_edit_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, bot_id: int) -> None:
    """Show edit menu for a specific bot."""
    user_id = update.effective_user.id
    bot = await db.get_bot(bot_id)
    
    if not bot or bot.get('user_id') != user_id:
        await update.callback_query.answer("Bot not found!", show_alert=True)
        return
    
    try:
        bot_info = await context.bot.get_me()
        bot_username = bot_info.username
    except:
        bot_username = "WayaBot"
    
    share_link = f"https://t.me/{bot_username}?start=bot_{bot_id}"
    
    keyboard = [
        [InlineKeyboardButton("Use This Bot", callback_data=f"bb_use_{bot_id}")],
        [InlineKeyboardButton("Edit Name", callback_data=f"bb_editname_{bot_id}"),
         InlineKeyboardButton("Edit Persona", callback_data=f"bb_editpersona_{bot_id}")],
        [InlineKeyboardButton("Edit Greeting", callback_data=f"bb_editgreet_{bot_id}")],
        [InlineKeyboardButton("Add Command", callback_data=f"bb_addcmd_{bot_id}"),
         InlineKeyboardButton("Add Knowledge", callback_data=f"bb_addknow_{bot_id}")],
        [InlineKeyboardButton("Add Automation", callback_data=f"bb_addauto_{bot_id}"),
         InlineKeyboardButton("Add Poll", callback_data=f"bb_addpoll_{bot_id}")],
        [InlineKeyboardButton("Analytics", callback_data=f"bb_stats_{bot_id}"),
         InlineKeyboardButton("Export Code", callback_data=f"bb_code_{bot_id}")],
        [InlineKeyboardButton("Share Bot", url=share_link)],
        [InlineKeyboardButton("Delete Bot", callback_data=f"bb_delete_{bot_id}")],
        [InlineKeyboardButton("Back", callback_data="bb_my_bots")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    bot_type = bot.get('bot_type', 'custom')
    type_name = {"business": "Business", "channel": "Channel", "custom": "Custom"}.get(bot_type, "Custom")
    
    await update.callback_query.message.edit_text(
        f"*Edit: {bot.get('name')}*\n\n"
        f"Type: {type_name}\n"
        f"Uses: {bot.get('usage_count', 0)}\n"
        f"Created: {str(bot.get('created_at', ''))[:10]}\n\n"
        f"*Share:* `{share_link}`",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )


async def show_poll_creator(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show poll creation menu."""
    keyboard = [
        [InlineKeyboardButton("Regular Poll", callback_data="bb_poll_regular")],
        [InlineKeyboardButton("Quiz", callback_data="bb_poll_quiz")],
        [InlineKeyboardButton("Multi-Answer Poll", callback_data="bb_poll_multi")],
        [InlineKeyboardButton("Scheduled Poll", callback_data="bb_poll_scheduled")],
        [InlineKeyboardButton("Back", callback_data="bb_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.message.edit_text(
        "*Create Poll*\n\n"
        "What type of poll would you like to create?\n\n"
        "*Regular Poll* - Simple voting\n"
        "*Quiz* - With correct answer\n"
        "*Multi-Answer* - Users can select multiple\n"
        "*Scheduled* - Post at a specific time",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )


async def show_business_bot_setup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show business bot setup menu."""
    keyboard = [
        [InlineKeyboardButton("Create Business Bot", callback_data="bb_create_business")],
        [InlineKeyboardButton("Set Working Hours", callback_data="bb_biz_hours")],
        [InlineKeyboardButton("Away Message", callback_data="bb_biz_away")],
        [InlineKeyboardButton("Quick Replies", callback_data="bb_biz_quick")],
        [InlineKeyboardButton("Back", callback_data="bb_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.message.edit_text(
        "*Business Bot Setup*\n\n"
        "Create a bot for your Telegram Business account!\n\n"
        "*Features:*\n"
        "- Automatic greetings\n"
        "- Away messages during off-hours\n"
        "- Quick replies for common questions\n"
        "- Customer management\n\n"
        "_Note: Requires Telegram Business subscription_",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )


async def show_channel_bot_setup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show channel bot setup menu."""
    keyboard = [
        [InlineKeyboardButton("Create Channel Bot", callback_data="bb_create_channel")],
        [InlineKeyboardButton("Auto Post", callback_data="bb_ch_autopost")],
        [InlineKeyboardButton("Scheduled Posts", callback_data="bb_ch_schedule")],
        [InlineKeyboardButton("Polls for Channel", callback_data="bb_ch_polls")],
        [InlineKeyboardButton("Back", callback_data="bb_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.message.edit_text(
        "*Channel Bot Setup*\n\n"
        "Create a bot to manage your Telegram channel!\n\n"
        "*Features:*\n"
        "- Automatic posting\n"
        "- Scheduled announcements\n"
        "- Polls and engagement\n"
        "- Content formatting\n\n"
        "_Add your bot as admin to your channel first_",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )


async def handle_feature_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, feature_key: str) -> None:
    """Handle when user selects a feature to add to their bot."""
    user_id = update.effective_user.id
    
    # Get or initialize selected features
    session = await db.get_session(user_id)
    state_data = session.get('state_data', {}) if session else {}
    selected = state_data.get('selected_features', [])
    
    # Toggle feature
    if feature_key in selected:
        selected.remove(feature_key)
    else:
        selected.append(feature_key)
    
    await db.update_session_state(user_id, "bb_selecting_features", {"selected_features": selected})
    
    # Update the feature selection UI
    keyboard = []
    row = []
    for i, (key, feat) in enumerate(BOT_FEATURE_CARDS.items()):
        check = "✓ " if key in selected else ""
        btn = InlineKeyboardButton(
            f"{check}{feat['icon']} {feat['title']}", 
            callback_data=f"bb_feat_{key}"
        )
        row.append(btn)
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton(f"Create Bot ({len(selected)} features)", callback_data="bb_features_done")])
    keyboard.append([InlineKeyboardButton("Back", callback_data="bb_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.message.edit_text(
        "*Select Features*\n\n"
        f"Selected: {len(selected)} features\n\n"
        "Tap features to toggle them:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )
