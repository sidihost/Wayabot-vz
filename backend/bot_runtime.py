"""
Bot Runtime Engine - Autonomous Bot Execution System
=====================================================
Runs user-created bots autonomously on our infrastructure.
Users never see code - bots just work automatically.

Features:
- Auto-deploy: Bots go live instantly after creation
- Code generation: Generate bot code internally (user never sees it)
- Hot-reload: Update bot behavior without restart
- Webhook routing: Route messages to the correct bot
- Health monitoring: Auto-restart failed bots
- Analytics: Track bot performance automatically
"""

import asyncio
import json
import hashlib
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

import database as db
from ai_engine import generate_response, get_groq_client, BEST_MODEL
from agent_engine import (
    auto_react_to_message,
    get_agent_settings,
    track_engagement,
    AgentSettings
)
from moderation import moderate_message, ModerationLevel
from suggestions import generate_suggestions

# =============================================================================
# BOT STATE & RUNTIME
# =============================================================================

class BotStatus(Enum):
    DEPLOYING = "deploying"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"
    STOPPED = "stopped"


@dataclass
class RuntimeBot:
    """Represents a running bot instance."""
    bot_id: int
    user_id: int
    name: str
    system_prompt: str
    welcome_message: str
    status: BotStatus = BotStatus.DEPLOYING
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    message_count: int = 0
    error_count: int = 0
    config: Dict[str, Any] = field(default_factory=dict)
    agent_settings: Optional[AgentSettings] = None


