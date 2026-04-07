"""
Waya Bot Builder - AI Engine Module
🏆 MAX POWER: Llama 4 + Whisper + COMPOUND (Agentic AI with tools)!
"""

import os
import json
from typing import Optional, Dict, Any, List
from groq import AsyncGroq
from datetime import datetime

# Best Groq Models for maximum intelligence
BEST_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"  # Fastest and smartest
REASONING_MODEL = "deepseek-ai/DeepSeek-R1"  # For complex reasoning tasks
CREATIVE_MODEL = "meta-llama/llama-4-maverick-17b-128e-instruct"  # For creative tasks

# Whisper - fastest transcription
WHISPER_MODEL = "whisper-large-v3-turbo"

# COMPOUND - Agentic AI with tools
COMPOUND_MODEL = "compound-beta"  # Web search + code execution

# Bot Builder Intelligence Levels
INTELLIGENCE_LEVELS = {
    "basic": {"model": BEST_MODEL, "max_tokens": 1024, "temperature": 0.5},
    "standard": {"model": BEST_MODEL, "max_tokens": 2048, "temperature": 0.7},
    "advanced": {"model": REASONING_MODEL, "max_tokens": 4096, "temperature": 0.6},
    "creative": {"model": CREATIVE_MODEL, "max_tokens": 4096, "temperature": 0.85},
}


