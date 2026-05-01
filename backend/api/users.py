from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from typing import List, Optional
from pydantic import BaseModel

from database import get_db, User
from auth.permissions import CurrentUser, require_admin, UserRole

router = APIRouter(prefix="/api/v1/users", tags=["Users"])

class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    organization_id: Optional[int]
    department: Optional[str]
    is_active: bool

    class Config:
        from_attributes = True

@router.get("/", response_model=List[UserResponse])
async def list_users(
    search: Optional[str] = Query(None, min_length=2),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    exclude_org_members: bool = Query(False, description="Exclude users who are already in an organization"),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_admin),
):
    query = select(User)
    
    if search:
        search_term = f"%{search}%"
        query = query.where(
            or_(
                User.email.ilike(search_term),
                User.full_name.ilike(search_term)
            )
        )
    
    if exclude_org_members:
        query = query.where(User.organization_id.is_(None))
        
    query = query.offset(offset).limit(limit)
    
    result = await db.execute(query)
    users = result.scalars().all()
    
    return users
