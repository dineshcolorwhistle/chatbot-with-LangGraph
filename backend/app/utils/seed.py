import logging
from datetime import datetime
from app.config import settings
from app.database import Database
from app.middleware.auth import hash_password

logger = logging.getLogger(__name__)

async def seed_admin():
    """
    Check if the admin credentials exist in the database and seed them if they are missing.
    Reads admin credentials from settings (ADMIN_EMAIL, ADMIN_PASSWORD).
    """
    try:
        admins_col = Database.get_admins_collection()
        
        # Check if admin already exists
        admin = await admins_col.find_one({"email": settings.ADMIN_EMAIL})
        if admin:
            logger.info("👨‍💼 Admin user already exists in database. Skipping seed.")
            return

        # Seed new admin
        hashed_pwd = hash_password(settings.ADMIN_PASSWORD)
        admin_doc = {
            "email": settings.ADMIN_EMAIL,
            "hashed_password": hashed_pwd,
            "created_at": datetime.utcnow()
        }

        await admins_col.insert_one(admin_doc)
        logger.info(f"🚀 Successfully seeded super admin credential for: {settings.ADMIN_EMAIL}")

    except Exception as e:
        logger.error(f"❌ Failed to seed admin user: {e}")
        raise
