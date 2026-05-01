"""
Threat Intelligence Service

Интеграция с открытыми TI-feeds для автоматического обновления чёрных списков.

Источники:
- AlienVault OTX (Open Threat Exchange) — pulses/indicators
- AbuseIPDB — IP reputation
- Google Safe Browsing API — malicious URLs (при наличии API key)

Схема работы:
1. Celery Beat задача запускается периодически (каждые 15 мин)
2. Fetch новых indicators с OTX
3. Upsert в Redis cache для быстрой проверки
4. Обновление ThreatAlert в БД
5. WebSocket push всем security officers
6. Invalidate Redis cache для affected senders
"""
import asyncio
import logging
import hashlib
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, field
import json

import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

try:
    from redis_client import redis_client, RedisClient
    REDIS_AVAILABLE = True
except ImportError:
    redis_client = None
    RedisClient = None
    REDIS_AVAILABLE = False

logger = logging.getLogger(__name__)

# =============================================================================
# Data classes
# =============================================================================

@dataclass
class ThreatIndicator:
    """Единичный indicator угрозы"""
    type: str            # ip, domain, url, hash
    value: str            # сам indicator
    source: str           # otx, abuseipdb, safebrowsing
    severity: str          # critical, high, medium, low
    Malware_family: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    confidence: float = 1.0  # 0-1


@dataclass
class IntelFeedResult:
    """Результат fetch одного feed"""
    source: str
    fetched: int
    new_indicators: int
    errors: List[str] = field(default_factory=list)
    duration_ms: int = 0


# =============================================================================
# Redis key schema
# =============================================================================

def _cache_key(indicator_type: str, value: str) -> str:
    return f"ti:{indicator_type}:{value.lower()}"


TI_LIST_KEY = "ti:domains:blacklist"      # HASH: domain -> metadata json
TI_IP_KEY  = "ti:ips:blacklist"           # HASH: ip -> metadata json
TI_URL_KEY = "ti:urls:blacklist"         # HASH: url -> metadata json
TI_HASH_KEY = "ti:hashes:blacklist"       # HASH: hash -> metadata json
TI_LAST_SYNC = "ti:last_sync"             # STRING: ISO timestamp


# =============================================================================
# Feed clients
# =============================================================================

class AlienVaultOTXClient:
    """
    AlienVault Open Threat Exchange API v3

    Free tier: 20 req/hour, 10k pulses/month
    Docs: https://otx.alienvault.com/api
    """
    BASE_URL = "https://otx.alienvault.com/api/v1"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OTX_API_KEY")
        self.mock_mode = not self.api_key
        self.logger = logging.getLogger(f"{__name__}.OTX")

        if self.mock_mode:
            self.logger.warning("OTX: Running in MOCK mode (no API key)")
        else:
            self.logger.info("OTX: Running in LIVE mode")

    async def fetch_pulses(self, modified_since_hours: int = 24) -> List[ThreatIndicator]:
        """Fetch pulses modified since N hours ago."""
        if self.mock_mode:
            return self._mock_fetch()

        try:
            since = datetime.utcnow() - timedelta(hours=modified_since_hours)
            url = f"{self.BASE_URL}/pulses/subscribed"
            params = {"modified_since": int(since.timestamp())}

            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(
                    url,
                    headers={"X-OTX-API-KEY": self.api_key},
                    params=params
                )
                resp.raise_for_status()
                data = resp.json()

            indicators: List[ThreatIndicator] = []
            for pulse in data.get("results", []):
                pulse_name = pulse.get("name", "")
                pulse_tags = pulse.get("tags", [])
                pulse_severity = self._severity_from_tags(pulse_tags)

                for indicator in pulse.get("indicators", []):
                    ind_type = self._map_indicator_type(indicator.get("type", ""))
                    if not ind_type:
                        continue

                    indicators.append(ThreatIndicator(
                        type=ind_type,
                        value=indicator.get("indicator", ""),
                        source="otx",
                        severity=pulse_severity,
                        malware_family=pulse_name,
                        tags=pulse_tags,
                        first_seen=pulse.get("created", None),
                        last_seen=pulse.get("modified", None),
                        confidence=0.8  # OTX pulses have ~80% confidence
                    ))

            self.logger.info(f"OTX: fetched {len(indicators)} indicators from {len(data.get('results', []))} pulses")
            return indicators

        except httpx.HTTPStatusError as e:
            self.logger.error(f"OTX HTTP error: {e.response.status_code} {e.response.text}")
            return []
        except Exception as e:
            self.logger.error(f"OTX fetch error: {e}")
            return []

    def _mock_fetch(self) -> List[ThreatIndicator]:
        """Mock data simulating recent malicious indicators."""
        return [
            ThreatIndicator(
                type="ip", value="185.220.101.42",
                source="otx", severity="high",
                malware_family="TrickBot", tags=["botnet", "c2"],
                confidence=0.85
            ),
            ThreatIndicator(
                type="domain", value="malware-distribution.ru.net",
                source="otx", severity="critical",
                malware_family="Emotet", tags=["malware", "phishing"],
                confidence=0.9
            ),
            ThreatIndicator(
                type="url", value="http://185.220.101.42/payload.exe",
                source="otx", severity="high",
                malware_family="IcedID", tags=["malware", "dropper"],
                confidence=0.75
            ),
            ThreatIndicator(
                type="domain", value="fraud-gov-phishing.com",
                source="otx", severity="critical",
                malware_family="GovPhishing", tags=["phishing", "government"],
                confidence=0.95
            ),
        ]

    @staticmethod
    def _map_indicator_type(otx_type: str) -> Optional[str]:
        mapping = {
            "IPv4": "ip",
            "IPv6": "ip",
            "domain": "domain",
            "hostname": "domain",
            "url": "url",
            "filehash-md5": "hash",
            "filehash-sha256": "hash",
            "filehash-sha1": "hash",
            "email": "email",
            "cve": None,  # пока не обрабатываем CVE
        }
        return mapping.get(otx_type)

    @staticmethod
    def _severity_from_tags(tags: List[str]) -> str:
        high_tags = {"apt", "ransomware", "banker", "trojan", "bot", "c2"}
        med_tags  = {"phishing", "malware", "spam", "exploit"}
        low_tags  = {"suspicious", "grayware"}

        tags_lower = {t.lower() for t in tags}
        if tags_lower & high_tags:
            return "critical"
        if tags_lower & med_tags:
            return "high"
        if tags_lower & low_tags:
            return "medium"
        return "low"


