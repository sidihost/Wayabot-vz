"""
Waya Bot Builder - AI Engine Module
Multi-provider AI: DigitalOcean Gradient, Groq, OpenAI-compatible
"""

import os
import json
import httpx
from typing import Optional, Dict, Any, List
from datetime import datetime

# Try to import Groq, but make it optional
try:
    from groq import AsyncGroq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False
    AsyncGroq = None

# AI Provider configuration
# Priority: DIGITALOCEAN > GROQ > OPENAI_COMPATIBLE
AI_PROVIDER = os.environ.get("AI_PROVIDER", "auto").lower()  # auto, digitalocean, groq, openai

# DigitalOcean Gradient configuration
DO_API_KEY = os.environ.get("DIGITALOCEAN_API_KEY") or os.environ.get("DO_API_KEY")
DO_BASE_URL = "https://inference.do-ai.run/v1"
DO_MODEL = os.environ.get("DO_MODEL", "meta-llama/Llama-3.3-70B-Instruct-Turbo")

# Groq configuration
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")

# OpenAI-compatible configuration (fallback)
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

# Determine best available provider
def get_ai_provider() -> str:
    """Determine which AI provider to use based on available keys."""
    if AI_PROVIDER != "auto":
        return AI_PROVIDER
    
    # Auto-detect: prioritize DigitalOcean > Groq > OpenAI
    if DO_API_KEY:
        return "digitalocean"
    if GROQ_API_KEY and GROQ_AVAILABLE:
        return "groq"
    if OPENAI_API_KEY:
        return "openai"
    
    # Default to digitalocean if nothing is set (will fail gracefully)
    return "digitalocean"

# Model configuration based on provider
def get_model_config() -> tuple[str, str, str]:
    """Get (base_url, api_key, model) for current provider."""
    provider = get_ai_provider()
    
    if provider == "digitalocean":
        return (DO_BASE_URL, DO_API_KEY, DO_MODEL)
    elif provider == "groq":
        return (None, GROQ_API_KEY, GROQ_MODEL)  # Groq uses its own client
    elif provider == "openai":
        return (OPENAI_BASE_URL, OPENAI_API_KEY, OPENAI_MODEL)
    else:
        return (DO_BASE_URL, DO_API_KEY, DO_MODEL)

# Legacy compatibility
BEST_MODEL = GROQ_MODEL
FALLBACK_MODEL = "llama-3.1-8b-instant"
REASONING_MODEL = BEST_MODEL
COMPOUND_MODEL = BEST_MODEL

# Whisper model for voice
WHISPER_MODEL = "whisper-large-v3-turbo"

# Fallback chain for Groq
MODEL_FALLBACK_CHAIN = [
    GROQ_MODEL,
    "llama-3.1-8b-instant",
]


async def compound_response(user_message: str, conversation_history: list = None) -> str:
    """
    Agentic AI with tools - uses universal chat completion.
    """
    system_msg = """You are an advanced AI with tools:
- Web search for current info
- Code execution  
- Visit websites

Be helpful, concise. Use tools when needed."""
    
    messages = [{"role": "system", "content": system_msg}]
    
    if conversation_history:
        for msg in conversation_history[-10:]:
            messages.append({"role": msg.get("role"), "content": msg.get("content")})
    
    messages.append({"role": "user", "content": user_message})
    
    try:
        result = await chat_completion(messages, temperature=0.7, max_tokens=2000)
        if result:
            return result
    except Exception as e:
        print(f"Compound error: {e}")
    
    # Fallback to regular response
    return await generate_response(user_message, conversation_history)


# Initialize client
groq_client: Optional[AsyncGroq] = None


