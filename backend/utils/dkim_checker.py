"""
DKIM (DomainKeys Identified Mail) Checker
Validates DKIM signatures for email authentication
"""
import logging
import asyncio
from typing import Dict, Optional, List
from concurrent.futures import ThreadPoolExecutor
import email
from email import policy

logger = logging.getLogger(__name__)

# Thread pool for blocking operations
executor = ThreadPoolExecutor(max_workers=4)


class DKIMChecker:
    """DKIM validation using dkimpy"""

    def __init__(self):
        pass

    async def verify_dkim(
        self,
        raw_email: bytes,
        sender_domain: Optional[str] = None
    ) -> Dict:
        """
        Verify DKIM signature in email

        Args:
            raw_email: Raw email message as bytes
            sender_domain: Expected sender domain (optional)

        Returns:
            Dict with DKIM validation results
        """
        logger.info(f"Verifying DKIM signature")

        try:
            # Run DKIM verification in thread pool
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                executor,
                self._verify_dkim_sync,
                raw_email,
                sender_domain
            )

            return result

        except Exception as e:
            logger.error(f"DKIM verification error: {e}", exc_info=True)
            return self._create_error_result(str(e))

    def _verify_dkim_sync(
        self,
        raw_email: bytes,
        sender_domain: Optional[str]
    ) -> Dict:
        """Synchronous DKIM verification (runs in thread pool)"""
        try:
            import dkim

            # Verify DKIM signature
            result = dkim.verify(raw_email)

            # Extract DKIM signature info
            signature_info = self._extract_dkim_info(raw_email)

            # Determine score
            score = 100 if result else 0

            # Get signing domain
            signing_domain = signature_info.get('domain', None)

            # Check alignment if sender domain provided
            aligned = None
            if sender_domain and signing_domain:
                aligned = self._check_dkim_alignment(sender_domain, signing_domain)

            return {
                'result': 'pass' if result else 'fail',
                'valid': result,
                'score': score,
                'signature_info': signature_info,
                'signing_domain': signing_domain,
                'aligned': aligned,
                'details': self._get_result_details(result, signature_info)
            }

        except Exception as e:
            logger.error(f"Sync DKIM verification error: {e}")
            return self._create_error_result(str(e))

    def _extract_dkim_info(self, raw_email: bytes) -> Dict:
        """Extract DKIM signature information from email"""
        try:
            # Parse email
            msg = email.message_from_bytes(raw_email, policy=policy.default)

            # Get DKIM-Signature header
            dkim_header = msg.get('DKIM-Signature', '')

            if not dkim_header:
                return {
                    'present': False,
                    'domain': None,
                    'selector': None,
                    'algorithm': None
                }

            # Parse DKIM signature tags
            tags = {}
            for part in dkim_header.split(';'):
                part = part.strip()
                if '=' in part:
                    key, value = part.split('=', 1)
                    tags[key.strip()] = value.strip()

            return {
                'present': True,
                'domain': tags.get('d', None),
                'selector': tags.get('s', None),
                'algorithm': tags.get('a', None),
                'canonicalization': tags.get('c', None),
                'headers': tags.get('h', None),
                'signature': tags.get('b', 'present')[:20] + '...',  # Truncate
                'body_hash': tags.get('bh', 'present')[:20] + '...',  # Truncate
                'raw_header': dkim_header[:100] + '...'  # Truncate for display
            }

        except Exception as e:
            logger.error(f"Error extracting DKIM info: {e}")
            return {'present': False, 'error': str(e)}

    def _check_dkim_alignment(
        self,
        from_domain: str,
        signing_domain: str
    ) -> bool:
        """Check DKIM alignment (RFC 7489)"""
        # Relaxed alignment: organizational domain match
        def get_org_domain(domain: str) -> str:
            parts = domain.lower().split('.')
            if len(parts) >= 2:
                return '.'.join(parts[-2:])
            return domain.lower()

        return get_org_domain(from_domain) == get_org_domain(signing_domain)

    def _get_result_details(self, result: bool, signature_info: Dict) -> str:
        """Get human-readable DKIM result"""
        if not signature_info.get('present'):
            return 'ℹ️ DKIM NONE: No DKIM signature found'

        if result:
            domain = signature_info.get('domain', 'unknown')
            selector = signature_info.get('selector', 'unknown')
            algo = signature_info.get('algorithm', 'unknown')
            return f'✅ DKIM PASS: Signed by {domain} (selector: {selector}, algo: {algo})'
        else:
            return '❌ DKIM FAIL: Signature verification failed'

    def _create_error_result(self, error_msg: str) -> Dict:
        """Create error result dict"""
        return {
            'result': 'error',
            'valid': False,
            'score': 0,
            'signature_info': {'present': False, 'error': error_msg},
            'signing_domain': None,
            'aligned': None,
            'details': f'❌ DKIM Error: {error_msg}'
        }

    async def verify_dkim_from_headers(
        self,
        headers: Dict[str, str],
        body: str
    ) -> Dict:
        """
        Verify DKIM from parsed headers and body

        Args:
            headers: Email headers dict
            body: Email body

        Returns:
            Dict with DKIM validation results
        """
        try:
            # Reconstruct raw email
            raw_email = self._reconstruct_email(headers, body)

            # Verify
            return await self.verify_dkim(raw_email)

        except Exception as e:
            logger.error(f"Error verifying DKIM from headers: {e}")
            return self._create_error_result(str(e))

    def _reconstruct_email(self, headers: Dict[str, str], body: str) -> bytes:
        """Reconstruct raw email from headers and body"""
        lines = []

        # Add headers
        for key, value in headers.items():
            lines.append(f"{key}: {value}")

        # Empty line between headers and body
        lines.append("")

        # Add body
        lines.append(body)

        # Join and encode
        return '\r\n'.join(lines).encode('utf-8')


