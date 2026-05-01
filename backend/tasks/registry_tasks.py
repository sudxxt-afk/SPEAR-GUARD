from celery import Task
from celery.utils.log import get_task_logger
from typing import List, Dict, Tuple, Optional
import asyncio

from config.celery_config import celery_app
from services.registry_auto_populator import RegistryAutoPopulator
from integrations.active_directory import ActiveDirectoryIntegration, EGRULIntegration
from services.registry_service import RegistryService
from schemas.registry import TrustLevel
from database import TrustedRegistry, AsyncSessionLocal

logger = get_task_logger(__name__)


class DatabaseTask(Task):
    """Base task with database session management"""

    def __init__(self):
        self._session = None


@celery_app.task(bind=True, base=DatabaseTask, name="tasks.registry_tasks.auto_populate_registry_task")
def auto_populate_registry_task(
    self,
    months_back: int = 6,
    min_emails: int = 10,
    min_reply_rate: float = 30.0,
    dry_run: bool = False
) -> Dict:
    """
    Automatically populate registry from historical email analysis

    Runs daily at 02:00 Moscow time

    Args:
        months_back: Months of history to analyze
        min_emails: Minimum emails required
        min_reply_rate: Minimum reply rate percentage
        dry_run: If True, don't actually add to registry

    Returns:
        Dict with task results
    """
    logger.info(
        f"Starting auto-populate task: months_back={months_back}, "
        f"min_emails={min_emails}, min_reply_rate={min_reply_rate}, dry_run={dry_run}"
    )

    async def _run_task():
        async with AsyncSessionLocal() as session:
            try:
                populator = RegistryAutoPopulator(session)

                added_count, skipped_count, added_emails = await populator.auto_populate_from_history(
                    months_back=months_back,
                    min_emails=min_emails,
                    min_reply_rate=min_reply_rate,
                    dry_run=dry_run
                )

                result = {
                    "status": "success",
                    "added_count": added_count,
                    "skipped_count": skipped_count,
                    "added_emails": added_emails,
                    "dry_run": dry_run
                }

                logger.info(
                    f"Auto-populate task completed: {added_count} added, "
                    f"{skipped_count} skipped (dry_run={dry_run})"
                )

                return result

            except Exception as e:
                logger.error(f"Error in auto-populate task: {e}", exc_info=True)
                return {
                    "status": "error",
                    "error": str(e),
                    "added_count": 0,
                    "skipped_count": 0
                }

    # Run async task
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(_run_task())


@celery_app.task(bind=True, base=DatabaseTask, name="tasks.registry_tasks.update_trust_scores_task")
def update_trust_scores_task(self) -> Dict:
    """
    Recalculate trust scores for existing registry entries

    Runs daily at 03:00 Moscow time

    Returns:
        Dict with task results
    """
    logger.info("Starting trust score update task")

    async def _run_task():
        async with AsyncSessionLocal() as session:
            try:
                populator = RegistryAutoPopulator(session)
                updated_count = await populator.update_trust_scores()

                result = {
                    "status": "success",
                    "updated_count": updated_count
                }

                logger.info(f"Trust score update completed: {updated_count} entries updated")
                return result

            except Exception as e:
                logger.error(f"Error in trust score update task: {e}", exc_info=True)
                return {
                    "status": "error",
                    "error": str(e),
                    "updated_count": 0
                }

    loop = asyncio.get_event_loop()
    return loop.run_until_complete(_run_task())


