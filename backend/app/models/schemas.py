from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Dict, Any, List

class ChatRequest(BaseModel):
    session_id: str = Field(..., description="Unique session/thread ID for the conversation")
    message: str = Field(..., description="User input message. Can be empty for welcome message initialization.")
    namespace: Optional[str] = Field(default="default", description="Client namespace for partition isolation")

class ChatResponse(BaseModel):
    reply: str = Field(..., description="Assistant response content")
    stage: str = Field(..., description="Current stage of the conversation")
    data_collected: Dict[str, Any] = Field(..., description="Serialized lead details collected so far")

class LoginRequest(BaseModel):
    email: EmailStr = Field(..., description="Admin email address")
    password: str = Field(..., description="Admin password")

class LoginResponse(BaseModel):
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token schema type")

class IngestRequest(BaseModel):
    namespace: str = Field(..., description="Pinecone namespace to upload vectors to")
    folder_path: Optional[str] = Field(default=None, description="Optional custom folder path on the server containing PDFs")

class IngestResponse(BaseModel):
    status: str = Field(..., description="Status of ingestion")
    message: str = Field(..., description="Details of the files processed")

class YouTubeExtractRequest(BaseModel):
    video_url: str = Field(..., description="Valid YouTube video URL to extract transcript from")
    namespace: str = Field(..., description="Pinecone namespace to upload vector under")
