"""
Waya Bot Builder - Command Handlers Module
All Telegram bot command and message handlers.
"""

import json
import io
from datetime import datetime, timedelta, timezone
from typing import Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes
from telegram.constants import ParseMode, ChatAction

import database as db
from ai_engine import (
    generate_response, generate_bot_suggestion, analyze_message_intent,
    parse_reminder_request, parse_task_request, summarize_text, translate_text,
    generate_quiz_question, get_smart_suggestions, get_bot_system_prompt, WAYA_SYSTEM_PROMPT
)
from voice_engine import voice_engine, voice_preferences, VoiceEngine
from emotion_engine import emotion_engine, EmotionEngine


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
    
    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)


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
    
    if not stats:
        await update.message.reply_text("Could not load your profile. Please try again.")
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

*📈 Statistics:*
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
    
    await update.message.reply_text(
        profile_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )


async def leaderboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /leaderboard command."""
    await track_command(update.effective_user.id, "leaderboard")
    
    async with db.get_connection() as conn:
        rows = await conn.fetch("""
            SELECT u.first_name, u.username, s.xp_points, s.level, s.streak_days
            FROM user_stats s
            JOIN users u ON s.user_id = u.id
            ORDER BY s.xp_points DESC
            LIMIT 10
        """)
    
    if not rows:
        await update.message.reply_text("No users on the leaderboard yet!")
        return
    
    text = "🏆 *Waya Leaderboard*\n\n"
    
    medals = ["🥇", "🥈", "🥉"]
    for i, row in enumerate(rows):
        medal = medals[i] if i < 3 else f"{i+1}."
        name = row['first_name'] or f"@{row['username']}" or "Anonymous"
        text += f"{medal} *{name}*\n"
        text += f"    Level {row['level']} • {row['xp_points']:,} XP • 🔥{row['streak_days']}\n\n"
    
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


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
    """Handle the /build command."""
    await ensure_user(update)
    await track_command(update.effective_user.id, "build")
    
    if context.args:
        # User described what they want
        description = " ".join(context.args)
        await update.message.chat.send_action(ChatAction.TYPING)
        
        suggestion = await generate_bot_suggestion(description)
        
        if "error" not in suggestion:
            keyboard = [
                [InlineKeyboardButton("✅ Create This Bot", callback_data=f"create_suggested_bot")],
                [InlineKeyboardButton("🔄 Different Suggestion", callback_data="build_new_suggestion"),
                 InlineKeyboardButton("📋 Templates", callback_data="show_templates")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Store suggestion in session
            await db.update_session_state(
                update.effective_user.id,
                "awaiting_bot_creation",
                {"suggestion": suggestion}
            )
            
            text = f"""
🤖 *Bot Suggestion*

Based on your description, here's what I recommend:

*Name:* {suggestion.get('bot_name', 'Custom Bot')}
*Type:* {suggestion.get('bot_type', 'general').replace('_', ' ').title()}

*Description:*
{suggestion.get('bot_description', 'A helpful custom bot')}

