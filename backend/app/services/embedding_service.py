import logging
from typing import List, Optional
import httpx
from app.config import settings
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)

class EmbeddingService:
    """
    Service to generate vector embeddings using either OpenAI or Ollama.
    """

    @classmethod
    async def generate_embedding(cls, text: str) -> List[float]:
        """
        Generate embedding vector for the provided text.
        """
        provider = settings.LLM_PROVIDER.lower()

        if provider == "openai":
            return await cls._generate_openai_embedding(text)
        elif provider == "ollama":
            return await cls._generate_ollama_embedding(text)
        else:
            raise ValueError(f"Unsupported LLM/Embedding provider: {settings.LLM_PROVIDER}")

    @classmethod
    async def _generate_openai_embedding(cls, text: str) -> List[float]:
        """Generate vector embedding via OpenAI Embedding API."""
        try:
            client = LLMService.get_openai_client()
            response = await client.embeddings.create(
                model=settings.OPENAI_EMBEDDING_MODEL,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"❌ OpenAI embedding generation failed: {e}")
            raise

    @classmethod
    async def _generate_ollama_embedding(cls, text: str) -> List[float]:
        """Generate vector embedding via Ollama /api/embeddings API."""
        url = f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/embeddings"
        payload = {
            "model": settings.EMBEDDING_MODEL,
            "prompt": text
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                result = response.json()
                embedding = result.get("embedding")
                if not embedding:
                    # Some versions of Ollama return it inside "embeddings" or a list of vectors
                    embedding = result.get("embeddings", [[]])[0]
                
                if not embedding:
                    raise ValueError(f"No embedding found in Ollama response: {result}")
                return embedding
        except Exception as e:
            logger.error(f"❌ Ollama embedding generation failed: {e}")
            raise
