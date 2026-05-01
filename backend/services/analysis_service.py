import logging
import base64
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

# Redis
try:
    from redis_client import redis_client
    REDIS_AVAILABLE = True
except ImportError:
    redis_client = None
    REDIS_AVAILABLE = False

# Analyzers
from analyzers.technical_analyzer import technical_analyzer
from analyzers.linguistic_analyzer import linguistic_analyzer
from analyzers import behavioral_analyzer
from analyzers.contextual_analyzer import contextual_analyzer
from analyzers.url_inspector import url_inspector
from analyzers.attachment_scanner import attachment_scanner

# Repositories
try:
    from repositories.email_analysis_repo import EmailAnalysisRepository
    from repositories.trusted_registry_repo import TrustedRegistryRepository
except ModuleNotFoundError:
    # Fallback: Add project root to path (needed for some Celery configurations)
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from repositories.email_analysis_repo import EmailAnalysisRepository
    from repositories.trusted_registry_repo import TrustedRegistryRepository

# Models & Utilities
from database import EmailAnalysis
from schemas.registry import TrustLevel
from utils.email_validator import (
    extract_domain_from_email,
    normalize_email,
    is_valid_email_format
)

logger = logging.getLogger(__name__)

class AnalysisService:
    """
    Orchestrates the entire email analysis pipeline.
    Replaces logic previously located in api/analyze.py
    """
    def __init__(self, db: AsyncSession):
        self.db = db
        self.email_repo = EmailAnalysisRepository(db)
        self.email_repo = EmailAnalysisRepository(db)
        self.registry_repo = TrustedRegistryRepository(db)
        self.behavioral_analyzer = behavioral_analyzer.BehavioralAnalyzer(db) # Now uses internal repo
        from websocket_manager import connection_manager
        self.ws_manager = connection_manager

    async def _emit_log(self, user_id: Optional[int], message: str, level: str = "info"):
        if user_id:
            await self.ws_manager.send_to_user({
                "type": "analysis_log",
                "data": {
                    "message": message,
                    "level": level,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }, user_id)

    async def perform_full_analysis(self,
                                  from_address: str,
                                  to_address: str,
                                  subject: str,
                                  headers: Dict[str, str],
                                  body: Optional[str] = None,
                                  sender_ip: Optional[str] = None,
                                  raw_email_bytes: Optional[bytes] = None,
                                  user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Execute all analyzers and return raw results.
        Does NOT persist data.
        """
        if user_id:
             await self._emit_log(user_id, f"🚀 STARTING ANALYSIS for: {subject} <{from_address}>", level="info")

        # 1. Technical Analysis (SPF/DKIM/DMARC)
        tech_result = await technical_analyzer.check_headers(
            raw_email=raw_email_bytes,
            headers=headers,
            body=body,
            sender_ip=sender_ip,
        )
        await self._emit_log(user_id, f"🔍 Technical Analysis: SPF={tech_result.get('spf', {}).get('result', 'N/A')}, DKIM={tech_result.get('dkim', {}).get('result', 'N/A')}")
        if tech_result.get("authentication", {}).get("score", 0) < 50:
             await self._emit_log(user_id, "⚠️ Technical Checks Failed: Authentication issues detected", level="warning")
        else:
             await self._emit_log(user_id, "✅ Technical Checks Passed", level="success")

        # 2. Linguistic Analysis (AI)
        linguistic_result = {}
        if body:
            linguistic_result = await linguistic_analyzer.analyze_text(
                text=body,
                sender=from_address,
                subject=subject
            )
            await self._emit_log(user_id, f"🧠 Linguistic Analysis: Sentiment={linguistic_result.get('sentiment', 'N/A')}, Urgency={linguistic_result.get('urgency', 'N/A')}")
        else:
            await self._emit_log(user_id, "⏭️ Skipping Linguistic Analysis (No body content)")

        # 3. Contextual Analysis
        context_result = await contextual_analyzer.analyze(
            from_address=from_address,
            to_address=to_address,
            subject=subject,
            headers=headers,
            body_preview=(body or "")[:1000]
        )
        await self._emit_log(user_id, "🌍 Contextual Analysis: Checking relationship and communication patterns...")

        # 4. Behavioral Analysis
        await self._emit_log(user_id, f"🕵️‍♂️ Behavioral Analysis: Profiling sender {from_address}...")
        behavioral_result = await self.behavioral_analyzer.analyze(from_address=from_address)
        score = behavioral_result.get("score", 0)
        await self._emit_log(user_id, f"📊 Behavioral Match: {score}/100 confidence", level="info" if score > 70 else "warning")

        # 5. URL & Attachment Scanning
        url_results = []
        if body:
            extracted = url_inspector.extractor.extract_all_urls(body_text=body)
            # Limit to 10 for performance
            for item in extracted[:10]:
                if item.get("url"):
                    res = await url_inspector.analyze_url(item["url"])
                    res["url"] = item["url"]
                    url_results.append(res)
        
        # 6. Result Aggregation & Risk Calculation
        await self._emit_log(user_id, "🧮 Aggregating Risk Scores...")
        final_risk = self._calculate_risk_score(
            tech_result, linguistic_result, context_result, behavioral_result
        )

        # 7. Generate Explanations
        details = {
            "technical": [],
            "linguistic": [],
            "behavioral": [],
            "contextual": []
        }

        # Technical Details
        if tech_result.get("spf", {}).get("status") == "pass":
            details["technical"].append("✅ SPF проверка пройдена")
        else:
            details["technical"].append(f"❌ SPF ошибка: {tech_result.get('spf', {}).get('status', 'unknown')}")
        
        if tech_result.get("dkim", {}).get("status") == "pass":
            details["technical"].append("✅ DKIM подпись верна")
        else:
            details["technical"].append(f"❌ DKIM ошибка: {tech_result.get('dkim', {}).get('status', 'not found')}")

        # Linguistic Details
        if linguistic_result.get("urgency", "").lower() in ["high", "critical"]:
            details["linguistic"].append(f"⚠️ Высокая срочность: {linguistic_result.get('urgency_reason', 'манипуляция сроками')}")
        if linguistic_result.get("sentiment") == "negative":
            details["linguistic"].append("😠 Негативная тональность")
        for intent in linguistic_result.get("intents", []):
             details["linguistic"].append(f"🎯 Намерение: {intent}")

        # Contextual Details
        if context_result.get("is_new_sender"):
             details["contextual"].append("👤 Новый отправитель (ранее не общались)")
        if context_result.get("domain_age_days", 365) < 30:
             details["contextual"].append(f"baby-domain: Домену всего {context_result.get('domain_age_days')} дней")
        
        # Behavioral Details
        trust = behavioral_result.get("score", 0)
        if trust < 20:
             details["behavioral"].append("📉 Низкое доверие к отправителю")
        elif trust > 80:
             details["behavioral"].append("⭐ Высокое доверие (частая переписка)")

        return {
            "risk_score": final_risk,
            "technical": tech_result,
            "linguistic": linguistic_result,
            "behavioral": behavioral_result,
            "contextual": context_result,
            "urls": url_results,
            "analysis_details": details
        }

    async def analyze_email_headers(self, 
                                  from_address: str, 
                                  to_address: str, 
                                  subject: str, 
                                  headers: Dict[str, str], 
                                  body: Optional[str] = None,
                                  sender_ip: Optional[str] = None,
                                  raw_email_b64: Optional[str] = None,
                                  user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Full email analysis pipeline: Technical -> AI -> Context -> Behavioral -> Persistence
        """
        # 0. Pre-processing (decode raw email if present)
        raw_bytes = None
        if raw_email_b64:
            try:
                raw_bytes = base64.b64decode(raw_email_b64)
            except Exception as e:
                logger.error(f"Base64 decode error: {e}")

        # Execute Pipeline
        results = await self.perform_full_analysis(
            from_address=from_address,
            to_address=to_address,
            subject=subject,
            headers=headers,
            body=body,
            sender_ip=sender_ip,
            raw_email_bytes=raw_bytes,
            user_id=user_id # Pass user_id for logging
        )

        await self._emit_log(user_id, f"🏁 Analysis Complete. Risk Score: {results['risk_score']}", level="success" if results['risk_score'] < 50 else "danger")

        # 7. Persistence
        analysis_record = await self._persist_result(
            user_id=user_id,
            from_addr=from_address,
            to_addr=to_address,
            subject=subject,
            body=body,
            headers=headers,
            risk_score=results["risk_score"],
            tech=results["technical"],
            ling=results["linguistic"],
            behav=results["behavioral"],
            cont=results["contextual"]
        )

        # Merge persistence status into results for API format
        results["status"] = analysis_record.status
        results["analyzed_at"] = analysis_record.analyzed_at.isoformat()
        
        return results

    def _calculate_risk_score(self, tech, ling, cont, behav) -> float:
        """
        Calculate weighted risk score.
        Input scores are "validity scores" (100 = good), we convert to Risk (100 = bad)
        """
        # Tech score is 0-100 (100 is safe). We previously only took auth score.
        # Now we combine Auth, Spoofing, and Header Anomalies.
        auth_score = tech.get("authentication", {}).get("score", 0)
        spoof_score = tech.get("spoofing", {}).get("score", 100)
        headers_score = tech.get("header_anomalies", {}).get("score", 100)
        
        # Taking the minimum acts as a "weakest link" approach - if any part is bad, tech score is bad.
        # Or we can average them. Let's weigh them: Auth is critical. Spoofing is critical.
        tech_score = min(auth_score, spoof_score, headers_score) 
        
        tech_risk = 100 - tech_score
        
        # Linguistic risk is already 0-100 (100 is bad - usually)
        # Check linguistic_analyzer implementation: returns "risk_score" directly
        ling_risk = ling.get("risk_score", 0)
        
        # Contextual returns "score" (validity, 100=safe)
        cont_risk = 100 - cont.get("score", 100)
        
        # Behavioral returns "score" (validity, 100=safe)
        behav_risk = 100 - behav.get("score", 100)

        # Weights
        # Adjusted for better phishing detection:
        # Tech: 15% (Auth is important but often passed by hacked accounts/spoofing)
        # Linguistic: 40% (Content is king for social engineering)
        # Behavioral: 25% (Trust history)
        # Context: 20% (New sender, age, etc)
        final_risk = (
            tech_risk * 0.15 +
            ling_risk * 0.40 +
            behav_risk * 0.25 +
            cont_risk * 0.20
        )
        # Bonus penalty: If Linguistic is Critical (>70), ensure Final Risk is at least High (>50)
        if ling_risk > 70:
            final_risk = max(final_risk, 65.0)

        # KILL CHAIN OVERRIDE
        # If Linguistic Analyzer identified a specific attack scenario (Kill Chain), 
        # we trust it implicitly and force a CRITICAL score, ignoring technical "passes"
        attack_type = ling.get("attack_type", "generic")
        if attack_type in ["bec_fraud", "credential_phishing"] or ling_risk >= 90:
             final_risk = max(final_risk, 90.0) # Force Critical

        return round(final_risk, 2)

    async def check_incoming_email(
        self,
        from_address: str,
        to_address: str,
        subject: str,
        ip_address: str,
        headers: Dict[str, str],
        body_preview: Optional[str] = None,
        spf_result: Optional[str] = None,
        dkim_result: Optional[str] = None,
        dkim_signature: Optional[str] = None,
        use_cache: bool = True
    ) -> Dict:
        """
        Check incoming email against registry and perform security analysis.
        Implements Fast Track logic for trusted senders.
        """
        import json # Local import for caching logic

        # Normalize and validate
        from_address = normalize_email(from_address)
        to_address = normalize_email(to_address)

        if not is_valid_email_format(from_address):
             return {
                "action": "block",
                "status": "danger",
                "risk_score": 100.0,
                "confidence": 100.0,
                "reason": "invalid_format",
                "details": "Invalid sender email format",
                "timestamp": datetime.utcnow().isoformat()
            }

        # Check Cache
        if use_cache and REDIS_AVAILABLE:
            cache_key = f"registry_check:{from_address}:{ip_address}"
            try:
                cached = await redis_client.get(cache_key)
                if cached:
                    res = json.loads(cached)
                    res["cached"] = True
                    return res
            except Exception as e:
                logger.error(f"Cache read error: {e}")

        domain = extract_domain_from_email(from_address)
        
        # Registry Lookup
        registry_entry = await self.registry_repo.get_by_email(from_address)
        
        result = {}
        if registry_entry and registry_entry.trust_level in [TrustLevel.MAX_TRUST, TrustLevel.HIGH_TRUST]:
            # Fast Track
            result = await self._fast_track_check(
                from_address, to_address, subject, domain, ip_address, headers,
                registry_entry, spf_result, dkim_result
            )
        else:
            # Full Check
            result = await self._full_check(
                from_address, to_address, subject, domain, ip_address, headers,
                body_preview, registry_entry, spf_result, dkim_result
            )

        # Cache Result
        if use_cache and REDIS_AVAILABLE:
             try:
                ttl = 900 if result["action"] != "block" else 300
                await redis_client.setex(
                    f"registry_check:{from_address}:{ip_address}",
                    ttl,
                    json.dumps(result)
                )
             except Exception as e:
                logger.error(f"Cache write error: {e}")
        
        result["cached"] = False
        return result

    async def _fast_track_check(self, from_addr, to_addr, subject, domain, ip, headers, entry, spf, dkim):
        """Minimal check for trusted senders"""
        # technical_analyzer check
        tech_res = await technical_analyzer.check_headers(
            raw_email=None, headers=headers, body=None, sender_ip=ip
        )
        tech_score = tech_res.get("authentication", {}).get("score", 0)
        risk_score = 100 - tech_score
        
        status = "safe"
        action = "allow"
        if risk_score > 60: 
            status = "warning"
            action = "quarantine"
            
        return {
            "action": action,
            "status": status,
            "risk_score": round(max(0, risk_score), 2),
            "confidence": 95.0,
            "in_registry": True,
            "trust_level": entry.trust_level,
            "check_type": "fast_track",
            "checks": {"technical": tech_res},
            "registry_info": {
                "email": entry.email_address,
                "organization": entry.organization_name
            },
            "timestamp": datetime.utcnow().isoformat()
        }

    async def _full_check(self, from_addr, to_addr, subject, domain, ip, headers, body_preview, entry, spf, dkim):
        """Full comprehensive check"""
        # 1. Technical
        tech_res = await technical_analyzer.check_headers(
            raw_email=None, headers=headers, body=None, sender_ip=ip
        )
        
        # 2. Contextual
        cont_res = await contextual_analyzer.analyze(
            from_address=from_addr, to_address=to_addr, subject=subject,
            headers=headers, body_preview=body_preview
        )
        
        # 3. Behavioral
        behav_res = await self.behavioral_analyzer.analyze(from_address=from_addr)
        
        # Calculate Logic
        risk_score = self._calculate_risk_score(tech_res, {}, cont_res, behav_res)
        
        # Registry Bonus
        if entry:
             if entry.trust_level == TrustLevel.MEDIUM_TRUST: risk_score *= 0.9
             elif entry.trust_level == TrustLevel.LOW_TRUST: risk_score *= 0.95

        action = "allow"
        status = "safe"
        if risk_score >= 70: 
            action = "block"
            status = "danger"
        elif risk_score >= 50:
            action = "quarantine"
            status = "warning"
        elif risk_score >= 30:
            status = "caution"

        return {
            "action": action,
            "status": status,
            "risk_score": round(risk_score, 2),
            "confidence": 90.0 if entry else 75.0,
            "in_registry": entry is not None,
            "check_type": "full",
            "checks": {
                "technical": tech_res,
                "context": cont_res,
                "behavioral": behav_res
            },
            "timestamp": datetime.utcnow().isoformat()
        }

    async def persist_result(self, user_id, from_addr, to_addr, subject, body, headers, risk_score, tech, ling, behav, cont) -> EmailAnalysis:
        # Renamed internal method to public if needed, or keep internal usages
        return await self._persist_result(user_id, from_addr, to_addr, subject, body, headers, risk_score, tech, ling, behav, cont)

    async def _persist_result(self, user_id: int, from_addr: str, to_addr: str, 
                            subject: str, body: str, headers: Dict, 
                            risk_score: float, tech: Dict, ling: Dict, 
                            behav: Dict, cont: Dict, details: Dict) -> EmailAnalysis:
        analysis = EmailAnalysis(
            user_id=user_id,
            message_id=headers.get("Message-ID", f"unknown-{datetime.utcnow().timestamp()}"),
            from_address=from_addr,
            to_address=to_addr,
            subject=subject,
            body_preview=(body or "")[:500],
            body_text=body,
            raw_headers=headers,
            risk_score=risk_score,
            status=self._calculate_status(risk_score),
            technical_score=min(
                tech.get("authentication", {}).get("score", 0),
                tech.get("spoofing", {}).get("score", 100),
                tech.get("header_anomalies", {}).get("score", 100)
            ),
            linguistic_score=ling.get("risk_score", 0),
            behavioral_score=behav.get("score", 0),
            contextual_score=cont.get("score", 0),
            analysis_details=details
        )
        self.db.add(analysis)
        await self.db.flush()
        return analysis
