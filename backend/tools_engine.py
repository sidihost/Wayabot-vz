"""
Waya Bot Builder - Tools Engine
Real-world capabilities: web search, code execution, image analysis, document processing.
Gives the bot the ability to interact with the real world.
"""

import asyncio
import aiohttp
import base64
import io
import json
import logging
import os
import re
import subprocess
import tempfile
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List, Dict, Any, Tuple, Union
import urllib.parse

logger = logging.getLogger(__name__)


class ToolType(str, Enum):
    """Available tools"""
    WEB_SEARCH = "web_search"
    CODE_EXECUTION = "code_execution"
    IMAGE_ANALYSIS = "image_analysis"
    DOCUMENT_PROCESSING = "document_processing"
    CALCULATOR = "calculator"
    WEATHER = "weather"
    NEWS = "news"
    TRANSLATION = "translation"
    TELEGRAM_PROFILE = "telegram_profile"


class ToolStatus(str, Enum):
    """Tool execution status"""
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    RATE_LIMITED = "rate_limited"


@dataclass
class ToolResult:
    """Result from a tool execution"""
    tool: ToolType
    status: ToolStatus
    data: Any = None
    error: Optional[str] = None
    execution_time_ms: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_success(self) -> bool:
        return self.status == ToolStatus.SUCCESS
    
    def to_context(self) -> str:
        """Convert result to context string for AI"""
        if not self.is_success:
            return f"[{self.tool.value} failed: {self.error}]"
        
        if self.tool == ToolType.WEB_SEARCH:
            return self._format_search_results()
        elif self.tool == ToolType.CODE_EXECUTION:
            return self._format_code_result()
        elif self.tool == ToolType.IMAGE_ANALYSIS:
            return self._format_image_analysis()
        elif self.tool == ToolType.DOCUMENT_PROCESSING:
            return self._format_document()
        elif self.tool == ToolType.WEATHER:
            return self._format_weather()
        elif self.tool == ToolType.CALCULATOR:
            return f"Calculation result: {self.data}"
        elif self.tool == ToolType.TELEGRAM_PROFILE:
            return self._format_telegram_profile()
        else:
            return str(self.data)
    
    def _format_search_results(self) -> str:
        if not self.data:
            return "[No search results found]"
        results = []
        for i, r in enumerate(self.data[:5], 1):
            results.append(f"{i}. **{r.get('title', 'No title')}**\n   {r.get('snippet', '')}\n   Source: {r.get('url', '')}")
        return "**Web Search Results:**\n" + "\n\n".join(results)
    
    def _format_code_result(self) -> str:
        if not self.data:
            return "[Code execution produced no output]"
        output = self.data.get('output', '')
        error = self.data.get('error', '')
        if error:
            return f"**Code Execution Error:**\n```\n{error}\n```"
        return f"**Code Output:**\n```\n{output}\n```"
    
    def _format_image_analysis(self) -> str:
        if not self.data:
            return "[Could not analyze image]"
        return f"**Image Analysis:**\n{self.data.get('description', self.data)}"
    
    def _format_document(self) -> str:
        if not self.data:
            return "[Could not process document]"
        return f"**Document Content:**\n{self.data.get('text', self.data)[:2000]}..."
    
    def _format_weather(self) -> str:
        if not self.data:
            return "[Weather data unavailable]"
        w = self.data
        return f"**Weather in {w.get('location', 'Unknown')}:**\n" \
               f"- Temperature: {w.get('temperature', 'N/A')}\n" \
               f"- Conditions: {w.get('conditions', 'N/A')}\n" \
               f"- Humidity: {w.get('humidity', 'N/A')}"
    
    def _format_telegram_profile(self) -> str:
        if not self.data:
            return "[Could not analyze profile]"
        p = self.data
        lines = [f"**Telegram Profile Analysis: @{p.get('username', 'Unknown')}**\n"]
        
        # Basic info
        if p.get('first_name') or p.get('last_name'):
            name = f"{p.get('first_name', '')} {p.get('last_name', '')}".strip()
            lines.append(f"**Name:** {name}")
        if p.get('bio'):
            lines.append(f"**Bio:** {p['bio']}")
        if p.get('user_id'):
            lines.append(f"**User ID:** `{p['user_id']}`")
        
        # Account features
        features = []
        if p.get('is_premium'):
            features.append("Premium")
        if p.get('has_private_forwards'):
            features.append("Private Forwards")
        if p.get('is_bot'):
            features.append("Bot Account")
        if features:
            lines.append(f"**Features:** {', '.join(features)}")
        
        # Profile photos
        if p.get('photo_count'):
            lines.append(f"**Profile Photos:** {p['photo_count']}")
        
        # AI Analysis
        if p.get('ai_analysis'):
            lines.append(f"\n**AI Insights:**\n{p['ai_analysis']}")
        
        # Social links
        if p.get('social_links'):
            lines.append(f"\n**Detected Links:** {', '.join(p['social_links'])}")
        
        return "\n".join(lines)


@dataclass
class SearchResult:
    """A single search result"""
    title: str
    url: str
    snippet: str
    source: str = ""
    published_date: Optional[str] = None