*Suggested Features:*
"""
            for feature in suggestion.get('features', [])[:5]:
                text += f"• {feature}\n"
            
            text += f"\n*Greeting:*\n_{suggestion.get('greeting_message', 'Hello!')}_"
            
            await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
            return
    
    # Show template options
    keyboard = [
        [InlineKeyboardButton("🛎️ Customer Support", callback_data="template_support"),
         InlineKeyboardButton("❓ FAQ Bot", callback_data="template_faq")],
        [InlineKeyboardButton("🧠 Quiz Master", callback_data="template_quiz"),
         InlineKeyboardButton("📚 Language Tutor", callback_data="template_education")],
        [InlineKeyboardButton("💻 Code Helper", callback_data="template_coding"),
         InlineKeyboardButton("💪 Fitness Coach", callback_data="template_fitness")],
        [InlineKeyboardButton("✍️ Creative Writer", callback_data="template_creative"),
         InlineKeyboardButton("📅 Personal Assistant", callback_data="template_assistant")],
        [InlineKeyboardButton("🧘 Meditation Guide", callback_data="template_wellness"),
         InlineKeyboardButton("🍳 Recipe Chef", callback_data="template_cooking")],
        [InlineKeyboardButton("📋 Browse All Templates", callback_data="show_all_templates")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🤖 *Build a Custom Bot*\n\n"
        "Choose a template to get started, or describe what you want:\n\n"
        "`/build a customer support bot for my coffee shop`\n\n"
        "I'll create a personalized bot configuration for you!",
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
    
    await update.message.reply_text(
        f"🌍 *Translation to {target_lang}:*\n\n"
        f"Original: _{text_to_translate}_\n\n"
        f"Translated: *{translation}*",
        parse_mode=ParseMode.MARKDOWN
    )


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
    
    await update.message.reply_text(
        f"📝 *Summary:*\n\n{summary}",
        parse_mode=ParseMode.MARKDOWN
    )


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
    """Handle incoming text messages."""
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
            
            await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
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
        empathic_mode = pref_row['enable_empathic_responses'] if pref_row else True
    
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
    
    response = await generate_response(
        user_message=message_text,
        conversation_history=history,
        system_prompt=system_prompt,
        user_name=get_user_display_name(update),
        emotion_context=emotion_context,
        empathic_mode=empathic_mode
    )
    
    await db.add_conversation(user_id, "assistant", response)
    await db.increment_stat(user_id, "total_ai_requests")
    await db.add_xp(user_id, 1)
    
    await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)


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
            "⏰ Set a reminder:\n`/remind <what> in <time>`\n\nExample: `/remind Call mom in 2 hours`",
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif data == "quick_task":
        await query.message.reply_text(
            "✅ Create a task:\n`/task <description>`\n\nExample: `/task Buy groceries`",
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif data == "quick_note":
        await query.message.reply_text(
            "📝 Create a note:\n`/note <title> | <content>`\n\nExample: `/note Ideas | Great project concept`",
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif data == "build_bot":
        await query.message.reply_text(
            "🤖 Build a custom bot!\n\nDescribe what you want:\n`/build a friendly customer support bot`\n\nOr browse templates: `/templates`",
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif data == "start_chat":
        await query.message.reply_text(
            "💬 I'm ready to chat!\n\nJust type your message and I'll respond. I can help with questions, writing, coding, and more!",
            parse_mode=ParseMode.MARKDOWN
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
                f"Your *{template.get('name')}* bot is ready!\n\n"
                f"Activate it with: `/usebot {bot_id}`",
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
    
    # Reminder actions
    elif data.startswith("reminder_done_"):
        reminder_id = int(data.replace("reminder_done_", ""))
        await db.complete_reminder(reminder_id, user_id)
        await db.add_xp(user_id, 5)
        await query.message.edit_text("✅ Reminder completed! +5 XP")
    
    elif data.startswith("reminder_snooze_"):
        parts = data.replace("reminder_snooze_", "").split("_")
        reminder_id = int(parts[0])
        minutes = int(parts[1])
        await db.snooze_reminder(reminder_id, user_id, minutes)
        await query.message.edit_text(f"⏰ Snoozed for {minutes} minutes!")


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
    """List available voices."""
    await ensure_user(update)
    
    voices_list = []
    for name, info in VoiceEngine.AVAILABLE_VOICES.items():
        voices_list.append(f"• *{name}*: {info['description']}\n  _{info['use_case']}_")
    
    await update.message.reply_text(
        "🎙 *Available Voices*\n\n" + "\n\n".join(voices_list[:10]) + 
        "\n\n*Usage:* `/voice VoiceName: Your text here`",
        parse_mode=ParseMode.MARKDOWN
    )


async def setvoice_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Set user's default voice."""
    await ensure_user(update)
    user_id = update.effective_user.id
    
    if not context.args:
        await update.message.reply_text(
            "Usage: `/setvoice <voice_name>`\n\n"
            "Example: `/setvoice Rachel`\n"
            "Use `/voices` to see available voices.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    voice_name = ' '.join(context.args)
    
    # Validate voice name
    if voice_name not in VoiceEngine.AVAILABLE_VOICES:
        await update.message.reply_text(
            f"Unknown voice: {voice_name}\n\n"
            "Use `/voices` to see available voices."
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
        f"✅ Default voice set to *{voice_name}*\n\n"
        f"_{voice_info['description']}_",
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
        
        current = row['enable_empathic_responses'] if row else True
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
    logging.error(f"Exception: {context.error}", exc_info=context.error)
    
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "❌ Something went wrong. Please try again.\n\n"
            "If the problem persists, use `/feedback` to report it."
        )
