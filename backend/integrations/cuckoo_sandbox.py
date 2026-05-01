"""
Cuckoo Sandbox Mock Integration

Mock integration with Cuckoo Sandbox for malware analysis.
This is a simulation for development/testing purposes.

In production, this would connect to a real Cuckoo Sandbox instance.

Author: SPEAR-GUARD Team
Date: 2025-11-05
"""

import asyncio
import logging
import hashlib
import random
from typing import Dict, List, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class CuckooSandboxClient:
    """
    Mock Cuckoo Sandbox Client

    Simulates malware analysis results including:
    - Network activity
    - File system modifications
    - Registry changes
    - API calls
    - Behavioral patterns
    """

    # Mock malicious behaviors
    MALICIOUS_BEHAVIORS = [
        "Creates executable in temp directory",
        "Modifies registry run keys for persistence",
        "Attempts to disable Windows Defender",
        "Downloads additional payload from C2 server",
        "Encrypts user files (ransomware behavior)",
        "Establishes outbound connection to unknown IP",
        "Injects code into system processes",
        "Captures keystrokes (keylogger behavior)",
        "Exfiltrates data to external server",
        "Modifies system hosts file"
    ]

    SUSPICIOUS_BEHAVIORS = [
        "Creates hidden files",
        "Modifies browser settings",
        "Accesses stored credentials",
        "Enumerates running processes",
        "Queries system information",
        "Attempts network scanning"
    ]

    NETWORK_INDICATORS = [
        {"ip": "185.220.101.42", "port": 443, "protocol": "https", "country": "RU", "malicious": True},
        {"ip": "192.168.1.100", "port": 80, "protocol": "http", "country": "US", "malicious": False},
        {"ip": "10.0.0.1", "port": 53, "protocol": "dns", "country": "Local", "malicious": False},
    ]

    def __init__(self, api_url: Optional[str] = None, api_key: Optional[str] = None):
        """
        Initialize Cuckoo Sandbox client

        Args:
            api_url: Cuckoo API URL (not used in mock)
            api_key: API key (not used in mock)
        """
        self.api_url = api_url or "http://localhost:8090"
        self.api_key = api_key
        self.logger = logging.getLogger(f"{__name__}.CuckooSandboxClient")
        self.logger.info("Cuckoo Sandbox: Running in MOCK mode")

    async def analyze_file(
        self,
        file_content: bytes,
        filename: str,
        timeout: int = 60
    ) -> Dict[str, any]:
        """
        Submit file for sandbox analysis

        Args:
            file_content: File bytes
            filename: Original filename
            timeout: Analysis timeout in seconds

        Returns:
            Dict with analysis results
        """
        self.logger.info(f"Analyzing file: {filename} ({len(file_content)} bytes)")

        # Simulate analysis delay
        await asyncio.sleep(2)

        # Determine file danger based on extension and content
        is_malicious = self._is_potentially_malicious(filename, file_content)

        # Generate mock analysis results
        return self._generate_analysis_results(
            filename=filename,
            file_size=len(file_content),
            is_malicious=is_malicious
        )

    def _is_potentially_malicious(self, filename: str, file_content: bytes) -> bool:
        """
        Determine if file should be flagged as malicious (mock logic)

        Args:
            filename: File name
            file_content: File content

        Returns:
            True if should be flagged as malicious
        """
        filename_lower = filename.lower()

        # Dangerous extensions
        dangerous_extensions = [
            '.exe', '.scr', '.bat', '.cmd', '.com', '.pif',
            '.vbs', '.js', '.jar', '.msi', '.dll'
        ]

        # Check for double extensions
        if filename_lower.count('.') >= 2:
            # e.g., document.pdf.exe
            for ext in dangerous_extensions:
                if filename_lower.endswith(ext):
                    return True

        # Check single dangerous extension
        for ext in dangerous_extensions:
            if filename_lower.endswith(ext):
                return True

        # Check for macro indicators in content (simplified)
        if b'macros' in file_content.lower() or b'vba' in file_content.lower():
            return True

        # Check file size (very small executables are suspicious)
        if filename_lower.endswith('.exe') and len(file_content) < 1024:
            return True

        return False

    def _generate_analysis_results(
        self,
        filename: str,
        file_size: int,
        is_malicious: bool
    ) -> Dict[str, any]:
        """
        Generate mock analysis results

        Args:
            filename: File name
            file_size: File size in bytes
            is_malicious: Whether to mark as malicious

        Returns:
            Dict with detailed analysis results
        """
        task_id = random.randint(1000, 9999)
        file_hash = hashlib.sha256(filename.encode() + str(file_size).encode()).hexdigest()

        if is_malicious:
            return {
                'task_id': task_id,
                'status': 'completed',
                'score': random.randint(70, 100),  # High score = malicious
                'classification': 'malicious',
                'file_info': {
                    'name': filename,
                    'size': file_size,
                    'sha256': file_hash,
                    'type': self._guess_file_type(filename)
                },
                'behaviors': {
                    'malicious': random.sample(
                        self.MALICIOUS_BEHAVIORS,
                        k=min(3, len(self.MALICIOUS_BEHAVIORS))
                    ),
                    'suspicious': random.sample(
                        self.SUSPICIOUS_BEHAVIORS,
                        k=min(2, len(self.SUSPICIOUS_BEHAVIORS))
                    )
                },
                'network': {
                    'connections': [
                        self.NETWORK_INDICATORS[0],  # Malicious connection
                        self.NETWORK_INDICATORS[2]   # Local DNS
                    ],
                    'dns_queries': [
                        'evil-c2-server.com',
                        'malware-distribution.net'
                    ],
                    'http_requests': [
                        {'url': 'http://evil-c2-server.com/payload.exe', 'method': 'GET'}
                    ]
                },
                'signatures': [
                    {
                        'name': 'Ransomware behavior detected',
                        'severity': 'high',
                        'description': 'File exhibits ransomware-like behavior'
                    },
                    {
                        'name': 'Persistence mechanism',
                        'severity': 'medium',
                        'description': 'Modifies registry for persistence'
                    }
                ],
                'processes': [
                    {
                        'name': filename,
                        'pid': 1234,
                        'command_line': f'C:\\Temp\\{filename}',
                        'spawned_processes': ['cmd.exe', 'powershell.exe']
                    }
                ],
                'registry': [
                    {
                        'key': 'HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run',
                        'value': 'Malware',
                        'data': f'C:\\Temp\\{filename}'
                    }
                ],
                'files': {
                    'created': [
                        'C:\\Temp\\payload.exe',
                        'C:\\Users\\User\\AppData\\Local\\Temp\\malware.dll'
                    ],
                    'modified': [
                        'C:\\Windows\\System32\\drivers\\etc\\hosts'
                    ],
                    'deleted': []
                },
                'analysis_time': 45,
                'timestamp': datetime.utcnow().isoformat()
            }
        else:
            return {
                'task_id': task_id,
                'status': 'completed',
                'score': random.randint(0, 30),  # Low score = benign
                'classification': 'benign',
                'file_info': {
                    'name': filename,
                    'size': file_size,
                    'sha256': file_hash,
                    'type': self._guess_file_type(filename)
                },
                'behaviors': {
                    'malicious': [],
                    'suspicious': []
                },
                'network': {
                    'connections': [],
                    'dns_queries': [],
                    'http_requests': []
                },
                'signatures': [],
                'processes': [
                    {
                        'name': filename,
                        'pid': 1234,
                        'command_line': f'C:\\Temp\\{filename}',
                        'spawned_processes': []
                    }
                ],
                'registry': [],
                'files': {
                    'created': [],
                    'modified': [],
                    'deleted': []
                },
                'analysis_time': 30,
                'timestamp': datetime.utcnow().isoformat()
            }

    def _guess_file_type(self, filename: str) -> str:
        """Guess file type from extension"""
        ext = filename.lower().split('.')[-1]

        file_types = {
            'exe': 'Windows Executable',
            'dll': 'Dynamic Link Library',
            'pdf': 'PDF Document',
            'docx': 'Microsoft Word Document',
            'xlsx': 'Microsoft Excel Spreadsheet',
            'zip': 'ZIP Archive',
            'jar': 'Java Archive',
            'scr': 'Screen Saver',
            'bat': 'Batch File',
            'vbs': 'VBScript File',
            'js': 'JavaScript File'
        }

        return file_types.get(ext, 'Unknown')

    async def get_analysis_status(self, task_id: int) -> Dict[str, any]:
        """
        Get status of analysis task

        Args:
            task_id: Task ID

        Returns:
            Dict with status info
        """
        # Mock: always completed after short delay
        await asyncio.sleep(0.5)

        return {
            'task_id': task_id,
            'status': 'completed',
            'completed_at': datetime.utcnow().isoformat()
        }

    async def get_analysis_report(self, task_id: int) -> Dict[str, any]:
        """
        Get detailed analysis report

        Args:
            task_id: Task ID

        Returns:
            Dict with full report
        """
        # Mock: return sample report
        await asyncio.sleep(0.5)

        return {
            'task_id': task_id,
            'status': 'completed',
            'message': 'Mock report - use analyze_file() for detailed results'
        }

    async def analyze_url(self, url: str) -> Dict[str, any]:
        """
        Submit URL for analysis

        Args:
            url: URL to analyze

        Returns:
            Dict with analysis results
        """
        self.logger.info(f"Analyzing URL: {url}")

        await asyncio.sleep(1.5)

        # Determine if URL is malicious based on patterns
        is_malicious = self._is_url_malicious(url)

        return {
            'url': url,
            'status': 'completed',
            'score': random.randint(70, 100) if is_malicious else random.randint(0, 30),
            'classification': 'malicious' if is_malicious else 'benign',
            'behaviors': {
                'downloads_malware': is_malicious,
                'phishing_page': 'login' in url.lower() or 'verify' in url.lower(),
                'redirects': random.randint(0, 3),
                'uses_obfuscation': is_malicious
            },
            'network': {
                'ip_address': f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}",
                'country': 'RU' if is_malicious else 'US',
                'asn': 'AS12345'
            },
            'content': {
                'contains_forms': 'login' in url.lower(),
                'external_links': random.randint(5, 20),
                'iframes': random.randint(0, 3) if is_malicious else 0
            },
            'timestamp': datetime.utcnow().isoformat()
        }

    def _is_url_malicious(self, url: str) -> bool:
        """Determine if URL should be flagged as malicious"""
        url_lower = url.lower()

        malicious_patterns = [
            'evil', 'phishing', 'malware', 'hack', 'scam',
            'fake', 'fraud', 'virus', 'trojan'
        ]

        suspicious_patterns = [
            'login', 'verify', 'account', 'secure', 'banking',
            'password', 'confirm', 'update'
        ]

        # Check malicious patterns
        if any(pattern in url_lower for pattern in malicious_patterns):
            return True

        # Check suspicious patterns + IP address
        if any(pattern in url_lower for pattern in suspicious_patterns):
            # IP in URL is suspicious for login pages
            import re
            if re.search(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', url):
                return True

        return False


# Singleton instance
cuckoo_client = CuckooSandboxClient()
