from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import math

from database import get_db
from schemas.registry import (
    RegistryCreate,
    RegistryUpdate,
    RegistryApprove,
    RegistryQuarantine,
    RegistryResponse,
    RegistryListResponse,
    RegistryStats
)
from services.registry_service import RegistryService
from auth.permissions import (
    get_current_active_user,
    require_security_officer,
    CurrentUser
)

router = APIRouter(prefix="/api/v1/registry", tags=["Trusted Registry"])


@router.get(
    "/",
    response_model=RegistryListResponse,
    summary="Get all registry entries",
    description="Get paginated list of registry entries with optional filtering"
)
async def get_all_entries(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    trust_level: Optional[int] = Query(None, ge=1, le=4, description="Filter by trust level"),
    status: Optional[str] = Query(None, description="Filter by status (active, pending, quarantine)"),
    search: Optional[str] = Query(None, description="Search in email, domain, organization"),
    is_verified: Optional[bool] = Query(None, description="Filter by verification status"),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_active_user)
):
    """
    Get all registry entries with filtering and pagination.

    **Permissions:** Any authenticated user

    **Filters:**
    - trust_level: Filter by trust level (1-4)
    - status: active, pending, quarantine
    - search: Search in email, domain, or organization name
    - is_verified: Filter by verification status
    """
    items, total = await RegistryService.get_all(
        db=db,
        page=page,
        per_page=per_page,
        trust_level=trust_level,
        status=status,
        search=search,
        is_verified=is_verified
    )

    pages = math.ceil(total / per_page) if total > 0 else 1

    return RegistryListResponse(
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
        items=items
    )


@router.get(
    "/stats",
    response_model=RegistryStats,
    summary="Get registry statistics",
    description="Get statistical overview of the registry"
)
async def get_stats(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_security_officer)
):
    """
    Get registry statistics.

    **Permissions:** Security officer or admin
    """
    stats = await RegistryService.get_stats(db)
    return stats


@router.get(
    "/pending",
    response_model=RegistryListResponse,
    summary="Get pending entries",
    description="Get entries waiting for approval"
)
async def get_pending_entries(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_security_officer)
):
    """
    Get pending registry entries (awaiting approval).

    **Permissions:** Security officer or admin
    """
    items, total = await RegistryService.get_pending(
        db=db,
        page=page,
        per_page=per_page
    )

    pages = math.ceil(total / per_page) if total > 0 else 1

    return RegistryListResponse(
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
        items=items
    )


@router.get(
    "/{email}",
    response_model=RegistryResponse,
    summary="Get registry entry by email",
    description="Get specific registry entry by email address"
)
async def get_entry(
    email: str,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_active_user)
):
    """
    Get registry entry by email address.

    **Permissions:** Any authenticated user
    """
    entry = await RegistryService.get_by_email(db, email)
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Registry entry for '{email}' not found"
        )
    return entry


@router.post(
    "/",
    response_model=RegistryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add new registry entry",
    description="Add new email address to trusted registry"
)
async def create_entry(
    data: RegistryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_active_user)
):
    """
    Add new entry to trusted registry.

    **Permissions:**
    - Regular users: Can suggest additions (entry will be pending)
    - Security officers: Can add verified entries directly

    **Note:** Security officers' additions are auto-approved and verified.
    Regular users' additions require approval from security officer.
    """
    try:
        entry = await RegistryService.create(db, data, current_user)
        return entry
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put(
    "/{email}",
    response_model=RegistryResponse,
    summary="Update registry entry",
    description="Update existing registry entry"
)
async def update_entry(
    email: str,
    data: RegistryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_security_officer)
):
    """
    Update registry entry.

    **Permissions:** Security officer or admin
    """
    entry = await RegistryService.update(db, email, data, current_user)
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Registry entry for '{email}' not found"
        )
    return entry


@router.delete(
    "/{email}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete registry entry",
    description="Deactivate registry entry (soft delete)"
)
async def delete_entry(
    email: str,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_security_officer)
):
    """
    Delete (deactivate) registry entry.

    **Permissions:** Security officer or admin

    **Note:** This is a soft delete - entry is deactivated, not removed.
    """
    deleted = await RegistryService.delete(db, email, current_user)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Registry entry for '{email}' not found"
        )
    return None


@router.post(
    "/{email}/approve",
    response_model=RegistryResponse,
    summary="Approve pending entry",
    description="Approve pending registry entry"
)
async def approve_entry(
    email: str,
    data: RegistryApprove,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_security_officer)
):
    """
    Approve pending registry entry.

    **Permissions:** Security officer or admin

    This verifies the entry and sets the approved trust level.
    """
    entry = await RegistryService.approve(db, email, data, current_user)
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Registry entry for '{email}' not found"
        )
    return entry


@router.post(
    "/{email}/quarantine",
    response_model=RegistryResponse,
    summary="Quarantine entry",
    description="Put registry entry into quarantine"
)
async def quarantine_entry(
    email: str,
    data: RegistryQuarantine,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_security_officer)
):
    """
    Put registry entry into quarantine.

    **Permissions:** Security officer or admin

    This deactivates the entry due to suspicious activity.
    A reason must be provided.
    """
    entry = await RegistryService.quarantine(db, email, data, current_user)
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Registry entry for '{email}' not found"
        )
    return entry