@celery_app.task(bind=True, base=DatabaseTask, name="tasks.registry_tasks.import_from_ad_task")
def import_from_ad_task(
    self,
    organizations: Optional[List[str]] = None,
    dry_run: bool = False
) -> Dict:
    """
    Import government employee emails from Active Directory

    Runs weekly on Monday at 01:00 Moscow time

    Args:
        organizations: List of organization names to filter by
        dry_run: If True, don't actually add to registry

    Returns:
        Dict with task results
    """
    logger.info(f"Starting AD import task: organizations={organizations}, dry_run={dry_run}")

    async def _run_task():
        async with AsyncSessionLocal() as session:
            try:
                # Initialize AD integration
                ad_integration = ActiveDirectoryIntegration()
                await ad_integration.connect()

                # Import government emails
                registry_data = await ad_integration.import_government_emails(organizations)

                logger.info(f"Retrieved {len(registry_data)} entries from Active Directory")

                added_count = 0
                skipped_count = 0
                added_emails = []

                for entry in registry_data:
                    email = entry['email_address']

                    # Check if already exists
                    existing = await RegistryService.get_by_email(session, email)
                    if existing:
                        logger.debug(f"Skipping {email} - already in registry")
                        skipped_count += 1
                        continue

                    if dry_run:
                        logger.info(f"[DRY RUN] Would add {email} from AD")
                        added_count += 1
                        added_emails.append(email)
                    else:
                        # Add to registry with HIGH_TRUST level for government employees
                        try:
                            new_entry = TrustedRegistry(
                                email_address=email,
                                domain=entry['domain'],
                                organization_name=entry['organization_name'],
                                trust_level=TrustLevel.HIGH_TRUST.value,
                                added_by=None,  # Automatic addition
                                approved_by=None,
                                is_verified=True,  # AD entries auto-verified
                                is_active=True,
                                status='active',
                                notes=f"Imported from Active Directory: {entry['full_name']}, {entry['title']}"
                            )

                            session.add(new_entry)
                            # BUG-12 fix: batch commit after loop instead of per-entry commit

                        except Exception as e:
                            logger.error(f"Error adding {email}: {e}")
                            skipped_count += 1

                # BUG-12 fix: single commit for all entries
                await session.commit()

                await ad_integration.disconnect()

                result = {
                    "status": "success",
                    "source": "active_directory",
                    "added_count": added_count,
                    "skipped_count": skipped_count,
                    "added_emails": added_emails,
                    "dry_run": dry_run
                }

                logger.info(
                    f"AD import completed: {added_count} added, {skipped_count} skipped "
                    f"(dry_run={dry_run})"
                )

                return result

            except Exception as e:
                logger.error(f"Error in AD import task: {e}", exc_info=True)
                return {
                    "status": "error",
                    "error": str(e),
                    "added_count": 0,
                    "skipped_count": 0
                }

    loop = asyncio.get_event_loop()
    return loop.run_until_complete(_run_task())


