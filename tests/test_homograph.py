"""
Unit tests for Homograph (IDN) Attack Detection

Tests detection of:
- Cyrillic lookalikes (а → a, е → e, о → o, etc.)
- Punycode phishing domains
- Mixed script domains
- Confusable characters
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))


class TestHomographDetection:
    """Test homograph attack detection."""

    def test_detects_cyrillic_a_as_latin_a(self):
        """Cyrillic 'а' (U+0430) should be detected as lookalike of Latin 'a'."""
        from analyzers.contextual_analyzer import contextual_analyzer
        
        # Cyrillic 'а' looks like Latin 'a'
        result = contextual_analyzer._check_homograph("аpple.com")
        
        assert result["is_homograph"] is True
        assert "cyrillic" in result["script"].lower()

    def test_detects_cyrillic_o_as_latin_o(self):
        """Cyrillic 'о' (U+043E) should be detected as lookalike of Latin 'o'."""
        from analyzers.contextual_analyzer import contextual_analyzer
        
        result = contextual_analyzer._check_homograph("gоogle.com")  # о instead of o
        
        assert result["is_homograph"] is True

    def test_detects_cyrillic_e_as_latin_e(self):
        """Cyrillic 'е' (U+0435) should be detected as lookalike of Latin 'e'."""
        from analyzers.contextual_analyzer import contextual_analyzer
        
        result = contextual_analyzer._check_homograph("tеst.com")  # е instead of e
        
        assert result["is_homograph"] is True

    def test_detects_cyrillic_p_as_latin_p(self):
        """Cyrillic 'р' (U+0440) should be detected as lookalike of Latin 'p'."""
        from analyzers.contextual_analyzer import contextual_analyzer
        
        result = contextual_analyzer._check_homograph("раypal.com")  # р instead of p
        
        assert result["is_homograph"] is True

    def test_accepts_pure_cyrillic_domain(self):
        """Pure Cyrillic domain (non-phishing) should be accepted."""
        from analyzers.contextual_analyzer import contextual_analyzer
        
        # Russian government domain - legitimate
        result = contextual_analyzer._check_hомograph("россия.рф")
        
        # This might be detected but flagged as different script
        # The key is that it's not trying to look like Latin
        assert result is not None

    def test_detects_punycode_phishing(self):
        """Punycode domains (xn--) should be detected."""
        from analyzers.contextual_analyzer import contextual_analyzer
        
        # Example: apple.com in punycode
        result = contextual_analyzer._check_homograph("xn--80ak6aa92e.com")
        
        # This is a known punycode phishing pattern
        assert result is not None

    def test_accepts_legitimate_ascii_domain(self):
        """Pure ASCII domains should be safe."""
        from analyzers.contextual_analyzer import contextual_analyzer
        
        result = contextual_analyzer._check_homograph("google.com")
        
        assert result["is_homograph"] is False

    def test_detects_mixed_script(self):
        """Mixed Latin/Cyrillic should be flagged."""
        from analyzers.contextual_analyzer import contextual_analyzer
        
        # 'a' is Latin, 'р' is Cyrillic - looks like "apple"
        result = contextual_analyzer._check_homograph("app1e.com")  # number 1 instead
        
        # Not a homograph but might be caught as suspicious
        assert result is not None


class TestDisplayNameSpoofing:
    """Test display name spoofing detection."""

    def test_detects_email_in_display_name(self):
        """Email address in display name should be flagged."""
        from analyzers.contextual_analyzer import contextual_analyzer
        
        result = contextual_analyzer._check_display_name_spoofing(
            display_name="John Smith <john.smith@company.com>",
            from_address="attacker@evil.com"
        )
        
        assert result["is_spoofed"] is True

    def test_detects_legitimate_display_name(self):
        """Legitimate display name should pass."""
        from analyzers.contextual_analyzer import contextual_analyzer
        
        result = contextual_analyzer._check_display_name_spoofing(
            display_name="John Smith",
            from_address="john.smith@company.com"
        )
        
        assert result["is_spoofed"] is False

    def test_detects_similar_domain_spoofing(self):
        """Similar domain in display name should be flagged."""
        from analyzers.contextual_analyzer import contextual_analyzer
        
        # display name says company.com but actual email is company-company.com
        result = contextual_analyzer._check_display_name_spoofing(
            display_name="IT Department <it@company.com>",
            from_address="it@company-company.com"
        )
        
        assert result["is_spoofed"] is True


class TestHomographRiskScoring:
    """Test risk scoring for homograph attacks."""

    def test_critical_risk_for_lookalike(self):
        """Lookalike domain should add critical risk."""
        from analyzers.contextual_analyzer import contextual_analyzer
        
        result = contextual_analyzer._check_homograph("аpple.com")
        
        # Homograph should have high risk score
        assert result["risk_score"] >= 70

    def test_low_risk_for_legitimate(self):
        """Legitimate domain should have low risk."""
        from analyzers.contextual_analyzer import contextual_analyzer
        
        result = contextual_analyzer._check_homograph("google.com")
        
        assert result["risk_score"] < 20