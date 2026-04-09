"""
Waya Bot Builder - Advanced Memory Engine
Long-term memory system with semantic search, memory consolidation, and intelligent retrieval.
Makes the bot truly remember users across sessions.
"""

import asyncio
import json
import logging
import re
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any, Tuple
from enum import Enum
import hashlib

logger = logging.getLogger(__name__)


class MemoryType(str, Enum):
    """Types of memories the bot can store"""
    FACT = "fact"                    # User facts: "My name is John", "I live in Lagos"
    PREFERENCE = "preference"        # User preferences: "I prefer brief answers"
    EVENT = "event"                  # Events: "Had a job interview yesterday"
    RELATIONSHIP = "relationship"    # People mentioned: "My wife Sarah"
    PATTERN = "pattern"              # Behavioral patterns: "Usually messages in morning"
    TOPIC_INTEREST = "topic_interest"  # Topics they care about
    EMOTION = "emotion"              # Emotional states and triggers
    GOAL = "goal"                    # User goals and aspirations
    CONTEXT = "context"              # Contextual information


class MemoryImportance(str, Enum):
    """Importance levels for memory prioritization"""
    CRITICAL = "critical"    # Never forget (names, key relationships)
    HIGH = "high"            # Important facts
    MEDIUM = "medium"        # General information
    LOW = "low"              # Nice to know
    TRANSIENT = "transient"  # Can be forgotten


@dataclass
class Memory:
    """A single memory unit"""
    id: Optional[int] = None
    user_id: int = 0
    memory_type: MemoryType = MemoryType.FACT
    content: str = ""
    summary: str = ""  # Brief version for context
    importance: float = 0.5  # 0-1 scale
    confidence: float = 0.8  # How confident we are this is accurate
    source: str = "conversation"  # Where this memory came from
    
    # Temporal information
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_accessed: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    access_count: int = 0
    
    # Decay and reinforcement
    decay_factor: float = 1.0  # Decreases over time without access
    reinforcement_count: int = 0  # Times this was confirmed
    
    # Metadata
    tags: List[str] = field(default_factory=list)
    related_memories: List[int] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # For semantic search (embedding stored separately)
    embedding_hash: Optional[str] = None


