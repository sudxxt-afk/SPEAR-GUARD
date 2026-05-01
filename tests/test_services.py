"""
Integration tests for services and integrations

Tests:
- Analysis Service
- Registry Service
- Threat Intel Service
- Cuckoo Sandbox integration
- VirusTotal integration
- SMTP integration
- Active Directory integration
"""

import pytest
import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))


class TestAnalysisService:
    """Test AnalysisService."""

    @pytest.mark.asyncio
    async def test_perform_full_analysis(self, test_db, test_user):
        """Should perform full email analysis."""
        from services.analysis_service import AnalysisService
        
        service = AnalysisService(test_db)
        
        result = await service.perform_full_analysis(
            from_address="sender@example.com",
            to_address="recipient@example.org",
            subject="Test Subject",
            headers={
                "From": "sender@example.com",
                "To": "recipient@example.org",
                "Subject": "Test Subject"
            },
            body="This is a test email body with some content.",
            sender_ip="192.168.1.1"
        )
        
        assert result is not None
        assert "risk_score" in result

    @pytest.mark.asyncio
    async def test_analyze_email_headers(self, test_db, test_user):
        """Should analyze email and persist result."""
        from services.analysis_service import AnalysisService
        
        service = AnalysisService(test_db)
        
        result = await service.analyze_email_headers(
            from_address="test@example.com",
            to_address="user@agency.gov.ru",
            subject="Test",
            headers={"From": "test@example.com", "To": "user@agency.gov.ru"},
            user_id=test_user.id
        )
        
        assert result is not None


class TestRegistryService:
    """Test RegistryService methods."""

    @pytest.mark.asyncio
    async def test_add_sender(self, test_db, test_user, test_organization):
        """Should add sender to registry."""
        from services.registry_service import RegistryService
        
        service = RegistryService(test_db)
        
        result = await service.add_sender(
            email=f"new{datetime.now().timestamp()}@example.com",
            domain="example.com",
            organization_name="Test",
            trust_level=1,
            added_by=test_user.id,
            organization_id=test_organization.id
        )
        
        assert result is not None

    @pytest.mark.asyncio
    async def test_find_by_email(self, test_db, test_trusted_sender):
        """Should find sender by email."""
        from services.registry_service import RegistryService
        
        service = RegistryService(test_db)
        
        result = await service.find_by_email(test_trusted_sender.email_address)
        
        assert result is not None
        assert result.email_address == test_trusted_sender.email_address

    @pytest.mark.asyncio
    async def test_list_senders(self, test_db, test_organization):
        """Should list all senders for org."""
        from services.registry_service import RegistryService
        
        service = RegistryService(test_db)
        
        results = await service.list_senders(organization_id=test_organization.id)
        
        assert results is not None
        assert isinstance(results, list)


class TestThreatIntelService:
    """Test Threat Intel Service."""

    @pytest.mark.asyncio
    async def test_check_ip_reputation(self):
        """Should check IP reputation."""
        from services.threat_intel_service import ThreatIntelService
        
        service = ThreatIntelService()
        
        # Mock the API calls
        with patch.object(service.otx_client, 'check_ip', new_callable=AsyncMock, return_value={"result": "safe"}):
            with patch.object(service.abuse_client, 'check_ip', new_callable=AsyncMock, return_value={"data": {"is_public": True}}):
                result = await service.check_ip_reputation("8.8.8.8")
                
                assert result is not None

    @pytest.mark.asyncio
    async def test_check_domain_reputation(self):
        """Should check domain reputation."""
        from services.threat_intel_service import ThreatIntelService
        
        service = ThreatIntelService()
        
        result = await service.check_domain_reputation("example.com")
        
        assert result is not None

    @pytest.mark.asyncio
    async def test_get_cache_stats(self):
        """Should return cache statistics."""
        from services.threat_intel_service import ThreatIntelService
        
        service = ThreatIntelService()
        
        stats = await service.get_cache_stats()
        
        assert stats is not None


