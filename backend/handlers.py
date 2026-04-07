"""
Waya Bot Builder - Command Handlers Module
Premium AI assistant with advanced Telegram features!
"""

import json
import io
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes
from telegram.constants import ParseMode, ChatAction, MessageEntityType


# =====================================================
# PREMIUM TELEGRAM FEATURES
# =====================================================

async def send_loading_message(update: Update, text: str = "Thinking..."):
    """Send a loading message with typing animation."""
    msg = await update.message.reply_text(f"⏳ {text}")
    return msg

async def update_loading_message(msg, text: str):
    """Update loading message."""
    try:
        await msg.edit_text(text)
    except:
        pass

async def send_spoiler_message(update: Update, text: str, spoiler_text: str):
    """Send a message with hidden spoiler."""
    # Telegram spoiler - use ||text|| syntax
    await update.message.reply_text(
        f"{text}\n\n||{spoiler_text}||",
        parse_mode=ParseMode.MARKDOWN
    )

async def send_fading_message(update: Update, text: str, fade_after: int = 60):
    """Send a message that will be deleted after X seconds."""
    msg = await update.message.reply_text(text)
    # Schedule deletion
    asyncio.create_task(_delete_after_delay(msg, fade_after))
    return msg

async def _delete_after_delay(msg, delay: int):
    """Delete message after delay."""
    await asyncio.sleep(delay)
    try:
        await msg.delete()
    except:
        pass

async def send_typing_sequence(update: Update, steps: list):
    """Show typing sequence for multiple steps."""
    for step in steps:
        await update.message.chat.send_action(ChatAction.TYPING)
        await asyncio.sleep(0.5)
        await update.message.reply_text(step)

async def send_buttons_message(update: Update, text: str, buttons: list):
    """Send message with inline buttons."""
    keyboard = []
    for row in buttons:
        keyboard_row = [InlineKeyboardButton(btn["text"], callback_data=btn.get("callback", "")) for btn in row]
        keyboard.append(keyboard_row)
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(text, reply_markup=reply_markup)


# Telegram message limit is 4096 characters
TELEGRAM_MAX_MESSAGE_LENGTH = 4096

async def safe_reply_text(message, text: str, parse_mode=None, reply_markup=None, **kwargs):
    """
    Safely send a message, splitting it if it exceeds Telegram's 4096 character limit.
    Returns the last message sent.
    """
    if not message:
        return None
    
    if not text:
        text = "..."
    
    # If message is within limit, send normally
    if len(text) <= TELEGRAM_MAX_MESSAGE_LENGTH:
        try:
            return await message.reply_text(text, parse_mode=parse_mode, reply_markup=reply_markup, **kwargs)
        except Exception as e:
            # If markdown fails, try without parse_mode
            if parse_mode and "parse" in str(e).lower():
                return await message.reply_text(text, reply_markup=reply_markup, **kwargs)
            raise
    
    # Split long messages
    chunks = []
    current_chunk = ""
    
    # Try to split on paragraph boundaries first, then sentences, then words
    paragraphs = text.split('\n\n')
    
    for para in paragraphs:
        if len(current_chunk) + len(para) + 2 <= TELEGRAM_MAX_MESSAGE_LENGTH:
            current_chunk += para + "\n\n"
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            
            # If single paragraph is too long, split by sentences
            if len(para) > TELEGRAM_MAX_MESSAGE_LENGTH:
                sentences = para.replace('. ', '.|').split('|')
                current_chunk = ""
                for sentence in sentences:
                    if len(current_chunk) + len(sentence) + 1 <= TELEGRAM_MAX_MESSAGE_LENGTH:
                        current_chunk += sentence + " "
                    else:
                        if current_chunk:
                            chunks.append(current_chunk.strip())
                        # If single sentence is still too long, just truncate
                        if len(sentence) > TELEGRAM_MAX_MESSAGE_LENGTH:
                            chunks.append(sentence[:TELEGRAM_MAX_MESSAGE_LENGTH - 3] + "...")
                            current_chunk = ""
                        else:
                            current_chunk = sentence + " "
            else:
                current_chunk = para + "\n\n"
    
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    
    # Send all chunks
    last_msg = None
    for i, chunk in enumerate(chunks):
        try:
            # Only add reply_markup to the last message
            markup = reply_markup if i == len(chunks) - 1 else None
            last_msg = await message.reply_text(chunk, parse_mode=parse_mode, reply_markup=markup, **kwargs)
        except Exception as e:
            # Try without parse_mode if it fails
            if parse_mode and "parse" in str(e).lower():
                markup = reply_markup if i == len(chunks) - 1 else None
                last_msg = await message.reply_text(chunk, reply_markup=markup, **kwargs)
            else:
                raise
    
    return last_msg


import database as db
from ai_engine import (
    generate_response, generate_bot_suggestion, analyze_message_intent,
    parse_reminder_request, parse_task_request, summarize_text, translate_text,
    generate_quiz_question, get_smart_suggestions, get_bot_system_prompt, WAYA_SYSTEM_PROMPT,
    transcribe_voice,  # 🎙 Groq Whisper
    compound_response,  # 🤖 COMPOUND - Agentic AI with tools!
    generate_response_streaming  # Streaming responses for chat effect
)
from voice_engine import voice_engine, voice_preferences, VoiceEngine
from emotion_engine import emotion_engine, EmotionEngine


# Minimum interval between message edits to avoid Telegram rate limits
STREAM_UPDATE_INTERVAL = 0.8  # seconds

async def stream_response_to_message(
    message,
    response_generator,
    initial_text: str = "...",
    typing_indicator: str = " ▌"
):
    """
    Stream AI response with a typing effect by editing the message.
    Updates the message as chunks arrive, creating a 'live typing' effect.
    """
    import time
    
    # Send initial message
    try:
        sent_msg = await message.reply_text(initial_text + typing_indicator)
    except Exception as e:
        # Fallback if we can't send
        return None, str(e)
    
    full_response = ""
    last_update_time = time.time()
    last_text_length = 0
    
    try:
        async for chunk in response_generator:
            full_response += chunk
            current_time = time.time()
            
            # Only update if enough time has passed and text has grown significantly
            # This avoids Telegram rate limits (max ~20 edits per minute)
            if (current_time - last_update_time >= STREAM_UPDATE_INTERVAL and 
                len(full_response) - last_text_length >= 20):
                try:
                    # Truncate if too long for a single message
                    display_text = full_response[:4000] if len(full_response) > 4000 else full_response
                    await sent_msg.edit_text(display_text + typing_indicator)
                    last_update_time = current_time
                    last_text_length = len(full_response)
                except Exception:
                    # Ignore edit errors (rate limit, message unchanged, etc.)
                    pass
        
        # Final update without typing indicator
        if full_response:
            try:
                # Handle long messages
                if len(full_response) > TELEGRAM_MAX_MESSAGE_LENGTH:
                    # Delete the streaming message and use safe_reply_text for long content
                    await sent_msg.delete()
                    await safe_reply_text(message, full_response, parse_mode=ParseMode.MARKDOWN)
                else:
                    await sent_msg.edit_text(full_response, parse_mode=ParseMode.MARKDOWN)
            except Exception:
                # If markdown fails, try without
                try:
                    await sent_msg.edit_text(full_response)
                except:
                    pass
        
        return sent_msg, full_response
        
    except Exception as e:
        # If streaming fails, return what we have
        if full_response:
            try:
                await sent_msg.edit_text(full_response)
            except:
                pass
        return sent_msg, full_response or str(e)


def get_user_display_name(update: Update) -> str:
    """Get a display name for the user."""
    user = update.effective_user
    if user.first_name and user.last_name:
        return f"{user.first_name} {user.last_name}"
    elif user.first_name:
        return user.first_name
    elif user.username:
        return f"@{user.username}"
    return "there"


async def ensure_user(update: Update) -> dict:
    """Ensure user exists in database and return user data."""
    user = update.effective_user
    user_data = await db.get_or_create_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        language_code=user.language_code or 'en',
        is_premium=user.is_premium or False
    )
    
    # Update streak
    await db.update_streak(user.id)
    
    return user_data


async def track_command(user_id: int, command: str):
    """Track command usage."""
    await db.increment_stat(user_id, "total_messages")
    await db.log_event(user_id, f"command_{command}", category="command")
    await db.add_xp(user_id, 2)  # 2 XP per command