async def transcribe_voice(audio_bytes: bytes, prompt: str = None) -> str:
    """
    Transcribe voice using Groq Whisper.
    Note: Voice transcription requires Groq API key.
    """
    client = get_groq_client()
    if not client:
        print("[AI] Voice transcription unavailable - Groq not configured")
        return None
    
    import io
    audio_file = io.BytesIO(audio_bytes)
    audio_file.name = "voice.ogg"
    
    try:
        transcription = await client.audio.transcriptions.create(
            file=audio_file,
            model=WHISPER_MODEL,
            prompt=prompt or "Transcribe this voice message. It's a Telegram voice message.",
            response_format="text",
            temperature=0.0
        )
        # Handle different response formats
        if isinstance(transcription, str):
            return transcription
        elif hasattr(transcription, 'text'):
            return transcription.text
        else:
            return str(transcription)
    except Exception as e:
        print(f"Whisper transcription error: {e}")
        return None


async def translate_audio(audio_bytes: bytes, target_language: str = "en") -> str:
    """
    Translate audio to text in target language.
    Note: Audio translation requires Groq API key.
    """
    client = get_groq_client()
    if not client:
        print("[AI] Audio translation unavailable - Groq not configured")
        return None
    
    import io
    audio_file = io.BytesIO(audio_bytes)
    audio_file.name = "voice.ogg"
    
    try:
        translation = await client.audio.translations.create(
            file=audio_file,
            model="whisper-large-v3",
            language=target_language,
            response_format="text",
            temperature=0.0
        )
        return translation.text
    except Exception as e:
        print(f"Translation error: {e}")
        return None


# Initialize clients
groq_client: Optional[Any] = None
http_client: Optional[httpx.AsyncClient] = None


def get_groq_client():
    """Get or create Groq client (only if Groq is available)."""
    global groq_client
    if not GROQ_AVAILABLE:
        return None
    if groq_client is None:
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            return None
        groq_client = AsyncGroq(api_key=api_key)
    return groq_client


def get_http_client() -> httpx.AsyncClient:
    """Get or create HTTP client for OpenAI-compatible APIs."""
    global http_client
    if http_client is None:
        http_client = httpx.AsyncClient(timeout=60.0)
    return http_client


def reset_clients():
    """Reset all AI clients."""
    global groq_client, http_client
    groq_client = None
    http_client = None


async def chat_completion(
    messages: List[Dict[str, str]],
    temperature: float = 0.7,
    max_tokens: int = 1500
) -> Optional[str]:
    """
    Universal chat completion that works with any provider.
    Tries providers in order: DigitalOcean > Groq > OpenAI
    """
    provider = get_ai_provider()
    print(f"[AI] Using provider: {provider}")
    
    # Try DigitalOcean Gradient first
    if provider == "digitalocean" and DO_API_KEY:
        try:
            result = await _do_chat_completion(messages, temperature, max_tokens)
            if result:
                return result
        except Exception as e:
            print(f"[AI] DigitalOcean failed: {e}")
    
    # Try Groq
    if (provider == "groq" or provider == "digitalocean") and GROQ_API_KEY and GROQ_AVAILABLE:
        try:
            result = await _groq_chat_completion(messages, temperature, max_tokens)
            if result:
                return result
        except Exception as e:
            print(f"[AI] Groq failed: {e}")
    
    # Try OpenAI-compatible
    if OPENAI_API_KEY:
        try:
            result = await _openai_chat_completion(messages, temperature, max_tokens)
            if result:
                return result
        except Exception as e:
            print(f"[AI] OpenAI failed: {e}")
    
    return None


