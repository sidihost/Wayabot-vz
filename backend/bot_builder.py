"""
Waya Bot Builder - Advanced Bot Creation Engine
Build powerful AI bots with cards, automation, code generation and more!
"""

import json
import asyncio
from typing import Optional, Dict, Any, List
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode, ChatAction

from ai_engine import generate_response, get_groq_client, BEST_MODEL
import database as db


# =============================================================================
# BOT FEATURE CARDS - Beautiful UI for selecting features
# =============================================================================

BOT_FEATURE_CARDS = {
    "ai_chat": {
        "title": "AI Chat",
        "icon": "brain",
        "description": "Smart conversations with context memory",
        "code_snippet": "Responds intelligently to any message"
    },
    "commands": {
        "title": "Custom Commands", 
        "icon": "terminal",
        "description": "Add /commands your bot responds to",
        "code_snippet": "/help, /start, /info, etc."
    },
    "auto_reply": {
        "title": "Auto Replies",
        "icon": "reply",
        "description": "Trigger responses on keywords",
        "code_snippet": "When user says 'price' -> show pricing"
    },
    "scheduler": {
        "title": "Scheduled Messages",
        "icon": "clock",
        "description": "Send messages at specific times",
        "code_snippet": "Daily tips at 9 AM"
    },
    "knowledge_base": {
        "title": "Knowledge Base",
        "icon": "book",
        "description": "Train bot with custom Q&A",
        "code_snippet": "FAQ, product info, policies"
    },
    "buttons": {
        "title": "Interactive Buttons",
        "icon": "grid",
        "description": "Clickable menus and actions",
        "code_snippet": "Main Menu -> Products -> Buy"
    },
    "forms": {
        "title": "Data Collection",
        "icon": "form",
        "description": "Collect user information",
        "code_snippet": "Name, email, feedback forms"
    },
    "broadcast": {
        "title": "Broadcast Messages",
        "icon": "megaphone",
        "description": "Send to all users at once",
        "code_snippet": "Announcements, updates, promos"
    },
    "analytics": {
        "title": "Analytics",
        "icon": "chart",
        "description": "Track bot usage and stats",
        "code_snippet": "Users, messages, popular commands"
    },
    "voice": {
        "title": "Voice Support",
        "icon": "mic",
        "description": "Voice messages and TTS",
        "code_snippet": "Listen and speak to users"
    },
    "multilingual": {
        "title": "Multi-Language",
        "icon": "globe",
        "description": "Support multiple languages",
        "code_snippet": "Auto-detect and respond"
    },
    "webhook": {
        "title": "Webhooks",
        "icon": "link",
        "description": "Connect to external services",
        "code_snippet": "API integrations"
    }
}

BOT_CATEGORIES = {
    "business": {
        "name": "Business",
        "icon": "briefcase",
        "templates": ["customer_support", "sales_bot", "appointment_booking", "faq_bot"]
    },
    "education": {
        "name": "Education", 
        "icon": "graduation-cap",
        "templates": ["tutor_bot", "quiz_bot", "language_learning", "course_assistant"]
    },
    "lifestyle": {
        "name": "Lifestyle",
        "icon": "heart",
        "templates": ["fitness_coach", "recipe_bot", "meditation_guide", "daily_motivation"]
    },
    "entertainment": {
        "name": "Entertainment",
        "icon": "gamepad",
        "templates": ["trivia_bot", "story_teller", "joke_bot", "meme_generator"]
    },
    "productivity": {
        "name": "Productivity",
        "icon": "check-circle",
        "templates": ["task_manager", "note_taker", "reminder_bot", "meeting_scheduler"]
    },
    "community": {
        "name": "Community",
        "icon": "users",
        "templates": ["welcome_bot", "moderation_bot", "poll_bot", "event_manager"]
    }
}


# =============================================================================
# INTERACTIVE BOT BUILDER WITH CARDS
# =============================================================================

