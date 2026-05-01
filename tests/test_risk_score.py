"""
Unit tests for Risk Score calculation in AnalysisService

Tests the _calculate_risk_score method with various inputs:
- Technical score variations
- Linguistic score variations
- Contextual score variations
- Behavioral score variations
- Kill chain overrides
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))


class TestRiskScoreCalculation:
    """Test cases for risk score calculation."""

    def test_all_scores_safe_returns_low_risk(self):
        """When all scores are safe (100), risk should be low."""
        # Import the service to test
        from services.analysis_service import AnalysisService
        
        # Create a mock database session
        from sqlalchemy.ext.asyncio import AsyncSession
        from unittest.mock import MagicMock
        
        mock_db = MagicMock(spec=AsyncSession)
        service = AnalysisService(mock_db)
        
        # Safe scores (100 = safe)
        tech = {
            "authentication": {"score": 100},
            "spoofing": {"score": 100},
            "header_anomalies": {"score": 100}
        }
        ling = {"risk_score": 0}  # No linguistic risk
        cont = {"score": 100}  # Safe context
        behav = {"score": 100}  # Safe behavior
        
        result = service._calculate_risk_score(tech, ling, cont, behav)
        
        # Expected: tech_risk=0, ling_risk=0, cont_risk=0, behav_risk=0
        # Weighted: 0*0.15 + 0*0.4 + 0*0.25 + 0*0.2 = 0
        assert result < 10, f"Expected low risk, got {result}"

    def test_all_scores_dangerous_returns_high_risk(self):
        """When all scores are dangerous, risk should be high."""
        from services.analysis_service import AnalysisService
        from sqlalchemy.ext.asyncio import AsyncSession
        from unittest.mock import MagicMock
        
        mock_db = MagicMock(spec=AsyncSession)
        service = AnalysisService(mock_db)
        
        # Dangerous scores
        tech = {
            "authentication": {"score": 0},
            "spoofing": {"score": 0},
            "header_anomalies": {"score": 0}
        }
        ling = {"risk_score": 100}  # Maximum linguistic risk
        cont = {"score": 0}  # Dangerous context
        behav = {"score": 0}  # Dangerous behavior
        
        result = service._calculate_risk_score(tech, ling, cont, behav)
        
        # Weighted: 100*0.15 + 100*0.4 + 100*0.25 + 100*0.2 = 100
        assert result >= 70, f"Expected high risk, got {result}"

    def test_linguistic_weight_is_highest(self):
        """Linguistic analysis should have highest weight (40%)."""
        from services.analysis_service import AnalysisService
        from sqlalchemy.ext.asyncio import AsyncSession
        from unittest.mock import MagicMock
        
        mock_db = MagicMock(spec=AsyncSession)
        service = AnalysisService(mock_db)
        
        # Only linguistic is dangerous - use moderate score to avoid kill chain override
        tech = {"authentication": {"score": 100}, "spoofing": {"score": 100}, "header_anomalies": {"score": 100}}
        ling = {"risk_score": 50}  # Moderate - won't trigger kill chain override
        cont = {"score": 100}
        behav = {"score": 100}
        
        result = service._calculate_risk_score(tech, ling, cont, behav)
        
        # Expected: 0*0.15 + 50*0.4 + 0*0.25 + 0*0.2 = 20
        # Note: Without kill chain override, it should be around 20
        assert result >= 15 and result <= 25, f"Expected ~20, got {result}"

    def test_kill_chain_overrides_technical_passes(self):
        """Kill chain attack types should override technical passes."""
        from services.analysis_service import AnalysisService
        from sqlalchemy.ext.asyncio import AsyncSession
        from unittest.mock import MagicMock
        
        mock_db = MagicMock(spec=AsyncSession)
        service = AnalysisService(mock_db)
        
        # All safe technical, but BEC fraud detected
        tech = {"authentication": {"score": 100}, "spoofing": {"score": 100}, "header_anomalies": {"score": 100}}
        ling = {"risk_score": 50, "attack_type": "bec_fraud"}  # BEC fraud overrides
        cont = {"score": 100}
        behav = {"score": 100}
        
        result = service._calculate_risk_score(tech, ling, cont, behav)
        
        # Kill chain override should force CRITICAL
        assert result >= 65, f"Expected critical (>=65), got {result}"

    def test_credential_phishing_overrides(self):
        """Credential phishing attack type should force high risk."""
        from services.analysis_service import AnalysisService
        from sqlalchemy.ext.asyncio import AsyncSession
        from unittest.mock import MagicMock
        
        mock_db = MagicMock(spec=AsyncSession)
        service = AnalysisService(mock_db)
        
        tech = {"authentication": {"score": 90}, "spoofing": {"score": 90}, "header_anomalies": {"score": 90}}
        ling = {"risk_score": 60, "attack_type": "credential_phishing"}
        cont = {"score": 90}
        behav = {"score": 90}
        
        result = service._calculate_risk_score(tech, ling, cont, behav)
        
        assert result >= 65, f"Expected critical, got {result}"

    def test_high_linguistic_risk_ensures_minimum(self):
        """High linguistic risk (>70) should ensure minimum final risk of 65."""
        from services.analysis_service import AnalysisService
        from sqlalchemy.ext.asyncio import AsyncSession
        from unittest.mock import MagicMock
        
        mock_db = MagicMock(spec=AsyncSession)
        service = AnalysisService(mock_db)
        
        # All safe except high linguistic
        tech = {"authentication": {"score": 100}, "spoofing": {"score": 100}, "header_anomalies": {"score": 100}}
        ling = {"risk_score": 75}  # High but not kill chain
        cont = {"score": 100}
        behav = {"score": 100}
        
        result = service._calculate_risk_score(tech, ling, cont, behav)
        
        # Base calculation: 0*0.15 + 75*0.4 + 0*0.25 + 0*0.2 = 30
        # But with bonus: max(30, 65) = 65
        assert result >= 65, f"Expected minimum 65, got {result}"

    def test_missing_authentication_score_uses_default(self):
        """Missing authentication score should default to 0 (worst case)."""
        from services.analysis_service import AnalysisService
        from sqlalchemy.ext.asyncio import AsyncSession
        from unittest.mock import MagicMock
        
        mock_db = MagicMock(spec=AsyncSession)
        service = AnalysisService(mock_db)
        
        # Missing authentication score
        tech = {
            "spoofing": {"score": 100},
            "header_anomalies": {"score": 100}
            # No "authentication" key
        }
        ling = {"risk_score": 0}
        cont = {"score": 100}
        behav = {"score": 100}
        
        result = service._calculate_risk_score(tech, ling, cont, behav)
        
        # auth_score defaults to 0, so tech_risk = 100 - 0 = 100
        # Final: 100*0.15 + 0*0.4 + 0*0.25 + 0*0.2 = 15
        assert result >= 10, f"Expected some risk, got {result}"


class TestRiskScoreCategories:
    """Test risk score categorization."""

    def test_low_risk_safe(self):
        """Risk score < 30 should be safe."""
        from services.analysis_service import AnalysisService
        from sqlalchemy.ext.asyncio import AsyncSession
        from unittest.mock import MagicMock
        
        mock_db = MagicMock(spec=AsyncSession)
        service = AnalysisService(mock_db)
        
        # Very safe scores
        tech = {"authentication": {"score": 100}, "spoofing": {"score": 100}, "header_anomalies": {"score": 100}}
        result = service._calculate_risk_score(tech, {"risk_score": 5}, {"score": 100}, {"score": 100})
        
        assert result < 30

    def test_medium_risk_caution(self):
        """Risk score 30-49 should be caution."""
        from services.analysis_service import AnalysisService
        from sqlalchemy.ext.asyncio import AsyncSession
        from unittest.mock import MagicMock
        
        mock_db = MagicMock(spec=AsyncSession)
        service = AnalysisService(mock_db)
        
        tech = {"authentication": {"score": 70}, "spoofing": {"score": 70}, "header_anomalies": {"score": 70}}
        result = service._calculate_risk_score(tech, {"risk_score": 40}, {"score": 70}, {"score": 70})
        
        assert 30 <= result < 50

    def test_high_risk_warning(self):
        """Risk score 50-69 should be warning."""
        from services.analysis_service import AnalysisService
        from sqlalchemy.ext.asyncio import AsyncSession
        from unittest.mock import MagicMock
        
        mock_db = MagicMock(spec=AsyncSession)
        service = AnalysisService(mock_db)
        
        tech = {"authentication": {"score": 50}, "spoofing": {"score": 50}, "header_anomalies": {"score": 50}}
        result = service._calculate_risk_score(tech, {"risk_score": 60}, {"score": 50}, {"score": 50})
        
        assert 50 <= result < 70

    def test_critical_risk_danger(self):
        """Risk score >= 70 should be danger."""
        from services.analysis_service import AnalysisService
        from sqlalchemy.ext.asyncio import AsyncSession
        from unittest.mock import MagicMock
        
        mock_db = MagicMock(spec=AsyncSession)
        service = AnalysisService(mock_db)
        
        tech = {"authentication": {"score": 20}, "spoofing": {"score": 20}, "header_anomalies": {"score": 20}}
        result = service._calculate_risk_score(tech, {"risk_score": 80}, {"score": 20}, {"score": 20})
        
        assert result >= 70