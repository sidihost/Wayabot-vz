"""
Waya Bot Builder - Telegram Animations System
Creates engaging animated responses using message editing for celebratory moments.
"""

import asyncio
import random
import logging
from typing import Optional, List, Dict, Any, Callable
from enum import Enum
from telegram_api import TelegramAPI, get_telegram_api

logger = logging.getLogger(__name__)


class AnimationType(Enum):
    """Available animation types"""
    CONFETTI = "confetti"
    ROCKET_LAUNCH = "rocket"
    CHECKMARK_PULSE = "checkmark"
    LOADING_DOTS = "loading"
    TYPING_EFFECT = "typing"
    SPARKLE = "sparkle"
    CELEBRATION = "celebration"
    PROGRESS_BAR = "progress"
    COUNTDOWN = "countdown"
    BUILDING = "building"


# =========================================================================
# ANIMATION FRAMES
# =========================================================================

CONFETTI_FRAMES = [
    "🎊",
    "🎊 🎉",
    "🎊 🎉 🎈",
    "🎊 🎉 🎈 ✨",
    "🎊 🎉 🎈 ✨ 🌟",
    """
    🎊 🎉 🎈 ✨ 🌟
         🎊 🎉 🎈
           ✨ 🌟
    """,
    """
   🎊  ✨  🎉  🌟  🎈
      🎊  🎉  ✨  🎈
   ✨  🌟  🎊  🎉  ✨
      🎈  ✨  🌟  🎊
   🎉  🎊  🎈  ✨  🌟
    """,
]

ROCKET_FRAMES = [
    "🚀",
    "    🚀\n   💨",
    "      🚀\n     💨\n    💨",
    "        🚀\n       💨\n      💨\n     💨",
    "          🚀\n         💨\n        💨\n       💨\n      💨",
    "            🚀\n           💨\n          💨\n         💨\n        💨\n       💨",
    "              🚀 ✨\n             💨\n            💨\n           💨\n          💨\n         💨\n        💨",
    "🚀 → → → → → → → 🌟",
]

CHECKMARK_FRAMES = [
    "○",
    "◔",
    "◑",
    "◕",
    "●",
    "✓",
    "✓ ✓",
    "✓ ✓ ✓",
    "✅",
    "✅ Done!",
]

LOADING_DOTS = [
    ".",
    "..",
    "...",
    "....",
    ".....",
    "......",
    ".......",
    "........",
]

SPARKLE_FRAMES = [
    "✨",
    "✨ ⭐",
    "✨ ⭐ 🌟",
    "⭐ 🌟 ✨ ⭐",
    "🌟 ✨ ⭐ 🌟 ✨",
    "✨ 🌟 ⭐ ✨ 🌟 ⭐",
    "🌟 ✨ ⭐ 🌟 ✨ ⭐ 🌟",
]

BUILDING_FRAMES = [
    "🔧 Building your bot...",
    "🔧 Building your bot.\n⚙️ Configuring AI...",
    "🔧 Building your bot..\n⚙️ Configuring AI.\n🧠 Training responses...",
    "🔧 Building your bot...\n⚙️ Configuring AI..\n🧠 Training responses.\n🔗 Setting up connections...",
    "🔧 Building your bot ✅\n⚙️ Configuring AI..\n🧠 Training responses.\n🔗 Setting up connections...",
    "🔧 Building your bot ✅\n⚙️ Configuring AI ✅\n🧠 Training responses..\n🔗 Setting up connections...",
    "🔧 Building your bot ✅\n⚙️ Configuring AI ✅\n🧠 Training responses ✅\n🔗 Setting up connections..",
    "🔧 Building your bot ✅\n⚙️ Configuring AI ✅\n🧠 Training responses ✅\n🔗 Setting up connections ✅",
]

PROGRESS_BAR_FRAMES = [
    "▱▱▱▱▱▱▱▱▱▱ 0%",
    "▰▱▱▱▱▱▱▱▱▱ 10%",
    "▰▰▱▱▱▱▱▱▱▱ 20%",
    "▰▰▰▱▱▱▱▱▱▱ 30%",
    "▰▰▰▰▱▱▱▱▱▱ 40%",
    "▰▰▰▰▰▱▱▱▱▱ 50%",
    "▰▰▰▰▰▰▱▱▱▱ 60%",
    "▰▰▰▰▰▰▰▱▱▱ 70%",
    "▰▰▰▰▰▰▰▰▱▱ 80%",
    "▰▰▰▰▰▰▰▰▰▱ 90%",
    "▰▰▰▰▰▰▰▰▰▰ 100% ✅",
]

CELEBRATION_MESSAGES = [
    "🎉 Your bot is LIVE!",
    "🚀 Launched and ready to go!",
    "✨ Magic complete! Bot activated!",
    "🏆 Success! Your bot is now online!",
    "⚡ Powered up and ready!",
    "🌟 Brilliant! Your bot is active!",
]