async def show_bot_builder_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the main bot builder menu with beautiful cards."""
    user_id = update.effective_user.id
    
    keyboard = [
        [InlineKeyboardButton("Create with AI", callback_data="bb_create_ai"),
         InlineKeyboardButton("Use Template", callback_data="bb_templates")],
        [InlineKeyboardButton("My Bots", callback_data="bb_my_bots"),
         InlineKeyboardButton("Edit Bot", callback_data="bb_edit")],
        [InlineKeyboardButton("Bot Analytics", callback_data="bb_analytics"),
         InlineKeyboardButton("Bot Code", callback_data="bb_export_code")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = (
        "*Bot Builder*\n\n"
        "Create powerful AI bots in seconds!\n\n"
        "*Create with AI* - Describe what you want\n"
        "*Use Template* - Start from pre-built bots\n"
        "*My Bots* - Manage your creations\n"
        "*Edit Bot* - Modify existing bots\n"
        "*Bot Analytics* - See usage stats\n"
        "*Bot Code* - Export Python code\n\n"
        "What would you like to do?"
    )
    
    if update.callback_query:
        await update.callback_query.message.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
    else:
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)


async def show_feature_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, bot_name: str = None):
    """Show feature cards for user to select what they want in their bot."""
    query = update.callback_query
    user_id = update.effective_user.id
    
    # Store bot creation state
    await db.update_session_state(user_id, "bb_selecting_features", {
        "bot_name": bot_name,
        "selected_features": []
    })
    
    # Create feature buttons (2 per row)
    features = list(BOT_FEATURE_CARDS.items())
    keyboard = []
    
    for i in range(0, len(features), 2):
        row = []
        for j in range(2):
            if i + j < len(features):
                key, feat = features[i + j]
                row.append(InlineKeyboardButton(
                    f"{feat['title']}", 
                    callback_data=f"bb_feat_{key}"
                ))
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton("Continue", callback_data="bb_features_done")])
    keyboard.append([InlineKeyboardButton("Back", callback_data="bb_menu")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = (
        "*Select Features*\n\n"
        "Tap to add features to your bot:\n\n"
        "Selected: _None yet_\n\n"
        "Tap features then press Continue"
    )
    
    await query.message.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)


async def handle_feature_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, feature_key: str):
    """Handle when user selects/deselects a feature."""
    query = update.callback_query
    user_id = update.effective_user.id
    
    session = await db.get_session(user_id)
    state_data = session.get('state_data', {}) if session else {}
    selected = state_data.get('selected_features', [])
    
    # Toggle feature
    if feature_key in selected:
        selected.remove(feature_key)
    else:
        selected.append(feature_key)
    
    state_data['selected_features'] = selected
    await db.update_session_state(user_id, "bb_selecting_features", state_data)
    
    # Rebuild keyboard with checkmarks
    features = list(BOT_FEATURE_CARDS.items())
    keyboard = []
    
    for i in range(0, len(features), 2):
        row = []
        for j in range(2):
            if i + j < len(features):
                key, feat = features[i + j]
                check = "[x] " if key in selected else ""
                row.append(InlineKeyboardButton(
                    f"{check}{feat['title']}", 
                    callback_data=f"bb_feat_{key}"
                ))
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton("Continue", callback_data="bb_features_done")])
    keyboard.append([InlineKeyboardButton("Back", callback_data="bb_menu")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Show selected features
    selected_names = [BOT_FEATURE_CARDS[f]['title'] for f in selected]
    selected_text = ", ".join(selected_names) if selected_names else "_None yet_"
    
    text = (
        "*Select Features*\n\n"
        "Tap to add features to your bot:\n\n"
        f"Selected: {selected_text}\n\n"
        "Tap features then press Continue"
    )
    
    await query.message.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)


async def show_category_templates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show bot category selection with templates."""
    query = update.callback_query
    
    keyboard = []
    categories = list(BOT_CATEGORIES.items())
    
    for i in range(0, len(categories), 2):
        row = []
        for j in range(2):
            if i + j < len(categories):
                key, cat = categories[i + j]
                row.append(InlineKeyboardButton(
                    cat['name'], 
                    callback_data=f"bb_cat_{key}"
                ))
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton("Back", callback_data="bb_menu")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = (
        "*Choose a Category*\n\n"
        "Select the type of bot you want to create:\n\n"
        "*Business* - Support, sales, appointments\n"
        "*Education* - Learning, quizzes, courses\n"
        "*Lifestyle* - Fitness, recipes, wellness\n"
        "*Entertainment* - Games, jokes, stories\n"
        "*Productivity* - Tasks, notes, reminders\n"
        "*Community* - Moderation, events, polls"
    )
    
    await query.message.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)


# =============================================================================
# BOT MANAGEMENT - VIEW, EDIT, DELETE
# =============================================================================

