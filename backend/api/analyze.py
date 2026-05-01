"""
Email Analysis API
Performs technical analysis (SPF/DKIM/DMARC), URL inspection, and attachment scanning.
"""
import base64
import logging
import os
from datetime import datetime
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

from auth.permissions import get_current_user, CurrentUser
from database import get_db
from sqlalchemy.ext.asyncio import AsyncSession


router = APIRouter(prefix="/api/v1/analyze", tags=["Analyze"])
logger = logging.getLogger(__name__)

# Import WebSocket integration for real-time notifications
try:
    from websocket_integration import notify_email_analysis_complete, notify_alert_created
    WS_AVAILABLE = True
except ImportError:
    WS_AVAILABLE = False
    logger.warning("WebSocket integration not available")


class HeaderAnalysisRequest(BaseModel):
  """Request for header/technical analysis"""
  from_address: EmailStr
  to_address: EmailStr
  subject: str
  sender_ip: str
  headers: Dict[str, str]
  body: Optional[str] = None
  raw_email: Optional[str] = Field(
      None, description="Raw email in base64 (.eml) for DKIM and attachment parsing"
  )


@router.post(
    "/headers",
    status_code=status.HTTP_200_OK,
    summary="Technical analysis of email (SPF/DKIM/DMARC, URLs, attachments)",
)
@router.post(
    "/headers",
    status_code=status.HTTP_200_OK,
    summary="Technical analysis of email (SPF/DKIM/DMARC, URLs, attachments)",
)
async def analyze_headers(
    payload: HeaderAnalysisRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Perform full email analysis using AnalysisService.
    """
    from services.analysis_service import AnalysisService
    
    # 1. Initialize Service
    service = AnalysisService(db)
    
    # 2. Delegate to Service
    try:
        result = await service.analyze_email_headers(
            from_address=payload.from_address,
            to_address=payload.to_address,
            subject=payload.subject,
            headers=payload.headers,
            body=payload.body,
            sender_ip=payload.sender_ip,
            raw_email_b64=payload.raw_email,
            user_id=current_user.id
        )
        
        # 3. Add Attachment Scan Results (Service currently does not handle attachments explicitly similar to API)
        # Note: AnalysisService design in Phase 1 focused on Logic extraction. 
        # Attachment scanning is a bit unique due to file handling. 
        # For now, we keep attachment scanning in API or move it to Service later.
        # To strictly follow "Slim Controller", we should move it.
        # However, to avoid Breaking Changes with minimal risk, let's keep it here or delegate.
        # The prompt asked for "orchestrator.analyze(email)".
        
        # Let's keep attachment scanning here for now as "File Handling" logic, 
        # but ideally it belongs in the service too.
        
        attachment_results = []
        # Enable sandbox based on environment variable (default: disabled for performance)
        enable_sandbox = os.getenv("ENABLE_SANDBOX_ANALYSIS", "false").lower() == "true"
        
        if payload.raw_email:
             # Re-decode for attachments (inefficient but safe for refactor step)
             try:
                import email
                from email import policy
                from analyzers.attachment_scanner import attachment_scanner
                
                raw_bytes = base64.b64decode(payload.raw_email)
                msg = email.message_from_bytes(raw_bytes, policy=policy.default)
                
                for part in msg.walk():
                    filename = part.get_filename()
                    if filename:
                        content = part.get_payload(decode=True) or b""
                        if content:
                            scan = await attachment_scanner.scan_attachment(
                                filename, content, enable_sandbox=enable_sandbox, enable_virustotal=True
                            )
                            scan["filename"] = filename
                            attachment_results.append(scan)
             except Exception:
                 pass
        
        result["attachments"] = attachment_results
        
        # WebSocket Notification Logic (Service handles persistence, but notification might be here or there)
        # AnalysisService persist_result sends the notification potentially?
        # Looking at AnalysisService implementation above - it DOES NOT have WS logic yet.
        # We must migrate WS logic to Service or keep it here.
        # Clean Architecture: Side effects (notifications) often belong in Service or Domain Events.
        # Let's add WS notification here for now to ensure reliability until Service is fully mature.
        
        if WS_AVAILABLE and result.get("risk_score"):
             try:
                from websocket_integration import notify_email_analysis_complete
                analysis_data = {
                    "message_id": payload.headers.get("Message-ID"),
                    "from_address": payload.from_address,
                    "to_address": payload.to_address,
                    "subject": payload.subject,
                    "risk_score": result["risk_score"],
                    "status": result["status"],
                    "analyzed_at": datetime.utcnow().isoformat(),
                }
                await notify_email_analysis_complete(analysis_data, user_id=current_user.id)
             except Exception:
                 pass
        
        return result

    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
