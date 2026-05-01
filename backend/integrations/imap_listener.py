"""
IMAP Email Listener Service

Polls configured mailbox for new emails and sends them to the analysis API.
Supports Gmail, Outlook, Yandex, and other IMAP-compatible servers.

Usage:
  python -m integrations.imap_listener

Environment variables:
  IMAP_HOST, IMAP_PORT, IMAP_USER, IMAP_PASSWORD, IMAP_FOLDER,
  IMAP_POLL_INTERVAL, IMAP_USE_SSL, BACKEND_URL, API_SYSTEM_TOKEN
"""
import asyncio
import base64
import imaplib
import json
import logging
import os
import signal
import sys
import ssl
from email import policy
from email.parser import BytesParser
from typing import Dict, List, Optional

import httpx

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("imap_listener")


class IMAPListener:
    """IMAP email polling service."""

    def __init__(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        folder: str = "INBOX",
        use_ssl: bool = True,
        poll_interval: int = 60,
        backend_url: str = "http://backend:8000",
        api_token: str = "",
    ):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.folder = folder
        self.use_ssl = use_ssl
        self.poll_interval = poll_interval
        self.backend_url = backend_url.rstrip("/")
        self.api_token = api_token
        self.running = True
        self.mail: Optional[imaplib.IMAP4_SSL] = None

    def connect(self) -> bool:
        """Connect to IMAP server."""
        try:
            if self.use_ssl:
                context = ssl.create_default_context()
                self.mail = imaplib.IMAP4_SSL(self.host, self.port, ssl_context=context, timeout=30)
            else:
                self.mail = imaplib.IMAP4(self.host, self.port, timeout=30)
            
            self.mail.login(self.user, self.password)
            self.mail.select(self.folder)
            logger.info(f"Connected to {self.host}:{self.port} as {self.user}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to IMAP server: {e}")
            return False

    def disconnect(self):
        """Disconnect from IMAP server."""
        if self.mail:
            try:
                self.mail.logout()
            except Exception:
                pass
            self.mail = None

    def fetch_unseen_emails(self) -> List[bytes]:
        """Fetch all unseen emails from the mailbox."""
        emails: List[bytes] = []
        if not self.mail:
            return emails

        try:
            # Refresh mailbox state - Gmail IMAP requires this to see new emails
            self.mail.noop()  # Keep connection alive
            self.mail.select(self.folder)  # Re-select to refresh
            
            status, messages = self.mail.search(None, "UNSEEN")
            if status != "OK":
                return emails

            email_ids = messages[0].split()
            logger.info(f"Found {len(email_ids)} unseen email(s)")

            for email_id in email_ids:
                try:
                    status, msg_data = self.mail.fetch(email_id, "(RFC822)")
                    if status == "OK" and msg_data[0]:
                        raw_email = msg_data[0][1]
                        if isinstance(raw_email, bytes):
                            emails.append(raw_email)
                            # Mark as seen
                            self.mail.store(email_id, "+FLAGS", "\\Seen")
                except Exception as e:
                    logger.error(f"Error fetching email {email_id}: {e}")

        except Exception as e:
            logger.error(f"Error searching for unseen emails: {e}")

        return emails

    def parse_email(self, raw_email: bytes) -> Dict:
        """Parse raw email bytes into structured data."""
        try:
            msg = BytesParser(policy=policy.default).parsebytes(raw_email)
            headers = {k: msg.get(k, "") for k in msg.keys()}

            # Extract body
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        payload = part.get_payload(decode=True)
                        if payload:
                            charset = part.get_content_charset() or "utf-8"
                            body = payload.decode(charset, errors="ignore")
                            break
            else:
                payload = msg.get_payload(decode=True)
                if payload:
                    charset = msg.get_content_charset() or "utf-8"
                    body = payload.decode(charset, errors="ignore")

            return {
                "from_address": msg.get("From", ""),
                "to_address": msg.get("To", ""),
                "subject": msg.get("Subject", ""),
                "sender_ip": self._extract_sender_ip(headers),
                "headers": headers,
                "body": body,
                "raw_email": base64.b64encode(raw_email).decode("ascii"),
            }
        except Exception as e:
            logger.error(f"Failed to parse email: {e}")
            return {}

    def _extract_sender_ip(self, headers: Dict) -> str:
        """Extract sender IP from Received headers."""
        received = headers.get("Received", "")
        if isinstance(received, list):
            received = received[0] if received else ""
        
        # Simple extraction - look for IP in brackets
        import re
        match = re.search(r"\[(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\]", received)
        return match.group(1) if match else "0.0.0.0"

    async def send_to_analyzer(self, email_data: Dict) -> bool:
        """Send parsed email to analysis API."""
        if not email_data:
            return False

        url = f"{self.backend_url}/api/v1/analyze/headers"
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    url, headers=headers, content=json.dumps(email_data)
                )
                if resp.is_success:
                    logger.info(
                        f"Analyzed: {email_data.get('from_address')} → "
                        f"{email_data.get('to_address')} | Subject: {email_data.get('subject', '')[:50]}"
                    )
                    return True
                else:
                    logger.error(f"Analysis failed: {resp.status_code} {resp.text}")
                    return False
        except Exception as e:
            logger.error(f"HTTP error sending to analyzer: {e}")
            return False

    async def poll_once(self) -> int:
        """Poll mailbox once and process all new emails."""
        # BUG-25 fix: send heartbeat here too so gaps between run() cycles
        # don't cause missed heartbeats if poll_once takes longer than expected
        await self.send_heartbeat()

        if not self.mail:
            if not self.connect():
                return 0

        emails = self.fetch_unseen_emails()
        processed = 0

        for raw_email in emails:
            email_data = self.parse_email(raw_email)
            if email_data:
                logger.info(f"Submitting email for analysis: {email_data.get('subject')}")
                if await self.send_to_analyzer(email_data):
                    processed += 1
                else:
                    logger.error(f"Failed to submit email: {email_data.get('subject')}")

        return processed

    async def send_heartbeat(self):
        """Send heartbeat to backend."""
        try:
            url = f"{self.backend_url}/api/v1/system/heartbeat"
            headers = {
                "X-API-Token": self.api_token,
                "Content-Type": "application/json",
            }
            data = {
                "service_name": "imap-listener",
                "status": "online" if self.mail else "error",
                "timestamp": __import__("time").time(),
                "details": {
                    "folder": self.folder,
                    "ssl": self.use_ssl
                }
            }
            async with httpx.AsyncClient(timeout=10) as client:
                await client.post(url, headers=headers, json=data)
        except Exception as e:
            logger.error(f"Failed to send heartbeat: {e}")

    async def run(self):
        """Main polling loop with heartbeat."""
        logger.info(
            f"Starting IMAP listener: {self.host}:{self.port}/{self.folder} "
            f"(poll every {self.poll_interval}s)"
        )

        while self.running:
            try:
                # Send heartbeat
                await self.send_heartbeat()
                
                processed = await self.poll_once()
                if processed > 0:
                    logger.info(f"Processed {processed} email(s)")
            except Exception as e:
                logger.error(f"Error in poll cycle: {e}")
                self.disconnect()  # Force reconnect on next cycle

            await asyncio.sleep(self.poll_interval)

        self.disconnect()
        logger.info("IMAP listener stopped")

    def stop(self):
        """Stop the listener."""
        self.running = False