class WebSearchTool:
    """
    Web search using multiple providers with fallback.
    Supports: Brave Search, Tavily, SerpAPI, DuckDuckGo
    """
    
    def __init__(self):
        self.brave_api_key = os.environ.get("BRAVE_API_KEY")
        self.tavily_api_key = os.environ.get("TAVILY_API_KEY")
        self.serpapi_key = os.environ.get("SERPAPI_KEY")
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=15)
            )
        return self.session
    
    async def search(
        self,
        query: str,
        num_results: int = 5,
        search_type: str = "general"  # general, news, images
    ) -> ToolResult:
        """
        Search the web for information.
        Falls back through providers if one fails.
        """
        start_time = datetime.now(timezone.utc)
        
        # Try providers in order
        providers = [
            self._search_brave,
            self._search_tavily,
            self._search_duckduckgo,
        ]
        
        for provider in providers:
            try:
                results = await provider(query, num_results, search_type)
                if results:
                    elapsed = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
                    return ToolResult(
                        tool=ToolType.WEB_SEARCH,
                        status=ToolStatus.SUCCESS,
                        data=results,
                        execution_time_ms=int(elapsed),
                        metadata={"query": query, "provider": provider.__name__}
                    )
            except Exception as e:
                logger.warning(f"Search provider {provider.__name__} failed: {e}")
                continue
        
        return ToolResult(
            tool=ToolType.WEB_SEARCH,
            status=ToolStatus.ERROR,
            error="All search providers failed"
        )
    
    async def _search_brave(self, query: str, num_results: int, search_type: str) -> List[Dict]:
        """Search using Brave Search API"""
        if not self.brave_api_key:
            raise ValueError("BRAVE_API_KEY not configured")
        
        session = await self._get_session()
        
        url = "https://api.search.brave.com/res/v1/web/search"
        headers = {
            "Accept": "application/json",
            "X-Subscription-Token": self.brave_api_key
        }
        params = {
            "q": query,
            "count": num_results,
            "text_decorations": False
        }
        
        async with session.get(url, headers=headers, params=params) as resp:
            if resp.status != 200:
                raise Exception(f"Brave API returned {resp.status}")
            
            data = await resp.json()
            results = []
            
            for item in data.get("web", {}).get("results", [])[:num_results]:
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "snippet": item.get("description", ""),
                    "source": "Brave Search"
                })
            
            return results
    
    async def _search_tavily(self, query: str, num_results: int, search_type: str) -> List[Dict]:
        """Search using Tavily API"""
        if not self.tavily_api_key:
            raise ValueError("TAVILY_API_KEY not configured")
        
        session = await self._get_session()
        
        url = "https://api.tavily.com/search"
        payload = {
            "api_key": self.tavily_api_key,
            "query": query,
            "max_results": num_results,
            "search_depth": "basic"
        }
        
        async with session.post(url, json=payload) as resp:
            if resp.status != 200:
                raise Exception(f"Tavily API returned {resp.status}")
            
            data = await resp.json()
            results = []
            
            for item in data.get("results", [])[:num_results]:
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "snippet": item.get("content", "")[:300],
                    "source": "Tavily"
                })
            
            return results
    
    async def _search_duckduckgo(self, query: str, num_results: int, search_type: str) -> List[Dict]:
        """Fallback search using DuckDuckGo (no API key needed)"""
        session = await self._get_session()
        
        # Use DuckDuckGo instant answer API
        url = "https://api.duckduckgo.com/"
        params = {
            "q": query,
            "format": "json",
            "no_html": 1,
            "skip_disambig": 1
        }
        
        async with session.get(url, params=params) as resp:
            if resp.status != 200:
                raise Exception(f"DuckDuckGo API returned {resp.status}")
            
            data = await resp.json()
            results = []
            
            # Get abstract if available
            if data.get("Abstract"):
                results.append({
                    "title": data.get("Heading", query),
                    "url": data.get("AbstractURL", ""),
                    "snippet": data.get("Abstract", ""),
                    "source": data.get("AbstractSource", "DuckDuckGo")
                })
            
            # Get related topics
            for item in data.get("RelatedTopics", [])[:num_results-len(results)]:
                if isinstance(item, dict) and item.get("Text"):
                    results.append({
                        "title": item.get("Text", "")[:60] + "...",
                        "url": item.get("FirstURL", ""),
                        "snippet": item.get("Text", ""),
                        "source": "DuckDuckGo"
                    })
            
            return results
    
    async def close(self):
        """Close the HTTP session"""
        if self.session and not self.session.closed:
            await self.session.close()


