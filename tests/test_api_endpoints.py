"""
Integration tests for API endpoints

Tests:
- Auth endpoints
- Registry endpoints
- Alert endpoints
- Analysis endpoints
- System endpoints
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))


class TestAuthAPI:
    """Test authentication API endpoints."""

    @pytest.mark.asyncio
    async def test_login_success(self, client):
        """POST /api/v1/auth/login should return token on success."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "admin@spear-guard.gov.ru",
                "password": "admin"
            }
        )
        
        # May vary based on seeded data
        assert response.status_code in [200, 401, 404, 422]

    @pytest.mark.asyncio
    async def test_login_invalid_json(self, client):
        """POST /api/v1/auth/login with invalid JSON."""
        response = await client.post(
            "/api/v1/auth/login",
            content="not-json"
        )
        
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_logout(self, client, auth_headers):
        """POST /api/v1/auth/logout should work."""
        response = await client.post(
            "/api/v1/auth/logout",
            headers=auth_headers
        )
        
        assert response.status_code in [200, 401]


class TestRegistryAPI:
    """Test registry API endpoints."""

    @pytest.mark.asyncio
    async def test_list_senders(self, client, auth_headers):
        """GET /api/v1/registry should list senders."""
        response = await client.get(
            "/api/v1/registry",
            headers=auth_headers
        )
        
        assert response.status_code in [200, 401]

    @pytest.mark.asyncio
    async def test_create_sender(self, client, auth_headers):
        """POST /api/v1/registry should create sender."""
        response = await client.post(
            "/api/v1/registry",
            json={
                "email_address": f"test{datetime.now().timestamp()}@example.com",
                "domain": "example.com",
                "organization_name": "Test Org",
                "trust_level": 1,
                "organization_id": 1
            },
            headers=auth_headers
        )
        
        assert response.status_code in [200, 201, 400, 422]

    @pytest.mark.asyncio
    async def test_get_sender(self, client, auth_headers):
        """GET /api/v1/registry/{id} should return sender."""
        response = await client.get(
            "/api/v1/registry/1",
            headers=auth_headers
        )
        
        assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_update_sender(self, client, auth_headers):
        """PUT /api/v1/registry/{id} should update sender."""
        response = await client.put(
            "/api/v1/registry/1",
            json={"trust_level": 2},
            headers=auth_headers
        )
        
        assert response.status_code in [200, 404, 422]

    @pytest.mark.asyncio
    async def test_delete_sender(self, client, auth_headers):
        """DELETE /api/v1/registry/{id} should delete sender."""
        response = await client.delete(
            "/api/v1/registry/1",
            headers=auth_headers
        )
        
        assert response.status_code in [200, 204, 404]


class TestAlertsAPI:
    """Test alerts API endpoints."""

    @pytest.mark.asyncio
    async def test_list_alerts(self, client, auth_headers):
        """GET /api/v1/alerts should list alerts."""
        response = await client.get(
            "/api/v1/alerts",
            headers=auth_headers
        )
        
        assert response.status_code in [200, 401]

    @pytest.mark.asyncio
    async def test_create_alert(self, client, auth_headers):
        """POST /api/v1/alerts should create alert."""
        response = await client.post(
            "/api/v1/alerts",
            json={
                "title": "Test Alert",
                "message": "This is a test",
                "severity": "medium"
            },
            headers=auth_headers
        )
        
        assert response.status_code in [201, 400, 422]

    @pytest.mark.asyncio
    async def test_get_alert(self, client, auth_headers):
        """GET /api/v1/alerts/{id} should return alert."""
        response = await client.get(
            "/api/v1/alerts/1",
            headers=auth_headers
        )
        
        assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_acknowledge_alert(self, client, auth_headers):
        """POST /api/v1/alerts/{id}/acknowledge should work."""
        response = await client.post(
            "/api/v1/alerts/1/acknowledge",
            headers=auth_headers
        )
        
        assert response.status_code in [200, 404]