@dataclass
class ConversationSummary:
    """Summary of a conversation period"""
    id: Optional[int] = None
    user_id: int = 0
    summary: str = ""
    key_topics: List[str] = field(default_factory=list)
    key_facts_learned: List[str] = field(default_factory=list)
    emotional_arc: str = ""  # How emotions changed
    user_intent: str = ""  # What user was trying to achieve
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    message_count: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class UserKnowledgeGraph:
    """Graph of user's world - people, places, things they've mentioned"""
    user_id: int
    entities: Dict[str, Dict[str, Any]] = field(default_factory=dict)  # name -> entity info
    relationships: List[Dict[str, Any]] = field(default_factory=list)  # entity1 -> relation -> entity2
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class MemoryExtractor:
    """Extracts memories from conversation text using pattern matching and NLP"""
    
    # Patterns for extracting different types of information
    FACT_PATTERNS = [
        # Personal facts
        (r"(?:my name is|i'm|i am|call me)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)", "name", MemoryImportance.CRITICAL),
        (r"(?:i live in|i'm from|i am from|i'm based in)\s+([A-Za-z\s]+?)(?:\.|,|$)", "location", MemoryImportance.HIGH),
        (r"(?:i work (?:at|for|as)|my job is|i'm a|i am a)\s+(.+?)(?:\.|,|$)", "occupation", MemoryImportance.HIGH),
        (r"(?:i'm|i am)\s+(\d{1,3})\s*(?:years old|yo)", "age", MemoryImportance.MEDIUM),
        (r"my (?:email|mail) is\s+([^\s]+@[^\s]+)", "email", MemoryImportance.HIGH),
        (r"my (?:birthday|bday) is\s+(.+?)(?:\.|,|$)", "birthday", MemoryImportance.HIGH),
    ]
    
    PREFERENCE_PATTERNS = [
        (r"(?:i prefer|i like|i love|i enjoy)\s+(.+?)(?:\.|,|$|but)", "preference", MemoryImportance.MEDIUM),
        (r"(?:i hate|i don't like|i dislike)\s+(.+?)(?:\.|,|$|but)", "dislike", MemoryImportance.MEDIUM),
        (r"(?:please|always|could you)\s+(?:be|keep it|make it)\s+(brief|short|detailed|verbose)", "response_style", MemoryImportance.HIGH),
        (r"(?:i speak|my language is|in)\s+([A-Za-z]+)(?:\s+language)?", "language", MemoryImportance.MEDIUM),
    ]
    
    RELATIONSHIP_PATTERNS = [
        (r"my (wife|husband|spouse|partner)(?:'s name is|,?\s+)([A-Z][a-z]+)", "spouse", MemoryImportance.CRITICAL),
        (r"my (son|daughter|child|kid)(?:'s name is|,?\s+)([A-Z][a-z]+)", "child", MemoryImportance.CRITICAL),
        (r"my (mom|mother|dad|father|parent)(?:'s name is|,?\s+)([A-Z][a-z]+)", "parent", MemoryImportance.HIGH),
        (r"my (friend|best friend|buddy)(?:'s name is|,?\s+)([A-Z][a-z]+)", "friend", MemoryImportance.MEDIUM),
        (r"my (boss|manager|colleague|coworker)(?:'s name is|,?\s+)([A-Z][a-z]+)", "work_relation", MemoryImportance.MEDIUM),
    ]
    
    EVENT_PATTERNS = [
        (r"(?:yesterday|today|last week|last month)\s+(?:i|we)\s+(.+?)(?:\.|,|$)", "recent_event", MemoryImportance.MEDIUM),
        (r"(?:next week|tomorrow|next month|soon)\s+(?:i|we)\s+(?:will|am going to|'m going to)\s+(.+?)(?:\.|,|$)", "upcoming_event", MemoryImportance.MEDIUM),
        (r"(?:i have|i've got|there's)\s+(?:a|an)\s+(meeting|appointment|interview|exam|test|deadline)\s+(.+?)(?:\.|,|$)", "scheduled_event", MemoryImportance.HIGH),
    ]
    
    GOAL_PATTERNS = [
        (r"(?:i want to|i'd like to|i hope to|my goal is to|i'm trying to)\s+(.+?)(?:\.|,|$)", "goal", MemoryImportance.MEDIUM),
        (r"(?:i'm learning|i'm studying|i'm working on)\s+(.+?)(?:\.|,|$)", "current_project", MemoryImportance.MEDIUM),
    ]
    
    @classmethod
    def extract_memories(cls, text: str, user_id: int) -> List[Memory]:
        """Extract all possible memories from text"""
        memories = []
        text_lower = text.lower()
        
        # Extract facts
        for pattern, fact_type, importance in cls.FACT_PATTERNS:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            for match in matches:
                content = match if isinstance(match, str) else match[0]
                memories.append(Memory(
                    user_id=user_id,
                    memory_type=MemoryType.FACT,
                    content=f"User's {fact_type}: {content.strip()}",
                    summary=f"{fact_type}: {content.strip()}",
                    importance=cls._importance_to_float(importance),
                    tags=[fact_type, "personal_info"],
                    metadata={"fact_type": fact_type, "value": content.strip()}
                ))
        
        # Extract preferences
        for pattern, pref_type, importance in cls.PREFERENCE_PATTERNS:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            for match in matches:
                content = match if isinstance(match, str) else match[0]
                memories.append(Memory(
                    user_id=user_id,
                    memory_type=MemoryType.PREFERENCE,
                    content=f"User preference ({pref_type}): {content.strip()}",
                    summary=f"Prefers: {content.strip()}",
                    importance=cls._importance_to_float(importance),
                    tags=[pref_type, "preference"],
                    metadata={"preference_type": pref_type, "value": content.strip()}
                ))
        
        # Extract relationships
        for pattern, rel_type, importance in cls.RELATIONSHIP_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple) and len(match) >= 2:
                    relation, name = match[0], match[1]
                    memories.append(Memory(
                        user_id=user_id,
                        memory_type=MemoryType.RELATIONSHIP,
                        content=f"User's {relation}: {name}",
                        summary=f"{relation.capitalize()}: {name}",
                        importance=cls._importance_to_float(importance),
                        tags=[rel_type, "relationship", relation],
                        metadata={"relationship_type": relation, "person_name": name}
                    ))
        
        # Extract events
        for pattern, event_type, importance in cls.EVENT_PATTERNS:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            for match in matches:
                content = match if isinstance(match, str) else " ".join(match)
                memories.append(Memory(
                    user_id=user_id,
                    memory_type=MemoryType.EVENT,
                    content=f"Event: {content.strip()}",
                    summary=content.strip()[:100],
                    importance=cls._importance_to_float(importance),
                    tags=[event_type, "event"],
                    metadata={"event_type": event_type}
                ))
        
        # Extract goals
        for pattern, goal_type, importance in cls.GOAL_PATTERNS:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            for match in matches:
                content = match if isinstance(match, str) else match[0]
                memories.append(Memory(
                    user_id=user_id,
                    memory_type=MemoryType.GOAL,
                    content=f"User goal: {content.strip()}",
                    summary=f"Wants to: {content.strip()}",
                    importance=cls._importance_to_float(importance),
                    tags=[goal_type, "goal"],
                    metadata={"goal_type": goal_type}
                ))
        
        return memories
    
    @staticmethod
    def _importance_to_float(importance: MemoryImportance) -> float:
        """Convert importance enum to float"""
        mapping = {
            MemoryImportance.CRITICAL: 1.0,
            MemoryImportance.HIGH: 0.8,
            MemoryImportance.MEDIUM: 0.5,
            MemoryImportance.LOW: 0.3,
            MemoryImportance.TRANSIENT: 0.1
        }
        return mapping.get(importance, 0.5)