async def _do_chat_completion(
    messages: List[Dict[str, str]],
    temperature: float,
    max_tokens: int
) -> Optional[str]:
    """DigitalOcean Gradient chat completion."""
    client = get_http_client()
    
    response = await client.post(
        f"{DO_BASE_URL}/chat/completions",
        headers={
            "Authorization": f"Bearer {DO_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": DO_MODEL,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        return data["choices"][0]["message"]["content"]
    else:
        error_text = response.text
        print(f"[AI] DigitalOcean error {response.status_code}: {error_text}")
        raise Exception(f"DigitalOcean API error: {response.status_code}")


async def _groq_chat_completion(
    messages: List[Dict[str, str]],
    temperature: float,
    max_tokens: int
) -> Optional[str]:
    """Groq chat completion."""
    client = get_groq_client()
    if not client:
        return None
    
    # Try models in fallback chain
    for model in MODEL_FALLBACK_CHAIN:
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"[AI] Groq model {model} failed: {e}")
            continue
    
    return None


async def _openai_chat_completion(
    messages: List[Dict[str, str]],
    temperature: float,
    max_tokens: int
) -> Optional[str]:
    """OpenAI-compatible chat completion."""
    client = get_http_client()
    
    response = await client.post(
        f"{OPENAI_BASE_URL}/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": OPENAI_MODEL,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        return data["choices"][0]["message"]["content"]
    else:
        raise Exception(f"OpenAI API error: {response.status_code}")


# Default system prompt for Waya - World-class AI Bot Platform
WAYA_SYSTEM_PROMPT = """You are Waya, the world's most advanced AI-powered Telegram bot creation platform.

## IDENTITY
You are not just a chatbot - you are a complete bot creation studio that makes BotFather look like a typewriter. Users describe what they want in plain English, and you build production-ready bots in seconds.

## CORE CAPABILITIES

### BOT CREATION (Your Superpower)
When someone describes a bot:
1. Understand their vision instantly
2. Generate a complete, working bot configuration  
3. Create a REAL Telegram bot they can share with anyone
4. No coding required - just describe and deploy

Examples of bots you can create:
- Customer support bots with FAQ, live chat escalation
- E-commerce bots with product catalogs, carts, payments
- Community bots with moderation, welcome messages, games
- Personal assistant bots with scheduling, reminders, notes
- Educational bots with quizzes, flashcards, progress tracking
- Any custom bot the user can imagine

### PRODUCTIVITY TOOLS
- Reminders: Natural language scheduling ("remind me to call mom every Sunday at 2pm")
- Notes: Save anything, search with AI, organize automatically
- Tasks: Track todos with priorities, deadlines, and smart suggestions

### AI ASSISTANT
- Answer questions with current knowledge
- Translate 100+ languages instantly  
- Summarize documents, articles, conversations
- Help with coding, writing, analysis, creative work
- Voice message understanding with emotion detection

## COMMUNICATION STYLE
- Concise and direct - no fluff or corporate speak
- Warm but efficient - respect the user's time
- Match the user's energy level
- Use bullet points and structure for clarity
- Never say "I cannot" - find alternatives

## BOT BUILDING FLOW
When user wants a bot:
1. If their description is clear: Generate the bot immediately
2. If unclear: Ask ONE specific question to clarify
3. Present the bot with: name, description, features, sample interactions
4. Offer: "Create Real Bot" (shareable @username) or "Test Here First"

## RESPONSE FORMAT
- First line: Address the core request
- Keep responses under 150 words unless detail is needed
- Use formatting: *bold* for emphasis, `code` for commands
- End with a clear next action when appropriate

## AVAILABLE COMMANDS
/build - Create a new bot
/mybots - Your bot collection  
/remind [text] - Set reminder
/note [text] - Save note
/task [text] - Create task
/help - Command reference

You represent the future of bot creation. Make every interaction feel like magic."""


# Specialized prompts for different bot types
BOT_TYPE_PROMPTS = {
    "customer_support": """You are a helpful customer support assistant. Your role is to:
- Listen carefully to customer issues
- Provide clear and helpful solutions
- Be empathetic and professional
- Escalate complex issues appropriately
- Follow up to ensure satisfaction""",

    "faq": """You are an FAQ assistant. Your role is to:
- Answer frequently asked questions accurately
- Provide clear and concise responses
- Direct users to relevant resources
- Admit when you don't know something""",

    "personal_assistant": """You are a personal assistant. Your role is to:
- Help manage schedules and reminders
- Assist with task organization
- Provide helpful suggestions
- Be proactive about upcoming events
- Remember user preferences""",

    "quiz_master": """You are a quiz master. Your role is to:
- Create engaging quiz questions
- Provide educational content
- Give helpful explanations for answers
- Track scores and progress
- Encourage learning""",

    "creative_writer": """You are a creative writing assistant. Your role is to:
- Help generate creative content
- Provide writing suggestions and improvements
- Assist with brainstorming ideas
- Maintain consistent tone and style
- Offer constructive feedback""",

    "code_helper": """You are a coding assistant. Your role is to:
- Help debug code issues
- Explain programming concepts
- Suggest best practices
- Provide code examples
- Review and improve code""",

    "language_tutor": """You are a language learning tutor. Your role is to:
- Help users learn new languages
- Provide vocabulary and grammar lessons
- Create practice exercises
- Correct mistakes gently
- Encourage consistent practice""",

    "health_coach": """You are a health and wellness coach. Your role is to:
- Provide general health information
- Suggest workout routines
- Offer nutrition tips
- Encourage healthy habits
- Note: Always recommend consulting healthcare professionals for medical advice""",

    "news_curator": """You are a news curator. Your role is to:
- Summarize news articles
- Provide balanced perspectives
- Help users stay informed
- Filter content by user interests
- Highlight important stories""",

    "general": """You are a helpful general-purpose assistant. Adapt your responses based on user needs."""
}


async def generate_response(
    user_message: str,
    conversation_history: List[Dict[str, str]] = None,
    system_prompt: str = None,
    user_name: str = None,
    temperature: float = 0.7,
    max_tokens: int = 1024,
    emotion_context: Dict[str, Any] = None,
    empathic_mode: bool = False
) -> str:
    """Generate an AI response using the best available provider."""
    
    # Build the system prompt with user context
    base_prompt = system_prompt or WAYA_SYSTEM_PROMPT
    if user_name:
        base_prompt += f"\n\nYou are talking to {user_name}. Address them by name occasionally to be personal."
    
    base_prompt += f"\n\nCurrent date and time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    
    # Add emotion context for empathic responses
    if empathic_mode and emotion_context:
        dominant = emotion_context.get("dominant_emotion", "neutral")
        confidence = emotion_context.get("confidence", 0)
        response_style = emotion_context.get("response_style", "supportive")
        
        emotion_guidance = f"""

EMOTIONAL CONTEXT:
The user appears to be feeling {dominant} (confidence: {confidence:.0%}).
Respond in a {response_style} manner. Adapt your tone and language accordingly:
- If they seem stressed or anxious, be calming and reassuring
- If they seem happy or excited, match their positive energy
- If they seem sad, be gentle and supportive
- Always be authentic and genuine in your empathy
"""
        base_prompt += emotion_guidance
        
        # Adjust temperature based on emotional state
        if emotion_context.get("intensity") == "negative":
            temperature = max(0.4, temperature - 0.2)  # More stable for negative emotions
        elif emotion_context.get("intensity") == "positive":
            temperature = min(0.9, temperature + 0.1)  # More creative for positive
    
    messages = [{"role": "system", "content": base_prompt}]
    
    # Add conversation history
    if conversation_history:
        for msg in conversation_history[-10:]:  # Last 10 messages for context
            messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", "")
            })
    
    # Add current message
    messages.append({"role": "user", "content": user_message})
    
    # Use universal chat completion (tries all providers)
    try:
        result = await chat_completion(messages, temperature, max_tokens)
        if result:
            return result
    except Exception as e:
        print(f"[AI] All providers failed: {e}")
    
    return "I'm having trouble connecting right now. Please try again in a moment."


