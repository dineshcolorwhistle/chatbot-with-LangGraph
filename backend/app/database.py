"""
MongoDB async database connection and collection management.
Uses Motor (async MongoDB driver) for non-blocking database operations.
"""

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class Database:
    """
    Manages the MongoDB connection lifecycle and provides access to collections.
    
    Collections:
        - admins: Admin user accounts (email, hashed_password, created_at)
        - chat_sessions: Full chat history per session (messages, collected_data, stage)
        - leads: Extracted lead data with summaries (personal_info, tech, scope)
    """

    client: AsyncIOMotorClient = None
    db: AsyncIOMotorDatabase = None

    @classmethod
    async def connect(cls):
        """Establish connection to MongoDB on application startup."""
        try:
            cls.client = AsyncIOMotorClient(settings.MONGODB_URI)
            cls.db = cls.client[settings.MONGODB_DB_NAME]

            # Verify connection by pinging the server
            await cls.client.admin.command("ping")
            logger.info(f"✅ Connected to MongoDB: {settings.MONGODB_DB_NAME}")

            # Create indexes for efficient queries
            await cls._create_indexes()

        except Exception as e:
            logger.error(f"❌ Failed to connect to MongoDB: {e}")
            raise

    @classmethod
    async def _create_indexes(cls):
        """Create database indexes for optimized query performance."""
        # Unique index on admin email
        await cls.db.admins.create_index("email", unique=True)

        # Index on session_id for fast chat session lookups
        await cls.db.chat_sessions.create_index("session_id", unique=True)

        # Index on session_id for leads
        await cls.db.leads.create_index("session_id")

        # Index on namespace for filtering by tenant
        await cls.db.chat_sessions.create_index("namespace")
        await cls.db.leads.create_index("namespace")

        logger.info("✅ Database indexes created")

    @classmethod
    async def disconnect(cls):
        """Close MongoDB connection on application shutdown."""
        if cls.client:
            cls.client.close()
            logger.info("🔌 MongoDB connection closed")

    @classmethod
    def get_db(cls) -> AsyncIOMotorDatabase:
        """Get the database instance. Raises if not connected."""
        if cls.db is None:
            raise RuntimeError("Database not connected. Call Database.connect() first.")
        return cls.db

    # ── Collection Accessors ─────────────────────────────────

    @classmethod
    def get_admins_collection(cls):
        """Get the admins collection."""
        return cls.get_db().admins

    @classmethod
    def get_sessions_collection(cls):
        """Get the chat_sessions collection."""
        return cls.get_db().chat_sessions

    @classmethod
    def get_leads_collection(cls):
        """Get the leads collection."""
        return cls.get_db().leads
