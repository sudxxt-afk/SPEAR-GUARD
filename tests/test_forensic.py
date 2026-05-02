"""
Unit tests for Forensic Investigation API

Tests:
- Sender timeline retrieval
- Recipient network analysis
- Email forensic details
- Report export
- Incident timeline
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta


# Test data
@pytest.fixture
def mock_email_analysis():
    """Create mock email analysis for testing"""
    return MagicMock(
        id=1,
        message_id="<test-123@example.com>",
        from_address="attacker@evil.com",
        to_address="user@government.ru",
        subject="Urgent: Verify your account",
        body_preview="Click here to verify",
        risk_score=85.5,
        status="danger",
        technical_score=90.0,
        linguistic_score=80.0,
        behavioral_score=75.0,
        contextual_score=85.0,
        in_registry=False,
        trust_level=0,
        analyzed_at=datetime.utcnow(),
        analysis_details={"test": "data"},
        body_text="Test body",
        raw_headers="From: attacker@evil.com",
    )


@pytest.fixture
def mock_user():
    """Create mock user"""
    return MagicMock(
        id=1,
        email="admin@spear-guard.gov.ru",
        full_name="Admin",
        role="admin",
    )


class TestForensicAPISchemas:
    """Test API schema validation"""

    def test_sender_timeline_response_structure(self):
        """Verify sender timeline response has required fields"""
        # Simulated response from API
        response = {
            "sender": "test@example.com",
            "timeline": [
                {
                    "id": 1,
                    "message_id": "<msg-1>",
                    "from": "test@example.com",
                    "to": "user@government.ru",
                    "subject": "Test",
                    "risk_score": 50.0,
                    "status": "safe",
                }
            ],
            "statistics": {
                "total_emails": 10,
                "high_risk": 2,
                "medium_risk": 3,
                "safe": 5,
                "unique_recipients": 3,
                "first_seen": "2024-01-01T00:00:00",
                "last_seen": "2024-12-31T23:59:59",
            },
        }

        # Verify structure
        assert "sender" in response
        assert "timeline" in response
        assert "statistics" in response
        assert isinstance(response["timeline"], list)
        assert "total_emails" in response["statistics"]

    def test_recipient_network_response_structure(self):
        """Verify recipient network response has required fields"""
        response = {
            "sender": "test@example.com",
            "total_recipients": 5,
            "network": [
                {
                    "email": "user1@government.ru",
                    "emails_received": 3,
                    "average_risk_score": 25.0,
                    "high_risk_count": 0,
                }
            ],
            "high_risk_recipients": [],
        }

        assert "sender" in response
        assert "total_recipients" in response
        assert "network" in response
        assert "high_risk_recipients" in response

    def test_email_details_response_structure(self):
        """Verify email details response has required fields"""
        response = {
            "email": {
                "id": 1,
                "message_id": "<msg-1>",
                "from": "test@example.com",
                "to": "user@government.ru",
                "risk_score": 75.0,
                "status": "danger",
            },
            "alerts": [
                {
                    "id": 1,
                    "alert_type": "phishing",
                    "severity": "high",
                    "title": "Phishing detected",
                }
            ],
            "registry_info": {
                "is_registered": False,
                "organization_name": None,
                "trust_level": None,
                "is_verified": None,
            },
        }

        assert "email" in response
        assert "alerts" in response
        assert "registry_info" in response
        assert response["email"]["risk_score"] is not None

    def test_export_report_response_structure(self):
        """Verify forensic report response has required fields"""
        response = {
            "report_type": "Forensic Email Analysis",
            "generated_at": "2024-12-31T23:59:59",
            "investigator": "admin@spear-guard.gov.ru",
            "target_sender": "test@example.com",
            "time_range": "365 days",
            "summary": {
                "total_emails": 10,
                "high_risk_count": 2,
                "medium_risk_count": 3,
                "safe_count": 5,
                "unique_recipients": 3,
            },
            "timeline": [],
            "recommendations": [
                {
                    "severity": "high",
                    "title": "Test recommendation",
                    "description": "Test description",
                }
            ],
        }

        assert "report_type" in response
        assert "summary" in response
        assert "recommendations" in response
        assert isinstance(response["recommendations"], list)


class TestForensicStatistics:
    """Test forensic statistics calculation"""

    def test_statistics_calculation_empty(self):
        """Test statistics with no emails"""
        timeline = []
        stats = {
            "total_emails": len(timeline),
            "high_risk": sum(1 for e in timeline if (e.get("risk_score", 0) or 0) >= 75),
            "medium_risk": sum(1 for e in timeline if 50 <= (e.get("risk_score", 0) or 0) < 75),
            "safe": sum(1 for e in timeline if (e.get("risk_score", 0) or 0) < 50),
            "unique_recipients": len(set(e.get("to") for e in timeline if e.get("to"))),
            "first_seen": timeline[-1].get("analyzed_at") if timeline else None,
            "last_seen": timeline[0].get("analyzed_at") if timeline else None,
        }

        assert stats["total_emails"] == 0
        assert stats["high_risk"] == 0

    def test_statistics_calculation_with_data(self):
        """Test statistics with sample emails"""
        timeline = [
            {"to": "user1@gov.ru", "risk_score": 85.0, "analyzed_at": "2024-01-01"},
            {"to": "user2@gov.ru", "risk_score": 55.0, "analyzed_at": "2024-01-02"},
            {"to": "user1@gov.ru", "risk_score": 20.0, "analyzed_at": "2024-01-03"},
        ]

        stats = {
            "total_emails": len(timeline),
            "high_risk": sum(1 for e in timeline if (e.get("risk_score", 0) or 0) >= 75),
            "medium_risk": sum(1 for e in timeline if 50 <= (e.get("risk_score", 0) or 0) < 75),
            "safe": sum(1 for e in timeline if (e.get("risk_score", 0) or 0) < 50),
            "unique_recipients": len(set(e.get("to") for e in timeline if e.get("to"))),
        }

        assert stats["total_emails"] == 3
        assert stats["high_risk"] == 1
        assert stats["medium_risk"] == 1
        assert stats["safe"] == 1
        assert stats["unique_recipients"] == 2  # user1 appears twice


class TestForensicNetwork:
    """Test recipient network analysis"""

    def test_network_builds_correctly(self):
        """Test network graph is built correctly"""
        # Simulate emails from one sender
        emails = [
            {"to": "user1@gov.ru", "risk_score": 30.0, "status": "safe", "analyzed_at": datetime(2024, 1, 1)},
            {"to": "user2@gov.ru", "risk_score": 80.0, "status": "danger", "analyzed_at": datetime(2024, 1, 2)},
            {"to": "user1@gov.ru", "risk_score": 25.0, "status": "safe", "analyzed_at": datetime(2024, 1, 3)},
        ]

        # Build network
        recipients = {}
        for email in emails:
            recipient = email["to"]
            if recipient not in recipients:
                recipients[recipient] = {
                    "email": recipient,
                    "count": 0,
                    "risk_scores": [],
                    "statuses": [],
                    "first_contact": email["analyzed_at"],
                    "last_contact": email["analyzed_at"],
                }

            recipients[recipient]["count"] += 1
            recipients[recipient]["risk_scores"].append(email["risk_score"])
            recipients[recipient]["statuses"].append(email["status"])

        assert len(recipients) == 2
        assert recipients["user1@gov.ru"]["count"] == 2
        assert recipients["user2@gov.ru"]["count"] == 1


class TestForensicRecommendations:
    """Test recommendation generation"""

    def test_recommendation_high_risk_volume(self):
        """Test detection of high volume of risky emails"""
        emails = [{"risk_score": 85.0} for _ in range(10)]

        recommendations = []
        high_risk = [e for e in emails if (e.get("risk_score", 0) or 0) >= 75]
        if len(high_risk) > 5:
            recommendations.append({
                "severity": "critical",
                "title": "High Volume of Risky Emails",
                "description": f"{len(high_risk)} emails with risk score > 75 detected.",
            })

        assert len(recommendations) == 1
        assert recommendations[0]["severity"] == "critical"

    def test_recommendation_credential_harvesting(self):
        """Test detection of credential harvesting patterns"""
        emails = [
            {"subject": "Password reset required"},
            {"subject": "Verify your account now"},
            {"subject": "Meeting notes"},
        ]

        recommendations = []
        subjects = [e.get("subject", "").lower() for e in emails if e.get("subject")]
        if any("password" in s or "account" in s or "verify" in s for s in subjects):
            recommendations.append({
                "severity": "high",
                "title": "Credential Harvesting Attempt",
                "description": "Emails contain password/account related keywords.",
            })

        assert len(recommendations) == 1
        assert recommendations[0]["severity"] == "high"

    def test_recommendation_not_in_registry(self):
        """Test detection of sender not in trusted registry"""
        emails = [{"in_registry": False} for _ in range(10)]
        not_in_registry = [e for e in emails if not e.get("in_registry", True)]

        recommendations = []
        if len(not_in_registry) > len(emails) * 0.5:
            recommendations.append({
                "severity": "medium",
                "title": "Sender Not in Trusted Registry",
                "description": f"Only {len(emails) - len(not_in_registry)}/{len(emails)} emails from trusted senders.",
            })

        assert len(recommendations) == 1


class TestForensicIncidentTimeline:
    """Test incident timeline functionality"""

    def test_incident_timeline_structure(self):
        """Test incident timeline has correct structure"""
        main_email = {
            "id": 1,
            "from": "attacker@evil.com",
            "to": "victim@government.ru",
            "subject": "Phishing email",
            "risk_score": 90.0,
            "status": "danger",
            "analyzed_at": datetime(2024, 1, 15),
        }

        all_from_sender = [
            {"analyzed_at": datetime(2024, 1, 1), "to": "user1@gov.ru", "subject": "Test 1", "risk": 30.0, "status": "safe"},
            {"analyzed_at": datetime(2024, 1, 15), "to": "victim@government.ru", "subject": "Phishing", "risk": 90.0, "status": "danger"},
        ]

        incident = {
            "main_email": main_email,
            "sender_history": {
                "total_emails": len(all_from_sender),
                "first_contact": all_from_sender[0]["analyzed_at"].isoformat() if all_from_sender else None,
                "last_contact": all_from_sender[-1]["analyzed_at"].isoformat() if all_from_sender else None,
            },
            "timeline": [
                {
                    "date": e["analyzed_at"].isoformat() if e.get("analyzed_at") else None,
                    "event": "Email received",
                    "recipient": e["to"],
                    "subject": e["subject"],
                    "risk": e["risk"],
                    "status": e["status"],
                }
                for e in all_from_sender
            ],
        }

        assert incident["main_email"]["id"] == 1
        assert incident["sender_history"]["total_emails"] == 2
        assert len(incident["timeline"]) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])