@celery_app.task(bind=True, base=DatabaseTask, name="tasks.registry_tasks.import_from_egrul_task")
def import_from_egrul_task(
    self,
    min_contract_count: int = 5,
    dry_run: bool = False
) -> Dict:
    """
    Import contractor emails from EGRUL (Russian business registry)

    Runs monthly on the 1st day at 01:00 Moscow time

    Args:
        min_contract_count: Minimum number of government contracts
        dry_run: If True, don't actually add to registry

    Returns:
        Dict with task results
    """
    logger.info(f"Starting EGRUL import task: min_contract_count={min_contract_count}, dry_run={dry_run}")

    async def _run_task():
        async with AsyncSessionLocal() as session:
            try:
                # Initialize EGRUL integration
                egrul_integration = EGRULIntegration()

                # Import contractor emails
                registry_data = await egrul_integration.import_contractor_emails(min_contract_count)

                logger.info(f"Retrieved {len(registry_data)} contractor entries from EGRUL")

                added_count = 0
                skipped_count = 0
                added_emails = []

                for entry in registry_data:
                    email = entry['email_address']

                    # BUG-13 fix: skip group email addresses (shared inboxes)
                    group_patterns = ('@noreply', '@no-reply', '@do-not-reply', '@contact@', '@support@', '@info@', '@admin@')
                    if email.lower().startswith(group_patterns):
                        logger.debug(f"Skipping {email} - appears to be a group/shared address")
                        skipped_count += 1
                        continue

                    # Check if already exists
                    existing = await RegistryService.get_by_email(session, email)
                    if existing:
                        logger.debug(f"Skipping {email} - already in registry")
                        skipped_count += 1
                        continue

                    if dry_run:
                        logger.info(f"[DRY RUN] Would add {email} from EGRUL")
                        added_count += 1
                        added_emails.append(email)
                    else:
                        # Add to registry with MEDIUM_TRUST for contractors
                        try:
                            new_entry = TrustedRegistry(
                                email_address=email,
                                domain=entry['domain'],
                                organization_name=entry['organization_name'],
                                trust_level=TrustLevel.MEDIUM_TRUST.value,
                                added_by=None,  # Automatic addition
                                approved_by=None,
                                is_verified=False,  # EGRUL entries need verification
                                is_active=True,
                                status='pending',  # Pending verification
                                notes=f"Imported from EGRUL: INN {entry['inn']}, {entry['contract_count']} contracts"
                            )

                            session.add(new_entry)
                            # BUG-12 fix: batch commit after loop instead of per-entry commit

                        except Exception as e:
                            logger.error(f"Error adding {email}: {e}")
                            skipped_count += 1

                # BUG-12 fix: single commit for all entries
                await session.commit()

                # Count actual additions after commit (BUG-12: batch commit)
                def _is_group_email(email: str) -> bool:
                    return email.lower().startswith(('@noreply', '@no-reply', '@do-not-reply', '@contact@', '@support@', '@info@', '@admin@'))
                added_count = sum(
                    1 for e in registry_data
                    if not dry_run
                    and not _is_group_email(e['email_address'])
                    and not RegistryService.get_by_email(session, e['email_address'])
                ) or added_count

                result = {
                    "status": "success",
                    "source": "egrul",
                    "added_count": added_count,
                    "skipped_count": skipped_count,
                    "added_emails": added_emails,
                    "dry_run": dry_run
                }

                logger.info(
                    f"EGRUL import completed: {added_count} added, {skipped_count} skipped "
                    f"(dry_run={dry_run})"
                )

                return result

            except Exception as e:
                logger.error(f"Error in EGRUL import task: {e}", exc_info=True)
                return {
                    "status": "error",
                    "error": str(e),
                    "added_count": 0,
                    "skipped_count": 0
                }

    loop = asyncio.get_event_loop()
    return loop.run_until_complete(_run_task())


# Manual trigger tasks (for testing and immediate execution)

@celery_app.task(name="tasks.registry_tasks.trigger_manual_import")
def trigger_manual_import(
    source: str = "all",
    dry_run: bool = True
) -> Dict:
    """
    Manually trigger registry import from all sources

    Args:
        source: 'all', 'history', 'ad', or 'egrul'
        dry_run: If True, don't actually add to registry

    Returns:
        Dict with combined results
    """
    logger.info(f"Manual import triggered: source={source}, dry_run={dry_run}")

    results = {
        "source": source,
        "dry_run": dry_run,
        "tasks": {}
    }

    if source in ["all", "history"]:
        logger.info("Running auto-populate from history...")
        result = auto_populate_registry_task.apply(
            kwargs={"dry_run": dry_run}
        ).get()
        results["tasks"]["history"] = result

    if source in ["all", "ad"]:
        logger.info("Running AD import...")
        result = import_from_ad_task.apply(
            kwargs={"dry_run": dry_run}
        ).get()
        results["tasks"]["ad"] = result

    if source in ["all", "egrul"]:
        logger.info("Running EGRUL import...")
        result = import_from_egrul_task.apply(
            kwargs={"dry_run": dry_run}
        ).get()
        results["tasks"]["egrul"] = result

    # Calculate totals
    total_added = sum(
        task_result.get("added_count", 0)
        for task_result in results["tasks"].values()
    )
    total_skipped = sum(
        task_result.get("skipped_count", 0)
        for task_result in results["tasks"].values()
    )

    results["total_added"] = total_added
    results["total_skipped"] = total_skipped

    logger.info(
        f"Manual import completed: {total_added} total added, "
        f"{total_skipped} total skipped (dry_run={dry_run})"
    )

    return results