class CodeExecutionTool:
    """
    Safe code execution in a sandboxed environment.
    Supports Python with restricted capabilities.
    """
    
    # Safe built-ins for code execution
    SAFE_BUILTINS = {
        'abs', 'all', 'any', 'ascii', 'bin', 'bool', 'bytes', 'callable',
        'chr', 'complex', 'dict', 'divmod', 'enumerate', 'filter', 'float',
        'format', 'frozenset', 'hash', 'hex', 'int', 'isinstance', 'issubclass',
        'iter', 'len', 'list', 'map', 'max', 'min', 'next', 'oct', 'ord',
        'pow', 'print', 'range', 'repr', 'reversed', 'round', 'set', 'slice',
        'sorted', 'str', 'sum', 'tuple', 'type', 'zip'
    }
    
    # Blocked imports
    BLOCKED_MODULES = {
        'os', 'sys', 'subprocess', 'shutil', 'socket', 'requests',
        'urllib', 'http', 'ftplib', 'smtplib', 'telnetlib', 'pickle',
        'shelve', 'marshal', 'dbm', 'sqlite3', 'builtins', '__builtins__'
    }
    
    def __init__(self, max_execution_time: int = 5, max_output_length: int = 5000):
        self.max_execution_time = max_execution_time
        self.max_output_length = max_output_length
    
    async def execute(
        self,
        code: str,
        language: str = "python"
    ) -> ToolResult:
        """
        Execute code safely and return the result.
        """
        start_time = datetime.now(timezone.utc)
        
        if language.lower() != "python":
            return ToolResult(
                tool=ToolType.CODE_EXECUTION,
                status=ToolStatus.ERROR,
                error=f"Language '{language}' not supported. Only Python is available."
            )
        
        # Validate code for safety
        safety_check = self._check_code_safety(code)
        if safety_check:
            return ToolResult(
                tool=ToolType.CODE_EXECUTION,
                status=ToolStatus.ERROR,
                error=f"Code blocked for safety: {safety_check}"
            )
        
        try:
            result = await self._execute_python(code)
            elapsed = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            
            return ToolResult(
                tool=ToolType.CODE_EXECUTION,
                status=ToolStatus.SUCCESS,
                data=result,
                execution_time_ms=int(elapsed),
                metadata={"language": language}
            )
        except asyncio.TimeoutError:
            return ToolResult(
                tool=ToolType.CODE_EXECUTION,
                status=ToolStatus.TIMEOUT,
                error=f"Code execution timed out after {self.max_execution_time}s"
            )
        except Exception as e:
            return ToolResult(
                tool=ToolType.CODE_EXECUTION,
                status=ToolStatus.ERROR,
                error=str(e)
            )
    
    def _check_code_safety(self, code: str) -> Optional[str]:
        """Check if code is safe to execute"""
        code_lower = code.lower()
        
        # Check for blocked imports
        import_pattern = r'(?:import|from)\s+(\w+)'
        imports = re.findall(import_pattern, code)
        for imp in imports:
            if imp.lower() in self.BLOCKED_MODULES:
                return f"Import of '{imp}' is not allowed"
        
        # Check for dangerous patterns
        dangerous_patterns = [
            (r'exec\s*\(', 'exec() is not allowed'),
            (r'eval\s*\(', 'eval() is not allowed'),
            (r'__import__', '__import__ is not allowed'),
            (r'open\s*\(', 'file operations are not allowed'),
            (r'compile\s*\(', 'compile() is not allowed'),
            (r'globals\s*\(', 'globals() is not allowed'),
            (r'locals\s*\(', 'locals() is not allowed'),
        ]
        
        for pattern, message in dangerous_patterns:
            if re.search(pattern, code_lower):
                return message
        
        return None
    
    async def _execute_python(self, code: str) -> Dict[str, Any]:
        """Execute Python code in a restricted environment"""
        # Create a restricted globals environment
        import math
        import statistics
        import random
        import json as json_module
        import datetime as dt_module
        
        restricted_globals = {
            '__builtins__': {name: getattr(__builtins__, name) if hasattr(__builtins__, name) else None 
                            for name in self.SAFE_BUILTINS},
            'math': math,
            'statistics': statistics,
            'random': random,
            'json': json_module,
            'datetime': dt_module,
        }
        
        # Capture output
        output_buffer = io.StringIO()
        result = {"output": "", "error": "", "return_value": None}
        
        async def run_code():
            import sys
            old_stdout = sys.stdout
            sys.stdout = output_buffer
            
            try:
                # Execute the code
                exec(code, restricted_globals)
                result["output"] = output_buffer.getvalue()[:self.max_output_length]
            except Exception as e:
                result["error"] = f"{type(e).__name__}: {str(e)}"
            finally:
                sys.stdout = old_stdout
        
        # Run with timeout
        try:
            await asyncio.wait_for(run_code(), timeout=self.max_execution_time)
        except asyncio.TimeoutError:
            result["error"] = "Execution timed out"
        
        return result


