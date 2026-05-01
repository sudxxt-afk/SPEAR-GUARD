from fastapi import APIRouter, Depends, HTTPException, status, Header
from pydantic import BaseModel
from typing import Dict, Any, List
from datetime import datetime
import logging
import os
import json
from database import get_db
from redis_client import get_redis
from auth.permissions import get_current_user
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/v1/system", tags=["System"])
logger = logging.getLogger(__name__)

# Redis key prefix for heartbeats
HEARTBEAT_KEY_PREFIX = "service:heartbeat:"
HEARTBEAT_TTL = 120  # 2 minutes

class HeartbeatRequest(BaseModel):
    service_name: str
    status: str  # "online", "error", "maintenance"
    details: Dict[str, Any] = {}
    timestamp: float

class ServiceStatus(BaseModel):
    service_name: str
    status: str
    last_seen: datetime
    details: Dict[str, Any]
    is_healthy: bool

@router.post("/heartbeat")
async def receive_heartbeat(
    payload: HeartbeatRequest,
    x_api_token: str = Header(..., alias="X-API-Token"),
):
    """
    Receive heartbeat from background services (IMAP/SMTP listeners).
    Requires valid API_SYSTEM_TOKEN in X-API-Token header.
    """
    # Validate API_SYSTEM_TOKEN from header
    expected_token = os.getenv("API_SYSTEM_TOKEN")
    if not expected_token:
        logger.error("API_SYSTEM_TOKEN not configured on server")
        raise HTTPException(status_code=503, detail="Service misconfigured")
    if x_api_token != expected_token:
        raise HTTPException(status_code=401, detail="Invalid API token")

    try:
        redis = await get_redis()
        key = f"{HEARTBEAT_KEY_PREFIX}{payload.service_name}"
        
        data = {
            "status": payload.status,
            "details": payload.details,
            "last_seen": datetime.utcnow().isoformat(),
            "timestamp": payload.timestamp
        }
        
        await redis.set(key, json.dumps(data), ex=HEARTBEAT_TTL)
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Failed to process heartbeat: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/status", response_model=List[ServiceStatus])
async def get_system_status(
    current_user = Depends(get_current_user),
    redis = Depends(get_redis)
):
    """
    Get aggregated status of all registered services.
    Now includes Celery-based IMAP sync status.
    """
    import asyncio
    from concurrent.futures import ThreadPoolExecutor
    
    result = []
    
    # Check Celery worker status (for IMAP sync) - run in threadpool to avoid blocking
    def check_celery():
        try:
            from config.celery_config import celery_app
            ping_result = celery_app.control.ping(timeout=1) or []
            return len(ping_result) > 0, len(ping_result), None
        except Exception as e:
            return False, 0, str(e)
    
    try:
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as pool:
            celery_healthy, worker_count, error = await loop.run_in_executor(pool, check_celery)
        
        result.append(ServiceStatus(
            service_name="celery-imap-sync",
            status="online" if celery_healthy else "offline",
            last_seen=datetime.utcnow(),
            details={
                "workers": worker_count,
                "error": error
            } if error else {"workers": worker_count},
            is_healthy=celery_healthy
        ))
    except Exception as e:
        logger.warning(f"Failed to check Celery status: {e}")
        result.append(ServiceStatus(
            service_name="celery-imap-sync",
            status="offline",
            last_seen=datetime.utcnow(),
            details={"error": str(e)},
            is_healthy=False
        ))
        
    return result

@router.post("/test-imap")
async def test_imap_connection(
    current_user = Depends(get_current_user)
):
    """
    Test IMAP connection with configured credentials.
    """
    import imaplib
    import os
    
    host = os.getenv("IMAP_HOST", "imap.gmail.com")
    port = int(os.getenv("IMAP_PORT", "993"))
    user = os.getenv("IMAP_USER", "")
    password = os.getenv("IMAP_PASSWORD", "")
    use_ssl = os.getenv("IMAP_USE_SSL", "true").lower() == "true"
    
    if not user or not password:
        return {
            "success": False,
            "error": "IMAP credentials not configured",
            "details": {"host": host, "user": user or "(not set)"}
        }
    
    try:
        if use_ssl:
            mail = imaplib.IMAP4_SSL(host, port)
        else:
            mail = imaplib.IMAP4(host, port)
        
        mail.login(user, password)
        mail.select("INBOX")
        
        # Get mailbox status
        status, messages = mail.search(None, "ALL")
        total_emails = len(messages[0].split()) if status == "OK" else 0
        
        status, unseen = mail.search(None, "UNSEEN")
        unseen_count = len(unseen[0].split()) if status == "OK" else 0
        
        mail.logout()
        
        return {
            "success": True,
            "message": "IMAP connection successful!",
            "details": {
                "host": host,
                "user": user,
                "total_emails": total_emails,
                "unseen_emails": unseen_count
            }
        }
    except imaplib.IMAP4.error as e:
        error_msg = str(e)
        if "AUTHENTICATIONFAILED" in error_msg or "Invalid credentials" in error_msg:
            return {
                "success": False,
                "error": "Authentication failed. For Gmail, you need an App Password.",
                "details": {"host": host, "user": user}
            }
        return {
            "success": False,
            "error": f"IMAP error: {error_msg}",
            "details": {"host": host, "user": user}
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "details": {"host": host, "user": user}
        }

@router.post("/test-gemini")
async def test_gemini_connection(
    current_user = Depends(get_current_user)
):
    """
    Test Gemini AI connection using the configured API key.
    """
    from analyzers.linguistic_analyzer import linguistic_analyzer
    
    if not linguistic_analyzer.model:
        return {
            "success": False, 
            "message": "Gemini Model not initialized (check API Key in .env)",
            "details": {"api_key_configured": bool(linguistic_analyzer.api_key)}
        }
        
    try:
        # Simple test prompt
        result = await linguistic_analyzer.analyze_text(
            text="This is a test message to verify connectivity with Google Gemini AI. Please confirm reception.", 
            sender="admin@spear-guard.local", 
            subject="System Connectivity Test"
        )
        
        # Check if it fell back to rule-based (which means AI failed)
        is_fallback = result.get("analysis_type") == "rule-based"
        
        if is_fallback:
             return {
                "success": False,
                "message": "Gemini is configured but analysis fell back to rules (AI Error?)", 
                "details": result
            }
            
        return {
            "success": True,
            "message": "Gemini AI connection successful!",
            "details": {
                "risk_level": result.get("risk_level"),
                "summary": result.get("summary"),
                "auth_status": "Authenticated"
            }
        }
    except Exception as e:
        logger.error(f"Gemini Test Failed: {e}")
        return {
            "success": False,
            "message": f"Gemini Test Failed: {str(e)}"
        }