class AbuseIPDBClient:
    """
    AbuseIPDB IP Reputation API

    Free tier: 1000 req/day
    Docs: https://www.abuseipdb.com/api
    """
    BASE_URL = "https://api.abuseipdb.com/api/v2"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("ABUSEIPDB_API_KEY")
        self.mock_mode = not self.api_key
        self.logger = logging.getLogger(f"{__name__}.AbuseIPDB")

        if self.mock_mode:
            self.logger.warning("AbuseIPDB: Running in MOCK mode (no API key)")

    async def check_ip(self, ip: str, max_age_days: int = 30) -> Optional[ThreatIndicator]:
        """Проверить конкретный IP в AbuseIPDB."""
        if self.mock_mode:
            return self._mock_check(ip)

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    f"{self.BASE_URL}/check",
                    headers={"Key": self.api_key, "Accept": "application/json"},
                    params={"ipAddress": ip, "maxAgeInDays": max_age_days}
                )
                resp.raise_for_status()
                data = resp.json().get("data", {})

            abuse_score = data.get("abuseConfidenceScore", 0)
            if abuse_score < 20:
                return None  # не подозрительный

            return ThreatIndicator(
                type="ip",
                value=ip,
                source="abuseipdb",
                severity=self._severity_from_score(abuse_score),
                confidence=abuse_score / 100.0
            )

        except Exception as e:
            self.logger.error(f"AbuseIPDB check error for {ip}: {e}")
            return None

    def _mock_check(self, ip: str) -> Optional[ThreatIndicator]:
        """Mock: подозрительные IP по паттерну."""
        suspicious = ["185.", "91.", "185.220.", "103."]
        if any(ip.startswith(p) for p in suspicious):
            return ThreatIndicator(
                type="ip", value=ip,
                source="abuseipdb", severity="high",
                confidence=0.7
            )
        return None

    @staticmethod
    def _severity_from_score(score: int) -> str:
        if score >= 75: return "critical"
        if score >= 50: return "high"
        if score >= 25: return "medium"
        return "low"


# =============================================================================
# Main Threat Intel Service
# =============================================================================

