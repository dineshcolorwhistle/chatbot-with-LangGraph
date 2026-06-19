# LangGraph AI Agentic Chatbot — Implementation Plan

## Architecture Overview

- **4 Agents**: Intent Classifier, Conversation, Summarization, Email
- **9 Graph Nodes**: welcome, intent_classifier, off_topic, budget_response, contact_response, rag_conversation, limit_warning, final_input, completed
- **3 Conditional Edges**: route_by_stage, classify_intent, check_message_limit
- **Tech Stack**: FastAPI + LangGraph + MongoDB (motor) + Pinecone + Ollama/OpenAI + SMTP
- **Frontend**: Embeddable HTML/CSS/JS chat widget

---

## Graph Topology

```
START → route_by_stage (conditional entry)
    │
    ├─ stage=welcome → welcome_node → END
    │
    ├─ stage=conversation → intent_classifier_node → classify_intent (conditional)
    │       ├─ off_topic → off_topic_node → END
    │       ├─ budget → budget_response_node → END
    │       ├─ contact → contact_response_node → END
    │       └─ valid → rag_conversation_node → check_message_limit (conditional)
    │                       ├─ count < MAX → END
    │                       └─ count >= MAX → limit_warning_node → END
    │
    ├─ stage=final_input → final_input_node → completed_node → END
    │
    └─ stage=completed → completed_node → END
```

---

## Step-by-Step Implementation

### STEP 1: Project Foundation ✅ COMPLETED
**Files to create:**
- `backend/requirements.txt`
- `backend/.env.example`
- `backend/app/__init__.py`
- `backend/app/config.py` (Pydantic Settings from .env)
- `backend/app/database.py` (MongoDB async connection with motor)
- All `__init__.py` files for packages (models, graph, nodes, edges, services, routes, middleware, utils)
- `backend/documents/` folder (for PDF ingestion)

**What this step achieves:** Project structure ready, config loading, MongoDB connection.

---

### STEP 2: Data Models ✅ COMPLETED
**Files to create:**
- `backend/app/models/state.py` — AgentState TypedDict + CollectedData Pydantic models (PersonalInfo, TechDiscovery, ScopePricing)
- `backend/app/models/schemas.py` — API request/response models (ChatRequest, ChatResponse, LoginRequest, etc.)
- `backend/app/models/db_models.py` — MongoDB document schemas (AdminDocument, ChatSessionDocument, LeadDocument)

**What this step achieves:** All data structures defined.

---

### STEP 3: Utility & Auth Services ✅ COMPLETED
**Files to create:**
- `backend/app/utils/helpers.py` — format_company_name, serialize_data, merge_collected_data
- `backend/app/utils/seed.py` — Admin seeding on startup
- `backend/app/middleware/auth.py` — JWT creation/verification, password hashing

**What this step achieves:** Admin auth system, helper functions.

---

### STEP 4: LLM & Embedding Services ✅ COMPLETED
**Files to create:**
- `backend/app/services/llm_service.py` — Dual LLM abstraction (Ollama + OpenAI), call_llm, call_llm_simple
- `backend/app/services/embedding_service.py` — generate_embedding (OpenAI / Ollama)

**What this step achieves:** LLM calls working for both providers.

---

### STEP 5: Pinecone & RAG Service ✅ COMPLETED
**Files to create:**
- `backend/app/services/pinecone_service.py` — init_pinecone, query_pinecone, upsert_vectors

**What this step achieves:** Vector search working against Pinecone namespaces.

---

