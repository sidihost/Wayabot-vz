"""
Waya Bot Builder - Database Module
Handles all persistent storage for users, bots, conversations, reminders, and analytics.
"""

import aiosqlite
import json
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path

DATABASE_PATH = Path("/tmp/waya_bot.db")


async def get_db():
    """Get database connection."""
    db = await aiosqlite.connect(DATABASE_PATH)
    db.row_factory = aiosqlite.Row
    return db


async def init_database():
    """Initialize the database with all required tables."""
    async with await get_db() as db:
        # Users table - stores Telegram user information
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                language_code TEXT DEFAULT 'en',
                is_premium INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                settings TEXT DEFAULT '{}',
                total_messages INTEGER DEFAULT 0,
                total_commands INTEGER DEFAULT 0
            )
        """)
        
        # Custom bots created by users
        await db.execute("""
            CREATE TABLE IF NOT EXISTS custom_bots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_id INTEGER NOT NULL,
                bot_name TEXT NOT NULL,
                bot_description TEXT,
                bot_type TEXT NOT NULL,
                config TEXT DEFAULT '{}',
                commands TEXT DEFAULT '[]',
                triggers TEXT DEFAULT '[]',
                responses TEXT DEFAULT '[]',
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (owner_id) REFERENCES users(user_id)
            )
        """)
        
        # Conversation history for AI context
        await db.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                bot_context TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        # Reminders system
        await db.execute("""
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                remind_at TIMESTAMP NOT NULL,
                repeat_type TEXT,
                repeat_interval INTEGER,
                is_completed INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        # User notes and data storage
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                tags TEXT DEFAULT '[]',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        # Scheduled messages
        await db.execute("""
            CREATE TABLE IF NOT EXISTS scheduled_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                chat_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                send_at TIMESTAMP NOT NULL,
                repeat_type TEXT,
                is_sent INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        # User tasks/todos
        await db.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                due_date TIMESTAMP,
                priority TEXT DEFAULT 'medium',
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        # Bot templates
        await db.execute("""
            CREATE TABLE IF NOT EXISTS bot_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                category TEXT NOT NULL,
                config TEXT NOT NULL,
                popularity INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # User preferences and AI personality settings
        await db.execute("""
            CREATE TABLE IF NOT EXISTS ai_personalities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                system_prompt TEXT NOT NULL,
                temperature REAL DEFAULT 0.7,
                is_active INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        # Analytics and usage tracking
        await db.execute("""
            CREATE TABLE IF NOT EXISTS analytics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                event_data TEXT DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        # Polls created by users
        await db.execute("""
            CREATE TABLE IF NOT EXISTS polls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                question TEXT NOT NULL,
                options TEXT NOT NULL,
                votes TEXT DEFAULT '{}',
                is_anonymous INTEGER DEFAULT 1,
                is_multiple_choice INTEGER DEFAULT 0,
                closes_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        # Insert default bot templates
        await db.execute("""
            INSERT OR IGNORE INTO bot_templates (id, name, description, category, config) VALUES
            (1, 'Customer Support Bot', 'Handle customer inquiries with AI', 'business', '{"greeting": "Hello! How can I help you today?", "fallback": "Let me connect you with a human agent.", "keywords": ["help", "support", "issue", "problem"]}'),
            (2, 'FAQ Bot', 'Answer frequently asked questions', 'business', '{"greeting": "Hi! Ask me anything about our services.", "faqs": []}'),
            (3, 'Personal Assistant', 'Your AI-powered personal assistant', 'productivity', '{"features": ["reminders", "notes", "tasks", "weather", "news"]}'),
            (4, 'Quiz Bot', 'Create and manage quizzes', 'education', '{"quiz_types": ["multiple_choice", "true_false", "open_ended"]}'),
            (5, 'Feedback Collector', 'Collect and analyze user feedback', 'business', '{"questions": [], "rating_scale": 5}'),
            (6, 'Event Scheduler', 'Schedule and manage events', 'productivity', '{"features": ["calendar", "rsvp", "reminders"]}'),
            (7, 'Content Publisher', 'Automate content publishing', 'marketing', '{"platforms": ["telegram"], "scheduling": true}'),
            (8, 'Language Learning Bot', 'Learn new languages with AI', 'education', '{"languages": ["english", "spanish", "french", "german"]}'),
            (9, 'Fitness Tracker', 'Track workouts and fitness goals', 'health', '{"features": ["workouts", "nutrition", "goals", "reminders"]}'),
            (10, 'News Aggregator', 'Get personalized news updates', 'information', '{"categories": ["tech", "business", "sports", "entertainment"]}')
        """)
        
        await db.commit()


# User Management Functions
async def get_or_create_user(user_id: int, username: str = None, first_name: str = None, 
                             last_name: str = None, language_code: str = 'en', is_premium: bool = False) -> Dict[str, Any]:
    """Get existing user or create new one."""
    async with await get_db() as db:
        cursor = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = await cursor.fetchone()
        
        if user:
            # Update last active and user info
            await db.execute("""
                UPDATE users SET 
                    username = COALESCE(?, username),
                    first_name = COALESCE(?, first_name),
                    last_name = COALESCE(?, last_name),
                    language_code = COALESCE(?, language_code),
                    is_premium = ?,
                    last_active = CURRENT_TIMESTAMP
                WHERE user_id = ?
            """, (username, first_name, last_name, language_code, int(is_premium), user_id))
            await db.commit()
            return dict(user)
        else:
            await db.execute("""
                INSERT INTO users (user_id, username, first_name, last_name, language_code, is_premium)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, username, first_name, last_name, language_code, int(is_premium)))
            await db.commit()
            return {
                'user_id': user_id,
                'username': username,
                'first_name': first_name,
                'last_name': last_name,
                'language_code': language_code,
                'is_premium': is_premium,
                'settings': '{}',
                'total_messages': 0,
                'total_commands': 0
            }


async def update_user_stats(user_id: int, message: bool = False, command: bool = False):
    """Update user message/command counts."""
    async with await get_db() as db:
        if message:
            await db.execute("UPDATE users SET total_messages = total_messages + 1 WHERE user_id = ?", (user_id,))
        if command:
            await db.execute("UPDATE users SET total_commands = total_commands + 1 WHERE user_id = ?", (user_id,))
        await db.commit()


async def get_user_settings(user_id: int) -> Dict[str, Any]:
    """Get user settings."""
    async with await get_db() as db:
        cursor = await db.execute("SELECT settings FROM users WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        if row:
            return json.loads(row['settings'])
        return {}


async def update_user_settings(user_id: int, settings: Dict[str, Any]):
    """Update user settings."""
    async with await get_db() as db:
        await db.execute("UPDATE users SET settings = ? WHERE user_id = ?", (json.dumps(settings), user_id))
        await db.commit()


# Conversation Management
async def add_conversation(user_id: int, role: str, content: str, bot_context: str = None):
    """Add a message to conversation history."""
    async with await get_db() as db:
        await db.execute("""
            INSERT INTO conversations (user_id, role, content, bot_context)
            VALUES (?, ?, ?, ?)
        """, (user_id, role, content, bot_context))
        await db.commit()


async def get_conversation_history(user_id: int, limit: int = 20) -> List[Dict[str, Any]]:
    """Get recent conversation history for a user."""
    async with await get_db() as db:
        cursor = await db.execute("""
            SELECT role, content, created_at FROM conversations
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (user_id, limit))
        rows = await cursor.fetchall()
        return [dict(row) for row in reversed(rows)]


async def clear_conversation_history(user_id: int):
    """Clear conversation history for a user."""
    async with await get_db() as db:
        await db.execute("DELETE FROM conversations WHERE user_id = ?", (user_id,))
        await db.commit()


# Reminder Management
async def create_reminder(user_id: int, message: str, remind_at: datetime, 
                         repeat_type: str = None, repeat_interval: int = None) -> int:
    """Create a new reminder."""
    async with await get_db() as db:
        cursor = await db.execute("""
            INSERT INTO reminders (user_id, message, remind_at, repeat_type, repeat_interval)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, message, remind_at.isoformat(), repeat_type, repeat_interval))
        await db.commit()
        return cursor.lastrowid


async def get_pending_reminders(user_id: int = None) -> List[Dict[str, Any]]:
    """Get all pending reminders, optionally filtered by user."""
    async with await get_db() as db:
        if user_id:
            cursor = await db.execute("""
                SELECT * FROM reminders 
                WHERE user_id = ? AND is_completed = 0
                ORDER BY remind_at ASC
            """, (user_id,))
        else:
            cursor = await db.execute("""
                SELECT * FROM reminders 
                WHERE is_completed = 0 AND remind_at <= datetime('now')
                ORDER BY remind_at ASC
            """)
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def mark_reminder_complete(reminder_id: int):
    """Mark a reminder as completed."""
    async with await get_db() as db:
        await db.execute("UPDATE reminders SET is_completed = 1 WHERE id = ?", (reminder_id,))
        await db.commit()


async def delete_reminder(reminder_id: int, user_id: int) -> bool:
    """Delete a reminder."""
    async with await get_db() as db:
        cursor = await db.execute(
            "DELETE FROM reminders WHERE id = ? AND user_id = ?", 
            (reminder_id, user_id)
        )
        await db.commit()
        return cursor.rowcount > 0


# Notes Management
async def create_note(user_id: int, title: str, content: str, tags: List[str] = None) -> int:
    """Create a new note."""
    async with await get_db() as db:
        cursor = await db.execute("""
            INSERT INTO user_notes (user_id, title, content, tags)
            VALUES (?, ?, ?, ?)
        """, (user_id, title, content, json.dumps(tags or [])))
        await db.commit()
        return cursor.lastrowid


async def get_user_notes(user_id: int, search: str = None) -> List[Dict[str, Any]]:
    """Get all notes for a user, optionally filtered by search term."""
    async with await get_db() as db:
        if search:
            cursor = await db.execute("""
                SELECT * FROM user_notes 
                WHERE user_id = ? AND (title LIKE ? OR content LIKE ?)
                ORDER BY updated_at DESC
            """, (user_id, f"%{search}%", f"%{search}%"))
        else:
            cursor = await db.execute("""
                SELECT * FROM user_notes WHERE user_id = ?
                ORDER BY updated_at DESC
            """, (user_id,))
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def delete_note(note_id: int, user_id: int) -> bool:
    """Delete a note."""
    async with await get_db() as db:
        cursor = await db.execute(
            "DELETE FROM user_notes WHERE id = ? AND user_id = ?", 
            (note_id, user_id)
        )
        await db.commit()
        return cursor.rowcount > 0


# Task Management
async def create_task(user_id: int, title: str, description: str = None, 
                     due_date: datetime = None, priority: str = 'medium') -> int:
    """Create a new task."""
    async with await get_db() as db:
        cursor = await db.execute("""
            INSERT INTO tasks (user_id, title, description, due_date, priority)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, title, description, due_date.isoformat() if due_date else None, priority))
        await db.commit()
        return cursor.lastrowid


async def get_user_tasks(user_id: int, status: str = None) -> List[Dict[str, Any]]:
    """Get all tasks for a user."""
    async with await get_db() as db:
        if status:
            cursor = await db.execute("""
                SELECT * FROM tasks WHERE user_id = ? AND status = ?
                ORDER BY priority DESC, due_date ASC
            """, (user_id, status))
        else:
            cursor = await db.execute("""
                SELECT * FROM tasks WHERE user_id = ?
                ORDER BY status ASC, priority DESC, due_date ASC
            """, (user_id,))
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def update_task_status(task_id: int, user_id: int, status: str) -> bool:
    """Update task status."""
    async with await get_db() as db:
        completed_at = datetime.now().isoformat() if status == 'completed' else None
        cursor = await db.execute("""
            UPDATE tasks SET status = ?, completed_at = ?
            WHERE id = ? AND user_id = ?
        """, (status, completed_at, task_id, user_id))
        await db.commit()
        return cursor.rowcount > 0


async def delete_task(task_id: int, user_id: int) -> bool:
    """Delete a task."""
    async with await get_db() as db:
        cursor = await db.execute(
            "DELETE FROM tasks WHERE id = ? AND user_id = ?", 
            (task_id, user_id)
        )
        await db.commit()
        return cursor.rowcount > 0


# Custom Bot Management
async def create_custom_bot(owner_id: int, bot_name: str, bot_description: str, 
                           bot_type: str, config: Dict[str, Any] = None) -> int:
    """Create a new custom bot configuration."""
    async with await get_db() as db:
        cursor = await db.execute("""
            INSERT INTO custom_bots (owner_id, bot_name, bot_description, bot_type, config)
            VALUES (?, ?, ?, ?, ?)
        """, (owner_id, bot_name, bot_description, bot_type, json.dumps(config or {})))
        await db.commit()
        return cursor.lastrowid


async def get_user_bots(user_id: int) -> List[Dict[str, Any]]:
    """Get all custom bots created by a user."""
    async with await get_db() as db:
        cursor = await db.execute("""
            SELECT * FROM custom_bots WHERE owner_id = ?
            ORDER BY created_at DESC
        """, (user_id,))
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_bot_templates(category: str = None) -> List[Dict[str, Any]]:
    """Get available bot templates."""
    async with await get_db() as db:
        if category:
            cursor = await db.execute("""
                SELECT * FROM bot_templates WHERE category = ?
                ORDER BY popularity DESC
            """, (category,))
        else:
            cursor = await db.execute("""
                SELECT * FROM bot_templates ORDER BY popularity DESC
            """)
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def update_custom_bot(bot_id: int, owner_id: int, updates: Dict[str, Any]) -> bool:
    """Update a custom bot configuration."""
    async with await get_db() as db:
        set_clauses = []
        values = []
        for key, value in updates.items():
            if key in ['bot_name', 'bot_description', 'config', 'commands', 'triggers', 'responses', 'is_active']:
                set_clauses.append(f"{key} = ?")
                values.append(json.dumps(value) if isinstance(value, (dict, list)) else value)
        
        if not set_clauses:
            return False
        
        set_clauses.append("updated_at = CURRENT_TIMESTAMP")
        values.extend([bot_id, owner_id])
        
        cursor = await db.execute(f"""
            UPDATE custom_bots SET {', '.join(set_clauses)}
            WHERE id = ? AND owner_id = ?
        """, values)
        await db.commit()
        return cursor.rowcount > 0


# AI Personality Management
async def create_ai_personality(user_id: int, name: str, system_prompt: str, 
                                temperature: float = 0.7) -> int:
    """Create a new AI personality."""
    async with await get_db() as db:
        cursor = await db.execute("""
            INSERT INTO ai_personalities (user_id, name, system_prompt, temperature)
            VALUES (?, ?, ?, ?)
        """, (user_id, name, system_prompt, temperature))
        await db.commit()
        return cursor.lastrowid


async def get_user_personalities(user_id: int) -> List[Dict[str, Any]]:
    """Get all AI personalities for a user."""
    async with await get_db() as db:
        cursor = await db.execute("""
            SELECT * FROM ai_personalities WHERE user_id = ?
            ORDER BY created_at DESC
        """, (user_id,))
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def set_active_personality(user_id: int, personality_id: int) -> bool:
    """Set the active AI personality for a user."""
    async with await get_db() as db:
        # Deactivate all personalities for user
        await db.execute("UPDATE ai_personalities SET is_active = 0 WHERE user_id = ?", (user_id,))
        # Activate the selected one
        cursor = await db.execute("""
            UPDATE ai_personalities SET is_active = 1 
            WHERE id = ? AND user_id = ?
        """, (personality_id, user_id))
        await db.commit()
        return cursor.rowcount > 0


async def get_active_personality(user_id: int) -> Optional[Dict[str, Any]]:
    """Get the active AI personality for a user."""
    async with await get_db() as db:
        cursor = await db.execute("""
            SELECT * FROM ai_personalities 
            WHERE user_id = ? AND is_active = 1
        """, (user_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None


# Analytics
async def log_analytics(user_id: int, event_type: str, event_data: Dict[str, Any] = None):
    """Log an analytics event."""
    async with await get_db() as db:
        await db.execute("""
            INSERT INTO analytics (user_id, event_type, event_data)
            VALUES (?, ?, ?)
        """, (user_id, event_type, json.dumps(event_data or {})))
        await db.commit()


async def get_user_analytics(user_id: int, days: int = 30) -> Dict[str, Any]:
    """Get analytics for a user."""
    async with await get_db() as db:
        # Get event counts
        cursor = await db.execute("""
            SELECT event_type, COUNT(*) as count FROM analytics
            WHERE user_id = ? AND created_at >= datetime('now', ?)
            GROUP BY event_type
        """, (user_id, f'-{days} days'))
        events = {row['event_type']: row['count'] for row in await cursor.fetchall()}
        
        # Get user stats
        cursor = await db.execute("""
            SELECT total_messages, total_commands, created_at FROM users WHERE user_id = ?
        """, (user_id,))
        user = await cursor.fetchone()
        
        return {
            'events': events,
            'total_messages': user['total_messages'] if user else 0,
            'total_commands': user['total_commands'] if user else 0,
            'member_since': user['created_at'] if user else None
        }


# Poll Management
async def create_poll(user_id: int, question: str, options: List[str], 
                     is_anonymous: bool = True, is_multiple_choice: bool = False,
                     closes_at: datetime = None) -> int:
    """Create a new poll."""
    async with await get_db() as db:
        cursor = await db.execute("""
            INSERT INTO polls (user_id, question, options, is_anonymous, is_multiple_choice, closes_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, question, json.dumps(options), int(is_anonymous), 
              int(is_multiple_choice), closes_at.isoformat() if closes_at else None))
        await db.commit()
        return cursor.lastrowid


async def vote_poll(poll_id: int, user_id: int, option_index: int) -> bool:
    """Vote on a poll."""
    async with await get_db() as db:
        cursor = await db.execute("SELECT votes, is_multiple_choice FROM polls WHERE id = ?", (poll_id,))
        row = await cursor.fetchone()
        if not row:
            return False
        
        votes = json.loads(row['votes'])
        user_key = str(user_id)
        
        if row['is_multiple_choice']:
            if user_key not in votes:
                votes[user_key] = []
            if option_index not in votes[user_key]:
                votes[user_key].append(option_index)
        else:
            votes[user_key] = option_index
        
        await db.execute("UPDATE polls SET votes = ? WHERE id = ?", (json.dumps(votes), poll_id))
        await db.commit()
        return True


async def get_poll_results(poll_id: int) -> Optional[Dict[str, Any]]:
    """Get poll results."""
    async with await get_db() as db:
        cursor = await db.execute("SELECT * FROM polls WHERE id = ?", (poll_id,))
        row = await cursor.fetchone()
        if not row:
            return None
        
        poll = dict(row)
        poll['options'] = json.loads(poll['options'])
        poll['votes'] = json.loads(poll['votes'])
        
        # Calculate vote counts
        vote_counts = [0] * len(poll['options'])
        for user_votes in poll['votes'].values():
            if isinstance(user_votes, list):
                for idx in user_votes:
                    vote_counts[idx] += 1
            else:
                vote_counts[user_votes] += 1
        
        poll['vote_counts'] = vote_counts
        poll['total_voters'] = len(poll['votes'])
        
        return poll