async def show_my_bots(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's bots with management options."""
    query = update.callback_query
    user_id = update.effective_user.id
    
    bots = await db.get_user_bots(user_id)
    
    if not bots:
        keyboard = [
            [InlineKeyboardButton("Create Bot", callback_data="bb_create_ai")],
            [InlineKeyboardButton("Back", callback_data="bb_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.edit_text(
            "*My Bots*\n\n"
            "You haven't created any bots yet.\n\n"
            "Create your first AI bot now!",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
        return
    
    # Build bot list
    text = "*My Bots*\n\n"
    keyboard = []
    
    for bot in bots[:10]:  # Limit to 10 bots
        status = "[Active]" if bot.get('is_active') else ""
        text += f"*{bot['name']}* {status}\n"
        text += f"  Type: {bot.get('bot_type', 'general')}\n"
        text += f"  Uses: {bot.get('usage_count', 0)}\n\n"
        
        keyboard.append([
            InlineKeyboardButton(f"Use {bot['name']}", callback_data=f"bb_use_{bot['id']}"),
            InlineKeyboardButton("Edit", callback_data=f"bb_edit_{bot['id']}")
        ])
    
    keyboard.append([InlineKeyboardButton("Create New Bot", callback_data="bb_create_ai")])
    keyboard.append([InlineKeyboardButton("Back", callback_data="bb_menu")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)


async def show_bot_edit_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, bot_id: int):
    """Show edit options for a specific bot."""
    query = update.callback_query
    user_id = update.effective_user.id
    
    bot = await db.get_bot(bot_id)
    
    if not bot or bot.get('user_id') != user_id:
        await query.answer("Bot not found", show_alert=True)
        return
    
    keyboard = [
        [InlineKeyboardButton("Edit Name", callback_data=f"bb_editname_{bot_id}"),
         InlineKeyboardButton("Edit Personality", callback_data=f"bb_editpersona_{bot_id}")],
        [InlineKeyboardButton("Edit Greeting", callback_data=f"bb_editgreet_{bot_id}"),
         InlineKeyboardButton("Add Commands", callback_data=f"bb_addcmd_{bot_id}")],
        [InlineKeyboardButton("Add Knowledge", callback_data=f"bb_addknow_{bot_id}"),
         InlineKeyboardButton("Add Automation", callback_data=f"bb_addauto_{bot_id}")],
        [InlineKeyboardButton("View Analytics", callback_data=f"bb_stats_{bot_id}"),
         InlineKeyboardButton("Export Code", callback_data=f"bb_code_{bot_id}")],
        [InlineKeyboardButton("Delete Bot", callback_data=f"bb_delete_{bot_id}")],
        [InlineKeyboardButton("Back", callback_data="bb_my_bots")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = (
        f"*Edit: {bot['name']}*\n\n"
        f"Type: {bot.get('bot_type', 'general')}\n"
        f"Created: {bot.get('created_at', 'Unknown')[:10]}\n"
        f"Total uses: {bot.get('usage_count', 0)}\n\n"
        "What would you like to edit?"
    )
    
    await query.message.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)


# =============================================================================
# AI-POWERED BOT CREATION
# =============================================================================

async def create_bot_with_ai(update: Update, context: ContextTypes.DEFAULT_TYPE, user_request: str):
    """Create a bot using AI based on user's description."""
    user_id = update.effective_user.id
    
    # Get bot username for links
    try:
        bot_info = await context.bot.get_me()
        bot_username = bot_info.username
    except:
        bot_username = "WayaBotBuilder_bot"
    
    # Generate bot config using AI
    client = get_groq_client()
    
    prompt = f"""Create a Telegram bot configuration based on this request: "{user_request}"

Return a JSON object with:
{{
    "bot_name": "Creative name for the bot",
    "bot_type": "general|support|education|fitness|creative|assistant|quiz|wellness|cooking",
    "bot_description": "What the bot does (1-2 sentences)",
    "greeting_message": "Friendly first message to users",
    "system_prompt": "Detailed instructions for how the bot should behave, its personality, knowledge areas, and response style",
    "personality": {{
        "tone": "friendly|professional|casual|enthusiastic",
        "traits": ["helpful", "knowledgeable", "patient"]
    }},
    "features": ["Feature 1", "Feature 2", "Feature 3"],
    "commands": [
        {{"command": "start", "description": "Start the bot"}},
        {{"command": "help", "description": "Show help"}}
    ],
    "sample_responses": {{
        "greeting": "Sample greeting response",
        "help": "Sample help response",
        "fallback": "What to say when confused"
    }},
    "knowledge_base": [
        {{"question": "Sample question?", "answer": "Sample answer"}}
    ],
    "automations": [
        {{"trigger": "keyword or pattern", "action": "What bot does"}}
    ]
}}

Make it creative and professional. The system_prompt should be detailed (at least 100 words)."""

    try:
        response = await client.chat.completions.create(
            model=BEST_MODEL,
            messages=[
                {"role": "system", "content": "You are an expert bot designer. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
            max_tokens=2000
        )
        
        content = response.choices[0].message.content
        
        # Extract JSON from response
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        
        config = json.loads(content.strip())
        
    except Exception as e:
        print(f"Bot creation AI error: {e}")
        # Fallback config
        config = {
            "bot_name": user_request.split()[-1].title() + " Bot",
            "bot_type": "general",
            "bot_description": f"A bot that helps with {user_request}",
            "greeting_message": f"Hello! I'm here to help with {user_request}. How can I assist you?",
            "system_prompt": f"You are a helpful assistant specializing in {user_request}. Be friendly, knowledgeable, and helpful.",
            "personality": {"tone": "friendly", "traits": ["helpful"]},
            "features": ["AI Chat", "Smart Responses", "24/7 Available"],
            "commands": [{"command": "start", "description": "Start"}, {"command": "help", "description": "Help"}]
        }
    
    # Create bot in database
    bot_id = await db.create_custom_bot(
        user_id=user_id,
        name=config.get('bot_name', 'My Bot'),
        bot_type=config.get('bot_type', 'general'),
        system_prompt=config.get('system_prompt', ''),
        description=config.get('bot_description'),
        welcome_message=config.get('greeting_message'),
        personality=config.get('personality'),
        commands=config.get('commands'),
        settings={
            "features": config.get('features', []),
            "sample_responses": config.get('sample_responses', {}),
            "automations": config.get('automations', [])
        }
    )
    
    # Add knowledge base entries
    knowledge = config.get('knowledge_base', [])
    for item in knowledge[:10]:  # Limit to 10
        await db.add_bot_knowledge(
            bot_id=bot_id,
            question=item.get('question', ''),
            answer=item.get('answer', '')
        )
    
    # Activate the bot
    await db.set_active_bot(user_id, bot_id)
    await db.add_xp(user_id, 50)  # Bonus XP for creating a bot
    
    # Create shareable link
    share_link = f"https://t.me/{bot_username}?start=bot_{bot_id}"
    
    return {
        "bot_id": bot_id,
        "config": config,
        "share_link": share_link
    }


# =============================================================================
# CODE GENERATION - Export bot as Python code
# =============================================================================

async def generate_bot_code(bot_id: int, user_id: int) -> str:
    """Generate Python code for a bot that user can run standalone."""
    
    bot = await db.get_bot(bot_id)
    if not bot or bot.get('user_id') != user_id:
        return "# Bot not found or access denied"
    
    bot_name = bot.get('name', 'MyBot')
    system_prompt = bot.get('system_prompt', 'You are a helpful assistant.')
    welcome_msg = bot.get('welcome_message', 'Hello!')
    commands = bot.get('commands', [])
    
    # Generate the Python code
    code = f'''"""
{bot_name} - Generated by Waya Bot Builder
A Telegram bot powered by Groq AI

To run this bot:
1. Install dependencies: pip install python-telegram-bot groq
2. Set your API keys as environment variables:
   - TELEGRAM_BOT_TOKEN: Get from @BotFather
   - GROQ_API_KEY: Get from console.groq.com
3. Run: python {bot_name.lower().replace(" ", "_")}_bot.py
"""

import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from groq import AsyncGroq

# Configuration
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
BOT_NAME = "{bot_name}"

# AI Configuration
SYSTEM_PROMPT = """{system_prompt}"""

WELCOME_MESSAGE = """{welcome_msg}"""

# Initialize Groq client
groq_client = None

def get_groq_client():
    global groq_client
    if groq_client is None:
        groq_client = AsyncGroq(api_key=GROQ_API_KEY)
    return groq_client

# Conversation history storage (in-memory, replace with database for production)
conversations = {{}}

async def generate_response(user_id: int, message: str) -> str:
    """Generate AI response using Groq."""
    client = get_groq_client()
    
    # Get conversation history
    history = conversations.get(user_id, [])
    
    messages = [
        {{"role": "system", "content": SYSTEM_PROMPT}},
        *history[-10:],  # Last 10 messages for context
        {{"role": "user", "content": message}}
    ]
    
    try:
        response = await client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.7,
            max_tokens=1024
        )
        
        ai_response = response.choices[0].message.content
        
        # Store in history
        history.append({{"role": "user", "content": message}})
        history.append({{"role": "assistant", "content": ai_response}})
        conversations[user_id] = history[-20:]  # Keep last 20 messages
        
        return ai_response
    except Exception as e:
        print(f"AI Error: {{e}}")
        return "I'm having trouble responding right now. Please try again."

async def start_command(update: Update, context):
    """Handle /start command."""
    keyboard = [
        [InlineKeyboardButton("Help", callback_data="help")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        WELCOME_MESSAGE,
        reply_markup=reply_markup
    )

async def help_command(update: Update, context):
    """Handle /help command."""
    help_text = f"""*{{BOT_NAME}} Help*

Available commands:
/start - Start the bot
/help - Show this help message
/clear - Clear conversation history

Just send me a message and I'll respond!
"""
    await update.message.reply_text(help_text, parse_mode="Markdown")

async def clear_command(update: Update, context):
    """Clear conversation history."""
    user_id = update.effective_user.id
    conversations[user_id] = []
    await update.message.reply_text("Conversation cleared! Let's start fresh.")

async def handle_message(update: Update, context):
    """Handle regular messages."""
    user_id = update.effective_user.id
    message = update.message.text
    
    # Show typing indicator
    await update.message.chat.send_action("typing")
    
    # Generate AI response
    response = await generate_response(user_id, message)
    
    await update.message.reply_text(response)

async def handle_callback(update: Update, context):
    """Handle button callbacks."""
    query = update.callback_query
    await query.answer()
    
    if query.data == "help":
        await help_command(update, context)

def main():
    """Start the bot."""
    if not BOT_TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN not set")
        return
    if not GROQ_API_KEY:
        print("Error: GROQ_API_KEY not set")
        return
    
    # Create application
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("clear", clear_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(handle_callback))
    
    print(f"{{BOT_NAME}} is starting...")
    app.run_polling()

if __name__ == "__main__":
    main()
'''
    
    return code


# =============================================================================
# BOT ANALYTICS
# =============================================================================

async def get_bot_analytics(bot_id: int, user_id: int) -> Dict[str, Any]:
    """Get analytics for a specific bot."""
    
    bot = await db.get_bot(bot_id)
    if not bot or bot.get('user_id') != user_id:
        return {"error": "Bot not found"}
    
    # Get usage stats from database
    async with db.get_connection() as conn:
        # Total conversations
        total_convos = await conn.fetchval(
            "SELECT COUNT(*) FROM conversations WHERE bot_id = $1",
            bot_id
        ) or 0
        
        # Unique users (from conversations)
        unique_users = await conn.fetchval(
            "SELECT COUNT(DISTINCT user_id) FROM conversations WHERE bot_id = $1",
            bot_id
        ) or 0
        
        # Messages today
        today_messages = await conn.fetchval(
            """SELECT COUNT(*) FROM conversations 
               WHERE bot_id = $1 AND created_at > CURRENT_DATE""",
            bot_id
        ) or 0
        
        # Messages this week
        week_messages = await conn.fetchval(
            """SELECT COUNT(*) FROM conversations 
               WHERE bot_id = $1 AND created_at > CURRENT_DATE - INTERVAL '7 days'""",
            bot_id
        ) or 0
    
    return {
        "bot_name": bot.get('name'),
        "bot_type": bot.get('bot_type'),
        "created_at": str(bot.get('created_at', ''))[:10],
        "total_uses": bot.get('usage_count', 0),
        "total_conversations": total_convos,
        "unique_users": unique_users,
        "messages_today": today_messages,
        "messages_this_week": week_messages,
        "rating": bot.get('rating', 0),
        "is_active": bot.get('is_active', False)
    }


# =============================================================================
# AUTOMATION ENGINE
# =============================================================================

async def add_bot_automation(bot_id: int, user_id: int, trigger: str, action: str, response: str):
    """Add an automation rule to a bot."""
    
    bot = await db.get_bot(bot_id)
    if not bot or bot.get('user_id') != user_id:
        return {"error": "Bot not found"}
    
    # Get current automations
    settings = bot.get('settings', {})
    automations = settings.get('automations', [])
    
    # Add new automation
    automations.append({
        "trigger": trigger,
        "action": action,
        "response": response,
        "enabled": True
    })
    
    settings['automations'] = automations
    
    # Update bot settings
    async with db.get_connection() as conn:
        await conn.execute(
            "UPDATE custom_bots SET settings = $1, updated_at = NOW() WHERE id = $2",
            json.dumps(settings), bot_id
        )
    
    return {"success": True, "automation_count": len(automations)}


async def check_automations(bot_id: int, message: str) -> Optional[str]:
    """Check if any automation triggers match the message."""
    
    bot = await db.get_bot(bot_id)
    if not bot:
        return None
    
    settings = bot.get('settings', {})
    automations = settings.get('automations', [])
    
    message_lower = message.lower()
    
    for auto in automations:
        if not auto.get('enabled', True):
            continue
        
        trigger = auto.get('trigger', '').lower()
        
        # Check if trigger matches
        if trigger in message_lower:
            return auto.get('response')
    
    return None


# =============================================================================
# PROMPT-BASED BOT EDITING
# =============================================================================

async def edit_bot_with_prompt(bot_id: int, user_id: int, edit_request: str) -> Dict[str, Any]:
    """Edit a bot using natural language."""
    
    bot = await db.get_bot(bot_id)
    if not bot or bot.get('user_id') != user_id:
        return {"error": "Bot not found"}
    
    client = get_groq_client()
    
    current_config = {
        "name": bot.get('name'),
        "description": bot.get('description'),
        "system_prompt": bot.get('system_prompt'),
        "welcome_message": bot.get('welcome_message'),
        "personality": bot.get('personality'),
        "commands": bot.get('commands')
    }
    
    prompt = f"""You are editing a Telegram bot. Current configuration:
{json.dumps(current_config, indent=2)}

User wants to make this change: "{edit_request}"

Return a JSON object with ONLY the fields that need to be updated:
{{
    "name": "Only if changing name",
    "description": "Only if changing description",
    "system_prompt": "Only if changing behavior/personality",
    "welcome_message": "Only if changing greeting",
    "add_command": {{"command": "cmd", "description": "desc"}},
    "add_automation": {{"trigger": "word", "response": "reply"}},
    "changes_summary": "Brief description of what was changed"
}}

Only include fields that are being changed."""

    try:
        response = await client.chat.completions.create(
            model=BEST_MODEL,
            messages=[
                {"role": "system", "content": "You are a bot editor. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1000
        )
        
        content = response.choices[0].message.content
        
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        
        changes = json.loads(content.strip())
        
    except Exception as e:
        print(f"Edit bot AI error: {e}")
        return {"error": "Failed to process edit request"}
    
    # Apply changes to database
    async with db.get_connection() as conn:
        updates = []
        params = []
        param_idx = 1
        
        if "name" in changes:
            updates.append(f"name = ${param_idx}")
            params.append(changes["name"])
            param_idx += 1
        
        if "description" in changes:
            updates.append(f"description = ${param_idx}")
            params.append(changes["description"])
            param_idx += 1
        
        if "system_prompt" in changes:
            updates.append(f"system_prompt = ${param_idx}")
            params.append(changes["system_prompt"])
            param_idx += 1
        
        if "welcome_message" in changes:
            updates.append(f"welcome_message = ${param_idx}")
            params.append(changes["welcome_message"])
            param_idx += 1
        
        if updates:
            updates.append("updated_at = NOW()")
            params.append(bot_id)
            
            await conn.execute(
                f"UPDATE custom_bots SET {', '.join(updates)} WHERE id = ${param_idx}",
                *params
            )
    
    # Handle automation additions
    if "add_automation" in changes:
        auto = changes["add_automation"]
        await add_bot_automation(
            bot_id, user_id,
            auto.get("trigger", ""),
            "reply",
            auto.get("response", "")
        )
    
    return {
        "success": True,
        "changes": changes.get("changes_summary", "Bot updated successfully")
    }
