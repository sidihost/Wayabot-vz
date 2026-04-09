"""
Waya Bot Builder - Intelligence Core
Master orchestrator that combines all intelligence engines into a unified system.
This is the brain that makes Waya the smartest Telegram bot ever.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple

# Import intelligence engines - these are in the same directory
from memory_engine import MemoryEngine, init_memory_engine, get_memory_engine
from tools_engine import ToolsEngine, get_tools_engine, ToolResult
from cognitive_engine import CognitiveEngine, CognitiveContext, ReasoningChain, init_cognitive_engine, get_cognitive_engine
from learning_engine import LearningEngine, UserProfile, init_learning_engine, get_learning_engine
from proactive_engine import ProactiveEngine, ProactiveAction, init_proactive_engine, get_proactive_engine

logger = logging.getLogger(__name__)


@dataclass
class IntelligentResponse:
    """Complete response from the intelligence system"""
    message: str
    
    # Reasoning info
    used_memory: bool = False
    used_tools: bool = False
    tool_results: List[ToolResult] = field(default_factory=list)
    reasoning_chain: Optional[ReasoningChain] = None
    
    # Personalization
    was_personalized: bool = False
    user_profile: Optional[UserProfile] = None
    
    # Suggestions
    suggestions: List[str] = field(default_factory=list)
    quick_replies: List[str] = field(default_factory=list)
    
    # Follow-ups
    follow_up_detected: Optional[str] = None
    
    # Metadata
    confidence: float = 0.8
    processing_time_ms: int = 0
    engines_used: List[str] = field(default_factory=list)


class IntelligenceCore:
    """
    The central intelligence system that orchestrates all engines.
    
    This is what makes Waya smarter than any other Telegram bot:
    1. Memory - Remembers everything about users across sessions
    2. Tools - Can search the web, run code, analyze images
    3. Cognition - Thinks through problems step by step
    4. Learning - Gets better at helping each user over time
    5. Proactivity - Anticipates needs and offers help
    """
    
    def __init__(self, db_pool, ai_engine=None):
        self.db_pool = db_pool
        self.ai_engine = ai_engine
        
        # Engine instances (initialized later)
        self.memory: Optional[MemoryEngine] = None
        self.tools: Optional[ToolsEngine] = None
        self.cognition: Optional[CognitiveEngine] = None
        self.learning: Optional[LearningEngine] = None
        self.proactive: Optional[ProactiveEngine] = None
        
        self._initialized = False
    
    async def initialize(self):
        """Initialize all intelligence engines"""
        if self._initialized:
            return
        
        logger.info("Initializing Intelligence Core...")
        
        try:
            # Initialize all engines in parallel where possible
            self.memory = await init_memory_engine(self.db_pool)
            self.learning = await init_learning_engine(self.db_pool)
            self.proactive = await init_proactive_engine(self.db_pool)
            self.cognition = await init_cognitive_engine(self.ai_engine)
            self.tools = get_tools_engine()
            
            self._initialized = True
            logger.info("Intelligence Core initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Intelligence Core: {e}")
            raise
    
    async def process_message(
        self,
        user_id: int,
        message: str,
        conversation_history: List[Dict[str, str]] = None,
        system_prompt: Optional[str] = None,
        user_name: Optional[str] = None,
        image_data: Optional[bytes] = None,
        document_data: Optional[bytes] = None
    ) -> IntelligentResponse:
        """
        Process a user message through the full intelligence pipeline.
        This is the main entry point for intelligent responses.
        """
        start_time = datetime.now(timezone.utc)
        response = IntelligentResponse(message="")
        response.engines_used = []
        
        try:
            # Step 1: Get user profile from learning engine
            if self.learning:
                response.user_profile = await self.learning.get_user_profile(user_id)
                response.engines_used.append("learning")
            
            # Step 2: Get memory context
            memory_context = ""
            if self.memory:
                memory_context = await self.memory.get_memory_context(user_id, message)
                if memory_context:
                    response.used_memory = True
                    response.engines_used.append("memory")
            
            # Step 3: Check for media to analyze
            tool_context = ""
            if self.tools:
                # Analyze image if provided
                if image_data:
                    result = await self.tools.image_analysis.analyze(image_data)
                    if result.is_success:
                        tool_context += f"\n\n[Image Analysis: {result.to_context()}]"
                        response.tool_results.append(result)
                        response.used_tools = True
                
                # Process document if provided
                if document_data:
                    result = await self.tools.document_processing.process(document_data)
                    if result.is_success:
                        tool_context += f"\n\n[Document Content: {result.to_context()}]"
                        response.tool_results.append(result)
                        response.used_tools = True
            
            # Step 4: Build cognitive context
            if self.cognition:
                cognitive_ctx = CognitiveContext(
                    user_id=user_id,
                    user_message=message + tool_context,
                    conversation_history=conversation_history or [],
                    memory_context=memory_context,
                    user_profile=response.user_profile.__dict__ if response.user_profile else {},
                    system_prompt=system_prompt
                )
                
                # Step 5: Think and respond using cognitive engine
                final_response, reasoning_chain = await self.cognition.think_and_respond(cognitive_ctx)
                
                response.message = final_response
                response.reasoning_chain = reasoning_chain
                response.engines_used.append("cognition")
                
                if reasoning_chain.tool_results:
                    response.tool_results.extend(reasoning_chain.tool_results)
                    response.used_tools = True
                    response.engines_used.append("tools")
            else:
                # Fallback: use basic AI engine
                if self.ai_engine:
                    import ai_engine as ai_mod
                    response.message = await ai_mod.generate_response(
                        message,
                        conversation_history,
                        system_prompt=system_prompt,
                        user_name=user_name
                    )
            
            # Step 6: Adapt response to user preferences
            if self.learning and response.user_profile:
                response.message = await self.learning.adapt_response(
                    user_id, response.message, response.user_profile
                )
                response.was_personalized = True
            
            # Step 7: Get smart suggestions
            if self.proactive:
                response.quick_replies = await self.proactive.get_smart_suggestions(
                    user_id, message, response.message
                )
                response.engines_used.append("proactive")
            
            # Step 8: Check for follow-up opportunities
            if self.proactive:
                follow_up = await self.proactive.detect_follow_up_opportunities(user_id, message)
                if follow_up:
                    response.follow_up_detected = follow_up
            
            # Step 9: Process interaction for learning
            if self.learning:
                await self.learning.process_interaction(
                    user_id, message, response.message
                )
            
            # Step 10: Extract and store memories
            if self.memory:
                await self.memory.process_conversation(
                    user_id, message, response.message
                )
            
            response.confidence = 0.85
            
        except Exception as e:
            logger.error(f"Intelligence Core error: {e}")
            response.message = "I apologize, but I'm having trouble processing that right now. Please try again."
            response.confidence = 0.3
        
        # Record processing time
        elapsed = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        response.processing_time_ms = int(elapsed)
        
        return response
    
    async def get_daily_briefing(self, user_id: int) -> Optional[str]:
        """Generate a daily briefing for a user"""
        if not self.proactive:
            return None
        
        # Get weather if tools available
        weather = None
        if self.tools:
            # Try to get user's location from memory
            if self.memory:
                profile = await self.memory.get_user_profile_memories(user_id)
                location = profile.get("location")
                if location:
                    weather_result = await self.tools.weather.get_weather(location)
                    if weather_result.is_success:
                        weather = weather_result.data
        
        briefing = await self.proactive.generate_daily_briefing(user_id, weather)
        return briefing.to_message()
    
    async def handle_feedback(
        self,
        user_id: int,
        feedback_type: str,
        message: str = "",
        response: str = ""
    ):
        """Handle user feedback"""
        if self.learning:
            from learning_engine import FeedbackType
            ft = FeedbackType(feedback_type) if feedback_type in FeedbackType.__members__.values() else FeedbackType.THUMBS_UP
            await self.learning.record_feedback(user_id, ft, message, response)
    
    async def run_periodic_tasks(self):
        """Run periodic maintenance tasks"""
        # Memory decay
        if self.memory:
            await self.memory.apply_memory_decay()
        
        # Batch learning
        if self.learning:
            await self.learning.run_batch_learning()
        
        # Proactive checks
        if self.proactive:
            await self.proactive.run_scheduled_checks()
    
    async def get_user_insights(self, user_id: int) -> Dict[str, Any]:
        """Get insights about a user"""
        insights = {
            "memories": 0,
            "interactions": 0,
            "engagement_score": 0.5,
            "topics_of_interest": [],
            "communication_style": "friendly"
        }
        
        if self.memory:
            memories = await self.memory.recall_memories(user_id, limit=100, min_importance=0.1)
            insights["memories"] = len(memories)
        
        if self.learning:
            profile = await self.learning.get_user_profile(user_id)
            insights["interactions"] = profile.total_interactions
            insights["engagement_score"] = profile.engagement_score
            insights["topics_of_interest"] = profile.topics_of_interest
            insights["communication_style"] = profile.preferred_style.value
        
        return insights
    
    async def close(self):
        """Clean up resources"""
        if self.tools:
            await self.tools.close()


# Global intelligence core instance
_intelligence_core: Optional[IntelligenceCore] = None


async def init_intelligence_core(db_pool, ai_engine=None) -> IntelligenceCore:
    """Initialize the global intelligence core"""
    global _intelligence_core
    _intelligence_core = IntelligenceCore(db_pool, ai_engine)
    await _intelligence_core.initialize()
    return _intelligence_core


def get_intelligence_core() -> Optional[IntelligenceCore]:
    """Get the global intelligence core"""
    return _intelligence_core


async def close_intelligence_core():
    """Close the intelligence core"""
    global _intelligence_core
    if _intelligence_core:
        await _intelligence_core.close()
        _intelligence_core = None
