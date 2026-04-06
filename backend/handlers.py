"""
Waya Bot Builder - Command Handlers Module
All Telegram bot command and message handlers.
"""

import json
from datetime import datetime, timedelta
from typing import Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes
from telegram.constants import ParseMode, ChatAction

from database import (
    get_or_create_user, update_user_stats, add_conversation, get_conversation_history,
    clear_conversation_history, create_reminder, get_pending_reminders, delete_reminder,
    mark_reminder_complete, create_note, get_user_notes, delete_note, create_task,
    get_user_tasks, update_task_status, delete_task, create_custom_bot, get_user_bots,
    get_bot_templates, update_custom_bot, create_ai_personality, get_user_personalities,
    set_active_personality, get_active_personality, log_analytics, get_user_analytics,
    create_poll, vote_poll, get_poll_results, get_user_settings, update_user_settings
)

from ai_engine import (
    generate_response, generate_bot_suggestion, analyze_message_intent,
    parse_reminder_request, parse_task_request, summarize_text, translate_text,
    generate_quiz_question, get_smart_suggestions, get_bot_system_prompt
)


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
    return await get_or_create_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        language_code=user.language_code or 'en',
        is_premium=user.is_premium or False
    )


# ==================== MAIN COMMANDS ====================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /start command."""
    user_data = await ensure_user(update)
    await update_user_stats(update.effective_user.id, command=True)
    await log_analytics(update.effective_user.id, "command_start")
    
    name = get_user_display_name(update)
    
    welcome_message = f"""
🤖 *Welcome to Waya, {name}!*

I'm your intelligent bot builder and personal AI assistant, powered by advanced AI to help you with anything you need.

*What I can do for you:*

📝 *Productivity*
• Set reminders and alarms
• Create and manage notes
• Track tasks and to-dos
• Schedule messages

🤖 *Bot Building*
• Create custom Telegram bots
• Configure bot behaviors
• Use pre-built templates
• Design conversation flows

🧠 *AI Features*
• Answer any questions
• Translate languages
• Summarize texts
• Generate content

📊 *More Features*
• Create polls
• Get smart suggestions
• Analyze data
• Custom AI personalities

*Quick Start Commands:*
/help - See all commands
/remind - Set a reminder
/note - Create a note
/task - Add a task
/build - Build a custom bot
/chat - Just talk to me!

Let's get started! What would you like to do?
"""
    
    keyboard = [
        [InlineKeyboardButton("📝 Set Reminder", callback_data="quick_reminder"),
         InlineKeyboardButton("📋 Add Task", callback_data="quick_task")],
        [InlineKeyboardButton("🤖 Build a Bot", callback_data="build_bot"),
         InlineKeyboardButton("📄 Create Note", callback_data="quick_note")],
        [InlineKeyboardButton("💬 Chat with AI", callback_data="start_chat"),
         InlineKeyboardButton("❓ Get Help", callback_data="show_help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        welcome_message,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /help command."""
    await update_user_stats(update.effective_user.id, command=True)
    
    help_text = """
📚 *Waya Command Reference*

*Basic Commands:*
/start - Start the bot
/help - Show this help message
/menu - Show main menu
/settings - Your settings
/stats - View your statistics

*Reminders:*
/remind <text> - Set a reminder
/reminders - List your reminders
/delreminder <id> - Delete a reminder

*Notes:*
/note <title> | <content> - Create a note
/notes - List your notes
/searchnotes <query> - Search notes
/delnote <id> - Delete a note

*Tasks:*
/task <title> - Create a task
/tasks - List your tasks
/done <id> - Mark task complete
/deltask <id> - Delete a task

*Bot Building:*
/build - Start building a bot
/mybots - View your custom bots
/templates - Browse bot templates
/editbot <id> - Edit a bot

*AI Features:*
/chat - Start AI conversation
/clear - Clear conversation history
/translate <lang> <text> - Translate text
/summarize <text> - Summarize text
/quiz <topic> - Generate a quiz question

*Personality:*
/personalities - View AI personalities
/setpersonality <id> - Set active personality
/newpersonality - Create new personality

*Polls:*
/poll <question> | <opt1> | <opt2>... - Create poll
/pollresults <id> - View poll results

*Other:*
/suggest - Get smart suggestions
/feedback <text> - Send feedback

💡 *Tip:* You can also just chat with me naturally!
"""
    
    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)


async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /menu command - show main menu."""
    await update_user_stats(update.effective_user.id, command=True)
    
    keyboard = [
        [KeyboardButton("📝 Reminders"), KeyboardButton("📋 Tasks")],
        [KeyboardButton("📄 Notes"), KeyboardButton("🤖 My Bots")],
        [KeyboardButton("💬 Chat"), KeyboardButton("📊 Stats")],
        [KeyboardButton("⚙️ Settings"), KeyboardButton("❓ Help")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "📱 *Main Menu*\n\nChoose an option below:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )


# ==================== REMINDER COMMANDS ====================

async def remind_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /remind command."""
    await ensure_user(update)
    await update_user_stats(update.effective_user.id, command=True)
    
    if not context.args:
        await update.message.reply_text(
            "📝 *Set a Reminder*\n\n"
            "Usage: `/remind <what to remind>`\n\n"
            "Examples:\n"
            "• `/remind Call mom in 2 hours`\n"
            "• `/remind Meeting tomorrow at 3pm`\n"
            "• `/remind Take medicine at 9am daily`\n\n"
            "I'll understand natural language for dates and times!",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    reminder_text = " ".join(context.args)
    
    await update.message.chat.send_action(ChatAction.TYPING)
    
    # Parse the reminder using AI
    parsed = await parse_reminder_request(reminder_text)
    
    if "error" in parsed:
        await update.message.reply_text(
            f"❌ Sorry, I couldn't understand that reminder. Please try again with a clearer format.\n\n"
            f"Example: `/remind Call John tomorrow at 2pm`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    try:
        remind_at = datetime.fromisoformat(parsed["datetime"])
        reminder_msg = parsed.get("reminder_text", reminder_text)
        repeat = parsed.get("repeat")
        
        reminder_id = await create_reminder(
            user_id=update.effective_user.id,
            message=reminder_msg,
            remind_at=remind_at,
            repeat_type=repeat if repeat and repeat != "none" else None
        )
        
        await log_analytics(update.effective_user.id, "reminder_created", {"id": reminder_id})
        
        repeat_text = f"\n🔄 Repeats: {repeat}" if repeat and repeat != "none" else ""
        
        await update.message.reply_text(
            f"✅ *Reminder Set!*\n\n"
            f"📝 {reminder_msg}\n"
            f"⏰ {remind_at.strftime('%B %d, %Y at %I:%M %p')}{repeat_text}\n\n"
            f"I'll remind you when it's time! (ID: {reminder_id})",
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        await update.message.reply_text(
            f"❌ Error creating reminder: {str(e)}\n\nPlease try again.",
            parse_mode=ParseMode.MARKDOWN
        )


async def reminders_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /reminders command."""
    await ensure_user(update)
    await update_user_stats(update.effective_user.id, command=True)
    
    reminders = await get_pending_reminders(update.effective_user.id)
    
    if not reminders:
        await update.message.reply_text(
            "📭 You don't have any pending reminders.\n\n"
            "Use `/remind <text>` to create one!",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    text = "📝 *Your Reminders:*\n\n"
    for r in reminders:
        remind_at = datetime.fromisoformat(r['remind_at'])
        repeat = f" (🔄 {r['repeat_type']})" if r['repeat_type'] else ""
        text += f"*{r['id']}.* {r['message']}\n"
        text += f"   ⏰ {remind_at.strftime('%b %d, %Y %I:%M %p')}{repeat}\n\n"
    
    text += "\n_Use `/delreminder <id>` to delete a reminder_"
    
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def del_reminder_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /delreminder command."""
    await update_user_stats(update.effective_user.id, command=True)
    
    if not context.args:
        await update.message.reply_text(
            "Usage: `/delreminder <id>`\n\nUse `/reminders` to see your reminder IDs.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    try:
        reminder_id = int(context.args[0])
        success = await delete_reminder(reminder_id, update.effective_user.id)
        
        if success:
            await update.message.reply_text(f"✅ Reminder {reminder_id} deleted!")
        else:
            await update.message.reply_text("❌ Reminder not found or already deleted.")
    except ValueError:
        await update.message.reply_text("❌ Please provide a valid reminder ID.")


# ==================== NOTE COMMANDS ====================

async def note_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /note command."""
    await ensure_user(update)
    await update_user_stats(update.effective_user.id, command=True)
    
    if not context.args:
        await update.message.reply_text(
            "📄 *Create a Note*\n\n"
            "Usage: `/note <title> | <content>`\n\n"
            "Example:\n"
            "`/note Meeting Notes | Discussed project timeline and budget`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    text = " ".join(context.args)
    parts = text.split("|", 1)
    
    title = parts[0].strip()
    content = parts[1].strip() if len(parts) > 1 else ""
    
    if not content:
        content = title
        title = f"Note {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    
    note_id = await create_note(
        user_id=update.effective_user.id,
        title=title,
        content=content
    )
    
    await log_analytics(update.effective_user.id, "note_created", {"id": note_id})
    
    await update.message.reply_text(
        f"✅ *Note Saved!*\n\n"
        f"📌 *{title}*\n{content[:200]}{'...' if len(content) > 200 else ''}\n\n"
        f"ID: {note_id}",
        parse_mode=ParseMode.MARKDOWN
    )


async def notes_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /notes command."""
    await ensure_user(update)
    await update_user_stats(update.effective_user.id, command=True)
    
    notes = await get_user_notes(update.effective_user.id)
    
    if not notes:
        await update.message.reply_text(
            "📭 You don't have any notes yet.\n\n"
            "Use `/note <title> | <content>` to create one!",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    text = "📄 *Your Notes:*\n\n"
    for n in notes[:10]:  # Show first 10
        text += f"*{n['id']}.* {n['title']}\n"
        preview = n['content'][:50] + "..." if len(n['content']) > 50 else n['content']
        text += f"   _{preview}_\n\n"
    
    if len(notes) > 10:
        text += f"\n_...and {len(notes) - 10} more notes_"
    
    text += "\n\n_Use `/searchnotes <query>` to search_"
    
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def search_notes_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /searchnotes command."""
    await update_user_stats(update.effective_user.id, command=True)
    
    if not context.args:
        await update.message.reply_text(
            "Usage: `/searchnotes <query>`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    query = " ".join(context.args)
    notes = await get_user_notes(update.effective_user.id, search=query)
    
    if not notes:
        await update.message.reply_text(f"📭 No notes found matching '{query}'")
        return
    
    text = f"🔍 *Notes matching '{query}':*\n\n"
    for n in notes:
        text += f"*{n['id']}.* {n['title']}\n"
        preview = n['content'][:50] + "..." if len(n['content']) > 50 else n['content']
        text += f"   _{preview}_\n\n"
    
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def del_note_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /delnote command."""
    await update_user_stats(update.effective_user.id, command=True)
    
    if not context.args:
        await update.message.reply_text("Usage: `/delnote <id>`", parse_mode=ParseMode.MARKDOWN)
        return
    
    try:
        note_id = int(context.args[0])
        success = await delete_note(note_id, update.effective_user.id)
        
        if success:
            await update.message.reply_text(f"✅ Note {note_id} deleted!")
        else:
            await update.message.reply_text("❌ Note not found.")
    except ValueError:
        await update.message.reply_text("❌ Please provide a valid note ID.")


# ==================== TASK COMMANDS ====================

async def task_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /task command."""
    await ensure_user(update)
    await update_user_stats(update.effective_user.id, command=True)
    
    if not context.args:
        await update.message.reply_text(
            "📋 *Create a Task*\n\n"
            "Usage: `/task <task description>`\n\n"
            "Examples:\n"
            "• `/task Buy groceries`\n"
            "• `/task Finish report by Friday high priority`\n"
            "• `/task Call client tomorrow`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    task_text = " ".join(context.args)
    
    await update.message.chat.send_action(ChatAction.TYPING)
    
    # Parse the task using AI
    parsed = await parse_task_request(task_text)
    
    title = parsed.get("title", task_text)
    description = parsed.get("description")
    priority = parsed.get("priority", "medium")
    due_date = None
    
    if parsed.get("due_date"):
        try:
            due_date = datetime.fromisoformat(parsed["due_date"])
        except:
            pass
    
    task_id = await create_task(
        user_id=update.effective_user.id,
        title=title,
        description=description,
        due_date=due_date,
        priority=priority
    )
    
    await log_analytics(update.effective_user.id, "task_created", {"id": task_id})
    
    priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(priority, "🟡")
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
    await update_user_stats(update.effective_user.id, command=True)
    
    tasks = await get_user_tasks(update.effective_user.id)
    
    if not tasks:
        await update.message.reply_text(
            "📭 You don't have any tasks.\n\n"
            "Use `/task <description>` to create one!",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    pending = [t for t in tasks if t['status'] == 'pending']
    completed = [t for t in tasks if t['status'] == 'completed']
    
    text = "📋 *Your Tasks:*\n\n"
    
    if pending:
        text += "*Pending:*\n"
        for t in pending:
            priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(t['priority'], "🟡")
            due = ""
            if t['due_date']:
                due_dt = datetime.fromisoformat(t['due_date'])
                due = f" (📅 {due_dt.strftime('%b %d')})"
            text += f"  {priority_emoji} *{t['id']}.* {t['title']}{due}\n"
    
    if completed:
        text += f"\n*Completed ({len(completed)}):*\n"
        for t in completed[:5]:
            text += f"  ✅ ~~{t['title']}~~\n"
    
    text += "\n_Use `/done <id>` to complete a task_"
    
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def done_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /done command."""
    await update_user_stats(update.effective_user.id, command=True)
    
    if not context.args:
        await update.message.reply_text("Usage: `/done <task_id>`", parse_mode=ParseMode.MARKDOWN)
        return
    
    try:
        task_id = int(context.args[0])
        success = await update_task_status(task_id, update.effective_user.id, "completed")
        
        if success:
            await update.message.reply_text(f"✅ Task {task_id} marked as complete! Great job! 🎉")
        else:
            await update.message.reply_text("❌ Task not found.")
    except ValueError:
        await update.message.reply_text("❌ Please provide a valid task ID.")


async def del_task_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /deltask command."""
    await update_user_stats(update.effective_user.id, command=True)
    
    if not context.args:
        await update.message.reply_text("Usage: `/deltask <id>`", parse_mode=ParseMode.MARKDOWN)
        return
    
    try:
        task_id = int(context.args[0])
        success = await delete_task(task_id, update.effective_user.id)
        
        if success:
            await update.message.reply_text(f"✅ Task {task_id} deleted!")
        else:
            await update.message.reply_text("❌ Task not found.")
    except ValueError:
        await update.message.reply_text("❌ Please provide a valid task ID.")


# ==================== BOT BUILDING COMMANDS ====================

async def build_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /build command - start building a custom bot."""
    await ensure_user(update)
    await update_user_stats(update.effective_user.id, command=True)
    
    if not context.args:
        keyboard = [
            [InlineKeyboardButton("🛎️ Customer Support", callback_data="build_customer_support"),
             InlineKeyboardButton("❓ FAQ Bot", callback_data="build_faq")],
            [InlineKeyboardButton("📅 Personal Assistant", callback_data="build_personal_assistant"),
             InlineKeyboardButton("🎯 Quiz Bot", callback_data="build_quiz_master")],
            [InlineKeyboardButton("✍️ Creative Writer", callback_data="build_creative_writer"),
             InlineKeyboardButton("💻 Code Helper", callback_data="build_code_helper")],
            [InlineKeyboardButton("🌍 Language Tutor", callback_data="build_language_tutor"),
             InlineKeyboardButton("🎨 Custom Bot", callback_data="build_custom")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🤖 *Bot Builder*\n\n"
            "Choose a bot template to get started, or describe what kind of bot you want to build:\n\n"
            "Example: `/build a customer support bot for my online store`",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
        return
    
    # User described what they want - use AI to suggest
    description = " ".join(context.args)
    
    await update.message.chat.send_action(ChatAction.TYPING)
    
    suggestion = await generate_bot_suggestion(description)
    
    if "error" in suggestion:
        await update.message.reply_text(
            "❌ Sorry, I had trouble understanding your request. Please try again or choose a template.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Store suggestion in context for later use
    context.user_data['bot_suggestion'] = suggestion
    
    features = "\n".join([f"  • {f}" for f in suggestion.get('features', [])[:5]])
    commands = ", ".join(suggestion.get('suggested_commands', [])[:5])
    
    keyboard = [
        [InlineKeyboardButton("✅ Create This Bot", callback_data="confirm_bot_creation")],
        [InlineKeyboardButton("✏️ Customize", callback_data="customize_bot"),
         InlineKeyboardButton("❌ Cancel", callback_data="cancel_bot")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"🤖 *Bot Suggestion*\n\n"
        f"*Name:* {suggestion.get('bot_name', 'Custom Bot')}\n"
        f"*Type:* {suggestion.get('bot_type', 'general').replace('_', ' ').title()}\n"
        f"*Description:* {suggestion.get('bot_description', 'A custom bot')}\n\n"
        f"*Suggested Features:*\n{features}\n\n"
        f"*Commands:* {commands}\n\n"
        f"*Greeting:* _{suggestion.get('greeting_message', 'Hello!')}_\n\n"
        "Would you like to create this bot?",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )


async def my_bots_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /mybots command."""
    await ensure_user(update)
    await update_user_stats(update.effective_user.id, command=True)
    
    bots = await get_user_bots(update.effective_user.id)
    
    if not bots:
        await update.message.reply_text(
            "📭 You haven't created any bots yet.\n\n"
            "Use `/build` to create your first bot!",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    text = "🤖 *Your Custom Bots:*\n\n"
    for bot in bots:
        status = "🟢 Active" if bot['is_active'] else "🔴 Inactive"
        text += f"*{bot['id']}.* {bot['bot_name']}\n"
        text += f"   Type: {bot['bot_type'].replace('_', ' ').title()}\n"
        text += f"   Status: {status}\n\n"
    
    text += "_Use `/editbot <id>` to modify a bot_"
    
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def templates_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /templates command."""
    await update_user_stats(update.effective_user.id, command=True)
    
    templates = await get_bot_templates()
    
    text = "📋 *Bot Templates:*\n\n"
    
    categories = {}
    for t in templates:
        cat = t['category'].title()
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(t)
    
    for cat, tmps in categories.items():
        text += f"*{cat}:*\n"
        for t in tmps:
            text += f"  • {t['name']}\n"
        text += "\n"
    
    text += "_Use `/build <template name>` to start with a template_"
    
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


# ==================== AI CHAT COMMANDS ====================

async def chat_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /chat command - start AI conversation mode."""
    await ensure_user(update)
    await update_user_stats(update.effective_user.id, command=True)
    
    context.user_data['chat_mode'] = True
    
    await update.message.reply_text(
        "💬 *Chat Mode Activated*\n\n"
        "I'm ready to chat! Ask me anything or tell me what you need.\n\n"
        "Commands still work in chat mode:\n"
        "• `/clear` - Clear conversation history\n"
        "• `/end` - End chat mode\n"
        "• `/personality` - Change AI personality",
        parse_mode=ParseMode.MARKDOWN
    )


async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /clear command."""
    await clear_conversation_history(update.effective_user.id)
    await update.message.reply_text("🗑️ Conversation history cleared! Let's start fresh.")


async def translate_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /translate command."""
    await update_user_stats(update.effective_user.id, command=True)
    
    if len(context.args) < 2:
        await update.message.reply_text(
            "🌍 *Translate Text*\n\n"
            "Usage: `/translate <language> <text>`\n\n"
            "Example:\n"
            "`/translate Spanish Hello, how are you?`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    language = context.args[0]
    text = " ".join(context.args[1:])
    
    await update.message.chat.send_action(ChatAction.TYPING)
    
    translation = await translate_text(text, language)
    
    await update.message.reply_text(
        f"🌍 *Translation to {language}:*\n\n{translation}",
        parse_mode=ParseMode.MARKDOWN
    )


async def summarize_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /summarize command."""
    await update_user_stats(update.effective_user.id, command=True)
    
    if not context.args:
        await update.message.reply_text(
            "📝 *Summarize Text*\n\n"
            "Usage: `/summarize <text>`\n\n"
            "Or reply to a message with `/summarize`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    text = " ".join(context.args)
    
    await update.message.chat.send_action(ChatAction.TYPING)
    
    summary = await summarize_text(text)
    
    await update.message.reply_text(
        f"📝 *Summary:*\n\n{summary}",
        parse_mode=ParseMode.MARKDOWN
    )


async def quiz_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /quiz command."""
    await update_user_stats(update.effective_user.id, command=True)
    
    if not context.args:
        await update.message.reply_text(
            "🎯 *Generate Quiz Question*\n\n"
            "Usage: `/quiz <topic>`\n\n"
            "Example: `/quiz Python programming`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    topic = " ".join(context.args)
    
    await update.message.chat.send_action(ChatAction.TYPING)
    
    quiz = await generate_quiz_question(topic)
    
    if "error" in quiz:
        await update.message.reply_text("❌ Couldn't generate a quiz question. Please try again.")
        return
    
    # Store correct answer for later
    context.user_data['quiz_answer'] = quiz.get('correct_answer')
    context.user_data['quiz_explanation'] = quiz.get('explanation')
    
    options = "\n".join(quiz.get('options', []))
    
    keyboard = [
        [InlineKeyboardButton("A", callback_data="quiz_A"),
         InlineKeyboardButton("B", callback_data="quiz_B"),
         InlineKeyboardButton("C", callback_data="quiz_C"),
         InlineKeyboardButton("D", callback_data="quiz_D")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"🎯 *Quiz Time!*\n\n"
        f"*{quiz.get('question', 'Question')}*\n\n"
        f"{options}\n\n"
        f"Select your answer:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )


# ==================== PERSONALITY COMMANDS ====================

async def personalities_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /personalities command."""
    await ensure_user(update)
    await update_user_stats(update.effective_user.id, command=True)
    
    personalities = await get_user_personalities(update.effective_user.id)
    
    default_text = "🎭 *AI Personalities:*\n\n*Default:*\n  • Waya (Default Assistant)\n\n"
    
    if not personalities:
        await update.message.reply_text(
            default_text +
            "You haven't created any custom personalities yet.\n\n"
            "Use `/newpersonality` to create one!",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    text = default_text + "*Your Personalities:*\n"
    for p in personalities:
        active = " ✓" if p['is_active'] else ""
        text += f"  • *{p['id']}.* {p['name']}{active}\n"
    
    text += "\n_Use `/setpersonality <id>` to switch_"
    
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def new_personality_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /newpersonality command."""
    await ensure_user(update)
    context.user_data['creating_personality'] = True
    
    await update.message.reply_text(
        "🎭 *Create New AI Personality*\n\n"
        "Please provide the following in this format:\n\n"
        "`Name | System Prompt`\n\n"
        "Example:\n"
        "`Friendly Teacher | You are a patient and encouraging teacher who explains concepts simply and celebrates learning.`",
        parse_mode=ParseMode.MARKDOWN
    )


async def set_personality_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /setpersonality command."""
    await update_user_stats(update.effective_user.id, command=True)
    
    if not context.args:
        await update.message.reply_text(
            "Usage: `/setpersonality <id>`\n\nUse `/personalities` to see available options.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    try:
        personality_id = int(context.args[0])
        success = await set_active_personality(update.effective_user.id, personality_id)
        
        if success:
            await update.message.reply_text(f"✅ Personality switched! I'll now use this personality in our conversations.")
        else:
            await update.message.reply_text("❌ Personality not found.")
    except ValueError:
        await update.message.reply_text("❌ Please provide a valid personality ID.")


# ==================== POLL COMMANDS ====================

async def poll_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /poll command."""
    await ensure_user(update)
    await update_user_stats(update.effective_user.id, command=True)
    
    if not context.args:
        await update.message.reply_text(
            "📊 *Create a Poll*\n\n"
            "Usage: `/poll <question> | <option1> | <option2> | ...`\n\n"
            "Example:\n"
            "`/poll What's your favorite color? | Red | Blue | Green | Yellow`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    text = " ".join(context.args)
    parts = [p.strip() for p in text.split("|")]
    
    if len(parts) < 3:
        await update.message.reply_text(
            "❌ Please provide a question and at least 2 options separated by |",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    question = parts[0]
    options = parts[1:]
    
    poll_id = await create_poll(
        user_id=update.effective_user.id,
        question=question,
        options=options
    )
    
    # Create inline keyboard for voting
    keyboard = []
    for i, opt in enumerate(options):
        keyboard.append([InlineKeyboardButton(opt, callback_data=f"vote_{poll_id}_{i}")])
    keyboard.append([InlineKeyboardButton("📊 View Results", callback_data=f"poll_results_{poll_id}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"📊 *Poll Created!*\n\n*{question}*\n\nVote below:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )


async def poll_results_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /pollresults command."""
    await update_user_stats(update.effective_user.id, command=True)
    
    if not context.args:
        await update.message.reply_text("Usage: `/pollresults <poll_id>`", parse_mode=ParseMode.MARKDOWN)
        return
    
    try:
        poll_id = int(context.args[0])
        results = await get_poll_results(poll_id)
        
        if not results:
            await update.message.reply_text("❌ Poll not found.")
            return
        
        text = f"📊 *Poll Results*\n\n*{results['question']}*\n\n"
        
        total = sum(results['vote_counts'])
        for i, (opt, count) in enumerate(zip(results['options'], results['vote_counts'])):
            pct = (count / total * 100) if total > 0 else 0
            bar = "█" * int(pct / 10) + "░" * (10 - int(pct / 10))
            text += f"{opt}\n{bar} {count} ({pct:.1f}%)\n\n"
        
        text += f"_Total voters: {results['total_voters']}_"
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    except ValueError:
        await update.message.reply_text("❌ Please provide a valid poll ID.")


# ==================== STATS & SETTINGS COMMANDS ====================

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /stats command."""
    await ensure_user(update)
    await update_user_stats(update.effective_user.id, command=True)
    
    analytics = await get_user_analytics(update.effective_user.id)
    
    text = f"📊 *Your Statistics*\n\n"
    text += f"💬 Messages sent: {analytics['total_messages']}\n"
    text += f"⌨️ Commands used: {analytics['total_commands']}\n"
    
    if analytics.get('member_since'):
        text += f"📅 Member since: {analytics['member_since'][:10]}\n"
    
    if analytics.get('events'):
        text += "\n*Activity (last 30 days):*\n"
        for event, count in list(analytics['events'].items())[:5]:
            text += f"  • {event.replace('_', ' ').title()}: {count}\n"
    
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /settings command."""
    await ensure_user(update)
    await update_user_stats(update.effective_user.id, command=True)
    
    settings = await get_user_settings(update.effective_user.id)
    
    keyboard = [
        [InlineKeyboardButton(
            f"{'🔔' if settings.get('notifications', True) else '🔕'} Notifications",
            callback_data="toggle_notifications"
        )],
        [InlineKeyboardButton(
            f"{'🌙' if settings.get('quiet_hours', False) else '☀️'} Quiet Hours",
            callback_data="toggle_quiet_hours"
        )],
        [InlineKeyboardButton("🌐 Language", callback_data="change_language")],
        [InlineKeyboardButton("🎭 AI Personality", callback_data="change_personality")],
        [InlineKeyboardButton("🗑️ Clear All Data", callback_data="clear_all_data")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "⚙️ *Settings*\n\nConfigure your preferences:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )


async def suggest_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /suggest command - get smart suggestions."""
    await ensure_user(update)
    await update_user_stats(update.effective_user.id, command=True)
    
    await update.message.chat.send_action(ChatAction.TYPING)
    
    # Gather user context
    reminders = await get_pending_reminders(update.effective_user.id)
    tasks = await get_user_tasks(update.effective_user.id, status="pending")
    analytics = await get_user_analytics(update.effective_user.id)
    
    user_context = {
        "pending_reminders": len(reminders),
        "pending_tasks": len(tasks),
        "total_messages": analytics['total_messages'],
        "recent_activity": list(analytics.get('events', {}).keys())[:5],
        "time_of_day": datetime.now().strftime("%H:%M"),
        "day_of_week": datetime.now().strftime("%A")
    }
    
    suggestions = await get_smart_suggestions(user_context)
    
    text = "💡 *Smart Suggestions*\n\n"
    for i, suggestion in enumerate(suggestions, 1):
        text += f"{i}. {suggestion}\n"
    
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def feedback_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /feedback command."""
    await update_user_stats(update.effective_user.id, command=True)
    
    if not context.args:
        await update.message.reply_text(
            "📝 *Send Feedback*\n\n"
            "Usage: `/feedback <your message>`\n\n"
            "I appreciate all feedback to help improve!",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    feedback = " ".join(context.args)
    await log_analytics(update.effective_user.id, "feedback", {"message": feedback})
    
    await update.message.reply_text(
        "✅ Thank you for your feedback! I'll use it to improve. 🙏",
        parse_mode=ParseMode.MARKDOWN
    )


# ==================== MESSAGE HANDLER ====================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle all text messages."""
    if not update.message or not update.message.text:
        return
    
    user_data = await ensure_user(update)
    await update_user_stats(update.effective_user.id, message=True)
    
    message = update.message.text
    
    # Check for keyboard button presses
    button_handlers = {
        "📝 Reminders": reminders_command,
        "📋 Tasks": tasks_command,
        "📄 Notes": notes_command,
        "🤖 My Bots": my_bots_command,
        "💬 Chat": chat_command,
        "📊 Stats": stats_command,
        "⚙️ Settings": settings_command,
        "❓ Help": help_command
    }
    
    if message in button_handlers:
        await button_handlers[message](update, context)
        return
    
    # Check if creating personality
    if context.user_data.get('creating_personality'):
        context.user_data['creating_personality'] = False
        parts = message.split("|", 1)
        if len(parts) == 2:
            name = parts[0].strip()
            prompt = parts[1].strip()
            personality_id = await create_ai_personality(
                update.effective_user.id, name, prompt
            )
            await update.message.reply_text(
                f"✅ Personality '{name}' created! (ID: {personality_id})\n\n"
                f"Use `/setpersonality {personality_id}` to activate it.",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await update.message.reply_text(
                "❌ Invalid format. Please use: `Name | System Prompt`",
                parse_mode=ParseMode.MARKDOWN
            )
        return
    
    # Default: AI chat response
    await update.message.chat.send_action(ChatAction.TYPING)
    
    # Get conversation history
    history = await get_conversation_history(update.effective_user.id)
    
    # Get active personality
    personality = await get_active_personality(update.effective_user.id)
    system_prompt = personality['system_prompt'] if personality else None
    temperature = personality['temperature'] if personality else 0.7
    
    # Generate response
    name = get_user_display_name(update)
    response = await generate_response(
        user_message=message,
        conversation_history=history,
        system_prompt=system_prompt,
        user_name=name,
        temperature=temperature
    )
    
    # Save to conversation history
    await add_conversation(update.effective_user.id, "user", message)
    await add_conversation(update.effective_user.id, "assistant", response)
    
    await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)


# ==================== CALLBACK HANDLER ====================

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle callback queries from inline keyboards."""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = update.effective_user.id
    
    # Quick action callbacks
    if data == "quick_reminder":
        await query.message.reply_text(
            "📝 To set a reminder, use:\n`/remind <what to remind>`\n\n"
            "Example: `/remind Call mom in 2 hours`",
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif data == "quick_task":
        await query.message.reply_text(
            "📋 To add a task, use:\n`/task <task description>`\n\n"
            "Example: `/task Buy groceries`",
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif data == "quick_note":
        await query.message.reply_text(
            "📄 To create a note, use:\n`/note <title> | <content>`\n\n"
            "Example: `/note Meeting Notes | Discussed timeline`",
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif data == "build_bot":
        await query.message.reply_text(
            "🤖 To build a bot, use:\n`/build <description>`\n\n"
            "Or use `/build` to see templates!",
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif data == "start_chat":
        context.user_data['chat_mode'] = True
        await query.message.reply_text(
            "💬 Chat mode activated! Just type your message and I'll respond.",
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif data == "show_help":
        await query.message.reply_text(
            "Use /help to see all available commands!",
            parse_mode=ParseMode.MARKDOWN
        )
    
    # Bot building callbacks
    elif data.startswith("build_"):
        bot_type = data.replace("build_", "")
        if bot_type == "custom":
            await query.message.reply_text(
                "🎨 Describe the custom bot you want to build:\n\n"
                "Example: `/build A bot that helps users track their daily habits`",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            # Create bot with template
            bot_id = await create_custom_bot(
                owner_id=user_id,
                bot_name=f"{bot_type.replace('_', ' ').title()} Bot",
                bot_description=f"A {bot_type.replace('_', ' ')} bot",
                bot_type=bot_type,
                config={"template": bot_type}
            )
            await log_analytics(user_id, "bot_created", {"id": bot_id, "type": bot_type})
            await query.message.reply_text(
                f"✅ Your {bot_type.replace('_', ' ').title()} Bot has been created! (ID: {bot_id})\n\n"
                f"Use `/editbot {bot_id}` to customize it.",
                parse_mode=ParseMode.MARKDOWN
            )
    
    elif data == "confirm_bot_creation":
        suggestion = context.user_data.get('bot_suggestion', {})
        bot_id = await create_custom_bot(
            owner_id=user_id,
            bot_name=suggestion.get('bot_name', 'Custom Bot'),
            bot_description=suggestion.get('bot_description', ''),
            bot_type=suggestion.get('bot_type', 'general'),
            config=suggestion
        )
        await log_analytics(user_id, "bot_created", {"id": bot_id})
        await query.message.reply_text(
            f"✅ Your bot '{suggestion.get('bot_name')}' has been created! (ID: {bot_id})\n\n"
            f"Use `/mybots` to view your bots.",
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif data == "cancel_bot":
        context.user_data.pop('bot_suggestion', None)
        await query.message.reply_text("❌ Bot creation cancelled.")
    
    # Quiz callbacks
    elif data.startswith("quiz_"):
        answer = data.replace("quiz_", "")
        correct = context.user_data.get('quiz_answer', '')
        explanation = context.user_data.get('quiz_explanation', '')
        
        if answer == correct:
            await query.message.reply_text(
                f"✅ *Correct!* Great job!\n\n_{explanation}_",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await query.message.reply_text(
                f"❌ *Incorrect.* The correct answer was {correct}.\n\n_{explanation}_",
                parse_mode=ParseMode.MARKDOWN
            )
    
    # Poll voting callbacks
    elif data.startswith("vote_"):
        parts = data.split("_")
        poll_id = int(parts[1])
        option_idx = int(parts[2])
        
        await vote_poll(poll_id, user_id, option_idx)
        await query.message.reply_text("✅ Your vote has been recorded!")
    
    elif data.startswith("poll_results_"):
        poll_id = int(data.replace("poll_results_", ""))
        results = await get_poll_results(poll_id)
        
        if results:
            text = f"📊 *Poll Results*\n\n*{results['question']}*\n\n"
            total = sum(results['vote_counts'])
            for opt, count in zip(results['options'], results['vote_counts']):
                pct = (count / total * 100) if total > 0 else 0
                bar = "█" * int(pct / 10) + "░" * (10 - int(pct / 10))
                text += f"{opt}\n{bar} {count} ({pct:.1f}%)\n\n"
            text += f"_Total voters: {results['total_voters']}_"
            await query.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    # Settings callbacks
    elif data == "toggle_notifications":
        settings = await get_user_settings(user_id)
        settings['notifications'] = not settings.get('notifications', True)
        await update_user_settings(user_id, settings)
        status = "enabled" if settings['notifications'] else "disabled"
        await query.message.reply_text(f"🔔 Notifications {status}!")
    
    elif data == "toggle_quiet_hours":
        settings = await get_user_settings(user_id)
        settings['quiet_hours'] = not settings.get('quiet_hours', False)
        await update_user_settings(user_id, settings)
        status = "enabled" if settings['quiet_hours'] else "disabled"
        await query.message.reply_text(f"🌙 Quiet hours {status}!")


# ==================== ERROR HANDLER ====================

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors."""
    import logging
    logging.error(f"Update {update} caused error {context.error}")
    
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "❌ An error occurred. Please try again later.",
            parse_mode=ParseMode.MARKDOWN
        )
