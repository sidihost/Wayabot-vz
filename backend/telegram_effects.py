"""
Telegram Effects & Animations Module
Advanced Telegram Bot API features for stunning UX!

Features:
- Message reactions (auto-react to user messages)
- Animated typing sequences
- Progress indicators
- Success/failure animations
- Smart message editing
- Celebration effects
"""

import asyncio
import random
from typing import Optional, List, Union
from telegram import Update, Message, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode, ChatAction
from telegram.error import TelegramError


# =============================================================================
# REACTION EMOJIS - Telegram supported reactions
# =============================================================================

REACTIONS = {
    # Positive
    "love": "❤",
    "like": "👍",
    "fire": "🔥",
    "celebrate": "🎉",
    "wow": "😮",
    "cool": "😎",
    "star": "⭐",
    "clap": "👏",
    "hundred": "💯",
    "rocket": "🚀",
    
    # Thinking/Working
    "thinking": "🤔",
    "eyes": "👀",
    "brain": "🧠",
    
    # Success
    "check": "✅",
    "sparkles": "✨",
    "trophy": "🏆",
    
    # Error/Warning
    "sad": "😢",
    "warning": "⚠️",
}

# Success celebration sequences
SUCCESS_SEQUENCES = [
    ["Processing...", "Almost there...", "Done!"],
    ["Working on it...", "Creating magic...", "Ready!"],
    ["Let me think...", "Got it!", "Here you go!"],
]

# Bot creation celebration messages
BOT_CREATED_MESSAGES = [
    "Your AI bot is live!",
    "Bot created successfully!",
    "Your bot is ready to chat!",
    "Done! Your bot is online!",
]


# =============================================================================
# REACTION FUNCTIONS
# =============================================================================

async def react_to_message(
    message: Message,
    reaction: str = "like",
    is_big: bool = False
) -> bool:
    """
    Add a reaction to a user's message.
    
    Args:
        message: The message to react to
        reaction: Reaction key (e.g., "love", "fire", "celebrate")
        is_big: If True, shows a bigger animation
    
    Returns:
        True if successful, False otherwise
    """
    emoji = REACTIONS.get(reaction, reaction)
    
    try:
        await message.set_reaction(
            reaction=[{"type": "emoji", "emoji": emoji}],
            is_big=is_big
        )
        return True
    except TelegramError as e:
        # Silently fail - reactions might not be available in all chats
        print(f"[v0] Reaction failed: {e}")
        return False
    except Exception as e:
        print(f"[v0] Reaction error: {e}")
        return False


async def react_success(message: Message) -> bool:
    """Add a success reaction (random positive emoji)."""
    success_reactions = ["love", "fire", "celebrate", "star", "sparkles", "rocket", "hundred"]
    return await react_to_message(message, random.choice(success_reactions), is_big=True)


async def react_thinking(message: Message) -> bool:
    """Add a thinking reaction while processing."""
    return await react_to_message(message, "eyes")


async def react_error(message: Message) -> bool:
    """Add an error/sad reaction."""
    return await react_to_message(message, "sad")


async def react_and_reply(
    message: Message,
    text: str,
    reaction: str = "like",
    parse_mode: str = None,
    reply_markup = None
) -> Message:
    """React to message and send reply simultaneously."""
    # Fire both tasks concurrently
    react_task = asyncio.create_task(react_to_message(message, reaction))
    
    # Send the reply
    reply = await message.reply_text(
        text,
        parse_mode=parse_mode,
        reply_markup=reply_markup
    )
    
    # Wait for reaction to complete (don't block on it)
    try:
        await asyncio.wait_for(react_task, timeout=1.0)
    except:
        pass
    
    return reply


# =============================================================================
# ANIMATED TYPING & PROGRESS
# =============================================================================

async def show_typing(update: Update, duration: float = 1.0):
    """Show typing indicator for specified duration."""
    await update.message.chat.send_action(ChatAction.TYPING)
    await asyncio.sleep(duration)


async def animated_progress(
    message: Message,
    steps: List[str],
    final_text: str,
    delay: float = 0.8
) -> Message:
    """
    Show animated progress through multiple steps.
    
    Args:
        message: Message to edit
        steps: List of progress step messages
        final_text: Final message after all steps
        delay: Delay between steps in seconds
    
    Returns:
        The final edited message
    """
    for step in steps:
        try:
            await message.edit_text(step)
            await asyncio.sleep(delay)
        except TelegramError:
            pass
    
    try:
        await message.edit_text(final_text, parse_mode=ParseMode.MARKDOWN)
    except:
        pass
    
    return message