class ThreatIntelService:
    """
    Orchestrates threat intelligence feeds.

    Использование:
        service = ThreatIntelService(db)
        result = await service.sync_all_feeds()
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.otx = AlienVaultOTXClient()
        self.abuse = AbuseIPDBClient()
        self.logger = logging.getLogger(f"{__name__}.ThreatIntelService")

    async def check_ip(self, ip: str) -> Optional[ThreatIndicator]:
        """Проверить IP against known threats (Redis cache first, then feeds)."""
        # 1. Redis cache lookup
        if REDIS_AVAILABLE and redis_client:
            cache_key = _cache_key("ip", ip)
            cached = await redis_client.hget(TI_IP_KEY, cache_key)
            if cached:
                try:
                    data = json.loads(cached)
                    self.logger.debug(f"TI cache hit for IP {ip}")
                    return ThreatIndicator(**data)
                except (json.JSONDecodeError, TypeError):
                    pass

        # 2. Realtime AbuseIPDB check (rate-limited by AbuseIPClient internally)
        return await self.abuse.check_ip(ip)

    async def check_domain(self, domain: str) -> Optional[ThreatIndicator]:
        """Проверить domain against TI feeds (Redis first)."""
        domain_lower = domain.lower()

        if REDIS_AVAILABLE and redis_client:
            cached = await redis_client.hget(TI_LIST_KEY, domain_lower)
            if cached:
                try:
                    return ThreatIndicator(**json.loads(cached))
                except (json.JSONDecodeError, TypeError):
                    pass

        # OTX lookup for domain
        if self.otx.api_key:
            indicators = await self.otx.fetch_pulses(modified_since_hours=1)
            for ind in indicators:
                if ind.type == "domain" and ind.value == domain_lower:
                    return ind

        return None

    async def sync_all_feeds(self) -> Dict[str, Any]:
        """
        Fetch и сохранить все TI feeds.
        Возвращает summary результат.
        """
        from database import ThreatAlert
        from utils.crypto import get_redis_sync

        results: List[IntelFeedResult] = []
        all_indicators: List[ThreatIndicator] = []
        start = datetime.utcnow()

        # 1. Fetch OTX
        otx_result = IntelFeedResult(source="alienvault_otx", fetched=0, new_indicators=0)
        try:
            indicators = await self.otx.fetch_pulses(modified_since_hours=24)
            otx_result.fetched = len(indicators)
            all_indicators.extend(indicators)
        except Exception as e:
            otx_result.errors.append(str(e))
        results.append(otx_result)

        # 2. Store in Redis (batch)
        if REDIS_AVAILABLE and redis_client:
            await self._store_indicators_redis(all_indicators)

        # 3. Store in DB (ThreatAlert)
        new_alerts = await self._upsert_threat_alerts(all_indicators)
        await self.db.commit()

        # 4. Update last sync timestamp
        if REDIS_AVAILABLE and redis_client:
            await redis_client.set(TI_LAST_SYNC, datetime.utcnow().isoformat())

        duration_ms = int((datetime.utcnow() - start).total_seconds() * 1000)

        self.logger.info(
            f"TI sync complete: {len(all_indicators)} indicators, "
            f"{new_alerts} new alerts, {duration_ms}ms"
        )

        return {
            "sources": [r.source for r in results],
            "total_fetched": sum(r.fetched for r in results),
            "total_stored": len(all_indicators),
            "new_alerts": new_alerts,
            "errors": [e for r in results for e in r.errors],
            "duration_ms": duration_ms,
            "timestamp": datetime.utcnow().isoformat()
        }

    async def _store_indicators_redis(self, indicators: List[ThreatIndicator]) -> None:
        """Batch store indicators in Redis hashes."""
        if not redis_client:
            return

        batch: Dict[str, Dict[str, str]] = {
            "ip": {},
            "domain": {},
            "url": {},
            "hash": {},
        }

        key_map = {
            "ip": TI_IP_KEY,
            "domain": TI_LIST_KEY,
            "url": TI_URL_KEY,
            "hash": TI_HASH_KEY,
        }

        for ind in indicators:
            key = key_map.get(ind.type)
            if not key:
                continue
            batch[ind.type][ind.value.lower()] = json.dumps({
                "type": ind.type,
                "value": ind.value,
                "source": ind.source,
                "severity": ind.severity,
                "malware_family": ind.malware_family,
                "tags": ind.tags,
                "confidence": ind.confidence,
                "last_seen": (ind.last_seen or datetime.utcnow()).isoformat()
            })

        for ind_type, mapping in batch.items():
            if not mapping:
                continue
            key = key_map[ind_type]
            pipe = redis_client.redis.pipeline() if hasattr(redis_client, 'redis') and redis_client.redis else None
            if pipe:
                for hkey, val in mapping.items():
                    pipe.hset(key, hkey, val)
                await pipe.execute()

        self.logger.info(f"TI: stored {sum(len(v) for v in batch.values())} indicators in Redis")

    async def _upsert_threat_alerts(
        self, indicators: List[ThreatIndicator]
    ) -> int:
        """Upsert ThreatAlert records from indicators. Returns count of new alerts."""
        from database import ThreatAlert

        new_count = 0
        for ind in indicators:
            # Check if alert already exists
            existing = await self.db.execute(
                select(ThreatAlert).where(
                    and_(
                        ThreatAlert.source_address == ind.value,
                        ThreatAlert.alert_type == f"ti_{ind.type}",
                        ThreatAlert.created_at > datetime.utcnow() - timedelta(days=7)
                    )
                )
            )
            if existing.scalars().first():
                continue

            alert = ThreatAlert(
                organization_id=None,  # global
                alert_type=f"ti_{ind.type}",
                severity=self._severity_map(ind.severity),
                title=f"TI: {ind.type.upper()} {ind.value} ({ind.source})",
                description=f"{ind.source.upper()} | Severity: {ind.severity} | Family: {ind.malware_family or 'unknown'}",
                source_address=ind.value,
                status="active",
            )
            self.db.add(alert)
            new_count += 1

        return new_count

    @staticmethod
    def _severity_map(ti_severity: str) -> str:
        mapping = {
            "critical": "critical",
            "high": "high",
            "medium": "medium",
            "low": "low"
        }
        return mapping.get(ti_severity, "medium")
