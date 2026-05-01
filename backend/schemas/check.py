"""
Schemas for email check API
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Dict, Optional, List
from datetime import datetime


class EmailCheckRequest(BaseModel):
    """Request to check an incoming email"""

    from_address: EmailStr = Field(..., description="Sender email address")
    to_address: EmailStr = Field(..., description="Recipient email address")
    subject: str = Field(..., min_length=1, max_length=500, description="Email subject")
    ip_address: str = Field(..., description="Sender's IP address")

    # Email headers
    headers: Dict[str, str] = Field(
        default_factory=dict,
        description="Email headers (From, To, Date, Message-ID, etc.)"
    )

    # Optional fields
    body_preview: Optional[str] = Field(
        None,
        max_length=1000,
        description="First N characters of email body"
    )

    spf_result: Optional[str] = Field(
        None,
        description="Pre-computed SPF result (pass/fail/softfail/neutral/none)"
    )

    dkim_result: Optional[str] = Field(
        None,
        description="Pre-computed DKIM result (pass/fail/none)"
    )

    dkim_signature: Optional[str] = Field(
        None,
        description="DKIM signature header value"
    )

    use_cache: bool = Field(
        True,
        description="Whether to use Redis cache"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "from_address": "director@ministry.gov.ru",
                "to_address": "security@fsb.gov.ru",
                "subject": "Monthly security report",
                "ip_address": "10.0.1.15",
                "headers": {
                    "From": "Director <director@ministry.gov.ru>",
                    "To": "Security <security@fsb.gov.ru>",
                    "Date": "Mon, 13 Oct 2025 10:30:00 +0300",
                    "Message-ID": "<abc123@ministry.gov.ru>",
                    "Return-Path": "<director@ministry.gov.ru>"
                },
                "body_preview": "Dear colleagues, Please find attached...",
                "spf_result": "pass",
                "dkim_result": "pass",
                "use_cache": True
            }
        }


class TechnicalCheckResult(BaseModel):
    """Technical validation results"""
    valid: bool
    result: str
    score: int
    details: str


class ContextCheckResult(BaseModel):
    """Context validation results"""
    valid: bool
    score: int
    issues: List[str]
    details: str
    skipped: Optional[bool] = None
    reason: Optional[str] = None


class BehavioralCheckResult(BaseModel):
    """Behavioral analysis results"""
    valid: bool
    score: int
    issues: List[str]
    recent_email_count: Optional[int] = None
    details: str
    skipped: Optional[bool] = None
    reason: Optional[str] = None


class ChecksDetail(BaseModel):
    """Detailed check results"""
    technical: Dict
    context: Dict
    behavioral: Dict


class RegistryInfo(BaseModel):
    """Registry information for sender"""
    email: str
    organization: Optional[str]
    trust_level: int
    verified: bool


class EmailCheckResponse(BaseModel):
    """Response from email check"""

    action: str = Field(..., description="Recommended action: allow/quarantine/block")
    status: str = Field(..., description="Risk status: safe/caution/warning/danger")
    risk_score: float = Field(..., ge=0, le=100, description="Risk score (0-100)")
    confidence: float = Field(..., ge=0, le=100, description="Confidence level (%)")

    in_registry: bool = Field(..., description="Whether sender is in trusted registry")
    trust_level: Optional[int] = Field(None, description="Trust level from registry (1-4)")
    check_type: str = Field(..., description="Type of check performed: fast_track/full/rejected")

    checks: Dict = Field(..., description="Detailed check results")

    registry_info: Optional[Dict] = Field(
        None,
        description="Registry information if sender is registered"
    )

    timestamp: str = Field(..., description="Check timestamp (ISO format)")
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")
    cached: bool = Field(False, description="Whether result was cached")

    # Optional rejection details
    reason: Optional[str] = Field(None, description="Rejection reason if applicable")
    details: Optional[str] = Field(None, description="Additional details")

    class Config:
        json_schema_extra = {
            "example": {
                "action": "allow",
                "status": "safe",
                "risk_score": 15.5,
                "confidence": 95.0,
                "in_registry": True,
                "trust_level": 1,
                "check_type": "fast_track",
                "checks": {
                    "technical": {
                        "technical_score": 92.5,
                        "risk_level": "low",
                        "passed": True
                    },
                    "context": {
                        "skipped": True,
                        "reason": "Fast track for trusted sender"
                    },
                    "behavioral": {
                        "skipped": True,
                        "reason": "Fast track for trusted sender"
                    }
                },
                "registry_info": {
                    "email": "director@ministry.gov.ru",
                    "organization": "Министерство цифрового развития",
                    "trust_level": 1,
                    "verified": True
                },
                "timestamp": "2025-10-13T10:30:00.123456",
                "processing_time_ms": 50,
                "cached": False
            }
        }


class BulkCheckRequest(BaseModel):
    """Request to check multiple emails"""
    emails: List[EmailCheckRequest] = Field(
        ...,
        max_length=100,
        description="List of emails to check (max 100)"
    )


class BulkCheckResponse(BaseModel):
    """Response from bulk check"""
    results: List[EmailCheckResponse]
    total: int
    successful: int
    failed: int
    processing_time_ms: float


class CheckStatsResponse(BaseModel):
    """Statistics about email checks"""
    total_checks: int
    checks_by_action: Dict[str, int]
    checks_by_status: Dict[str, int]
    average_risk_score: float
    cache_hit_rate: float
    average_processing_time_ms: float
