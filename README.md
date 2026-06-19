# Multi-Agent Lead Qualification Chatbot with LangGraph

This application is an **AI-powered Multi-Agent Lead Qualification Chatbot** designed for websites to interact with visitors, answer queries using trained RAG context, capture lead details, and generate requirements summary blueprints delivered to email.

Rebuilt from custom stage orchestrators into a **pure LangGraph StateGraph** architecture.

---

## Key Features & Agents

1. **4 Autonomous Agents**:
   - **Intent Classifier Agent**: Evaluates user messages to detect off-topic chat, budget requests, and contact inquiries, routing via graph conditional edges.
   - **Conversation Agent**: Interacts with users, queries **Pinecone** namespaces for RAG context, and extracts lead requirements into structured data models.
   - **Summarization Agent**: Auto-generates professional lead requirement briefs on session completion.
   - **Email Agent**: Dispatches admin alerts and visitor thank-you responses via SMTP.
2. **Strict Guardrails**:
   - **No Generic Data**: Answers strictly from trained RAG context. Politely redirects off-topic conversations.
   - **Budget Shield**: Intercepts pricing queries and redirects to human representative contact flow.
   - **Contact Nudge**: Proactively asks for missing details (Name/Email/Company) right before the message limit is reached.
3. **MongoDB Session Store**: Persists chat transcripts and lead records in MongoDB, while active threads route through LangGraph checkpointers.
4. **Premium Frontend Widget**: Includes an embeddable glassmorphic chat widget complete with typing animations, FAB toggle button, reset triggers, and session cache.

---

## Project Structure

```
chatbot-with-LangGraph/
├── backend/
│   ├── app/
│   │   ├── main.py                        # FastAPI startup, lifecycles, and mounts
│   │   ├── config.py                      # Pydantic Settings environment mapper
│   │   ├── database.py                    # Motor MongoDB async connections and indexes
│   │   ├── graph/                         # StateGraph builders, nodes, and routing edges
│   │   ├── middleware/                    # JWT Bearer route dependencies
│   │   ├── models/                        # State Dicts, API schemas, and MongoDB models
│   │   ├── routes/                        # Chatbot API, authentication, and admin routes
│   │   ├── services/                      # OpenAI/Ollama, Pinecone, Email, and Ingestors
│   │   └── utils/                         # Namespace formatting and Super Admin seeding
│   ├── documents/                         # PDF ingestion directory
│   └── requirements.txt                   # Backend packages
├── frontend/                              # Static Widget files
│   ├── index.html                         # Widget Integration Demo Landing Page
│   ├── css/style.css                      # Premium Glassmorphic Vanilla CSS
│   └── js/chat.js                         # ChatWidget state controller
├── IMPLEMENTATION_PLAN.md                 # Detailed blueprint
├── .gitignore                             # Python, Env, and IDE ignore list
└── README.md                              # Application Guide
```

---

## Installation & Setup

### 1. Prerequisites
Ensure you have the following installed locally:
- Python 3.10+
- MongoDB instance (running locally or remote)
- Pinecone Index
- Ollama (running locally with models `llama3.1` and `nomic-embed-text`) OR an OpenAI API Key.

### 2. Configure Environment Variables
Copy the `.env.example` file to `.env` inside `backend/` directory:
```bash
cp backend/.env.example backend/.env
```
Fill in the values in `backend/.env` (MongoDB URI, Pinecone API key, LLM Provider, SMTP email settings, default admin credentials, etc.).

### 3. Install Dependencies
Navigate to `backend` and install dependencies:
```bash
cd backend
pip install -r requirements.txt
```

### 4. Seed Admin & Start Server
Run the FastAPI application in your terminal using the Python module execution syntax (recommended on Windows where Uvicorn might not be on system PATH):
```bash
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
This will automatically connect to MongoDB, seed the Super Admin credentials configured in your `.env` file, and start listening on port 8000.

---

## Admin & Documentation URLs

FastAPI automatically generates interactive API documentation and test clients for all endpoints:

* **Interactive Admin UI (Swagger Docs)**: [http://localhost:8000/docs](http://localhost:8000/docs)  
  *(Click the **Authorize** button in the top-right corner, enter your configured Admin credentials to authenticate, and run file/YouTube ingestions directly from your browser!)*
* **ReDoc Reference Docs**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
* **Authentication Endpoint**: `http://localhost:8000/api/auth/login` (POST)
* **Document Ingestion Endpoint**: `http://localhost:8000/api/admin/ingest` (POST)
* **YouTube Extraction Endpoint**: `http://localhost:8000/api/admin/extract-youtube` (POST)

---


## Ingesting Training Documents

You can populate your vector store namespaces with custom training documents (PDFs) or YouTube transcripts:

### Ingesting Folder PDFs
1. Place PDF files under the `backend/documents/` folder.
2. Login to retrieve your Admin JWT:
   ```bash
   curl -X POST http://localhost:8000/api/auth/login \
     -H "Content-Type: application/json" \
     -d '{"email":"admin@example.com","password":"admin123"}'
   ```
3. Trigger folder ingestion under a namespace:
   ```bash
   curl -X POST http://localhost:8000/api/admin/ingest \
     -H "Authorization: Bearer <your-jwt-token>" \
     -H "Content-Type: application/json" \
     -d '{"namespace":"colorwhistle"}'
   ```

### Ingesting YouTube Transcripts
Provide a video link and namespace, and the backend will extract transcripts, generate a PDF reference doc, embed the segments, and upsert them to Pinecone:
```bash
curl -X POST http://localhost:8000/api/admin/extract-youtube \
  -H "Authorization: Bearer <your-jwt-token>" \
  -H "Content-Type: application/json" \
  -d '{"video_url":"https://www.youtube.com/watch?v=VIDEO_ID", "namespace":"colorwhistle"}'
```

---

## Running the Widget Demo

With the backend running on port 8000:
1. Open your browser and navigate to `http://localhost:8000/widget/index.html`.
2. Click the floating chat bubble in the bottom right corner to toggle the premium consultant widget.
3. Chat with the agent, test guardrails (weather queries, budget estimations), and complete lead discovery.

---

## Embedding the Chatbot Widget in Other Websites

You can embed this glassmorphic lead qualification chatbot widget into any external website (HTML pages, WordPress sites, Webflow, Shopify, etc.) by copying and pasting a single `<script>` tag before the closing `</body>` tag. The script automatically loads the necessary styling sheets and mounts the chat floating container dynamically:

### Single Script Embed Snippet

```html
<script 
  src="http://YOUR_BACKEND_HOST:8000/widget/js/chat.js"
  data-api-url="http://YOUR_BACKEND_HOST:8000"
  data-namespace="colorwhistle"
  data-company-name="ColorWhistle"
  data-logo-url="https://colorwhistle.com/logo.svg"
  data-position="bottom-right"
></script>
```

### Configurable Script Attributes:
*   `data-api-url`: The root URL of your running backend FastAPI server (e.g., `http://localhost:8000` or `https://your-chatbot-api.com`). This is used to dynamically fetch assets and send API payloads.
*   `data-namespace`: The specific Pinecone vector store namespace (e.g. `colorwhistle`). Leads and RAG details are partition-isolated under this value.
*   `data-company-name` (Optional): The company name displayed in the chatbot header (e.g., `ColorWhistle Consultant`).
*   `data-logo-url` (Optional): The absolute URL of your logo to render as the chatbot avatar (replaces the default `🤖`).
*   `data-position` (Optional): Set to `"bottom-right"` (default) or `"bottom-left"` to control the float position.