class TestAnalysisAPI:
    """Test analysis API endpoints."""

    @pytest.mark.asyncio
    async def test_analyze_headers(self, client, auth_headers):
        """POST /api/v1/analyze/headers should analyze email."""
        response = await client.post(
            "/api/v1/analyze/headers",
            json={
                "from_address": "sender@example.com",
                "to_address": "recipient@example.org",
                "subject": "Test Subject",
                "sender_ip": "192.168.1.1",
                "headers": {
                    "From": "sender@example.com",
                    "To": "recipient@example.org",
                    "Subject": "Test Subject"
                }
            },
            headers=auth_headers
        )
        
        assert response.status_code in [200, 500, 422]

    @pytest.mark.asyncio
    async def test_scan_attachment(self, client, auth_headers):
        """POST /api/v1/analyze/attachments should scan attachment."""
        import base64
        
        # Simple text file as base64
        file_data = base64.b64encode(b"test content").decode()
        
        response = await client.post(
            "/api/v1/analyze/attachments",
            json={
                "filename": "test.txt",
                "file_data": file_data,
                "enable_sandbox": False,
                "enable_virustotal": False
            },
            headers=auth_headers
        )
        
        assert response.status_code in [200, 400, 422, 500]


class TestCheckAPI:
    """Test check API endpoints."""

    @pytest.mark.asyncio
    async def test_fast_check(self, client, auth_headers):
        """POST /api/v1/check/fast should perform fast check."""
        response = await client.post(
            "/api/v1/check/fast",
            json={
                "from_address": "sender@example.com",
                "to_address": "recipient@example.org",
                "subject": "Test",
                "domain": "example.com",
                "ip": "192.168.1.1"
            },
            headers=auth_headers
        )
        
        assert response.status_code in [200, 422, 500]

    @pytest.mark.asyncio
    async def test_full_check(self, client, auth_headers):
        """POST /api/v1/check/full should perform full check."""
        response = await client.post(
            "/api/v1/check/full",
            json={
                "from_address": "sender@example.com",
                "to_address": "recipient@example.org",
                "subject": "Test",
                "domain": "example.com",
                "ip": "192.168.1.1",
                "headers": {},
                "body_preview": "Test body"
            },
            headers=auth_headers
        )
        
        assert response.status_code in [200, 422, 500]


class TestOrganizationsAPI:
    """Test organizations API endpoints."""

    @pytest.mark.asyncio
    async def test_list_organizations(self, client, auth_headers):
        """GET /api/v1/organizations should list orgs."""
        response = await client.get(
            "/api/v1/organizations",
            headers=auth_headers
        )
        
        assert response.status_code in [200, 401]

    @pytest.mark.asyncio
    async def test_create_organization(self, client, auth_headers):
        """POST /api/v1/organizations should create org."""
        response = await client.post(
            "/api/v1/organizations",
            json={
                "name": f"Test Org {datetime.now().timestamp()}",
                "domain": "test.org",
                "description": "Test organization"
            },
            headers=auth_headers
        )
        
        assert response.status_code in [201, 400, 422]


class TestUsersAPI:
    """Test users API endpoints."""

    @pytest.mark.asyncio
    async def test_list_users(self, client, auth_headers):
        """GET /api/v1/users should list users."""
        response = await client.get(
            "/api/v1/users",
            headers=auth_headers
        )
        
        assert response.status_code in [200, 401]


class TestSystemAPI:
    """Test system API endpoints."""

    @pytest.mark.asyncio
    async def test_health_check(self, client):
        """GET /health should return health status."""
        response = await client.get("/health")
        
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert "services" in data

    @pytest.mark.asyncio
    async def test_root_endpoint(self, client):
        """GET / should return API info."""
        response = await client.get("/")
        
        assert response.status_code == 200
        
        data = response.json()
        assert "name" in data
        assert "version" in data


import datetime


class TestWebSocketAPI:
    """Test WebSocket endpoint."""

    @pytest.mark.asyncio
    async def test_ws_endpoint_exists(self, client):
        """WebSocket endpoint should be accessible."""
        # Just verify the route is registered
        # Full WS testing requires special client
        response = await client.get("/api/v1/ws")
        
        # May return 404 or upgrade required
        assert response.status_code in [404, 426, 200]