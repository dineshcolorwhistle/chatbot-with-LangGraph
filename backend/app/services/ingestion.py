import os
import uuid
import fitz  # PyMuPDF
import logging
from typing import List, Dict, Any
from app.services.embedding_service import EmbeddingService
from app.services.pinecone_service import PineconeService

logger = logging.getLogger(__name__)

class IngestionService:
    """
    Handles extracting text from PDF files, chunking the content,
    generating vector embeddings, and uploading to Pinecone.
    """

    @classmethod
    def split_text_into_chunks(cls, text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> List[str]:
        """
        Split raw text into chunks of specified size with overlapping bounds.
        """
        if not text:
            return []
            
        chunks = []
        start = 0
        text_len = len(text)
        
        while start < text_len:
            end = start + chunk_size
            chunk = text[start:end]
            chunks.append(chunk)
            
            # Move index forward by chunk_size minus overlap
            start += chunk_size - chunk_overlap
            
            # Avoid infinite loop if size <= overlap
            if chunk_size - chunk_overlap <= 0:
                break
                
        return chunks

    @classmethod
    async def ingest_single_file(cls, file_path: str, namespace: str) -> str:
        """
        Extract text from a single PDF file, chunk, embed, and upload.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        logger.info(f"📂 Ingesting PDF file: '{file_path}' into namespace '{namespace}'")
        
        # 1. Read PDF file text using PyMuPDF (fitz)
        text_content = []
        try:
            doc = fitz.open(file_path)
            for page in doc:
                text_content.append(page.get_text())
            doc.close()
        except Exception as e:
            logger.error(f"❌ Failed to parse PDF file '{file_path}': {e}")
            raise ValueError(f"Could not read PDF structure: {e}")

        full_text = "\n".join(text_content).strip()
        if not full_text:
            logger.warning(f"⚠️ PDF file '{file_path}' contains no extractable text.")
            return "No text content found in file."

        # 2. Split text into chunks
        chunks = cls.split_text_into_chunks(full_text)
        logger.info(f"✂️ Split '{os.path.basename(file_path)}' into {len(chunks)} chunks.")

        # 3. Create vectors and embed
        vectors = []
        file_basename = os.path.basename(file_path)
        
        for idx, chunk in enumerate(chunks):
            chunk_cleaned = chunk.strip()
            if not chunk_cleaned:
                continue
                
            try:
                # Generate vector embedding for chunk
                vector_values = await EmbeddingService.generate_embedding(chunk_cleaned)
                
                # Setup vector struct
                vector_id = f"{file_basename}_chunk_{idx}_{uuid.uuid4().hex[:8]}"
                vectors.append({
                    "id": vector_id,
                    "values": vector_values,
                    "metadata": {
                        "text": chunk_cleaned,
                        "source": file_basename
                    }
                })
            except Exception as e:
                logger.error(f"❌ Failed to embed chunk {idx} of file '{file_basename}': {e}")
                # Continue embedding remaining chunks

        # 4. Upsert vectors in batches of 100 to avoid Pinecone body limits
        if vectors:
            batch_size = 100
            for i in range(0, len(vectors), batch_size):
                batch = vectors[i:i + batch_size]
                await PineconeService.upsert_vectors(batch, namespace)
            return f"Successfully processed {len(chunks)} chunks from {file_basename}."
        
        return "No chunks could be embedded."

    @classmethod
    async def ingest_documents(cls, folder_path: str, namespace: str) -> str:
        """
        Scan a folder for PDF files and ingest all of them.
        """
        logger.info(f"📂 Scanning folder '{folder_path}' for PDF ingestion...")
        pdf_files = [f for f in os.listdir(folder_path) if f.lower().endswith(".pdf")]
        
        if not pdf_files:
            return "No PDF files found in documents directory."

        results = []
        for pdf in pdf_files:
            file_path = os.path.join(folder_path, pdf)
            try:
                msg = await cls.ingest_single_file(file_path, namespace)
                results.append(f"{pdf}: {msg}")
            except Exception as e:
                results.append(f"{pdf}: Failed - {str(e)}")
                
        return " | ".join(results)
