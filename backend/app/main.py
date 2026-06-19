import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

from app.config import settings
from app.database import Database
from app.utils.seed import seed_admin
from app.routes import auth, chat, admin

# Setup logger configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Initialize FastAPI App
app = FastAPI(
    title="LangGraph AI Chatbot Backend",
    description="Multi-Agent Lead Qualification Chatbot API with RAG, Guardrails, and Session Persistence.",
    version="1.0.0"
)

# CORS configurations — allows frontend chat widget to connect from any client domain
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Frontend static files directory for easy widget serving and demos
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
frontend_dir = os.path.join(base_dir, "frontend")

# If the directory doesn't exist yet, we'll create it on startup to avoid FastAPI startup errors
os.makedirs(frontend_dir, exist_ok=True)
app.mount("/widget", StaticFiles(directory=frontend_dir, html=True), name="widget")


# ── Lifecycle Events ────────────────────────────────────────

@app.on_event("startup")
async def startup_event():
    """Run database connectivity checks and super admin credential seeding on startup."""
    logger.info("Starting up LangGraph Chatbot Backend application...")
    
    # 1. Connect to MongoDB
    await Database.connect()
    
    # 2. Seed Super Admin details
    await seed_admin()
    
    logger.info("🚀 Application startup complete. Ready for API traffic.")

@app.on_event("shutdown")
async def shutdown_event():
    """Disconnect database connections gracefully on shutdown."""
    logger.info("Shutting down applications...")
    await Database.disconnect()


# ── Route Registrations ────────────────────────────────────

app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(admin.router)

@app.get("/")
async def root():
    """Redirect root endpoint to frontend widget index.html."""
    return RedirectResponse(url="/widget/index.html")