async def generate_response_streaming(
    user_message: str,
    conversation_history: List[Dict[str, str]] = None,
    system_prompt: str = None,
    user_name: str = None,
    temperature: float = 0.7,
    max_tokens: int = 1024
):
    """
    Generate AI response with streaming support.
    Falls back to non-streaming if Groq is not available.
    """
    # Build the system prompt
    base_prompt = system_prompt or WAYA_SYSTEM_PROMPT
    if user_name:
        base_prompt += f"\n\nYou are talking to {user_name}. Address them by name occasionally to be personal."
    
    base_prompt += f"\n\nCurrent date and time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    
    messages = [{"role": "system", "content": base_prompt}]
    
    # Add conversation history
    if conversation_history:
        for msg in conversation_history[-10:]:
            messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", "")
            })
    
    messages.append({"role": "user", "content": user_message})
    
    # Try Groq streaming first
    client = get_groq_client()
    if client:
        try:
            stream = await client.chat.completions.create(
                model=BEST_MODEL,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True
            )
            
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
            return
        except Exception as e:
            print(f"[AI] Groq streaming failed: {e}")
    
    # Fall back to non-streaming chat_completion
    try:
        result = await chat_completion(messages, temperature, max_tokens)
        if result:
            yield result
        else:
            yield "I'm having trouble connecting right now. Please try again in a moment."
    except Exception as e:
        yield "I apologize, but I encountered an issue. Please try again."


