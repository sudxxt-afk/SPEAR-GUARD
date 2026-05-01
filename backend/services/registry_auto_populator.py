from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import logging

from database import EmailAnalysis, TrustedRegistry
from schemas.registry import TrustLevel
from services.registry_service import RegistryService

logger = logging.getLogger(__name__)


class EmailStatistics:
    """Statistics for an email sender"""
    def __init__(self, email: str):
        self.email = email
        self.domain = email.split('@')[1] if '@' in email else ''
        self.total_emails = 0
        self.spam_count = 0
        self.reply_count = 0
        self.first_email_date: Optional[datetime] = None
        self.last_email_date: Optional[datetime] = None
        self.average_risk_score = 0.0
        self.recipients: set = set()

    @property
    def reply_rate(self) -> float:
        """Calculate reply rate percentage"""
        return (self.reply_count / self.total_emails * 100) if self.total_emails > 0 else 0

    @property
    def spam_rate(self) -> float:
        """Calculate spam rate percentage"""
        return (self.spam_count / self.total_emails * 100) if self.total_emails > 0 else 0

    @property
    def duration_months(self) -> float:
        """Calculate communication duration in months"""
        if not self.first_email_date or not self.last_email_date:
            return 0
        delta = self.last_email_date - self.first_email_date
        return delta.days / 30.0

    def meets_criteria(self, min_emails: int = 10, min_duration_months: float = 6.0,
                       min_reply_rate: float = 30.0, max_spam_rate: float = 10.0) -> bool:
        """Check if sender meets auto-addition criteria"""
        return (
            self.total_emails >= min_emails and
            self.duration_months >= min_duration_months and
            self.reply_rate >= min_reply_rate and
            self.spam_rate <= max_spam_rate and
            self.average_risk_score < 50.0
        )


