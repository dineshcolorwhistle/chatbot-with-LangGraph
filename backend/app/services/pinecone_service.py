import logging
from typing import List, Dict, Any, Optional
from pinecone import Pinecone
from app.config import settings
from app.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)

class PineconeService:
    """
    Manages vector database interactions with Pinecone.
    Provides RAG query context retrieval and bulk vector upserts.
    All operations are namespace-partitioned to support multi-tenancy.
    """
    
    _pc_client: Optional[Pinecone] = None
    _index: Optional[Any] = None

    @classmethod
    def get_index(cls) -> Any:
        """Lazy load Pinecone client and connect to the index."""
        if cls._index is None:
            if not settings.PINECONE_API_KEY:
                raise ValueError("PINECONE_API_KEY is not configured in settings.")
            
            cls._pc_client = Pinecone(api_key=settings.PINECONE_API_KEY)
            cls._index = cls._pc_client.Index(settings.PINECONE_INDEX_NAME)
            logger.info(f"🌲 Connected to Pinecone index: {settings.PINECONE_INDEX_NAME}")
        return cls._index

    @classmethod
    async def query_pinecone(cls, query_text: str, namespace: str, top_k: int = 5) -> str:
        """
        Embed user query, query Pinecone index inside namespace partition,
        and assemble a consolidated context string.
        """
        try:
            # 1. Generate query embedding
            embedding = await EmbeddingService.generate_embedding(query_text)
            
            # 2. Query index
            index = cls.get_index()
            # Pinecone client operations are synchronous. Run in executor or call directly.
            # Usually direct calls are fast enough, but we should wrap in try/except.
            response = index.query(
                vector=embedding,
                top_k=top_k,
                include_metadata=True,
                namespace=namespace
            )
            
            # 3. Consolidate matching text from metadata 'text' field
            matches = response.get("matches", [])
            if not matches:
                logger.info(f"⚠️ No RAG context matches found in namespace: '{namespace}' for query.")
                return ""
            
            contexts = []
            for match in matches:
                metadata = match.get("metadata", {})
                # Look for typical keys containing raw text chunk
                text_chunk = metadata.get("text") or metadata.get("content") or ""
                if text_chunk:
                    contexts.append(text_chunk.strip())
            
            separator = "\n\n---\n\n"
            return separator.join(contexts)

        except Exception as e:
            logger.error(f"❌ Pinecone search failed: {e}")
            # Non-blocking fallback: return empty string so the LLM continues without context rather than crashing
            return ""

    @classmethod
    async def upsert_vectors(cls, vectors: List[Dict[str, Any]], namespace: str) -> Dict[str, Any]:
        """
        Upsert a list of vectors to the Pinecone index.
        Each vector dict should look like:
        {
            "id": "doc_chunk_1",
            "values": [0.1, 0.2, ...],
            "metadata": {"text": "chunk text contents...", "source": "filename.pdf"}
        }
        """
        try:
            index = cls.get_index()
            # Pinecone upsert format is a list of tuples or dictionaries
            upsert_response = index.upsert(
                vectors=vectors,
                namespace=namespace
            )
            logger.info(f"🌲 Successfully upserted {len(vectors)} vectors to namespace: '{namespace}'")
            return upsert_response
        except Exception as e:
            logger.error(f"❌ Pinecone vector upsert failed: {e}")
            raise