MILESTONE_CELEBRATIONS = {
    100: ["🎯 100 messages!", "Your bot just hit 100 messages! 🎉"],
    500: ["🔥 500 messages!", "Halfway to a thousand! Keep going! 💪"],
    1000: ["🏆 1,000 MESSAGES!", "Your bot is officially popular! 🌟"],
    5000: ["👑 5K Messages!", "Your bot is a superstar! ⭐"],
    10000: ["🚀 10,000 MESSAGES!", "Legendary status achieved! 🎊"],
}


# =========================================================================
# ANIMATION PLAYER
# =========================================================================

class AnimationPlayer:
    """Plays animations in Telegram chats via message editing"""
    
    def __init__(self, api: TelegramAPI):
        self.api = api
    
    async def play_animation(
        self,
        chat_id: int,
        message_id: int,
        animation_type: AnimationType,
        prefix: str = "",
        suffix: str = "",
        frame_delay: float = 0.3
    ) -> bool:
        """
        Play an animation by editing a message through frames.
        
        Args:
            chat_id: Chat to play animation in
            message_id: Message to edit for animation
            animation_type: Type of animation to play
            prefix: Text to show before animation
            suffix: Text to show after animation
            frame_delay: Delay between frames
        
        Returns:
            True if animation completed successfully
        """
        frames = self._get_frames(animation_type)
        
        for i, frame in enumerate(frames):
            text = f"{prefix}\n\n{frame}\n\n{suffix}".strip()
            
            success = await self.api._request("editMessageText", {
                "chat_id": chat_id,
                "message_id": message_id,
                "text": text,
                "parse_mode": "HTML"
            })
            
            # Continue even if "message not modified" error
            if not success.get("ok"):
                if "message is not modified" not in success.get("description", ""):
                    if "message to edit not found" in success.get("description", ""):
                        return False
            
            if i < len(frames) - 1:
                await asyncio.sleep(frame_delay)
        
        return True
    
    def _get_frames(self, animation_type: AnimationType) -> List[str]:
        """Get frames for an animation type"""
        frames_map = {
            AnimationType.CONFETTI: CONFETTI_FRAMES,
            AnimationType.ROCKET_LAUNCH: ROCKET_FRAMES,
            AnimationType.CHECKMARK_PULSE: CHECKMARK_FRAMES,
            AnimationType.LOADING_DOTS: LOADING_DOTS,
            AnimationType.SPARKLE: SPARKLE_FRAMES,
            AnimationType.PROGRESS_BAR: PROGRESS_BAR_FRAMES,
            AnimationType.BUILDING: BUILDING_FRAMES,
        }
        return frames_map.get(animation_type, LOADING_DOTS)
    
    async def send_animated_message(
        self,
        chat_id: int,
        final_text: str,
        animation_type: AnimationType = AnimationType.LOADING_DOTS,
        initial_text: str = "Processing...",
        frame_delay: float = 0.3
    ) -> Optional[Dict[str, Any]]:
        """
        Send a message, animate it, then show final text.
        
        Args:
            chat_id: Chat to send to
            final_text: Text to show after animation
            animation_type: Type of animation
            initial_text: Text for initial message
            frame_delay: Delay between frames
        
        Returns:
            The final message result
        """
        # Send initial message
        result = await self.api._request("sendMessage", {
            "chat_id": chat_id,
            "text": initial_text
        })
        
        if not result.get("ok"):
            return None
        
        message_id = result["result"]["message_id"]
        
        # Play animation
        await self.play_animation(
            chat_id, message_id, animation_type, 
            frame_delay=frame_delay
        )
        
        # Show final text
        final_result = await self.api._request("editMessageText", {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": final_text,
            "parse_mode": "HTML"
        })
        
        return final_result


# =========================================================================
# BOT CREATION ANIMATIONS
# =========================================================================