### STEP 6: LangGraph Nodes & Edges ✅ COMPLETED
**Files to create:**
- `backend/app/graph/edges/routing.py` — route_by_stage, classify_intent, check_message_limit
- `backend/app/graph/nodes/welcome.py` — welcome_node
- `backend/app/graph/nodes/intent_classifier.py` — intent_classifier_node (LLM-based classification)
- `backend/app/graph/nodes/off_topic.py` — off_topic_node (template response)
- `backend/app/graph/nodes/budget_response.py` — budget_response_node (template response)
- `backend/app/graph/nodes/contact_response.py` — contact_response_node (template response)
- `backend/app/graph/nodes/rag_conversation.py` — rag_conversation_node (RAG + LLM + data extraction)
- `backend/app/graph/nodes/limit_warning.py` — limit_warning_node
- `backend/app/graph/nodes/final_input.py` — final_input_node
- `backend/app/graph/nodes/completed.py` — completed_node (summarization + email trigger)
- `backend/app/graph/builder.py` — StateGraph compilation with all nodes, edges, checkpointer

**What this step achieves:** Full LangGraph graph compiled and ready.

---

### STEP 7: Email & Summarization Services ✅ COMPLETED
**Files to create:**
- `backend/app/services/email_service.py` — SMTP async email (admin notification + visitor thank-you)
- `backend/app/services/summarization.py` — LLM-based lead summary generation

**What this step achieves:** Background agents (summarization + email) working.

---

### STEP 8: API Routes & Main App ✅ COMPLETED
**Files to create:**
- `backend/app/routes/auth.py` — POST /api/auth/login
- `backend/app/routes/chat.py` — POST /api/chat, /api/reset, /api/exit
- `backend/app/routes/admin.py` — POST /api/admin/ingest, /api/admin/extract-youtube
- `backend/app/main.py` — FastAPI app with CORS, startup/shutdown, route registration, static files

**What this step achieves:** Full backend API running.

---

### STEP 9: Document Ingestion & YouTube ✅ COMPLETED
**Files to create:**
- `backend/app/services/ingestion.py` — PDF chunking (PyMuPDF) + Pinecone upsert
- `backend/app/services/youtube_extractor.py` — YouTube transcript extraction + PDF conversion (fpdf2)

**What this step achieves:** Admin can ingest documents and YouTube transcripts into Pinecone.

---

### STEP 10: Frontend Chat Widget ✅ COMPLETED
**Files to create:**
- `frontend/index.html` — Demo page with chat widget
- `frontend/css/style.css` — Premium glassmorphism dark-mode styling
- `frontend/js/chat.js` — ChatWidget class with REST API calls, typing indicator, session management

**What this step achieves:** Fully functional embeddable chat widget.

---

## Environment Variables (.env)

```env
# MongoDB
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB_NAME=chatbot_langgraph

# Pinecone
PINECONE_API_KEY=
PINECONE_INDEX_NAME=chatbot-index

# LLM Provider: "openai" or "ollama"
LLM_PROVIDER=ollama
LLM_MODEL=llama3.1
OLLAMA_BASE_URL=http://localhost:11434
OPENAI_API_KEY=

# Embeddings
EMBEDDING_MODEL=nomic-embed-text
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# SMTP Email
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM_EMAIL=

# Admin
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=admin123

# JWT
JWT_SECRET_KEY=your-secret-key-change-this
JWT_ALGORITHM=HS256
JWT_EXPIRY_HOURS=24

# Chatbot
MAX_USER_MESSAGES=5
```

---

## MongoDB Collections

| Collection | Purpose |
|-----------|---------|
| `admins` | Admin accounts (email, hashed_password, created_at) |
| `chat_sessions` | Full chat history per session (messages, collected_data, stage, timestamps) |
| `leads` | Extracted lead data + summary (personal_info, tech, scope, summary) |

---

## API Endpoints

| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| `/api/auth/login` | POST | No | Admin login → JWT |
| `/api/chat` | POST | No | Main chat (LangGraph invocation) |
| `/api/reset` | POST | No | Reset session |
| `/api/exit` | POST | No | Force complete session |
| `/api/admin/ingest` | POST | JWT | PDF ingestion to Pinecone |
| `/api/admin/extract-youtube` | POST | JWT | YouTube transcript extraction |
