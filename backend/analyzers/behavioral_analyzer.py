"""
Behavioral Email Analyzer
Analyzes sender behavior tracking:
- Volume spikes
- Time of day anomalies
- History tracking
- First-time sender detection
"""
import logging
from typing import Dict, Optional, List
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc

from database import EmailAnalysis
from utils.email_validator import extract_domain_from_email

logger = logging.getLogger(__name__)

class BehavioralAnalyzer:
    def __init__(self, db: AsyncSession):
        self.db = db
        # Import inside init to avoid circular deps if needed, or use repository
        from repositories.email_analysis_repo import EmailAnalysisRepository
        self.repo = EmailAnalysisRepository(db)

    async def analyze(
        self,
        from_address: str,
        email_timestamp: Optional[datetime] = None
    ) -> Dict:
        """
        Behavioral Analysis with Zero Trust policy.
        
        Base Score: 50 (Neutral/Unknown)
        Trust is EARNED via:
        - History longevity
        - Volume consistency
        
        Risk is DETECTED via:
        - Volume spikes (Z-Score)
        - Time anomalies
        - Free provider + New Sender
        """
        logger.debug(f"Checking behavioral anomalies for {from_address}")

        issues = []
        positive_signals = []
        
        # 1. Base Score: Zero Trust (Start Neutral/Suspicious)
        score = 50 
        
        # Query stats via Repository
        daily_stats = await self.repo.get_daily_volumes(from_address, days=90) # Look back 90 days
        daily_volumes = [count for _, count in daily_stats]
        total_emails = sum(daily_volumes)
        history_days = len(daily_volumes)
        
        # Current volume (last 24h)
        current_24h_vol = await self.repo.count_recent_emails(from_address, hours=24)

        # 2. Earn Trust (History & Consistency)
        # Check reputation quality
        reputation = await self.repo.get_sender_reputation_stats(from_address)
        avg_risk = reputation["avg_risk"]
        high_risk = reputation["high_risk_count"]
        
        # Only award trust if history is CLEAN (avg risk < 40)
        is_clean_history = avg_risk < 40
        
        if is_clean_history:
            if total_emails > 50:
                score += 20
                positive_signals.append(f"Established trusted sender ({total_emails} clean emails)")
            elif total_emails > 10:
                score += 10
                positive_signals.append(f"Known trusted sender ({total_emails} clean emails)")
                
            if history_days > 30:
                score += 15
                positive_signals.append(f"Long-term good standing ({history_days} days)")
            elif history_days > 7:
                score += 5
        else:
            # Persistent Threat Penalty
            if high_risk > 2 or avg_risk > 60:
                score -= 30
                issues.append(f"Persistent Threat: History contains {high_risk} high-risk emails (Avg Risk {avg_risk:.1f})")
            elif avg_risk > 40:
                issues.append(f"Suspicious History: Avg Risk {avg_risk:.1f}")

        # 3. Detect Anomalies (Volume Spikes)
        if len(daily_volumes) >= 5:
            import statistics
            try:
                mean = statistics.mean(daily_volumes)
                stdev = statistics.stdev(daily_volumes) if len(daily_volumes) > 1 else 0
                
                if stdev > 0:
                    z_score = (current_24h_vol - mean) / stdev
                    if z_score > 4:
                        issues.append(f"Critical volume spike (Z-Score {z_score:.1f})")
                        score -= 40
                    elif z_score > 3:
                        issues.append(f"Volume anomaly (Z-Score {z_score:.1f})")
                        score -= 20
                else:
                    # Logic for zero variance (stable sender suddenly spikes)
                    if current_24h_vol > mean * 5 and mean > 0:
                         issues.append(f"Sudden volume spike: {current_24h_vol} (avg {mean:.1f})")
                         score -= 30
            except Exception as e:
                logger.warning(f"Stats calculation error: {e}")

        # 4. Cold Start Penalty (New Sender)
        if total_emails < 5:
            score -= 10 # Start lower than 50
            issues.append("New sender (Cold Start)")
            
            # Check for Free Provider on New Sender
            from utils.email_validator import extract_domain_from_email
            from_domain = extract_domain_from_email(from_address)
            if from_domain:
                free_providers = ["gmail.com", "yahoo.com", "mail.ru", "yandex.ru", "outlook.com", 
                                "hotmail.com", "inbox.ru", "bk.ru", "list.ru", "rambler.ru"]
                if from_domain.lower() in free_providers:
                    issues.append(f"New sender using free provider: {from_domain}")
                    score -= 20 # Heavy penalty for fresh gmail accounts

        # 5. History Checks (Risk & Spam)
        recent_emails = await self.repo.get_recent_by_sender(from_address, days=30, limit=20)
        if recent_emails:
             high_risk_count = sum(1 for e in recent_emails if e.risk_score and e.risk_score > 70)
             if high_risk_count > 0:
                issues.append(f"{high_risk_count} recent high-risk emails")
                score -= 15 * min(high_risk_count, 3)

        # 6. Time-of-day analysis
        email_time = email_timestamp or datetime.utcnow()
        email_hour_msk = (email_time.hour + 3) % 24  # Convert to MSK
        
        if email_hour_msk >= 0 and email_hour_msk < 6:
            issues.append(f"Night activity ({email_hour_msk}:00 MSK)")
            score -= 10

        return {
            "score": max(0, min(100, score)), # Cap at 0-100
            "issues": issues,
            "positive_signals": positive_signals,
            "recent_email_count": total_emails,
            "emails_24h": current_24h_vol,
            "details": f"Behavioral Score: {score} (Zero Trust Model)"
        }
