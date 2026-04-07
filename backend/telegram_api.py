"""
Waya Bot Builder - Advanced Telegram Bot API Wrapper
Provides enhanced functionality for reactions, animations, moderation, and more.
"""

import aiohttp
import asyncio
import logging
from typing import Optional, List, Dict, Any, Union
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

# Telegram Bot API base URL
TELEGRAM_API_BASE = "https://api.telegram.org/bot"


class ReactionEmoji(Enum):
    """Available reaction emojis in Telegram"""
    THUMBS_UP = "👍"
    THUMBS_DOWN = "👎"
    HEART = "❤"
    FIRE = "🔥"
    PARTY = "🎉"
    CRYING = "😢"
    LAUGHING = "😂"
    SURPRISED = "😮"
    ANGRY = "😡"
    THINKING = "🤔"
    MIND_BLOWN = "🤯"
    SCREAMING = "😱"
    CLAPPING = "👏"
    EYES = "👀"
    HUNDRED = "💯"
    ROCKET = "🚀"
    LIGHTNING = "⚡"
    PRAY = "🙏"
    MONOCLE = "🧐"
    POOP = "💩"
    BANANA = "🍌"
    TROPHY = "🏆"
    BROKEN_HEART = "💔"
    COLD = "🥶"
    HOT = "🥵"
    VOMITING = "🤮"
    CLOWN = "🤡"
    SLEEPY = "😴"
    NEUTRAL = "😐"
    STRAWBERRY = "🍓"
    CHAMPAGNE = "🍾"
    KISS = "💋"
    GHOST = "👻"
    ALIEN = "👽"
    ROBOT = "🤖"
    HEART_EYES = "😍"
    SALUTE = "🫡"
    SKULL = "💀"
    NERD = "🤓"
    WRITING = "✍"
    HUG = "🤗"


@dataclass
class ReactionType:
    """Represents a reaction type"""
    emoji: str
    type: str = "emoji"  # emoji or custom_emoji
    custom_emoji_id: Optional[str] = None


@dataclass
class ChatPermissions:
    """Chat permissions for users"""
    can_send_messages: bool = True
    can_send_audios: bool = True
    can_send_documents: bool = True
    can_send_photos: bool = True
    can_send_videos: bool = True
    can_send_video_notes: bool = True
    can_send_voice_notes: bool = True
    can_send_polls: bool = True
    can_send_other_messages: bool = True
    can_add_web_page_previews: bool = True
    can_change_info: bool = False
    can_invite_users: bool = True
    can_pin_messages: bool = False
    can_manage_topics: bool = False

    def to_dict(self) -> Dict[str, bool]:
        return {
            "can_send_messages": self.can_send_messages,
            "can_send_audios": self.can_send_audios,
            "can_send_documents": self.can_send_documents,
            "can_send_photos": self.can_send_photos,
            "can_send_videos": self.can_send_videos,
            "can_send_video_notes": self.can_send_video_notes,
            "can_send_voice_notes": self.can_send_voice_notes,
            "can_send_polls": self.can_send_polls,
            "can_send_other_messages": self.can_send_other_messages,
            "can_add_web_page_previews": self.can_add_web_page_previews,
            "can_change_info": self.can_change_info,
            "can_invite_users": self.can_invite_users,
            "can_pin_messages": self.can_pin_messages,
            "can_manage_topics": self.can_manage_topics,
        }


