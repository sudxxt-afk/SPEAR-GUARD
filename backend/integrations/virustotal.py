"""
VirusTotal API Integration

Provides interface to VirusTotal API v3 for:
- URL scanning
- File hash lookup
- Domain reputation check

Author: SPEAR-GUARD Team
Date: 2025-11-05
"""

import os
import asyncio
import logging
import hashlib
import time
from typing import Dict, Optional, List
from datetime import datetime, timedelta
import aiohttp
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


class VirusTotalClient:
    """
    VirusTotal API v3 Client

    Features:
    - URL scanning and reputation
    - File hash lookup
    - Domain analysis
    - Rate limiting
    - Async support
    - Mock mode for testing (when no API key)
    """

    # API Configuration
    API_BASE_URL = "https://www.virustotal.com/api/v3"

    # Rate limits (free tier)
    REQUESTS_PER_MINUTE = 4
    REQUESTS_PER_DAY = 500

    # Mock mode responses
    MOCK_RESPONSES = {
        'clean_url': {
            'malicious': 0,
            'suspicious': 0,
            'harmless': 80,
            'undetected': 10,
            'reputation': 100
        },
        'malicious_url': {
            'malicious': 45,
            'suspicious': 12,
            'harmless': 5,
            'undetected': 28,
            'reputation': -50
        },
        'phishing_url': {
            'malicious': 38,
            'suspicious': 15,
            'harmless': 10,
            'undetected': 27,
            'reputation': -30,
            'categories': ['phishing', 'malicious']
        }
    }

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize VirusTotal client

        Args:
            api_key: VirusTotal API key (optional, uses mock if not provided)
        """
        self.api_key = api_key or os.getenv('VIRUSTOTAL_API_KEY')
        self.mock_mode = not self.api_key

        self.logger = logging.getLogger(f"{__name__}.VirusTotalClient")

        if self.mock_mode:
            self.logger.warning("VirusTotal: Running in MOCK mode (no API key)")
        else:
            self.logger.info("VirusTotal: Running in LIVE mode")

        # Rate limiting
        self.request_timestamps = []
        self.executor = ThreadPoolExecutor(max_workers=2)

        # Session for HTTP requests
        self.session: Optional[aiohttp.ClientSession] = None

    async def _ensure_session(self):
        """Ensure aiohttp session exists"""
        if self.session is None:
            self.session = aiohttp.ClientSession()  # BUG-10 fix: key passed per-request, not in session

    async def close(self):
        """Close aiohttp session and shutdown executor"""
        if self.session:
            await self.session.close()
            self.session = None
        # BUG-21 fix: properly shutdown ThreadPoolExecutor
        if hasattr(self, 'executor') and self.executor:
            self.executor.shutdown(wait=True)
            self.executor = None

    async def _rate_limit_check(self):
        """
        Check and enforce rate limits

        Raises:
            Exception: If rate limit exceeded
        """
        now = time.time()

        # Remove timestamps older than 1 minute
        self.request_timestamps = [
            ts for ts in self.request_timestamps
            if now - ts < 60
        ]

        # BUG-20 fix: check BEFORE adding (not >= which allows 5 requests)
        if len(self.request_timestamps) >= self.REQUESTS_PER_MINUTE:
            wait_time = 60 - (now - self.request_timestamps[0])
            self.logger.warning(f"Rate limit reached, waiting {wait_time:.1f}s")
            await asyncio.sleep(wait_time)
            # Prune stale entries instead of clearing the entire list
            self.request_timestamps = [
                ts for ts in self.request_timestamps
                if now - ts < 60
            ]

        # BUG-10 fix: pass API key per-request in correct header format
        self.request_timestamps.append(now)

    async def _get_request_headers(self) -> Dict[str, str]:
        """Build request headers with API key."""
        return {
            'x-apikey': self.api_key,
            'Accept': 'application/json'
        }

    async def scan_url(self, url: str) -> Dict[str, any]:
        """
        Scan URL with VirusTotal

        Args:
            url: URL to scan

        Returns:
            Dict with scan results
        """
        if self.mock_mode:
            return await self._mock_scan_url(url)

        try:
            await self._rate_limit_check()
            await self._ensure_session()

            # Submit URL for scanning
            scan_response = await self._submit_url(url)

            # Get analysis results
            analysis_id = scan_response.get('data', {}).get('id')
            if not analysis_id:
                raise Exception("No analysis ID returned")

            # Wait a bit for analysis to complete
            await asyncio.sleep(2)

            # Get analysis results
            results = await self._get_url_analysis(analysis_id)

            return self._parse_url_results(results)

        except Exception as e:
            self.logger.error(f"VirusTotal URL scan error: {e}")
            return {
                'error': str(e),
                'malicious': 0,
                'suspicious': 0,
                'harmless': 0,
                'undetected': 0,
                'reputation': 0
            }

    async def _submit_url(self, url: str) -> Dict:
        """Submit URL to VirusTotal"""
        endpoint = f"{self.API_BASE_URL}/urls"
        headers = await self._get_request_headers()

        async with self.session.post(
            endpoint,
            json={'url': url},  # BUG-10 fix: use json= (proper JSON body)
            headers=headers      # BUG-10 fix: key passed per-request, not session-level
        ) as response:
            response.raise_for_status()
            return await response.json()

    async def _get_url_analysis(self, analysis_id: str) -> Dict:
        """Get URL analysis results"""
        endpoint = f"{self.API_BASE_URL}/analyses/{analysis_id}"
        headers = await self._get_request_headers()

        async with self.session.get(endpoint, headers=headers) as response:
            response.raise_for_status()
            return await response.json()

    def _parse_url_results(self, results: Dict) -> Dict[str, any]:
        """Parse VirusTotal URL analysis results"""
        try:
            stats = results.get('data', {}).get('attributes', {}).get('stats', {})

            return {
                'malicious': stats.get('malicious', 0),
                'suspicious': stats.get('suspicious', 0),
                'harmless': stats.get('harmless', 0),
                'undetected': stats.get('undetected', 0),
                'timeout': stats.get('timeout', 0),
                'total_scans': sum(stats.values()),
                'reputation': results.get('data', {}).get('attributes', {}).get('reputation', 0),
                'categories': results.get('data', {}).get('attributes', {}).get('categories', {}),
                'last_analysis_date': results.get('data', {}).get('attributes', {}).get('last_analysis_date')
            }
        except Exception as e:
            self.logger.error(f"Error parsing VT results: {e}")
            return {
                'malicious': 0,
                'suspicious': 0,
                'harmless': 0,
                'undetected': 0,
                'error': str(e)
            }

    async def _mock_scan_url(self, url: str) -> Dict[str, any]:
        """
        Mock URL scanning for testing

        Returns different results based on URL patterns
        """
        await asyncio.sleep(0.1)  # Simulate API delay

        url_lower = url.lower()

        # Detect malicious patterns
        malicious_patterns = [
            'evil', 'phishing', 'malware', 'virus', 'hack',
            'suspicious', 'scam', 'fraud', 'fake'
        ]

        phishing_patterns = [
            'login', 'signin', 'verify', 'account-update',
            'secure-banking', 'paypal-confirm', 'password-reset'
        ]

        # Check for malicious patterns
        if any(pattern in url_lower for pattern in malicious_patterns):
            response = self.MOCK_RESPONSES['malicious_url'].copy()
            response['url'] = url
            response['scan_date'] = datetime.utcnow().isoformat()
            return response

        # Check for phishing patterns
        if any(pattern in url_lower for pattern in phishing_patterns):
            response = self.MOCK_RESPONSES['phishing_url'].copy()
            response['url'] = url
            response['scan_date'] = datetime.utcnow().isoformat()
            return response

        # Default to clean
        response = self.MOCK_RESPONSES['clean_url'].copy()
        response['url'] = url
        response['scan_date'] = datetime.utcnow().isoformat()
        return response

    async def check_domain_reputation(self, domain: str) -> Dict[str, any]:
        """
        Check domain reputation

        Args:
            domain: Domain name

        Returns:
            Dict with reputation data
        """
        if self.mock_mode:
            return await self._mock_domain_reputation(domain)

        try:
            await self._rate_limit_check()
            await self._ensure_session()

            endpoint = f"{self.API_BASE_URL}/domains/{domain}"
            headers = await self._get_request_headers()

            async with self.session.get(endpoint, headers=headers) as response:
                response.raise_for_status()
                results = await response.json()

            return self._parse_domain_results(results)

        except Exception as e:
            self.logger.error(f"VirusTotal domain check error: {e}")
            return {
                'error': str(e),
                'reputation': 0,
                'categories': []
            }

    def _parse_domain_results(self, results: Dict) -> Dict[str, any]:
        """Parse VirusTotal domain results"""
        try:
            attributes = results.get('data', {}).get('attributes', {})

            return {
                'reputation': attributes.get('reputation', 0),
                'categories': attributes.get('categories', {}),
                'last_analysis_stats': attributes.get('last_analysis_stats', {}),
                'popularity_ranks': attributes.get('popularity_ranks', {}),
                'creation_date': attributes.get('creation_date'),
                'last_update_date': attributes.get('last_update_date')
            }
        except Exception as e:
            self.logger.error(f"Error parsing domain results: {e}")
            return {'error': str(e)}

    async def _mock_domain_reputation(self, domain: str) -> Dict[str, any]:
        """Mock domain reputation check"""
        await asyncio.sleep(0.1)

        # Government/known domains = high reputation
        trusted_domains = ['.gov.ru', '.mil.ru', 'google.com', 'microsoft.com', 'gov.']

        if any(td in domain.lower() for td in trusted_domains):
            return {
                'domain': domain,
                'reputation': 95,
                'categories': {'government': 'gov', 'trusted': 'verified'},
                'last_analysis_stats': {
                    'malicious': 0,
                    'suspicious': 0,
                    'harmless': 80,
                    'undetected': 5
                },
                'creation_date': '2010-01-01',
                'popularity_ranks': {'Alexa': {'rank': 1000}}
            }

        # Suspicious domains
        suspicious_keywords = ['evil', 'phish', 'scam', 'fake', 'malware']
        if any(kw in domain.lower() for kw in suspicious_keywords):
            return {
                'domain': domain,
                'reputation': -50,
                'categories': {'malicious': 'phishing'},
                'last_analysis_stats': {
                    'malicious': 35,
                    'suspicious': 10,
                    'harmless': 5,
                    'undetected': 40
                },
                'creation_date': datetime.utcnow().strftime('%Y-%m-%d'),
                'popularity_ranks': {}
            }

        # Unknown domain = neutral
        return {
            'domain': domain,
            'reputation': 0,
            'categories': {},
            'last_analysis_stats': {
                'malicious': 0,
                'suspicious': 0,
                'harmless': 20,
                'undetected': 70
            },
            'creation_date': '2020-01-01',
            'popularity_ranks': {}
        }

    async def check_file_hash(self, file_hash: str) -> Dict[str, any]:
        """
        Check file hash against VirusTotal database

        Args:
            file_hash: SHA256 hash of file

        Returns:
            Dict with scan results
        """
        if self.mock_mode:
            return await self._mock_file_hash(file_hash)

        try:
            await self._rate_limit_check()
            await self._ensure_session()

            endpoint = f"{self.API_BASE_URL}/files/{file_hash}"
            headers = await self._get_request_headers()

            async with self.session.get(endpoint, headers=headers) as response:
                if response.status == 404:
                    return {
                        'found': False,
                        'hash': file_hash,
                        'message': 'File not found in VirusTotal database'
                    }

                response.raise_for_status()
                results = await response.json()

            return self._parse_file_results(results)

        except Exception as e:
            self.logger.error(f"VirusTotal file hash check error: {e}")
            return {
                'error': str(e),
                'found': False,
                'hash': file_hash
            }

    def _parse_file_results(self, results: Dict) -> Dict[str, any]:
        """Parse VirusTotal file scan results"""
        try:
            attributes = results.get('data', {}).get('attributes', {})
            stats = attributes.get('last_analysis_stats', {})

            return {
                'found': True,
                'malicious': stats.get('malicious', 0),
                'suspicious': stats.get('suspicious', 0),
                'harmless': stats.get('harmless', 0),
                'undetected': stats.get('undetected', 0),
                'total_scans': sum(stats.values()),
                'file_type': attributes.get('type_description'),
                'size': attributes.get('size'),
                'names': attributes.get('names', []),
                'first_seen': attributes.get('first_submission_date'),
                'last_seen': attributes.get('last_analysis_date')
            }
        except Exception as e:
            self.logger.error(f"Error parsing file results: {e}")
            return {'error': str(e), 'found': False}

    async def _mock_file_hash(self, file_hash: str) -> Dict[str, any]:
        """Mock file hash check"""
        await asyncio.sleep(0.1)

        # Known malicious hash patterns (for testing)
        if 'dead' in file_hash.lower() or 'bad' in file_hash.lower():
            return {
                'found': True,
                'hash': file_hash,
                'malicious': 42,
                'suspicious': 8,
                'harmless': 5,
                'undetected': 15,
                'total_scans': 70,
                'file_type': 'Win32 EXE',
                'size': 524288,
                'names': ['malware.exe', 'trojan.exe'],
                'first_seen': '2024-01-15T10:30:00',
                'last_seen': datetime.utcnow().isoformat()
            }

        # Clean file
        if 'clean' in file_hash.lower() or 'good' in file_hash.lower():
            return {
                'found': True,
                'hash': file_hash,
                'malicious': 0,
                'suspicious': 0,
                'harmless': 65,
                'undetected': 5,
                'total_scans': 70,
                'file_type': 'PDF document',
                'size': 102400,
                'names': ['document.pdf'],
                'first_seen': '2024-01-10T09:00:00',
                'last_seen': datetime.utcnow().isoformat()
            }

        # Not found
        return {
            'found': False,
            'hash': file_hash,
            'message': 'File not found in database'
        }

    def calculate_file_hash(self, file_content: bytes) -> str:
        """
        Calculate SHA256 hash of file content

        Args:
            file_content: File bytes

        Returns:
            SHA256 hash (hex string)
        """
        return hashlib.sha256(file_content).hexdigest()


# Singleton instance
virustotal_client = VirusTotalClient()