# =====================================================
# MAIN COMMANDS
# =====================================================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /start command."""
    user_data = await ensure_user(update)
    await track_command(update.effective_user.id, "start")
    
    name = get_user_display_name(update)
    is_new = user_data.get("is_new", False)
    
    if is_new:
        welcome_message = f"""
🎉 *Welcome to Waya, {name}!*

I'm your intelligent bot builder and AI assistant, powered by cutting-edge AI to help you with anything!

*🚀 Quick Start:*

📝 *Productivity*
• `/remind Call mom in 2 hours` - Set reminders
• `/note Meeting ideas` - Take quick notes
• `/task Buy groceries` - Track tasks

🤖 *Bot Building*
• `/build` - Create your own custom bot
• `/templates` - Browse 12+ bot templates
• `/mybots` - Manage your bots

🧠 *AI Features*
• Just chat with me naturally!
• `/translate Spanish Hello world`
• `/summarize [paste text]`
• `/quiz Science` - Take a quiz

📊 *Progress*
• `/profile` - Your stats & achievements
• `/leaderboard` - Top users

*Type /help for all commands!*

What would you like to do first? 👇
"""
    else:
        welcome_message = f"""
👋 *Welcome back, {name}!*

Great to see you again! How can I help you today?

Quick actions below or just tell me what you need!
"""
    
    keyboard = [
        [InlineKeyboardButton("📝 Set Reminder", callback_data="quick_reminder"),
         InlineKeyboardButton("📋 Add Task", callback_data="quick_task")],
        [InlineKeyboardButton("🤖 Build a Bot", callback_data="build_bot"),
         InlineKeyboardButton("📄 Create Note", callback_data="quick_note")],
        [InlineKeyboardButton("💬 Chat with AI", callback_data="start_chat"),
         InlineKeyboardButton("📊 My Profile", callback_data="show_profile")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        welcome_message,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /help command."""
    await track_command(update.effective_user.id, "help")
    
    help_text = """
📚 *Waya Command Reference*

*🏠 Basic Commands:*
`/start` - Welcome message
`/help` - This help guide
`/menu` - Interactive menu
`/profile` - Your stats & level
`/settings` - Preferences

*⏰ Reminders:*
`/remind <text>` - Set reminder (natural language!)
`/reminders` - List pending reminders
`/delreminder <id>` - Delete reminder
`/snooze <id> <minutes>` - Snooze reminder

*📝 Notes:*
`/note <title> | <content>` - Create note
`/notes` - List your notes
`/searchnotes <query>` - Search notes
`/delnote <id>` - Delete note

*✅ Tasks:*
`/task <description>` - Create task
`/tasks` - List your tasks
`/done <id>` - Complete task
`/deltask <id>` - Delete task

*🤖 Bot Building:*
`/build` - Start building a bot
`/templates` - Browse templates
`/mybots` - Your custom bots
`/usebot <id>` - Activate a bot

*🧠 AI Features:*
`/chat` - Start AI chat mode
`/clear` - Clear chat history
`/translate <lang> <text>` - Translate
`/summarize <text>` - Summarize text
`/quiz <topic>` - Quiz question

*🎭 Personalities:*
`/personalities` - View personalities
`/newpersonality` - Create one
`/setpersonality <id>` - Switch

*📊 Polls:*
`/poll <question> | <opt1> | <opt2>...`
`/pollresults <id>` - View results

*🎙 Voice AI (ElevenLabs):*
`/voice <text>` - Text to speech
`/voices` - List all voices
`/setvoice <name>` - Set default voice
`/voicestyle <style>` - Set voice style
`/speakthis` - Reply to convert to voice

*💚 Emotion AI (Hume):*
`/mood <text>` - Analyze emotions
`/emotions` - Your emotional insights
`/empathy` - Toggle empathic mode
`/wellbeing` - Wellbeing check
`/analyzeemotion` - Analyze voice emotions

*📈 Other:*
`/stats` - Usage statistics
`/suggest` - Smart suggestions
`/leaderboard` - Top users
`/feedback <text>` - Send feedback

💡 *Pro Tip:* You can just chat naturally - I understand context!
"""
    
    # Use effective_message to support both direct commands and callback queries
    message = update.effective_message
    if message:
        await message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)


async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /menu command."""
    await track_command(update.effective_user.id, "menu")
    
    keyboard = [
        [KeyboardButton("⏰ Reminders"), KeyboardButton("✅ Tasks")],
        [KeyboardButton("📝 Notes"), KeyboardButton("🤖 My Bots")],
        [KeyboardButton("💬 Chat"), KeyboardButton("📊 Profile")],
        [KeyboardButton("⚙️ Settings"), KeyboardButton("❓ Help")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "📱 *Main Menu*\n\nSelect an option:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )


async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /profile command."""
    await ensure_user(update)
    await track_command(update.effective_user.id, "profile")
    
    user_id = update.effective_user.id
    name = get_user_display_name(update)
    
    stats = await db.get_user_stats(user_id)
    user = await db.get_user(user_id)
    
    # Use effective_message to support both direct commands and callback queries
    message = update.effective_message
    
    if not stats:
        if message:
            await message.reply_text("Could not load your profile. Please try again.")
        return
    
    # Calculate level progress
    current_xp = stats.get("xp_points", 0)
    level = stats.get("level", 1)
    xp_for_current = (level - 1) ** 2 * 100
    xp_for_next = level ** 2 * 100
    xp_in_level = current_xp - xp_for_current
    xp_needed = xp_for_next - xp_for_current
    progress = min(100, int((xp_in_level / max(1, xp_needed)) * 100))
    progress_bar = "▓" * (progress // 10) + "░" * (10 - progress // 10)
    
    # Determine rank emoji
    rank_emojis = {1: "🥉", 2: "🥈", 3: "🥇", 4: "💎", 5: "👑"}
    rank_emoji = rank_emojis.get(min(5, (level // 10) + 1), "🌟")
    
    profile_text = f"""
{rank_emoji} *{name}'s Profile*

*📊 Level & XP:*
Level: {level} {rank_emoji}
XP: {current_xp:,} / {xp_for_next:,}
[{progress_bar}] {progress}%

*🔥 Streak:*
Current: {stats.get('streak_days', 0)} days
Longest: {stats.get('longest_streak', 0)} days

*�� Statistics:*
💬 Messages: {stats.get('total_messages', 0):,}
🤖 AI Requests: {stats.get('total_ai_requests', 0):,}
⏰ Reminders: {stats.get('total_reminders_created', 0)} ({stats.get('total_reminders_completed', 0)} done)
✅ Tasks: {stats.get('total_tasks_created', 0)} ({stats.get('total_tasks_completed', 0)} done)
📝 Notes: {stats.get('total_notes', 0)}
🤖 Bots Created: {stats.get('total_bots_created', 0)}

*📅 Member Since:*
{user.get('created_at', datetime.now()).strftime('%B %d, %Y') if user else 'Unknown'}

Keep chatting to earn more XP! 🚀
"""
    
    keyboard = [
        [InlineKeyboardButton("🏆 Leaderboard", callback_data="show_leaderboard"),
         InlineKeyboardButton("🎯 Achievements", callback_data="show_achievements")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if message:
        await message.reply_text(
            profile_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )


async def leaderboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /leaderboard command."""
    await track_command(update.effective_user.id, "leaderboard")
    
    # Use effective_message to support both direct commands and callback queries
    message = update.effective_message
    
    async with db.get_connection() as conn:
        rows = await conn.fetch("""
            SELECT u.first_name, u.username, s.xp_points, s.level, s.streak_days
            FROM user_stats s
            JOIN users u ON s.user_id = u.id
            ORDER BY s.xp_points DESC
            LIMIT 10
        """)
    
    if not rows:
        if message:
            await message.reply_text("No users on the leaderboard yet!")
        return
    
    text = "🏆 *Waya Leaderboard*\n\n"
    
    medals = ["🥇", "🥈", "🥉"]
    for i, row in enumerate(rows):
        medal = medals[i] if i < 3 else f"{i+1}."
        name = row['first_name'] or f"@{row['username']}" or "Anonymous"
        text += f"{medal} *{name}*\n"
        text += f"    Level {row['level']} • {row['xp_points']:,} XP • 🔥{row['streak_days']}\n\n"
    
    if message:
        await message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


# =====================================================
# REMINDER COMMANDS
# =====================================================

async def remind_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /remind command."""
    await ensure_user(update)
    await track_command(update.effective_user.id, "remind")
    
    if not context.args:
        await update.message.reply_text(
            "⏰ *Set a Reminder*\n\n"
            "Usage: `/remind <what to remind>`\n\n"
            "I understand natural language:\n"
            "• `/remind Call mom in 2 hours`\n"
            "• `/remind Meeting tomorrow at 3pm`\n"
            "• `/remind Take medicine at 9am daily`\n"
            "• `/remind Pay bills on Friday`\n\n"
            "Just describe when and what! 🎯",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    reminder_text = " ".join(context.args)
    await update.message.chat.send_action(ChatAction.TYPING)
    
    # Parse with AI
    parsed = await parse_reminder_request(reminder_text)
    
    if "error" in parsed:
        await update.message.reply_text(
            "❌ I couldn't understand that reminder.\n\n"
            "Try being more specific:\n"
            "`/remind Call John tomorrow at 2pm`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    try:
        remind_at = datetime.fromisoformat(parsed["datetime"].replace("Z", "+00:00"))
        if remind_at.tzinfo is None:
            remind_at = remind_at.replace(tzinfo=timezone.utc)
            
        reminder_msg = parsed.get("reminder_text", reminder_text)
        repeat = parsed.get("repeat")
        
        reminder_id = await db.create_reminder(
            user_id=update.effective_user.id,
            title=reminder_msg,
            remind_at=remind_at,
            repeat_type=repeat if repeat and repeat != "none" else "none"
        )
        
        await db.add_xp(update.effective_user.id, 5)
        
        repeat_text = f"\n🔄 Repeats: {repeat}" if repeat and repeat != "none" else ""
        
        await update.message.reply_text(
            f"✅ *Reminder Set!*\n\n"
            f"📌 {reminder_msg}\n"
            f"⏰ {remind_at.strftime('%B %d, %Y at %I:%M %p')}{repeat_text}\n\n"
            f"I'll notify you when it's time! (ID: {reminder_id})",
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        await update.message.reply_text(
            f"❌ Error creating reminder. Please try again.\n\nTip: Be specific about the time!",
            parse_mode=ParseMode.MARKDOWN
        )


async def reminders_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /reminders command."""
    await ensure_user(update)
    await track_command(update.effective_user.id, "reminders")
    
    reminders = await db.get_user_reminders(update.effective_user.id)
    
    if not reminders:
        await update.message.reply_text(
            "📭 No pending reminders.\n\n"
            "Set one with: `/remind Call mom in 2 hours`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    text = "⏰ *Your Reminders:*\n\n"
    
    for r in reminders[:15]:
        remind_at = r['remind_at']
        if isinstance(remind_at, str):
            remind_at = datetime.fromisoformat(remind_at)
        
        priority_emoji = {"urgent": "🚨", "high": "❗", "normal": "📌", "low": "📝"}.get(r.get('priority', 'normal'), "📌")
        repeat = f" 🔄" if r.get('repeat_type') and r['repeat_type'] != 'none' else ""
        
        text += f"{priority_emoji} *{r['id']}.* {r['title']}{repeat}\n"
        text += f"    ⏰ {remind_at.strftime('%b %d, %I:%M %p')}\n\n"
    
    if len(reminders) > 15:
        text += f"\n_...and {len(reminders) - 15} more_"
    
    text += "\n`/delreminder <id>` to delete"
    
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def del_reminder_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /delreminder command."""
    await track_command(update.effective_user.id, "delreminder")
    
    if not context.args:
        await update.message.reply_text("Usage: `/delreminder <id>`", parse_mode=ParseMode.MARKDOWN)
        return
    
    try:
        reminder_id = int(context.args[0])
        success = await db.delete_reminder(reminder_id, update.effective_user.id)
        
        if success:
            await update.message.reply_text(f"✅ Reminder {reminder_id} deleted!")
        else:
            await update.message.reply_text("❌ Reminder not found.")
    except ValueError:
        await update.message.reply_text("❌ Please provide a valid ID.")


async def snooze_reminder_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /snooze command."""
    await track_command(update.effective_user.id, "snooze")
    
    if len(context.args) < 2:
        await update.message.reply_text(
            "Usage: `/snooze <id> <minutes>`\n\n"
            "Example: `/snooze 5 30` (snooze reminder 5 for 30 minutes)",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    try:
        reminder_id = int(context.args[0])
        minutes = int(context.args[1])
        
        success = await db.snooze_reminder(reminder_id, update.effective_user.id, minutes)
        
        if success:
            await update.message.reply_text(f"⏰ Reminder snoozed for {minutes} minutes!")
        else:
            await update.message.reply_text("❌ Reminder not found.")
    except ValueError:
        await update.message.reply_text("❌ Please provide valid numbers.")


# =====================================================
# NOTE COMMANDS
# =====================================================

async def note_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /note command."""
    await ensure_user(update)
    await track_command(update.effective_user.id, "note")
    
    if not context.args:
        await update.message.reply_text(
            "📝 *Create a Note*\n\n"
            "Usage: `/note <title> | <content>`\n\n"
            "Examples:\n"
            "• `/note Shopping List | Milk, eggs, bread`\n"
            "• `/note Quick thought about the project`\n\n"
            "The `|` separator is optional!",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    text = " ".join(context.args)
    parts = text.split("|", 1)
    
    title = parts[0].strip()
    content = parts[1].strip() if len(parts) > 1 else title
    
    if len(parts) == 1:
        title = f"Note {datetime.now().strftime('%b %d, %H:%M')}"
    
    note_id = await db.create_note(
        user_id=update.effective_user.id,
        title=title,
        content=content
    )
    
    await db.add_xp(update.effective_user.id, 3)
    
    await update.message.reply_text(
        f"✅ *Note Saved!*\n\n"
        f"📌 *{title}*\n"
        f"{content[:200]}{'...' if len(content) > 200 else ''}\n\n"
        f"ID: {note_id}",
        parse_mode=ParseMode.MARKDOWN
    )


async def notes_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /notes command."""
    await ensure_user(update)
    await track_command(update.effective_user.id, "notes")
    
    notes = await db.get_user_notes(update.effective_user.id)
    
    if not notes:
        await update.message.reply_text(
            "📭 No notes yet.\n\n"
            "Create one: `/note Meeting ideas | Discuss budget`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    text = "📝 *Your Notes:*\n\n"
    
    for n in notes[:10]:
        pin = "📌 " if n.get('is_pinned') else ""
        text += f"{pin}*{n['id']}.* {n.get('title', 'Untitled')}\n"
        preview = n['content'][:50] + "..." if len(n['content']) > 50 else n['content']
        text += f"   _{preview}_\n\n"
    
    if len(notes) > 10:
        text += f"_...and {len(notes) - 10} more_\n"
    
    text += "\n`/searchnotes <query>` to search"
    
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def search_notes_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /searchnotes command."""
    await track_command(update.effective_user.id, "searchnotes")
    
    if not context.args:
        await update.message.reply_text("Usage: `/searchnotes <query>`", parse_mode=ParseMode.MARKDOWN)
        return
    
    query = " ".join(context.args)
    notes = await db.search_notes(update.effective_user.id, query)
    
    if not notes:
        await update.message.reply_text(f"📭 No notes found matching '{query}'")
        return
    
    text = f"🔍 *Notes matching '{query}':*\n\n"
    for n in notes:
        text += f"*{n['id']}.* {n.get('title', 'Untitled')}\n"
        preview = n['content'][:50] + "..." if len(n['content']) > 50 else n['content']
        text += f"   _{preview}_\n\n"
    
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def del_note_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /delnote command."""
    await track_command(update.effective_user.id, "delnote")
    
    if not context.args:
        await update.message.reply_text("Usage: `/delnote <id>`", parse_mode=ParseMode.MARKDOWN)
        return
    
    try:
        note_id = int(context.args[0])
        success = await db.delete_note(note_id, update.effective_user.id)
        
        if success:
            await update.message.reply_text(f"✅ Note {note_id} deleted!")
        else:
            await update.message.reply_text("❌ Note not found.")
    except ValueError:
        await update.message.reply_text("❌ Please provide a valid ID.")


# =====================================================
# TASK COMMANDS
# =====================================================

async def task_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /task command."""
    await ensure_user(update)
    await track_command(update.effective_user.id, "task")
    
    if not context.args:
        await update.message.reply_text(
            "✅ *Create a Task*\n\n"
            "Usage: `/task <description>`\n\n"
            "I understand natural language:\n"
            "• `/task Buy groceries`\n"
            "• `/task Finish report by Friday high priority`\n"
            "• `/task Call client tomorrow`\n\n"
            "Priorities: low, normal, high, urgent",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    task_text = " ".join(context.args)
    await update.message.chat.send_action(ChatAction.TYPING)
    
    # Parse with AI
    parsed = await parse_task_request(task_text)
    
    title = parsed.get("title", task_text)
    description = parsed.get("description")
    priority = parsed.get("priority", "normal")
    
    # Validate and map priority to allowed values
    VALID_PRIORITIES = {"low", "normal", "high", "urgent"}
    PRIORITY_MAP = {"medium": "normal", "critical": "urgent", "important": "high"}
    if priority not in VALID_PRIORITIES:
        priority = PRIORITY_MAP.get(priority.lower() if priority else "normal", "normal")
    
    due_date = None
    
    if parsed.get("due_date"):
        try:
            due_date = datetime.fromisoformat(parsed["due_date"].replace("Z", "+00:00"))
        except:
            pass
    
    task_id = await db.create_task(
        user_id=update.effective_user.id,
        title=title,
        description=description,
        due_date=due_date,
        priority=priority
    )
    
    await db.add_xp(update.effective_user.id, 4)
    
    priority_emoji = {"urgent": "🚨", "high": "🔴", "normal": "🟡", "low": "🟢"}.get(priority, "🟡")
    due_text = f"\n📅 Due: {due_date.strftime('%b %d, %Y')}" if due_date else ""
    
    await update.message.reply_text(
        f"✅ *Task Created!*\n\n"
        f"{priority_emoji} *{title}*{due_text}\n"
        f"Priority: {priority.capitalize()}\n\n"
        f"ID: {task_id}",
        parse_mode=ParseMode.MARKDOWN
    )


async def tasks_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /tasks command."""
    await ensure_user(update)
    await track_command(update.effective_user.id, "tasks")
    
    tasks = await db.get_user_tasks(update.effective_user.id)
    
    if not tasks:
        await update.message.reply_text(
            "📭 No tasks.\n\n"
            "Create one: `/task Buy groceries`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    pending = [t for t in tasks if t['status'] in ('pending', 'in_progress')]
    completed = [t for t in tasks if t['status'] == 'completed']
    
    text = "✅ *Your Tasks:*\n\n"
    
    if pending:
        text += "*📋 Pending:*\n"
        for t in pending:
            priority_emoji = {"urgent": "🚨", "high": "🔴", "normal": "🟡", "low": "🟢"}.get(t['priority'], "🟡")
            due = ""
            if t.get('due_date'):
                due_dt = t['due_date']
                if isinstance(due_dt, str):
                    due_dt = datetime.fromisoformat(due_dt)
                due = f" (📅 {due_dt.strftime('%b %d')})"
            text += f"  {priority_emoji} *{t['id']}.* {t['title']}{due}\n"
        text += "\n"
    
    if completed:
        text += f"*✅ Completed ({len(completed)}):*\n"
        for t in completed[:3]:
            text += f"  ✅ ~~{t['title']}~~\n"
        if len(completed) > 3:
            text += f"  _...and {len(completed) - 3} more_\n"
    
    text += "\n`/done <id>` to complete"
    
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def done_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /done command."""
    await track_command(update.effective_user.id, "done")
    
    if not context.args:
        await update.message.reply_text("Usage: `/done <task_id>`", parse_mode=ParseMode.MARKDOWN)
        return
    
    try:
        task_id = int(context.args[0])
        success = await db.update_task_status(task_id, update.effective_user.id, "completed")
        
        if success:
            xp_result = await db.add_xp(update.effective_user.id, 10)
            level_up = " 🎉 Level up!" if xp_result.get("level_up") else ""
            await update.message.reply_text(f"✅ Task completed! +10 XP{level_up} 🎉")
        else:
            await update.message.reply_text("❌ Task not found.")
    except ValueError:
        await update.message.reply_text("❌ Please provide a valid ID.")


async def del_task_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /deltask command."""
    await track_command(update.effective_user.id, "deltask")
    
    if not context.args:
        await update.message.reply_text("Usage: `/deltask <id>`", parse_mode=ParseMode.MARKDOWN)
        return
    
    try:
        task_id = int(context.args[0])
        success = await db.delete_task(task_id, update.effective_user.id)
        
        if success:
            await update.message.reply_text(f"✅ Task {task_id} deleted!")
        else:
            await update.message.reply_text("❌ Task not found.")
    except ValueError:
        await update.message.reply_text("❌ Please provide a valid ID.")


# =====================================================
# BOT BUILDING COMMANDS
# =====================================================

async def build_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Build a bot INSTANTLY - one step, no clicking!
    User says what they want → bot creates it automatically.
    """
    await ensure_user(update)
    user_id = update.effective_user.id
    name = get_user_display_name(update)
    
    # What does user want?
    if not context.args:
        await update.message.reply_text(
            f"🤖 *Instant Bot Builder*\n\n"
            f"✨ **Premium Features:**\n"
            f"• AI-powered instant creation\n"
            f"• Smart context understanding\n"
            f"• Voice-ready responses\n\n"
            f"Tell me what you want:\n"
            f"`I need a coffee shop bot`\n"
            f"`create a fitness coach`\n\n"
            f"I'll create it instantly! ⚡",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Get user request
    user_request = " ".join(context.args)
    
    # PREMIUM TYPING SEQUENCE - show the magic!
    await update.message.chat.send_action(ChatAction.TYPING)
    loading_msg = await update.message.reply_text("🎨 *Analyzing your request...*")
    await asyncio.sleep(0.8)
    
    await update.message.chat.send_action(ChatAction.TYPING)
    await loading_msg.edit_text("🧠 *Designing your bot...*")
    await asyncio.sleep(0.8)
    
    # AI creates
    await update.message.chat.send_action(ChatAction.TYPING)
    config = await generate_bot_suggestion(user_request)
    
    await loading_msg.edit_text("⚙️ *Building...*")
    await asyncio.sleep(0.5)
    
    if "error" in config:
        await loading_msg.edit_text(f"❌ Oops! {config.get('error', 'Something went wrong')}")
        return
    
    # Create bot in database
    bot_id = await db.create_custom_bot(
        user_id=user_id,
        name=config.get('bot_name', 'My Bot'),
        bot_type=config.get('bot_type', 'general'),
        system_prompt=config.get('system_prompt', ''),
        description=config.get('bot_description'),
        welcome_message=config.get('greeting_message'),
        personality=config.get('personality'),
        commands=config.get('commands')
    )
    
    # Make it active!
    await db.set_active_bot(user_id, bot_id)
    await db.add_xp(user_id, 30)
    
    # PREMIUM SUCCESS with buttons!
    bot_name = config.get('bot_name', 'Bot')
    desc = config.get('bot_description', '')[:100]
    features = config.get('features', [])[:3]
    
    keyboard = [
        [InlineKeyboardButton("💬 Start Chatting", callback_data="start_chat")],
        [InlineKeyboardButton("🎤 Enable Voice", callback_data="add_voice"),
         InlineKeyboardButton("📋 Details", callback_data=f"view_bot_{bot_id}")],
        [InlineKeyboardButton("📝 My Bots", callback_data="menu_mybots")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await loading_msg.edit_text(
        f"✅ *{bot_name}* is ready!\n\n"
        f"*Description:* {desc}\n\n"
        f"*Features:*\n"
        f"• {features[0] if len(features) > 0 else 'Smart responses'}\n"
        f"• {features[1] if len(features) > 1 else 'Context memory'}\n"
        f"• {features[2] if len(features) > 2 else 'Voice ready'}\n\n"
        f"*How to use:*\n"
        f"• Just send any message to chat!\n"
        f"• Use `/usebot {bot_id}` to switch to this bot\n"
        f"• Use `/mybots` to see all your bots\n\n"
        f"Bot ID: `{bot_id}`",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )


async def templates_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /templates command."""
    await track_command(update.effective_user.id, "templates")
    
    templates = await db.get_bot_templates()
    
    if not templates:
        await update.message.reply_text("No templates available.")
        return
    
    text = "📋 *Bot Templates*\n\n"
    
    categories = {}
    for t in templates:
        cat = t.get('category', 'Other')
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(t)
    
    for category, temps in categories.items():
        text += f"*{category}:*\n"
        for t in temps:
            featured = "⭐ " if t.get('is_featured') else ""
            text += f"  {featured}{t['name']}\n"
        text += "\n"
    
    text += "_Use /build to create from a template!_"
    
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def my_bots_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /mybots command."""
    await ensure_user(update)
    await track_command(update.effective_user.id, "mybots")
    
    bots = await db.get_user_bots(update.effective_user.id)
    
    if not bots:
        await update.message.reply_text(
            "🤖 You haven't created any bots yet.\n\n"
            "Use `/build` to create your first one!",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    text = "🤖 *Your Custom Bots:*\n\n"
    
    for bot in bots:
        status = "🟢 Active" if bot.get('is_active') else "🔴 Inactive"
        text += f"*{bot['id']}.* {bot['name']}\n"
        text += f"   Type: {bot['bot_type'].replace('_', ' ').title()}\n"
        text += f"   {status} • Used {bot.get('usage_count', 0)} times\n\n"
    
    text += "\n`/usebot <id>` to activate a bot"
    
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def activate_bot_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /usebot command."""
    await track_command(update.effective_user.id, "usebot")
    
    if not context.args:
        await update.message.reply_text(
            "Usage: `/usebot <bot_id>`\n\n"
            "Use `/mybots` to see your bots.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    try:
        bot_id = int(context.args[0])
        bot = await db.get_bot(bot_id)
        
        if not bot:
            await update.message.reply_text("❌ Bot not found.")
            return
        
        await db.set_active_bot(update.effective_user.id, bot_id)
        await db.increment_bot_usage(bot_id)
        
        welcome = bot.get('welcome_message') or f"*{bot['name']}* is now active!"
        
        await update.message.reply_text(
            f"🤖 *Bot Activated!*\n\n{welcome}\n\n"
            f"_Chat with your bot now! Send `/usebot 0` to deactivate._",
            parse_mode=ParseMode.MARKDOWN
        )
    except ValueError:
        await update.message.reply_text("❌ Please provide a valid bot ID.")


# =====================================================
# AI CHAT COMMANDS
# =====================================================

async def chat_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /chat command."""
    await ensure_user(update)
    await track_command(update.effective_user.id, "chat")
    
    await update.message.reply_text(
        "💬 *AI Chat Mode*\n\n"
        "I'm ready to chat! Just type your message.\n\n"
        "I can help you with:\n"
        "• Answering questions\n"
        "• Writing and editing\n"
        "• Brainstorming ideas\n"
        "• Coding help\n"
        "• And much more!\n\n"
        "_Use /clear to reset our conversation_",
        parse_mode=ParseMode.MARKDOWN
    )


async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /clear command."""
    await track_command(update.effective_user.id, "clear")
    
    await db.clear_conversation_history(update.effective_user.id)
    await db.clear_session_state(update.effective_user.id)
    
    await update.message.reply_text(
        "🧹 Conversation cleared!\n\n"
        "I've forgotten our previous chat. Let's start fresh!"
    )


async def translate_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /translate command."""
    await ensure_user(update)
    await track_command(update.effective_user.id, "translate")
    
    if len(context.args) < 2:
        await update.message.reply_text(
            "🌍 *Translate Text*\n\n"
            "Usage: `/translate <language> <text>`\n\n"
            "Examples:\n"
            "• `/translate Spanish Hello, how are you?`\n"
            "• `/translate Japanese Good morning`\n"
            "• `/translate French I love programming`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    target_lang = context.args[0]
    text_to_translate = " ".join(context.args[1:])
    
    await update.message.chat.send_action(ChatAction.TYPING)
    
    translation = await translate_text(text_to_translate, target_lang)
    await db.increment_stat(update.effective_user.id, "total_ai_requests")
    
    response_text = (
        f"🌍 *Translation to {target_lang}:*\n\n"
        f"Original: _{text_to_translate}_\n\n"
        f"Translated: *{translation}*"
    )
    await safe_reply_text(update.message, response_text, parse_mode=ParseMode.MARKDOWN)


async def summarize_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /summarize command."""
    await ensure_user(update)
    await track_command(update.effective_user.id, "summarize")
    
    if not context.args:
        await update.message.reply_text(
            "📝 *Summarize Text*\n\n"
            "Usage: `/summarize <text>`\n\n"
            "Paste any long text and I'll summarize it for you!",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    text_to_summarize = " ".join(context.args)
    
    await update.message.chat.send_action(ChatAction.TYPING)
    
    summary = await summarize_text(text_to_summarize)
    await db.increment_stat(update.effective_user.id, "total_ai_requests")
    
    await safe_reply_text(update.message, f"📝 *Summary:*\n\n{summary}", parse_mode=ParseMode.MARKDOWN)


async def quiz_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /quiz command."""
    await ensure_user(update)
    await track_command(update.effective_user.id, "quiz")
    
    topic = " ".join(context.args) if context.args else "general knowledge"
    
    await update.message.chat.send_action(ChatAction.TYPING)
    
    quiz = await generate_quiz_question(topic)
    await db.increment_stat(update.effective_user.id, "total_ai_requests")
    
    if "error" in quiz:
        await update.message.reply_text("❌ Couldn't generate a quiz. Try a different topic!")
        return
    
    # Store correct answer in session
    await db.update_session_state(
        update.effective_user.id,
        "awaiting_quiz_answer",
        {"correct": quiz.get("correct_answer", "A"), "explanation": quiz.get("explanation", "")}
    )
    
    text = f"🧠 *Quiz: {topic.title()}*\n\n"
    text += f"*{quiz.get('question', 'Question')}*\n\n"
    
    options = quiz.get("options", ["A", "B", "C", "D"])
    keyboard = []
    row = []
    for i, opt in enumerate(options):
        letter = chr(65 + i)  # A, B, C, D
        row.append(InlineKeyboardButton(letter, callback_data=f"quiz_answer_{letter}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
        text += f"*{opt}*\n"
    if row:
        keyboard.append(row)
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)


# =====================================================
# PERSONALITY COMMANDS
# =====================================================

async def personalities_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /personalities command."""
    await ensure_user(update)
    await track_command(update.effective_user.id, "personalities")
    
    personalities = await db.get_user_personalities(update.effective_user.id)
    
    text = "🎭 *AI Personalities*\n\n"
    
    if personalities:
        for p in personalities:
            active = "✅ " if p.get('is_active') else ""
            text += f"{active}*{p['id']}.* {p['name']}\n"
            text += f"   _{p.get('description', 'Custom personality')[:50]}_\n\n"
    else:
        text += "_No custom personalities yet._\n\n"
    
    text += "Create one: `/newpersonality`\n"
    text += "Switch: `/setpersonality <id>`"
    
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def new_personality_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /newpersonality command."""
    await ensure_user(update)
    await track_command(update.effective_user.id, "newpersonality")
    
    await db.update_session_state(
        update.effective_user.id,
        "creating_personality",
        {"step": "name"}
    )
    
    await update.message.reply_text(
        "🎭 *Create AI Personality*\n\n"
        "Let's create a custom AI personality!\n\n"
        "What would you like to name it?\n\n"
        "_Example: Friendly Teacher, Sarcastic Friend, Professional Assistant_",
        parse_mode=ParseMode.MARKDOWN
    )


async def set_personality_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /setpersonality command."""
    await track_command(update.effective_user.id, "setpersonality")
    
    if not context.args:
        await update.message.reply_text(
            "Usage: `/setpersonality <id>`\n\n"
            "Use `/personalities` to see available personalities.\n"
            "Use `/setpersonality 0` to reset to default.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    try:
        personality_id = int(context.args[0])
        
        if personality_id == 0:
            # Reset to default
            async with db.get_connection() as conn:
                await conn.execute(
                    "UPDATE ai_personalities SET is_active = FALSE WHERE user_id = $1",
                    update.effective_user.id
                )
            await update.message.reply_text("✅ Reset to default Waya personality!")
            return
        
        success = await db.set_active_personality(update.effective_user.id, personality_id)
        
        if success:
            await update.message.reply_text(f"✅ Personality switched!")
        else:
            await update.message.reply_text("❌ Personality not found.")
    except ValueError:
        await update.message.reply_text("❌ Please provide a valid ID.")


# =====================================================
# POLL COMMANDS
# =====================================================

async def poll_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /poll command."""
    await ensure_user(update)
    await track_command(update.effective_user.id, "poll")
    
    if not context.args:
        await update.message.reply_text(
            "📊 *Create a Poll*\n\n"
            "Usage: `/poll <question> | <option1> | <option2> ...`\n\n"
            "Example:\n"
            "`/poll What's your favorite color? | Red | Blue | Green | Yellow`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    text = " ".join(context.args)
    parts = [p.strip() for p in text.split("|")]
    
    if len(parts) < 3:
        await update.message.reply_text(
            "❌ Need at least 2 options.\n\n"
            "Format: `/poll Question | Option1 | Option2`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    question = parts[0]
    options = parts[1:][:10]  # Max 10 options
    
    # Create poll record
    poll_id = await db.create_poll(
        user_id=update.effective_user.id,
        question=question,
        options=options
    )
    
    # Send Telegram poll
    poll_message = await update.message.reply_poll(
        question=question,
        options=options,
        is_anonymous=True
    )
    
    await update.message.reply_text(f"✅ Poll created! ID: {poll_id}")


async def poll_results_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /pollresults command."""
    await track_command(update.effective_user.id, "pollresults")
    
    polls = await db.get_user_polls(update.effective_user.id, include_closed=True)
    
    if not polls:
        await update.message.reply_text("You haven't created any polls yet.")
        return
    
    text = "📊 *Your Polls:*\n\n"
    
    for p in polls[:10]:
        status = "🟢 Open" if not p.get('is_closed') else "🔴 Closed"
        text += f"*{p['id']}.* {p['question'][:50]}\n"
        text += f"   {status} • {p.get('total_votes', 0)} votes\n\n"
    
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


# =====================================================
# OTHER COMMANDS
# =====================================================

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /stats command."""
    await track_command(update.effective_user.id, "stats")
    
    stats = await db.get_user_stats(update.effective_user.id)
    activity = await db.get_user_activity(update.effective_user.id, days=7)
    
    if not stats:
        await update.message.reply_text("Could not load stats.")
        return
    
    text = "📈 *Your Usage Statistics*\n\n"
    text += f"💬 Total Messages: {stats.get('total_messages', 0):,}\n"
    text += f"🤖 AI Requests: {stats.get('total_ai_requests', 0):,}\n"
    text += f"⏰ Reminders: {stats.get('total_reminders_created', 0)}\n"
    text += f"✅ Tasks: {stats.get('total_tasks_created', 0)}\n"
    text += f"📝 Notes: {stats.get('total_notes', 0)}\n"
    text += f"🤖 Bots Created: {stats.get('total_bots_created', 0)}\n"
    
    if activity.get("daily_activity"):
        text += f"\n*Last 7 Days Activity:*\n"
        for day in activity["daily_activity"][-7:]:
            text += f"  {day['date']}: {day['count']} actions\n"
    
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /settings command."""
    await ensure_user(update)
    await track_command(update.effective_user.id, "settings")
    
    user = await db.get_user(update.effective_user.id)
    prefs = user.get('preferences', {}) if user else {}
    
    text = "⚙️ *Settings*\n\n"
    text += f"🌍 Language: {user.get('language_code', 'en') if user else 'en'}\n"
    text += f"🕐 Timezone: {user.get('timezone', 'UTC') if user else 'UTC'}\n"
    text += f"📧 Daily Summary: {'On' if prefs.get('daily_summary') else 'Off'}\n"
    text += f"🔕 Quiet Hours: {'On' if prefs.get('quiet_hours') else 'Off'}\n"
    
    keyboard = [
        [InlineKeyboardButton("🌍 Language", callback_data="setting_language"),
         InlineKeyboardButton("🕐 Timezone", callback_data="setting_timezone")],
        [InlineKeyboardButton("📧 Daily Summary", callback_data="setting_daily"),
         InlineKeyboardButton("🔕 Quiet Hours", callback_data="setting_quiet")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)


async def suggest_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /suggest command."""
    await ensure_user(update)
    await track_command(update.effective_user.id, "suggest")
    
    await update.message.chat.send_action(ChatAction.TYPING)
    
    # Gather context
    stats = await db.get_user_stats(update.effective_user.id)
    tasks = await db.get_user_tasks(update.effective_user.id, status='pending')
    reminders = await db.get_user_reminders(update.effective_user.id, limit=5)
    
    context_data = {
        "pending_tasks": len(tasks),
        "pending_reminders": len(reminders),
        "total_messages": stats.get('total_messages', 0) if stats else 0,
        "level": stats.get('level', 1) if stats else 1,
        "streak": stats.get('streak_days', 0) if stats else 0
    }
    
    suggestions = await get_smart_suggestions(context_data)
    
    text = "💡 *Smart Suggestions*\n\n"
    for i, suggestion in enumerate(suggestions, 1):
        text += f"{i}. {suggestion}\n"
    
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def feedback_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /feedback command."""
    await track_command(update.effective_user.id, "feedback")
    
    if not context.args:
        await update.message.reply_text(
            "📝 *Send Feedback*\n\n"
            "Usage: `/feedback <your message>`\n\n"
            "We'd love to hear your thoughts, suggestions, or bug reports!",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    feedback_text = " ".join(context.args)
    
    async with db.get_connection() as conn:
        await conn.execute("""
            INSERT INTO feedback (user_id, feedback_type, content)
            VALUES ($1, 'general', $2)
        """, update.effective_user.id, feedback_text)
    
    await update.message.reply_text(
        "✅ Thank you for your feedback!\n\n"
        "We appreciate you taking the time to help us improve Waya."
    )


# =====================================================
# MESSAGE HANDLER
# =====================================================


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming text messages - smart AI assistant that understands context."""
    if not update.message or not update.message.text:
        return
    
    user_data = await ensure_user(update)
    user_id = update.effective_user.id
    message_text = update.message.text
    
    await db.increment_stat(user_id, "total_messages")
    
    # Check session state for ongoing flows
    session = await db.get_session(user_id)
    state = session.get('current_state', 'idle') if session else 'idle'
    state_data = session.get('state_data', {}) if session else {}
    
    # Handle personality creation flow
    if state == "creating_personality":
        step = state_data.get('step', 'name')
        
        if step == 'name':
            await db.update_session_state(user_id, "creating_personality", {
                "step": "description",
                "name": message_text
            })
            await update.message.reply_text(
                f"Great! *{message_text}* sounds good.\n\n"
                "Now, describe how this personality should behave:\n\n"
                "_Example: Be friendly and encouraging, use casual language, add occasional humor_",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        elif step == 'description':
            name = state_data.get('name', 'Custom')
            system_prompt = f"You are {name}. {message_text}"
            
            personality_id = await db.create_personality(
                user_id=user_id,
                name=name,
                description=message_text[:200],
                system_prompt=system_prompt
            )
            
            await db.clear_session_state(user_id)
            
            await update.message.reply_text(
                f"✅ *Personality Created!*\n\n"
                f"*{name}* is ready to use!\n\n"
                f"Activate it with: `/setpersonality {personality_id}`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
    
    # SMART INTENT DETECTION - understands natural language!
    # Check if user wants to create a bot - even without /build command!
    intent = await analyze_message_intent(message_text)
    
    # Keywords that trigger bot creation
    bot_triggers = [
        "create bot", "build bot", "make a bot", "need a bot", "want a bot",
        "bot for", "bot that", "customer support bot", "help bot",
        "coffee shop bot", "fitness bot", "assistant bot", "tutor bot"
    ]
    
    wants_bot = any(trigger in message_text.lower() for trigger in bot_triggers)
    
    # 🧠 SMART TASKS - understand natural language!
    # Reminder: "remind me to call mom in 2 hours"
    if "remind" in message_text.lower() and ("to" in message_text.lower() or "in " in message_text.lower()):
        reminder_text = message_text.replace("remind", "").replace("me", "").replace("reminder", "").strip()
        if reminder_text:
            await update.message.chat.send_action(ChatAction.TYPING)
            parsed = await parse_reminder_request(message_text)
            if parsed and "reminder_text" in parsed:
                # Parse the datetime from the AI response
                remind_at = None
                datetime_str = parsed.get('datetime')
                if datetime_str:
                    try:
                        from datetime import datetime as dt
                        remind_at = dt.fromisoformat(datetime_str.replace('Z', '+00:00'))
                    except:
                        # Default to 1 hour from now if parsing fails
                        remind_at = datetime.now(timezone.utc) + timedelta(hours=1)
                else:
                    remind_at = datetime.now(timezone.utc) + timedelta(hours=1)
                
                await db.create_reminder(
                    user_id=user_id, 
                    title=parsed.get('reminder_text', reminder_text),
                    remind_at=remind_at,
                    repeat_type=parsed.get('repeat', 'none') or 'none'
                )
                await db.add_xp(user_id, 10)
                await update.message.reply_text(f"✅ Reminder set!\n\n{parsed.get('reminder_text', reminder_text)[:100]}")
                return
    
    # Note: "note: idea about project"
    if message_text.lower().startswith("note") or "write down" in message_text.lower() or "remember this" in message_text.lower():
        note_content = message_text.replace("note", "").replace("write down", "").replace("remember this", "").strip("：: ")
        if note_content and len(note_content) > 2:
            await db.create_note(user_id, note_content[:200], note_content)
            await db.add_xp(user_id, 5)
            await update.message.reply_text(f"✅ Note saved!\n\n{note_content[:100]}")
            return
    
    # Task: "task: buy groceries"
    if message_text.lower().startswith("task") or "todo" in message_text.lower():
        task_content = message_text.replace("task", "").replace("todo", "").strip("：: ")
        if task_content and len(task_content) > 2:
            await db.create_task(user_id, task_content)
            await db.add_xp(user_id, 5)
            await update.message.reply_text(f"✅ Task added!\n\n{task_content[:100]}")
            return
    
    if wants_bot:
        # Show typing
        await update.message.chat.send_action(ChatAction.TYPING)
        await update.message.reply_text("🎨 Creating your bot...")
        
        # Use AI to create the bot!
        config = await generate_bot_suggestion(message_text)
        
        if "error" in config:
            await update.message.reply_text(f"❌ {config['error']}")
            return
        
        # Create in DB
        bot_id = await db.create_custom_bot(
            user_id=user_id,
            name=config.get('bot_name', 'My Bot'),
            bot_type=config.get('bot_type', 'general'),
            system_prompt=config.get('system_prompt', ''),
            description=config.get('bot_description'),
            welcome_message=config.get('greeting_message'),
            personality=config.get('personality'),
            commands=config.get('commands')
        )
        
        await db.set_active_bot(user_id, bot_id)
        await db.add_xp(user_id, 30)
        
        await update.message.reply_text(
            f"✅ *{config.get('bot_name')} Created!*\n\n"
            f"Your custom bot is ready and active!\n\n"
            f"What it does: {config.get('bot_description', 'Helps you')[:80]}\n\n"
            f"Start chatting! 💬",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Check for menu button presses
    menu_handlers = {
        "⏰ Reminders": reminders_command,
        "✅ Tasks": tasks_command,
        "📝 Notes": notes_command,
        "🤖 My Bots": my_bots_command,
        "💬 Chat": chat_command,
        "📊 Profile": profile_command,
        "⚙️ Settings": settings_command,
        "❓ Help": help_command
    }
    
    if message_text in menu_handlers:
        await menu_handlers[message_text](update, context)
        return
    
    # Check for active custom bot
    if session and session.get('active_bot_id'):
        bot = await db.get_bot(session['active_bot_id'])
        if bot:
            await db.increment_bot_usage(bot['id'])
            system_prompt = bot.get('system_prompt', WAYA_SYSTEM_PROMPT)
            
            history = await db.get_conversation_history(user_id, limit=10)
            await db.add_conversation(user_id, "user", message_text)
            
            await update.message.chat.send_action(ChatAction.TYPING)
            
            response = await generate_response(
                user_message=message_text,
                conversation_history=history,
                system_prompt=system_prompt,
                user_name=get_user_display_name(update)
            )
            
            await db.add_conversation(user_id, "assistant", response)
            await db.increment_stat(user_id, "total_ai_requests")
            await db.increment_stat(user_id, "total_bot_interactions")
            
            # Use safe_reply_text for potentially long AI responses
            await safe_reply_text(update.message, response, parse_mode=ParseMode.MARKDOWN)
            return
    
    # Check for active personality
    personality = await db.get_active_personality(user_id)
    system_prompt = personality.get('system_prompt', WAYA_SYSTEM_PROMPT) if personality else WAYA_SYSTEM_PROMPT
    
    # Check user's empathic mode preference
    empathic_mode = False
    emotion_context = None
    
    async with db.get_connection() as conn:
        pref_row = await conn.fetchrow("""
            SELECT enable_empathic_responses FROM user_emotion_preferences
            WHERE user_id = $1
        """, user_id)
        # Safely access the preference with a default value
        if pref_row is not None:
            empathic_mode = pref_row.get('enable_empathic_responses', True) if hasattr(pref_row, 'get') else pref_row['enable_empathic_responses']
        else:
            empathic_mode = True
    
    # Analyze emotions if empathic mode is on
    if empathic_mode and emotion_engine.is_configured:
        emotion_context = await emotion_engine.analyze_text_emotion(message_text)
        if emotion_context:
            # Store emotional state
            async with db.get_connection() as conn:
                await emotion_engine.update_user_emotional_state(conn, user_id, emotion_context)
    
    # Regular AI conversation
    history = await db.get_conversation_history(user_id, limit=15)
    await db.add_conversation(user_id, "user", message_text)
    
    await update.message.chat.send_action(ChatAction.TYPING)
    
    # Check if user has voice mode enabled
    voice_mode_enabled = False
    voice_name = None
    voice_style = None
    
    if voice_engine.is_configured:
        async with db.get_connection() as conn:
            pref = await conn.fetchrow("""
                SELECT voice_name, voice_style FROM user_voice_preferences
                WHERE user_id = $1
            """, user_id)
            if pref and pref['voice_name']:
                voice_mode_enabled = True
                voice_name = pref['voice_name']
                voice_style = pref.get('voice_style', 'default')
    
    # Use streaming for a live typing effect!
    try:
        # Create the streaming generator
        response_gen = generate_response_streaming(
            user_message=message_text,
            conversation_history=history,
            system_prompt=system_prompt,
            user_name=get_user_display_name(update)
        )
        
        # Stream the response with typing effect
        sent_msg, response = await stream_response_to_message(
            update.message,
            response_gen,
            initial_text="Thinking..."
        )
        
        if not response:
            response = "I apologize, something went wrong. Please try again."
            await safe_reply_text(update.message, response)
            return
            
    except Exception as e:
        # Fallback to non-streaming if streaming fails
        try:
            response = await compound_response(
                user_message=message_text,
                conversation_history=history
            )
        except:
            response = await generate_response(
                user_message=message_text,
                conversation_history=history,
                system_prompt=system_prompt,
                user_name=get_user_display_name(update)
            )
        await safe_reply_text(update.message, response, parse_mode=ParseMode.MARKDOWN)
    
    await db.add_conversation(user_id, "assistant", response)
    await db.increment_stat(user_id, "total_ai_requests")
    await db.add_xp(user_id, 1)
    
    # If voice mode is enabled, also send voice reply
    if voice_mode_enabled and voice_name:
        await update.message.chat.send_action(ChatAction.RECORD_VOICE)
        audio_bytes = await voice_engine.text_to_speech(response, voice=voice_name, style=voice_style)
        
        if audio_bytes:
            await update.message.reply_voice(io.BytesIO(audio_bytes), caption="🎤 Voice reply")


# =====================================================
# INTELLIGENT MEDIA HANDLERS
# =====================================================

async def handle_voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle voice messages - PREMIUM smart assistant!
    """
    if not update.message or not update.message.voice:
        return
    
    user_data = await ensure_user(update)
    user_id = update.effective_user.id
    name = get_user_display_name(update)
    
    # PREMIUM: Show processing with loading
    loading = await update.message.reply_text("🎙 *Listening...*")
    await update.message.chat.send_action(ChatAction.RECORD_VOICE)
    
    # Download voice
    voice = update.message.voice
    voice_file = await voice.get_file()
    voice_bytes = await voice_file.download_as_bytearray()
    
    # Analyze emotions
    emotions = None
    if emotion_engine.is_configured:
        emotions = await emotion_engine.analyze_voice_emotion(bytes(voice_bytes))
    
    # Update loading
    await loading.edit_text("🧠 *Understanding...*")
    await asyncio.sleep(0.5)
    
    # Get voice preference
    voice_name = "Rachel"
    voice_style = "default"
    
    if voice_engine.is_configured:
        async with db.get_connection() as conn:
            pref = await conn.fetchrow("""
                SELECT voice_name, voice_style FROM user_voice_preferences
                WHERE user_id = $1
            """, user_id)
            if pref:
                voice_name = pref.get('voice_name', 'Rachel')
                voice_style = pref.get('voice_style', 'default')
    
    # Smart response based on what user might want
    await loading.edit_text("✨ *Generating reply...*")
    
    # Generate smart response
    response_text = f"Hey {name}! Heard you loud and clear 🔊\n\nWhat would you like me to help with?"
    
    # Send voice reply
    await update.message.chat.send_action(ChatAction.RECORD_VOICE)
    
    if voice_engine.is_configured:
        audio_bytes = await voice_engine.text_to_speech(response_text, voice=voice_name, style=voice_style)
        
        if audio_bytes:
            keyboard = [
                [InlineKeyboardButton("📝 Write Note", callback_data="quick_note"),
                 InlineKeyboardButton("⏰ Reminder", callback_data="quick_reminder")],
                [InlineKeyboardButton("🤖 Build Bot", callback_data="build_bot")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await loading.delete()
            await update.message.reply_voice(
                io.BytesIO(audio_bytes), 
                caption=f"🎙 Hey {name}!"
            )
            await update.message.reply_text(
                f"🎙 *Got your voice!*\n\n"
                f"I can:\n"
                f"• Set reminders & notes\n"
                f"• Build custom bots\n"
                f"• Answer questions\n\n"
                f"||Tap a button or just talk!||",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            return
    
    


async def handle_audio_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle audio files intelligently."""
    if not update.message or not update.message.audio:
        return
    
    user_data = await ensure_user(update)
    user_id = update.effective_user.id
    name = get_user_display_name(update)
    
    audio = update.message.audio
    file_name = audio.file_name or "audio"
    
    # Quick acknowledge with suggestions
    keyboard = [
        [InlineKeyboardButton("🎤 Convert to Voice", callback_data="convert_audio")],
        [InlineKeyboardButton("📝 Transcribe", callback_data="transcribe")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"🎵 Got audio: *{file_name}*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )


async def handle_photo_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle photo/images intelligently - analyze and respond."""
    if not update.message or not update.message.photo:
        return
    
    user_data = await ensure_user(update)
    user_id = update.effective_user.id
    
    # Get the photo
    photo = update.message.photo[-1]  # Get largest photo
    
    # Offer analysis options
    keyboard = [
        [InlineKeyboardButton("🔍 Analyze Image", callback_data="analyze_photo")],
        [InlineKeyboardButton("📝 Extract Text", callback_data="ocr_photo")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🖼 Got your image! I can:\n"
        "• Analyze what's in the image\n"
        "• Extract text from it (OCR)\n\n"
        "What would you like me to do?",
        reply_markup=reply_markup
    )


# =====================================================
# CALLBACK HANDLER
# =====================================================

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle callback queries from inline keyboards."""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = update.effective_user.id
    
    # Quick actions
    if data == "quick_reminder":
        await query.message.reply_text(
            "⏰ `/remind Call mom in 2 hours`",
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif data == "quick_task":
        await query.message.reply_text(
            "✅ `/task Buy groceries`"
        )
    
    elif data == "quick_note":
        await query.message.reply_text(
            "📝 `/note Ideas | Great idea`"
        )
    
    elif data == "build_bot":
        await query.message.reply_text(
            "🤖 `/build a coffee shop bot` or pick a template!"
        )
    
    elif data == "start_chat":
        await query.message.reply_text(
            "💬 Just chat with me! I can help with questions, coding, writing, and more."
        )
    
    elif data == "show_profile":
        # Trigger profile command
        context.args = []
        await profile_command(update, context)
    
    elif data == "show_help":
        context.args = []
        await help_command(update, context)
    
    elif data == "show_leaderboard":
        context.args = []
        await leaderboard_command(update, context)
    
    # Template selection
    elif data.startswith("template_"):
        template_type = data.replace("template_", "")
        templates = await db.get_bot_templates()
        
        type_map = {
            "support": "support",
            "faq": "faq",
            "quiz": "quiz",
            "education": "education",
            "coding": "coding",
            "fitness": "fitness",
            "creative": "creative",
            "assistant": "assistant",
            "wellness": "wellness",
            "cooking": "cooking"
        }
        
        bot_type = type_map.get(template_type, "general")
        matching = [t for t in templates if t.get('bot_type') == bot_type]
        
        if matching:
            template = matching[0]
            await db.update_session_state(user_id, "creating_bot_from_template", {
                "template_id": template['id'],
                "template": template
            })
            
            keyboard = [
                [InlineKeyboardButton("✅ Create Bot", callback_data="confirm_create_bot"),
                 InlineKeyboardButton("🔄 Customize", callback_data="customize_template")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.message.reply_text(
                f"🤖 *{template['name']}*\n\n"
                f"{template.get('description', '')}\n\n"
                f"*Sample greeting:*\n_{template.get('welcome_message', 'Hello!')}_",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
    
    elif data == "create_suggested_bot":
        # Handle creating bot from AI suggestion
        session = await db.get_session(user_id)
        state_data = session.get('state_data', {}) if session else {}
        suggestion = state_data.get('suggestion', {})
        
        if not suggestion:
            await query.message.reply_text("Session expired. Use /build to create a new bot.")
            return
        
        bot_id = await db.create_custom_bot(
            user_id=user_id,
            name=suggestion.get('bot_name', 'Custom Bot'),
            bot_type=suggestion.get('bot_type', 'general'),
            system_prompt=suggestion.get('system_prompt', ''),
            description=suggestion.get('bot_description'),
            welcome_message=suggestion.get('greeting_message'),
            personality=suggestion.get('personality'),
            commands=suggestion.get('commands')
        )
        
        await db.clear_session_state(user_id)
        await db.set_active_bot(user_id, bot_id)  # Auto-activate the new bot
        await db.add_xp(user_id, 25)
        
        bot_name = suggestion.get('bot_name', 'Custom Bot')
        keyboard = [
            [InlineKeyboardButton("💬 Start Chatting", callback_data="start_chat")],
            [InlineKeyboardButton("📝 My Bots", callback_data="menu_mybots")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.reply_text(
            f"✅ *{bot_name}* Created Successfully!\n\n"
            f"Your bot is now active and ready to chat!\n\n"
            f"*How to use:*\n"
            f"• Send any message to start chatting\n"
            f"• Use `/mybots` to manage your bots\n"
            f"• Use `/usebot {bot_id}` to switch bots\n\n"
            f"Bot ID: `{bot_id}`",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )

    elif data == "build_new_suggestion":
        # Get a new suggestion
        session = await db.get_session(user_id)
        state_data = session.get('state_data', {}) if session else {}
        description = state_data.get('description', 'general bot')
        
        await query.message.chat.send_action(ChatAction.TYPING)
        suggestion = await generate_bot_suggestion(description)
        
        if "error" not in suggestion:
            await db.update_session_state(user_id, "awaiting_bot_creation", {"suggestion": suggestion, "description": description})
            
            keyboard = [
                [InlineKeyboardButton("✅ Create Bot", callback_data="create_suggested_bot")],
                [InlineKeyboardButton("🔄 Try Another", callback_data="build_new_suggestion")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Shorter message
            name = suggestion.get('bot_name', 'Custom Bot')
            desc = suggestion.get('bot_description', '')[:120]
            features = suggestion.get('features', [])[:3]
            
            text = f"""🤖 *{name}*

{desc}

*Features:*
• {features[0] if len(features) > 0 else 'Custom responses'}
• {features[1] if len(features) > 1 else 'Smart automation'}
• {features[2] if len(features) > 2 else 'Easy integration'}"""
            
            await query.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)

    elif data == "confirm_create_bot":
        session = await db.get_session(user_id)
        state_data = session.get('state_data', {}) if session else {}
        template = state_data.get('template', {})
        
        if template:
            bot_id = await db.create_custom_bot(
                user_id=user_id,
                name=template.get('name', 'Custom Bot'),
                bot_type=template.get('bot_type', 'general'),
                system_prompt=template.get('system_prompt', ''),
                description=template.get('description'),
                welcome_message=template.get('welcome_message'),
                personality=template.get('personality'),
                commands=template.get('commands')
            )
            
            await db.clear_session_state(user_id)
            await db.add_xp(user_id, 20)
            
            await query.message.reply_text(
                f"✅ *Bot Created!*\n\n"
                f"*{template.get('name')}* is ready!\n\n"
                f"Use: `/usebot {bot_id}`",
                parse_mode=ParseMode.MARKDOWN
            )
    
    elif data == "show_all_templates":
        templates = await db.get_bot_templates()
        text = "📋 *All Bot Templates:*\n\n"
        for t in templates:
            featured = "⭐ " if t.get('is_featured') else ""
            text += f"{featured}*{t['name']}*\n_{t.get('description', '')[:60]}_\n\n"
        
        await query.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    # Quiz answers
    elif data.startswith("quiz_answer_"):
        answer = data.replace("quiz_answer_", "")
        session = await db.get_session(user_id)
        state_data = session.get('state_data', {}) if session else {}
        
        correct = state_data.get('correct', 'A')
        explanation = state_data.get('explanation', '')
        
        await db.clear_session_state(user_id)
        
        if answer == correct:
            xp_result = await db.add_xp(user_id, 15)
            level_up = " 🎉 Level up!" if xp_result.get("level_up") else ""
            await query.message.reply_text(
                f"✅ *Correct!* +15 XP{level_up}\n\n{explanation}",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await query.message.reply_text(
                f"❌ *Incorrect!* The answer was {correct}.\n\n{explanation}",
                parse_mode=ParseMode.MARKDOWN
            )
    
    # Voice selection buttons
    elif data.startswith("setvoice_"):
        voice_name = data.replace("setvoice_", "")
        
        if voice_name not in VoiceEngine.AVAILABLE_VOICES:
            await query.answer("Unknown voice", show_alert=True)
            return
        
        async with db.get_connection() as conn:
            await conn.execute("""
                INSERT INTO user_voice_preferences (user_id, voice_name, updated_at)
                VALUES ($1, $2, NOW())
                ON CONFLICT (user_id) DO UPDATE SET voice_name = $2, updated_at = NOW()
            """, user_id, voice_name)
        
        voice_info = VoiceEngine.AVAILABLE_VOICES[voice_name]
        await query.answer(f"✅ Default voice set to {voice_name}!")
        await query.message.edit_text(
            f"✅ *{voice_name}* is now your default voice!\n\n"
            f"_{voice_info['description']}_",
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif data.startswith("tryvoice_"):
        voice_name = data.replace("tryvoice_", "")
        
        if voice_name not in VoiceEngine.AVAILABLE_VOICES:
            await query.answer("Unknown voice", show_alert=True)
            return
        
        # Generate a short test voice
        test_text = f"Hi! This is {voice_name}. Now you know how I sound!"
        
        await update.message.chat.send_action(ChatAction.RECORD_VOICE)
        
        audio_bytes = await voice_engine.text_to_speech(test_text, voice=voice_name)
        
        if audio_bytes:
            voice_info = VoiceEngine.AVAILABLE_VOICES[voice_name]
            await query.message.reply_voice(io.BytesIO(audio_bytes), caption=f"🎤 {voice_name}: {voice_info['description']}")
            await query.answer("Sent!")
        else:
            await query.answer("Voice generation failed", show_alert=True)


# =====================================================
# VOICE AI HANDLERS (ELEVENLABS)
# =====================================================

async def voice_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generate voice from text using ElevenLabs."""
    await ensure_user(update)
    user_id = update.effective_user.id
    await track_command(user_id, "voice")
    
    if not voice_engine.is_configured:
        await update.message.reply_text(
            "Voice AI is currently not configured.\n\n"
            "The bot admin needs to set the ELEVENLABS_API_KEY."
        )
        return
    
    text = ' '.join(context.args) if context.args else None
    
    if not text:
        # Show voice options
        voices_text = voice_engine.get_available_voices_formatted()
        styles_text = voice_engine.get_voice_styles_formatted()
        
        await update.message.reply_text(
            f"🎙 *Voice Generation*\n\n"
            f"Generate speech from text using AI voices.\n\n"
            f"*Usage:* `/voice <text to speak>`\n"
            f"*With voice:* `/voice Rachel: Hello there!`\n"
            f"*With style:* `/voice Rachel dramatic: This is dramatic!`\n\n"
            f"*Quick Commands:*\n"
            f"• `/voices` - List all voices\n"
            f"• `/setvoice Rachel` - Set default voice\n"
            f"• `/voicestyle expressive` - Set style\n\n"
            f"{voices_text[:1500]}",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    await update.message.chat.send_action(ChatAction.RECORD_VOICE)
    
    # Parse voice and style from text
    voice = None
    style = "default"
    
    # Check for "Voice: text" format
    if ':' in text:
        parts = text.split(':', 1)
        voice_part = parts[0].strip()
        text = parts[1].strip()
        
        # Check for "Voice Style: text" format
        voice_parts = voice_part.split()
        if len(voice_parts) >= 2 and voice_parts[-1].lower() in VoiceEngine.VOICE_STYLES:
            style = voice_parts[-1].lower()
            voice = ' '.join(voice_parts[:-1])
        else:
            voice = voice_part
    
    # Get user preference if no voice specified
    if not voice:
        async with db.get_connection() as conn:
            prefs = await voice_preferences.get_user_preference(conn, user_id)
            voice = prefs.get("voice", "Rachel")
            if style == "default":
                style = prefs.get("style", "default")
    
    # Generate voice
    audio_bytes = await voice_engine.text_to_speech(text[:5000], voice=voice, style=style)
    
    if audio_bytes:
        # Send as voice message
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = "voice.mp3"
        
        await update.message.reply_voice(
            voice=audio_file,
            caption=f"🎙 Generated with *{voice}* ({style})",
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Track usage
        async with db.get_connection() as conn:
            await conn.execute("""
                INSERT INTO voice_generation_history (user_id, voice_name, voice_style, text_length, characters_used)
                VALUES ($1, $2, $3, $4, $5)
            """, user_id, voice, style, len(text), len(text))
        
        await db.add_xp(user_id, 5)
    else:
        await update.message.reply_text(
            "❌ Failed to generate voice. Please try again.\n"
            "Make sure your text is not too long (max 5000 characters)."
        )


async def voices_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List available voices with buttons."""
    await ensure_user(update)
    
    # Create inline keyboard with voice selection buttons
    keyboard = []
    row = []
    voice_names = list(VoiceEngine.AVAILABLE_VOICES.keys())
    
    for i, name in enumerate(voice_names):
        row.append(InlineKeyboardButton(name, callback_data=f"setvoice_{name}"))
        if len(row) == 2 or i == len(voice_names) - 1:
            keyboard.append(row)
            row = []
    
    # Add row for default voices
    keyboard.append([
        InlineKeyboardButton("🎤 Try Rachel", callback_data="tryvoice_Rachel"),
        InlineKeyboardButton("🎤 Try Antoni", callback_data="tryvoice_Antoni")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Short list for the text part (more concise)
    short_list = "\n".join([f"• {name}" for name in voice_names[:6]])
    
    await update.message.reply_text(
        "🎙 *Pick a Voice*\n\n" + short_list + "\n...and more!\n\n"
        "Tap a name above or use `/setvoice <name>`",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )


async def setvoice_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Set user's default voice."""
    await ensure_user(update)
    user_id = update.effective_user.id
    
    if not context.args:
        await update.message.reply_text(
            "Usage: `/setvoice <voice_name>`\n\n"
            "Example: `/setvoice Rachel`\n"
            "Use `/voices` for buttons!",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    voice_name = ' '.join(context.args)
    
    # Validate voice name
    if voice_name not in VoiceEngine.AVAILABLE_VOICES:
        await update.message.reply_text(
            f"Unknown: {voice_name}\n\nUse `/voices` to pick!"
        )
        return
    
    async with db.get_connection() as conn:
        await conn.execute("""
            INSERT INTO user_voice_preferences (user_id, voice_name, updated_at)
            VALUES ($1, $2, NOW())
            ON CONFLICT (user_id) DO UPDATE SET voice_name = $2, updated_at = NOW()
        """, user_id, voice_name)
    
    voice_info = VoiceEngine.AVAILABLE_VOICES[voice_name]
    await update.message.reply_text(
        f"✅ *{voice_name}* set as default!\n_{voice_info['description']}_",
        parse_mode=ParseMode.MARKDOWN
    )


async def voicestyle_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Set user's default voice style."""
    await ensure_user(update)
    user_id = update.effective_user.id
    
    styles = list(VoiceEngine.VOICE_STYLES.keys())
    
    if not context.args:
        style_list = "\n".join([f"• *{s}*" for s in styles])
        await update.message.reply_text(
            f"🎨 *Voice Styles*\n\n{style_list}\n\n"
            f"Usage: `/voicestyle <style>`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    style = context.args[0].lower()
    
    if style not in styles:
        await update.message.reply_text(f"Unknown style. Available: {', '.join(styles)}")
        return
    
    async with db.get_connection() as conn:
        await conn.execute("""
            INSERT INTO user_voice_preferences (user_id, voice_style, updated_at)
            VALUES ($1, $2, NOW())
            ON CONFLICT (user_id) DO UPDATE SET voice_style = $2, updated_at = NOW()
        """, user_id, style)
    
    await update.message.reply_text(f"✅ Voice style set to *{style}*", parse_mode=ParseMode.MARKDOWN)


async def speakthis_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Convert replied message to speech."""
    await ensure_user(update)
    user_id = update.effective_user.id
    
    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to a message with `/speakthis` to convert it to voice.")
        return
    
    if not voice_engine.is_configured:
        await update.message.reply_text("Voice AI is not configured.")
        return
    
    text = update.message.reply_to_message.text or update.message.reply_to_message.caption
    if not text:
        await update.message.reply_text("The replied message has no text content.")
        return
    
    await update.message.chat.send_action(ChatAction.RECORD_VOICE)
    
    # Get user preferences
    async with db.get_connection() as conn:
        prefs = await voice_preferences.get_user_preference(conn, user_id)
    
    audio_bytes = await voice_engine.text_to_speech(
        text[:5000],
        voice=prefs.get("voice", "Rachel"),
        style=prefs.get("style", "default")
    )
    
    if audio_bytes:
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = "voice.mp3"
        await update.message.reply_voice(voice=audio_file)
        await db.add_xp(user_id, 3)
    else:
        await update.message.reply_text("Failed to generate voice. Please try again.")


# =====================================================
# EMOTION AI HANDLERS (HUME)
# =====================================================

async def mood_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Analyze current mood from recent messages or provided text."""
    await ensure_user(update)
    user_id = update.effective_user.id
    await track_command(user_id, "mood")
    
    text = ' '.join(context.args) if context.args else None
    
    if not text:
        # Analyze from recent conversation
        async with db.get_connection() as conn:
            messages = await conn.fetch("""
                SELECT content FROM conversations
                WHERE user_id = $1 AND role = 'user'
                ORDER BY created_at DESC LIMIT 5
            """, user_id)
        
        if not messages:
            await update.message.reply_text(
                "I don't have enough conversation history to analyze your mood.\n\n"
                "Try: `/mood I'm feeling excited about my new project!`"
            )
            return
        
        text = " ".join([m['content'] for m in messages])
    
    await update.message.chat.send_action(ChatAction.TYPING)
    
    # Analyze emotions
    emotions = await emotion_engine.analyze_text_emotion(text)
    
    if not emotions:
        await update.message.reply_text("Could not analyze emotions. Please try again.")
        return
    
    dominant = emotions.get("dominant_emotion", "neutral")
    confidence = emotions.get("confidence", 0)
    top_emotions = emotions.get("top_emotions", {})
    
    # Get emotion info
    emotion_info = EmotionEngine.EMOTION_CATEGORIES.get(dominant, {})
    intensity = emotion_info.get("intensity", "neutral")
    
    # Build response
    intensity_emoji = {"positive": "😊", "negative": "😔", "neutral": "😐"}.get(intensity, "🤔")
    
    top_emotions_text = "\n".join([
        f"• {e.replace('_', ' ').title()}: {s:.0%}"
        for e, s in list(top_emotions.items())[:5]
    ])
    
    response_style = emotions.get("response_style", "supportive")
    
    await update.message.reply_text(
        f"{intensity_emoji} *Emotional Analysis*\n\n"
        f"*Dominant:* {dominant.replace('_', ' ').title()} ({confidence:.0%})\n"
        f"*Intensity:* {intensity.title()}\n\n"
        f"*Detected Emotions:*\n{top_emotions_text}\n\n"
        f"_I'll adjust my responses to be more {response_style}_",
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Store emotional state
    async with db.get_connection() as conn:
        await emotion_engine.update_user_emotional_state(conn, user_id, emotions)
    
    await db.add_xp(user_id, 3)


async def emotions_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """View emotional history and insights."""
    await ensure_user(update)
    user_id = update.effective_user.id
    await track_command(user_id, "emotions")
    
    async with db.get_connection() as conn:
        # Get recent history
        history = await emotion_engine.get_user_emotional_history(conn, user_id, limit=10)
        
        # Get insights
        insights = await emotion_engine.get_emotional_insights(conn, user_id, days=7)
    
    if not history:
        await update.message.reply_text(
            "📊 *Emotional Insights*\n\n"
            "No emotional data yet. Start chatting and I'll learn about your emotional patterns!\n\n"
            "Use `/mood <text>` to analyze specific text.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Format history
    history_text = "\n".join([
        f"• {h['emotion'].replace('_', ' ').title()} ({h['confidence']:.0%}) - {h['time'].strftime('%m/%d %H:%M')}"
        for h in history[:5]
    ])
    
    # Format insights
    wellbeing = insights.get("wellbeing_score", 50)
    wellbeing_bar = "█" * (wellbeing // 10) + "░" * (10 - wellbeing // 10)
    
    sentiment = insights.get("sentiment_breakdown", {})
    
    await update.message.reply_text(
        f"📊 *Emotional Insights (Last 7 Days)*\n\n"
        f"*Wellbeing Score:* {wellbeing}/100\n"
        f"[{wellbeing_bar}]\n\n"
        f"*Sentiment Breakdown:*\n"
        f"😊 Positive: {sentiment.get('positive', '0%')}\n"
        f"😐 Neutral: {sentiment.get('neutral', '0%')}\n"
        f"😔 Negative: {sentiment.get('negative', '0%')}\n\n"
        f"*Most Common:* {insights.get('most_common_emotion', 'N/A').replace('_', ' ').title()}\n"
        f"*Interactions:* {insights.get('total_interactions', 0)}\n\n"
        f"*Recent Emotions:*\n{history_text}",
        parse_mode=ParseMode.MARKDOWN
    )


async def empathy_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Toggle empathic response mode."""
    await ensure_user(update)
    user_id = update.effective_user.id
    
    async with db.get_connection() as conn:
        # Get current setting
        row = await conn.fetchrow("""
            SELECT enable_empathic_responses FROM user_emotion_preferences
            WHERE user_id = $1
        """, user_id)
        
        # Safely access the preference with a default value
        if row is not None:
            current = row.get('enable_empathic_responses', True) if hasattr(row, 'get') else row['enable_empathic_responses']
        else:
            current = True
        new_value = not current
        
        await conn.execute("""
            INSERT INTO user_emotion_preferences (user_id, enable_empathic_responses, updated_at)
            VALUES ($1, $2, NOW())
            ON CONFLICT (user_id) DO UPDATE SET enable_empathic_responses = $2, updated_at = NOW()
        """, user_id, new_value)
    
    status = "enabled" if new_value else "disabled"
    emoji = "💚" if new_value else "⚪"
    
    await update.message.reply_text(
        f"{emoji} *Empathic Responses {status.title()}*\n\n"
        f"{'I will now adapt my tone based on your emotions.' if new_value else 'I will respond in a neutral, consistent tone.'}",
        parse_mode=ParseMode.MARKDOWN
    )


async def wellbeing_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Get a wellbeing check and supportive message."""
    await ensure_user(update)
    user_id = update.effective_user.id
    name = get_user_display_name(update)
    await track_command(user_id, "wellbeing")
    
    await update.message.chat.send_action(ChatAction.TYPING)
    
    async with db.get_connection() as conn:
        insights = await emotion_engine.get_emotional_insights(conn, user_id, days=7)
    
    wellbeing = insights.get("wellbeing_score", 50)
    most_common = insights.get("most_common_emotion", "neutral")
    
    # Generate supportive message based on wellbeing
    if wellbeing >= 70:
        message = (
            f"🌟 *Wellbeing Check for {name}*\n\n"
            f"Your emotional wellbeing looks great! You've been predominantly "
            f"feeling {most_common.replace('_', ' ')} lately.\n\n"
            f"*Score: {wellbeing}/100* ✨\n\n"
            f"Keep up the positive energy! Remember to:\n"
            f"• Celebrate your wins\n"
            f"• Share positivity with others\n"
            f"• Maintain healthy habits"
        )
    elif wellbeing >= 40:
        message = (
            f"💙 *Wellbeing Check for {name}*\n\n"
            f"You're doing okay, with a mix of emotions. "
            f"I've noticed you've been feeling {most_common.replace('_', ' ')} sometimes.\n\n"
            f"*Score: {wellbeing}/100*\n\n"
            f"Some suggestions:\n"
            f"• Take breaks when needed\n"
            f"• Reach out to friends\n"
            f"• Practice self-compassion"
        )
    else:
        message = (
            f"💚 *Wellbeing Check for {name}*\n\n"
            f"It seems like you've been going through some challenging emotions. "
            f"I'm here to support you.\n\n"
            f"*Score: {wellbeing}/100*\n\n"
            f"Remember:\n"
            f"• It's okay to not be okay\n"
            f"• Small steps matter\n"
            f"• You're not alone\n\n"
            f"_Use `/chat` to talk about anything on your mind._"
        )
    
    await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)


async def analyze_voice_emotion(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Analyze emotions from voice message."""
    await ensure_user(update)
    user_id = update.effective_user.id
    
    if not update.message.reply_to_message or not update.message.reply_to_message.voice:
        await update.message.reply_text(
            "Reply to a voice message with `/analyzeemotion` to detect emotions from speech."
        )
        return
    
    if not emotion_engine.is_configured:
        await update.message.reply_text("Emotion AI voice analysis requires Hume AI API key.")
        return
    
    await update.message.chat.send_action(ChatAction.TYPING)
    
    # Download voice message
    voice_file = await update.message.reply_to_message.voice.get_file()
    voice_bytes = await voice_file.download_as_bytearray()
    
    # Analyze
    emotions = await emotion_engine.analyze_voice_emotion(bytes(voice_bytes))
    
    if emotions:
        dominant = emotions.get("dominant_emotion", "unknown")
        confidence = emotions.get("confidence", 0)
        top_emotions = emotions.get("top_emotions", {})
        
        top_text = "\n".join([
            f"• {e.replace('_', ' ').title()}: {s:.0%}"
            for e, s in list(top_emotions.items())[:5]
        ])
        
        await update.message.reply_text(
            f"🎙 *Voice Emotion Analysis*\n\n"
            f"*Detected:* {dominant.replace('_', ' ').title()} ({confidence:.0%})\n\n"
            f"*Emotions:*\n{top_text}",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await update.message.reply_text("Could not analyze voice emotions. Please try a clearer recording.")


# =====================================================
# ERROR HANDLER
# =====================================================

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors in the bot."""
    import logging
    import traceback
    
    # Log the full error details
    error = context.error
    error_message = str(error) if error else "Unknown error"
    error_type = type(error).__name__ if error else "Unknown"
    
    logging.error(f"Exception [{error_type}]: {error_message}")
    if error:
        logging.error(f"Traceback: {''.join(traceback.format_exception(type(error), error, error.__traceback__))}")
    
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "❌ Something went wrong. Please try again.\n\n"
            "If the problem persists, use `/feedback` to report it."
        )
