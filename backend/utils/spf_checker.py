"""
SPF (Sender Policy Framework) Checker
Validates SPF records for email authentication
"""
import logging
import asyncio
from typing import Dict, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor
import dns.resolver
import dns.exception

logger = logging.getLogger(__name__)

# Thread pool for blocking DNS operations
executor = ThreadPoolExecutor(max_workers=4)


class SPFChecker:
    """SPF validation using pyspf and dnspython"""

    def __init__(self):
        self.resolver = dns.resolver.Resolver()
        self.resolver.timeout = 5.0
        self.resolver.lifetime = 5.0

    async def verify_spf(
        self,
        sender_email: str,
        sender_ip: str,
        helo_domain: Optional[str] = None
    ) -> Dict:
        """
        Verify SPF record for sender

        Args:
            sender_email: Email address of sender
            sender_ip: IP address of sending server
            helo_domain: HELO/EHLO domain (optional)

        Returns:
            Dict with SPF validation results
        """
        logger.info(f"Verifying SPF for {sender_email} from {sender_ip}")

        try:
            # Extract domain from email
            if '@' not in sender_email:
                return self._create_error_result("Invalid email format")

            domain = sender_email.split('@')[1].lower()

            # Run SPF check in thread pool (blocking operation)
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                executor,
                self._check_spf_sync,
                sender_ip,
                sender_email,
                domain,
                helo_domain
            )

            return result

        except Exception as e:
            logger.error(f"SPF verification error: {e}", exc_info=True)
            return self._create_error_result(str(e))

    def _check_spf_sync(
        self,
        sender_ip: str,
        sender_email: str,
        domain: str,
        helo_domain: Optional[str]
    ) -> Dict:
        """Synchronous SPF check (runs in thread pool)"""
        try:
            import spf

            # Prepare query
            query_params = {
                'i': sender_ip,
                's': sender_email,
                'h': helo_domain or domain
            }

            # Query SPF
            result, explanation = spf.check2(
                i=sender_ip,
                s=sender_email,
                h=helo_domain or domain
            )

            # Map result to score
            score_map = {
                'pass': 100,
                'none': 50,
                'neutral': 50,
                'softfail': 20,
                'fail': 0,
                'temperror': 30,
                'permerror': 10
            }

            score = score_map.get(result, 0)

            # Get SPF record details
            spf_record = self._get_spf_record(domain)

            return {
                'result': result,
                'explanation': explanation,
                'score': score,
                'valid': result in ['pass', 'neutral', 'none'],
                'spf_record': spf_record,
                'domain': domain,
                'sender_ip': sender_ip,
                'details': self._get_result_details(result, explanation)
            }

        except Exception as e:
            logger.error(f"Sync SPF check error: {e}")
            return self._create_error_result(str(e))

    def _get_spf_record(self, domain: str) -> Optional[str]:
        """Get SPF TXT record for domain"""
        try:
            # Query TXT records
            answers = self.resolver.resolve(domain, 'TXT')

            for rdata in answers:
                txt_value = str(rdata).strip('"')
                if txt_value.startswith('v=spf1'):
                    return txt_value

            return None

        except dns.resolver.NXDOMAIN:
            logger.debug(f"Domain {domain} does not exist")
            return None
        except dns.resolver.NoAnswer:
            logger.debug(f"No TXT records for {domain}")
            return None
        except Exception as e:
            logger.error(f"Error getting SPF record: {e}")
            return None

    def _get_result_details(self, result: str, explanation: str) -> str:
        """Get human-readable details for SPF result"""
        details_map = {
            'pass': f'✅ SPF PASS: {explanation}',
            'fail': f'❌ SPF FAIL: {explanation}',
            'softfail': f'⚠️ SPF SOFTFAIL: {explanation}',
            'neutral': f'ℹ️ SPF NEUTRAL: {explanation}',
            'none': f'ℹ️ SPF NONE: No SPF record found',
            'temperror': f'⚠️ SPF TEMPERROR: Temporary DNS error',
            'permerror': f'❌ SPF PERMERROR: Permanent error in SPF record'
        }

        return details_map.get(result, f'SPF {result.upper()}: {explanation}')

    def _create_error_result(self, error_msg: str) -> Dict:
        """Create error result dict"""
        return {
            'result': 'error',
            'explanation': error_msg,
            'score': 0,
            'valid': False,
            'spf_record': None,
            'domain': None,
            'sender_ip': None,
            'details': f'❌ SPF Error: {error_msg}'
        }

    async def check_spf_alignment(
        self,
        from_domain: str,
        return_path_domain: str
    ) -> Dict:
        """
        Check SPF alignment (RFC 7489 DMARC)

        Args:
            from_domain: Domain from From header
            return_path_domain: Domain from Return-Path header

        Returns:
            Dict with alignment results
        """
        logger.debug(f"Checking SPF alignment: {from_domain} vs {return_path_domain}")

        # Strict alignment: exact match
        strict_aligned = from_domain.lower() == return_path_domain.lower()

        # Relaxed alignment: organizational domain match
        relaxed_aligned = self._check_organizational_domain(
            from_domain,
            return_path_domain
        )

        return {
            'strict_aligned': strict_aligned,
            'relaxed_aligned': relaxed_aligned,
            'from_domain': from_domain,
            'return_path_domain': return_path_domain,
            'aligned': relaxed_aligned,  # Use relaxed by default
            'details': self._get_alignment_details(
                strict_aligned,
                relaxed_aligned,
                from_domain,
                return_path_domain
            )
        }

    def _check_organizational_domain(
        self,
        domain1: str,
        domain2: str
    ) -> bool:
        """Check if domains share organizational domain"""
        # Simple implementation: check if domains end with same base
        # In production: use Public Suffix List

        def get_org_domain(domain: str) -> str:
            parts = domain.lower().split('.')
            if len(parts) >= 2:
                return '.'.join(parts[-2:])
            return domain.lower()

        return get_org_domain(domain1) == get_org_domain(domain2)

    def _get_alignment_details(
        self,
        strict: bool,
        relaxed: bool,
        from_domain: str,
        return_path: str
    ) -> str:
        """Get alignment details message"""
        if strict:
            return f'✅ SPF Aligned (Strict): {from_domain} = {return_path}'
        elif relaxed:
            return f'✅ SPF Aligned (Relaxed): {from_domain} ≈ {return_path}'
        else:
            return f'❌ SPF Not Aligned: {from_domain} ≠ {return_path}'


# Singleton instance
spf_checker = SPFChecker()


# Convenience functions
async def verify_spf(
    sender_email: str,
    sender_ip: str,
    helo_domain: Optional[str] = None
) -> Dict:
    """Verify SPF for sender"""
    return await spf_checker.verify_spf(sender_email, sender_ip, helo_domain)


async def check_spf_alignment(
    from_domain: str,
    return_path_domain: str
) -> Dict:
    """Check SPF alignment"""
    return await spf_checker.check_spf_alignment(from_domain, return_path_domain)
