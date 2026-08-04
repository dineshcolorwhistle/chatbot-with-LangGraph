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
            api_key = settings.OPENAI_API_KEY or settings.CLOUD_API_KEY
            base_url = settings.CLOUD_BASE_URL
            if not api_key:
                raise ValueError("OPENAI_API_KEY or CLOUD_API_KEY is not configured in settings/environment.")
            cls._openai_client = AsyncOpenAI(api_key=api_key, base_url=base_url)
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

        if provider in ["openai", "cloud"]:
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

            model_name = settings.CLOUD_MODEL or settings.LLM_MODEL
            if model_name == "qwen2.5:0.5b" or not model_name:
                model_name = "gpt-4o-mini"

            response = await client.chat.completions.create(
                model=model_name,
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

    @classmethod
    async def classify_purchase_intent(cls, messages: List[Dict[str, str]]) -> bool:
        """
        Analyzes the chat logs to determine if the user has purchase intent.
        Purchase intent: interest in creating/discussing project requirements, websites, quotations.
        """
        chat_log = []
        for msg in messages:
            role = "Visitor" if msg["role"] == "user" else "Consultant"
            chat_log.append(f"{role}: {msg['content']}")
        chat_log_str = "\n".join(chat_log)

        system_prompt = (
            "You are a sales intent classification bot.\n"
            "Analyze the following chat conversation history between a visitor and a consultant.\n"
            "Determine if the visitor shows any purchase intent.\n"
            "\"Purchase intent\" is defined as any interest in:\n"
            "- Developing or building a project (website, app, SaaS, software, design, etc.)\n"
            "- Requesting a quotation, pricing estimation, or budget discussion for services\n"
            "- Discussing project requirements, features, or timeline\n"
            "- Arranging a follow-up meeting, call, or consultation to discuss collaboration or services\n\n"
            "Respond with a JSON object containing a single key \"purchase_intent\" with a boolean value (true or false). "
            "Do not include any conversational greeting, notes, or markdown. Output valid JSON only."
        )

        try:
            raw_output = await cls.call_llm_simple(
                system_prompt=system_prompt,
                user_message=f"--- CONVERSATION LOGS ---\n{chat_log_str}",
                temperature=0.0
            )
            parsed = cls.clean_json_response(raw_output)
            val = parsed.get("purchase_intent", False)
            if isinstance(val, str):
                return val.lower() == "true"
            return bool(val)
        except Exception as e:
            logger.error(f"❌ Failed to classify purchase intent: {e}")
            # Default to True on failure to avoid losing a potential lead
            return True
