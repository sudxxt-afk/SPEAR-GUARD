"""
URL Extractor Utility

Extracts and normalizes URLs from email content (plain text, HTML, headers).
Supports multiple formats and handles edge cases.

Author: SPEAR-GUARD Team
Date: 2025-11-05
"""

import re
import logging
from typing import List, Set, Dict, Optional
from urllib.parse import urlparse, unquote, parse_qs
from html.parser import HTMLParser
from email.message import Message

logger = logging.getLogger(__name__)


class HTMLLinkExtractor(HTMLParser):
    """
    Custom HTML parser to extract links from HTML content
    """

    def __init__(self):
        super().__init__()
        self.links = []
        self.in_a_tag = False
        self.current_href = None
        self.current_text = ""

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.in_a_tag = True
            self.current_text = ""
            for attr, value in attrs:
                if attr == 'href':
                    self.current_href = value

    def handle_endtag(self, tag):
        if tag == 'a' and self.in_a_tag:
            if self.current_href:
                self.links.append({
                    'url': self.current_href,
                    'text': self.current_text.strip()
                })
            self.in_a_tag = False
            self.current_href = None
            self.current_text = ""

    def handle_data(self, data):
        if self.in_a_tag:
            self.current_text += data


class URLExtractor:
    """
    Comprehensive URL extraction from email content

    Features:
    - Plain text URL extraction
    - HTML link extraction
    - Header URL extraction (X-headers, List-Unsubscribe, etc.)
    - URL normalization and deduplication
    - URL shortener detection
    - Homograph detection (IDN domains)
    """

    # Common URL shorteners
    URL_SHORTENERS = {
        'bit.ly', 'tinyurl.com', 'goo.gl', 'ow.ly', 't.co',
        'is.gd', 'buff.ly', 'adf.ly', 'bit.do', 'mcaf.ee',
        'su.pr', 'filoops.info', 'tiny.cc', 'cli.gs', 'pic.gd',
        'DwarfURL.com', 'yfrog.com', 'migre.me', 'ff.im', 'tiny.pl',
        'url4.eu', 'tr.im', 'twit.ac', 'post.ly', 'link.zip',
        'cutt.ly', 'rebrand.ly', 'short.io', 's.id', 'clck.ru'
    }

    # Regex patterns for URL extraction
    URL_PATTERN = re.compile(
        r'https?://(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}(?:/[^\s]*)?',
        re.IGNORECASE
    )

    # Pattern for email with clickable links
    EMAIL_LINK_PATTERN = re.compile(
        r'<a\s+(?:[^>]*?\s+)?href="([^"]*)"',
        re.IGNORECASE
    )

    # Homograph detection - mixing scripts.
    # BUG-17 fix: ensure sets are properly constructed (fallback to empty if encoding damaged).
    CYRILLIC_CHARS = set('абвгдеёжзийклмнопрстуфхцчшщъыьэюяАВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ')
    GREEK_CHARS = set('αβγδεζηθικλμνξοπρστυφχψωΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩ')

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.URLExtractor")

    def extract_all_urls(
        self,
        body_text: Optional[str] = None,
        body_html: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> List[Dict[str, any]]:
        """
        Extract all URLs from email content

        Args:
            body_text: Plain text body
            body_html: HTML body
            headers: Email headers dict

        Returns:
            List of URL info dicts with metadata
        """
        all_urls = []
        seen_urls = set()

        # Extract from plain text
        if body_text:
            text_urls = self._extract_from_text(body_text)
            for url_info in text_urls:
                url = url_info['url']
                if url not in seen_urls:
                    all_urls.append(url_info)
                    seen_urls.add(url)

        # Extract from HTML
        if body_html:
            html_urls = self._extract_from_html(body_html)
            for url_info in html_urls:
                url = url_info['url']
                if url not in seen_urls:
                    all_urls.append(url_info)
                    seen_urls.add(url)

        # Extract from headers
        if headers:
            header_urls = self._extract_from_headers(headers)
            for url_info in header_urls:
                url = url_info['url']
                if url not in seen_urls:
                    all_urls.append(url_info)
                    seen_urls.add(url)

        # Normalize and analyze each URL
        for url_info in all_urls:
            self._analyze_url(url_info)

        self.logger.info(f"Extracted {len(all_urls)} unique URLs")
        return all_urls

    def _extract_from_text(self, text: str) -> List[Dict[str, any]]:
        """
        Extract URLs from plain text

        Args:
            text: Plain text content

        Returns:
            List of URL info dicts
        """
        urls = []
        matches = self.URL_PATTERN.finditer(text)

        for match in matches:
            url = match.group(0)
            urls.append({
                'url': url,
                'source': 'text',
                'display_text': None
            })

        return urls

    def _extract_from_html(self, html: str) -> List[Dict[str, any]]:
        """
        Extract URLs from HTML content

        Args:
            html: HTML content

        Returns:
            List of URL info dicts with display text
        """
        urls = []

        try:
            parser = HTMLLinkExtractor()
            parser.feed(html)

            for link in parser.links:
                urls.append({
                    'url': link['url'],
                    'source': 'html',
                    'display_text': link['text']
                })

        except Exception as e:
            self.logger.error(f"HTML parsing error: {e}")

            # Fallback to regex
            matches = self.EMAIL_LINK_PATTERN.finditer(html)
            for match in matches:
                url = match.group(1)
                urls.append({
                    'url': url,
                    'source': 'html',
                    'display_text': None
                })

        return urls

    def _extract_from_headers(self, headers: Dict[str, str]) -> List[Dict[str, any]]:
        """
        Extract URLs from email headers

        Common headers with URLs:
        - List-Unsubscribe
        - List-Subscribe
        - X-* custom headers
        - Reply-To (sometimes contains URLs)

        Args:
            headers: Email headers dict

        Returns:
            List of URL info dicts
        """
        urls = []

        # Headers that commonly contain URLs
        url_headers = [
            'List-Unsubscribe',
            'List-Subscribe',
            'List-Post',
            'List-Archive'
        ]

        for header_name, header_value in headers.items():
            # Check specific URL headers
            if header_name in url_headers:
                matches = self.URL_PATTERN.finditer(header_value)
                for match in matches:
                    urls.append({
                        'url': match.group(0),
                        'source': f'header:{header_name}',
                        'display_text': None
                    })

            # Check X-* custom headers
            elif header_name.startswith('X-') and 'http' in header_value.lower():
                matches = self.URL_PATTERN.finditer(header_value)
                for match in matches:
                    urls.append({
                        'url': match.group(0),
                        'source': f'header:{header_name}',
                        'display_text': None
                    })

        return urls

    def _analyze_url(self, url_info: Dict[str, any]) -> None:
        """
        Analyze URL and add metadata

        Adds:
        - Parsed components (scheme, domain, path, query)
        - Is shortener
        - Is homograph (IDN)
        - Has suspicious patterns

        Args:
            url_info: URL info dict (modified in place)
        """
        url = url_info['url']

        try:
            # Parse URL
            parsed = urlparse(url)

            url_info['parsed'] = {
                'scheme': parsed.scheme,
                'domain': parsed.netloc,
                'path': parsed.path,
                'query': parsed.query,
                'fragment': parsed.fragment
            }

            # Check if URL shortener
            domain = parsed.netloc.lower()
            url_info['is_shortener'] = domain in self.URL_SHORTENERS

            # Check for homograph attack (IDN domain)
            url_info['is_idn'] = self._is_homograph(domain)

            # Check for suspicious patterns
            url_info['suspicious_patterns'] = self._detect_suspicious_patterns(url)

            # Check display text mismatch
            if url_info.get('display_text'):
                url_info['display_mismatch'] = self._check_display_mismatch(
                    url,
                    url_info['display_text']
                )

        except Exception as e:
            self.logger.error(f"URL analysis error for {url}: {e}")
            url_info['analysis_error'] = str(e)

    def _is_homograph(self, domain: str) -> bool:
        """
        Detect homograph attack (mixing Latin with Cyrillic/Greek)

        Args:
            domain: Domain name

        Returns:
            True if potential homograph attack
        """
        # Check if domain uses non-ASCII characters
        if not domain.isascii():
            # Try to decode IDN
            try:
                decoded = domain.encode('idna').decode('ascii')
                # If it starts with 'xn--', it's an IDN domain
                return 'xn--' in decoded
            except:
                pass

        # Check for mixing of character sets
        chars = set(domain)
        has_latin = any(c.isalpha() and c.isascii() for c in chars)
        has_cyrillic = bool(chars & self.CYRILLIC_CHARS)
        has_greek = bool(chars & self.GREEK_CHARS)

        # Mixing scripts is suspicious
        if has_latin and (has_cyrillic or has_greek):
            return True

        return False

    def _detect_suspicious_patterns(self, url: str) -> List[str]:
        """
        Detect suspicious URL patterns

        Patterns:
        - IP address instead of domain
        - Excessive subdomains
        - Suspicious keywords
        - Port numbers
        - @ symbol (user:pass@domain)

        Args:
            url: URL string

        Returns:
            List of detected suspicious patterns
        """
        patterns = []
        parsed = urlparse(url)
        domain = parsed.netloc

        # IP address instead of domain
        ip_pattern = re.compile(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}')
        if ip_pattern.match(domain.split(':')[0]):  # Remove port if present
            patterns.append('ip_address')

        # @ symbol (user credentials)
        if '@' in domain:
            patterns.append('credentials_in_url')

        # Port number (unusual)
        if ':' in domain and not domain.endswith(':80') and not domain.endswith(':443'):
            patterns.append('unusual_port')

        # Excessive subdomains (>3 dots)
        if domain.count('.') > 3:
            patterns.append('excessive_subdomains')

        # Suspicious keywords in path/query
        suspicious_keywords = [
            'login', 'signin', 'verify', 'account', 'update',
            'secure', 'confirm', 'banking', 'password', 'wallet'
        ]
        url_lower = url.lower()
        for keyword in suspicious_keywords:
            if keyword in url_lower:
                patterns.append(f'keyword:{keyword}')
                break  # Only flag once

        # Very long URL (>200 chars)
        if len(url) > 200:
            patterns.append('very_long_url')

        # Double slashes in path
        if '//' in parsed.path:
            patterns.append('double_slashes')

        return patterns

    def _check_display_mismatch(self, url: str, display_text: str) -> bool:
        """
        Check if display text doesn't match actual URL

        Common phishing tactic: <a href="evil.com">legitimate-bank.com</a>

        Args:
            url: Actual URL
            display_text: Displayed text

        Returns:
            True if mismatch detected
        """
        if not display_text:
            return False

        # Extract domain from URL
        try:
            parsed = urlparse(url)
            url_domain = parsed.netloc.lower()

            # Check if display text looks like a domain/URL
            if '.' in display_text and ' ' not in display_text:
                display_lower = display_text.lower().strip()

                # Remove http(s):// if present
                display_lower = re.sub(r'^https?://', '', display_lower)

                # Compare domains
                if url_domain not in display_lower and display_lower not in url_domain:
                    return True

        except Exception as e:
            self.logger.error(f"Display mismatch check error: {e}")

        return False

    def normalize_url(self, url: str) -> str:
        """
        Normalize URL for comparison

        - Remove tracking parameters
        - Lowercase domain
        - Remove fragments
        - Decode URL encoding

        Args:
            url: Raw URL

        Returns:
            Normalized URL
        """
        try:
            parsed = urlparse(url)

            # Lowercase domain
            domain = parsed.netloc.lower()

            # Remove tracking parameters
            query_params = parse_qs(parsed.query)
            tracking_params = ['utm_source', 'utm_medium', 'utm_campaign', 'fbclid', 'gclid']
            filtered_params = {k: v for k, v in query_params.items() if k not in tracking_params}

            # Reconstruct query string
            from urllib.parse import urlencode
            query = urlencode(filtered_params, doseq=True) if filtered_params else ''

            # Reconstruct URL (without fragment)
            normalized = f"{parsed.scheme}://{domain}{parsed.path}"
            if query:
                normalized += f"?{query}"

            # Decode URL encoding
            normalized = unquote(normalized)

            return normalized

        except Exception as e:
            self.logger.error(f"URL normalization error: {e}")
            return url

    def get_base_domain(self, url: str) -> Optional[str]:
        """
        Extract base domain from URL

        Args:
            url: Full URL

        Returns:
            Base domain (e.g., 'example.com')
        """
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()

            # Remove port
            domain = domain.split(':')[0]

            # Get base domain (last 2 parts)
            parts = domain.split('.')
            if len(parts) >= 2:
                return '.'.join(parts[-2:])

            return domain

        except Exception as e:
            self.logger.error(f"Base domain extraction error: {e}")
            return None


# Singleton instance
url_extractor = URLExtractor()