async def compound_response(user_message: str, conversation_history: list = None) -> str:
    """
    🤖 COMPOUND - Agentic AI with tools!
    Web search, code execution, visit websites autonomously!
    """
    client = get_groq_client()
    
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
        response = await client.chat.completions.create(
            model=COMPOUND_MODEL,
            messages=messages,
            temperature=0.7,
            max_tokens=2000
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Compound error: {e}")
        return await generate_response(user_message, conversation_history)


# Initialize client
groq_client: Optional[AsyncGroq] = None


async def transcribe_voice(audio_bytes: bytes, prompt: str = None) -> str:
    """
    🎙 Transcribe voice using Groq Whisper - FASTEST!
    Voice → Text in milliseconds!
    """
    client = get_groq_client()
    
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
        return transcription.text
    except Exception as e:
        print(f"Whisper error: {e}")
        return None


async def translate_audio(audio_bytes: bytes, target_language: str = "en") -> str:
    """
    🌐 Translate audio to text in target language!
    Uses Groq Whisper translation.
    """
    client = get_groq_client()
    
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


# Initialize Groq client
groq_client: Optional[AsyncGroq] = None


def get_groq_client() -> AsyncGroq:
    """Get or create Groq client."""
    global groq_client
    if groq_client is None:
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY environment variable is not set")
        groq_client = AsyncGroq(api_key=api_key)
    return groq_client


# Default system prompt for Waya
WAYA_SYSTEM_PROMPT = """You are Waya, an intelligent and friendly Telegram bot assistant. You are helpful, knowledgeable, and always aim to provide the best assistance possible.

Key traits:
- Friendly and approachable personality
- Highly knowledgeable across many topics
- Excellent at understanding context and user intent
- Can help with tasks, answer questions, provide recommendations
- Proactive in offering helpful suggestions
- Remembers context from the conversation

Current capabilities you can help users with:
- Creating and managing reminders
- Taking and organizing notes
- Managing tasks and to-do lists
- Building custom bots
- Answering questions on any topic
- Providing recommendations and suggestions
- Analyzing and summarizing content
- Language translation
- Creative writing assistance
- Coding help and explanations
- And much more!

Always be helpful, concise, and friendly. If you don't know something, admit it honestly.
When users ask about bot building, guide them through the process step by step."""


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
    """Generate an AI response using Groq with optional emotion awareness."""
    client = get_groq_client()
    
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
    
    try:
        response = await client.chat.completions.create(
            model=BEST_MODEL,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"I apologize, but I encountered an error: {str(e)}. Please try again."


async def generate_empathic_response(
    user_message: str,
    user_name: str,
    dominant_emotion: str,
    emotion_intensity: str = "neutral"
) -> str:
    """Generate a deeply empathic response based on detected emotions."""
    client = get_groq_client()
    
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
    
    try:
        response = await client.chat.completions.create(
            model=BEST_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.7 if emotion_intensity == "neutral" else (0.5 if emotion_intensity == "negative" else 0.8),
            max_tokens=1024
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"I'm here for you. {str(e)}"


async def generate_bot_suggestion(user_request: str, intelligence_level: str = "advanced") -> Dict[str, Any]:
    """
    Generate a highly intelligent, fully-featured Telegram bot.
    This is the core AI bot builder that creates complete, production-ready bots.
    """
    client = get_groq_client()
    
    # Use appropriate model based on intelligence level
    config = INTELLIGENCE_LEVELS.get(intelligence_level, INTELLIGENCE_LEVELS["advanced"])
    
    # Advanced multi-step prompt for maximum intelligence
    analysis_prompt = f"""Analyze this bot request and extract key requirements:
    
Request: {user_request}

Identify:
1. Primary purpose/function
2. Target audience
3. Key features needed
4. Personality traits
5. Any specific integrations or capabilities mentioned

Respond with a brief analysis."""

    # First, analyze the request
    try:
        analysis = await client.chat.completions.create(
            model=BEST_MODEL,
            messages=[
                {"role": "system", "content": "You are an expert bot requirements analyst. Be concise and insightful."},
                {"role": "user", "content": analysis_prompt}
            ],
            temperature=0.3,
            max_tokens=500
        )
        analysis_result = analysis.choices[0].message.content
    except:
        analysis_result = user_request

    # Now generate the complete bot with enhanced intelligence
    generation_prompt = f"""You are the world's best Telegram bot architect and AI engineer. Create an EXCEPTIONAL, highly intelligent bot.

ORIGINAL REQUEST: {user_request}

ANALYSIS: {analysis_result}

Design a complete, production-ready bot. The bot should be:
- Highly intelligent with context awareness
- Natural and conversational
- Capable of handling complex queries
- Proactive in offering help

Generate a comprehensive bot configuration as JSON:
{{
    "bot_name": "UniqueCreativeName",
    "bot_description": "Compelling 2-sentence description of capabilities",
    "bot_type": "specific_type",
    "category": "category_name",
    "intelligence_level": "advanced",
    
    "personality": {{
        "traits": ["trait1", "trait2", "trait3"],
        "tone": "professional/friendly/casual/witty",
        "communication_style": "concise/detailed/adaptive",
        "emoji_usage": "minimal/moderate/expressive"
    }},
    
    "system_prompt": "Comprehensive system prompt that defines the bot's identity, capabilities, personality, and behavior guidelines. Be specific and detailed. Include context awareness instructions.",
    
    "greeting_message": "Engaging welcome message that introduces the bot and its capabilities",
    
    "features": [
        {{
            "name": "Feature Name",
            "description": "What it does",
            "trigger": "How to activate it",
            "ai_powered": true
        }}
    ],
    
    "commands": [
        {{
            "command": "/commandname",
            "description": "Clear description",
            "parameters": "optional parameters",
            "example": "/commandname example usage"
        }}
    ],
    
    "conversation_flows": [
        {{
            "trigger": "user intent or keyword",
            "response_type": "text/media/interactive",
            "ai_generated": true,
            "follow_up": "optional follow-up prompt"
        }}
    ],
    
    "knowledge_areas": ["area1", "area2", "area3"],
    
    "response_templates": {{
        "greeting": "Welcome message",
        "help": "Help message with available commands",
        "fallback": "Intelligent fallback that offers alternatives",
        "error": "Friendly error message",
        "success": "Confirmation message template"
    }},
    
    "ai_capabilities": {{
        "context_memory": true,
        "learning_enabled": false,
        "emotion_aware": true,
        "multilingual": false,
        "voice_enabled": false,
        "image_analysis": false
    }},
    
    "settings": {{
        "response_delay_ms": 0,
        "typing_simulation": true,
        "max_response_length": 2000,
        "rate_limit_per_minute": 30
    }}
}}

IMPORTANT GUIDELINES:
- Make the system_prompt DETAILED and SPECIFIC - this is the brain of the bot
- Include at least 3-5 meaningful features
- Commands should be intuitive and memorable
- Conversation flows should handle common user intents
- The bot should feel intelligent and capable
- Include error handling and edge cases in response templates

Respond ONLY with valid, complete JSON."""

    try:
        response = await client.chat.completions.create(
            model=config["model"],
            messages=[
                {
                    "role": "system", 
                    "content": """You are the world's most advanced AI bot architect. You create Telegram bots that are:
- Exceptionally intelligent and context-aware
- Natural in conversation
- Feature-rich but user-friendly
- Production-ready with proper error handling

Your bots are known for being the best in class - intelligent, helpful, and delightful to use.
Always respond with valid, complete JSON only."""
                },
                {"role": "user", "content": generation_prompt}
            ],
            temperature=config["temperature"],
            max_tokens=config["max_tokens"]
        )
        
        result = response.choices[0].message.content
        
        # Parse the JSON response
        try:
            bot_config = json.loads(result)
        except json.JSONDecodeError:
            import re
            json_match = re.search(r'\{[\s\S]*\}', result)
            if json_match:
                bot_config = json.loads(json_match.group())
            else:
                return {"error": "Could not parse bot configuration", "raw": result}
        
        # Enrich the configuration with metadata
        bot_config['user_original_request'] = user_request
        bot_config['created_with_intelligence'] = intelligence_level
        bot_config['ai_analysis'] = analysis_result
        
        # Validate and ensure required fields
        required_fields = ['bot_name', 'system_prompt', 'greeting_message']
        for field in required_fields:
            if field not in bot_config:
                bot_config[field] = _generate_default_field(field, user_request)
        
        return bot_config
        
    except Exception as e:
        return {"error": str(e)}


def _generate_default_field(field: str, request: str) -> str:
    """Generate default values for missing fields."""
    defaults = {
        'bot_name': 'SmartBot',
        'system_prompt': f'You are a helpful assistant created for: {request}. Be friendly, concise, and helpful.',
        'greeting_message': 'Hello! I am here to help you. How can I assist you today?'
    }
    return defaults.get(field, '')


async def generate_advanced_bot(
    user_request: str,
    bot_type: str = None,
    features: List[str] = None,
    personality: Dict[str, Any] = None,
    knowledge_base: List[str] = None
) -> Dict[str, Any]:
    """
    Generate a highly customized, intelligent bot with specific requirements.
    This is for power users who want fine-grained control.
    """
    client = get_groq_client()
    
    customization = {
        "requested_type": bot_type,
        "requested_features": features or [],
        "personality_config": personality or {},
        "knowledge_areas": knowledge_base or []
    }
    
    prompt = f"""Create a specialized, highly intelligent Telegram bot with these specific requirements:

CORE REQUEST: {user_request}

CUSTOMIZATION:
- Bot Type: {bot_type or 'auto-detect based on request'}
- Requested Features: {json.dumps(features or ['auto-generate based on request'])}
- Personality: {json.dumps(personality or {'auto': True})}
- Knowledge Base: {json.dumps(knowledge_base or ['general'])}

Design the most intelligent, capable bot possible that meets these requirements.
The bot should demonstrate:
1. Deep understanding of context
2. Proactive helpful behavior
3. Natural conversation flow
4. Expert-level knowledge in its domain
5. Graceful error handling

Generate comprehensive JSON configuration with all required fields."""

    try:
        response = await client.chat.completions.create(
            model=REASONING_MODEL,  # Use reasoning model for complex customization
            messages=[
                {
                    "role": "system",
                    "content": "You are an elite AI bot architect specializing in creating highly customized, intelligent bots. Generate complete, production-ready configurations."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.6,
            max_tokens=4096
        )
        
        result = response.choices[0].message.content
        try:
            config = json.loads(result)
            config['customization_applied'] = customization
            return config
        except json.JSONDecodeError:
            import re
            json_match = re.search(r'\{[\s\S]*\}', result)
            if json_match:
                config = json.loads(json_match.group())
                config['customization_applied'] = customization
                return config
            return {"error": "Could not create customized bot"}
    except Exception as e:
        return {"error": str(e)}


async def enhance_bot_intelligence(existing_bot: Dict[str, Any], enhancement_request: str) -> Dict[str, Any]:
    """
    Enhance an existing bot's intelligence and capabilities.
    """
    client = get_groq_client()
    
    prompt = f"""You have an existing bot configuration. Enhance it based on the user's request.

EXISTING BOT:
{json.dumps(existing_bot, indent=2)}

ENHANCEMENT REQUEST: {enhancement_request}

Improve the bot by:
1. Enhancing the system prompt for better intelligence
2. Adding relevant new features
3. Improving conversation flows
4. Making responses more natural and helpful

Return the COMPLETE enhanced bot configuration as JSON.
Preserve all existing good features while adding improvements."""

    try:
        response = await client.chat.completions.create(
            model=BEST_MODEL,
            messages=[
                {"role": "system", "content": "You are a bot enhancement specialist. Improve bots while preserving their core identity."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=3000
        )
        
        result = response.choices[0].message.content
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            import re
            json_match = re.search(r'\{[\s\S]*\}', result)
            if json_match:
                return json.loads(json_match.group())
            return existing_bot  # Return original if enhancement fails
    except Exception as e:
        return {"error": str(e), "original": existing_bot}


async def generate_bot_from_template(template_name: str, customizations: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Generate a bot based on a predefined template with optional customizations.
    """
    templates = {
        "customer_support": {
            "base_type": "customer_support",
            "features": ["ticket_creation", "faq_answers", "escalation", "satisfaction_survey"],
            "personality": {"tone": "professional", "empathy": "high"}
        },
        "personal_assistant": {
            "base_type": "personal_assistant",
            "features": ["reminders", "notes", "tasks", "calendar", "smart_suggestions"],
            "personality": {"tone": "friendly", "proactive": True}
        },
        "quiz_master": {
            "base_type": "quiz_master",
            "features": ["quiz_generation", "scoring", "leaderboards", "explanations"],
            "personality": {"tone": "enthusiastic", "educational": True}
        },
        "code_assistant": {
            "base_type": "code_helper",
            "features": ["code_review", "debugging", "explanations", "best_practices"],
            "personality": {"tone": "technical", "detailed": True}
        },
        "language_tutor": {
            "base_type": "language_tutor",
            "features": ["vocabulary", "grammar", "conversation_practice", "pronunciation"],
            "personality": {"tone": "encouraging", "patient": True}
        },
        "content_creator": {
            "base_type": "creative_writer",
            "features": ["brainstorming", "writing", "editing", "style_matching"],
            "personality": {"tone": "creative", "adaptive": True}
        },
        "research_assistant": {
            "base_type": "general",
            "features": ["web_search", "summarization", "fact_checking", "citations"],
            "personality": {"tone": "academic", "thorough": True}
        },
        "fitness_coach": {
            "base_type": "health_coach",
            "features": ["workout_plans", "nutrition", "progress_tracking", "motivation"],
            "personality": {"tone": "motivating", "supportive": True}
        }
    }
    
    if template_name not in templates:
        return {"error": f"Template '{template_name}' not found. Available: {list(templates.keys())}"}
    
    template = templates[template_name]
    
    # Merge customizations
    if customizations:
        if 'features' in customizations:
            template['features'] = list(set(template['features'] + customizations['features']))
        if 'personality' in customizations:
            template['personality'].update(customizations['personality'])
    
    # Generate the full bot based on template
    request = f"Create a {template_name.replace('_', ' ')} bot with features: {', '.join(template['features'])}"
    return await generate_advanced_bot(
        user_request=request,
        bot_type=template['base_type'],
        features=template['features'],
        personality=template['personality']
    )


async def analyze_message_intent(message: str) -> Dict[str, Any]:
    """Analyze the intent of a user message."""
    client = get_groq_client()
    
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

    try:
        response = await client.chat.completions.create(
            model=BEST_MODEL,
            messages=[
                {"role": "system", "content": "You are a message intent analyzer. Respond only with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=512
        )
        
        result = response.choices[0].message.content
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
    client = get_groq_client()
    
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

    try:
        response = await client.chat.completions.create(
            model=BEST_MODEL,
            messages=[
                {"role": "system", "content": "You are a datetime parsing expert. Respond only with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=256
        )
        
        result = response.choices[0].message.content
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
    client = get_groq_client()
    
    prompt = f"""Parse this task request and extract the details.

Message: {message}

Respond with JSON:
{{
    "title": "task title",
    "description": "task description or null",
    "due_date": "ISO format datetime if mentioned, or null",
    "priority": "high, medium, or low",
    "confidence": 0.0 to 1.0
}}

Only respond with valid JSON."""

    try:
        response = await client.chat.completions.create(
            model=BEST_MODEL,
            messages=[
                {"role": "system", "content": "You are a task parsing expert. Respond only with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=256
        )
        
        result = response.choices[0].message.content
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
    client = get_groq_client()
    
    try:
        response = await client.chat.completions.create(
            model=BEST_MODEL,
            messages=[
                {"role": "system", "content": f"Summarize the following text in {max_length} words or less. Be concise and capture the key points."},
                {"role": "user", "content": text}
            ],
            temperature=0.3,
            max_tokens=max_length * 2
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error summarizing: {str(e)}"


async def translate_text(text: str, target_language: str) -> str:
    """Translate text to a target language."""
    client = get_groq_client()
    
    try:
        response = await client.chat.completions.create(
            model=BEST_MODEL,
            messages=[
                {"role": "system", "content": f"Translate the following text to {target_language}. Provide only the translation, no explanations."},
                {"role": "user", "content": text}
            ],
            temperature=0.2,
            max_tokens=1024
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error translating: {str(e)}"


async def generate_quiz_question(topic: str, difficulty: str = "medium") -> Dict[str, Any]:
    """Generate a quiz question on a topic."""
    client = get_groq_client()
    
    prompt = f"""Generate a {difficulty} difficulty quiz question about: {topic}

Respond with JSON:
{{
    "question": "the question text",
    "options": ["A) option1", "B) option2", "C) option3", "D) option4"],
    "correct_answer": "A, B, C, or D",
    "explanation": "brief explanation of the correct answer"
}}

Only respond with valid JSON."""

    try:
        response = await client.chat.completions.create(
            model=BEST_MODEL,
            messages=[
                {"role": "system", "content": "You are a quiz question generator. Respond only with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
            max_tokens=512
        )
        
        result = response.choices[0].message.content
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
    client = get_groq_client()
    
    context_str = json.dumps(user_context, indent=2)
    
    prompt = f"""Based on the following user context, suggest 3-5 helpful actions or things the user might want to do next.

User Context:
{context_str}

Respond with a JSON array of suggestion strings:
["suggestion 1", "suggestion 2", "suggestion 3"]

Only respond with valid JSON array."""

    try:
        response = await client.chat.completions.create(
            model=BEST_MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful assistant suggesting next actions. Respond only with a JSON array."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=256
        )
        
        result = response.choices[0].message.content
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