def main():
    """Entry point for IMAP listener service."""
    # Load configuration from environment
    host = os.getenv("IMAP_HOST", "imap.gmail.com")

    raw_port = os.getenv("IMAP_PORT", "993")
    # BUG-27 fix: wrap in try/except — bad IMAP_PORT crashes with cryptic ValueError
    try:
        port = int(raw_port)
    except ValueError:
        logger.error(f"Invalid IMAP_PORT value '{raw_port}' — must be an integer")
        sys.exit(1)

    user = os.getenv("IMAP_USER", "")
    password = os.getenv("IMAP_PASSWORD", "")
    folder = os.getenv("IMAP_FOLDER", "INBOX")
    use_ssl = os.getenv("IMAP_USE_SSL", "true").lower() == "true"
    poll_interval = int(os.getenv("IMAP_POLL_INTERVAL", "60"))
    backend_url = os.getenv("BACKEND_URL", "http://backend:8000")
    api_token = os.getenv("API_SYSTEM_TOKEN", "")

    if not user or not password:
        logger.error("IMAP_USER and IMAP_PASSWORD must be set")
        sys.exit(1)

    if not api_token:
        logger.error("API_SYSTEM_TOKEN must be set")
        sys.exit(1)

    listener = IMAPListener(
        host=host,
        port=port,
        user=user,
        password=password,
        folder=folder,
        use_ssl=use_ssl,
        poll_interval=poll_interval,
        backend_url=backend_url,
        api_token=api_token,
    )

    # Graceful shutdown
    def shutdown_handler(signum, frame):
        logger.info("Shutdown signal received")
        listener.stop()

    signal.signal(signal.SIGTERM, shutdown_handler)
    signal.signal(signal.SIGINT, shutdown_handler)

    # Run the listener
    asyncio.run(listener.run())


if __name__ == "__main__":
    main()