class RegistryAutoPopulator:
    """Service for automatic registry population"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def analyze_historical_emails(
        self,
        months_back: int = 6,
        min_emails: int = 10
    ) -> List[EmailStatistics]:
        """
        Analyze historical emails to identify potential trusted senders

        Args:
            months_back: How many months back to analyze
            min_emails: Minimum number of emails required

        Returns:
            List of email statistics for senders meeting minimum criteria
        """
        logger.info(f"Analyzing historical emails from last {months_back} months")

        cutoff_date = datetime.utcnow() - timedelta(days=30 * months_back)

        # Query all emails from the period
        query = select(EmailAnalysis).where(
            EmailAnalysis.analyzed_at >= cutoff_date
        ).order_by(EmailAnalysis.from_address, EmailAnalysis.analyzed_at)

        result = await self.db.execute(query)
        emails = result.scalars().all()

        # Aggregate statistics by sender
        stats_by_sender: Dict[str, EmailStatistics] = {}

        for email in emails:
            sender = email.from_address.lower()

            if sender not in stats_by_sender:
                stats_by_sender[sender] = EmailStatistics(sender)

            stats = stats_by_sender[sender]
            stats.total_emails += 1

            # Track dates
            if stats.first_email_date is None or email.analyzed_at < stats.first_email_date:
                stats.first_email_date = email.analyzed_at
            if stats.last_email_date is None or email.analyzed_at > stats.last_email_date:
                stats.last_email_date = email.analyzed_at

            # Track spam
            if email.status in ['danger', 'blocked']:
                stats.spam_count += 1

            # Track recipients
            if email.to_address:
                stats.recipients.add(email.to_address)

            # Aggregate risk scores
            if email.risk_score is not None:
                stats.average_risk_score = (
                    (stats.average_risk_score * (stats.total_emails - 1) + email.risk_score)
                    / stats.total_emails
                )

        # Filter senders meeting minimum criteria
        qualified_senders = [
            stats for stats in stats_by_sender.values()
            if stats.total_emails >= min_emails
        ]

        logger.info(
            f"Found {len(qualified_senders)} senders with at least {min_emails} emails "
            f"from {len(stats_by_sender)} total unique senders"
        )

        return qualified_senders

    def calculate_trust_level(self, stats: EmailStatistics) -> TrustLevel:
        """
        Calculate trust level based on email statistics

        Trust Level calculation:
        - Level 1 (MAX_TRUST): 50+ emails, 6+ months, 60%+ reply rate, <1% spam
        - Level 2 (HIGH_TRUST): 30+ emails, 6+ months, 40%+ reply rate, <5% spam
        - Level 3 (MEDIUM_TRUST): 20+ emails, 6+ months, 30%+ reply rate, <10% spam
        - Level 4 (LOW_TRUST): 10+ emails, 6+ months, 30%+ reply rate, <10% spam
        """
        score = 0

        # Email volume score (0-30 points)
        if stats.total_emails >= 50:
            score += 30
        elif stats.total_emails >= 30:
            score += 20
        elif stats.total_emails >= 20:
            score += 10
        elif stats.total_emails >= 10:
            score += 5

        # Duration score (0-20 points)
        if stats.duration_months >= 12:
            score += 20
        elif stats.duration_months >= 6:
            score += 10
        elif stats.duration_months >= 3:
            score += 5

        # Reply rate score (0-30 points)
        if stats.reply_rate >= 60:
            score += 30
        elif stats.reply_rate >= 40:
            score += 20
        elif stats.reply_rate >= 30:
            score += 10

        # Spam rate penalty (0-20 points)
        if stats.spam_rate < 1:
            score += 20
        elif stats.spam_rate < 5:
            score += 10
        elif stats.spam_rate < 10:
            score += 5

        # Risk score bonus (0-10 points)
        if stats.average_risk_score < 20:
            score += 10
        elif stats.average_risk_score < 30:
            score += 5

        # Map score to trust level
        if score >= 80:
            return TrustLevel.MAX_TRUST
        elif score >= 60:
            return TrustLevel.HIGH_TRUST
        elif score >= 40:
            return TrustLevel.MEDIUM_TRUST
        else:
            return TrustLevel.LOW_TRUST

    async def auto_populate_from_history(
        self,
        months_back: int = 6,
        min_emails: int = 10,
        min_reply_rate: float = 30.0,
        dry_run: bool = False
    ) -> Tuple[int, int, List[str]]:
        """
        Automatically populate registry from historical email analysis

        Args:
            months_back: Months of history to analyze
            min_emails: Minimum emails required
            min_reply_rate: Minimum reply rate percentage
            dry_run: If True, don't actually add to registry

        Returns:
            Tuple of (added_count, skipped_count, added_emails)
        """
        logger.info("Starting automatic registry population from email history")

        # Analyze historical emails
        candidates = await self.analyze_historical_emails(months_back, min_emails)

        added_count = 0
        skipped_count = 0
        added_emails = []

        for stats in candidates:
            # Check if meets all criteria
            if not stats.meets_criteria(
                min_emails=min_emails,
                min_duration_months=months_back,
                min_reply_rate=min_reply_rate
            ):
                skipped_count += 1
                continue

            # Check if already in registry
            existing = await RegistryService.get_by_email(self.db, stats.email)
            if existing:
                logger.debug(f"Skipping {stats.email} - already in registry")
                skipped_count += 1
                continue

            # Calculate trust level
            trust_level = self.calculate_trust_level(stats)

            if dry_run:
                logger.info(
                    f"[DRY RUN] Would add {stats.email} with trust level {trust_level.value} "
                    f"(emails: {stats.total_emails}, reply rate: {stats.reply_rate:.1f}%, "
                    f"spam rate: {stats.spam_rate:.1f}%)"
                )
                added_count += 1
                added_emails.append(stats.email)
            else:
                # Add to registry
                try:
                    new_entry = TrustedRegistry(
                        email_address=stats.email,
                        domain=stats.domain,
                        organization_name=None,  # Will be filled later if available
                        trust_level=trust_level.value,
                        added_by=None,  # Automatic addition
                        approved_by=None,  # Requires manual approval
                        is_verified=False,  # Auto-added entries need verification
                        is_active=True,
                        status='pending',
                        total_emails=stats.total_emails,
                        last_email_at=stats.last_email_date,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow()
                    )

                    self.db.add(new_entry)
                    await self.db.commit()

                    added_count += 1
                    added_emails.append(stats.email)

                    logger.info(
                        f"Auto-added {stats.email} to registry with trust level {trust_level.value} "
                        f"(emails: {stats.total_emails}, reply rate: {stats.reply_rate:.1f}%, "
                        f"duration: {stats.duration_months:.1f} months)"
                    )

                except Exception as e:
                    logger.error(f"Error adding {stats.email} to registry: {e}")
                    skipped_count += 1

        logger.info(
            f"Auto-population complete: {added_count} added, {skipped_count} skipped "
            f"from {len(candidates)} candidates"
        )

        return added_count, skipped_count, added_emails

    async def update_trust_scores(self) -> int:
        """
        Recalculate trust scores for existing registry entries based on recent activity

        Returns:
            Number of entries updated
        """
        logger.info("Starting trust score update for existing registry entries")

        # Get all active registry entries
        query = select(TrustedRegistry).where(TrustedRegistry.is_active == True)
        result = await self.db.execute(query)
        entries = result.scalars().all()

        updated_count = 0

        for entry in entries:
            # Analyze recent emails from this sender
            recent_stats = await self._get_sender_statistics(entry.email_address)

            if recent_stats and recent_stats.total_emails > 0:
                # Recalculate trust level
                new_trust_level = self.calculate_trust_level(recent_stats)

                # Update if changed
                if new_trust_level.value != entry.trust_level:
                    old_level = entry.trust_level
                    entry.trust_level = new_trust_level.value
                    entry.updated_at = datetime.utcnow()

                    updated_count += 1

                    logger.info(
                        f"Updated trust level for {entry.email_address}: "
                        f"{old_level} -> {new_trust_level.value}"
                    )

        if updated_count > 0:
            await self.db.commit()

        logger.info(f"Trust score update complete: {updated_count} entries updated")

        return updated_count

    async def _get_sender_statistics(
        self,
        email: str,
        months_back: int = 6
    ) -> Optional[EmailStatistics]:
        """Get statistics for a specific sender"""
        cutoff_date = datetime.utcnow() - timedelta(days=30 * months_back)

        query = select(EmailAnalysis).where(
            and_(
                EmailAnalysis.from_address == email.lower(),
                EmailAnalysis.analyzed_at >= cutoff_date
            )
        )

        result = await self.db.execute(query)
        emails = result.scalars().all()

        if not emails:
            return None

        stats = EmailStatistics(email)

        for email_record in emails:
            stats.total_emails += 1

            if stats.first_email_date is None or email_record.analyzed_at < stats.first_email_date:
                stats.first_email_date = email_record.analyzed_at
            if stats.last_email_date is None or email_record.analyzed_at > stats.last_email_date:
                stats.last_email_date = email_record.analyzed_at

            if email_record.status in ['danger', 'blocked']:
                stats.spam_count += 1

            if email_record.to_address:
                stats.recipients.add(email_record.to_address)

            if email_record.risk_score is not None:
                stats.average_risk_score = (
                    (stats.average_risk_score * (stats.total_emails - 1) + email_record.risk_score)
                    / stats.total_emails
                )

        return stats
