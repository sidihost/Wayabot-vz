"""
Waya Bot Builder - Cognitive Engine
ReAct-style multi-step reasoning with thought chains, self-reflection, and tool use.
This is what makes the bot truly intelligent - it thinks before it responds.
"""

import asyncio
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List, Dict, Any, Tuple

from .memory_engine import MemoryEngine, get_memory_engine, Memory
from .tools_engine import ToolsEngine, get_tools_engine, ToolResult, ToolStatus

logger = logging.getLogger(__name__)


class ThoughtType(str, Enum):
    """Types of thoughts in the reasoning chain"""
    ANALYZE = "analyze"      # Understanding what user needs
    RECALL = "recall"        # Retrieving relevant memories
    PLAN = "plan"            # Planning the approach
    TOOL_USE = "tool_use"    # Using a tool
    OBSERVE = "observe"      # Processing tool results
    REFLECT = "reflect"      # Self-reflection on quality
    RESPOND = "respond"      # Final response generation


@dataclass
class Thought:
    """A single thought in the reasoning chain"""
    type: ThoughtType
    content: str
    confidence: float = 0.8
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ReasoningChain:
    """Complete chain of thoughts for one response"""
    thoughts: List[Thought] = field(default_factory=list)
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    tool_results: List[ToolResult] = field(default_factory=list)
    memories_used: List[Memory] = field(default_factory=list)
    final_response: str = ""
    reasoning_time_ms: int = 0
    success: bool = True
    error: Optional[str] = None
    
    def add_thought(self, thought_type: ThoughtType, content: str, **kwargs):
        """Add a thought to the chain"""
        self.thoughts.append(Thought(
            type=thought_type,
            content=content,
            **kwargs
        ))
    
    def get_thought_chain_text(self) -> str:
        """Get human-readable thought chain"""
        lines = []
        for thought in self.thoughts:
            emoji = {
                ThoughtType.ANALYZE: "🔍",
                ThoughtType.RECALL: "💭",
                ThoughtType.PLAN: "📋",
                ThoughtType.TOOL_USE: "🔧",
                ThoughtType.OBSERVE: "👁️",
                ThoughtType.REFLECT: "🤔",
                ThoughtType.RESPOND: "💬"
            }.get(thought.type, "•")
            lines.append(f"{emoji} **{thought.type.value.title()}**: {thought.content}")
        return "\n".join(lines)


@dataclass
class CognitiveContext:
    """Full context for cognitive processing"""
    user_id: int
    user_message: str
    conversation_history: List[Dict[str, str]] = field(default_factory=list)
    memory_context: str = ""
    user_profile: Dict[str, Any] = field(default_factory=dict)
    current_emotion: Optional[str] = None
    session_data: Dict[str, Any] = field(default_factory=dict)
    system_prompt: Optional[str] = None


