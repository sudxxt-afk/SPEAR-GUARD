"""
Lightweight SMTP listener that receives email copies and forwards them to the analysis API.

Flow:
1) Accept SMTP on a configurable port (default 2525).
2) Parse EML, collect headers/body and peer IP.
3) POST to /api/v1/analyze/headers with Bearer token.

Usage:
  python -m integrations.smtp_listener --port 2525 --backend-url http://backend:8000 --api-token <token>
  # For local dev:
  python -m integrations.smtp_listener --port 2525 --backend-url http://localhost:8000 --api-token <token>
"""
import argparse
import asyncio
import base64
import time
import json
import logging
from email import policy
from email.parser import BytesParser
from typing import Dict, Optional

import httpx
from aiosmtpd.controller import Controller
from aiosmtpd.handlers import AsyncMessage

logger = logging.getLogger("smtp_listener")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def extract_body(message) -> str:
    """Extract plain-text body from email message."""
    if message.is_multipart():
        for part in message.walk():
            if part.get_content_type() == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    try:
                        return payload.decode(part.get_content_charset() or "utf-8", errors="ignore")
                    except Exception:
                        return payload.decode("utf-8", errors="ignore")
    else:
        payload = message.get_payload(decode=True)
        if payload:
            try:
                return payload.decode(message.get_content_charset() or "utf-8", errors="ignore")
            except Exception:
                return payload.decode("utf-8", errors="ignore")
    return ""


class AnalysisHandler(AsyncMessage):
    def __init__(self, backend_url: str, api_token: str):
        super().__init__()
        self.backend_url = backend_url.rstrip("/")
        self.api_token = api_token

    async def send_to_analyzer(self, payload: Dict):
        """Forward parsed email payload to the analysis API."""
        url = f"{self.backend_url}/api/v1/analyze/headers"
        headers_req = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(url, headers=headers_req, content=json.dumps(payload))
                if resp.is_success:
                    logger.info(
                        f"Analyzed email from {payload['from_address']} -> {payload['to_address']}: {resp.status_code}"
                    )
                else:
                    logger.error(f"Analysis failed: {resp.status_code} {resp.text}")
        except Exception as e:
            logger.error(f"HTTP error posting to analyzer: {e}")

    async def handle_DATA(self, server, session, envelope):
        """Handle incoming email data (aiosmtpd entry point)."""
        try:
            peer = session.peer
            mail_from = envelope.mail_from
            rcpt_tos = envelope.rcpt_tos
            data = envelope.content  # bytes

            logger.info(f"Received message from {peer} ({mail_from}) -> {rcpt_tos}")

            sender_ip = peer[0] if peer else "0.0.0.0"

            try:
                parsed = BytesParser(policy=policy.default).parsebytes(data)
            except Exception as e:
                logger.error(f"Failed to parse email: {e}")
                return "500 Internal Error"

            headers: Dict[str, str] = {k: parsed.get(k, "") for k in parsed.keys()}
            body_text = extract_body(parsed)

            payload = {
                "from_address": parsed.get("From", ""),
                "to_address": parsed.get("To", ""),
                "subject": parsed.get("Subject", ""),
                "sender_ip": sender_ip,
                "headers": headers,
                "body": body_text,
                "raw_email": base64.b64encode(data).decode("ascii"),
            }

            # BUG-02 FIX: send_to_analyzer was never called — now it is
            await self.send_to_analyzer(payload)

            return "250 Message accepted for delivery"
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return "500 Internal Error"


async def heartbeat_loop(backend_url: str, api_token: str, port: int):
    """Background task to send heartbeats."""
    import socket

    logger.info("Heartbeat loop started")
    while True:
        try:
            # BUG-08 FIX: actually check if the SMTP port is open before reporting "online"
            status = "offline"
            try:
                with socket.create_connection(("localhost", port), timeout=2):
                    status = "online"
            except Exception:
                pass

            url = f"{backend_url}/api/v1/system/heartbeat"
            headers = {
                "X-API-Token": api_token,
                "Content-Type": "application/json",
            }
            data = {
                "service_name": "smtp-listener",
                "status": status,
                "timestamp": time.time(),
                "details": {
                    "port": port,
                }
            }
            async with httpx.AsyncClient(timeout=10) as client:
                await client.post(url, headers=headers, json=data)

        except Exception as e:
            logger.error(f"Failed to send heartbeat: {e}")

        await asyncio.sleep(60)


def main():

    parser = argparse.ArgumentParser(description="SMTP Listener for Email Analysis")
    parser.add_argument("--host", default="0.0.0.0", help="Listen host")
    parser.add_argument("--port", type=int, default=2525, help="Listen port")
    parser.add_argument("--backend-url", required=True, help="Backend API URL (e.g., http://localhost:8000)")
    parser.add_argument("--api-token", required=True, help="Bearer token for analyzer endpoint")

    args = parser.parse_args()

    # Create a new event loop for the application
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Start SMTP server
    controller = Controller(
        AnalysisHandler(args.backend_url, args.api_token),
        hostname=args.host,
        port=args.port
    )

    controller.start()
    logger.info(f"SMTP Listener running on {args.host}:{args.port}")

    # Start heartbeat loop as a background task
    loop.create_task(heartbeat_loop(args.backend_url, args.api_token, args.port))

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        controller.stop()
        loop.close()


if __name__ == "__main__":
    main()