async def generate_empathic_response(
    user_message: str,
    user_name: str,
    dominant_emotion: str,
    emotion_intensity: str = "neutral"
) -> str:
    """Generate a deeply empathic response based on detected emotions."""
    empathy_prompts = {
        "positive": f"""You are responding to {user_name} who is feeling {dominant_emotion}.
They're in a positive emotional state. Match their energy - be warm, enthusiastic, and celebratory.
Share in their joy genuinely. Be encouraging and uplifting.""",
        
        "negative": f"""You are responding to {user_name} who is feeling {dominant_emotion}.
They may be going through a difficult time. Be gentle, compassionate, and supportive.
Acknowledge their feelings without trying to immediately fix things. 
Show genuine empathy and let them know it's okay to feel this way.
Offer comfort and support, not unsolicited advice.""",
        
        "neutral": f"""You are responding to {user_name} who seems to be in a {dominant_emotion} state.
Be warm, helpful, and attentive. Adapt your tone based on what they need."""
    }
    
    system_prompt = empathy_prompts.get(emotion_intensity, empathy_prompts["neutral"])
    system_prompt += "\n\nRespond naturally and authentically. Don't mention that you detected their emotions unless it feels natural."
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message}
    ]
    
    temp = 0.7 if emotion_intensity == "neutral" else (0.5 if emotion_intensity == "negative" else 0.8)
    
    try:
        result = await chat_completion(messages, temperature=temp, max_tokens=1024)
        return result or "I'm here for you."
    except Exception as e:
        return "I'm here for you."


