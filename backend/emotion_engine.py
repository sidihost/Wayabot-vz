"""
Waya Bot Builder - Emotion Engine Module
Hume AI integration for emotion detection and empathic responses
"""

import asyncio
import json
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
import httpx
from config import get_settings

settings = get_settings()


class EmotionEngine:
    """Hume AI Emotion Detection Engine"""
    
    # Emotion categories with descriptions
    EMOTION_CATEGORIES = {
        "admiration": {"emoji": "star", "intensity": "positive", "response_style": "appreciative"},
        "adoration": {"emoji": "heart", "intensity": "positive", "response_style": "warm"},
        "aesthetic_appreciation": {"emoji": "sparkle", "intensity": "positive", "response_style": "thoughtful"},
        "amusement": {"emoji": "grin", "intensity": "positive", "response_style": "playful"},
        "anger": {"emoji": "angry", "intensity": "negative", "response_style": "calming"},
        "annoyance": {"emoji": "unamused", "intensity": "negative", "response_style": "patient"},
        "anxiety": {"emoji": "worried", "intensity": "negative", "response_style": "reassuring"},
        "awe": {"emoji": "wow", "intensity": "positive", "response_style": "enthusiastic"},
        "awkwardness": {"emoji": "flushed", "intensity": "neutral", "response_style": "supportive"},
        "boredom": {"emoji": "yawn", "intensity": "negative", "response_style": "engaging"},
        "calmness": {"emoji": "relieved", "intensity": "positive", "response_style": "peaceful"},
        "concentration": {"emoji": "think", "intensity": "neutral", "response_style": "focused"},
        "confusion": {"emoji": "confused", "intensity": "neutral", "response_style": "clarifying"},
        "contemplation": {"emoji": "ponder", "intensity": "neutral", "response_style": "reflective"},
        "contempt": {"emoji": "smirk", "intensity": "negative", "response_style": "understanding"},
        "contentment": {"emoji": "smile", "intensity": "positive", "response_style": "warm"},
        "craving": {"emoji": "drool", "intensity": "neutral", "response_style": "helpful"},
        "determination": {"emoji": "determined", "intensity": "positive", "response_style": "encouraging"},
        "disappointment": {"emoji": "disappointed", "intensity": "negative", "response_style": "supportive"},
        "disapproval": {"emoji": "thumbdown", "intensity": "negative", "response_style": "understanding"},
        "disgust": {"emoji": "nauseated", "intensity": "negative", "response_style": "validating"},
        "distress": {"emoji": "persevere", "intensity": "negative", "response_style": "comforting"},
        "doubt": {"emoji": "think", "intensity": "neutral", "response_style": "reassuring"},
        "ecstasy": {"emoji": "starry", "intensity": "positive", "response_style": "celebratory"},
        "embarrassment": {"emoji": "flushed", "intensity": "negative", "response_style": "gentle"},
        "empathic_pain": {"emoji": "pensive", "intensity": "negative", "response_style": "compassionate"},
        "enthusiasm": {"emoji": "fire", "intensity": "positive", "response_style": "energetic"},
        "envy": {"emoji": "envious", "intensity": "negative", "response_style": "understanding"},
        "excitement": {"emoji": "excited", "intensity": "positive", "response_style": "enthusiastic"},
        "fear": {"emoji": "fearful", "intensity": "negative", "response_style": "protective"},
        "gratitude": {"emoji": "pray", "intensity": "positive", "response_style": "appreciative"},
        "guilt": {"emoji": "pensive", "intensity": "negative", "response_style": "compassionate"},
        "horror": {"emoji": "scream", "intensity": "negative", "response_style": "calming"},
        "interest": {"emoji": "curious", "intensity": "positive", "response_style": "engaging"},
        "joy": {"emoji": "joy", "intensity": "positive", "response_style": "cheerful"},
        "love": {"emoji": "heart", "intensity": "positive", "response_style": "warm"},
        "nostalgia": {"emoji": "pensiv", "intensity": "neutral", "response_style": "reflective"},
        "pain": {"emoji": "hurt", "intensity": "negative", "response_style": "compassionate"},
        "pride": {"emoji": "proud", "intensity": "positive", "response_style": "celebratory"},
        "realization": {"emoji": "bulb", "intensity": "neutral", "response_style": "supportive"},
        "relief": {"emoji": "relieved", "intensity": "positive", "response_style": "reassuring"},
        "romance": {"emoji": "hearts", "intensity": "positive", "response_style": "warm"},
        "sadness": {"emoji": "sad", "intensity": "negative", "response_style": "comforting"},
        "sarcasm": {"emoji": "smirk", "intensity": "neutral", "response_style": "witty"},
        "satisfaction": {"emoji": "satisfied", "intensity": "positive", "response_style": "affirming"},
        "shame": {"emoji": "flushed", "intensity": "negative", "response_style": "gentle"},
        "surprise_negative": {"emoji": "astonished", "intensity": "negative", "response_style": "calming"},
        "surprise_positive": {"emoji": "open_mouth", "intensity": "positive", "response_style": "enthusiastic"},
        "sympathy": {"emoji": "hug", "intensity": "neutral", "response_style": "compassionate"},
        "tiredness": {"emoji": "sleepy", "intensity": "negative", "response_style": "gentle"},
        "triumph": {"emoji": "trophy", "intensity": "positive", "response_style": "celebratory"},
    }
    
    # Response tone mapping based on dominant emotions
    RESPONSE_TONES = {
        "calming": {
            "system_prompt": "Respond with calm, measured, and reassuring language. Acknowledge their feelings and help them feel at ease.",
            "temperature": 0.6
        },
        "supportive": {
            "system_prompt": "Be warm, supportive, and understanding. Show empathy and offer encouragement.",
            "temperature": 0.7
        },
        "enthusiastic": {
            "system_prompt": "Match their energy! Be excited, positive, and engaging. Celebrate with them.",
            "temperature": 0.8
        },
        "comforting": {
            "system_prompt": "Be gentle and compassionate. Offer comfort and let them know it's okay to feel this way.",
            "temperature": 0.5
        },
        "playful": {
            "system_prompt": "Be fun, witty, and lighthearted. Match their playful mood.",
            "temperature": 0.9
        },
        "focused": {
            "system_prompt": "Be clear, direct, and helpful. They're in a focused state, so provide concise information.",
            "temperature": 0.4
        },
        "reflective": {
            "system_prompt": "Be thoughtful and philosophical. Engage in deeper conversation and reflection.",
            "temperature": 0.7
        },
        "understanding": {
            "system_prompt": "Show deep understanding without judgment. Validate their perspective.",
            "temperature": 0.6
        },
        "engaging": {
            "system_prompt": "Be interesting and captivating. Spark their curiosity and keep them engaged.",
            "temperature": 0.8
        },
        "gentle": {
            "system_prompt": "Be soft, patient, and non-judgmental. Handle with care.",
            "temperature": 0.5
        },
        "warm": {
            "system_prompt": "Be friendly, caring, and affectionate. Create a warm conversational atmosphere.",
            "temperature": 0.7
        },
        "compassionate": {
            "system_prompt": "Show deep empathy and care. Be present for their emotional experience.",
            "temperature": 0.6
        },
        "celebratory": {
            "system_prompt": "Celebrate their achievement or good news! Be joyful and congratulatory.",
            "temperature": 0.85
        },
        "reassuring": {
            "system_prompt": "Provide reassurance and confidence. Help them feel secure and capable.",
            "temperature": 0.6
        },
        "protective": {
            "system_prompt": "Be reassuring and help them feel safe. Address their concerns directly.",
            "temperature": 0.5
        },
        "clarifying": {
            "system_prompt": "Be clear and patient in explaining. Break down complex topics simply.",
            "temperature": 0.5
        },
        "patient": {
            "system_prompt": "Be extremely patient and understanding. Don't rush, take time to help.",
            "temperature": 0.6
        },
        "appreciative": {
            "system_prompt": "Express genuine appreciation. Acknowledge and value their input.",
            "temperature": 0.7
        },
        "affirming": {
            "system_prompt": "Affirm and validate. Reinforce positive feelings and outcomes.",
            "temperature": 0.7
        },
        "thoughtful": {
            "system_prompt": "Be contemplative and considered in your response. Show depth of thought.",
            "temperature": 0.65
        },
        "helpful": {
            "system_prompt": "Focus on being maximally helpful. Address their needs directly.",
            "temperature": 0.6
        },
        "witty": {
            "system_prompt": "Be clever and quick-witted. Match their sarcastic or humorous tone appropriately.",
            "temperature": 0.8
        },
        "validating": {
            "system_prompt": "Validate their feelings and perspective. Acknowledge the legitimacy of their reaction.",
            "temperature": 0.6
        },
        "encouraging": {
            "system_prompt": "Be motivating and encouraging. Help them feel capable and supported.",
            "temperature": 0.75
        },
        "energetic": {
            "system_prompt": "Match their high energy! Be dynamic and vivacious in your response.",
            "temperature": 0.85
        },
        "cheerful": {
            "system_prompt": "Be bright, optimistic, and cheerful. Spread positivity.",
            "temperature": 0.8
        },
        "peaceful": {
            "system_prompt": "Maintain a peaceful, serene tone. Foster tranquility in the conversation.",
            "temperature": 0.5
        },
    }
    
    def __init__(self):
        self.api_key = settings.hume_api_key
        self.base_url = "https://api.hume.ai/v0"
        self._client: Optional[httpx.AsyncClient] = None
        self._emotion_cache: Dict[int, Dict[str, Any]] = {}  # user_id -> emotions
    
    @property
    def is_configured(self) -> bool:
        """Check if Hume AI is properly configured"""
        return bool(self.api_key) and settings.enable_emotion_ai
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={
                    "X-Hume-Api-Key": self.api_key,
                    "Content-Type": "application/json"
                },
                timeout=30.0
            )
        return self._client
    
    async def close(self):
        """Close the HTTP client"""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def analyze_text_emotion(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Analyze emotions in text using Hume AI Language model
        
        Args:
            text: Text to analyze
            
        Returns:
            Dictionary with emotion predictions and scores
        """
        if not self.is_configured:
            return self._fallback_emotion_analysis(text)
        
        if not text or len(text.strip()) < 5:
            return None
        
        try:
            client = await self._get_client()
            
            response = await client.post(
                "/batch/jobs",
                json={
                    "models": {
                        "language": {}
                    },
                    "text": [text[:5000]]  # Limit text length
                }
            )
            response.raise_for_status()
            job_data = response.json()
            job_id = job_data.get("job_id")
            
            if not job_id:
                return self._fallback_emotion_analysis(text)
            
            # Poll for results (with timeout)
            for _ in range(10):  # Max 10 attempts
                await asyncio.sleep(1)
                
                result_response = await client.get(f"/batch/jobs/{job_id}/predictions")
                if result_response.status_code == 200:
                    results = result_response.json()
                    return self._parse_emotion_results(results)
                elif result_response.status_code == 202:
                    continue  # Still processing
                else:
                    break
            
            return self._fallback_emotion_analysis(text)
            
        except Exception as e:
            print(f"Hume AI error: {e}")
            return self._fallback_emotion_analysis(text)
    
    async def analyze_voice_emotion(self, audio_bytes: bytes) -> Optional[Dict[str, Any]]:
        """
        Analyze emotions in voice/audio using Hume AI Prosody model
        
        Args:
            audio_bytes: Audio data to analyze
            
        Returns:
            Dictionary with emotion predictions
        """
        if not self.is_configured:
            return None
        
        try:
            # Need multipart upload for audio
            async with httpx.AsyncClient(
                base_url=self.base_url,
                headers={"X-Hume-Api-Key": self.api_key},
                timeout=60.0
            ) as upload_client:
                files = {"file": ("audio.mp3", audio_bytes, "audio/mpeg")}
                response = await upload_client.post(
                    "/batch/jobs",
                    data={"models": json.dumps({"prosody": {}})},
                    files=files
                )
                response.raise_for_status()
                job_data = response.json()
                job_id = job_data.get("job_id")
                
                if not job_id:
                    return None
                
                # Poll for results
                for _ in range(15):
                    await asyncio.sleep(2)
                    result_response = await upload_client.get(f"/batch/jobs/{job_id}/predictions")
                    if result_response.status_code == 200:
                        results = result_response.json()
                        return self._parse_emotion_results(results)
                    elif result_response.status_code == 202:
                        continue
                    else:
                        break
                
            return None
            
        except Exception as e:
            print(f"Voice emotion analysis error: {e}")
            return None
    
    def _parse_emotion_results(self, results: Any) -> Dict[str, Any]:
        """Parse Hume AI emotion results into standardized format"""
        emotions = {}
        
        try:
            # Navigate through Hume's response structure
            if isinstance(results, list) and len(results) > 0:
                predictions = results[0].get("results", {}).get("predictions", [])
                if predictions:
                    for pred in predictions:
                        if "models" in pred:
                            language_results = pred["models"].get("language", {})
                            if "grouped_predictions" in language_results:
                                for group in language_results["grouped_predictions"]:
                                    for prediction in group.get("predictions", []):
                                        for emotion in prediction.get("emotions", []):
                                            name = emotion.get("name", "").lower().replace(" ", "_")
                                            score = emotion.get("score", 0)
                                            emotions[name] = score
        except Exception as e:
            print(f"Error parsing emotion results: {e}")
        
        if not emotions:
            return self._fallback_emotion_analysis("")
        
        # Get top emotions
        sorted_emotions = sorted(emotions.items(), key=lambda x: x[1], reverse=True)
        top_emotions = sorted_emotions[:5]
        dominant_emotion = top_emotions[0][0] if top_emotions else "neutral"
        
        return {
            "dominant_emotion": dominant_emotion,
            "confidence": top_emotions[0][1] if top_emotions else 0.5,
            "top_emotions": dict(top_emotions),
            "all_emotions": emotions,
            "response_style": self._get_response_style(dominant_emotion),
            "analyzed_at": datetime.utcnow().isoformat()
        }
    
    def _fallback_emotion_analysis(self, text: str) -> Dict[str, Any]:
        """
        Rule-based fallback emotion analysis when API is unavailable
        """
        text_lower = text.lower()
        
        # Keyword-based emotion detection
        emotion_keywords = {
            "joy": ["happy", "glad", "excited", "wonderful", "amazing", "great", "love", "awesome", "fantastic", "yay"],
            "sadness": ["sad", "unhappy", "depressed", "down", "crying", "miss", "lonely", "heartbroken", "upset"],
            "anger": ["angry", "mad", "furious", "annoyed", "frustrated", "hate", "rage", "irritated"],
            "fear": ["scared", "afraid", "worried", "anxious", "nervous", "terrified", "panic"],
            "surprise_positive": ["wow", "amazing", "incredible", "unbelievable", "shocked", "omg"],
            "gratitude": ["thanks", "thank you", "grateful", "appreciate", "thankful"],
            "confusion": ["confused", "don't understand", "what", "huh", "unclear", "lost"],
            "enthusiasm": ["excited", "can't wait", "pumped", "stoked", "eager"],
            "tiredness": ["tired", "exhausted", "sleepy", "worn out", "drained"],
            "interest": ["interesting", "curious", "tell me more", "fascinating", "intriguing"],
        }
        
        detected_emotions = {}
        for emotion, keywords in emotion_keywords.items():
            score = sum(1 for kw in keywords if kw in text_lower) / len(keywords)
            if score > 0:
                detected_emotions[emotion] = min(score * 2, 1.0)  # Scale up, cap at 1.0
        
        if not detected_emotions:
            detected_emotions = {"calmness": 0.5}
        
        sorted_emotions = sorted(detected_emotions.items(), key=lambda x: x[1], reverse=True)
        dominant = sorted_emotions[0][0]
        
        return {
            "dominant_emotion": dominant,
            "confidence": sorted_emotions[0][1],
            "top_emotions": dict(sorted_emotions[:5]),
            "all_emotions": detected_emotions,
            "response_style": self._get_response_style(dominant),
            "analyzed_at": datetime.utcnow().isoformat(),
            "method": "fallback"
        }
    
    def _get_response_style(self, emotion: str) -> str:
        """Get the appropriate response style for an emotion"""
        emotion_info = self.EMOTION_CATEGORIES.get(emotion)
        if emotion_info:
            return emotion_info.get("response_style", "supportive")
        return "supportive"
    
    def get_tone_prompt(self, emotion: str) -> Tuple[str, float]:
        """
        Get the system prompt and temperature for responding to an emotion
        
        Returns:
            Tuple of (system_prompt, temperature)
        """
        response_style = self._get_response_style(emotion)
        tone_config = self.RESPONSE_TONES.get(response_style, self.RESPONSE_TONES["supportive"])
        return tone_config["system_prompt"], tone_config["temperature"]
    
    def get_empathic_response_context(self, emotions: Dict[str, Any]) -> str:
        """
        Generate context for AI to create empathic responses
        """
        dominant = emotions.get("dominant_emotion", "neutral")
        confidence = emotions.get("confidence", 0.5)
        top_emotions = emotions.get("top_emotions", {})
        
        emotion_info = self.EMOTION_CATEGORIES.get(dominant, {})
        intensity = emotion_info.get("intensity", "neutral")
        
        context_lines = [
            f"The user appears to be feeling {dominant} (confidence: {confidence:.0%}).",
        ]
        
        if len(top_emotions) > 1:
            other_emotions = [e for e in list(top_emotions.keys())[1:4] if top_emotions[e] > 0.1]
            if other_emotions:
                context_lines.append(f"They may also be experiencing: {', '.join(other_emotions)}.")
        
        if intensity == "negative":
            context_lines.append("Be extra supportive and gentle in your response.")
        elif intensity == "positive":
            context_lines.append("Match their positive energy appropriately.")
        
        return " ".join(context_lines)
    
    async def update_user_emotional_state(
        self,
        db,
        user_id: int,
        emotions: Dict[str, Any]
    ) -> bool:
        """Store user's emotional state in database for tracking"""
        try:
            await db.execute("""
                INSERT INTO user_emotional_history (
                    user_id, dominant_emotion, confidence, 
                    top_emotions, analyzed_at
                ) VALUES ($1, $2, $3, $4, NOW())
            """,
                user_id,
                emotions.get("dominant_emotion"),
                emotions.get("confidence"),
                json.dumps(emotions.get("top_emotions", {}))
            )
            return True
        except Exception as e:
            print(f"Error storing emotional state: {e}")
            return False
    
    async def get_user_emotional_history(
        self,
        db,
        user_id: int,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get user's recent emotional history"""
        try:
            rows = await db.fetch("""
                SELECT dominant_emotion, confidence, top_emotions, analyzed_at
                FROM user_emotional_history
                WHERE user_id = $1
                ORDER BY analyzed_at DESC
                LIMIT $2
            """, user_id, limit)
            
            return [
                {
                    "emotion": row["dominant_emotion"],
                    "confidence": row["confidence"],
                    "details": json.loads(row["top_emotions"]) if row["top_emotions"] else {},
                    "time": row["analyzed_at"]
                }
                for row in rows
            ]
        except Exception as e:
            print(f"Error fetching emotional history: {e}")
            return []
    
    async def get_emotional_insights(
        self,
        db,
        user_id: int,
        days: int = 7
    ) -> Dict[str, Any]:
        """Generate insights about user's emotional patterns"""
        try:
            rows = await db.fetch("""
                SELECT dominant_emotion, confidence, analyzed_at
                FROM user_emotional_history
                WHERE user_id = $1 AND analyzed_at > NOW() - INTERVAL '%s days'
                ORDER BY analyzed_at DESC
            """ % days, user_id)
            
            if not rows:
                return {"message": "Not enough data for insights yet."}
            
            # Count emotions
            emotion_counts = {}
            for row in rows:
                emotion = row["dominant_emotion"]
                emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
            
            total = len(rows)
            dominant_overall = max(emotion_counts.items(), key=lambda x: x[1])
            
            # Categorize by intensity
            positive_count = 0
            negative_count = 0
            neutral_count = 0
            
            for emotion, count in emotion_counts.items():
                emotion_info = self.EMOTION_CATEGORIES.get(emotion, {})
                intensity = emotion_info.get("intensity", "neutral")
                if intensity == "positive":
                    positive_count += count
                elif intensity == "negative":
                    negative_count += count
                else:
                    neutral_count += count
            
            return {
                "period_days": days,
                "total_interactions": total,
                "most_common_emotion": dominant_overall[0],
                "emotion_distribution": {
                    k: f"{v/total:.0%}" for k, v in emotion_counts.items()
                },
                "sentiment_breakdown": {
                    "positive": f"{positive_count/total:.0%}",
                    "negative": f"{negative_count/total:.0%}",
                    "neutral": f"{neutral_count/total:.0%}"
                },
                "wellbeing_score": min(100, max(0, int(
                    (positive_count * 2 + neutral_count - negative_count * 1.5) / total * 50 + 50
                )))
            }
            
        except Exception as e:
            print(f"Error generating insights: {e}")
            return {"error": "Could not generate insights"}


# Global engine instance
emotion_engine = EmotionEngine()