class ImageAnalysisTool:
    """
    Image analysis using vision models (GPT-4V, Claude Vision).
    Can describe images, extract text, answer questions.
    """
    
    def __init__(self):
        self.openai_api_key = os.environ.get("OPENAI_API_KEY")
        self.anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY")
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30)
            )
        return self.session
    
    async def analyze(
        self,
        image_data: Union[str, bytes],  # URL or base64 or raw bytes
        query: Optional[str] = None,
        analysis_type: str = "describe"  # describe, ocr, answer
    ) -> ToolResult:
        """
        Analyze an image and return description or answer questions.
        """
        start_time = datetime.now(timezone.utc)
        
        # Convert image to base64 if needed
        image_b64 = await self._prepare_image(image_data)
        if not image_b64:
            return ToolResult(
                tool=ToolType.IMAGE_ANALYSIS,
                status=ToolStatus.ERROR,
                error="Could not process image"
            )
        
        # Build the prompt based on analysis type
        if analysis_type == "ocr":
            prompt = "Extract all text visible in this image. Return just the text, formatted appropriately."
        elif analysis_type == "answer" and query:
            prompt = f"Look at this image and answer: {query}"
        else:
            prompt = "Describe this image in detail. What do you see? Include any text, people, objects, and context."
        
        # Try vision models
        try:
            if self.openai_api_key:
                result = await self._analyze_with_openai(image_b64, prompt)
            elif self.anthropic_api_key:
                result = await self._analyze_with_anthropic(image_b64, prompt)
            else:
                return ToolResult(
                    tool=ToolType.IMAGE_ANALYSIS,
                    status=ToolStatus.ERROR,
                    error="No vision API configured. Set OPENAI_API_KEY or ANTHROPIC_API_KEY."
                )
            
            elapsed = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            return ToolResult(
                tool=ToolType.IMAGE_ANALYSIS,
                status=ToolStatus.SUCCESS,
                data={"description": result, "analysis_type": analysis_type},
                execution_time_ms=int(elapsed)
            )
        except Exception as e:
            logger.error(f"Image analysis failed: {e}")
            return ToolResult(
                tool=ToolType.IMAGE_ANALYSIS,
                status=ToolStatus.ERROR,
                error=str(e)
            )
    
    async def _prepare_image(self, image_data: Union[str, bytes]) -> Optional[str]:
        """Convert image to base64"""
        try:
            if isinstance(image_data, bytes):
                return base64.b64encode(image_data).decode('utf-8')
            
            if image_data.startswith('data:image'):
                # Already base64 data URL
                return image_data.split(',')[1]
            
            if image_data.startswith('http'):
                # Download the image
                session = await self._get_session()
                async with session.get(image_data) as resp:
                    if resp.status == 200:
                        data = await resp.read()
                        return base64.b64encode(data).decode('utf-8')
            
            # Assume it's already base64
            return image_data
        except Exception as e:
            logger.error(f"Image preparation failed: {e}")
            return None
    
    async def _analyze_with_openai(self, image_b64: str, prompt: str) -> str:
        """Analyze image with GPT-4 Vision"""
        session = await self._get_session()
        
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.openai_api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "gpt-4o",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_b64}",
                                "detail": "auto"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 500
        }
        
        async with session.post(url, headers=headers, json=payload) as resp:
            if resp.status != 200:
                error_text = await resp.text()
                raise Exception(f"OpenAI API error: {error_text}")
            
            data = await resp.json()
            return data["choices"][0]["message"]["content"]
    
    async def _analyze_with_anthropic(self, image_b64: str, prompt: str) -> str:
        """Analyze image with Claude Vision"""
        session = await self._get_session()
        
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": self.anthropic_api_key,
            "content-type": "application/json",
            "anthropic-version": "2023-06-01"
        }
        
        payload = {
            "model": "claude-3-5-sonnet-latest",
            "max_tokens": 500,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": image_b64
                            }
                        },
                        {"type": "text", "text": prompt}
                    ]
                }
            ]
        }
        
        async with session.post(url, headers=headers, json=payload) as resp:
            if resp.status != 200:
                error_text = await resp.text()
                raise Exception(f"Anthropic API error: {error_text}")
            
            data = await resp.json()
            return data["content"][0]["text"]
    
    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()


