import json
import re
import logging
from typing import List, Dict, Any, Optional
import httpx
from openai import AsyncOpenAI
from app.config import settings

logger = logging.getLogger(__name__)

class LLMService:
    """
    Unified LLM service supporting both OpenAI and Ollama.
    Handles message formatting, JSON extraction, and client initialization.
    """
    
    _openai_client: Optional[AsyncOpenAI] = None

    @classmethod
    def get_openai_client(cls) -> AsyncOpenAI:
        """Lazy load OpenAI Async client."""
        if cls._openai_client is None:
            if not settings.OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY is not configured in settings.")
            cls._openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        return cls._openai_client

    @classmethod
    async def call_llm(cls, system_prompt: str, messages: List[Dict[str, str]], temperature: float = 0.2) -> str:
        """
        Main entry point for unified chat completions.
        Formats payload, queries selected provider, and returns response string.
        """
        provider = settings.LLM_PROVIDER.lower()
        
        # Prepare messages array with system prompt prepended
        formatted_messages = [{"role": "system", "content": system_prompt}]
        formatted_messages.extend(messages)

        if provider == "openai":
            return await cls._call_openai(formatted_messages, temperature)
        elif provider == "ollama":
            return await cls._call_ollama(formatted_messages, temperature)
        else:
            raise ValueError(f"Unsupported LLM provider: {settings.LLM_PROVIDER}")

    @classmethod
    async def call_llm_simple(cls, system_prompt: str, user_message: str, temperature: float = 0.0) -> str:
        """
        Lightweight chat completion wrapper for single messages (e.g. intent classification).
        Avoids sending full conversation history to minimize latency/cost.
        """
        messages = [{"role": "user", "content": user_message}]
        return await cls.call_llm(system_prompt, messages, temperature)

    @classmethod
    async def _call_openai(cls, messages: List[Dict[str, str]], temperature: float) -> str:
        """Call OpenAI chat completion API."""
        try:
            client = cls.get_openai_client()
            
            # Check if JSON structure is expected by looking at prompt
            response_format = {"type": "text"}
            if any("json" in m["content"].lower() for m in messages):
                response_format = {"type": "json_object"}

            response = await client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=messages, # type: ignore
                temperature=temperature,
                response_format=response_format # type: ignore
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error(f"❌ OpenAI API call failed: {e}")
            raise

    @classmethod
    async def _call_ollama(cls, messages: List[Dict[str, str]], temperature: float) -> str:
        """Call local Ollama instance chat API using HTTPX."""
        url = f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/chat"
        
        # Check if JSON structure is expected by looking at prompt
        format_type = None
        if any("json" in m["content"].lower() for m in messages):
            format_type = "json"

        payload = {
            "model": settings.LLM_MODEL,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature
            }
        }
        if format_type:
            payload["format"] = format_type

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                result = response.json()
                return result.get("message", {}).get("content", "")
        except httpx.HTTPError as e:
            logger.error(f"❌ Ollama API call failed: {e}")
            raise

    @classmethod
    def clean_json_response(cls, text: str) -> Dict[str, Any]:
        """
        Utility to extract and parse JSON object from LLM raw text output.
        Handles formatting errors, markdown codeblocks, and trailing comma glitches.
        """
        text = text.strip()
        
        # Regex to find JSON blocks (between ```json and ``` or plain curly brackets)
        match = re.search(r"({.*})", text, re.DOTALL)
        if match:
            json_str = match.group(1)
        else:
            json_str = text

        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            # Fallback regex cleanups
            try:
                # Remove common trailing comma issues
                cleaned = re.sub(r",\s*([\]}])", r"\1", json_str)
                return json.loads(cleaned)
            except Exception as e:
                logger.error(f"❌ Failed to parse JSON from LLM response: {text}. Error: {e}")
                return {"response": text, "extracted_data": {}}