async def typing_dots_animation(
    message: Message,
    base_text: str = "Processing",
    duration: float = 2.0,
    interval: float = 0.4
) -> None:
    """
    Show animated dots while processing.
    
    Args:
        message: Message to animate
        base_text: Base text before dots
        duration: Total duration of animation
        interval: Time between dot updates
    """
    dots = [".", "..", "...", ""]
    elapsed = 0
    i = 0
    
    while elapsed < duration:
        try:
            await message.edit_text(f"{base_text}{dots[i % len(dots)]}")
        except:
            pass
        await asyncio.sleep(interval)
        elapsed += interval
        i += 1


async def progress_bar_animation(
    message: Message,
    total_steps: int = 5,
    step_delay: float = 0.5,
    complete_text: str = "Complete!"
) -> None:
    """
    Show a progress bar animation.
    
    Args:
        message: Message to animate
        total_steps: Number of progress steps
        step_delay: Delay between steps
        complete_text: Text to show when complete
    """
    for i in range(total_steps + 1):
        filled = "█" * i
        empty = "░" * (total_steps - i)
        percent = int((i / total_steps) * 100)
        
        try:
            await message.edit_text(f"[{filled}{empty}] {percent}%")
        except:
            pass
        
        if i < total_steps:
            await asyncio.sleep(step_delay)
    
    await asyncio.sleep(0.3)
    try:
        await message.edit_text(f"{complete_text}")
    except:
        pass


# =============================================================================
# SUCCESS CELEBRATIONS
# =============================================================================

