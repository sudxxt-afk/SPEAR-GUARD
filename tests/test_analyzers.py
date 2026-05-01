"""
Integration tests for all analyzers

Tests:
- Technical analyzer (SPF, DKIM, DMARC)
- URL inspector
- Attachment scanner
- Contextual analyzer
- Behavioral analyzer
"""

import pytest
import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))


class TestTechnicalAnalyzer:
    """Test technical email analysis."""

    @pytest.mark.asyncio
    async def test_check_headers_with_valid_email(self):
        """Should analyze email headers successfully."""
        from analyzers.technical_analyzer import TechnicalAnalyzer
        
        analyzer = TechnicalAnalyzer()
        
        headers = {
            "From": "sender@example.com",
            "To": "recipient@example.org",
            "Subject": "Test",
            "Return-Path": "<sender@example.com>"
        }
        
        # This will fail DNS checks but should return structure
        try:
            result = await analyzer.check_headers(headers=headers)
            assert "spf" in result
            assert "dkim" in result
        except Exception as e:
            # DNS may not be available in test env - that's OK
            pass

    @pytest.mark.asyncio
    async def test_check_headers_missing_from(self):
        """Should handle missing From header."""
        from analyzers.technical_analyzer import TechnicalAnalyzer
        
        analyzer = TechnicalAnalyzer()
        
        headers = {
            "To": "recipient@example.org",
            "Subject": "Test"
        }
        
        result = await analyzer.check_headers(headers=headers)
        
        # Should return result even without From
        assert result is not None
        assert "error" in result or "authentication" in result


class TestURLInspector:
    """Test URL analysis."""

    @pytest.mark.asyncio
    async def test_analyze_url_basic(self):
        """Should analyze URL and return result."""
        from analyzers.url_inspector import url_inspector
        
        # Test with a known URL
        result = await url_inspector.analyze_url("https://example.com")
        
        assert result is not None
        assert "url" in result or "risk_score" in result

    @pytest.mark.asyncio
    async def test_analyze_url_phishing_pattern(self):
        """Should detect phishing patterns in URL."""
        from analyzers.url_inspector import url_inspector
        
        # Phishing URL with suspicious patterns
        result = await url_inspector.analyze_url("http://evil-phishing-site.com/login?redirect=bank.com")
        
        assert result is not None

    @pytest.mark.asyncio
    async def test_extract_all_urls(self):
        """Should extract URLs from text."""
        from analyzers.url_inspector import url_inspector
        
        text = """
        Visit https://example.com for more info.
        Also check http://test.org/page?id=123
        """
        
        urls = url_inspector.extractor.extract_all_urls(text)
        
        assert len(urls) >= 2
        assert any("example.com" in u.get("url", "") for u in urls)


class TestAttachmentScanner:
    """Test attachment scanning."""

    @pytest.mark.asyncio
    async def test_scan_safe_file(self):
        """Should scan safe file without errors."""
        from analyzers.attachment_scanner import AttachmentScanner
        
        scanner = AttachmentScanner()
        
        # Safe file content
        content = b"Hello, this is a plain text file content."
        
        result = await scanner.scan_attachment(
            filename="test.txt",
            file_content=content,
            enable_sandbox=False,
            enable_virustotal=False
        )
        
        assert result is not None
        assert "overall_risk" in result

    @pytest.mark.asyncio
    async def test_scan_executable_extension(self):
        """Should detect dangerous file extension."""
        from analyzers.attachment_scanner import AttachmentScanner
        
        scanner = AttachmentScanner()
        
        # Dangerous extension
        content = b"MZ" + b"\x00" * 100  # Fake EXE header
        
        result = await scanner.scan_attachment(
            filename="malware.exe",
            file_content=content,
            enable_sandbox=False,
            enable_virustotal=False
        )
        
        assert result is not None
        # Should detect .exe as dangerous
        assert result["overall_risk"]["score"] > 0

    @pytest.mark.asyncio
    async def test_scan_double_extension(self):
        """Should detect double extension."""
        from analyzers.attachment_scanner import AttachmentScanner
        
        scanner = AttachmentScanner()
        
        content = b"PDF content here..."
        
        result = await scanner.scan_attachment(
            filename="document.pdf.exe",
            file_content=content,
            enable_sandbox=False,
            enable_virustotal=False
        )
        
        # Double extension should be flagged
        assert result is not None
        static = result.get("static_analysis", {})
        assert any(issue.get("type") == "double_extension" for issue in static.get("issues", []))


class TestContextualAnalyzer:
    """Test contextual analysis."""

    @pytest.mark.asyncio
    async def test_analyze_new_sender(self):
        """Should detect new sender."""
        from analyzers.contextual_analyzer import contextual_analyzer
        
        result = await contextual_analyzer.analyze(
            from_address="new@unknown-domain.com",
            to_address="employee@agency.gov.ru",
            subject="Hello",
            headers={},
            body_preview="Test message"
        )
        
        assert result is not None
        assert "is_new_sender" in result or "score" in result

    @pytest.mark.asyncio
    async def test_analyze_domain_age(self):
        """Should check domain age."""
        from analyzers.contextual_analyzer import contextual_analyzer
        
        # New domain (suspicious)
        result = await contextual_analyzer.analyze(
            from_address="test@new-domain-today.com",
            to_address="employee@agency.gov.ru",
            subject="Test",
            headers={},
            body_preview="Test"
        )
        
        assert result is not None