async def play_bot_creation_celebration(
    api: TelegramAPI,
    chat_id: int,
    bot_name: str
) -> Optional[int]:
    """
    Play full celebration sequence when a bot is created.
    
    Args:
        api: TelegramAPI instance
        chat_id: Chat ID
        bot_name: Name of the created bot
    
    Returns:
        Message ID of the celebration message
    """
    player = AnimationPlayer(api)
    
    # Step 1: Building animation
    build_msg = await api._request("sendMessage", {
        "chat_id": chat_id,
        "text": "🔧 Building your bot..."
    })
    
    if not build_msg.get("ok"):
        return None
    
    message_id = build_msg["result"]["message_id"]
    
    # Play building frames
    await player.play_animation(
        chat_id, message_id,
        AnimationType.BUILDING,
        frame_delay=0.4
    )
    
    await asyncio.sleep(0.3)
    
    # Step 2: Progress bar
    await api._request("editMessageText", {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": "⚡ Activating..."
    })
    
    await asyncio.sleep(0.5)
    
    # Step 3: Rocket launch
    await player.play_animation(
        chat_id, message_id,
        AnimationType.ROCKET_LAUNCH,
        frame_delay=0.25
    )
    
    await asyncio.sleep(0.3)
    
    # Step 4: Confetti explosion
    await player.play_animation(
        chat_id, message_id,
        AnimationType.CONFETTI,
        frame_delay=0.2
    )
    
    # Step 5: Final celebration message
    celebration = random.choice(CELEBRATION_MESSAGES)
    final_text = f"""
{celebration}

<b>🤖 {bot_name}</b>

Your AI-powered bot is now live and ready to chat!

<i>Tip: Your bot will automatically:</i>
• React to messages with relevant emojis
• Suggest smart replies
• Moderate content (if enabled)
• Schedule posts at optimal times

What would you like to do next?
    """.strip()
    
    await api._request("editMessageText", {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": final_text,
        "parse_mode": "HTML",
        "reply_markup": {
            "inline_keyboard": [
                [
                    {"text": "💬 Chat Now", "callback_data": "bot_chat"},
                    {"text": "⚙️ Settings", "callback_data": "bot_settings"}
                ],
                [
                    {"text": "🎯 Add Features", "callback_data": "bot_features"},
                    {"text": "📊 Analytics", "callback_data": "bot_analytics"}
                ],
                [
                    {"text": "📤 Share Bot", "callback_data": "bot_share"}
                ]
            ]
        }
    })
    
    return message_id


async def play_milestone_celebration(
    api: TelegramAPI,
    chat_id: int,
    milestone: int,
    bot_name: str
) -> Optional[int]:
    """
    Celebrate when a bot reaches a message milestone.
    
    Args:
        api: TelegramAPI instance
        chat_id: Chat ID
        milestone: The milestone number (100, 500, 1000, etc.)
        bot_name: Name of the bot
    
    Returns:
        Message ID
    """
    if milestone not in MILESTONE_CELEBRATIONS:
        return None
    
    title, subtitle = MILESTONE_CELEBRATIONS[milestone]
    player = AnimationPlayer(api)
    
    # Send initial sparkle
    result = await api._request("sendMessage", {
        "chat_id": chat_id,
        "text": "✨"
    })
    
    if not result.get("ok"):
        return None
    
    message_id = result["result"]["message_id"]
    
    # Play sparkle animation
    await player.play_animation(
        chat_id, message_id,
        AnimationType.SPARKLE,
        frame_delay=0.2
    )
    
    # Show milestone message
    final_text = f"""
{title}

<b>{bot_name}</b> has reached {milestone:,} messages!

{subtitle}

Keep building amazing experiences! 🚀
    """.strip()
    
    await api._request("editMessageText", {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": final_text,
        "parse_mode": "HTML"
    })
    
    return message_id


async def play_reminder_complete_animation(
    api: TelegramAPI,
    chat_id: int,
    reminder_title: str
) -> Optional[int]:
    """
    Play animation when a reminder is completed.
    
    Args:
        api: TelegramAPI instance
        chat_id: Chat ID
        reminder_title: Title of the completed reminder
    
    Returns:
        Message ID
    """
    player = AnimationPlayer(api)
    
    # Send initial message
    result = await api._request("sendMessage", {
        "chat_id": chat_id,
        "text": "○"
    })
    
    if not result.get("ok"):
        return None
    
    message_id = result["result"]["message_id"]
    
    # Play checkmark animation
    await player.play_animation(
        chat_id, message_id,
        AnimationType.CHECKMARK_PULSE,
        frame_delay=0.15
    )
    
    # Final message
    final_text = f"""
✅ <b>Reminder Complete!</b>

<s>{reminder_title}</s>

Great job staying on top of things! 🎯
    """.strip()
    
    await api._request("editMessageText", {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": final_text,
        "parse_mode": "HTML"
    })
    
    return message_id


async def play_feature_added_animation(
    api: TelegramAPI,
    chat_id: int,
    feature_name: str,
    feature_emoji: str = "⚡"
) -> Optional[int]:
    """
    Play animation when a new feature is added to a bot.
    
    Args:
        api: TelegramAPI instance
        chat_id: Chat ID
        feature_name: Name of the feature
        feature_emoji: Emoji for the feature
    
    Returns:
        Message ID
    """
    player = AnimationPlayer(api)
    
    # Send initial message
    result = await api._request("sendMessage", {
        "chat_id": chat_id,
        "text": "⚙️ Adding feature..."
    })
    
    if not result.get("ok"):
        return None
    
    message_id = result["result"]["message_id"]
    
    # Play progress animation
    await player.play_animation(
        chat_id, message_id,
        AnimationType.PROGRESS_BAR,
        frame_delay=0.15
    )
    
    await asyncio.sleep(0.2)
    
    # Play sparkle
    await player.play_animation(
        chat_id, message_id,
        AnimationType.SPARKLE,
        frame_delay=0.15
    )
    
    # Final message
    final_text = f"""
{feature_emoji} <b>Feature Added!</b>

<b>{feature_name}</b> is now active on your bot.

Your bot just got even smarter! 🧠
    """.strip()
    
    await api._request("editMessageText", {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": final_text,
        "parse_mode": "HTML"
    })
    
    return message_id


