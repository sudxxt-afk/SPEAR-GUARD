from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
from datetime import datetime
from enum import Enum


class TrustLevel(int, Enum):
    """Trust levels for registry entries"""
    MAX_TRUST = 1  # Maximum trust - VIP senders
    HIGH_TRUST = 2  # High trust - verified partners
    MEDIUM_TRUST = 3  # Medium trust - known senders
    LOW_TRUST = 4  # Low trust - new/unverified


class RegistryStatus(str, Enum):
    """Status of registry entry"""
    ACTIVE = "active"
    PENDING = "pending"
    QUARANTINE = "quarantine"
    REJECTED = "rejected"


# Request schemas
class RegistryCreate(BaseModel):
    """Schema for creating new registry entry"""
    email_address: EmailStr = Field(..., description="Email address to add to registry")
    domain: str = Field(..., min_length=3, max_length=255, description="Domain of the email")
    organization_name: Optional[str] = Field(None, max_length=255, description="Organization name")
    trust_level: TrustLevel = Field(TrustLevel.LOW_TRUST, description="Trust level (1-4)")
    reason: Optional[str] = Field(None, description="Reason for adding to registry")

    @validator('domain')
    def validate_domain(cls, v, values):
        """Validate domain matches email address"""
        if 'email_address' in values:
            email = values['email_address']
            if '@' in email:
                email_domain = email.split('@')[1]
                if v.lower() != email_domain.lower():
                    raise ValueError(f"Domain '{v}' does not match email domain '{email_domain}'")
        return v.lower()

    class Config:
        json_schema_extra = {
            "example": {
                "email_address": "director@ministry.gov.ru",
                "domain": "ministry.gov.ru",
                "organization_name": "Ministry of Digital Development",
                "trust_level": 1,
                "reason": "Official government correspondence"
            }
        }


class RegistryUpdate(BaseModel):
    """Schema for updating registry entry"""
    organization_name: Optional[str] = Field(None, max_length=255)
    trust_level: Optional[TrustLevel] = None
    is_active: Optional[bool] = None

    class Config:
        json_schema_extra = {
            "example": {
                "trust_level": 2,
                "organization_name": "Updated Organization Name"
            }
        }


class RegistryApprove(BaseModel):
    """Schema for approving registry entry"""
    approved_trust_level: TrustLevel = Field(..., description="Approved trust level")
    approval_notes: Optional[str] = Field(None, description="Approval notes")

    class Config:
        json_schema_extra = {
            "example": {
                "approved_trust_level": 2,
                "approval_notes": "Verified through official channels"
            }
        }


class RegistryQuarantine(BaseModel):
    """Schema for quarantining registry entry"""
    reason: str = Field(..., min_length=10, description="Reason for quarantine")

    class Config:
        json_schema_extra = {
            "example": {
                "reason": "Suspicious activity detected - multiple failed SPF checks"
            }
        }


# Response schemas
class RegistryResponse(BaseModel):
    """Schema for registry entry response"""
    id: int
    email_address: str
    domain: str
    organization_name: Optional[str]
    trust_level: int
    added_by: Optional[int]
    approved_by: Optional[int]
    is_verified: bool
    is_active: bool
    status: str
    total_emails: int
    last_email_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "email_address": "director@ministry.gov.ru",
                "domain": "ministry.gov.ru",
                "organization_name": "Ministry of Digital Development",
                "trust_level": 1,
                "added_by": 5,
                "approved_by": 1,
                "is_verified": True,
                "is_active": True,
                "status": "active",
                "total_emails": 247,
                "last_email_at": "2025-10-08T10:30:00",
                "created_at": "2025-01-15T09:00:00",
                "updated_at": "2025-10-08T10:30:00"
            }
        }


class RegistryListResponse(BaseModel):
    """Schema for paginated registry list"""
    total: int = Field(..., description="Total number of entries")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Entries per page")
    pages: int = Field(..., description="Total number of pages")
    items: list[RegistryResponse] = Field(..., description="Registry entries")

    class Config:
        json_schema_extra = {
            "example": {
                "total": 150,
                "page": 1,
                "per_page": 20,
                "pages": 8,
                "items": []
            }
        }


class RegistryStats(BaseModel):
    """Statistics for registry"""
    total_entries: int
    active_entries: int
    pending_entries: int
    quarantine_entries: int
    by_trust_level: dict[int, int]
    verified_count: int
    unverified_count: int

    class Config:
        json_schema_extra = {
            "example": {
                "total_entries": 1500,
                "active_entries": 1420,
                "pending_entries": 45,
                "quarantine_entries": 35,
                "by_trust_level": {
                    "1": 150,
                    "2": 680,
                    "3": 520,
                    "4": 150
                },
                "verified_count": 1350,
                "unverified_count": 150
            }
        }
