"""
Waya - The Ultimate Intelligent Telegram Bot Builder
Powered by Groq AI for lightning-fast intelligent responses.

Features:
- AI-powered conversations with context memory
- Reminder and task management
- Note-taking with search
- Custom bot building
- AI personalities
- Polls and quizzes
- Smart suggestions
- Multi-language translation
- Text summarization
- And much more!

Author: Waya Team
Version: 1.0.0
"""

import os
import json
import asyncio
from contextlib import asynccontextmanager
from typing import Optional

import fastapi
import fastapi.middleware.cors
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from telegram import Update, Bot
from telegram.ext import (
    Application, 
    CommandHandler, 
    MessageHandler, 
    CallbackQueryHandler,
    filters
)

from database import init_database
from scheduler import WayaScheduler, set_scheduler
from handlers import (
    start_command, help_command, menu_command,
    remind_command, reminders_command, del_reminder_command,
    note_command, notes_command, search_notes_command, del_note_command,
    task_command, tasks_command, done_command, del_task_command,
    build_command, my_bots_command, templates_command,
    chat_command, clear_command, translate_command, summarize_command, quiz_command,
    personalities_command, new_personality_command, set_personality_command,
    poll_command, poll_results_command,
    stats_command, settings_command, suggest_command, feedback_command,
    handle_message, handle_callback, error_handler
)


# Global application instance
telegram_app: Optional[Application] = None
scheduler: Optional[WayaScheduler] = None


def get_telegram_token() -> str:
    """Get the Telegram bot token from environment."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN environment variable is not set")
    return token


async def setup_telegram_app() -> Application:
    """Set up the Telegram bot application with all handlers."""
    token = get_telegram_token()
    
    # Build application
    app = Application.builder().token(token).build()
    
    # Register command handlers
    commands = [
        ("start", start_command),
        ("help", help_command),
        ("menu", menu_command),
        # Reminders
        ("remind", remind_command),
        ("reminders", reminders_command),
        ("delreminder", del_reminder_command),
        # Notes
        ("note", note_command),
        ("notes", notes_command),
        ("searchnotes", search_notes_command),
        ("delnote", del_note_command),
        # Tasks
        ("task", task_command),
        ("tasks", tasks_command),
        ("done", done_command),
        ("deltask", del_task_command),
        # Bot Building
        ("build", build_command),
        ("mybots", my_bots_command),
        ("templates", templates_command),
        # AI Chat
        ("chat", chat_command),
        ("clear", clear_command),
        ("translate", translate_command),
        ("summarize", summarize_command),
        ("quiz", quiz_command),
        # Personalities
        ("personalities", personalities_command),
        ("newpersonality", new_personality_command),
        ("setpersonality", set_personality_command),
        # Polls
        ("poll", poll_command),
        ("pollresults", poll_results_command),
        # Other
        ("stats", stats_command),
        ("settings", settings_command),
        ("suggest", suggest_command),
        ("feedback", feedback_command),
    ]
    
    for command, handler in commands:
        app.add_handler(CommandHandler(command, handler))
    
    # Message handler for all text messages
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Callback handler for inline keyboards
    app.add_handler(CallbackQueryHandler(handle_callback))
    
    # Error handler
    app.add_error_handler(error_handler)
    
    return app


@asynccontextmanager
async def lifespan(app: fastapi.FastAPI):
    """Application lifespan manager."""
    global telegram_app, scheduler
    
    print("🚀 Starting Waya Bot Builder...")
    
    # Initialize database
    await init_database()
    print("✅ Database initialized")
    
    # Set up Telegram application
    try:
        telegram_app = await setup_telegram_app()
        await telegram_app.initialize()
        print("✅ Telegram bot initialized")
        
        # Set up scheduler
        scheduler = WayaScheduler(telegram_app.bot)
        set_scheduler(scheduler)
        await scheduler.start()
        print("✅ Scheduler started")
        
    except ValueError as e:
        print(f"⚠️ Telegram setup skipped: {e}")
    except Exception as e:
        print(f"❌ Error setting up Telegram: {e}")
    
    print("🤖 Waya is ready!")
    
    yield
    
    # Shutdown
    print("🛑 Shutting down Waya...")
    
    if scheduler:
        await scheduler.stop()
    
    if telegram_app:
        await telegram_app.shutdown()
    
    print("👋 Waya stopped!")


# Create FastAPI app
app = fastapi.FastAPI(
    title="Waya - Intelligent Telegram Bot Builder",
    description="The ultimate AI-powered Telegram bot builder with Groq integration",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    fastapi.middleware.cors.CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint - health check and info."""
    return {
        "name": "Waya",
        "description": "The Ultimate Intelligent Telegram Bot Builder",
        "version": "1.0.0",
        "status": "running",
        "features": [
            "AI-powered conversations with Groq",
            "Reminder management",
            "Note-taking with search",
            "Task management",
            "Custom bot building",
            "AI personalities",
            "Polls and quizzes",
            "Smart suggestions",
            "Multi-language translation",
            "Text summarization"
        ],
        "telegram_connected": telegram_app is not None
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "telegram": "connected" if telegram_app else "disconnected",
        "scheduler": "running" if scheduler and scheduler._is_running else "stopped"
    }


