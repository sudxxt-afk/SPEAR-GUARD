from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from pydantic import BaseModel
from enum import Enum
from jose import jwt, JWTError
from datetime import datetime, timedelta
import os
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import User, get_db

# Security configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY") or os.getenv("SECRET_KEY") or "dev-secret-key-change-in-production"
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("REFRESH_TOKEN_EXPIRE_MINUTES", os.getenv("JWT_REFRESH_TOKEN_EXPIRE_MINUTES", str(60 * 24 * 30)))
)  # 30 days

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserRole(str, Enum):
    """User roles in the system"""
    USER = "user"  # Regular user - can only suggest additions
    SECURITY_OFFICER = "security_officer"  # Can manage registry
    ADMIN = "admin"  # Full system access


class TokenData(BaseModel):
    """Data stored in JWT token"""
    user_id: int
    email: str
    role: UserRole
    type: str = "access"
    exp: Optional[datetime] = None


class CurrentUser(BaseModel):
    """Current authenticated user"""
    id: int
    email: str
    full_name: str
    role: UserRole
    organization_id: Optional[int] = None  # For data isolation
    organization: Optional[str] = None  # Legacy field (org name as string)
    department: Optional[str] = None
    is_active: bool = True

    def is_security_officer(self) -> bool:
        """Check if user is security officer or admin"""
        return self.role in [UserRole.SECURITY_OFFICER, UserRole.ADMIN]

    def is_admin(self) -> bool:
        """Check if user is admin"""
        return self.role == UserRole.ADMIN

    def can_manage_registry(self) -> bool:
        """Check if user can manage registry"""
        return self.role in [UserRole.SECURITY_OFFICER, UserRole.ADMIN]

    def can_approve_registry(self) -> bool:
        """Check if user can approve registry entries"""
        return self.role in [UserRole.SECURITY_OFFICER, UserRole.ADMIN]


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
    token_type: str = "access",
) -> str:
    """
    Create JWT token (access/refresh/reset)
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "type": token_type})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str, expected_type: str = "access") -> TokenData:
    """
    Decode and validate JWT token with expected type
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("user_id")
        email: str = payload.get("email")
        role: str = payload.get("role")
        token_type: str = payload.get("type", "access")

        if user_id is None or email is None or token_type != expected_type:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return TokenData(user_id=user_id, email=email, role=role, type=token_type)

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


API_SYSTEM_TOKEN = os.getenv("API_SYSTEM_TOKEN", "change-this-to-secure-random-token")

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> CurrentUser:
    """
    Get current authenticated user from JWT token or system token
    """
    # Allow internal services to use API_SYSTEM_TOKEN
    if token == API_SYSTEM_TOKEN:
        user = await get_user_by_email(db, "admin@spear-guard.gov.ru")
        if user:
            return CurrentUser(
                id=user.id,
                email=user.email,
                full_name=user.full_name,
                role=UserRole(user.role),
                organization_id=user.organization_id,
                department=user.department,
                is_active=user.is_active
            )
        # Fallback if admin not found
        return CurrentUser(
            id=1,
            email="system@spear-guard.gov.ru",
            full_name="System Listener",
            role=UserRole.ADMIN,
            is_active=True
        )

    token_data = decode_token(token, expected_type="access")

    user = await get_user_by_email(db, token_data.email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )

    return CurrentUser(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        organization_id=user.organization_id,
        department=user.department,
        is_active=user.is_active
    )


async def get_current_active_user(
    current_user: CurrentUser = Depends(get_current_user)
) -> CurrentUser:
    """
    Verify that current user is active
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user


async def require_security_officer(
    current_user: CurrentUser = Depends(get_current_active_user)
) -> CurrentUser:
    """
    Require security officer or admin role
    """
    if not current_user.is_security_officer():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Security officer or admin access required"
        )
    return current_user


async def require_admin(
    current_user: CurrentUser = Depends(get_current_active_user)
) -> CurrentUser:
    """
    Require admin role
    """
    if not current_user.is_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


# Optional authentication (for public endpoints)
async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
) -> Optional[CurrentUser]:
    """
    Get current user if authenticated, None otherwise
    """
    if not credentials:
        return None

    try:
        return await get_current_user(credentials.credentials)  # type: ignore[arg-type]
    except HTTPException:
        return None


async def get_current_user_from_token(token: str) -> CurrentUser:
    """
    Get current user from JWT token (for WebSocket authentication)
    
    This function doesn't use FastAPI Depends, so it can be called directly
    with a token string (e.g., from WebSocket query parameters)
    
    Args:
        token: JWT token string
        
    Returns:
        CurrentUser object
        
    Raises:
        HTTPException: If authentication fails
    """
    from database import AsyncSessionLocal
    
    token_data = decode_token(token, expected_type="access")
    
    async with AsyncSessionLocal() as db:
        user = await get_user_by_email(db, token_data.email)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive user"
            )

        return CurrentUser(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            organization_id=user.organization_id,
            department=user.department,
            is_active=user.is_active
        )
