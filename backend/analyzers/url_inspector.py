"""
URL Inspector

Comprehensive URL analysis for phishing detection including:
- Homograph detection (IDN/punycode)
- URL shortener detection
- Domain age check (WHOIS)
- VirusTotal reputation
- Phishing pattern detection
- Display text mismatch
- Suspicious TLD detection

Author: SPEAR-GUARD Team
Date: 2025-11-05
"""

import asyncio
import logging
import re
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from urllib.parse import urlparse
import socket

# Import utilities and integrations
from utils.url_extractor import url_extractor
from integrations.virustotal import virustotal_client

logger = logging.getLogger(__name__)


class URLInspector:
    """
    Comprehensive URL security inspector

    Multi-layer analysis:
    1. URL structure analysis
    2. Homograph/IDN detection
    3. Domain reputation (VirusTotal)
    4. Phishing pattern detection
    5. URL shortener detection
    6. WHOIS/Domain age check
    7. Risk scoring
    """

    # Suspicious TLDs (commonly used in phishing)
    SUSPICIOUS_TLDS = {
        '.tk', '.ml', '.ga', '.cf', '.gq',  # Free TLDs
        '.xyz', '.top', '.work', '.click', '.link',
        '.loan', '.win', '.bid', '.review', '.party',
        '.science', '.date', '.download', '.stream'
    }

    # Trusted TLDs
    TRUSTED_TLDS = {
        '.gov', '.mil', '.edu', '.gov.ru', '.mil.ru'
    }

    # Phishing keywords in URLs
    PHISHING_KEYWORDS = [
        'login', 'signin', 'verify', 'account', 'update',
        'secure', 'banking', 'paypal', 'confirm', 'suspended',
        'locked', 'unusual', 'activity', 'password', 'verification',
        'wallet', 'restore', 'recover', 'validate', 'authorize'
    ]

    # Legitimate domains (whitelist)
    LEGITIMATE_DOMAINS = {
        'google.com', 'microsoft.com', 'apple.com', 'amazon.com',
        'gov.ru', 'gosuslugi.ru', 'mos.ru', 'nalog.ru',
        'github.com', 'stackoverflow.com', 'wikipedia.org'
    }

    def __init__(self):
        """Initialize URL inspector"""
        self.logger = logging.getLogger(f"{__name__}.URLInspector")
        self.extractor = url_extractor
        self.vt_client = virustotal_client

    async def analyze_url(
        self,
        url: str,
        display_text: Optional[str] = None,
        enable_virustotal: bool = True,
        enable_whois: bool = False  # Slow, disabled by default
    ) -> Dict[str, any]:
        """
        Comprehensive URL analysis

        Args:
            url: URL to analyze
            display_text: Display text (if from HTML link)
            enable_virustotal: Enable VirusTotal check
            enable_whois: Enable WHOIS domain age check

        Returns:
            Dict with complete analysis results
        """
        self.logger.info(f"Analyzing URL: {url}")

        start_time = datetime.utcnow()

        # Parse URL
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            base_domain = self.extractor.get_base_domain(url)
        except Exception as e:
            self.logger.error(f"URL parsing error: {e}")
            return {
                'url': url,
                'error': f'Invalid URL: {str(e)}',
                'risk_level': 'unknown'
            }

        # Run parallel checks
        tasks = []

        # 1. Structure analysis (synchronous)
        structure_analysis = self._analyze_structure(url, parsed, display_text)

        # 2. Phishing patterns (synchronous)
        phishing_patterns = self._detect_phishing_patterns(url, parsed)

        # 3. Homograph detection (synchronous)
        homograph_check = self._check_homograph(domain)

        # 4. VirusTotal reputation
        if enable_virustotal:
            tasks.append(self._check_virustotal(url, base_domain))
        else:
            tasks.append(asyncio.sleep(0))

        # 5. WHOIS domain age (optional, slow)
        if enable_whois:
            tasks.append(self._check_domain_age(base_domain))
        else:
            tasks.append(asyncio.sleep(0))

        # Wait for async tasks
        vt_result, whois_result = await asyncio.gather(*tasks)

        # Compile results
        results = {
            'url': url,
            'parsed': {
                'scheme': parsed.scheme,
                'domain': domain,
                'base_domain': base_domain,
                'path': parsed.path,
                'query': parsed.query
            },
            'structure_analysis': structure_analysis,
            'phishing_patterns': phishing_patterns,
            'homograph': homograph_check,
            'virustotal': vt_result if enable_virustotal else None,
            'domain_age': whois_result if enable_whois else None,
            'scan_time': (datetime.utcnow() - start_time).total_seconds(),
            'timestamp': datetime.utcnow().isoformat()
        }

        # Calculate overall risk
        results['overall_risk'] = self._calculate_risk(results)

        # Generate summary
        results['summary'] = self._generate_summary(results)

        self.logger.info(f"Analysis complete: {url} - Risk: {results['overall_risk']['level']}")

        return results

    async def analyze_multiple_urls(
        self,
        urls: List[str],
        enable_virustotal: bool = True
    ) -> List[Dict[str, any]]:
        """
        Analyze multiple URLs in parallel

        Args:
            urls: List of URLs
            enable_virustotal: Enable VirusTotal checks

        Returns:
            List of analysis results
        """
        tasks = [
            self.analyze_url(url, enable_virustotal=enable_virustotal)
            for url in urls
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle exceptions
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                final_results.append({
                    'url': urls[i],
                    'error': str(result),
                    'risk_level': 'unknown'
                })
            else:
                final_results.append(result)

        return final_results

    def _analyze_structure(
        self,
        url: str,
        parsed,
        display_text: Optional[str]
    ) -> Dict[str, any]:
        """
        Analyze URL structure for suspicious elements

        Args:
            url: Full URL
            parsed: Parsed URL object
            display_text: Display text (if any)

        Returns:
            Dict with structure analysis
        """
        issues = []
        domain = parsed.netloc.lower()

        # Check for IP address
        ip_pattern = re.compile(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}')
        if ip_pattern.match(domain.split(':')[0]):
            issues.append({
                'type': 'ip_address',
                'severity': 'high',
                'description': 'URL uses IP address instead of domain name'
            })

        # Check for @ symbol (credentials)
        if '@' in domain:
            issues.append({
                'type': 'credentials_in_url',
                'severity': 'critical',
                'description': 'URL contains username/password (phishing tactic)'
            })

        # Check for unusual port
        if ':' in domain:
            port = domain.split(':')[-1]
            if port not in ['80', '443', '8080', '8443']:
                issues.append({
                    'type': 'unusual_port',
                    'severity': 'medium',
                    'description': f'Unusual port number: {port}'
                })

        # Check subdomain count
        subdomain_count = domain.count('.')
        if subdomain_count > 3:
            issues.append({
                'type': 'excessive_subdomains',
                'severity': 'medium',
                'description': f'Too many subdomains: {subdomain_count}'
            })

        # Check URL length
        if len(url) > 200:
            issues.append({
                'type': 'very_long_url',
                'severity': 'low',
                'description': f'Very long URL: {len(url)} characters'
            })

        # Check for suspicious TLD
        base_domain = self.extractor.get_base_domain(url)
        if base_domain:
            for tld in self.SUSPICIOUS_TLDS:
                if base_domain.endswith(tld):
                    issues.append({
                        'type': 'suspicious_tld',
                        'severity': 'high',
                        'description': f'Suspicious top-level domain: {tld}'
                    })
                    break

        # Check display text mismatch
        if display_text and self.extractor._check_display_mismatch(url, display_text):
            issues.append({
                'type': 'display_mismatch',
                'severity': 'critical',
                'description': f'Display text "{display_text}" doesn\'t match actual URL'
            })

        # Check if URL shortener
        is_shortener = domain in self.extractor.URL_SHORTENERS
        if is_shortener:
            issues.append({
                'type': 'url_shortener',
                'severity': 'medium',
                'description': 'URL shortener used (destination unknown)'
            })

        return {
            'issues': issues,
            'is_shortener': is_shortener,
            'url_length': len(url),
            'subdomain_count': subdomain_count
        }

    def _detect_phishing_patterns(self, url: str, parsed) -> Dict[str, any]:
        """
        Detect common phishing patterns

        Args:
            url: Full URL
            parsed: Parsed URL object

        Returns:
            Dict with phishing pattern detection
        """
        url_lower = url.lower()
        domain_lower = parsed.netloc.lower()
        path_lower = parsed.path.lower()

        patterns_found = []

        # Check for phishing keywords
        for keyword in self.PHISHING_KEYWORDS:
            if keyword in url_lower:
                patterns_found.append({
                    'keyword': keyword,
                    'location': 'domain' if keyword in domain_lower else 'path',
                    'severity': 'high' if keyword in domain_lower else 'medium'
                })

        # Check for brand impersonation in subdomain
        # e.g., paypal.secure-login.com (impersonating paypal.com)
        known_brands = [
            'paypal', 'google', 'microsoft', 'apple', 'amazon',
            'facebook', 'instagram', 'twitter', 'bank', 'visa',
            'mastercard', 'sberbank', 'vtb', 'alfabank'
        ]

        for brand in known_brands:
            # Brand in subdomain but not in base domain
            if brand in domain_lower:
                base_domain = self.extractor.get_base_domain(url)
                if base_domain and brand not in base_domain:
                    patterns_found.append({
                        'keyword': brand,
                        'location': 'subdomain',
                        'severity': 'critical',
                        'description': f'Brand "{brand}" in subdomain - possible impersonation'
                    })

        # Check for suspicious character combinations
        if any(combo in domain_lower for combo in ['--', '..']):
            patterns_found.append({
                'keyword': 'special_chars',
                'location': 'domain',
                'severity': 'medium',
                'description': 'Unusual character combinations in domain'
            })

        # Calculate phishing score
        phishing_score = 0
        for pattern in patterns_found:
            if pattern['severity'] == 'critical':
                phishing_score += 40
            elif pattern['severity'] == 'high':
                phishing_score += 25
            elif pattern['severity'] == 'medium':
                phishing_score += 15

        phishing_score = min(phishing_score, 100)

        return {
            'patterns_found': patterns_found,
            'phishing_score': phishing_score,
            'is_likely_phishing': phishing_score >= 50
        }

    def _check_homograph(self, domain: str) -> Dict[str, any]:
        """
        Check for homograph attack (IDN spoofing)

        Args:
            domain: Domain name

        Returns:
            Dict with homograph detection results
        """
        is_idn = self.extractor._is_homograph(domain)

        result = {
            'is_idn': is_idn,
            'is_homograph': False,
            'details': None
        }

        if is_idn:
            # Try to decode IDN
            try:
                if 'xn--' in domain:
                    decoded = domain.encode('ascii').decode('idna')
                    result['decoded_domain'] = decoded
                    result['is_homograph'] = True
                    result['details'] = f'IDN domain: {domain} → {decoded}'
                else:
                    result['is_homograph'] = True
                    result['details'] = 'Mixed character sets detected (possible spoofing)'
            except Exception as e:
                result['details'] = f'IDN decoding error: {str(e)}'

        return result

    async def _check_virustotal(self, url: str, domain: str) -> Dict[str, any]:
        """
        Check URL and domain reputation with VirusTotal

        Args:
            url: Full URL
            domain: Domain name

        Returns:
            Combined VirusTotal results
        """
        try:
            # Run URL and domain checks in parallel
            url_check, domain_check = await asyncio.gather(
                self.vt_client.scan_url(url),
                self.vt_client.check_domain_reputation(domain)
            )

            return {
                'url_scan': url_check,
                'domain_reputation': domain_check
            }
        except Exception as e:
            self.logger.error(f"VirusTotal check error: {e}")
            return {'error': str(e)}

    async def _check_domain_age(self, domain: str) -> Dict[str, any]:
        """
        Check domain age using WHOIS (mock for now)

        Young domains (<30 days) are suspicious for phishing

        Args:
            domain: Domain name

        Returns:
            Dict with domain age info
        """
        # Mock implementation
        # In production, use python-whois library
        await asyncio.sleep(0.5)

        # Mock: trusted domains are old, suspicious ones are new
        if any(td in domain for td in self.LEGITIMATE_DOMAINS):
            creation_date = datetime.now() - timedelta(days=3650)  # 10 years
            age_days = 3650
        elif any(kw in domain for kw in ['evil', 'phish', 'scam', 'fake']):
            creation_date = datetime.now() - timedelta(days=5)  # 5 days
            age_days = 5
        else:
            creation_date = datetime.now() - timedelta(days=365)  # 1 year
            age_days = 365

        is_new = age_days < 30
        is_very_new = age_days < 7

        return {
            'creation_date': creation_date.isoformat(),
            'age_days': age_days,
            'is_new_domain': is_new,
            'is_very_new_domain': is_very_new,
            'warning': 'Very new domain - high phishing risk' if is_very_new else None
        }

    def _calculate_risk(self, results: Dict[str, any]) -> Dict[str, any]:
        """
        Calculate overall URL risk score

        Weights:
        - Structure analysis: 25%
        - Phishing patterns: 30%
        - Homograph: 15%
        - VirusTotal: 30%

        Args:
            results: Complete analysis results

        Returns:
            Dict with risk assessment
        """
        risk_scores = []
        weights = []

        # Structure analysis
        structure_issues = results['structure_analysis']['issues']
        critical_count = sum(1 for i in structure_issues if i['severity'] == 'critical')
        high_count = sum(1 for i in structure_issues if i['severity'] == 'high')
        medium_count = sum(1 for i in structure_issues if i['severity'] == 'medium')

        structure_score = min(
            (critical_count * 40) + (high_count * 25) + (medium_count * 15),
            100
        )
        risk_scores.append(structure_score)
        weights.append(25)

        # Phishing patterns
        phishing_score = results['phishing_patterns']['phishing_score']
        risk_scores.append(phishing_score)
        weights.append(30)

        # Homograph
        homograph_score = 80 if results['homograph']['is_homograph'] else 0
        risk_scores.append(homograph_score)
        weights.append(15)

        # VirusTotal
        if results['virustotal'] and not results['virustotal'].get('error'):
            vt = results['virustotal']

            # URL scan
            url_scan = vt.get('url_scan', {})
            if url_scan.get('malicious', 0) > 0:
                vt_score = 90
            elif url_scan.get('suspicious', 0) > 0:
                vt_score = 60
            else:
                vt_score = 0

            # Domain reputation
            domain_rep = vt.get('domain_reputation', {})
            rep_score = domain_rep.get('reputation', 0)
            if rep_score < -20:
                vt_score = max(vt_score, 85)
            elif rep_score < 0:
                vt_score = max(vt_score, 50)

            risk_scores.append(vt_score)
            weights.append(30)

        # Calculate weighted average
        if sum(weights) > 0:
            overall_score = sum(s * w for s, w in zip(risk_scores, weights)) / sum(weights)
        else:
            overall_score = risk_scores[0] if risk_scores else 0

        # Check if in whitelist
        base_domain = results['parsed']['base_domain']
        if base_domain in self.LEGITIMATE_DOMAINS:
            overall_score = min(overall_score, 20)  # Cap at low risk

        # Determine risk level
        if overall_score >= 70:
            level = 'critical'
            recommendation = 'BLOCK - Do not visit this URL'
        elif overall_score >= 50:
            level = 'high'
            recommendation = 'DANGEROUS - Likely phishing/malware'
        elif overall_score >= 30:
            level = 'medium'
            recommendation = 'SUSPICIOUS - Proceed with caution'
        else:
            level = 'low'
            recommendation = 'SAFE - URL appears legitimate'

        return {
            'score': round(overall_score, 2),
            'level': level,
            'recommendation': recommendation,
            'component_scores': {
                'structure': structure_score,
                'phishing': phishing_score,
                'homograph': homograph_score,
                'virustotal': vt_score if results['virustotal'] else None
            }
        }

    def _generate_summary(self, results: Dict[str, any]) -> str:
        """
        Generate human-readable summary

        Args:
            results: Complete analysis results

        Returns:
            Summary string
        """
        url = results['url']
        risk = results['overall_risk']

        summary_parts = [
            f"URL '{url}' analysis complete.",
            f"Overall risk: {risk['level'].upper()} ({risk['score']}/100).",
            f"{risk['recommendation']}."
        ]

        # Add specific warnings
        if results['structure_analysis']['is_shortener']:
            summary_parts.append("URL shortener detected - destination unknown.")

        if results['phishing_patterns']['is_likely_phishing']:
            summary_parts.append("Phishing patterns detected.")

        if results['homograph']['is_homograph']:
            summary_parts.append("Homograph attack detected (look-alike domain).")

        if results['virustotal'] and not results['virustotal'].get('error'):
            url_scan = results['virustotal'].get('url_scan', {})
            if url_scan.get('malicious', 0) > 0:
                summary_parts.append(
                    f"VirusTotal: {url_scan['malicious']} engines flagged as malicious."
                )

        return ' '.join(summary_parts)


# Singleton instance
url_inspector = URLInspector()