async def generate_bot_suggestion(user_request: str) -> Dict[str, Any]:
    """Generate COMPLETE bot configuration using AI - world-class quality."""
    prompt = f"""You are a senior Telegram bot architect at a top tech company. Create an exceptional bot.

USER REQUEST: {user_request}

Generate a production-ready bot configuration as JSON:

{{
    "bot_name": "CreativeName",
    "bot_username_suggestion": "creative_name_bot",
    "bot_description": "Compelling 1-2 sentence description that makes users want to try it",
    "bot_type": "category (support/assistant/community/education/ecommerce/entertainment/utility)",
    "personality": {{
        "tone": "friendly/professional/casual/playful/authoritative",
        "traits": ["trait1", "trait2", "trait3"]
    }},
    "system_prompt": "Detailed personality and behavior instructions (be specific about how the bot should respond, its expertise, boundaries, and style)",
    "greeting_message": "Engaging welcome that immediately shows value (max 2 sentences)",
    "features": [
        {{
            "name": "Feature Name",
            "description": "What it does",
            "trigger": "How user activates it"
        }}
    ],
    "commands": [
        {{"command": "/start", "description": "Start the bot", "response": "Welcome message"}},
        {{"command": "/help", "description": "Get help", "response": "Help text with all commands"}},
        {{"command": "/custom", "description": "Relevant to bot purpose", "response": "Action response"}}
    ],
    "quick_replies": ["Suggested reply 1", "Suggested reply 2", "Suggested reply 3"],
    "sample_conversations": [
        {{"user": "Example question", "bot": "Example great response"}}
    ],
    "knowledge_areas": ["area1", "area2"],
    "response_style": {{
        "max_length": "concise/medium/detailed",
        "use_emoji": true,
        "formatting": "plain/markdown/structured"
    }}
}}

REQUIREMENTS:
1. Bot name should be memorable and brandable (2-3 words max)
2. System prompt must be detailed (100-300 words) defining personality, expertise, and response style
3. Include 3-5 genuinely useful features relevant to the bot's purpose
4. Commands should have real functionality, not just placeholders
5. Quick replies should cover common user intents
6. Sample conversation should demonstrate the bot's personality
7. Make it feel like a product from Google, Apple, or OpenAI

Return ONLY valid JSON, no explanations."""

    messages = [
        {"role": "system", "content": "You are a world-class Telegram bot architect. You create bots that feel magical - intuitive, helpful, and delightful to use. Every bot you design could be a successful product. Output only valid JSON."},
        {"role": "user", "content": prompt}
    ]

    try:
        result = await chat_completion(messages, temperature=0.7, max_tokens=1500)
        if not result:
            return _create_fallback_bot_config(user_request)
        
        try:
            config = json.loads(result)
            config['user_original_request'] = user_request
            return config
        except json.JSONDecodeError:
            import re
            json_match = re.search(r'\{[\s\S]*\}', result)
            if json_match:
                config = json.loads(json_match.group())
                config['user_original_request'] = user_request
                return config
            return _create_fallback_bot_config(user_request)
    except Exception as e:
        return _create_fallback_bot_config(user_request)


def _create_fallback_bot_config(user_request: str) -> Dict[str, Any]:
    """Create a high-quality fallback bot configuration when AI generation fails."""
    # Extract key words from request for personalization
    request_lower = user_request.lower()
    
    # Determine bot type and customize
    if any(w in request_lower for w in ['support', 'help', 'customer', 'service']):
        bot_type, name, desc = "support", "Support Assistant", "Friendly customer support that resolves issues quickly"
    elif any(w in request_lower for w in ['shop', 'store', 'buy', 'sell', 'product', 'order']):
        bot_type, name, desc = "ecommerce", "Shop Assistant", "Your personal shopping helper for browsing and ordering"
    elif any(w in request_lower for w in ['learn', 'teach', 'study', 'quiz', 'education']):
        bot_type, name, desc = "education", "Study Buddy", "Learn anything with interactive lessons and quizzes"
    elif any(w in request_lower for w in ['fitness', 'health', 'workout', 'diet', 'exercise']):
        bot_type, name, desc = "health", "Wellness Coach", "Your personal health and fitness companion"
    elif any(w in request_lower for w in ['fun', 'game', 'play', 'entertainment', 'joke']):
        bot_type, name, desc = "entertainment", "Fun Bot", "Entertainment and games to brighten your day"
    else:
        bot_type, name, desc = "assistant", "Smart Assistant", "Your intelligent AI helper for any task"
    
    return {
        "bot_name": name,
        "bot_username_suggestion": name.lower().replace(" ", "_") + "_bot",
        "bot_description": desc,
        "bot_type": bot_type,
        "personality": {"tone": "friendly", "traits": ["helpful", "patient", "knowledgeable"]},
        "system_prompt": f"You are {name}, an AI assistant. Your purpose: {user_request[:200]}. Be helpful, friendly, and concise. Always try to understand what the user needs and provide clear, actionable responses. If you don't know something, admit it and suggest alternatives.",
        "greeting_message": f"Hey! I'm {name}. {desc}. How can I help you today?",
        "features": [
            {"name": "AI Chat", "description": "Natural conversation on any topic", "trigger": "Just send a message"},
            {"name": "Quick Help", "description": "Get instant answers", "trigger": "/help"},
            {"name": "Smart Responses", "description": "Context-aware replies", "trigger": "Automatic"}
        ],
        "commands": [
            {"command": "/start", "description": "Start the bot", "response": f"Welcome! I'm {name}. {desc}"},
            {"command": "/help", "description": "Get help", "response": "Just send me a message and I'll help you out!"}
        ],
        "quick_replies": ["Tell me more", "Help me with...", "What can you do?"],
        "sample_conversations": [{"user": "Hello", "bot": f"Hey there! I'm {name}. What can I help you with?"}],
        "response_style": {"max_length": "concise", "use_emoji": True, "formatting": "markdown"},
        "user_original_request": user_request
        },
        "user_original_request": user_request
    }