@app.post("/webhook")
async def webhook(request: Request):
    """Telegram webhook endpoint."""
    if not telegram_app:
        raise HTTPException(status_code=503, detail="Telegram bot not initialized")
    
    try:
        data = await request.json()
        update = Update.de_json(data, telegram_app.bot)
        
        # Process update asynchronously
        await telegram_app.process_update(update)
        
        return {"status": "ok"}
    
    except Exception as e:
        print(f"Webhook error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/set-webhook")
async def set_webhook(request: Request):
    """Set up the Telegram webhook."""
    if not telegram_app:
        raise HTTPException(status_code=503, detail="Telegram bot not initialized")
    
    try:
        data = await request.json()
        webhook_url = data.get("url")
        
        if not webhook_url:
            raise HTTPException(status_code=400, detail="URL is required")
        
        # Set webhook
        result = await telegram_app.bot.set_webhook(url=f"{webhook_url}/webhook")
        
        # Get bot info
        bot_info = await telegram_app.bot.get_me()
        
        return {
            "status": "success",
            "webhook_set": result,
            "bot": {
                "id": bot_info.id,
                "username": bot_info.username,
                "first_name": bot_info.first_name
            }
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/webhook")
async def delete_webhook():
    """Remove the Telegram webhook."""
    if not telegram_app:
        raise HTTPException(status_code=503, detail="Telegram bot not initialized")
    
    try:
        result = await telegram_app.bot.delete_webhook()
        return {"status": "success", "webhook_deleted": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/bot-info")
async def bot_info():
    """Get Telegram bot information."""
    if not telegram_app:
        raise HTTPException(status_code=503, detail="Telegram bot not initialized")
    
    try:
        bot = await telegram_app.bot.get_me()
        return {
            "id": bot.id,
            "username": bot.username,
            "first_name": bot.first_name,
            "can_join_groups": bot.can_join_groups,
            "can_read_all_group_messages": bot.can_read_all_group_messages,
            "supports_inline_queries": bot.supports_inline_queries
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats")
async def get_stats():
    """Get bot statistics."""
    from database import get_db
    
    async with await get_db() as db:
        # Get user count
        cursor = await db.execute("SELECT COUNT(*) as count FROM users")
        users = (await cursor.fetchone())['count']
        
        # Get reminder count
        cursor = await db.execute("SELECT COUNT(*) as count FROM reminders WHERE is_completed = 0")
        reminders = (await cursor.fetchone())['count']
        
        # Get custom bots count
        cursor = await db.execute("SELECT COUNT(*) as count FROM custom_bots")
        bots = (await cursor.fetchone())['count']
        
        # Get total messages
        cursor = await db.execute("SELECT SUM(total_messages) as total FROM users")
        messages = (await cursor.fetchone())['total'] or 0
        
        return {
            "total_users": users,
            "pending_reminders": reminders,
            "custom_bots": bots,
            "total_messages": messages
        }


# API endpoints for external integrations
@app.post("/api/send-message")
async def send_message(request: Request):
    """Send a message to a user via the bot."""
    if not telegram_app:
        raise HTTPException(status_code=503, detail="Telegram bot not initialized")
    
    try:
        data = await request.json()
        chat_id = data.get("chat_id")
        message = data.get("message")
        
        if not chat_id or not message:
            raise HTTPException(status_code=400, detail="chat_id and message are required")
        
        result = await telegram_app.bot.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode="Markdown"
        )
        
        return {
            "status": "success",
            "message_id": result.message_id
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/broadcast")
async def broadcast(request: Request):
    """Broadcast a message to all users."""
    if not telegram_app:
        raise HTTPException(status_code=503, detail="Telegram bot not initialized")
    
    try:
        data = await request.json()
        message = data.get("message")
        
        if not message:
            raise HTTPException(status_code=400, detail="message is required")
        
        from database import get_db
        
        async with await get_db() as db:
            cursor = await db.execute("SELECT user_id FROM users")
            users = await cursor.fetchall()
        
        sent = 0
        failed = 0
        
        for user in users:
            try:
                await telegram_app.bot.send_message(
                    chat_id=user['user_id'],
                    text=message,
                    parse_mode="Markdown"
                )
                sent += 1
            except Exception:
                failed += 1
            
            # Rate limiting
            await asyncio.sleep(0.05)
        
        return {
            "status": "success",
            "sent": sent,
            "failed": failed
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Templates API
@app.get("/api/templates")
async def get_templates():
    """Get all bot templates."""
    from database import get_bot_templates
    templates = await get_bot_templates()
    return {"templates": templates}


@app.get("/api/templates/{category}")
async def get_templates_by_category(category: str):
    """Get bot templates by category."""
    from database import get_bot_templates
    templates = await get_bot_templates(category=category)
    return {"templates": templates}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