class DKIMAlignmentChecker:
    """Check DKIM alignment for DMARC"""

    @staticmethod
    def check_alignment(
        from_domain: str,
        signing_domain: str,
        strict: bool = False
    ) -> Dict:
        """
        Check DKIM alignment

        Args:
            from_domain: Domain from From header
            signing_domain: Domain from DKIM signature (d= tag)
            strict: Use strict alignment (default: relaxed)

        Returns:
            Dict with alignment results
        """
        logger.debug(f"Checking DKIM alignment: {from_domain} vs {signing_domain}")

        if not signing_domain:
            return {
                'aligned': False,
                'strict_aligned': False,
                'relaxed_aligned': False,
                'from_domain': from_domain,
                'signing_domain': None,
                'details': '❌ DKIM Not Aligned: No signing domain'
            }

        # Strict alignment: exact match
        strict_aligned = from_domain.lower() == signing_domain.lower()

        # Relaxed alignment: organizational domain match
        relaxed_aligned = DKIMAlignmentChecker._check_org_domain(
            from_domain,
            signing_domain
        )

        aligned = strict_aligned if strict else relaxed_aligned

        return {
            'aligned': aligned,
            'strict_aligned': strict_aligned,
            'relaxed_aligned': relaxed_aligned,
            'from_domain': from_domain,
            'signing_domain': signing_domain,
            'details': DKIMAlignmentChecker._get_details(
                strict_aligned,
                relaxed_aligned,
                from_domain,
                signing_domain
            )
        }

    @staticmethod
    def _check_org_domain(domain1: str, domain2: str) -> bool:
        """Check if domains share organizational domain"""
        def get_org_domain(domain: str) -> str:
            parts = domain.lower().split('.')
            if len(parts) >= 2:
                return '.'.join(parts[-2:])
            return domain.lower()

        return get_org_domain(domain1) == get_org_domain(domain2)

    @staticmethod
    def _get_details(
        strict: bool,
        relaxed: bool,
        from_domain: str,
        signing_domain: str
    ) -> str:
        """Get alignment details"""
        if strict:
            return f'✅ DKIM Aligned (Strict): {from_domain} = {signing_domain}'
        elif relaxed:
            return f'✅ DKIM Aligned (Relaxed): {from_domain} ≈ {signing_domain}'
        else:
            return f'❌ DKIM Not Aligned: {from_domain} ≠ {signing_domain}'


# Singleton instance
dkim_checker = DKIMChecker()


# Convenience functions
async def verify_dkim(raw_email: bytes, sender_domain: Optional[str] = None) -> Dict:
    """Verify DKIM signature"""
    return await dkim_checker.verify_dkim(raw_email, sender_domain)


async def verify_dkim_from_headers(headers: Dict[str, str], body: str) -> Dict:
    """Verify DKIM from headers and body"""
    return await dkim_checker.verify_dkim_from_headers(headers, body)


def check_dkim_alignment(
    from_domain: str,
    signing_domain: str,
    strict: bool = False
) -> Dict:
    """Check DKIM alignment"""
    return DKIMAlignmentChecker.check_alignment(from_domain, signing_domain, strict)