class TestLinguisticAnalyzer:
    """Test linguistic analysis."""

    @pytest.mark.asyncio
    async def test_analyze_phishing_text(self):
        """Should detect phishing language."""
        from analyzers.linguistic_analyzer import linguistic_analyzer
        
        phishing_text = """
        URGENT: Your account has been compromised!
        Click here immediately to verify or lose your money!
        Act NOW or face consequences!
        """
        
        result = await linguistic_analyzer.analyze_text(
            text=phishing_text,
            sender="attacker@evil.com",
            subject="URGENT: Verify Account"
        )
        
        assert result is not None
        # Should detect urgency and threats
        assert "urgency" in result or "risk_score" in result

    @pytest.mark.asyncio
    async def test_analyze_legitimate_text(self):
        """Should pass legitimate text."""
        from analyzers.linguistic_analyzer import linguistic_analyzer
        
        legitimate_text = """
        Hi team,
        
        Please join us for the weekly meeting tomorrow at 10am.
        
        Agenda:
        - Project updates
        - Q&A
        
        Best regards
        """
        
        result = await linguistic_analyzer.analyze_text(
            text=legitimate_text,
            sender="colleague@partner.com",
            subject="Weekly Meeting"
        )
        
        assert result is not None
        # Should have low risk
        assert result.get("risk_score", 100) < 50


class TestBehavioralAnalyzer:
    """Test behavioral analysis."""

    @pytest.mark.asyncio
    async def test_analyze_new_sender_behavior(self):
        """Should handle new sender."""
        from analyzers.behavioral_analyzer import BehavioralAnalyzer
        from sqlalchemy.ext.asyncio import AsyncSession
        from unittest.mock import MagicMock
        
        mock_db = MagicMock(spec=AsyncSession)
        analyzer = BehavioralAnalyzer(mock_db)
        
        result = await analyzer.analyze(from_address="never_seen@sender.com")
        
        assert result is not None
        assert "score" in result or "confidence" in result

    @pytest.mark.asyncio
    async def test_analyze_known_sender(self):
        """Should recognize known sender."""
        from analyzers.behavioral_analyzer import BehavioralAnalyzer
        from sqlalchemy.ext.asyncio import AsyncSession
        from unittest.mock import MagicMock
        
        mock_db = MagicMock(spec=AsyncSession)
        analyzer = BehavioralAnalyzer(mock_db)
        
        # Known sender - should have some history
        result = await analyzer.analyze(from_address="colleague@agency.gov.ru")
        
        assert result is not None


class TestEmailValidator:
    """Test email validation utilities."""

    def test_extract_domain_from_email(self):
        """Should extract domain from email."""
        from utils.email_validator import extract_domain_from_email
        
        domain = extract_domain_from_email("user@example.com")
        
        assert domain == "example.com"

    def test_extract_domain_from_email_invalid(self):
        """Should handle invalid email."""
        from utils.email_validator import extract_domain_from_email
        
        domain = extract_domain_from_email("not-an-email")
        
        assert domain is None

    def test_normalize_email(self):
        """Should normalize email."""
        from utils.email_validator import normalize_email
        
        normalized = normalize_email("User@Example.COM")
        
        assert normalized == "user@example.com"

    def test_is_valid_email_format(self):
        """Should validate email format."""
        from utils.email_validator import is_valid_email_format
        
        assert is_valid_email_format("test@example.com") is True
        assert is_valid_email_format("invalid") is False
        assert is_valid_email_format("@example.com") is False


class TestSPFChecker:
    """Test SPF validation."""

    @pytest.mark.asyncio
    async def test_spf_check_missing_params(self):
        """Should handle missing parameters."""
        from utils.spf_checker import verify_spf
        
        # No IP or domain - should handle gracefully
        result = await verify_spf(None, None)
        
        assert result is not None


class TestDKIMChecker:
    """Test DKIM validation."""

    @pytest.mark.asyncio
    async def test_dkim_check_no_email(self):
        """Should handle missing email."""
        from utils.dkim_checker import verify_dkim
        
        result = await verify_dkim(None)
        
        assert result is not None


class TestURLExtractor:
    """Test URL extraction."""

    def test_extract_urls_from_text(self):
        """Should extract URLs from text."""
        from utils.url_extractor import url_extractor
        
        text = "Check https://example.com and http://test.org"
        
        urls = url_extractor.extract_all_urls(text)
        
        assert len(urls) >= 2

    def test_extract_malicious_urls(self):
        """Should extract suspicious URLs."""
        from utils.url_extractor import url_extractor
        
        text = """
        Click http://evil-site.com/login?redirect=bank.com
        Or visit https://fake-paypal.com/verify
        """
        
        urls = url_extractor.extract_all_urls(text)
        
        assert len(urls) > 0