async def analyze_message_intent(message: str) -> Dict[str, Any]:
    """Analyze the intent of a user message."""
    prompt = f"""Analyze the following message and determine the user's intent.

Message: {message}

Respond with a JSON object:
{{
    "intent": "primary intent (question, command, request, greeting, farewell, gratitude, complaint, other)",
    "sub_intent": "more specific intent if applicable",
    "entities": ["extracted entities like names, dates, locations, etc."],
    "sentiment": "positive, negative, or neutral",
    "urgency": "high, medium, or low",
    "requires_action": true/false,
    "suggested_response_type": "informational, actionable, conversational, clarification"
}}

Only respond with valid JSON."""

    messages = [
        {"role": "system", "content": "You are a message intent analyzer. Respond only with valid JSON."},
        {"role": "user", "content": prompt}
    ]

    try:
        result = await chat_completion(messages, temperature=0.3, max_tokens=512)
        if not result:
            return {"intent": "other", "sentiment": "neutral"}
        
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            import re
            json_match = re.search(r'\{[\s\S]*\}', result)
            if json_match:
                return json.loads(json_match.group())
            return {"intent": "other", "sentiment": "neutral"}
    except Exception as e:
        return {"intent": "other", "error": str(e)}


async def parse_reminder_request(message: str) -> Dict[str, Any]:
    """Parse a reminder request from natural language."""
    current_time = datetime.now()
    
    prompt = f"""Parse this reminder request and extract the details.

Current time: {current_time.strftime('%Y-%m-%d %H:%M:%S')}
Message: {message}

Respond with JSON:
{{
    "reminder_text": "the thing to be reminded about",
    "datetime": "ISO format datetime string for when to remind (YYYY-MM-DDTHH:MM:SS)",
    "repeat": "none, daily, weekly, monthly, or null",
    "confidence": 0.0 to 1.0
}}

Only respond with valid JSON."""

    messages = [
        {"role": "system", "content": "You are a datetime parsing expert. Respond only with valid JSON."},
        {"role": "user", "content": prompt}
    ]

    try:
        result = await chat_completion(messages, temperature=0.2, max_tokens=256)
        if not result:
            return {"error": "AI service unavailable"}
        
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            import re
            json_match = re.search(r'\{[\s\S]*\}', result)
            if json_match:
                return json.loads(json_match.group())
            return {"error": "Could not parse reminder"}
    except Exception as e:
        return {"error": str(e)}


async def parse_task_request(message: str) -> Dict[str, Any]:
    """Parse a task creation request from natural language."""
    prompt = f"""Parse this task request and extract the details.

Message: {message}

Respond with JSON:
{{
    "title": "task title",
    "description": "task description or null",
    "due_date": "ISO format datetime if mentioned, or null",
    "priority": "low, normal, high, or urgent",
    "confidence": 0.0 to 1.0
}}

Priority must be one of: low, normal, high, urgent. Default to "normal" if not specified.
Only respond with valid JSON."""

    messages = [
        {"role": "system", "content": "You are a task parsing expert. Respond only with valid JSON."},
        {"role": "user", "content": prompt}
    ]

    try:
        result = await chat_completion(messages, temperature=0.2, max_tokens=256)
        if not result:
            return {"error": "AI service unavailable"}
        
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            import re
            json_match = re.search(r'\{[\s\S]*\}', result)
            if json_match:
                return json.loads(json_match.group())
            return {"error": "Could not parse task"}
    except Exception as e:
        return {"error": str(e)}


