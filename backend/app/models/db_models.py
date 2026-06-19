from datetime import datetime
from pydantic import BaseModel, Field, EmailStr
from typing import List, Dict, Any, Optional

class AdminDocument(BaseModel):
    email: EmailStr
    hashed_password: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ChatSessionDocument(BaseModel):
    session_id: str
    namespace: str
    stage: str
    messages: List[Dict[str, str]]  # List of {"role": "user/assistant", "content": "..."}
    collected_data: Dict[str, Any]
    user_message_count: int
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class LeadDocument(BaseModel):
    session_id: str
    namespace: str
    personal_info: Dict[str, Any]
    tech_discovery: Dict[str, Any]
    scope_pricing: Dict[str, Any]
    summary: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
