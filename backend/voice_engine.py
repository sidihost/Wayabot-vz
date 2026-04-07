"""
Waya Bot Builder - Voice Engine Module
ElevenLabs integration for text-to-speech and voice cloning
"""

import asyncio
import hashlib
import io
import os
import tempfile
from typing import Optional, Dict, Any, List, AsyncGenerator
from datetime import datetime
import httpx
from config import get_settings

settings = get_settings()


class VoiceEngine:
    """ElevenLabs Voice AI Engine for text-to-speech"""
    
    # Available voices with descriptions
    AVAILABLE_VOICES = {
        "Rachel": {"id": "21m00Tcm4TlvDq8ikWAM", "description": "Calm, professional female voice", "use_case": "narration, podcasts"},
        "Domi": {"id": "AZnzlk1XvdvUeBnXmlld", "description": "Strong, confident female voice", "use_case": "audiobooks, announcements"},
        "Bella": {"id": "EXAVITQu4vr4xnSDxMaL", "description": "Soft, friendly female voice", "use_case": "customer service, tutorials"},
        "Antoni": {"id": "ErXwobaYiN019PkySvjV", "description": "Well-rounded male voice", "use_case": "general purpose, explainers"},
        "Thomas": {"id": "GBv7mTt0atIp3Br8iCZE", "description": "Calm, soothing male voice", "use_case": "meditation, storytelling"},
        "Charlie": {"id": "IKne3meq5aSn9XLyUdCD", "description": "Friendly Australian male voice", "use_case": "casual content, vlogs"},
        "Emily": {"id": "LcfcDJNUP1GQjkzn1xUU", "description": "Clear, articulate female voice", "use_case": "news, educational"},
        "Elli": {"id": "MF3mGyEYCl7XYWbV9V6O", "description": "Youthful, energetic female voice", "use_case": "gaming, entertainment"},
        "Josh": {"id": "TxGEqnHWrfWFTfGW9XjX", "description": "Deep, authoritative male voice", "use_case": "documentaries, trailers"},
        "Arnold": {"id": "VR6AewLTigWG4xSOukaG", "description": "Crisp, British male voice", "use_case": "audiobooks, formal content"},
        "Adam": {"id": "pNInz6obpgDQGcFmaJgB", "description": "Deep, narrative male voice", "use_case": "audiobooks, storytelling"},
        "Sam": {"id": "yoZ06aMxZJJ28mfd3POQ", "description": "Raspy, dynamic male voice", "use_case": "commercials, action"},
    }
    
    # Voice settings presets
    VOICE_STYLES = {
        "default": {"stability": 0.5, "similarity_boost": 0.75, "style": 0.0, "use_speaker_boost": True},
        "stable": {"stability": 0.8, "similarity_boost": 0.5, "style": 0.0, "use_speaker_boost": False},
        "expressive": {"stability": 0.3, "similarity_boost": 0.8, "style": 0.5, "use_speaker_boost": True},
        "narrative": {"stability": 0.6, "similarity_boost": 0.7, "style": 0.2, "use_speaker_boost": True},
        "conversational": {"stability": 0.4, "similarity_boost": 0.8, "style": 0.3, "use_speaker_boost": True},
        "dramatic": {"stability": 0.2, "similarity_boost": 0.9, "style": 0.7, "use_speaker_boost": True},
    }
    
    # Supported languages for multilingual model
    SUPPORTED_LANGUAGES = [
        "English", "German", "Polish", "Spanish", "Italian", "French", "Portuguese",
        "Hindi", "Arabic", "Chinese", "Japanese", "Korean", "Indonesian", "Dutch",
        "Turkish", "Filipino", "Swedish", "Bulgarian", "Romanian", "Czech", "Greek",
        "Finnish", "Croatian", "Malay", "Slovak", "Danish", "Tamil", "Ukrainian", "Russian"
    ]
    
    def __init__(self):
        self.api_key = settings.elevenlabs_api_key
        self.base_url = "https://api.elevenlabs.io/v1"
        self.default_voice = settings.elevenlabs_default_voice
        self.model = settings.elevenlabs_model
        self._client: Optional[httpx.AsyncClient] = None
        self._voices_cache: Dict[str, Any] = {}
        self._cache_timestamp: Optional[datetime] = None
    
    @property
    def is_configured(self) -> bool:
        """Check if ElevenLabs is properly configured"""
        return bool(self.api_key) and settings.enable_voice_ai
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={
                    "xi-api-key": self.api_key,
                    "Content-Type": "application/json"
                },
                timeout=60.0
            )
        return self._client
    
    async def close(self):
        """Close the HTTP client"""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    def get_voice_id(self, voice_name: str) -> str:
        """Get voice ID by name"""
        voice_info = self.AVAILABLE_VOICES.get(voice_name)
        if voice_info:
            return voice_info["id"]
        # If not in predefined, assume it's already a voice ID
        return voice_name
    
    async def list_voices(self) -> List[Dict[str, Any]]:
        """List all available voices including custom ones"""
        if not self.is_configured:
            return []
        
        try:
            client = await self._get_client()
            response = await client.get("/voices")
            response.raise_for_status()
            data = response.json()
            return data.get("voices", [])
        except Exception as e:
            print(f"Error listing voices: {e}")
            return []
    
    async def get_user_subscription(self) -> Dict[str, Any]:
        """Get user subscription info including character quota"""
        if not self.is_configured:
            return {}
        
        try:
            client = await self._get_client()
            response = await client.get("/user/subscription")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error getting subscription: {e}")
            return {}
    
    async def text_to_speech(
        self,
        text: str,
        voice: Optional[str] = None,
        style: str = "default",
        language: Optional[str] = None,
        output_format: str = "mp3_44100_128"
    ) -> Optional[bytes]:
        """
        Convert text to speech
        
        Args:
            text: Text to convert
            voice: Voice name or ID
            style: Voice style preset
            language: Language for multilingual model
            output_format: Audio output format
            
        Returns:
            Audio bytes or None if failed
        """
        if not self.is_configured:
            return None
        
        if not text or len(text.strip()) == 0:
            return None
        
        # Limit text length
        text = text[:5000]
        
        voice_name = voice or self.default_voice
        voice_id = self.get_voice_id(voice_name)
        voice_settings = self.VOICE_STYLES.get(style, self.VOICE_STYLES["default"])
        
        try:
            client = await self._get_client()
            
            payload = {
                "text": text,
                "model_id": self.model,
                "voice_settings": voice_settings
            }
            
            # Add language hint for multilingual model
            if language and "multilingual" in self.model:
                payload["language_code"] = self._get_language_code(language)
            
            response = await client.post(
                f"/text-to-speech/{voice_id}",
                json=payload,
                params={"output_format": output_format}
            )
            response.raise_for_status()
            
            return response.content
            
        except httpx.HTTPStatusError as e:
            print(f"ElevenLabs API error: {e.response.status_code} - {e.response.text}")
            return None
        except Exception as e:
            print(f"Error generating speech: {e}")
            return None
    
    async def text_to_speech_stream(
        self,
        text: str,
        voice: Optional[str] = None,
        style: str = "default"
    ) -> AsyncGenerator[bytes, None]:
        """Stream text to speech for real-time playback"""
        if not self.is_configured:
            return
        
        voice_name = voice or self.default_voice
        voice_id = self.get_voice_id(voice_name)
        voice_settings = self.VOICE_STYLES.get(style, self.VOICE_STYLES["default"])
        
        try:
            client = await self._get_client()
            
            async with client.stream(
                "POST",
                f"/text-to-speech/{voice_id}/stream",
                json={
                    "text": text[:5000],
                    "model_id": self.model,
                    "voice_settings": voice_settings
                }
            ) as response:
                response.raise_for_status()
                async for chunk in response.aiter_bytes():
                    yield chunk
                    
        except Exception as e:
            print(f"Error streaming speech: {e}")
    
    async def clone_voice(
        self,
        name: str,
        audio_files: List[bytes],
        description: Optional[str] = None,
        labels: Optional[Dict[str, str]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Clone a voice from audio samples
        
        Args:
            name: Name for the cloned voice
            audio_files: List of audio file bytes
            description: Voice description
            labels: Optional labels/tags
            
        Returns:
            Voice info dict or None if failed
        """
        if not self.is_configured:
            return None
        
        if not audio_files or len(audio_files) == 0:
            return None
        
        try:
            client = await self._get_client()
            
            # Prepare multipart form data
            files = []
            for i, audio in enumerate(audio_files):
                files.append(("files", (f"sample_{i}.mp3", audio, "audio/mpeg")))
            
            data = {"name": name}
            if description:
                data["description"] = description
            if labels:
                data["labels"] = str(labels)
            
            # Need to recreate client without JSON content-type for multipart
            async with httpx.AsyncClient(
                base_url=self.base_url,
                headers={"xi-api-key": self.api_key},
                timeout=120.0
            ) as upload_client:
                response = await upload_client.post(
                    "/voices/add",
                    data=data,
                    files=files
                )
                response.raise_for_status()
                return response.json()
                
        except Exception as e:
            print(f"Error cloning voice: {e}")
            return None
    
    async def delete_voice(self, voice_id: str) -> bool:
        """Delete a cloned voice"""
        if not self.is_configured:
            return False
        
        try:
            client = await self._get_client()
            response = await client.delete(f"/voices/{voice_id}")
            return response.status_code == 200
        except Exception as e:
            print(f"Error deleting voice: {e}")
            return False
    
    async def get_voice_settings(self, voice_id: str) -> Optional[Dict[str, Any]]:
        """Get settings for a specific voice"""
        if not self.is_configured:
            return None
        
        try:
            client = await self._get_client()
            response = await client.get(f"/voices/{voice_id}/settings")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error getting voice settings: {e}")
            return None
    
    def _get_language_code(self, language: str) -> str:
        """Convert language name to code"""
        language_codes = {
            "English": "en", "German": "de", "Polish": "pl", "Spanish": "es",
            "Italian": "it", "French": "fr", "Portuguese": "pt", "Hindi": "hi",
            "Arabic": "ar", "Chinese": "zh", "Japanese": "ja", "Korean": "ko",
            "Indonesian": "id", "Dutch": "nl", "Turkish": "tr", "Filipino": "tl",
            "Swedish": "sv", "Bulgarian": "bg", "Romanian": "ro", "Czech": "cs",
            "Greek": "el", "Finnish": "fi", "Croatian": "hr", "Malay": "ms",
            "Slovak": "sk", "Danish": "da", "Tamil": "ta", "Ukrainian": "uk", "Russian": "ru"
        }
        return language_codes.get(language, "en")
    
    def get_available_voices_formatted(self) -> str:
        """Get formatted list of available voices"""
        lines = ["Available Voices:\n"]
        for name, info in self.AVAILABLE_VOICES.items():
            lines.append(f"  {name}: {info['description']}")
            lines.append(f"    Best for: {info['use_case']}\n")
        return "\n".join(lines)
    
    def get_voice_styles_formatted(self) -> str:
        """Get formatted list of voice styles"""
        lines = ["Voice Styles:\n"]
        style_descriptions = {
            "default": "Balanced, natural sound",
            "stable": "Consistent, predictable output",
            "expressive": "More emotional variation",
            "narrative": "Great for storytelling",
            "conversational": "Natural, chatty tone",
            "dramatic": "High emotion, theatrical"
        }
        for style, desc in style_descriptions.items():
            lines.append(f"  {style}: {desc}")
        return "\n".join(lines)


class VoicePreferences:
    """Manage user voice preferences"""
    
    def __init__(self):
        self.engine = VoiceEngine()
    
    async def save_user_preference(
        self,
        db,
        user_id: int,
        voice: str,
        style: str = "default"
    ) -> bool:
        """Save user's voice preferences to database"""
        try:
            await db.execute("""
                INSERT INTO user_voice_preferences (user_id, voice_name, voice_style, updated_at)
                VALUES ($1, $2, $3, NOW())
                ON CONFLICT (user_id) DO UPDATE SET
                    voice_name = EXCLUDED.voice_name,
                    voice_style = EXCLUDED.voice_style,
                    updated_at = NOW()
            """, user_id, voice, style)
            return True
        except Exception as e:
            print(f"Error saving voice preference: {e}")
            return False
    
    async def get_user_preference(self, db, user_id: int) -> Dict[str, str]:
        """Get user's voice preferences"""
        try:
            row = await db.fetchrow("""
                SELECT voice_name, voice_style FROM user_voice_preferences
                WHERE user_id = $1
            """, user_id)
            if row:
                return {"voice": row["voice_name"], "style": row["voice_style"]}
            return {"voice": "Rachel", "style": "default"}
        except Exception:
            return {"voice": "Rachel", "style": "default"}


# Global engine instance
voice_engine = VoiceEngine()
voice_preferences = VoicePreferences()