class DocumentProcessingTool:
    """
    Process documents: PDFs, Word docs, text files.
    Extract text, summarize, answer questions.
    """
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30)
            )
        return self.session
    
    async def process(
        self,
        document_data: Union[str, bytes],  # URL or raw bytes
        doc_type: str = "auto",  # pdf, docx, txt, auto
        operation: str = "extract"  # extract, summarize
    ) -> ToolResult:
        """
        Process a document and extract/summarize content.
        """
        start_time = datetime.now(timezone.utc)
        
        try:
            # Get document bytes
            if isinstance(document_data, str) and document_data.startswith('http'):
                session = await self._get_session()
                async with session.get(document_data) as resp:
                    if resp.status != 200:
                        raise Exception(f"Failed to download document: {resp.status}")
                    doc_bytes = await resp.read()
                    
                    # Auto-detect type from content-type or URL
                    if doc_type == "auto":
                        content_type = resp.headers.get('content-type', '')
                        if 'pdf' in content_type or document_data.endswith('.pdf'):
                            doc_type = 'pdf'
                        elif 'word' in content_type or document_data.endswith('.docx'):
                            doc_type = 'docx'
                        else:
                            doc_type = 'txt'
            else:
                doc_bytes = document_data if isinstance(document_data, bytes) else document_data.encode()
            
            # Extract text based on type
            if doc_type == 'pdf':
                text = await self._extract_pdf(doc_bytes)
            elif doc_type == 'docx':
                text = await self._extract_docx(doc_bytes)
            else:
                text = doc_bytes.decode('utf-8', errors='ignore')
            
            elapsed = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            
            return ToolResult(
                tool=ToolType.DOCUMENT_PROCESSING,
                status=ToolStatus.SUCCESS,
                data={
                    "text": text[:10000],  # Limit text length
                    "char_count": len(text),
                    "doc_type": doc_type
                },
                execution_time_ms=int(elapsed)
            )
        except Exception as e:
            logger.error(f"Document processing failed: {e}")
            return ToolResult(
                tool=ToolType.DOCUMENT_PROCESSING,
                status=ToolStatus.ERROR,
                error=str(e)
            )
    
    async def _extract_pdf(self, pdf_bytes: bytes) -> str:
        """Extract text from PDF"""
        try:
            import pypdf
            
            pdf_file = io.BytesIO(pdf_bytes)
            reader = pypdf.PdfReader(pdf_file)
            
            text_parts = []
            for page in reader.pages:
                text_parts.append(page.extract_text())
            
            return "\n\n".join(text_parts)
        except ImportError:
            # Fallback: try pdfminer
            try:
                from pdfminer.high_level import extract_text
                pdf_file = io.BytesIO(pdf_bytes)
                return extract_text(pdf_file)
            except ImportError:
                raise Exception("PDF processing not available. Install pypdf or pdfminer.six")
    
    async def _extract_docx(self, docx_bytes: bytes) -> str:
        """Extract text from Word document"""
        try:
            import docx
            
            doc_file = io.BytesIO(docx_bytes)
            doc = docx.Document(doc_file)
            
            text_parts = []
            for para in doc.paragraphs:
                text_parts.append(para.text)
            
            return "\n".join(text_parts)
        except ImportError:
            raise Exception("Word document processing not available. Install python-docx")
    
    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()


class CalculatorTool:
    """Safe mathematical calculations"""
    
    def calculate(self, expression: str) -> ToolResult:
        """
        Safely evaluate a mathematical expression.
        """
        try:
            # Only allow safe math operations
            import math
            
            # Clean the expression
            expr = expression.replace('^', '**')
            
            # Allowed names
            safe_dict = {
                'abs': abs, 'round': round, 'min': min, 'max': max,
                'sum': sum, 'pow': pow, 'sqrt': math.sqrt,
                'sin': math.sin, 'cos': math.cos, 'tan': math.tan,
                'log': math.log, 'log10': math.log10, 'exp': math.exp,
                'pi': math.pi, 'e': math.e,
                'floor': math.floor, 'ceil': math.ceil
            }
            
            # Evaluate safely
            result = eval(expr, {"__builtins__": {}}, safe_dict)
            
            return ToolResult(
                tool=ToolType.CALCULATOR,
                status=ToolStatus.SUCCESS,
                data=result
            )
        except Exception as e:
            return ToolResult(
                tool=ToolType.CALCULATOR,
                status=ToolStatus.ERROR,
                error=str(e)
            )


class WeatherTool:
    """Get weather information"""
    
    def __init__(self):
        self.api_key = os.environ.get("OPENWEATHER_API_KEY")
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=10)
            )
        return self.session
    
    async def get_weather(self, location: str) -> ToolResult:
        """Get current weather for a location"""
        if not self.api_key:
            return ToolResult(
                tool=ToolType.WEATHER,
                status=ToolStatus.ERROR,
                error="Weather API not configured"
            )
        
        try:
            session = await self._get_session()
            
            url = "https://api.openweathermap.org/data/2.5/weather"
            params = {
                "q": location,
                "appid": self.api_key,
                "units": "metric"
            }
            
            async with session.get(url, params=params) as resp:
                if resp.status != 200:
                    return ToolResult(
                        tool=ToolType.WEATHER,
                        status=ToolStatus.ERROR,
                        error=f"Weather API error: {resp.status}"
                    )
                
                data = await resp.json()
                
                weather = {
                    "location": data.get("name", location),
                    "temperature": f"{data['main']['temp']:.1f}°C",
                    "feels_like": f"{data['main']['feels_like']:.1f}°C",
                    "conditions": data['weather'][0]['description'].title(),
                    "humidity": f"{data['main']['humidity']}%",
                    "wind": f"{data['wind']['speed']} m/s"
                }
                
                return ToolResult(
                    tool=ToolType.WEATHER,
                    status=ToolStatus.SUCCESS,
                    data=weather
                )
        except Exception as e:
            return ToolResult(
                tool=ToolType.WEATHER,
                status=ToolStatus.ERROR,
                error=str(e)
            )
    
    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()


