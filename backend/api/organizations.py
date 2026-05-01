"""
Organization Management API
Allows admins to create, view, update, and delete organizations.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

from database import get_db, Organization, User
from auth.permissions import get_current_active_user, CurrentUser, require_admin

router = APIRouter(prefix="/api/v1/organizations", tags=["Organizations"])


# Pydantic models
class OrganizationCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    domain: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None


class OrganizationUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    domain: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    is_active: Optional[bool] = None


class OrganizationResponse(BaseModel):
    id: int
    name: str
    domain: Optional[str]
    description: Optional[str]
    is_active: bool
    user_count: int = 0
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class OrganizationListResponse(BaseModel):
    data: List[OrganizationResponse]
    total: int


def org_to_dict(org: Organization, user_count: int = 0) -> dict:
    return {
        "id": org.id,
        "name": org.name,
        "domain": org.domain,
        "description": org.description,
        "is_active": org.is_active if org.is_active is not None else True,
        "user_count": user_count,
        "created_at": org.created_at.isoformat() if org.created_at else None,
        "updated_at": org.updated_at.isoformat() if org.updated_at else None,
    }


@router.get("/", response_model=OrganizationListResponse)
async def list_organizations(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    include_inactive: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_admin),
):
    """
    List all organizations. Admin only.
    """
    query = select(Organization)
    count_query = select(func.count()).select_from(Organization)
    
    if not include_inactive:
        query = query.where(Organization.is_active == True)
        count_query = count_query.where(Organization.is_active == True)
    
    query = query.order_by(Organization.name).offset(offset).limit(limit)
    
    result = await db.execute(query)
    orgs = result.scalars().all()
    
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Get user counts for each org
    org_data = []
    for org in orgs:
        user_count_result = await db.execute(
            select(func.count()).select_from(User).where(User.organization_id == org.id)
        )
        user_count = user_count_result.scalar() or 0
        org_data.append(org_to_dict(org, user_count))
    
    return {"data": org_data, "total": total}


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_organization(
    payload: OrganizationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_admin),
):
    """
    Create a new organization. Admin only.
    """
    # Check if name already exists
    existing = await db.execute(
        select(Organization).where(Organization.name == payload.name)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Organization with this name already exists")
    
    org = Organization(
        name=payload.name,
        domain=payload.domain,
        description=payload.description,
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(org)
    await db.commit()
    await db.refresh(org)
    
    return org_to_dict(org)


@router.get("/{org_id}")
async def get_organization(
    org_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_admin),
):
    """
    Get organization details. Admin only.
    """
    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()
    
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    user_count_result = await db.execute(
        select(func.count()).select_from(User).where(User.organization_id == org.id)
    )
    user_count = user_count_result.scalar() or 0
    
    return org_to_dict(org, user_count)


@router.patch("/{org_id}")
async def update_organization(
    org_id: int,
    payload: OrganizationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_admin),
):
    """
    Update organization. Admin only.
    """
    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()
    
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    # Check if new name conflicts
    if payload.name and payload.name != org.name:
        existing = await db.execute(
            select(Organization).where(Organization.name == payload.name)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Organization with this name already exists")
    
    # Update fields
    if payload.name is not None:
        org.name = payload.name
    if payload.domain is not None:
        org.domain = payload.domain
    if payload.description is not None:
        org.description = payload.description
    if payload.is_active is not None:
        org.is_active = payload.is_active
    
    org.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(org)
    
    return org_to_dict(org)


@router.delete("/{org_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_organization(
    org_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_admin),
):
    """
    Delete organization. Admin only.
    Sets is_active to False rather than hard delete.
    """
    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()
    
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    # Check if org has users
    user_count_result = await db.execute(
        select(func.count()).select_from(User).where(User.organization_id == org.id)
    )
    user_count = user_count_result.scalar() or 0
    
    if user_count > 0:
        # Soft delete - just deactivate
        org.is_active = False
        org.updated_at = datetime.utcnow()
        await db.commit()
    else:
        # Hard delete if no users
        await db.delete(org)
        await db.commit()
    
    return None


@router.get("/{org_id}/users")
async def list_organization_users(
    org_id: int,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_admin),
):
    """
    List users in an organization. Admin only.
    """
    # Check org exists
    org_result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = org_result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    # Get users
    query = (
        select(User)
        .where(User.organization_id == org_id)
        .order_by(User.full_name)
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(query)
    users = result.scalars().all()
    
    # Get total count
    count_result = await db.execute(
        select(func.count()).select_from(User).where(User.organization_id == org_id)
    )
    total = count_result.scalar() or 0
    
    user_data = [
        {
            "id": u.id,
            "email": u.email,
            "full_name": u.full_name,
            "role": u.role,
            "department": u.department,
            "is_active": u.is_active,
            "created_at": u.created_at.isoformat() if u.created_at else None,
        }
        for u in users
    ]
    
    return {"data": user_data, "total": total}


@router.post("/{org_id}/users/{user_id}")
async def add_user_to_organization(
    org_id: int,
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_admin),
):
    """
    Add a user to an organization. Admin only.
    """
    # Check org exists
    org_result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = org_result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    # Check user exists
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Assign user to org
    user.organization_id = org_id
    user.updated_at = datetime.utcnow()
    
    await db.commit()
    
    return {"message": f"User {user.email} added to organization {org.name}"}


@router.delete("/{org_id}/users/{user_id}")
async def remove_user_from_organization(
    org_id: int,
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_admin),
):
    """
    Remove a user from an organization. Admin only.
    """
    # Check user exists and belongs to org
    user_result = await db.execute(
        select(User).where(User.id == user_id, User.organization_id == org_id)
    )
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found in this organization")
    
    # Remove from org
    user.organization_id = None
    user.updated_at = datetime.utcnow()
    
    await db.commit()
    
    return {"message": f"User {user.email} removed from organization"}