async def celebrate_bot_creation(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    bot_name: str,
    share_link: str,
    greeting: str = None
) -> None:
    """
    Celebrate successful bot creation with animations.
    
    Args:
        update: Telegram update
        context: Bot context
        bot_name: Name of the created bot
        share_link: Shareable link for the bot
        greeting: Optional greeting message from the bot
    """
    message = update.message or update.callback_query.message
    
    # React to the original message with celebration
    if update.message:
        await react_to_message(update.message, "celebrate", is_big=True)
    
    # Send animated progress
    loading = await message.reply_text("Creating your bot...")
    
    steps = [
        "Setting up AI brain...",
        "Configuring personality...",
        "Generating responses...",
        "Almost ready..."
    ]
    
    for step in steps:
        await asyncio.sleep(0.6)
        try:
            await loading.edit_text(step)
        except:
            pass
    
    await asyncio.sleep(0.5)
    
    # Final success message with buttons
    keyboard = [
        [InlineKeyboardButton("Start Chatting", callback_data="start_chat")],
        [InlineKeyboardButton("Share Bot", url=share_link)],
        [InlineKeyboardButton("My Bots", callback_data="bb_my_bots")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    success_text = (
        f"*{bot_name}* is ready!\n\n"
        f"Share your bot:\n"
        f"`{share_link}`\n\n"
        f"Send a message to start chatting!"
    )
    
    try:
        await loading.edit_text(success_text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
    except:
        await message.reply_text(success_text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
    
    # Send bot greeting
    if greeting:
        await asyncio.sleep(0.5)
        await message.reply_text(f"*{bot_name}:* {greeting}", parse_mode=ParseMode.MARKDOWN)


async def celebrate_reminder_created(
    update: Update,
    reminder_text: str,
    reminder_time: str
) -> None:
    """Celebrate reminder creation."""
    if update.message:
        await react_to_message(update.message, "check", is_big=True)
    
    await asyncio.sleep(0.3)
    
    keyboard = [[InlineKeyboardButton("View Reminders", callback_data="view_reminders")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"Reminder set!\n\n"
        f"*{reminder_text}*\n"
        f"Time: {reminder_time}",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )


async def celebrate_poll_created(
    update: Update,
    question: str
) -> None:
    """Celebrate poll creation."""
    if update.message:
        await react_to_message(update.message, "fire", is_big=True)


async def celebrate_task_done(update: Update, task_text: str) -> None:
    """Celebrate completing a task."""
    if update.message:
        await react_to_message(update.message, "trophy", is_big=True)
    
    await update.message.reply_text(
        f"Task completed!\n\n~~{task_text}~~",
        parse_mode=ParseMode.MARKDOWN
    )


# =============================================================================
# SMART MESSAGE EDITING
# =============================================================================

async def smart_edit_message(
    message: Message,
    new_text: str,
    parse_mode: str = None,
    reply_markup = None,
    animate: bool = False
) -> bool:
    """
    Smartly edit a message with optional animation.
    
    Args:
        message: Message to edit
        new_text: New text content
        parse_mode: Parse mode for formatting
        reply_markup: Optional inline keyboard
        animate: If True, show brief animation before final text
    
    Returns:
        True if successful
    """
    try:
        if animate:
            # Brief typing animation
            await message.edit_text("...")
            await asyncio.sleep(0.3)
        
        await message.edit_text(
            new_text,
            parse_mode=parse_mode,
            reply_markup=reply_markup
        )
        return True
    except TelegramError as e:
        if "message is not modified" in str(e).lower():
            return True  # Same content, consider success
        print(f"[v0] Edit failed: {e}")
        return False
    except Exception as e:
        print(f"[v0] Edit error: {e}")
        return False


async def streaming_text_effect(
    message: Message,
    full_text: str,
    chunk_size: int = 10,
    delay: float = 0.1
) -> None:
    """
    Simulate streaming text effect by revealing text progressively.
    Note: Use sparingly as it makes many API calls.
    
    Args:
        message: Message to update
        full_text: Complete text to reveal
        chunk_size: Characters to reveal per update
        delay: Delay between updates
    """
    current = ""
    for i in range(0, len(full_text), chunk_size):
        current = full_text[:i + chunk_size]
        try:
            await message.edit_text(current + " |")
        except:
            pass
        await asyncio.sleep(delay)
    
    # Final update without cursor
    try:
        await message.edit_text(full_text)
    except:
        pass


# =============================================================================
# QUICK RESPONSE HELPERS
# =============================================================================

async def quick_success(update: Update, text: str) -> Message:
    """Quick success response with reaction."""
    await react_success(update.message)
    return await update.message.reply_text(f"Done! {text}")


async def quick_error(update: Update, text: str) -> Message:
    """Quick error response with reaction."""
    await react_error(update.message)
    return await update.message.reply_text(f"Error: {text}")


async def quick_working(update: Update, text: str = "Working on it...") -> Message:
    """Quick working indicator with thinking reaction."""
    await react_thinking(update.message)
    await update.message.chat.send_action(ChatAction.TYPING)
    return await update.message.reply_text(text)


# =============================================================================
# DICE & FUN ANIMATIONS
# =============================================================================

async def send_dice_animation(update: Update, emoji: str = "🎲") -> Message:
    """
    Send an animated dice.
    
    Args:
        emoji: One of 🎲, 🎯, 🏀, ⚽, 🎳, 🎰
    
    Returns:
        Message with the dice result
    """
    return await update.message.reply_dice(emoji=emoji)


async def send_celebration_sticker(update: Update) -> None:
    """Send a celebration (this would need a sticker file ID)."""
    # Placeholder - would need actual sticker file_id
    pass


# =============================================================================
# CONTEXTUAL AUTO-REACTIONS
# =============================================================================

async def auto_react_to_message(
    message: Message,
    message_text: str
) -> None:
    """
    Automatically add appropriate reaction based on message content.
    
    Args:
        message: User's message
        message_text: Text content of message
    """
    text_lower = message_text.lower()
    
    # Detect intent and react appropriately
    if any(word in text_lower for word in ["thanks", "thank you", "thx", "awesome", "great", "love"]):
        await react_to_message(message, "love")
    elif any(word in text_lower for word in ["help", "please", "can you", "could you"]):
        await react_to_message(message, "eyes")
    elif any(word in text_lower for word in ["build", "create", "make"]):
        await react_to_message(message, "rocket")
    elif any(word in text_lower for word in ["remind", "reminder", "schedule"]):
        await react_to_message(message, "check")
    elif any(word in text_lower for word in ["wow", "amazing", "incredible"]):
        await react_to_message(message, "fire", is_big=True)
    elif any(word in text_lower for word in ["?", "how", "what", "why", "when"]):
        await react_to_message(message, "thinking")
    elif any(word in text_lower for word in ["hi", "hello", "hey", "good morning", "good evening"]):
        await react_to_message(message, "like")