class TelegramAPI:
    """Advanced Telegram Bot API wrapper for agent features"""
    
    def __init__(self, bot_token: str):
        self.bot_token = bot_token
        self.base_url = f"{TELEGRAM_API_BASE}{bot_token}"
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session
    
    async def close(self):
        """Close the session"""
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def _request(
        self, 
        method: str, 
        data: Optional[Dict[str, Any]] = None,
        timeout: int = 30
    ) -> Dict[str, Any]:
        """Make a request to the Telegram API"""
        session = await self._get_session()
        url = f"{self.base_url}/{method}"
        
        try:
            async with session.post(url, json=data, timeout=aiohttp.ClientTimeout(total=timeout)) as response:
                result = await response.json()
                if not result.get("ok"):
                    error_code = result.get("error_code", "unknown")
                    description = result.get("description", "Unknown error")
                    logger.error(f"Telegram API error: {error_code} - {description}")
                return result
        except asyncio.TimeoutError:
            logger.error(f"Telegram API timeout for {method}")
            return {"ok": False, "error_code": "timeout", "description": "Request timed out"}
        except Exception as e:
            logger.error(f"Telegram API error for {method}: {e}")
            return {"ok": False, "error_code": "exception", "description": str(e)}
    
    # =========================================================================
    # REACTIONS
    # =========================================================================
    
    async def set_message_reaction(
        self,
        chat_id: Union[int, str],
        message_id: int,
        reaction: Union[str, List[str]],
        is_big: bool = False
    ) -> bool:
        """
        Set a reaction on a message.
        
        Args:
            chat_id: Chat ID
            message_id: Message ID to react to
            reaction: Single emoji or list of emojis
            is_big: Whether to show big animation
        
        Returns:
            True if successful
        """
        if isinstance(reaction, str):
            reaction = [reaction]
        
        reaction_types = [
            {"type": "emoji", "emoji": emoji}
            for emoji in reaction[:1]  # Telegram only allows one reaction per bot
        ]
        
        result = await self._request("setMessageReaction", {
            "chat_id": chat_id,
            "message_id": message_id,
            "reaction": reaction_types,
            "is_big": is_big
        })
        
        return result.get("ok", False)
    
    async def remove_reaction(
        self,
        chat_id: Union[int, str],
        message_id: int
    ) -> bool:
        """Remove bot's reaction from a message"""
        result = await self._request("setMessageReaction", {
            "chat_id": chat_id,
            "message_id": message_id,
            "reaction": []
        })
        return result.get("ok", False)
    
    # =========================================================================
    # ANIMATED MESSAGE EDITING
    # =========================================================================
    
    async def edit_message_animated(
        self,
        chat_id: Union[int, str],
        message_id: int,
        frames: List[str],
        frame_delay: float = 0.5,
        parse_mode: str = "HTML"
    ) -> bool:
        """
        Create animation by editing a message through multiple frames.
        
        Args:
            chat_id: Chat ID
            message_id: Message ID to edit
            frames: List of text frames to cycle through
            frame_delay: Delay between frames in seconds
            parse_mode: Parse mode for the text
        
        Returns:
            True if successful
        """
        for i, frame in enumerate(frames):
            result = await self._request("editMessageText", {
                "chat_id": chat_id,
                "message_id": message_id,
                "text": frame,
                "parse_mode": parse_mode
            })
            
            if not result.get("ok"):
                # If we get "message not modified" error, continue anyway
                if "message is not modified" not in result.get("description", ""):
                    return False
            
            # Don't delay after the last frame
            if i < len(frames) - 1:
                await asyncio.sleep(frame_delay)
        
        return True
    
    async def send_typing_then_message(
        self,
        chat_id: Union[int, str],
        text: str,
        typing_duration: float = 2.0,
        **kwargs
    ) -> Dict[str, Any]:
        """Send typing action, then send message"""
        # Send typing action
        await self._request("sendChatAction", {
            "chat_id": chat_id,
            "action": "typing"
        })
        
        await asyncio.sleep(typing_duration)
        
        # Send the actual message
        return await self._request("sendMessage", {
            "chat_id": chat_id,
            "text": text,
            **kwargs
        })
    
    # =========================================================================
    # STICKERS & ANIMATIONS
    # =========================================================================
    
    async def send_sticker(
        self,
        chat_id: Union[int, str],
        sticker: str,
        reply_to_message_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Send a sticker.
        
        Args:
            chat_id: Chat ID
            sticker: Sticker file_id or URL
            reply_to_message_id: Optional message to reply to
        """
        data = {
            "chat_id": chat_id,
            "sticker": sticker
        }
        if reply_to_message_id:
            data["reply_to_message_id"] = reply_to_message_id
        
        return await self._request("sendSticker", data)
    
    async def send_animation(
        self,
        chat_id: Union[int, str],
        animation: str,
        caption: Optional[str] = None,
        reply_to_message_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Send an animation (GIF)"""
        data = {
            "chat_id": chat_id,
            "animation": animation
        }
        if caption:
            data["caption"] = caption
        if reply_to_message_id:
            data["reply_to_message_id"] = reply_to_message_id
        
        return await self._request("sendAnimation", data)
    
    # =========================================================================
    # MODERATION
    # =========================================================================
    
    async def delete_message(
        self,
        chat_id: Union[int, str],
        message_id: int
    ) -> bool:
        """Delete a message"""
        result = await self._request("deleteMessage", {
            "chat_id": chat_id,
            "message_id": message_id
        })
        return result.get("ok", False)
    
    async def ban_chat_member(
        self,
        chat_id: Union[int, str],
        user_id: int,
        until_date: Optional[int] = None,
        revoke_messages: bool = False
    ) -> bool:
        """
        Ban a user from a chat.
        
        Args:
            chat_id: Chat ID
            user_id: User ID to ban
            until_date: Unix timestamp for unban (0 = forever)
            revoke_messages: Whether to delete all messages from the user
        """
        data = {
            "chat_id": chat_id,
            "user_id": user_id,
            "revoke_messages": revoke_messages
        }
        if until_date is not None:
            data["until_date"] = until_date
        
        result = await self._request("banChatMember", data)
        return result.get("ok", False)
    
    async def unban_chat_member(
        self,
        chat_id: Union[int, str],
        user_id: int,
        only_if_banned: bool = True
    ) -> bool:
        """Unban a user from a chat"""
        result = await self._request("unbanChatMember", {
            "chat_id": chat_id,
            "user_id": user_id,
            "only_if_banned": only_if_banned
        })
        return result.get("ok", False)
    
    async def restrict_chat_member(
        self,
        chat_id: Union[int, str],
        user_id: int,
        permissions: ChatPermissions,
        until_date: Optional[int] = None
    ) -> bool:
        """
        Restrict a chat member's permissions (mute).
        
        Args:
            chat_id: Chat ID
            user_id: User ID to restrict
            permissions: ChatPermissions object
            until_date: Unix timestamp when restriction expires
        """
        data = {
            "chat_id": chat_id,
            "user_id": user_id,
            "permissions": permissions.to_dict()
        }
        if until_date is not None:
            data["until_date"] = until_date
        
        result = await self._request("restrictChatMember", data)
        return result.get("ok", False)
    
    async def mute_user(
        self,
        chat_id: Union[int, str],
        user_id: int,
        duration_seconds: int = 3600
    ) -> bool:
        """
        Mute a user (restrict to read-only).
        
        Args:
            chat_id: Chat ID
            user_id: User ID to mute
            duration_seconds: How long to mute (default 1 hour)
        """
        import time
        until_date = int(time.time()) + duration_seconds
        
        muted_permissions = ChatPermissions(
            can_send_messages=False,
            can_send_audios=False,
            can_send_documents=False,
            can_send_photos=False,
            can_send_videos=False,
            can_send_video_notes=False,
            can_send_voice_notes=False,
            can_send_polls=False,
            can_send_other_messages=False,
            can_add_web_page_previews=False
        )
        
        return await self.restrict_chat_member(chat_id, user_id, muted_permissions, until_date)
    
    async def unmute_user(
        self,
        chat_id: Union[int, str],
        user_id: int
    ) -> bool:
        """Unmute a user (restore default permissions)"""
        default_permissions = ChatPermissions()
        return await self.restrict_chat_member(chat_id, user_id, default_permissions)
    
    async def get_chat_member(
        self,
        chat_id: Union[int, str],
        user_id: int
    ) -> Optional[Dict[str, Any]]:
        """Get information about a chat member"""
        result = await self._request("getChatMember", {
            "chat_id": chat_id,
            "user_id": user_id
        })
        if result.get("ok"):
            return result.get("result")
        return None
    
    async def get_chat_administrators(
        self,
        chat_id: Union[int, str]
    ) -> List[Dict[str, Any]]:
        """Get list of chat administrators"""
        result = await self._request("getChatAdministrators", {
            "chat_id": chat_id
        })
        if result.get("ok"):
            return result.get("result", [])
        return []
    
    # =========================================================================
    # INLINE KEYBOARDS & SUGGESTIONS
    # =========================================================================
    
    async def send_with_suggestions(
        self,
        chat_id: Union[int, str],
        text: str,
        suggestions: List[str],
        callback_prefix: str = "suggest",
        parse_mode: str = "HTML",
        row_width: int = 2
    ) -> Dict[str, Any]:
        """
        Send a message with suggestion buttons.
        
        Args:
            chat_id: Chat ID
            text: Message text
            suggestions: List of suggestion texts
            callback_prefix: Prefix for callback data
            parse_mode: Parse mode
            row_width: Number of buttons per row
        """
        # Build inline keyboard
        buttons = []
        for i, suggestion in enumerate(suggestions):
            buttons.append({
                "text": suggestion[:64],  # Telegram button text limit
                "callback_data": f"{callback_prefix}:{i}:{suggestion[:32]}"
            })
        
        # Arrange into rows
        keyboard = []
        for i in range(0, len(buttons), row_width):
            keyboard.append(buttons[i:i + row_width])
        
        return await self._request("sendMessage", {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "reply_markup": {
                "inline_keyboard": keyboard
            }
        })
    
    async def answer_callback_query(
        self,
        callback_query_id: str,
        text: Optional[str] = None,
        show_alert: bool = False
    ) -> bool:
        """Answer a callback query"""
        data = {"callback_query_id": callback_query_id}
        if text:
            data["text"] = text
        data["show_alert"] = show_alert
        
        result = await self._request("answerCallbackQuery", data)
        return result.get("ok", False)
    
    async def edit_message_reply_markup(
        self,
        chat_id: Union[int, str],
        message_id: int,
        reply_markup: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Edit inline keyboard of a message"""
        data = {
            "chat_id": chat_id,
            "message_id": message_id
        }
        if reply_markup:
            data["reply_markup"] = reply_markup
        
        result = await self._request("editMessageReplyMarkup", data)
        return result.get("ok", False)
    
    # =========================================================================
    # BOT CONFIGURATION
    # =========================================================================
    
    async def set_my_commands(
        self,
        commands: List[Dict[str, str]],
        scope: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Set bot commands"""
        data = {"commands": commands}
        if scope:
            data["scope"] = scope
        
        result = await self._request("setMyCommands", data)
        return result.get("ok", False)
    
    async def set_chat_menu_button(
        self,
        chat_id: Optional[Union[int, str]] = None,
        menu_button: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Set the bot's menu button"""
        data = {}
        if chat_id:
            data["chat_id"] = chat_id
        if menu_button:
            data["menu_button"] = menu_button
        
        result = await self._request("setChatMenuButton", data)
        return result.get("ok", False)
    
    async def get_me(self) -> Optional[Dict[str, Any]]:
        """Get bot info"""
        result = await self._request("getMe")
        if result.get("ok"):
            return result.get("result")
        return None
    
    # =========================================================================
    # WEBHOOK MANAGEMENT
    # =========================================================================
    
    async def set_webhook(
        self,
        url: str,
        certificate: Optional[str] = None,
        max_connections: int = 40,
        allowed_updates: Optional[List[str]] = None,
        drop_pending_updates: bool = False,
        secret_token: Optional[str] = None
    ) -> bool:
        """Set webhook for the bot"""
        data = {
            "url": url,
            "max_connections": max_connections,
            "drop_pending_updates": drop_pending_updates
        }
        if certificate:
            data["certificate"] = certificate
        if allowed_updates:
            data["allowed_updates"] = allowed_updates
        if secret_token:
            data["secret_token"] = secret_token
        
        result = await self._request("setWebhook", data)
        return result.get("ok", False)
    
    async def delete_webhook(
        self,
        drop_pending_updates: bool = False
    ) -> bool:
        """Delete webhook"""
        result = await self._request("deleteWebhook", {
            "drop_pending_updates": drop_pending_updates
        })
        return result.get("ok", False)
    
    async def get_webhook_info(self) -> Optional[Dict[str, Any]]:
        """Get current webhook info"""
        result = await self._request("getWebhookInfo")
        if result.get("ok"):
            return result.get("result")
        return None


# =========================================================================
# HELPER FUNCTIONS
# =========================================================================

def create_inline_keyboard(
    buttons: List[List[Dict[str, str]]]
) -> Dict[str, Any]:
    """Create an inline keyboard markup"""
    return {"inline_keyboard": buttons}


def create_reply_keyboard(
    buttons: List[List[str]],
    resize: bool = True,
    one_time: bool = False,
    placeholder: Optional[str] = None
) -> Dict[str, Any]:
    """Create a reply keyboard markup"""
    keyboard = [[{"text": btn} for btn in row] for row in buttons]
    markup = {
        "keyboard": keyboard,
        "resize_keyboard": resize,
        "one_time_keyboard": one_time
    }
    if placeholder:
        markup["input_field_placeholder"] = placeholder
    return markup


def create_remove_keyboard() -> Dict[str, Any]:
    """Create a remove keyboard markup"""
    return {"remove_keyboard": True}


# Singleton instances cache
_api_instances: Dict[str, TelegramAPI] = {}


def get_telegram_api(bot_token: str) -> TelegramAPI:
    """Get or create a TelegramAPI instance for a bot token"""
    if bot_token not in _api_instances:
        _api_instances[bot_token] = TelegramAPI(bot_token)
    return _api_instances[bot_token]


async def cleanup_all_instances():
    """Close all TelegramAPI instances"""
    for api in _api_instances.values():
        await api.close()
    _api_instances.clear()