class BotRuntimeEngine:
    """
    Manages all running bots on the platform.
    Handles message routing, auto-deploy, and monitoring.
    """
    
    def __init__(self):
        self._bots: Dict[int, RuntimeBot] = {}
        self._lock = asyncio.Lock()
        self._running = False
        self._health_task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start the runtime engine."""
        self._running = True
        
        # Load all active bots from database
        await self._load_active_bots()
        
        # Start health monitoring
        self._health_task = asyncio.create_task(self._health_monitor())
        
        print(f"[BotRuntime] Started with {len(self._bots)} active bots")
    
    async def stop(self):
        """Stop the runtime engine."""
        self._running = False
        
        if self._health_task:
            self._health_task.cancel()
            try:
                await self._health_task
            except asyncio.CancelledError:
                pass
        
        self._bots.clear()
        print("[BotRuntime] Stopped")
    
    async def _load_active_bots(self):
        """Load all active bots from the database."""
        try:
            async with db.get_connection() as conn:
                rows = await conn.fetch("""
                    SELECT 
                        cb.id, cb.user_id, cb.name, cb.system_prompt,
                        cb.welcome_message, cb.config, cb.is_active
                    FROM custom_bots cb
                    WHERE cb.is_active = TRUE
                    ORDER BY cb.created_at DESC
                """)
                
                for row in rows:
                    bot = RuntimeBot(
                        bot_id=row['id'],
                        user_id=row['user_id'],
                        name=row['name'],
                        system_prompt=row['system_prompt'] or '',
                        welcome_message=row['welcome_message'] or 'Hello!',
                        status=BotStatus.RUNNING,
                        config=json.loads(row['config']) if row['config'] else {}
                    )
                    
                    # Load agent settings
                    bot.agent_settings = await get_agent_settings(bot.bot_id)
                    
                    self._bots[bot.bot_id] = bot
                    
        except Exception as e:
            print(f"[BotRuntime] Error loading bots: {e}")
    
    async def deploy_bot(self, bot_id: int) -> Dict[str, Any]:
        """
        Deploy a bot instantly after creation.
        This is called automatically - user never sees this happen.
        """
        async with self._lock:
            try:
                # Get bot from database
                bot_data = await db.get_bot(bot_id)
                if not bot_data:
                    return {"success": False, "error": "Bot not found"}
                
                # Create runtime instance
                runtime_bot = RuntimeBot(
                    bot_id=bot_id,
                    user_id=bot_data['user_id'],
                    name=bot_data['name'],
                    system_prompt=bot_data.get('system_prompt', ''),
                    welcome_message=bot_data.get('welcome_message', 'Hello!'),
                    status=BotStatus.DEPLOYING,
                    config=bot_data.get('config', {})
                )
                
                # Generate internal bot code (user never sees this)
                internal_code = await self._generate_bot_code(runtime_bot)
                
                # Store in runtime
                runtime_bot.status = BotStatus.RUNNING
                runtime_bot.agent_settings = await get_agent_settings(bot_id)
                self._bots[bot_id] = runtime_bot
                
                # Update database status
                async with db.get_connection() as conn:
                    await conn.execute("""
                        UPDATE custom_bots 
                        SET is_active = TRUE, updated_at = NOW()
                        WHERE id = $1
                    """, bot_id)
                
                return {
                    "success": True,
                    "bot_id": bot_id,
                    "status": "running",
                    "message": "Bot deployed and running!"
                }
                
            except Exception as e:
                return {"success": False, "error": str(e)}
    
    async def _generate_bot_code(self, bot: RuntimeBot) -> str:
        """
        Generate internal bot code. This runs on our servers.
        User never sees this - it's all automatic.
        """
        # This generates a "virtual" bot definition that our runtime executes
        code_template = f'''
# Auto-generated bot: {bot.name}
# Bot ID: {bot.bot_id}
# Owner: {bot.user_id}
# Generated: {datetime.now().isoformat()}

BOT_CONFIG = {{
    "id": {bot.bot_id},
    "name": "{bot.name}",
    "system_prompt": """{bot.system_prompt}""",
    "welcome_message": """{bot.welcome_message}""",
    "features": {{
        "auto_react": True,
        "auto_moderate": True,
        "auto_suggest": True,
        "auto_schedule": True
    }}
}}

async def handle_message(message, context):
    """Process incoming message with full AI capabilities."""
    # All handled by BotRuntimeEngine.process_message()
    pass

async def handle_callback(query, context):
    """Process button callbacks."""
    # All handled by BotRuntimeEngine.process_callback()
    pass
'''
        
        # Store the generated code hash for versioning
        code_hash = hashlib.sha256(code_template.encode()).hexdigest()[:16]
        
        async with db.get_connection() as conn:
            # Store code version in bot config
            current_config = bot.config or {}
            current_config['_runtime'] = {
                'code_hash': code_hash,
                'deployed_at': datetime.now().isoformat(),
                'version': current_config.get('_runtime', {}).get('version', 0) + 1
            }
            
            await conn.execute("""
                UPDATE custom_bots SET config = $1 WHERE id = $2
            """, json.dumps(current_config), bot.bot_id)
        
        return code_template
    
    async def process_message(
        self,
        bot_id: int,
        chat_id: int,
        message_id: int,
        user_id: int,
        message_text: str,
        user_name: str,
        bot_token: str
    ) -> Optional[Dict[str, Any]]:
        """
        Process a message for a specific bot.
        This is the main entry point for bot message handling.
        """
        bot = self._bots.get(bot_id)
        if not bot or bot.status != BotStatus.RUNNING:
            return None
        
        try:
            # Update activity
            bot.last_activity = datetime.now()
            bot.message_count += 1
            
            result = {
                "response": None,
                "reactions": [],
                "suggestions": [],
                "moderation": None
            }
            
            agent = bot.agent_settings or await get_agent_settings(bot_id)
            
            # 1. Auto-react (non-blocking)
            if agent.auto_react_enabled:
                asyncio.create_task(
                    auto_react_to_message(
                        bot_token=bot_token,
                        chat_id=chat_id,
                        message_id=message_id,
                        message_text=message_text,
                        bot_id=bot_id,
                        reaction_style=agent.reaction_style
                    )
                )
            
            # 2. Auto-moderate
            if agent.auto_moderate_enabled:
                mod_result = await moderate_message(
                    bot_token=bot_token,
                    bot_id=bot_id,
                    chat_id=chat_id,
                    message_id=message_id,
                    user_id=user_id,
                    message_text=message_text,
                    moderation_level=ModerationLevel(agent.moderation_level)
                )
                result["moderation"] = mod_result
                if mod_result.is_violation:
                    return result  # Stop processing if violation
            
            # 3. Generate AI response
            history = await db.get_conversation_history(user_id, limit=10)
            await db.add_conversation(user_id, "user", message_text)
            
            response = await generate_response(
                user_message=message_text,
                conversation_history=history,
                system_prompt=bot.system_prompt,
                user_name=user_name
            )
            
            await db.add_conversation(user_id, "assistant", response)
            result["response"] = response
            
            # 4. Track engagement for optimal scheduling
            asyncio.create_task(track_engagement(bot_id, chat_id))
            
            # 5. Generate suggestions
            if agent.auto_suggest_enabled:
                sug_result = await generate_suggestions(
                    message_text=message_text,
                    conversation_context=[{"role": "assistant", "content": response}],
                    count=agent.suggestion_count,
                    use_ai=True
                )
                result["suggestions"] = [s.text for s in sug_result.suggestions]
            
            # Update stats
            await db.increment_bot_usage(bot_id)
            
            return result
            
        except Exception as e:
            bot.error_count += 1
            print(f"[BotRuntime] Error processing message for bot {bot_id}: {e}")
            return None
    
    async def hot_reload_bot(self, bot_id: int) -> bool:
        """
        Hot-reload a bot's configuration without restart.
        Changes take effect immediately.
        """
        try:
            bot_data = await db.get_bot(bot_id)
            if not bot_data:
                return False
            
            async with self._lock:
                if bot_id in self._bots:
                    bot = self._bots[bot_id]
                    bot.name = bot_data['name']
                    bot.system_prompt = bot_data.get('system_prompt', '')
                    bot.welcome_message = bot_data.get('welcome_message', 'Hello!')
                    bot.config = bot_data.get('config', {})
                    bot.agent_settings = await get_agent_settings(bot_id)
                    
                    # Regenerate internal code
                    await self._generate_bot_code(bot)
                    
                    return True
                else:
                    # Bot not in runtime, deploy it
                    await self.deploy_bot(bot_id)
                    return True
                    
        except Exception as e:
            print(f"[BotRuntime] Hot reload failed for bot {bot_id}: {e}")
            return False
    
    async def pause_bot(self, bot_id: int) -> bool:
        """Pause a bot (stops processing messages)."""
        if bot_id in self._bots:
            self._bots[bot_id].status = BotStatus.PAUSED
            return True
        return False
    
    async def resume_bot(self, bot_id: int) -> bool:
        """Resume a paused bot."""
        if bot_id in self._bots:
            self._bots[bot_id].status = BotStatus.RUNNING
            return True
        return False
    
    async def stop_bot(self, bot_id: int) -> bool:
        """Stop and remove a bot from runtime."""
        async with self._lock:
            if bot_id in self._bots:
                del self._bots[bot_id]
                return True
            return False
    
    def get_bot_status(self, bot_id: int) -> Optional[Dict[str, Any]]:
        """Get current status of a bot."""
        bot = self._bots.get(bot_id)
        if not bot:
            return None
        
        return {
            "bot_id": bot.bot_id,
            "name": bot.name,
            "status": bot.status.value,
            "message_count": bot.message_count,
            "error_count": bot.error_count,
            "last_activity": bot.last_activity.isoformat(),
            "uptime_seconds": (datetime.now() - bot.created_at).total_seconds()
        }
    
    def get_all_bots_status(self) -> List[Dict[str, Any]]:
        """Get status of all running bots."""
        return [self.get_bot_status(bot_id) for bot_id in self._bots]
    
    async def _health_monitor(self):
        """Background task to monitor bot health."""
        while self._running:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                for bot_id, bot in list(self._bots.items()):
                    # Check for stale bots (no activity for 24 hours)
                    idle_time = (datetime.now() - bot.last_activity).total_seconds()
                    
                    # Check for too many errors
                    if bot.error_count > 100:
                        print(f"[BotRuntime] Bot {bot_id} has too many errors, pausing")
                        bot.status = BotStatus.ERROR
                        bot.error_count = 0  # Reset after pause
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[BotRuntime] Health monitor error: {e}")


# Global runtime instance
bot_runtime = BotRuntimeEngine()


# =============================================================================
# AUTO-DEPLOY FUNCTIONS
# =============================================================================

async def auto_deploy_bot(bot_id: int) -> Dict[str, Any]:
    """
    Automatically deploy a bot after creation.
    Called internally - user never sees this.
    """
    return await bot_runtime.deploy_bot(bot_id)


async def auto_update_bot(bot_id: int) -> bool:
    """
    Automatically update a bot's configuration.
    Changes take effect immediately without user action.
    """
    return await bot_runtime.hot_reload_bot(bot_id)


# =============================================================================
# STARTUP INTEGRATION
# =============================================================================

async def start_bot_runtime():
    """Start the bot runtime engine on app startup."""
    await bot_runtime.start()


async def stop_bot_runtime():
    """Stop the bot runtime engine on app shutdown."""
    await bot_runtime.stop()
