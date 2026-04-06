"""
Waya Bot Builder - Scheduler Module
Handles background tasks like reminder notifications and scheduled messages.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional
from telegram import Bot
from telegram.constants import ParseMode
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

import database as db


class WayaScheduler:
    """Background scheduler for Waya bot."""
    
    def __init__(self, bot: Bot):
        self.bot = bot
        self.scheduler = AsyncIOScheduler(timezone="UTC")
        self._running = False
    
    async def start(self):
        """Start the scheduler."""
        if self._running:
            return
        
        # Check reminders every 30 seconds
        self.scheduler.add_job(
            self.check_reminders,
            IntervalTrigger(seconds=30),
            id='check_reminders',
            replace_existing=True,
            max_instances=1
        )
        
        # Daily summary at 8 AM UTC
        self.scheduler.add_job(
            self.daily_summary,
            'cron',
            hour=8,
            minute=0,
            id='daily_summary',
            replace_existing=True
        )
        
        # Cleanup old data weekly
        self.scheduler.add_job(
            self.cleanup_old_data,
            'cron',
            day_of_week='sun',
            hour=3,
            minute=0,
            id='cleanup',
            replace_existing=True
        )
        
        self.scheduler.start()
        self._running = True
        print("[Scheduler] Started with reminder checking every 30s")
    
    async def stop(self):
        """Stop the scheduler."""
        if self._running:
            self.scheduler.shutdown(wait=False)
            self._running = False
            print("[Scheduler] Stopped")
    
    async def check_reminders(self):
        """Check and send due reminders."""
        try:
            reminders = await db.get_due_reminders()
            
            for reminder in reminders:
                try:
                    # Build reminder message
                    priority_emoji = {
                        "urgent": "🚨",
                        "high": "❗",
                        "normal": "⏰",
                        "low": "📝"
                    }.get(reminder.get("priority", "normal"), "⏰")
                    
                    message = f"{priority_emoji} *Reminder!*\n\n"
                    message += f"📌 {reminder['title']}\n"
                    
                    if reminder.get("description"):
                        message += f"\n_{reminder['description']}_\n"
                    
                    if reminder.get("category"):
                        message += f"\n📁 Category: {reminder['category']}"
                    
                    # Add snooze options
                    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
                    keyboard = [
                        [
                            InlineKeyboardButton("✅ Done", callback_data=f"reminder_done_{reminder['id']}"),
                            InlineKeyboardButton("⏰ Snooze 10m", callback_data=f"reminder_snooze_{reminder['id']}_10"),
                        ],
                        [
                            InlineKeyboardButton("⏰ Snooze 1h", callback_data=f"reminder_snooze_{reminder['id']}_60"),
                            InlineKeyboardButton("⏰ Snooze 1d", callback_data=f"reminder_snooze_{reminder['id']}_1440"),
                        ]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    # Send reminder
                    await self.bot.send_message(
                        chat_id=reminder['user_id'],
                        text=message,
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=reply_markup
                    )
                    
                    # Mark as sent
                    await db.mark_reminder_sent(reminder['id'])
                    
                    # Handle recurring reminders
                    if reminder.get("repeat_type") and reminder["repeat_type"] != "none":
                        await self._reschedule_recurring(reminder)
                    
                    # Log analytics
                    await db.log_event(reminder['user_id'], "reminder_sent", {
                        "reminder_id": reminder['id'],
                        "title": reminder['title']
                    })
                    
                except Exception as e:
                    print(f"[Scheduler] Failed to send reminder {reminder['id']}: {e}")
        
        except Exception as e:
            print(f"[Scheduler] Error checking reminders: {e}")
    
    async def _reschedule_recurring(self, reminder: dict):
        """Reschedule a recurring reminder."""
        remind_at = reminder['remind_at']
        if isinstance(remind_at, str):
            remind_at = datetime.fromisoformat(remind_at)
        
        repeat_type = reminder['repeat_type']
        interval = reminder.get('repeat_interval', 1) or 1
        
        if repeat_type == 'daily':
            next_time = remind_at + timedelta(days=interval)
        elif repeat_type == 'weekly':
            next_time = remind_at + timedelta(weeks=interval)
        elif repeat_type == 'monthly':
            next_time = remind_at + timedelta(days=30 * interval)
        elif repeat_type == 'yearly':
            next_time = remind_at + timedelta(days=365 * interval)
        else:
            return
        
        # Check if we've exceeded max repeat count
        if reminder.get('max_repeat_count'):
            if reminder.get('repeat_count', 0) >= reminder['max_repeat_count']:
                return
        
        # Check if we've passed the end date
        if reminder.get('repeat_end_date'):
            end_date = reminder['repeat_end_date']
            if isinstance(end_date, str):
                end_date = datetime.fromisoformat(end_date)
            if next_time > end_date:
                return
        
        # Create next reminder
        await db.create_reminder(
            user_id=reminder['user_id'],
            title=reminder['title'],
            description=reminder.get('description'),
            remind_at=next_time,
            repeat_type=repeat_type,
            repeat_interval=interval,
            priority=reminder.get('priority', 'normal'),
            category=reminder.get('category'),
            tags=reminder.get('tags', [])
        )
    
    async def daily_summary(self):
        """Send daily summary to users who have it enabled."""
        try:
            async with db.get_connection() as conn:
                # Get users with daily summary enabled
                users = await conn.fetch("""
                    SELECT u.id, u.first_name, u.preferences
                    FROM users u
                    WHERE (u.preferences->>'daily_summary')::boolean = true
                    AND u.is_blocked = false
                """)
                
                for user in users:
                    try:
                        user_id = user['id']
                        name = user['first_name'] or 'there'
                        
                        # Get today's tasks
                        tasks = await db.get_user_tasks(user_id, status='pending')
                        urgent_tasks = [t for t in tasks if t.get('priority') in ('urgent', 'high')]
                        
                        # Get today's reminders
                        reminders = await db.get_user_reminders(user_id, active_only=True, limit=10)
                        today = datetime.now(timezone.utc).date()
                        today_reminders = [r for r in reminders 
                                         if r['remind_at'].date() == today]
                        
                        # Get stats
                        stats = await db.get_user_stats(user_id)
                        
                        # Build summary
                        message = f"🌅 *Good morning, {name}!*\n\n"
                        message += f"Here's your daily summary:\n\n"
                        
                        if today_reminders:
                            message += f"⏰ *Today's Reminders ({len(today_reminders)}):*\n"
                            for r in today_reminders[:5]:
                                time = r['remind_at'].strftime('%I:%M %p')
                                message += f"  • {r['title']} at {time}\n"
                            message += "\n"
                        
                        if urgent_tasks:
                            message += f"🔴 *Priority Tasks ({len(urgent_tasks)}):*\n"
                            for t in urgent_tasks[:5]:
                                message += f"  • {t['title']}\n"
                            message += "\n"
                        
                        if stats:
                            message += f"📊 *Your Stats:*\n"
                            message += f"  🔥 Streak: {stats.get('streak_days', 0)} days\n"
                            message += f"  ⭐ Level: {stats.get('level', 1)}\n"
                            message += f"  ✨ XP: {stats.get('xp_points', 0)}\n"
                        
                        message += "\nHave a productive day! 💪"
                        
                        await self.bot.send_message(
                            chat_id=user_id,
                            text=message,
                            parse_mode=ParseMode.MARKDOWN
                        )
                        
                    except Exception as e:
                        print(f"[Scheduler] Failed to send daily summary to {user['id']}: {e}")
        
        except Exception as e:
            print(f"[Scheduler] Error in daily summary: {e}")
    
    async def cleanup_old_data(self):
        """Clean up old data to keep database performant."""
        try:
            async with db.get_connection() as conn:
                # Delete old completed reminders (> 30 days)
                await conn.execute("""
                    DELETE FROM reminders 
                    WHERE is_completed = true 
                    AND completed_at < NOW() - INTERVAL '30 days'
                """)
                
                # Delete old analytics events (> 90 days)
                await conn.execute("""
                    DELETE FROM analytics_events 
                    WHERE created_at < NOW() - INTERVAL '90 days'
                """)
                
                # Delete old conversation history (> 7 days)
                await conn.execute("""
                    DELETE FROM conversations 
                    WHERE created_at < NOW() - INTERVAL '7 days'
                """)
                
                print("[Scheduler] Cleanup completed")
        
        except Exception as e:
            print(f"[Scheduler] Cleanup error: {e}")
    
    async def send_notification(self, user_id: int, title: str, message: str):
        """Send a notification to a user."""
        try:
            text = f"🔔 *{title}*\n\n{message}"
            await self.bot.send_message(
                chat_id=user_id,
                text=text,
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            print(f"[Scheduler] Failed to send notification to {user_id}: {e}")
