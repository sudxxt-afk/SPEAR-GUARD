"""
Pydantic schemas for attachment and URL analysis API

Author: SPEAR-GUARD Team
Date: 2025-11-05
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime


# ============================================================================
# ATTACHMENT SCHEMAS
# ============================================================================

class AttachmentScanRequest(BaseModel):
    """Request to scan attachment from base64 data"""
    filename: str = Field(..., description="Original filename")
    file_data: str = Field(..., description="Base64 encoded file content")
    enable_sandbox: bool = Field(
        default=False,
        description="Enable sandbox analysis (slow, ~30-60s)"
    )
    enable_virustotal: bool = Field(
        default=True,
        description="Enable VirusTotal hash lookup"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "filename": "document.pdf",
                "file_data": "JVBERi0xLjQKJeLjz9MKMSAwIG9iago8PC...",
                "enable_sandbox": False,
                "enable_virustotal": True
            }
        }


class FileHashInfo(BaseModel):
    """File hash information"""
    md5: str
    sha1: str
    sha256: str


class StaticAnalysisIssue(BaseModel):
    """Single issue from static analysis"""
    type: str
    severity: str
    description: str


class StaticAnalysisResult(BaseModel):
    """Static file analysis results"""
    filename: str
    extension: str
    mime_type: Optional[str]
    size: int
    issues: List[StaticAnalysisIssue]
    risk_level: str


class MacroAnalysisResult(BaseModel):
    """Macro detection results"""
    has_macros: bool
    indicators_found: List[str]
    macro_score: int
    recommendation: str


class VirusTotalFileResult(BaseModel):
    """VirusTotal file scan results"""
    found: Optional[bool] = None
    malicious: Optional[int] = None
    suspicious: Optional[int] = None
    harmless: Optional[int] = None
    undetected: Optional[int] = None
    total_scans: Optional[int] = None
    error: Optional[str] = None


class SandboxResult(BaseModel):
    """Sandbox analysis results"""
    task_id: Optional[int] = None
    status: Optional[str] = None
    score: Optional[int] = None
    classification: Optional[str] = None
    behaviors: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class OverallRiskResult(BaseModel):
    """Overall risk assessment"""
    score: float
    level: str
    recommendation: str
    component_scores: Dict[str, Any]


class AttachmentScanResponse(BaseModel):
    """Complete attachment scan results"""
    filename: str
    file_size: int
    file_hash: FileHashInfo
    static_analysis: StaticAnalysisResult
    macro_analysis: MacroAnalysisResult
    virustotal: Optional[VirusTotalFileResult]
    sandbox: Optional[SandboxResult]
    overall_risk: OverallRiskResult
    summary: str
    scan_time: float
    timestamp: str

    class Config:
        json_schema_extra = {
            "example": {
                "filename": "invoice.pdf.exe",
                "file_size": 524288,
                "file_hash": {
                    "md5": "d41d8cd98f00b204e9800998ecf8427e",
                    "sha1": "da39a3ee5e6b4b0d3255bfef95601890afd80709",
                    "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
                },
                "static_analysis": {
                    "filename": "invoice.pdf.exe",
                    "extension": ".exe",
                    "mime_type": "application/x-msdownload",
                    "size": 524288,
                    "issues": [
                        {
                            "type": "double_extension",
                            "severity": "critical",
                            "description": "File has double extension"
                        }
                    ],
                    "risk_level": "critical"
                },
                "macro_analysis": {
                    "has_macros": False,
                    "indicators_found": [],
                    "macro_score": 0,
                    "recommendation": "No macros detected"
                },
                "virustotal": {
                    "found": True,
                    "malicious": 42,
                    "suspicious": 8,
                    "harmless": 5,
                    "undetected": 15,
                    "total_scans": 70
                },
                "sandbox": None,
                "overall_risk": {
                    "score": 87.5,
                    "level": "critical",
                    "recommendation": "BLOCK - Do not open this file",
                    "component_scores": {
                        "static": 95,
                        "macro": 0,
                        "virustotal": 60,
                        "sandbox": None
                    }
                },
                "summary": "File 'invoice.pdf.exe' analysis complete. Overall risk: CRITICAL (87.5/100). BLOCK - Do not open this file. Critical issues found: 1. VirusTotal: 42 engines flagged as malicious.",
                "scan_time": 1.23,
                "timestamp": "2025-11-05T10:30:00"
            }
        }


# ============================================================================
# URL SCHEMAS
# ============================================================================

class URLAnalysisRequest(BaseModel):
    """Request to analyze single URL"""
    url: str = Field(..., description="URL to analyze")
    display_text: Optional[str] = Field(
        None,
        description="Display text (if from HTML link)"
    )
    enable_virustotal: bool = Field(
        default=True,
        description="Enable VirusTotal reputation check"
    )

    @validator('url')
    def validate_url(cls, v):
        if not v.startswith(('http://', 'https://')):
            raise ValueError('URL must start with http:// or https://')
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://secure-login.paypal-verify.com/account/verify",
                "display_text": "PayPal Security Center",
                "enable_virustotal": True
            }
        }


class BulkURLAnalysisRequest(BaseModel):
    """Request to analyze multiple URLs"""
    urls: List[str] = Field(..., description="List of URLs to analyze")
    enable_virustotal: bool = Field(
        default=True,
        description="Enable VirusTotal checks"
    )

    @validator('urls')
    def validate_urls(cls, v):
        if len(v) > 50:
            raise ValueError('Maximum 50 URLs per request')
        for url in v:
            if not url.startswith(('http://', 'https://')):
                raise ValueError(f'Invalid URL: {url}')
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "urls": [
                    "https://example.com/page1",
                    "https://suspicious-site.tk/login"
                ],
                "enable_virustotal": True
            }
        }


class EmailURLExtractionRequest(BaseModel):
    """Request to extract and analyze URLs from email"""
    body_text: Optional[str] = Field(None, description="Plain text body")
    body_html: Optional[str] = Field(None, description="HTML body")
    headers: Optional[Dict[str, str]] = Field(None, description="Email headers")
    enable_virustotal: bool = Field(
        default=True,
        description="Enable VirusTotal checks"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "body_text": "Visit our website: https://example.com",
                "body_html": "<p>Click here: <a href='https://phishing.com'>Secure Login</a></p>",
                "headers": {
                    "List-Unsubscribe": "<https://unsubscribe.example.com>"
                },
                "enable_virustotal": True
            }
        }


class StructureIssue(BaseModel):
    """URL structure issue"""
    type: str
    severity: str
    description: str


class StructureAnalysis(BaseModel):
    """URL structure analysis"""
    issues: List[StructureIssue]
    is_shortener: bool
    url_length: int
    subdomain_count: int


class PhishingPattern(BaseModel):
    """Detected phishing pattern"""
    keyword: str
    location: str
    severity: str
    description: Optional[str] = None


class PhishingPatternAnalysis(BaseModel):
    """Phishing pattern detection results"""
    patterns_found: List[PhishingPattern]
    phishing_score: int
    is_likely_phishing: bool


class HomographAnalysis(BaseModel):
    """Homograph/IDN detection results"""
    is_idn: bool
    is_homograph: bool
    details: Optional[str]
    decoded_domain: Optional[str] = None


class VirusTotalURLResult(BaseModel):
    """VirusTotal URL scan results"""
    url_scan: Optional[Dict[str, Any]] = None
    domain_reputation: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class OverallURLRisk(BaseModel):
    """Overall URL risk assessment"""
    score: float
    level: str
    recommendation: str
    component_scores: Dict[str, Any]


class URLAnalysisResponse(BaseModel):
    """Complete URL analysis results"""
    url: str
    parsed: Dict[str, Any]
    structure_analysis: StructureAnalysis
    phishing_patterns: PhishingPatternAnalysis
    homograph: HomographAnalysis
    virustotal: Optional[VirusTotalURLResult]
    domain_age: Optional[Dict[str, Any]]
    overall_risk: OverallURLRisk
    summary: str
    scan_time: float
    timestamp: str
    error: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://secure-login.paypal-verify.com/account",
                "parsed": {
                    "scheme": "https",
                    "domain": "secure-login.paypal-verify.com",
                    "base_domain": "paypal-verify.com",
                    "path": "/account",
                    "query": ""
                },
                "structure_analysis": {
                    "issues": [
                        {
                            "type": "display_mismatch",
                            "severity": "critical",
                            "description": "Display text doesn't match URL"
                        }
                    ],
                    "is_shortener": False,
                    "url_length": 62,
                    "subdomain_count": 2
                },
                "phishing_patterns": {
                    "patterns_found": [
                        {
                            "keyword": "paypal",
                            "location": "subdomain",
                            "severity": "critical",
                            "description": "Brand in subdomain - possible impersonation"
                        },
                        {
                            "keyword": "login",
                            "location": "path",
                            "severity": "high"
                        }
                    ],
                    "phishing_score": 65,
                    "is_likely_phishing": True
                },
                "homograph": {
                    "is_idn": False,
                    "is_homograph": False,
                    "details": None
                },
                "virustotal": {
                    "url_scan": {
                        "malicious": 15,
                        "suspicious": 5,
                        "harmless": 30,
                        "undetected": 40
                    },
                    "domain_reputation": {
                        "reputation": -25
                    }
                },
                "domain_age": None,
                "overall_risk": {
                    "score": 78.5,
                    "level": "critical",
                    "recommendation": "BLOCK - Do not visit this URL",
                    "component_scores": {
                        "structure": 40,
                        "phishing": 65,
                        "homograph": 0,
                        "virustotal": 85
                    }
                },
                "summary": "URL analysis complete. Overall risk: CRITICAL (78.5/100). BLOCK - Do not visit this URL. Phishing patterns detected. VirusTotal: 15 engines flagged as malicious.",
                "scan_time": 0.85,
                "timestamp": "2025-11-05T10:30:00"
            }
        }


class BulkURLAnalysisResponse(BaseModel):
    """Bulk URL analysis results"""
    total_urls: int
    results: List[URLAnalysisResponse]
    high_risk_count: int
    scan_time: float
    timestamp: str

    class Config:
        json_schema_extra = {
            "example": {
                "total_urls": 2,
                "results": [],
                "high_risk_count": 1,
                "scan_time": 1.5,
                "timestamp": "2025-11-05T10:30:00"
            }
        }