class MemoryEngine:
    """
    Advanced memory system for long-term user memory.
    Handles storage, retrieval, consolidation, and decay of memories.
    """
    
    def __init__(self, db_pool):
        self.db_pool = db_pool
        self.extractor = MemoryExtractor()
        self._cache: Dict[int, List[Memory]] = {}  # user_id -> recent memories cache
        self._cache_ttl: Dict[int, datetime] = {}
        
    async def init_schema(self):
        """Initialize memory tables"""
        async with self.db_pool.acquire() as conn:
            await conn.execute('''
                -- User memories table
                CREATE TABLE IF NOT EXISTS user_memories (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    memory_type VARCHAR(50) NOT NULL,
                    content TEXT NOT NULL,
                    summary TEXT,
                    importance FLOAT DEFAULT 0.5,
                    confidence FLOAT DEFAULT 0.8,
                    source VARCHAR(50) DEFAULT 'conversation',
                    
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    last_accessed TIMESTAMPTZ DEFAULT NOW(),
                    access_count INT DEFAULT 0,
                    
                    decay_factor FLOAT DEFAULT 1.0,
                    reinforcement_count INT DEFAULT 0,
                    
                    tags TEXT[] DEFAULT '{}',
                    related_memories INT[] DEFAULT '{}',
                    metadata JSONB DEFAULT '{}',
                    embedding_hash VARCHAR(64),
                    
                    CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );
                
                CREATE INDEX IF NOT EXISTS idx_memory_user ON user_memories(user_id);
                CREATE INDEX IF NOT EXISTS idx_memory_type ON user_memories(user_id, memory_type);
                CREATE INDEX IF NOT EXISTS idx_memory_importance ON user_memories(user_id, importance DESC);
                CREATE INDEX IF NOT EXISTS idx_memory_recent ON user_memories(user_id, last_accessed DESC);
                CREATE INDEX IF NOT EXISTS idx_memory_tags ON user_memories USING gin(tags);
                
                -- Conversation summaries
                CREATE TABLE IF NOT EXISTS conversation_summaries (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    summary TEXT NOT NULL,
                    key_topics TEXT[] DEFAULT '{}',
                    key_facts_learned TEXT[] DEFAULT '{}',
                    emotional_arc TEXT,
                    user_intent TEXT,
                    start_time TIMESTAMPTZ,
                    end_time TIMESTAMPTZ,
                    message_count INT DEFAULT 0,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    
                    CONSTRAINT fk_user_summary FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );
                
                CREATE INDEX IF NOT EXISTS idx_summary_user ON conversation_summaries(user_id, created_at DESC);
                
                -- User knowledge graph (entities and relationships)
                CREATE TABLE IF NOT EXISTS user_entities (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    entity_name VARCHAR(255) NOT NULL,
                    entity_type VARCHAR(50) NOT NULL,
                    properties JSONB DEFAULT '{}',
                    first_mentioned TIMESTAMPTZ DEFAULT NOW(),
                    last_mentioned TIMESTAMPTZ DEFAULT NOW(),
                    mention_count INT DEFAULT 1,
                    
                    CONSTRAINT fk_user_entity FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    UNIQUE(user_id, entity_name, entity_type)
                );
                
                CREATE INDEX IF NOT EXISTS idx_entity_user ON user_entities(user_id);
                
                -- Entity relationships
                CREATE TABLE IF NOT EXISTS entity_relationships (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    entity1_id INT REFERENCES user_entities(id) ON DELETE CASCADE,
                    entity2_id INT REFERENCES user_entities(id) ON DELETE CASCADE,
                    relationship_type VARCHAR(100) NOT NULL,
                    properties JSONB DEFAULT '{}',
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );
                
                CREATE INDEX IF NOT EXISTS idx_rel_user ON entity_relationships(user_id);
            ''')
            logger.info("Memory engine schema initialized")
    
    async def process_conversation(
        self,
        user_id: int,
        user_message: str,
        bot_response: str,
        context: Optional[Dict] = None
    ) -> List[Memory]:
        """
        Process a conversation turn and extract memories.
        Returns newly extracted memories.
        """
        # Extract memories from user message
        new_memories = self.extractor.extract_memories(user_message, user_id)
        
        # Store memories
        stored_memories = []
        for memory in new_memories:
            # Check for duplicates/updates
            existing = await self._find_similar_memory(user_id, memory)
            if existing:
                # Reinforce existing memory
                await self._reinforce_memory(existing.id)
                stored_memories.append(existing)
            else:
                # Store new memory
                stored = await self._store_memory(memory)
                if stored:
                    stored_memories.append(stored)
        
        # Invalidate cache for user
        self._invalidate_cache(user_id)
        
        return stored_memories
    
    async def recall_memories(
        self,
        user_id: int,
        query: Optional[str] = None,
        memory_types: Optional[List[MemoryType]] = None,
        limit: int = 10,
        min_importance: float = 0.3
    ) -> List[Memory]:
        """
        Recall relevant memories for a user.
        If query is provided, uses semantic matching.
        """
        async with self.db_pool.acquire() as conn:
            # Build query
            conditions = ["user_id = $1", "importance >= $2", "decay_factor > 0.1"]
            params = [user_id, min_importance]
            param_idx = 3
            
            if memory_types:
                type_placeholders = ', '.join(f'${i}' for i in range(param_idx, param_idx + len(memory_types)))
                conditions.append(f"memory_type IN ({type_placeholders})")
                params.extend([mt.value for mt in memory_types])
                param_idx += len(memory_types)
            
            # If we have a query, do keyword matching
            if query:
                conditions.append(f"(content ILIKE ${param_idx} OR summary ILIKE ${param_idx})")
                params.append(f"%{query}%")
                param_idx += 1
            
            sql = f'''
                SELECT id, user_id, memory_type, content, summary, importance, 
                       confidence, source, created_at, last_accessed, access_count,
                       decay_factor, reinforcement_count, tags, related_memories, metadata
                FROM user_memories
                WHERE {' AND '.join(conditions)}
                ORDER BY 
                    importance DESC,
                    last_accessed DESC,
                    access_count DESC
                LIMIT ${param_idx}
            '''
            params.append(limit)
            
            rows = await conn.fetch(sql, *params)
            
            memories = []
            for row in rows:
                memory = Memory(
                    id=row['id'],
                    user_id=row['user_id'],
                    memory_type=MemoryType(row['memory_type']),
                    content=row['content'],
                    summary=row['summary'] or "",
                    importance=row['importance'],
                    confidence=row['confidence'],
                    source=row['source'],
                    created_at=row['created_at'],
                    last_accessed=row['last_accessed'],
                    access_count=row['access_count'],
                    decay_factor=row['decay_factor'],
                    reinforcement_count=row['reinforcement_count'],
                    tags=row['tags'] or [],
                    related_memories=row['related_memories'] or [],
                    metadata=row['metadata'] or {}
                )
                memories.append(memory)
                
                # Update access time
                await conn.execute('''
                    UPDATE user_memories 
                    SET last_accessed = NOW(), access_count = access_count + 1
                    WHERE id = $1
                ''', row['id'])
            
            return memories
    
    async def get_user_profile_memories(self, user_id: int) -> Dict[str, Any]:
        """Get a structured profile from user's memories"""
        memories = await self.recall_memories(
            user_id,
            memory_types=[MemoryType.FACT, MemoryType.PREFERENCE],
            limit=50,
            min_importance=0.3
        )
        
        profile = {
            "name": None,
            "location": None,
            "occupation": None,
            "preferences": [],
            "interests": [],
            "facts": []
        }
        
        for mem in memories:
            metadata = mem.metadata or {}
            if mem.memory_type == MemoryType.FACT:
                fact_type = metadata.get("fact_type")
                value = metadata.get("value")
                if fact_type == "name" and value:
                    profile["name"] = value
                elif fact_type == "location" and value:
                    profile["location"] = value
                elif fact_type == "occupation" and value:
                    profile["occupation"] = value
                else:
                    profile["facts"].append(mem.content)
            elif mem.memory_type == MemoryType.PREFERENCE:
                profile["preferences"].append(mem.content)
        
        return profile
    
    async def get_memory_context(self, user_id: int, current_message: str) -> str:
        """
        Get formatted memory context to inject into AI prompt.
        This is the key method that makes the bot remember.
        """
        # Get user profile
        profile = await self.get_user_profile_memories(user_id)
        
        # Get recent conversation summaries
        summaries = await self._get_recent_summaries(user_id, limit=3)
        
        # Get relevant memories based on current message
        relevant = await self.recall_memories(
            user_id,
            query=current_message,
            limit=5,
            min_importance=0.3
        )
        
        # Get relationships
        relationships = await self._get_user_relationships(user_id)
        
        # Format context
        context_parts = []
        
        # User profile
        if profile["name"] or profile["location"] or profile["occupation"]:
            context_parts.append("**About this user:**")
            if profile["name"]:
                context_parts.append(f"- Name: {profile['name']}")
            if profile["location"]:
                context_parts.append(f"- Location: {profile['location']}")
            if profile["occupation"]:
                context_parts.append(f"- Occupation: {profile['occupation']}")
        
        # Preferences
        if profile["preferences"]:
            context_parts.append("\n**User preferences:**")
            for pref in profile["preferences"][:5]:
                context_parts.append(f"- {pref}")
        
        # Relationships
        if relationships:
            context_parts.append("\n**People they've mentioned:**")
            for rel in relationships[:5]:
                context_parts.append(f"- {rel}")
        
        # Relevant memories
        if relevant:
            context_parts.append("\n**Relevant memories from past conversations:**")
            for mem in relevant:
                if mem.content not in str(context_parts):  # Avoid duplicates
                    context_parts.append(f"- {mem.summary or mem.content[:100]}")
        
        # Recent summaries
        if summaries:
            context_parts.append("\n**Recent conversation context:**")
            for summary in summaries[:2]:
                context_parts.append(f"- {summary}")
        
        if not context_parts:
            return ""
        
        return "\n".join(context_parts)
    
    async def summarize_conversation(
        self,
        user_id: int,
        messages: List[Dict[str, str]],
        ai_engine=None
    ) -> Optional[ConversationSummary]:
        """
        Summarize a conversation period and extract learnings.
        Should be called periodically or when conversation ends.
        """
        if not messages or len(messages) < 3:
            return None
        
        # Create summary using AI if available
        if ai_engine:
            summary_text = await self._ai_summarize(messages, ai_engine)
        else:
            # Fallback to simple extraction
            summary_text = self._simple_summarize(messages)
        
        # Extract key topics
        topics = self._extract_topics(messages)
        
        # Determine emotional arc
        emotional_arc = self._analyze_emotional_arc(messages)
        
        summary = ConversationSummary(
            user_id=user_id,
            summary=summary_text,
            key_topics=topics,
            emotional_arc=emotional_arc,
            message_count=len(messages)
        )
        
        # Store summary
        await self._store_summary(summary)
        
        return summary
    
    async def apply_memory_decay(self):
        """
        Apply decay to old, unused memories.
        Should be run periodically (e.g., daily).
        """
        async with self.db_pool.acquire() as conn:
            # Decay memories that haven't been accessed recently
            await conn.execute('''
                UPDATE user_memories
                SET decay_factor = decay_factor * 0.95
                WHERE last_accessed < NOW() - INTERVAL '7 days'
                AND importance < 0.9
                AND decay_factor > 0.1
            ''')
            
            # Remove very decayed low-importance memories
            await conn.execute('''
                DELETE FROM user_memories
                WHERE decay_factor < 0.1
                AND importance < 0.5
                AND reinforcement_count < 2
            ''')
            
            logger.info("Memory decay applied")
    
    async def consolidate_memories(self, user_id: int, ai_engine=None):
        """
        Consolidate and merge similar memories.
        Creates higher-level abstractions from specific memories.
        """
        # Get all memories for user
        memories = await self.recall_memories(user_id, limit=100, min_importance=0.1)
        
        # Group by type
        by_type: Dict[MemoryType, List[Memory]] = {}
        for mem in memories:
            if mem.memory_type not in by_type:
                by_type[mem.memory_type] = []
            by_type[mem.memory_type].append(mem)
        
        # Merge similar memories within each type
        for mem_type, mems in by_type.items():
            if len(mems) > 10:
                # Too many of this type, consolidate
                await self._consolidate_type(user_id, mem_type, mems, ai_engine)
        
        logger.info(f"Consolidated memories for user {user_id}")
    
    # Private helper methods
    
    async def _store_memory(self, memory: Memory) -> Optional[Memory]:
        """Store a memory in the database"""
        try:
            async with self.db_pool.acquire() as conn:
                row = await conn.fetchrow('''
                    INSERT INTO user_memories 
                    (user_id, memory_type, content, summary, importance, confidence, 
                     source, tags, metadata)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    RETURNING id
                ''', 
                    memory.user_id,
                    memory.memory_type.value,
                    memory.content,
                    memory.summary,
                    memory.importance,
                    memory.confidence,
                    memory.source,
                    memory.tags,
                    json.dumps(memory.metadata)
                )
                memory.id = row['id']
                logger.debug(f"Stored memory {memory.id} for user {memory.user_id}")
                return memory
        except Exception as e:
            logger.error(f"Failed to store memory: {e}")
            return None
    
    async def _find_similar_memory(self, user_id: int, memory: Memory) -> Optional[Memory]:
        """Find if a similar memory already exists"""
        async with self.db_pool.acquire() as conn:
            # Check for exact content match or same metadata
            row = await conn.fetchrow('''
                SELECT id, content, importance, reinforcement_count
                FROM user_memories
                WHERE user_id = $1 
                AND memory_type = $2
                AND (
                    content = $3
                    OR (metadata->>'fact_type' = $4 AND metadata->>'fact_type' IS NOT NULL)
                )
            ''',
                user_id,
                memory.memory_type.value,
                memory.content,
                memory.metadata.get("fact_type", "")
            )
            
            if row:
                return Memory(
                    id=row['id'],
                    user_id=user_id,
                    content=row['content'],
                    importance=row['importance'],
                    reinforcement_count=row['reinforcement_count']
                )
            return None
    
    async def _reinforce_memory(self, memory_id: int):
        """Reinforce an existing memory (makes it stronger)"""
        async with self.db_pool.acquire() as conn:
            await conn.execute('''
                UPDATE user_memories
                SET reinforcement_count = reinforcement_count + 1,
                    decay_factor = LEAST(decay_factor + 0.1, 1.0),
                    importance = LEAST(importance + 0.05, 1.0),
                    last_accessed = NOW(),
                    access_count = access_count + 1
                WHERE id = $1
            ''', memory_id)
    
    async def _get_recent_summaries(self, user_id: int, limit: int = 3) -> List[str]:
        """Get recent conversation summaries"""
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch('''
                SELECT summary FROM conversation_summaries
                WHERE user_id = $1
                ORDER BY created_at DESC
                LIMIT $2
            ''', user_id, limit)
            return [row['summary'] for row in rows]
    
    async def _get_user_relationships(self, user_id: int) -> List[str]:
        """Get user's mentioned relationships"""
        memories = await self.recall_memories(
            user_id,
            memory_types=[MemoryType.RELATIONSHIP],
            limit=10,
            min_importance=0.3
        )
        return [mem.content for mem in memories]
    
    async def _store_summary(self, summary: ConversationSummary):
        """Store a conversation summary"""
        async with self.db_pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO conversation_summaries
                (user_id, summary, key_topics, key_facts_learned, emotional_arc,
                 user_intent, start_time, end_time, message_count)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            ''',
                summary.user_id,
                summary.summary,
                summary.key_topics,
                summary.key_facts_learned,
                summary.emotional_arc,
                summary.user_intent,
                summary.start_time,
                summary.end_time,
                summary.message_count
            )
    
    def _invalidate_cache(self, user_id: int):
        """Invalidate memory cache for user"""
        if user_id in self._cache:
            del self._cache[user_id]
        if user_id in self._cache_ttl:
            del self._cache_ttl[user_id]
    
    def _simple_summarize(self, messages: List[Dict[str, str]]) -> str:
        """Simple summarization without AI"""
        user_msgs = [m['content'] for m in messages if m.get('role') == 'user']
        if not user_msgs:
            return "No significant conversation"
        return f"User discussed: {', '.join(user_msgs[:3])}..."[:200]
    
    async def _ai_summarize(self, messages: List[Dict], ai_engine) -> str:
        """Use AI to summarize conversation"""
        try:
            prompt = f"""Summarize this conversation in 1-2 sentences, focusing on key topics and what was accomplished:

{json.dumps(messages[-10:], indent=2)}

Summary:"""
            response = await ai_engine.generate(prompt, max_tokens=100)
            return response.strip()
        except Exception as e:
            logger.error(f"AI summarization failed: {e}")
            return self._simple_summarize(messages)
    
    def _extract_topics(self, messages: List[Dict]) -> List[str]:
        """Extract key topics from messages"""
        topics = []
        # Simple keyword extraction
        keywords = ['help', 'question', 'problem', 'want', 'need', 'create', 'build', 'learn', 'understand']
        for msg in messages:
            content = msg.get('content', '').lower()
            for keyword in keywords:
                if keyword in content and keyword not in topics:
                    topics.append(keyword)
        return topics[:5]
    
    def _analyze_emotional_arc(self, messages: List[Dict]) -> str:
        """Analyze the emotional progression of conversation"""
        # Simple heuristic
        positive_words = ['thanks', 'great', 'awesome', 'perfect', 'love', 'happy']
        negative_words = ['frustrated', 'angry', 'confused', 'stuck', 'problem', 'issue']
        
        emotions = []
        for msg in messages:
            content = msg.get('content', '').lower()
            if any(w in content for w in positive_words):
                emotions.append('positive')
            elif any(w in content for w in negative_words):
                emotions.append('negative')
            else:
                emotions.append('neutral')
        
        if not emotions:
            return "neutral"
        
        start = emotions[0]
        end = emotions[-1]
        
        if start == 'negative' and end == 'positive':
            return "improved (started frustrated, ended satisfied)"
        elif start == 'positive' and end == 'positive':
            return "consistently positive"
        elif start == 'negative' and end == 'negative':
            return "needs follow-up (user may still be frustrated)"
        else:
            return "neutral throughout"
    
    async def _consolidate_type(
        self,
        user_id: int,
        mem_type: MemoryType,
        memories: List[Memory],
        ai_engine
    ):
        """Consolidate memories of a specific type"""
        # Group very similar memories and merge them
        # This is a placeholder for more sophisticated consolidation
        pass


# Global memory engine instance
_memory_engine: Optional[MemoryEngine] = None


async def init_memory_engine(db_pool) -> MemoryEngine:
    """Initialize the global memory engine"""
    global _memory_engine
    _memory_engine = MemoryEngine(db_pool)
    await _memory_engine.init_schema()
    return _memory_engine


def get_memory_engine() -> Optional[MemoryEngine]:
    """Get the global memory engine instance"""
    return _memory_engine
