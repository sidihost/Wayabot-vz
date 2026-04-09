"""
Waya - The Ultimate Intelligent Telegram Bot Builder
Powered by Groq AI for lightning-fast intelligent responses.

Features:
- AI-powered conversations with context memory
- Reminder and task management with natural language
- Note-taking with full-text search
- Custom bot building with 12+ templates
- AI personalities customization
- Polls and quizzes
- Smart suggestions
- Multi-language translation
- Text summarization
- Gamification with XP and streaks

Voice AI (ElevenLabs):
- Text-to-speech with 12+ premium voices
- Multiple voice styles (expressive, dramatic, etc.)
- Voice cloning capabilities
- Convert any message to audio

Emotion AI (Hume):
- Real-time emotion detection from text
- Voice emotion analysis
- Empathic response mode
- Emotional wellbeing insights
- Mood tracking and history

Author: Waya Team
Version: 2.0.0
"""

import os
import sys
import asyncio
from contextlib import asynccontextmanager
from typing import Optional

import fastapi
import fastapi.middleware.cors
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from telegram import Update
from telegram.ext import (
    Application, 
    CommandHandler, 
    MessageHandler, 
    CallbackQueryHandler,
    TypeHandler,
    filters
)

import database as db
from scheduler import WayaScheduler
from intelligence_core import init_intelligence_core, get_intelligence_core, close_intelligence_core

# Bot runtime - DISABLED until properly tested
BOT_RUNTIME_AVAILABLE = False
bot_runtime = None

async def start_bot_runtime(): 
    pass
    
async def stop_bot_runtime(): 
    pass
from handlers import (
    start_command, help_command, menu_command,
    remind_command, reminders_command, del_reminder_command, snooze_reminder_command,
    note_command, notes_command, search_notes_command, del_note_command,
    task_command, tasks_command, done_command, del_task_command,
    build_command, my_bots_command, templates_command, activate_bot_command,
    bots_menu_command, edit_bot_command,  # New bot builder commands
    chat_command, clear_command, translate_command, summarize_command, quiz_command,
    personalities_command, new_personality_command, set_personality_command,
    poll_command, poll_results_command,
    stats_command, settings_command, suggest_command, feedback_command,
    profile_command, leaderboard_command,
    # Voice AI (ElevenLabs)
    voice_command, voices_command, setvoice_command, voicestyle_command, speakthis_command,
    # Emotion AI (Hume)
    mood_command, emotions_command, empathy_command, wellbeing_command, analyze_voice_emotion,
    handle_message, handle_voice_message, handle_audio_message, handle_photo_message,
    handle_callback, error_handler,
    # Managed Bots (Telegram Bot API 9.6)
    handle_managed_bot_update
)


# Global instances
telegram_app: Optional[Application] = None
scheduler: Optional[WayaScheduler] = None
intelligence_core = None  # Intelligence Core instance


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
        # Core
        ("start", start_command),
        ("help", help_command),
        ("menu", menu_command),
        ("profile", profile_command),
        ("leaderboard", leaderboard_command),
        
        # Reminders
        ("remind", remind_command),
        ("reminders", reminders_command),
        ("delreminder", del_reminder_command),
        ("snooze", snooze_reminder_command),
        
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
        ("bots", bots_menu_command),  # New - shows full bot builder menu
        ("mybots", my_bots_command),
        ("templates", templates_command),
        ("usebot", activate_bot_command),
        ("editbot", edit_bot_command),  # New - edit bot via prompt
        
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
        
        # Voice AI (ElevenLabs)
        ("voice", voice_command),
        ("voices", voices_command),
        ("setvoice", setvoice_command),
        ("voicestyle", voicestyle_command),
        ("speakthis", speakthis_command),
        
        # Emotion AI (Hume)
        ("mood", mood_command),
        ("emotions", emotions_command),
        ("empathy", empathy_command),
        ("wellbeing", wellbeing_command),
        ("analyzeemotion", analyze_voice_emotion),
        
        # Other
        ("stats", stats_command),
        ("settings", settings_command),
        ("suggest", suggest_command),
        ("feedback", feedback_command),
    ]
    
    for command, handler in commands:
        app.add_handler(CommandHandler(command, handler))
    
    # Message handlers for all message types
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice_message))
    app.add_handler(MessageHandler(filters.AUDIO, handle_audio_message))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo_message))
    
    # Callback handler for inline keyboards
    app.add_handler(CallbackQueryHandler(handle_callback))
    
    # Managed bot handler (Telegram Bot API 9.6 - for creating real bots)
    app.add_handler(TypeHandler(Update, handle_managed_bot_update), group=1)
    
    # Error handler
    app.add_error_handler(error_handler)
    
    return app