async def summarize_text(text: str, max_length: int = 200) -> str:
    """Summarize a piece of text."""
    messages = [
        {"role": "system", "content": f"Summarize the following text in {max_length} words or less. Be concise and capture the key points."},
        {"role": "user", "content": text}
    ]
    
    try:
        result = await chat_completion(messages, temperature=0.3, max_tokens=max_length * 2)
        return result or "Could not summarize the text."
    except Exception as e:
        return f"Error summarizing: {str(e)}"


async def translate_text(text: str, target_language: str) -> str:
    """Translate text to a target language."""
    messages = [
        {"role": "system", "content": f"Translate the following text to {target_language}. Provide only the translation, no explanations."},
        {"role": "user", "content": text}
    ]
    
    try:
        result = await chat_completion(messages, temperature=0.2, max_tokens=1024)
        return result or "Could not translate the text."
    except Exception as e:
        return f"Error translating: {str(e)}"


async def generate_quiz_question(topic: str, difficulty: str = "medium") -> Dict[str, Any]:
    """Generate a quiz question on a topic."""
    prompt = f"""Generate a {difficulty} difficulty quiz question about: {topic}

Respond with JSON:
{{
    "question": "the question text",
    "options": ["A) option1", "B) option2", "C) option3", "D) option4"],
    "correct_answer": "A, B, C, or D",
    "explanation": "brief explanation of the correct answer"
}}

Only respond with valid JSON."""

    messages = [
        {"role": "system", "content": "You are a quiz question generator. Respond only with valid JSON."},
        {"role": "user", "content": prompt}
    ]

    try:
        result = await chat_completion(messages, temperature=0.8, max_tokens=512)
        if not result:
            return {"error": "AI service unavailable"}
        
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            import re
            json_match = re.search(r'\{[\s\S]*\}', result)
            if json_match:
                return json.loads(json_match.group())
            return {"error": "Could not generate quiz"}
    except Exception as e:
        return {"error": str(e)}


async def get_smart_suggestions(user_context: Dict[str, Any]) -> List[str]:
    """Generate smart suggestions based on user context."""
    context_str = json.dumps(user_context, indent=2)
    
    prompt = f"""Based on the following user context, suggest 3-5 helpful actions or things the user might want to do next.

User Context:
{context_str}

Respond with a JSON array of suggestion strings:
["suggestion 1", "suggestion 2", "suggestion 3"]

Only respond with valid JSON array."""

    messages = [
        {"role": "system", "content": "You are a helpful assistant suggesting next actions. Respond only with a JSON array."},
        {"role": "user", "content": prompt}
    ]

    try:
        result = await chat_completion(messages, temperature=0.7, max_tokens=256)
        if not result:
            return ["Check your tasks", "Set a reminder", "Create a note"]
        
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            import re
            json_match = re.search(r'\[[\s\S]*\]', result)
            if json_match:
                return json.loads(json_match.group())
            return ["Check your reminders", "View your tasks", "Ask me anything!"]
    except Exception as e:
        return ["Check your reminders", "View your tasks", "Ask me anything!"]


def get_bot_system_prompt(bot_type: str, custom_instructions: str = None) -> str:
    """Get the system prompt for a specific bot type."""
    base_prompt = BOT_TYPE_PROMPTS.get(bot_type, BOT_TYPE_PROMPTS["general"])
    
    if custom_instructions:
        base_prompt += f"\n\nAdditional Instructions:\n{custom_instructions}"
    
    return base_prompt
