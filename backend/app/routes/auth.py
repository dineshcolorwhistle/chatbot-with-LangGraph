import logging
from datetime import timedelta
from fastapi import APIRouter, HTTPException, status
from app.models.schemas import LoginRequest, LoginResponse
from app.database import Database
from app.middleware.auth import verify_password, create_jwt_token
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@router.post("/login", response_model=LoginResponse)
async def login(credentials: LoginRequest):
    """
    Authenticate admin credentials and issue a JWT token.
    """
    try:
        admins_col = Database.get_admins_collection()
        admin = await admins_col.find_one({"email": credentials.email})
        
        if not admin or not verify_password(credentials.password, admin["hashed_password"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Generate JWT token
        token_expiry = timedelta(hours=settings.JWT_EXPIRY_HOURS)
        token = create_jwt_token(data={"sub": admin["email"]}, expires_delta=token_expiry)
        
        logger.info(f"👨‍💼 Admin logged in: {credentials.email}")
        return LoginResponse(access_token=token)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Login endpoint failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )
