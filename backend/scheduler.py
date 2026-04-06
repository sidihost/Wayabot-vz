"""
Waya Bot Builder - Scheduler Module
Handles background tasks like reminder notifications and scheduled messages.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional
from telegram import Bot
from telegram.constants import ParseMode
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from database import (
    get_pending_reminders, mark_reminder_complete, create_reminder,
    get_user_settings
)


class WayaScheduler:
    """Background scheduler for Waya bot."""
    
    def __init__(self, bot: Bot):
        self.bot = bot
        self.scheduler = AsyncIOScheduler()
        self._is_running = False
    
    async def start(self):
        """Start the scheduler."""
        if self._is_running:
            return
        
        # Add jobs
        self.scheduler.add_job(
            self.check_reminders,
            IntervalTrigger(seconds=30),  # Check every 30 seconds
            id='check_reminders',
            replace_existing=True
        )
        
        self.scheduler.add_job(
            self.daily_summary,
            'cron',
            hour=8,  # 8 AM daily
            minute=0,
            id='daily_summary',
            replace_existing=True
        )
        
        self.scheduler.start()
        self._is_running = True
        print("Waya Scheduler started!")
    
    async def stop(self):
        """Stop the scheduler."""
        if self._is_running:
            self.scheduler.shutdown()
            self._is_running = False
            print("Waya Scheduler stopped!")
    
    async def check_reminders(self):
        """Check and send due reminders."""
        try:
            reminders = await get_pending_reminders()
            
            for reminder in reminders:
                remind_at = datetime.fromisoformat(reminder['remind_at'])
                
                if remind_at <= datetime.now():
                    # Check user settings for quiet hours
                    settings = await get_user_settings(reminder['user_id'])
                    
                    if settings.get('quiet_hours'):
                        hour = datetime.now().hour
                        if 22 <= hour or hour < 8:  # 10 PM to 8 AM
                            continue  # Skip during quiet hours
                    
                    # Send reminder
                    try:
                        await self.bot.send_message(
                            chat_id=reminder['user_id'],
                            text=f"⏰ *Reminder!*\n\n{reminder['message']}",
                            parse_mode=ParseMode.MARKDOWN
                        )
                        
                        # Handle repeat reminders
                        if reminder['repeat_type']:
                            await self._create_repeat_reminder(reminder)
                        
                        await mark_reminder_complete(reminder['id'])
                        
                    except Exception as e:
                        print(f"Failed to send reminder {reminder['id']}: {e}")
        
        except Exception as e:
            print(f"Error checking reminders: {e}")
    
    async def _create_repeat_reminder(self, reminder: dict):
        """Create the next occurrence of a repeating reminder."""
        remind_at = datetime.fromisoformat(reminder['remind_at'])
        
        if reminder['repeat_type'] == 'daily':
            next_remind = remind_at + timedelta(days=1)
        elif reminder['repeat_type'] == 'weekly':
            next_remind = remind_at + timedelta(weeks=1)
        elif reminder['repeat_type'] == 'monthly':
            # Add roughly a month
            next_remind = remind_at + timedelta(days=30)
        else:
            return
        
        await create_reminder(
            user_id=reminder['user_id'],
            message=reminder['message'],
            remind_at=next_remind,
            repeat_type=reminder['repeat_type'],
            repeat_interval=reminder.get('repeat_interval')
        )
    
    async def daily_summary(self):
        """Send daily summary to users who have it enabled."""
        # This would query all users with daily_summary enabled
        # and send them a personalized summary
        pass
    
    async def send_scheduled_message(self, chat_id: int, message: str):
        """Send a scheduled message."""
        try:
            await self.bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            print(f"Failed to send scheduled message to {chat_id}: {e}")


# Global scheduler instance
_scheduler: Optional[WayaScheduler] = None


def get_scheduler() -> Optional[WayaScheduler]:
    """Get the global scheduler instance."""
    return _scheduler


def set_scheduler(scheduler: WayaScheduler):
    """Set the global scheduler instance."""
    global _scheduler
    _scheduler = scheduler
