"""
Celery tasks for syncing user mail accounts.

This module replaces the standalone imap-listener with dynamic per-user tasks.
Each user's connected mail account is synced independently.
"""
from celery import Task
from celery.utils.log import get_task_logger
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import imaplib
import ssl
import email
from email.header import decode_header
import asyncio
import redis as redis_sync
import os

from config.celery_config import celery_app
from database import AsyncSessionLocal, MailAccount, EmailAnalysis, engine
from utils.crypto import decrypt_password

logger = get_task_logger(__name__)

# Sync Redis client for Celery tasks (outside async context)
REDIS_URL_SYNC = os.getenv("REDIS_URL", "redis://localhost:6379/0")
_sync_redis = redis_sync.Redis.from_url(REDIS_URL_SYNC, decode_responses=True)
LOCK_TTL_SECONDS = 600  # 10 minutes — prevents concurrent syncs for same account


class MailSyncTask(Task):
    """Base task with async database session management"""

    def run_async(self, coro):
        """Run an async coroutine in sync context"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            try:
                # Dispose engine connections tied to this loop to prevent
                # "Future attached to a different loop" errors.
                # BUG-22 fix: check loop state before dispose.
                if loop.is_running():
                    loop.run_until_complete(engine.dispose())
            except RuntimeError:
                # Loop already closed — safe to ignore
                pass
            except Exception:
                pass
            finally:
                loop.close()

    # BUG-05 fix: distributed lock to prevent concurrent syncs
    def acquire_sync_lock(self, account_id: int) -> bool:
        """
        Attempt to acquire a distributed lock for the given account.
        Returns True if lock acquired, False if already locked.
        """
        lock_key = f"mail_sync:lock:{account_id}"
        acquired = _sync_redis.set(lock_key, "locked", nx=True, ex=LOCK_TTL_SECONDS)
        return bool(acquired)

    def release_sync_lock(self, account_id: int) -> None:
        """Release the distributed sync lock for the given account."""
        lock_key = f"mail_sync:lock:{account_id}"
        _sync_redis.delete(lock_key)


def decode_mime_header(header_value: str) -> str:
    """
    Decode MIME encoded header value.
    BUG-26 fix: tries utf-8 first, then falls back to windows-1251 / koi8-r
    (common in Russian government email systems) before replacing undecodable bytes.
    """
    if not header_value:
        return ""

    decoded_parts = []
    for part, encoding in decode_header(header_value):
        if isinstance(part, bytes):
            # Try declared encoding, then common Russian encodings
            for codec in (encoding, 'windows-1251', 'koi8-r', 'utf-8'):
                if not codec:
                    continue
                try:
                    decoded_parts.append(part.decode(codec, errors='strict'))
                    break
                except (UnicodeDecodeError, LookupError):
                    continue
            else:
                # Last resort: replace bad bytes instead of dropping content
                decoded_parts.append(part.decode('utf-8', errors='replace'))
        else:
            decoded_parts.append(part)
    return ''.join(decoded_parts)


def connect_imap(account: MailAccount, password: str) -> imaplib.IMAP4:
    """
    Establish IMAP connection to mail server.
    
    Returns:
        Connected IMAP4 instance
    """
    if account.imap_use_ssl:
        context = ssl.create_default_context()
        imap = imaplib.IMAP4_SSL(
            account.imap_server, 
            account.imap_port, 
            ssl_context=context
        )
    else:
        imap = imaplib.IMAP4(account.imap_server, account.imap_port)
    
    imap.login(account.username, password)
    return imap


def fetch_new_emails(imap: imaplib.IMAP4, folder: str, since_date: Optional[datetime] = None) -> List[Dict]:
    """
    Fetch new emails from mailbox.
    
    Args:
        imap: Connected IMAP instance
        folder: Folder name to fetch from
        since_date: Only fetch emails since this date
        
    Returns:
        List of email dictionaries
    """
    emails = []
    
    imap.select(folder)
    
    # Build search criteria
    if since_date:
        date_str = since_date.strftime("%d-%b-%Y")
        search_criteria = f'(SINCE {date_str})'
    else:
        # Default to last 7 days
        since = datetime.utcnow() - timedelta(days=7)
        date_str = since.strftime("%d-%b-%Y")
        search_criteria = f'(SINCE {date_str})'
    
    status, message_ids = imap.search(None, search_criteria)
    
    if status != "OK":
        logger.warning(f"IMAP search failed: {status}")
        return emails
    
    message_id_list = message_ids[0].split()
    
    # Limit to most recent messages
    max_messages = 50
    message_id_list = message_id_list[-max_messages:]
    
    for msg_id in message_id_list:
        try:
            status, msg_data = imap.fetch(msg_id, "(RFC822)")
            if status != "OK":
                continue
            
            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)
            
            # Extract headers
            message_id = msg.get("Message-ID", "")
            from_addr = decode_mime_header(msg.get("From", ""))
            to_addr = decode_mime_header(msg.get("To", ""))
            subject = decode_mime_header(msg.get("Subject", ""))
            date_str = msg.get("Date", "")
            
            # Extract body preview
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    if content_type == "text/plain":
                        payload = part.get_payload(decode=True)
                        if payload:
                            body = payload.decode('utf-8', errors='replace')[:500]
                            break
            else:
                payload = msg.get_payload(decode=True)
                if payload:
                    body = payload.decode('utf-8', errors='replace')[:500]
            
            # Build raw headers dict
            raw_headers = {
                key: decode_mime_header(value) 
                for key, value in msg.items()
            }
            
            emails.append({
                "message_id": message_id,
                "from_address": from_addr,
                "to_address": to_addr,
                "subject": subject,
                "body_preview": body[:200],
                "body_text": body,
                "raw_headers": raw_headers,
                "date": date_str,
            })
            
        except Exception as e:
            logger.error(f"Failed to parse email {msg_id}: {e}")
            continue
    
    return emails


@celery_app.task(
    bind=True,
    base=MailSyncTask,
    name="tasks.mail_sync.sync_user_mailbox",
    max_retries=3,
    default_retry_delay=60
)
def sync_user_mailbox(self, account_id: int) -> Dict:
    """
    Sync a single user's mail account.

    This task fetches new emails from the user's connected IMAP account,
    runs them through the analysis pipeline, and stores results.

    BUG-05 fix: uses distributed Redis lock to prevent concurrent syncs
    and duplicate processing on Celery task retry.

    Args:
        account_id: ID of the MailAccount to sync

    Returns:
        Dict with sync results
    """
    # BUG-05 fix: acquire distributed lock before doing any work
    if not self.acquire_sync_lock(account_id):
        logger.warning(f"Account {account_id} is already being synced — skipping (idempotency)")
        return {"skipped": True, "reason": "already_syncing", "account_id": account_id}

    try:
        async def _sync():
            async with AsyncSessionLocal() as db:
                from sqlalchemy import select

                # Get account
                result = await db.execute(
                    select(MailAccount).where(MailAccount.id == account_id)
                )
                account = result.scalar_one_or_none()

                if not account:
                    logger.error(f"Mail account {account_id} not found")
                    return {"error": "Account not found", "account_id": account_id}

                if not account.is_active:
                    logger.info(f"Mail account {account_id} is inactive, skipping")
                    return {"skipped": True, "reason": "inactive", "account_id": account_id}

                try:
                    # Decrypt password
                    password = decrypt_password(account.encrypted_password)

                    # Connect to IMAP
                    logger.info(f"Connecting to {account.imap_server} for account {account.email}")
                    imap = connect_imap(account, password)

                    # Update status
                    account.status = "syncing"
                    await db.commit()

                    # Fetch new emails
                    since_date = account.last_sync_at or (datetime.utcnow() - timedelta(days=7))
                    emails = fetch_new_emails(imap, account.folder, since_date)

                    imap.logout()

                    logger.info(f"Fetched {len(emails)} emails from {account.email}")

                    # Process each email
                    new_count = 0
                    for email_data in emails:
                        # Check if already processed (idempotency at DB level)
                        existing = await db.execute(
                            select(EmailAnalysis).where(
                                EmailAnalysis.message_id == email_data["message_id"],
                                EmailAnalysis.user_id == account.user_id
                            )
                        )
                        if existing.scalars().first():
                            continue

                        # Create analysis record
                        analysis = EmailAnalysis(
                            message_id=email_data["message_id"],
                            user_id=account.user_id,
                            mail_account_id=account.id,
                            from_address=email_data["from_address"],
                            to_address=email_data["to_address"],
                            subject=email_data["subject"],
                            body_preview=email_data["body_preview"],
                            body_text=email_data["body_text"],
                            raw_headers=email_data["raw_headers"],
                            status="pending",
                            risk_score=0.0,
                        )
                        db.add(analysis)
                        await db.flush()
                        new_count += 1

                        # Queue analysis task
                        from tasks.analysis_tasks import analyze_email_task
                        analyze_email_task.delay(analysis.id)

                    # Update account status
                    account.status = "connected"
                    account.last_sync_at = datetime.utcnow()
                    account.total_emails_synced += new_count
                    account.last_error = None

                    await db.commit()

                    return {
                        "success": True,
                        "account_id": account_id,
                        "email": account.email,
                        "fetched": len(emails),
                        "new": new_count
                    }

                except imaplib.IMAP4.error as e:
                    error_msg = str(e)
                    logger.error(f"IMAP error for {account.email}: {error_msg}")

                    account.status = "auth_error" if "AUTHENTICATION" in error_msg.upper() else "error"
                    account.last_error = error_msg
                    await db.commit()

                    return {"error": error_msg, "account_id": account_id}

                except Exception as e:
                    logger.error(f"Sync error for {account.email}: {e}", exc_info=True)

                    account.status = "error"
                    account.last_error = str(e)
                    await db.commit()

                    # Retry on transient errors
                    raise self.retry(exc=e)

        return self.run_async(_sync())
    finally:
        # BUG-05 fix: always release lock, even on retry/exceptions
        self.release_sync_lock(account_id)


@celery_app.task(
    name="tasks.mail_sync.monitor_all_accounts",
)
def monitor_all_accounts() -> Dict:
    """
    Scheduler task: Check all active mail accounts and queue sync tasks.
    
    Runs periodically (e.g., every 5 minutes) via Celery Beat.
    Respects individual account sync_interval_minutes settings.
    """
    async def _monitor():
        async with AsyncSessionLocal() as db:
            from sqlalchemy import select, and_
            
            # Find accounts due for sync
            now = datetime.utcnow()
            
            # 1. Reset stuck 'syncing' accounts (older than 30 mins)
            stuck_threshold = now - timedelta(minutes=30)
            stuck_result = await db.execute(
                select(MailAccount).where(
                    and_(
                        MailAccount.status == "syncing",
                        MailAccount.updated_at < stuck_threshold
                    )
                )
            )
            stuck_accounts = stuck_result.scalars().all()
            
            for acc in stuck_accounts:
                logger.warning(f"Resetting STUCK sync for account {acc.id} ({acc.email})")
                acc.status = "error"
                acc.last_error = "Sync timed out (stuck state)"
                acc.updated_at = now
            
            if stuck_accounts:
                await db.commit()

            # 2. Find accounts due for sync (excluding those currently syncing)
            result = await db.execute(
                select(MailAccount).where(
                    and_(
                        MailAccount.is_active == True,
                        MailAccount.status.in_(["connected", "pending", "error"]) 
                    )
                )
            )
            accounts = result.scalars().all()
            
            queued = 0
            for account in accounts:
                # Check if sync is due
                if account.last_sync_at:
                    next_sync = account.last_sync_at + timedelta(minutes=account.sync_interval_minutes)
                    if now < next_sync:
                        continue
                
                # Check if recently updated (backoff for errors)
                if account.status == "error" and account.updated_at:
                     # Wait at least 5 mins before retrying error
                     if now < account.updated_at + timedelta(minutes=5):
                         continue

                # Set status to syncing immediately to prevent double-make.
                # BUG-06 fix: Distributed lock (BUG-05) handles race condition, so this is safe.
                account.status = "syncing"
                account.updated_at = now
                await db.commit()

                # Queue sync task
                sync_user_mailbox.delay(account.id)
                queued += 1
                logger.info(f"Queued sync for account {account.id} ({account.email})")
            
            if queued > 0:
                await db.commit()
            
            return {
                "checked": len(accounts),
                "queued": queued,
                "resetted_stuck": len(stuck_accounts),
                "timestamp": now.isoformat()
            }
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_monitor())
    finally:
        try:
            # Dispose engine connections tied to this loop to prevent
            # "Future attached to a different loop" errors.
            # BUG-22 fix: ensure loop is still running before dispose.
            if loop.is_running():
                loop.run_until_complete(engine.dispose())
        except RuntimeError as e:
            # Loop may already be closed — safe to ignore
            logger.debug(f"engine.dispose() skipped (loop state): {e}")
        except Exception:
            pass
        finally:
            loop.close()