@asynccontextmanager
async def lifespan(app: fastapi.FastAPI):
    """Application lifespan manager."""
    global telegram_app, scheduler, intelligence_core
    
    print("=" * 50)
    print("🚀 Starting Waya Bot Builder v2.0.0 - Intelligence Edition")
    print("=" * 50)
    
    # Initialize PostgreSQL database
    try:
        await db.init_db()
        print("✅ PostgreSQL database initialized")
    except Exception as e:
        print(f"❌ Database error: {e}")
        raise
    
    # Initialize Intelligence Core (Memory, Learning, Tools, Cognition, Proactive)
    try:
        intelligence_core = await init_intelligence_core(db._pool)
        print("✅ Intelligence Core initialized")
        print("   - Memory Engine: Long-term user memory")
        print("   - Learning Engine: Personalization & adaptation")
        print("   - Tools Engine: Web search, code execution, image analysis")
        print("   - Cognitive Engine: ReAct-style reasoning")
        print("   - Proactive Engine: Smart suggestions & briefings")
    except Exception as e:
        print(f"⚠️ Intelligence Core partial init: {e}")
        print("   Bot will run with basic AI capabilities")
    
    # Set up Telegram application
    try:
        telegram_app = await setup_telegram_app()
        await telegram_app.initialize()
        bot_info = await telegram_app.bot.get_me()
        print(f"✅ Telegram bot initialized: @{bot_info.username}")
        
        # Set up scheduler for reminders
        scheduler = WayaScheduler(telegram_app.bot)
        await scheduler.start()
        print("✅ Reminder scheduler started")
        
        # Auto-setup webhook if BOT_DOMAIN is set
        bot_domain = os.environ.get("BOT_DOMAIN")
        if bot_domain:
            try:
                webhook_url = f"https://{bot_domain}/webhook"
                result = await telegram_app.bot.set_webhook(
                    url=webhook_url,
                    allowed_updates=["message", "callback_query", "poll", "poll_answer", "managed_bot"]
                )
                if result:
                    print(f"✅ Webhook auto-configured: {webhook_url}")
                else:
                    print(f"⚠️ Webhook setup returned False for: {webhook_url}")
            except Exception as we:
                print(f"⚠️ Auto-webhook failed: {we}")
                print("   You can manually set it via POST /set-webhook")
        else:
            print("ℹ️ BOT_DOMAIN not set - webhook must be configured manually")
            print("   POST /set-webhook with {'url': 'https://your-domain.com'}")
        
    except ValueError as e:
        print(f"⚠️ Telegram setup skipped: {e}")
    except Exception as e:
        print(f"❌ Telegram error: {e}")
    
    # Start bot runtime engine (autonomous bot execution)
    if BOT_RUNTIME_AVAILABLE:
        try:
            await start_bot_runtime()
            print("✅ Bot Runtime Engine started (autonomous bot execution)")
        except Exception as e:
            print(f"⚠️ Bot Runtime startup error: {e}")
    else:
        print("ℹ️ Bot Runtime not available - user bots will run through main handler")
    
    print("=" * 50)
    print("🤖 Waya is ready and listening!")
    print("   All user bots run automatically on our infrastructure")
    print("=" * 50)
    
    yield
    
    # Shutdown
    print("\n🛑 Shutting down Waya...")
    
    # Close Intelligence Core
    if intelligence_core:
        await close_intelligence_core()
        print("✅ Intelligence Core stopped")
    
    # Stop bot runtime first
    if BOT_RUNTIME_AVAILABLE:
        await stop_bot_runtime()
        print("✅ Bot Runtime Engine stopped")
    
    if scheduler:
        await scheduler.stop()
        print("✅ Scheduler stopped")
    
    if telegram_app:
        await telegram_app.shutdown()
        print("✅ Telegram bot stopped")
    
    await db.close_db()
    print("✅ Database connection closed")
    
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


# =====================================================
# HEALTH & INFO ENDPOINTS
# =====================================================

