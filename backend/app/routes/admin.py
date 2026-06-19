import logging
import os
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from app.models.schemas import IngestRequest, IngestResponse, YouTubeExtractRequest
from app.middleware.auth import get_current_admin
from app.services.ingestion import IngestionService
from app.services.youtube_extractor import YouTubeExtractorService
from app.database import Database

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin", tags=["Admin Operations"])

@router.post("/ingest", response_model=IngestResponse)
async def ingest_documents_endpoint(
    request: IngestRequest,
    admin_email: str = Depends(get_current_admin)
):
    """
    Ingest PDF documents from a server directory, chunk them, embed,
    and upload them into Pinecone under a specific namespace.
    Protected by JWT Admin authentication.
    """
    namespace = request.namespace
    
    # Resolve default documents folder if none supplied
    folder_path = request.folder_path
    if not folder_path:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        folder_path = os.path.join(base_dir, "documents")
        
    if not os.path.exists(folder_path):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Documents directory '{folder_path}' does not exist on the server."
        )

    try:
        logger.info(f"📂 Admin '{admin_email}' triggered ingestion for namespace: '{namespace}'")
        summary = await IngestionService.ingest_documents(folder_path, namespace)
        return IngestResponse(
            status="success",
            message=f"Ingested files from '{folder_path}'. Details: {summary}"
        )
    except Exception as e:
        logger.error(f"❌ Document ingestion endpoint failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ingestion failed: {str(e)}"
        )

@router.post("/extract-youtube")
async def extract_youtube_endpoint(
    request: YouTubeExtractRequest,
    admin_email: str = Depends(get_current_admin)
):
    """
    Extract transcript from a YouTube video link, compile it to a PDF file,
    and automatically ingest it into Pinecone under the given namespace.
    Protected by JWT Admin authentication.
    """
    video_url = request.video_url
    namespace = request.namespace

    try:
        logger.info(f"🎥 Admin '{admin_email}' triggered YouTube transcript extraction for url: {video_url}")
        
        # 1. Extract transcript and convert to PDF inside the backend documents folder
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        docs_folder = os.path.join(base_dir, "documents")
        os.makedirs(docs_folder, exist_ok=True)
        
        pdf_path = await YouTubeExtractorService.extract_and_save_as_pdf(video_url, docs_folder)
        
        # 2. Ingest the generated PDF file directly into Pinecone namespace
        summary = await IngestionService.ingest_single_file(pdf_path, namespace)
        
        return {
            "status": "success",
            "message": f"YouTube video transcript saved as PDF ({os.path.basename(pdf_path)}) and uploaded into Pinecone namespace '{namespace}'. Details: {summary}"
        }
        
    except Exception as e:
        logger.error(f"❌ YouTube extraction endpoint failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"YouTube extraction/ingestion failed: {str(e)}"
        )

@router.get("/leads")
async def get_leads_endpoint(
    admin_email: str = Depends(get_current_admin)
):
    """
    Retrieve all qualified lead records from MongoDB, sorted by creation date.
    Protected by JWT Admin authentication.
    """
    try:
        leads_col = Database.get_leads_collection()
        cursor = leads_col.find({}).sort("created_at", -1)
        leads = await cursor.to_list(length=200)
        
        # Serialize MongoDB ObjectIds and datetime to string for JSON compatibility
        for lead in leads:
            if "_id" in lead:
                lead["_id"] = str(lead["_id"])
            if "created_at" in lead and isinstance(lead["created_at"], datetime):
                lead["created_at"] = lead["created_at"].isoformat()
        return leads
    except Exception as e:
        logger.error(f"❌ Failed to fetch leads: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch leads: {str(e)}"
        )