class CognitiveEngine:
    """
    Advanced reasoning engine using ReAct (Reason + Act) pattern.
    
    Thinking Process:
    1. ANALYZE: Understand what the user needs
    2. RECALL: Retrieve relevant memories
    3. PLAN: Decide on approach
    4. ACT: Use tools if needed
    5. OBSERVE: Process results
    6. REFLECT: Validate response quality
    7. RESPOND: Generate final response
    """
    
    def __init__(self, ai_engine=None):
        self.ai_engine = ai_engine
        self.memory_engine: Optional[MemoryEngine] = None
        self.tools_engine: Optional[ToolsEngine] = None
        self.max_reasoning_steps = 5
        self.min_confidence_threshold = 0.6
    
    async def initialize(self):
        """Initialize connections to other engines"""
        self.memory_engine = get_memory_engine()
        self.tools_engine = get_tools_engine()
    
    async def think_and_respond(
        self,
        context: CognitiveContext
    ) -> Tuple[str, ReasoningChain]:
        """
        Main entry point: Think through the problem and generate a response.
        Returns (final_response, reasoning_chain)
        """
        start_time = datetime.now(timezone.utc)
        chain = ReasoningChain()
        
        try:
            # Step 1: ANALYZE - Understand what user needs
            analysis = await self._analyze(context, chain)
            
            # Step 2: RECALL - Get relevant memories
            if self.memory_engine:
                memories = await self._recall_memories(context, chain)
                chain.memories_used = memories
            
            # Step 3: PLAN - Decide approach
            plan = await self._plan(context, analysis, chain)
            
            # Step 4: ACT - Use tools if needed
            if plan.get("needs_tools"):
                await self._use_tools(context, plan, chain)
            
            # Step 5: REFLECT - Check if we have enough information
            reflection = await self._reflect(context, chain)
            
            # Step 6: RESPOND - Generate final response
            response = await self._generate_response(context, chain)
            
            chain.final_response = response
            chain.success = True
            
        except Exception as e:
            logger.error(f"Cognitive processing error: {e}")
            chain.error = str(e)
            chain.success = False
            chain.final_response = await self._generate_fallback_response(context)
        
        # Record timing
        elapsed = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        chain.reasoning_time_ms = int(elapsed)
        
        return chain.final_response, chain
    
    async def _analyze(self, context: CognitiveContext, chain: ReasoningChain) -> Dict[str, Any]:
        """Analyze what the user is asking for"""
        
        analysis_prompt = f"""Analyze this user message and determine:
1. What is the user's primary intent? (question, request, chat, help, etc.)
2. What type of information or action do they need?
3. Is there any emotional undertone? (frustrated, happy, curious, etc.)
4. Do they need real-time information that requires a tool?
5. Is this a follow-up to a previous conversation?

User message: "{context.user_message}"

Recent conversation context:
{self._format_recent_history(context.conversation_history)}

Respond in JSON format:
{{"intent": "...", "info_type": "...", "emotion": "...", "needs_tools": true/false, "is_followup": true/false, "tool_suggestion": "web_search/calculator/code/image/document/none"}}"""

        try:
            if self.ai_engine:
                response = await self.ai_engine.generate(
                    analysis_prompt,
                    max_tokens=200,
                    temperature=0.3
                )
                # Parse JSON from response
                json_match = re.search(r'\{[^}]+\}', response, re.DOTALL)
                if json_match:
                    analysis = json.loads(json_match.group())
                else:
                    analysis = self._default_analysis(context)
            else:
                analysis = self._default_analysis(context)
        except Exception as e:
            logger.warning(f"Analysis failed: {e}")
            analysis = self._default_analysis(context)
        
        chain.add_thought(
            ThoughtType.ANALYZE,
            f"User intent: {analysis.get('intent', 'unknown')}. "
            f"Needs tools: {analysis.get('needs_tools', False)}. "
            f"Emotion: {analysis.get('emotion', 'neutral')}",
            metadata=analysis
        )
        
        return analysis
    
    async def _recall_memories(
        self,
        context: CognitiveContext,
        chain: ReasoningChain
    ) -> List[Memory]:
        """Recall relevant memories for this context"""
        
        if not self.memory_engine:
            return []
        
        try:
            # Get memories relevant to current message
            memories = await self.memory_engine.recall_memories(
                context.user_id,
                query=context.user_message,
                limit=5,
                min_importance=0.3
            )
            
            if memories:
                memory_summary = ", ".join([m.summary or m.content[:50] for m in memories[:3]])
                chain.add_thought(
                    ThoughtType.RECALL,
                    f"Retrieved {len(memories)} relevant memories: {memory_summary}",
                    metadata={"memory_count": len(memories)}
                )
            else:
                chain.add_thought(
                    ThoughtType.RECALL,
                    "No specific memories found for this context"
                )
            
            return memories
        except Exception as e:
            logger.warning(f"Memory recall failed: {e}")
            return []
    
    async def _plan(
        self,
        context: CognitiveContext,
        analysis: Dict[str, Any],
        chain: ReasoningChain
    ) -> Dict[str, Any]:
        """Plan the approach to respond"""
        
        plan = {
            "needs_tools": analysis.get("needs_tools", False),
            "tool_to_use": analysis.get("tool_suggestion", "none"),
            "approach": "direct_response",
            "confidence": 0.8
        }
        
        # Check if tools are needed based on message content
        if self.tools_engine:
            detected = self.tools_engine.detect_tool_need(context.user_message)
            if detected:
                tool_name, tool_params = detected
                plan["needs_tools"] = True
                plan["tool_to_use"] = tool_name
                plan["tool_params"] = tool_params
                plan["approach"] = "tool_assisted"
        
        # Determine approach
        if plan["needs_tools"]:
            chain.add_thought(
                ThoughtType.PLAN,
                f"Will use {plan['tool_to_use']} tool to get information, then respond",
                metadata=plan
            )
        elif analysis.get("is_followup"):
            plan["approach"] = "contextual_response"
            chain.add_thought(
                ThoughtType.PLAN,
                "This is a follow-up question - will use conversation context",
                metadata=plan
            )
        else:
            chain.add_thought(
                ThoughtType.PLAN,
                "Will provide a direct response using knowledge and memories",
                metadata=plan
            )
        
        return plan
    
    async def _use_tools(
        self,
        context: CognitiveContext,
        plan: Dict[str, Any],
        chain: ReasoningChain
    ):
        """Use tools to gather information"""
        
        if not self.tools_engine:
            return
        
        tool_name = plan.get("tool_to_use", "none")
        tool_params = plan.get("tool_params", {})
        
        if tool_name == "none":
            return
        
        chain.add_thought(
            ThoughtType.TOOL_USE,
            f"Executing {tool_name} with params: {tool_params}"
        )
        
        try:
            # Execute the tool
            result = await self.tools_engine.execute_tool(tool_name, **tool_params)
            
            chain.tool_calls.append({
                "tool": tool_name,
                "params": tool_params,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            chain.tool_results.append(result)
            
            # Observe the result
            if result.is_success:
                chain.add_thought(
                    ThoughtType.OBSERVE,
                    f"Tool returned successfully: {result.to_context()[:200]}...",
                    metadata={"status": "success"}
                )
            else:
                chain.add_thought(
                    ThoughtType.OBSERVE,
                    f"Tool failed: {result.error}",
                    metadata={"status": "error"}
                )
        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            chain.add_thought(
                ThoughtType.OBSERVE,
                f"Tool execution error: {str(e)}",
                metadata={"status": "error"}
            )
    
    async def _reflect(
        self,
        context: CognitiveContext,
        chain: ReasoningChain
    ) -> Dict[str, Any]:
        """Reflect on gathered information and validate quality"""
        
        reflection = {
            "has_enough_info": True,
            "confidence": 0.8,
            "issues": []
        }
        
        # Check if tool calls failed
        failed_tools = [r for r in chain.tool_results if not r.is_success]
        if failed_tools:
            reflection["issues"].append("Some tools failed to return results")
            reflection["confidence"] -= 0.2
        
        # Check if we have relevant memories
        if chain.memories_used:
            reflection["confidence"] += 0.1
        
        # Cap confidence
        reflection["confidence"] = min(max(reflection["confidence"], 0), 1)
        
        chain.add_thought(
            ThoughtType.REFLECT,
            f"Confidence level: {reflection['confidence']:.0%}. "
            f"Ready to respond: {reflection['has_enough_info']}",
            metadata=reflection
        )
        
        return reflection
    
    async def _generate_response(
        self,
        context: CognitiveContext,
        chain: ReasoningChain
    ) -> str:
        """Generate the final response using all gathered context"""
        
        # Build comprehensive prompt
        prompt_parts = []
        
        # System context
        if context.system_prompt:
            prompt_parts.append(context.system_prompt)
        else:
            prompt_parts.append("""You are Waya, an intelligent AI assistant that remembers users and can use tools to help them. You are friendly, helpful, and knowledgeable. When you use tools, incorporate the results naturally into your response.""")
        
        # Memory context
        if context.memory_context:
            prompt_parts.append(f"\n### What you know about this user:\n{context.memory_context}")
        
        # Tool results
        if chain.tool_results:
            tool_context = "\n### Information gathered:\n"
            for result in chain.tool_results:
                if result.is_success:
                    tool_context += result.to_context() + "\n"
            prompt_parts.append(tool_context)
        
        # Conversation history
        if context.conversation_history:
            prompt_parts.append("\n### Recent conversation:")
            for msg in context.conversation_history[-5:]:
                role = "User" if msg.get("role") == "user" else "Assistant"
                prompt_parts.append(f"{role}: {msg.get('content', '')}")
        
        # Current message
        prompt_parts.append(f"\n### Current message:\nUser: {context.user_message}")
        
        # Response instruction
        prompt_parts.append("""
### Instructions:
- Respond naturally and helpfully
- If you used tools, incorporate that information smoothly
- Reference any relevant memories about the user
- Be concise but thorough
- Match the user's energy and tone

Your response:""")
        
        full_prompt = "\n".join(prompt_parts)
        
        try:
            if self.ai_engine:
                response = await self.ai_engine.generate(
                    full_prompt,
                    max_tokens=1024,
                    temperature=0.7
                )
            else:
                response = "I apologize, but I'm having trouble processing your request right now."
        except Exception as e:
            logger.error(f"Response generation failed: {e}")
            response = await self._generate_fallback_response(context)
        
        chain.add_thought(
            ThoughtType.RESPOND,
            f"Generated response ({len(response)} chars)"
        )
        
        return response.strip()
    
    async def _generate_fallback_response(self, context: CognitiveContext) -> str:
        """Generate a fallback response when things go wrong"""
        return "I'm sorry, I'm having a bit of trouble right now. Could you try rephrasing your question?"
    
    def _default_analysis(self, context: CognitiveContext) -> Dict[str, Any]:
        """Default analysis when AI analysis fails"""
        message_lower = context.user_message.lower()
        
        return {
            "intent": "question" if "?" in context.user_message else "chat",
            "info_type": "general",
            "emotion": "neutral",
            "needs_tools": any(kw in message_lower for kw in ["search", "weather", "calculate", "news"]),
            "is_followup": any(w in message_lower for w in ["that", "it", "this", "those"]),
            "tool_suggestion": "none"
        }
    
    def _format_recent_history(self, history: List[Dict[str, str]], limit: int = 3) -> str:
        """Format recent conversation history"""
        if not history:
            return "No previous conversation"
        
        lines = []
        for msg in history[-limit:]:
            role = "User" if msg.get("role") == "user" else "Assistant"
            content = msg.get("content", "")[:100]
            lines.append(f"{role}: {content}")
        
        return "\n".join(lines)
    
    async def should_use_deep_thinking(self, message: str) -> bool:
        """Determine if message requires deep reasoning vs quick response"""
        # Quick responses for simple greetings
        simple_patterns = [
            r'^(hi|hello|hey|yo|sup|good morning|good evening|good night)[\s!.]*$',
            r'^(thanks|thank you|ok|okay|cool|great|nice|got it)[\s!.]*$',
            r'^(bye|goodbye|see you|later|ciao)[\s!.]*$',
            r'^(yes|no|yeah|nope|sure|nah)[\s!.]*$'
        ]
        
        message_lower = message.lower().strip()
        for pattern in simple_patterns:
            if re.match(pattern, message_lower, re.IGNORECASE):
                return False
        
        # Deep thinking for complex queries
        complex_indicators = [
            "explain", "why", "how does", "what if", "compare",
            "analyze", "help me", "I need", "can you", "should I"
        ]
        
        return any(ind in message_lower for ind in complex_indicators)


# Global cognitive engine instance
_cognitive_engine: Optional[CognitiveEngine] = None


async def init_cognitive_engine(ai_engine=None) -> CognitiveEngine:
    """Initialize the global cognitive engine"""
    global _cognitive_engine
    _cognitive_engine = CognitiveEngine(ai_engine)
    await _cognitive_engine.initialize()
    return _cognitive_engine


def get_cognitive_engine() -> Optional[CognitiveEngine]:
    """Get the global cognitive engine"""
    return _cognitive_engine