# =========================================================================
# TYPING EFFECT ANIMATION
# =========================================================================

async def send_with_typing_effect(
    api: TelegramAPI,
    chat_id: int,
    text: str,
    chars_per_frame: int = 3,
    frame_delay: float = 0.05,
    parse_mode: str = "HTML"
) -> Optional[int]:
    """
    Send a message with a typing effect (character by character).
    
    Args:
        api: TelegramAPI instance
        chat_id: Chat ID
        text: Text to type out
        chars_per_frame: Characters to add per frame
        frame_delay: Delay between frames
        parse_mode: Parse mode for final message
    
    Returns:
        Message ID
    """
    # For very short messages, just send normally
    if len(text) < 20:
        result = await api._request("sendMessage", {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode
        })
        if result.get("ok"):
            return result["result"]["message_id"]
        return None
    
    # Send initial cursor
    result = await api._request("sendMessage", {
        "chat_id": chat_id,
        "text": "▌"
    })
    
    if not result.get("ok"):
        return None
    
    message_id = result["result"]["message_id"]
    
    # Strip HTML for typing effect, will apply at end
    plain_text = text.replace("<b>", "").replace("</b>", "")
    plain_text = plain_text.replace("<i>", "").replace("</i>", "")
    plain_text = plain_text.replace("<code>", "").replace("</code>", "")
    
    # Type out characters
    current_text = ""
    for i in range(0, len(plain_text), chars_per_frame):
        current_text = plain_text[:i + chars_per_frame]
        display_text = current_text + "▌"
        
        await api._request("editMessageText", {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": display_text
        })
        
        await asyncio.sleep(frame_delay)
    
    # Final message with proper formatting
    await api._request("editMessageText", {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "parse_mode": parse_mode
    })
    
    return message_id


# =========================================================================
# LOADING ANIMATIONS
# =========================================================================

async def show_loading(
    api: TelegramAPI,
    chat_id: int,
    loading_text: str = "Processing",
    duration: float = 3.0
) -> Optional[int]:
    """
    Show a loading animation for a duration.
    
    Args:
        api: TelegramAPI instance
        chat_id: Chat ID
        loading_text: Text to show while loading
        duration: How long to show loading
    
    Returns:
        Message ID
    """
    result = await api._request("sendMessage", {
        "chat_id": chat_id,
        "text": f"{loading_text}."
    })
    
    if not result.get("ok"):
        return None
    
    message_id = result["result"]["message_id"]
    
    # Calculate frames
    frames = int(duration / 0.3)
    dots = [".", "..", "...", "....", "...", "..", "."]
    
    for i in range(frames):
        dot = dots[i % len(dots)]
        await api._request("editMessageText", {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": f"{loading_text}{dot}"
        })
        await asyncio.sleep(0.3)
    
    return message_id


# =========================================================================
# QUICK ANIMATIONS (Single emoji sequences)
# =========================================================================

QUICK_ANIMATIONS = {
    "success": ["⏳", "⌛", "✅"],
    "error": ["⏳", "⌛", "❌"],
    "thinking": ["🤔", "💭", "💡"],
    "love": ["💗", "💖", "💕", "❤️"],
    "fire": ["🔥", "🔥🔥", "🔥🔥🔥"],
    "star": ["⭐", "🌟", "✨"],
    "clap": ["👏", "👏👏", "👏👏👏"],
}


async def play_quick_animation(
    api: TelegramAPI,
    chat_id: int,
    message_id: int,
    animation_name: str,
    final_text: Optional[str] = None,
    frame_delay: float = 0.3
) -> bool:
    """
    Play a quick emoji animation sequence.
    
    Args:
        api: TelegramAPI instance
        chat_id: Chat ID
        message_id: Message to animate
        animation_name: Name of quick animation
        final_text: Optional text to show at end
        frame_delay: Delay between frames
    
    Returns:
        True if successful
    """
    frames = QUICK_ANIMATIONS.get(animation_name, ["⏳", "✅"])
    
    for frame in frames:
        await api._request("editMessageText", {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": frame
        })
        await asyncio.sleep(frame_delay)
    
    if final_text:
        await api._request("editMessageText", {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": final_text,
            "parse_mode": "HTML"
        })
    
    return True