class TelegramProfileTool:
    """
    Telegram profile analysis tool.
    Fetches and analyzes public Telegram user profiles.
    """
    
    def __init__(self):
        self.bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
        self.openai_api_key = os.environ.get("OPENAI_API_KEY")
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30)
            )
        return self.session
    
    async def analyze_profile(
        self,
        username: str,
        include_ai_analysis: bool = True
    ) -> ToolResult:
        """
        Analyze a Telegram user profile by username.
        
        Args:
            username: Telegram username (with or without @)
            include_ai_analysis: Whether to include AI-powered insights
        
        Returns:
            ToolResult with profile information and analysis
        """
        start_time = datetime.now(timezone.utc)
        
        # Clean username
        username = username.strip().lstrip('@')
        
        if not username:
            return ToolResult(
                tool=ToolType.TELEGRAM_PROFILE,
                status=ToolStatus.ERROR,
                error="Please provide a valid Telegram username"
            )
        
        try:
            # Gather profile data from multiple sources
            profile_data = await self._fetch_profile_data(username)
            
            if not profile_data:
                return ToolResult(
                    tool=ToolType.TELEGRAM_PROFILE,
                    status=ToolStatus.ERROR,
                    error=f"Could not find profile for @{username}. The user may not exist or may have privacy settings enabled."
                )
            
            # Add AI analysis if enabled and we have OpenAI
            if include_ai_analysis and self.openai_api_key:
                ai_analysis = await self._generate_ai_analysis(profile_data)
                profile_data['ai_analysis'] = ai_analysis
            
            elapsed = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            
            return ToolResult(
                tool=ToolType.TELEGRAM_PROFILE,
                status=ToolStatus.SUCCESS,
                data=profile_data,
                execution_time_ms=int(elapsed),
                metadata={"username": username}
            )
            
        except Exception as e:
            logger.error(f"Profile analysis failed for @{username}: {e}")
            return ToolResult(
                tool=ToolType.TELEGRAM_PROFILE,
                status=ToolStatus.ERROR,
                error=f"Error analyzing profile: {str(e)}"
            )
    
    async def _fetch_profile_data(self, username: str) -> Optional[Dict[str, Any]]:
        """Fetch profile data using multiple methods"""
        profile_data = {
            'username': username,
            'first_name': None,
            'last_name': None,
            'bio': None,
            'user_id': None,
            'is_premium': False,
            'is_bot': False,
            'has_private_forwards': False,
            'photo_count': 0,
            'social_links': [],
            'profile_photo_url': None,
        }
        
        session = await self._get_session()
        
        # Method 1: Try t.me web scraping for public info
        try:
            async with session.get(
                f"https://t.me/{username}",
                headers={'User-Agent': 'Mozilla/5.0 (compatible; WayaBot/2.0)'}
            ) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    
                    # Extract profile info from HTML
                    import re
                    
                    # Name extraction
                    name_match = re.search(r'<div class="tgme_page_title"><span[^>]*>([^<]+)</span>', html)
                    if name_match:
                        full_name = name_match.group(1).strip()
                        parts = full_name.split(' ', 1)
                        profile_data['first_name'] = parts[0]
                        if len(parts) > 1:
                            profile_data['last_name'] = parts[1]
                    
                    # Bio extraction
                    bio_match = re.search(r'<div class="tgme_page_description[^"]*">([^<]+)', html)
                    if bio_match:
                        profile_data['bio'] = bio_match.group(1).strip()
                    
                    # Profile photo
                    photo_match = re.search(r'<img class="tgme_page_photo_image"[^>]+src="([^"]+)"', html)
                    if photo_match:
                        profile_data['profile_photo_url'] = photo_match.group(1)
                        profile_data['photo_count'] = 1
                    
                    # Check if it's a bot
                    if 'tgme_page_extra">bot' in html.lower():
                        profile_data['is_bot'] = True
                    
                    # Extract any links in bio
                    links = re.findall(r'href="(https?://[^"]+)"', html)
                    social_patterns = ['twitter', 'instagram', 'github', 'linkedin', 'youtube', 'tiktok', 'facebook']
                    for link in links:
                        for pattern in social_patterns:
                            if pattern in link.lower():
                                profile_data['social_links'].append(link)
                                break
                    
                    # Check page validity
                    if 'tgme_page_title' in html or 'tgme_page_photo_image' in html:
                        return profile_data
        except Exception as e:
            logger.warning(f"t.me scraping failed: {e}")
        
        # Method 2: Try Telegram Bot API if we have the bot token
        if self.bot_token:
            try:
                # We can get user info through the bot API if the user has interacted
                # This is limited but can provide additional data
                pass
            except Exception as e:
                logger.warning(f"Bot API profile fetch failed: {e}")
        
        # Method 3: Try telemetr.io or similar public profile services
        try:
            async with session.get(
                f"https://telemetr.io/api/tg/users/{username}",
                headers={'User-Agent': 'Mozilla/5.0 (compatible; WayaBot/2.0)'}
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data:
                        profile_data['user_id'] = data.get('id')
                        profile_data['first_name'] = data.get('first_name') or profile_data['first_name']
                        profile_data['last_name'] = data.get('last_name') or profile_data['last_name']
                        if data.get('photo'):
                            profile_data['photo_count'] = 1
                        return profile_data
        except Exception as e:
            logger.warning(f"Telemetr.io fetch failed: {e}")
        
        # Return what we have if we got any data
        if profile_data['first_name'] or profile_data['bio']:
            return profile_data
        
        return None
    
    async def _generate_ai_analysis(self, profile_data: Dict[str, Any]) -> str:
        """Generate AI-powered analysis of the profile"""
        if not self.openai_api_key:
            return ""
        
        session = await self._get_session()
        
        # Build profile summary for AI
        profile_summary = f"""
Username: @{profile_data.get('username', 'Unknown')}
Name: {profile_data.get('first_name', '')} {profile_data.get('last_name', '')}
Bio: {profile_data.get('bio', 'No bio')}
Is Bot: {profile_data.get('is_bot', False)}
Is Premium: {profile_data.get('is_premium', False)}
Social Links: {', '.join(profile_data.get('social_links', [])) or 'None detected'}
"""
        
        try:
            url = "https://api.openai.com/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.openai_api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "gpt-4o-mini",
                "messages": [
                    {
                        "role": "system",
                        "content": """You are an expert at analyzing Telegram profiles. Based on the available public information, provide brief insights about:
1. What this user might be interested in based on their bio/name
2. Whether this appears to be a personal or professional account
3. Any notable observations
4. Potential topics for conversation

Keep your analysis concise (3-4 sentences), professional, and respectful of privacy. Only analyze what is publicly visible."""
                    },
                    {
                        "role": "user",
                        "content": f"Analyze this Telegram profile:\n{profile_summary}"
                    }
                ],
                "max_tokens": 200,
                "temperature": 0.7
            }
            
            async with session.post(url, headers=headers, json=payload) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data['choices'][0]['message']['content']
        except Exception as e:
            logger.warning(f"AI analysis failed: {e}")
        
        return ""
    
    async def analyze_by_user_id(self, user_id: int) -> ToolResult:
        """
        Analyze profile by Telegram user ID.
        Limited info available through this method.
        """
        start_time = datetime.now(timezone.utc)
        
        if not self.bot_token:
            return ToolResult(
                tool=ToolType.TELEGRAM_PROFILE,
                status=ToolStatus.ERROR,
                error="Bot token required for user ID lookup"
            )
        
        try:
            session = await self._get_session()
            
            # Try to get user profile photos
            url = f"https://api.telegram.org/bot{self.bot_token}/getUserProfilePhotos"
            async with session.post(url, json={"user_id": user_id}) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get('ok'):
                        photos = data.get('result', {})
                        photo_count = photos.get('total_count', 0)
                        
                        profile_data = {
                            'user_id': user_id,
                            'username': None,
                            'first_name': None,
                            'last_name': None,
                            'bio': None,
                            'photo_count': photo_count,
                            'is_premium': False,
                            'is_bot': False,
                        }
                        
                        elapsed = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
                        
                        return ToolResult(
                            tool=ToolType.TELEGRAM_PROFILE,
                            status=ToolStatus.SUCCESS,
                            data=profile_data,
                            execution_time_ms=int(elapsed),
                            metadata={"user_id": user_id, "note": "Limited data available via user ID"}
                        )
            
            return ToolResult(
                tool=ToolType.TELEGRAM_PROFILE,
                status=ToolStatus.ERROR,
                error=f"Could not fetch profile for user ID {user_id}"
            )
            
        except Exception as e:
            return ToolResult(
                tool=ToolType.TELEGRAM_PROFILE,
                status=ToolStatus.ERROR,
                error=str(e)
            )
    
    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()