class TestCuckooSandboxIntegration:
    """Test Cuckoo Sandbox integration."""

    @pytest.mark.asyncio
    async def test_analyze_file(self):
        """Should analyze file in sandbox."""
        from integrations.cuckoo_sandbox import cuckoo_client
        
        result = await cuckoo_client.analyze_file(
            file_content=b"test content",
            filename="test.txt"
        )
        
        assert result is not None
        assert "status" in result

    @pytest.mark.asyncio
    async def test_analyze_url(self):
        """Should analyze URL in sandbox."""
        from integrations.cuckoo_sandbox import cuckoo_client
        
        result = await cuckoo_client.analyze_url("https://example.com")
        
        assert result is not None


class TestVirusTotalIntegration:
    """Test VirusTotal integration."""

    @pytest.mark.asyncio
    async def test_check_file_hash(self):
        """Should check file hash."""
        from integrations.virustotal import virustotal_client
        
        # Known file hash
        result = await virustotal_client.check_file_hash(
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        )
        
        assert result is not None

    @pytest.mark.asyncio
    async def test_check_url(self):
        """Should check URL."""
        from integrations.virustotal import virustotal_client
        
        result = await virustotal_client.check_url("https://example.com")
        
        assert result is not None


class TestSMTPIntegration:
    """Test SMTP integration."""

    @pytest.mark.asyncio
    async def test_send_email_mock(self):
        """Should send email (mocked)."""
        from integrations.smtp_listener import send_alert_email
        
        # Mock SMTP
        with patch('aiosmtplib.SMTP') as mock_smtp:
            mock_instance = AsyncMock()
            mock_smtp.return_value.__aenter__.return_value = mock_instance
            
            result = await send_alert_email(
                to="test@example.com",
                subject="Test",
                body="Test body"
            )
            
            # Should not crash
            assert result is not None


class TestActiveDirectoryIntegration:
    """Test Active Directory integration."""

    @pytest.mark.asyncio
    async def test_sync_users(self):
        """Should sync users from AD."""
        from integrations.active_directory import sync_users_from_ad
        
        # Mock AD
        with patch('ldap3.Connection') as mock_conn:
            mock_connection = MagicMock()
            mock_conn.return_value = mock_connection
            
            result = await sync_users_from_ad()
            
            # Should not crash even without real AD
            assert result is not None


class TestIMAPListener:
    """Test IMAP listener."""

    @pytest.mark.asyncio
    async def test_connect_mock(self):
        """Should handle connection (mocked)."""
        from integrations.imap_listener import IMAPListener
        
        listener = IMAPListener(
            imap_server="imap.example.com",
            username="user@example.com",
            password="password"
        )
        
        # Just verify initialization
        assert listener is not None


import datetime


class TestDatabaseModels:
    """Test database models."""

    @pytest.mark.asyncio
    async def test_create_organization(self, test_db):
        """Should create organization."""
        from database import Organization
        
        org = Organization(
            name="Test Org",
            domain="test.org"
        )
        test_db.add(org)
        await test_db.flush()
        
        assert org.id is not None

    @pytest.mark.asyncio
    async def test_create_user(self, test_db, test_organization):
        """Should create user."""
        from database import User
        
        user = User(
            email=f"user{datetime.now().timestamp()}@test.org",
            full_name="Test User",
            hashed_password="hash",
            organization_id=test_organization.id
        )
        test_db.add(user)
        await test_db.flush()
        
        assert user.id is not None

    @pytest.mark.asyncio
    async def test_email_analysis_relationship(self, test_db, test_user):
        """Should create email analysis with relationships."""
        from database import EmailAnalysis
        
        analysis = EmailAnalysis(
            user_id=test_user.id,
            from_address="sender@example.com",
            to_address=test_user.email,
            subject="Test",
            risk_score=50.0,
            status="warning"
        )
        test_db.add(analysis)
        await test_db.flush()
        
        assert analysis.id is not None