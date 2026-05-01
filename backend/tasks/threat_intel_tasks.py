"""
Threat Intelligence Celery Tasks

Периодическая синхронизация TI-feeds + WebSocket push уведомлений.

Celery Beat schedule:
    - sync_threat_intel_task: каждые 15 минут
    - cleanup_expired_ti_task: каждые 6 часов
"""
from celery import Task
from celery.utils.log import get_task_logger
from typing import Dict, Any
import asyncio

from config.celery_config import celery_app
from database import AsyncSessionLocal

logger = get_task_logger(__name__)


class DBTiTask(Task):
    """Task с async session."""

    def run_async(self, coro):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()


@celery_app.task(
    bind=True,
    base=DBTiTask,
    name="tasks.threat_intel.sync_threat_intel",
    max_retries=3,
    default_retry_delay=300,  # 5 min retry
)
def sync_threat_intel_task(self) -> Dict[str, Any]:
    """
    Fetch и сохранить все Threat Intelligence feeds.

    Запускается Celery Beat каждые 15 минут.
    """
    logger.info("Starting Threat Intel sync task")

    async def _sync():
        from services.threat_intel_service import ThreatIntelService

        async with AsyncSessionLocal() as db:
            service = ThreatIntelService(db)
            result = await service.sync_all_feeds()

        # Push WebSocket notification to all security officers
        if result.get("new_alerts", 0) > 0:
            await _notify_security_officers(result)

        return result

    try:
        return DBTiTask.run_async(self, _sync())
    except Exception as e:
        logger.error(f"TI sync task failed: {e}", exc_info=True)
        raise self.retry(exc=e)


async def _notify_security_officers(result: Dict[str, Any]) -> None:
    """Push TI alert summary to all connected security officers via WebSocket."""
    try:
        from websocket_integration import notify_threat_intel_update
        await notify_threat_intel_update({
            "type": "threat_intel_update",
            "new_indicators": result.get("total_stored", 0),
            "new_alerts": result.get("new_alerts", 0),
            "sources": result.get("sources", []),
            "timestamp": result.get("timestamp")
        })
        logger.info("WebSocket: sent threat intel update to officers")
    except Exception as e:
        logger.warning(f"WebSocket TI notification failed (non-critical): {e}")


@celery_app.task(
    bind=True,
    base=DBTiTask,
    name="tasks.threat_intel.cleanup_expired_ti",
)
def cleanup_expired_ti_task(self) -> Dict[str, Any]:
    """
    Cleanup истёкших TI-blacklist entries из Redis.

    Запускается каждые 6 часов.
    """
    logger.info("Starting TI Redis cleanup task")

    async def _cleanup():
        from services.threat_intel_service import (
            TI_LIST_KEY, TI_IP_KEY, TI_URL_KEY, TI_HASH_KEY, TI_LAST_SYNC
        )

        try:
            from redis_client import redis_client
            if not redis_client or not redis_client.redis:
                return {"status": "skipped", "reason": "redis_unavailable"}

            import json
            from datetime import datetime, timedelta

            cleaned = 0
            expiry = datetime.utcnow() - timedelta(days=7)

            for key in [TI_IP_KEY, TI_LIST_KEY, TI_URL_KEY, TI_HASH_KEY]:
                entries = await redis_client.hgetall(key)
                to_delete = []

                for hkey, value in entries.items():
                    try:
                        data = json.loads(value)
                        last_seen_str = data.get("last_seen", "")
                        if last_seen_str:
                            last_seen = datetime.fromisoformat(last_seen_str)
                            if last_seen < expiry:
                                to_delete.append(hkey)
                    except (json.JSONDecodeError, KeyError, ValueError):
                        # malformed entry — delete
                        to_delete.append(hkey)

                if to_delete:
                    pipe = redis_client.redis.pipeline()
                    for hkey in to_delete:
                        pipe.hdel(key, hkey)
                    await pipe.execute()
                    cleaned += len(to_delete)
                    logger.info(f"TI cleanup: removed {len(to_delete)} expired entries from {key}")

            return {
                "status": "success",
                "cleaned_entries": cleaned,
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"TI cleanup failed: {e}")
            return {"status": "error", "error": str(e)}

    return DBTiTask.run_async(self, _cleanup())
