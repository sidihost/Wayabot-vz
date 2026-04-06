"""
Waya Bot Builder - AI Engine Module
Powered by Groq AI for ultra-fast intelligent responses.
"""

import os
import json
from typing import Optional, Dict, Any, List
from groq import AsyncGroq
from datetime import datetime

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
    max_tokens: int = 1024
) -> str:
    """Generate an AI response using Groq."""
    client = get_groq_client()
    
    # Build the system prompt with user context
    base_prompt = system_prompt or WAYA_SYSTEM_PROMPT
    if user_name:
        base_prompt += f"\n\nYou are talking to {user_name}. Address them by name occasionally to be personal."
    
    base_prompt += f"\n\nCurrent date and time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    
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
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"I apologize, but I encountered an error: {str(e)}. Please try again."


async def generate_bot_suggestion(user_request: str) -> Dict[str, Any]:
    """Generate a bot configuration suggestion based on user request."""
    client = get_groq_client()
    
    prompt = f"""Based on the following user request, suggest a bot configuration.
    
User Request: {user_request}

Respond with a JSON object containing:
{{
    "bot_name": "suggested name for the bot",
    "bot_description": "brief description",
    "bot_type": "one of: customer_support, faq, personal_assistant, quiz_master, creative_writer, code_helper, language_tutor, health_coach, news_curator, general",
    "suggested_commands": ["list of suggested commands like /start, /help, etc."],
    "suggested_triggers": ["keywords that should trigger responses"],
    "greeting_message": "suggested greeting message",
    "features": ["list of recommended features"],
    "customization_tips": ["tips for customizing the bot"]
}}

Only respond with valid JSON, no additional text."""

    try:
        response = await client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a bot configuration expert. Respond only with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1024
        )
        
        result = response.choices[0].message.content
        # Try to extract JSON from the response
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            # Try to find JSON in the response
            import re
            json_match = re.search(r'\{[\s\S]*\}', result)
            if json_match:
                return json.loads(json_match.group())
            return {"error": "Could not parse bot suggestion", "raw": result}
    except Exception as e:
        return {"error": str(e)}


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
            model="llama-3.3-70b-versatile",
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
            model="llama-3.3-70b-versatile",
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
            model="llama-3.3-70b-versatile",
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
            model="llama-3.3-70b-versatile",
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
            model="llama-3.3-70b-versatile",
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
            model="llama-3.3-70b-versatile",
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
            model="llama-3.3-70b-versatile",
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