@app.get("/")
async def root():
    """Root endpoint - health check and info."""
    return {
        "name": "Waya",
        "tagline": "The Ultimate Intelligent Telegram Bot Builder",
        "version": "1.0.0",
        "status": "running",
        "powered_by": "Groq AI",
        "database": "PostgreSQL",
        "features": [
            "AI-powered conversations with context memory",
            "Natural language reminder parsing",
            "Note-taking with full-text search",
            "Task management with priorities",
            "Custom bot building (12+ templates)",
            "AI personalities customization",
            "Polls and AI-generated quizzes",
            "Smart context-aware suggestions",
            "Multi-language translation",
            "Text summarization",
            "Gamification (XP, levels, streaks)",
            "Analytics and insights"
        ],
        "telegram_connected": telegram_app is not None,
        "documentation": "/docs"
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    db_healthy = False
    try:
        async with db.get_connection() as conn:
            await conn.fetchval("SELECT 1")
            db_healthy = True
    except:
        pass
    
    # Check AI status (tries all providers)
    ai_healthy = False
    ai_provider = "unknown"
    ai_error = None
    try:
        from ai_engine import chat_completion, get_ai_provider
        ai_provider = get_ai_provider()
        # Quick test with minimal tokens
        result = await chat_completion(
            messages=[{"role": "user", "content": "Hi"}],
            max_tokens=5
        )
        if result:
            ai_healthy = True
    except Exception as e:
        ai_error = str(e)
    
    runtime_bots = bot_runtime.get_all_bots_status() if bot_runtime else []
    runtime_running = bot_runtime._running if bot_runtime else False
    
    all_healthy = db_healthy and telegram_app and ai_healthy
    
    return {
        "status": "healthy" if all_healthy else "degraded",
        "components": {
            "database": "healthy" if db_healthy else "unhealthy",
            "telegram": "connected" if telegram_app else "disconnected",
            "ai": f"healthy ({ai_provider})" if ai_healthy else f"unhealthy ({ai_provider}): {ai_error}",
            "scheduler": "running" if scheduler and scheduler._running else "stopped",
            "bot_runtime": "running" if runtime_running else "stopped"
        },
        "active_bots": len(runtime_bots)
    }


@app.get("/runtime/bots")
async def get_runtime_bots():
    """Get status of all running user bots."""
    if not bot_runtime:
        return {"bots": [], "count": 0}
    
    bots = bot_runtime.get_all_bots_status()
    return {
        "bots": bots,
        "count": len(bots),
        "runtime_status": "running" if bot_runtime._running else "stopped"
    }


@app.get("/runtime/bots/{bot_id}")
async def get_runtime_bot_status(bot_id: int):
    """Get status of a specific bot."""
    if not bot_runtime:
        raise HTTPException(status_code=503, detail="Bot runtime not initialized")
    
    status = bot_runtime.get_bot_status(bot_id)
    if not status:
        raise HTTPException(status_code=404, detail="Bot not found in runtime")
    
    return status


# =====================================================
# TELEGRAM WEBHOOK ENDPOINTS
# =====================================================

@app.post("/webhook")
async def webhook(request: Request):
    """Telegram webhook endpoint."""
    if not telegram_app:
        raise HTTPException(status_code=503, detail="Telegram bot not initialized")
    
    try:
        data = await request.json()
        update = Update.de_json(data, telegram_app.bot)
        
        # Process update
        await telegram_app.process_update(update)
        
        return {"status": "ok"}
    
    except Exception as e:
        import traceback
        error_type = type(e).__name__
        error_message = str(e)
        tb = traceback.format_exc()
        print(f"[Webhook Error] [{error_type}] {error_message}")
        print(f"[Webhook Traceback] {tb}")
        # Return 200 OK to Telegram to prevent retries for application errors
        # Only return non-200 for actual server errors that should be retried
        return {"status": "error", "error": f"{error_type}: {error_message}"}


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
        
        # Ensure URL ends with /webhook
        full_url = f"{webhook_url.rstrip('/')}/webhook"
        
        # Set webhook with allowed updates
        result = await telegram_app.bot.set_webhook(
            url=full_url,
            allowed_updates=["message", "callback_query", "poll", "poll_answer"]
        )
        
        # Get bot info
        bot_info = await telegram_app.bot.get_me()
        
        return {
            "status": "success",
            "webhook_url": full_url,
            "webhook_set": result,
            "bot": {
                "id": bot_info.id,
                "username": bot_info.username,
                "first_name": bot_info.first_name
            },
            "instructions": f"Bot is now active! Message @{bot_info.username} on Telegram to start."
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/webhook")
async def delete_webhook():
    """Remove the Telegram webhook."""
    if not telegram_app:
        raise HTTPException(status_code=503, detail="Telegram bot not initialized")
    
    try:
        result = await telegram_app.bot.delete_webhook(drop_pending_updates=True)
        return {"status": "success", "webhook_deleted": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/webhook-info")
async def webhook_info():
    """Get current webhook information."""
    if not telegram_app:
        raise HTTPException(status_code=503, detail="Telegram bot not initialized")
    
    try:
        info = await telegram_app.bot.get_webhook_info()
        return {
            "url": info.url,
            "has_custom_certificate": info.has_custom_certificate,
            "pending_update_count": info.pending_update_count,
            "last_error_date": info.last_error_date,
            "last_error_message": info.last_error_message,
            "max_connections": info.max_connections,
            "allowed_updates": info.allowed_updates
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =====================================================
# BOT INFO ENDPOINTS
# =====================================================

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


# =====================================================
# STATISTICS ENDPOINTS
# =====================================================

@app.get("/stats")
async def get_stats():
    """Get overall bot statistics."""
    try:
        async with db.get_connection() as conn:
            # Get counts
            users = await conn.fetchval("SELECT COUNT(*) FROM users")
            reminders = await conn.fetchval("SELECT COUNT(*) FROM reminders WHERE is_active = TRUE AND is_completed = FALSE")
            notes = await conn.fetchval("SELECT COUNT(*) FROM notes WHERE is_archived = FALSE")
            tasks = await conn.fetchval("SELECT COUNT(*) FROM tasks WHERE status NOT IN ('completed', 'cancelled')")
            bots = await conn.fetchval("SELECT COUNT(*) FROM custom_bots")
            
            # Get total messages
            total_messages = await conn.fetchval("SELECT SUM(total_messages) FROM user_stats") or 0
            total_ai_requests = await conn.fetchval("SELECT SUM(total_ai_requests) FROM user_stats") or 0
            
            # Get active users (last 24h)
            active_users = await conn.fetchval("""
                SELECT COUNT(*) FROM users 
                WHERE last_active_at >= NOW() - INTERVAL '24 hours'
            """)
            
            return {
                "users": {
                    "total": users,
                    "active_24h": active_users
                },
                "content": {
                    "reminders": reminders,
                    "notes": notes,
                    "tasks": tasks,
                    "custom_bots": bots
                },
                "activity": {
                    "total_messages": total_messages,
                    "total_ai_requests": total_ai_requests
                }
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =====================================================
# API ENDPOINTS
# =====================================================

@app.post("/api/send-message")
async def send_message(request: Request):
    """Send a message to a user via the bot."""
    if not telegram_app:
        raise HTTPException(status_code=503, detail="Telegram bot not initialized")
    
    try:
        data = await request.json()
        chat_id = data.get("chat_id")
        message = data.get("message")
        parse_mode = data.get("parse_mode", "HTML")
        
        if not chat_id or not message:
            raise HTTPException(status_code=400, detail="chat_id and message are required")
        
        result = await telegram_app.bot.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode=parse_mode
        )
        
        return {
            "status": "success",
            "message_id": result.message_id,
            "chat_id": result.chat_id
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/templates")
async def get_templates(category: str = None, featured: bool = False):
    """Get bot templates."""
    try:
        templates = await db.get_bot_templates(category=category, featured_only=featured)
        return {
            "count": len(templates),
            "templates": templates
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/templates/categories")
async def get_template_categories():
    """Get all template categories."""
    try:
        async with db.get_connection() as conn:
            rows = await conn.fetch("""
                SELECT DISTINCT category, COUNT(*) as count 
                FROM bot_templates 
                GROUP BY category 
                ORDER BY count DESC
            """)
            return {
                "categories": [{"name": r["category"], "count": r["count"]} for r in rows]
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/user/{user_id}")
async def get_user_info(user_id: int):
    """Get user information."""
    try:
        user = await db.get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        stats = await db.get_user_stats(user_id)
        
        return {
            "user": {
                "id": user["id"],
                "username": user["username"],
                "first_name": user["first_name"],
                "created_at": str(user["created_at"]),
                "last_active": str(user["last_active_at"])
            },
            "stats": stats
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def run_polling():
    """Run bot in polling mode (for local development without webhook)."""
    global telegram_app, scheduler
    
    print("=" * 50)
    print("Starting Waya Bot in POLLING mode")
    print("=" * 50)
    
    # Initialize database
    await db.init_db()
    print("Database initialized")
    
    # Set up Telegram app
    telegram_app = await setup_telegram_app()
    await telegram_app.initialize()
    
    bot_info = await telegram_app.bot.get_me()
    print(f"Bot: @{bot_info.username}")
    
    # Start scheduler
    scheduler = WayaScheduler(telegram_app.bot)
    await scheduler.start()
    print("Scheduler started")
    
    # Delete any existing webhook
    await telegram_app.bot.delete_webhook(drop_pending_updates=True)
    print("Webhook cleared, starting polling...")
    
    # Start polling
    await telegram_app.start()
    await telegram_app.updater.start_polling(drop_pending_updates=True)
    
    print("=" * 50)
    print("Bot is running! Press Ctrl+C to stop.")
    print("=" * 50)
    
    # Keep running
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        await telegram_app.updater.stop()
        await telegram_app.stop()
        await telegram_app.shutdown()
        if scheduler:
            await scheduler.stop()
        await db.close_db()
        print("Bot stopped!")


if __name__ == "__main__":
    import sys
    import asyncio
    
    if len(sys.argv) > 1 and sys.argv[1] == "--polling":
        # Run in polling mode for local development
        asyncio.run(run_polling())
    else:
        # Run FastAPI server for webhook mode (production)
        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=8000)
