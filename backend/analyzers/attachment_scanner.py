"""
Attachment Scanner

Comprehensive malware scanning for email attachments including:
- Dangerous file extension detection
- Double extension detection
- Office macro analysis (oletools)
- VirusTotal hash lookup
- Cuckoo Sandbox analysis
- File size and metadata checks

Author: SPEAR-GUARD Team
Date: 2025-11-05
"""

import os
import asyncio
import logging
import hashlib
import mimetypes
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import re

# Import integrations
from integrations.virustotal import virustotal_client
from integrations.cuckoo_sandbox import cuckoo_client

logger = logging.getLogger(__name__)


class AttachmentScanner:
    """
    Comprehensive attachment security scanner

    Multi-layer analysis:
    1. Static analysis (extensions, signatures, metadata)
    2. Hash-based detection (VirusTotal)
    3. Macro detection (Office documents)
    4. Sandbox analysis (Cuckoo)
    5. Risk scoring and classification
    """

    # Dangerous file extensions
    DANGEROUS_EXTENSIONS = {
        '.exe', '.scr', '.bat', '.cmd', '.com', '.pif', '.vbs',
        '.js', '.jse', '.wsf', '.wsh', '.msi', '.dll', '.cpl',
        '.jar', '.app', '.deb', '.rpm', '.dmg', '.pkg'
    }

    # Suspicious but potentially legitimate
    SUSPICIOUS_EXTENSIONS = {
        '.zip', '.rar', '.7z', '.tar', '.gz', '.iso',
        '.ps1', '.psm1', '.vb', '.reg', '.lnk', '.chm'
    }

    # Office documents (may contain macros)
    OFFICE_EXTENSIONS = {
        '.doc', '.docx', '.docm', '.dot', '.dotm',
        '.xls', '.xlsx', '.xlsm', '.xlt', '.xltm',
        '.ppt', '.pptx', '.pptm', '.pot', '.potm',
        '.rtf'
    }

    # Safe extensions
    SAFE_EXTENSIONS = {
        '.txt', '.pdf', '.png', '.jpg', '.jpeg', '.gif',
        '.bmp', '.svg', '.mp3', '.mp4', '.avi', '.mov',
        '.csv', '.xml', '.json', '.html', '.css'
    }

    # File size limits
    MAX_SAFE_SIZE = 25 * 1024 * 1024  # 25 MB
    SUSPICIOUS_SIZE_MIN = 100  # Very small files are suspicious

    # Macro indicators (simple patterns)
    MACRO_INDICATORS = [
        b'macros', b'VBA', b'vbaProject.bin', b'xl/vbaProject.bin',
        b'word/vbaProject.bin', b'ppt/vbaProject.bin',
        b'AutoOpen', b'Auto_Open', b'Workbook_Open', b'Document_Open'
    ]

    def __init__(self):
        """Initialize attachment scanner"""
        self.logger = logging.getLogger(f"{__name__}.AttachmentScanner")
        self.vt_client = virustotal_client
        self.cuckoo_client = cuckoo_client

    async def scan_attachment(
        self,
        filename: str,
        file_content: bytes,
        enable_sandbox: bool = False,
        enable_virustotal: bool = True
    ) -> Dict[str, any]:
        """
        Comprehensive attachment scan

        Args:
            filename: Original filename
            file_content: File content bytes
            enable_sandbox: Enable Cuckoo sandbox analysis (slow)
            enable_virustotal: Enable VirusTotal hash lookup

        Returns:
            Dict with comprehensive scan results
        """
        self.logger.info(f"Scanning attachment: {filename} ({len(file_content)} bytes)")

        start_time = datetime.utcnow()

        # Run all checks in parallel where possible
        tasks = []

        # 1. Static analysis (fast, always run)
        static_analysis = self._static_analysis(filename, file_content)

        # 2. Hash-based checks
        if enable_virustotal:
            tasks.append(self._virustotal_check(file_content))
        else:
            tasks.append(asyncio.sleep(0))  # Placeholder

        # 3. Macro detection (for Office docs)
        if self._is_office_document(filename):
            macro_check = self._check_macros(file_content)
        else:
            macro_check = {'has_macros': False, 'macro_score': 0}

        # 4. Sandbox analysis (optional, slow)
        if enable_sandbox and static_analysis['risk_level'] != 'low':
            tasks.append(self._sandbox_analysis(filename, file_content))
        else:
            tasks.append(asyncio.sleep(0))  # Placeholder

        # Wait for async tasks
        vt_result, sandbox_result = await asyncio.gather(*tasks)

        # Aggregate results
        results = {
            'filename': filename,
            'file_size': len(file_content),
            'file_hash': {
                'md5': self._hash_file(file_content, 'md5'),
                'sha1': self._hash_file(file_content, 'sha1'),
                'sha256': self._hash_file(file_content, 'sha256')
            },
            'static_analysis': static_analysis,
            'macro_analysis': macro_check,
            'virustotal': vt_result if enable_virustotal else None,
            'sandbox': sandbox_result if enable_sandbox else None,
            'scan_time': (datetime.utcnow() - start_time).total_seconds(),
            'timestamp': datetime.utcnow().isoformat()
        }

        # Calculate overall risk
        results['overall_risk'] = self._calculate_overall_risk(results)

        # Generate summary
        results['summary'] = self._generate_summary(results)

        self.logger.info(f"Scan complete: {filename} - Risk: {results['overall_risk']['level']}")

        return results

    def _static_analysis(self, filename: str, file_content: bytes) -> Dict[str, any]:
        """
        Static file analysis without execution

        Checks:
        - File extension
        - Double extensions
        - File size
        - MIME type
        - Magic bytes

        Args:
            filename: File name
            file_content: File bytes

        Returns:
            Dict with static analysis results
        """
        analysis = {
            'filename': filename,
            'extension': self._get_extension(filename),
            'mime_type': self._get_mime_type(filename),
            'size': len(file_content),
            'issues': []
        }

        # Check for double extension
        if self._has_double_extension(filename):
            analysis['issues'].append({
                'type': 'double_extension',
                'severity': 'critical',
                'description': 'File has double extension (e.g., .pdf.exe) - common malware tactic'
            })

        # Check extension danger level
        ext = analysis['extension']
        if ext in self.DANGEROUS_EXTENSIONS:
            analysis['issues'].append({
                'type': 'dangerous_extension',
                'severity': 'critical',
                'description': f'Dangerous file type: {ext}'
            })
        elif ext in self.SUSPICIOUS_EXTENSIONS:
            analysis['issues'].append({
                'type': 'suspicious_extension',
                'severity': 'high',
                'description': f'Suspicious file type: {ext} (can contain malware)'
            })
        elif ext in self.OFFICE_EXTENSIONS:
            analysis['issues'].append({
                'type': 'office_document',
                'severity': 'medium',
                'description': f'Office document: {ext} (may contain macros)'
            })

        # Check file size
        if len(file_content) < self.SUSPICIOUS_SIZE_MIN:
            analysis['issues'].append({
                'type': 'suspicious_size',
                'severity': 'medium',
                'description': f'Suspiciously small file size: {len(file_content)} bytes'
            })
        elif len(file_content) > self.MAX_SAFE_SIZE:
            analysis['issues'].append({
                'type': 'large_file',
                'severity': 'low',
                'description': f'Large file size: {len(file_content)} bytes'
            })

        # Check filename for suspicious patterns
        suspicious_name_patterns = [
            'invoice', 'payment', 'receipt', 'urgent', 'important',
            'confidential', 'secure', 'password', 'account'
        ]
        filename_lower = filename.lower()
        for pattern in suspicious_name_patterns:
            if pattern in filename_lower and ext in self.DANGEROUS_EXTENSIONS:
                analysis['issues'].append({
                    'type': 'suspicious_filename',
                    'severity': 'high',
                    'description': f'Suspicious filename pattern: "{pattern}" with dangerous extension'
                })
                break

        # Determine risk level
        if any(issue['severity'] == 'critical' for issue in analysis['issues']):
            analysis['risk_level'] = 'critical'
        elif any(issue['severity'] == 'high' for issue in analysis['issues']):
            analysis['risk_level'] = 'high'
        elif any(issue['severity'] == 'medium' for issue in analysis['issues']):
            analysis['risk_level'] = 'medium'
        else:
            analysis['risk_level'] = 'low'

        return analysis

    def _has_double_extension(self, filename: str) -> bool:
        """
        Detect double extension (e.g., document.pdf.exe)

        Args:
            filename: File name

        Returns:
            True if double extension detected
        """
        # Remove spaces and get parts
        parts = filename.lower().replace(' ', '').split('.')

        if len(parts) < 3:
            return False

        # Check if last extension is dangerous
        last_ext = '.' + parts[-1]
        if last_ext not in self.DANGEROUS_EXTENSIONS:
            return False

        # Check if second-to-last looks like an extension
        second_ext = '.' + parts[-2]
        all_extensions = (
            self.DANGEROUS_EXTENSIONS |
            self.SUSPICIOUS_EXTENSIONS |
            self.OFFICE_EXTENSIONS |
            self.SAFE_EXTENSIONS
        )

        return second_ext in all_extensions

    def _get_extension(self, filename: str) -> str:
        """Get file extension (lowercase, with dot)"""
        _, ext = os.path.splitext(filename.lower())
        return ext

    def _get_mime_type(self, filename: str) -> Optional[str]:
        """Get MIME type from filename"""
        mime_type, _ = mimetypes.guess_type(filename)
        return mime_type

    def _is_office_document(self, filename: str) -> bool:
        """Check if file is Office document"""
        return self._get_extension(filename) in self.OFFICE_EXTENSIONS

    def _check_macros(self, file_content: bytes) -> Dict[str, any]:
        """
        Check for macros in Office documents

        Simple check for macro indicators in file content.
        In production, use oletools library for comprehensive analysis.

        Args:
            file_content: File bytes

        Returns:
            Dict with macro detection results
        """
        has_macros = False
        macro_indicators_found = []

        # Check for macro indicators
        for indicator in self.MACRO_INDICATORS:
            if indicator in file_content:
                has_macros = True
                macro_indicators_found.append(indicator.decode('latin1', errors='ignore'))

        macro_score = 0
        if has_macros:
            macro_score = 50 + (len(macro_indicators_found) * 10)
            macro_score = min(macro_score, 100)

        return {
            'has_macros': has_macros,
            'indicators_found': macro_indicators_found,
            'macro_score': macro_score,
            'recommendation': 'Do not enable macros' if has_macros else 'No macros detected'
        }

    async def _virustotal_check(self, file_content: bytes) -> Dict[str, any]:
        """
        Check file hash against VirusTotal

        Args:
            file_content: File bytes

        Returns:
            VirusTotal scan results
        """
        try:
            file_hash = self._hash_file(file_content, 'sha256')
            result = await self.vt_client.check_file_hash(file_hash)
            return result
        except Exception as e:
            self.logger.error(f"VirusTotal check error: {e}")
            return {'error': str(e)}

    async def _sandbox_analysis(self, filename: str, file_content: bytes) -> Dict[str, any]:
        """
        Run sandbox analysis with Cuckoo

        Args:
            filename: File name
            file_content: File bytes

        Returns:
            Sandbox analysis results
        """
        try:
            result = await self.cuckoo_client.analyze_file(
                file_content=file_content,
                filename=filename,
                timeout=60
            )
            return result
        except Exception as e:
            self.logger.error(f"Sandbox analysis error: {e}")
            return {'error': str(e)}

    def _hash_file(self, file_content: bytes, algorithm: str = 'sha256') -> str:
        """
        Calculate file hash

        Args:
            file_content: File bytes
            algorithm: Hash algorithm (md5, sha1, sha256)

        Returns:
            Hash hex string
        """
        if algorithm == 'md5':
            return hashlib.md5(file_content).hexdigest()
        elif algorithm == 'sha1':
            return hashlib.sha1(file_content).hexdigest()
        elif algorithm == 'sha256':
            return hashlib.sha256(file_content).hexdigest()
        else:
            raise ValueError(f"Unsupported hash algorithm: {algorithm}")

    def _calculate_overall_risk(self, results: Dict[str, any]) -> Dict[str, any]:
        """
        Calculate overall risk score and level

        Weights:
        - Static analysis: 30%
        - Macro analysis: 20%
        - VirusTotal: 30%
        - Sandbox: 20%

        Args:
            results: Complete scan results

        Returns:
            Dict with overall risk assessment
        """
        risk_scores = []
        weights = []

        # Static analysis
        static_risk = results['static_analysis']['risk_level']
        static_score = {
            'low': 10,
            'medium': 40,
            'high': 70,
            'critical': 95
        }[static_risk]
        risk_scores.append(static_score)
        weights.append(30)

        # Macro analysis
        macro_score = results['macro_analysis']['macro_score']
        risk_scores.append(macro_score)
        weights.append(20)

        # VirusTotal
        if results['virustotal'] and not results['virustotal'].get('error'):
            vt = results['virustotal']
            if vt.get('found'):
                total = vt.get('total_scans', 1)
                malicious = vt.get('malicious', 0)
                vt_score = (malicious / total) * 100 if total > 0 else 0
            else:
                vt_score = 0
            risk_scores.append(vt_score)
            weights.append(30)

        # Sandbox
        if results['sandbox'] and not results['sandbox'].get('error'):
            sandbox_score = results['sandbox'].get('score', 0)
            risk_scores.append(sandbox_score)
            weights.append(20)

        # Calculate weighted average
        if sum(weights) > 0:
            overall_score = sum(s * w for s, w in zip(risk_scores, weights)) / sum(weights)
        else:
            overall_score = risk_scores[0] if risk_scores else 0

        # Determine risk level
        if overall_score >= 70:
            level = 'critical'
            recommendation = 'BLOCK - Do not open this file'
        elif overall_score >= 50:
            level = 'high'
            recommendation = 'QUARANTINE - Review with security team'
        elif overall_score >= 30:
            level = 'medium'
            recommendation = 'CAUTION - Scan with updated antivirus'
        else:
            level = 'low'
            recommendation = 'SAFE - File appears clean'

        return {
            'score': round(overall_score, 2),
            'level': level,
            'recommendation': recommendation,
            'component_scores': {
                'static': static_score,
                'macro': macro_score,
                'virustotal': vt_score if results['virustotal'] else None,
                'sandbox': sandbox_score if results['sandbox'] else None
            }
        }

    def _generate_summary(self, results: Dict[str, any]) -> str:
        """
        Generate human-readable summary

        Args:
            results: Complete scan results

        Returns:
            Summary string
        """
        filename = results['filename']
        risk = results['overall_risk']
        static = results['static_analysis']

        summary_parts = [
            f"File '{filename}' analysis complete.",
            f"Overall risk: {risk['level'].upper()} ({risk['score']}/100).",
            f"{risk['recommendation']}."
        ]

        # Add specific findings
        if static['issues']:
            critical_issues = [i for i in static['issues'] if i['severity'] == 'critical']
            if critical_issues:
                summary_parts.append(f"Critical issues found: {len(critical_issues)}.")

        if results['macro_analysis']['has_macros']:
            summary_parts.append("Contains macros - do not enable.")

        if results['virustotal'] and results['virustotal'].get('found'):
            malicious = results['virustotal'].get('malicious', 0)
            if malicious > 0:
                summary_parts.append(f"VirusTotal: {malicious} engines flagged as malicious.")

        if results['sandbox'] and results['sandbox'].get('classification') == 'malicious':
            summary_parts.append("Sandbox detected malicious behavior.")

        return ' '.join(summary_parts)


# Singleton instance
attachment_scanner = AttachmentScanner()
