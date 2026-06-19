from typing import Annotated, Dict, Any, List
from typing_extensions import TypedDict
from pydantic import BaseModel, Field

# Match existing collected data schema
class PersonalInfo(BaseModel):
    name: str = ""
    email: str = ""
    company: str = ""
    location: str = ""

class TechDiscovery(BaseModel):
    project_type: str = ""
    tech_stack: str = ""
    features: str = ""
    integrations: str = ""

class ScopePricing(BaseModel):
    budget: str = ""
    timeline: str = ""
    mvp_or_production: str = ""
    priority_features: str = ""

class CollectedData(BaseModel):
    personal_info: PersonalInfo = Field(default_factory=PersonalInfo)
    tech_discovery: TechDiscovery = Field(default_factory=TechDiscovery)
    scope_pricing: ScopePricing = Field(default_factory=ScopePricing)

class AgentState(TypedDict):
    # Core state
    session_id: str
    namespace: str
    company_name: str
    stage: str  # "welcome" | "conversation" | "limit_warning" | "final_input" | "completed"
    intent: str  # "valid" | "off_topic" | "budget" | "contact"
    
    # Message logs
    messages: List[Dict[str, str]]  # list of {"role": "...", "content": "..."}
    user_message_count: int
    
    # Lead details
    collected_data: CollectedData
    
    # Output properties
    reply: str
    data_collected: Dict[str, Any]