class ToolsEngine:
    """
    Master tools engine that manages all tools and handles tool selection.
    """
    
    def __init__(self):
        self.web_search = WebSearchTool()
        self.code_execution = CodeExecutionTool()
        self.image_analysis = ImageAnalysisTool()
        self.document_processing = DocumentProcessingTool()
        self.calculator = CalculatorTool()
        self.weather = WeatherTool()
        self.telegram_profile = TelegramProfileTool()
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get list of available tools for AI to use"""
        return [
            {
                "name": "web_search",
                "description": "Search the web for current information, news, facts, prices, etc.",
                "parameters": {
                    "query": "The search query",
                    "num_results": "Number of results (default 5)"
                }
            },
            {
                "name": "code_execution",
                "description": "Execute Python code for calculations, data processing, etc.",
                "parameters": {
                    "code": "The Python code to execute"
                }
            },
            {
                "name": "image_analysis",
                "description": "Analyze an image - describe it, extract text, or answer questions about it",
                "parameters": {
                    "image_data": "Image URL or base64 data",
                    "query": "Optional question to answer about the image",
                    "analysis_type": "describe, ocr, or answer"
                }
            },
            {
                "name": "document_processing",
                "description": "Extract and process text from documents (PDF, Word, text files)",
                "parameters": {
                    "document_data": "Document URL or data",
                    "doc_type": "pdf, docx, txt, or auto"
                }
            },
            {
                "name": "calculator",
                "description": "Perform mathematical calculations",
                "parameters": {
                    "expression": "The math expression to evaluate"
                }
            },
            {
                "name": "weather",
                "description": "Get current weather for a location",
                "parameters": {
                    "location": "City name or location"
                }
            },
            {
                "name": "telegram_profile",
                "description": "Analyze a Telegram user profile by username. Get info about users, detect their interests, social links, and more.",
                "parameters": {
                    "username": "Telegram username (with or without @)",
                    "include_ai_analysis": "Whether to include AI-powered insights (default true)"
                }
            }
        ]
    
    async def execute_tool(
        self,
        tool_name: str,
        **kwargs
    ) -> ToolResult:
        """Execute a tool by name"""
        tool_map = {
            "web_search": lambda: self.web_search.search(
                kwargs.get("query", ""),
                kwargs.get("num_results", 5)
            ),
            "code_execution": lambda: self.code_execution.execute(
                kwargs.get("code", ""),
                kwargs.get("language", "python")
            ),
            "image_analysis": lambda: self.image_analysis.analyze(
                kwargs.get("image_data", ""),
                kwargs.get("query"),
                kwargs.get("analysis_type", "describe")
            ),
            "document_processing": lambda: self.document_processing.process(
                kwargs.get("document_data", ""),
                kwargs.get("doc_type", "auto"),
                kwargs.get("operation", "extract")
            ),
            "calculator": lambda: asyncio.coroutine(lambda: self.calculator.calculate(
                kwargs.get("expression", "")
            ))(),
            "weather": lambda: self.weather.get_weather(
                kwargs.get("location", "")
            ),
            "telegram_profile": lambda: self.telegram_profile.analyze_profile(
                kwargs.get("username", ""),
                kwargs.get("include_ai_analysis", True)
            )
        }
        
        if tool_name not in tool_map:
            return ToolResult(
                tool=ToolType.WEB_SEARCH,  # Default
                status=ToolStatus.ERROR,
                error=f"Unknown tool: {tool_name}"
            )
        
        return await tool_map[tool_name]()
    
    def detect_tool_need(self, message: str) -> Optional[Tuple[str, Dict[str, Any]]]:
        """
        Analyze a message to detect if a tool should be used.
        Returns (tool_name, parameters) or None.
        """
        message_lower = message.lower()
        
        # Web search triggers
        search_triggers = [
            "search for", "look up", "find out", "what is the latest",
            "current price", "news about", "who is", "what happened",
            "google", "search"
        ]
        if any(trigger in message_lower for trigger in search_triggers):
            # Extract query
            query = message
            for trigger in search_triggers:
                query = query.lower().replace(trigger, "").strip()
            return ("web_search", {"query": query or message})
        
        # Weather triggers
        weather_triggers = ["weather in", "weather at", "weather for", "temperature in"]
        for trigger in weather_triggers:
            if trigger in message_lower:
                location = message_lower.split(trigger)[-1].strip()
                return ("weather", {"location": location})
        
        # Calculator triggers
        calc_patterns = [
            r'calculate\s+(.+)',
            r'what is\s+([\d\+\-\*\/\(\)\.\^\s]+)',
            r'compute\s+(.+)',
            r'^([\d\+\-\*\/\(\)\.\^\s]+)$'
        ]
        for pattern in calc_patterns:
            match = re.search(pattern, message_lower)
            if match:
                expr = match.group(1).strip()
                if any(c.isdigit() for c in expr):
                    return ("calculator", {"expression": expr})
        
        # Code execution triggers
        code_triggers = ["run this code", "execute", "```python", "```py"]
        if any(trigger in message_lower for trigger in code_triggers):
            # Extract code block
            code_match = re.search(r'```(?:python|py)?\n?(.*?)```', message, re.DOTALL | re.IGNORECASE)
            if code_match:
                return ("code_execution", {"code": code_match.group(1)})
        
        # Telegram profile analysis triggers
        profile_triggers = [
            "analyze profile", "check profile", "who is @", "tell me about @",
            "look up @", "profile of @", "info on @", "analyze @", "stalk @",
            "investigate @", "find @", "lookup @", "profile @"
        ]
        if any(trigger in message_lower for trigger in profile_triggers):
            # Extract username
            username_match = re.search(r'@(\w+)', message)
            if username_match:
                return ("telegram_profile", {"username": username_match.group(1)})
        
        # Also detect direct username mentions with context
        if re.search(r'(?:analyze|check|who is|tell me about|look up|info)\s+@?(\w{5,})', message_lower):
            username_match = re.search(r'@(\w+)', message)
            if username_match:
                return ("telegram_profile", {"username": username_match.group(1)})
        
        return None
    
    async def close(self):
        """Close all tool sessions"""
        await self.web_search.close()
        await self.image_analysis.close()
        await self.document_processing.close()
        await self.weather.close()
        await self.telegram_profile.close()


# Global tools engine instance
_tools_engine: Optional[ToolsEngine] = None


def get_tools_engine() -> ToolsEngine:
    """Get or create the global tools engine"""
    global _tools_engine
    if _tools_engine is None:
        _tools_engine = ToolsEngine()
    return _tools_engine


async def close_tools_engine():
    """Close the global tools engine"""
    global _tools_engine
    if _tools_engine:
        await _tools_engine.close()
        _tools_engine = None
