"""
Pytest Configuration and Fixtures for SPEAR-GUARD Tests

Provides reusable fixtures for:
- Database sessions (async SQLAlchemy)
- Test clients (FastAPI)
- Mock services (Redis, etc.)
- Sample data (emails, users, organizations)

Usage:
    async def test_something(db, user, client):
        ...
"""

import pytest
import asyncio
import os
import sys
from typing import AsyncGenerator, Generator
from datetime import datetime, timedelta

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

# SQLAlchemy for testing
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

# FastAPI test client
from httpx import AsyncClient, ASGITransport

# Password hashing
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# =============================================================================
# DATABASE FIXTURES
# =============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def test_engine():
    """
    Create async SQLite engine for testing.
    Uses in-memory database for fast tests.
    """
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    yield engine
    await engine.dispose()


@pytest.fixture(scope="function")
async def test_db(test_engine):
    """
    Create test database tables and provide session.
    Automatically creates all tables from Base.
    """
    # Import all models to register them
    from database import Base
    from database import (
        Organization, User, MailAccount, EmailAnalysis, 
        TrustedRegistry, PhishingReport, ThreatAlert
    )
    
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session factory
    async_session = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    
    async with async_session() as session:
        yield session


@pytest.fixture(scope="function")
async def db_session(test_db):
    """Alias for test_db for clarity."""
    return test_db


# =============================================================================
# MODEL FIXTURES
# =============================================================================

@pytest.fixture
async def test_organization(test_db: AsyncSession) -> Organization:
    """Create a test organization."""
    org = Organization(
        name="Test Government Agency",
        domain="test.gov.ru",
        description="Test organization for unit tests",
        is_active=True,
    )
    test_db.add(org)
    await test_db.flush()
    await test_db.refresh(org)
    return org


@pytest.fixture
async def test_user(test_db: AsyncSession, test_organization: Organization) -> User:
    """Create a test user with hashed password."""
    hashed = pwd_context.hash("testpassword123")
    user = User(
        email="testuser@test.gov.ru",
        full_name="Test User",
        hashed_password=hashed,
        role="employee",
        organization_id=test_organization.id,
        department="IT Department",
        is_active=True,
    )
    test_db.add(user)
    await test_db.flush()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def test_security_officer(test_db: AsyncSession, test_organization: Organization) -> User:
    """Create a test security officer."""
    hashed = pwd_context.hash("officerpass123")
    user = User(
        email="officer@test.gov.ru",
        full_name="Security Officer",
        hashed_password=hashed,
        role="security_officer",
        organization_id=test_organization.id,
        department="Security",
        is_active=True,
    )
    test_db.add(user)
    await test_db.flush()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def test_admin(test_db: AsyncSession) -> User:
    """Create a test admin user."""
    hashed = pwd_context.hash("adminpass123")
    user = User(
        email="admin@spear-guard.gov.ru",
        full_name="System Admin",
        hashed_password=hashed,
        role="admin",
        organization_id=None,  # Admin has no org
        department="IT",
        is_active=True,
    )
    test_db.add(user)
    await test_db.flush()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def test_trusted_sender(
    test_db: AsyncSession, 
    test_organization: Organization,
    test_user: User
) -> TrustedRegistry:
    """Create a trusted sender entry."""
    sender = TrustedRegistry(
        organization_id=test_organization.id,
        email_address="trusted@partner.gov.ru",
        domain="partner.gov.ru",
        organization_name="Partner Government Agency",
        trust_level=1,  # Max trust
        added_by=test_user.id,
        approved_by=test_user.id,
        is_verified=True,
        is_active=True,
        status="active",
        total_emails=150,
        last_email_at=datetime.utcnow() - timedelta(days=1),
    )
    test_db.add(sender)
    await test_db.flush()
    await test_db.refresh(sender)
    return sender


@pytest.fixture
async def test_email_analysis(
    test_db: AsyncSession,
    test_user: User,
    test_organization: Organization
) -> EmailAnalysis:
    """Create a test email analysis record."""
    analysis = EmailAnalysis(
        user_id=test_user.id,
        message_id="<test-message-id@example.com>",
        from_address="sender@external.ru",
        to_address=test_user.email,
        subject="Test Phishing Email",
        body_preview="Click here to claim your prize...",
        risk_score=75.5,
        status="danger",
        in_registry=False,
        trust_level=0,
        technical_score=45.0,
        linguistic_score=80.0,
        behavioral_score=30.0,
        contextual_score=60.0,
        analysis_details={
            "technical": ["SPF fail", "DKIM not found"],
            "linguistic": ["High urgency detected"],
            "contextual": ["New sender"],
        },
        analyzed_at=datetime.utcnow(),
    )
    test_db.add(analysis)
    await test_db.flush()
    await test_db.refresh(analysis)
    return analysis


# =============================================================================
# SAMPLE EMAIL DATA FIXTURES
# =============================================================================

@pytest.fixture
def sample_email_headers() -> dict:
    """Sample email headers for testing."""
    return {
        "From": "sender@external.ru",
        "To": "user@test.gov.ru",
        "Subject": "URGENT: Verify your account",
        "Message-ID": "<test-123@example.com>",
        "Date": "Mon, 1 Jan 2024 12:00:00 +0000",
        "Return-Path": "<sender@external.ru>",
        "Received": "from external.ru by mx.test.gov.ru",
    }


@pytest.fixture
def sample_email_body() -> str:
    """Sample email body for testing."""
    return """
    Dear Customer,
    
    Your account has been compromised. Please click the link below immediately
    to verify your identity or your account will be suspended:
    
    https://fake-bank.com/verify?user=12345
    
    Failure to respond within 24 hours will result in permanent account suspension.
    
    Sincerely,
    Security Team
    """


@pytest.fixture
def sample_phishing_email() -> dict:
    """Complete sample phishing email for testing."""
    return {
        "from_address": "security@fake-bank.com",
        "to_address": "employee@agency.gov.ru",
        "subject": "URGENT: Immediate action required - Account Suspended",
        "headers": {
            "From": "security@fake-bank.com",
            "To": "employee@agency.gov.ru",
            "Subject": "URGENT: Immediate action required - Account Suspended",
            "Message-ID": "<phish-001@example.com>",
            "Return-Path": "<bounce@fake-bank.com>",
        },
        "body": """
        Dear Valued Customer,
        
        We have detected suspicious activity on your account.
        Your account will be PERMANENTLY SUSPENDED within 24 hours unless you verify.
        
        Click here NOW: http://malicious-site.com/login
        
        If you do not act immediately, you will lose all access.
        
        Bank Security Team
        """,
    }


@pytest.fixture
def sample_legitimate_email() -> dict:
    """Complete sample legitimate email for testing."""
    return {
        "from_address": "hr@partner-agency.gov.ru",
        "to_address": "employee@agency.gov.ru",
        "subject": "Meeting scheduled: Q1 Review",
        "headers": {
            "From": "hr@partner-agency.gov.ru",
            "To": "employee@agency.gov.ru",
            "Subject": "Meeting scheduled: Q1 Review",
            "Message-ID": "<legit-001@partner-agency.gov.ru>",
            "Return-Path": "<hr@partner-agency.gov.ru>",
            "Authentication-Results": "mx.agency.gov.ru; spf=pass; dkim=pass",
        },
        "body": """
        Hi Team,
        
        Please join us for the Q1 Review meeting next Tuesday at 10:00 AM.
        
        Agenda:
        - Review Q1 objectives
        - Discuss team achievements
        - Plan Q2 goals
        
        Meeting room: Conference A
        
        Best regards,
        HR Department
        """,
    }


# =============================================================================
# FASTAPI TEST CLIENT FIXTURES
# =============================================================================

@pytest.fixture(scope="function")
async def client(test_db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Create FastAPI test client with overridden database dependency.
    """
    # Import app - defer to avoid circular imports
    from main import app
    
    # Override database dependency
    from database import get_db
    
    async def override_get_db():
        yield test_db
    
    app.dependency_overrides[get_db] = override_get_db
    
    # Create async client
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    
    # Clean up
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers() -> dict:
    """Default auth headers with test token."""
    return {"Authorization": "Bearer test-token"}


@pytest.fixture
async def auth_client(client: AsyncClient, auth_headers: dict) -> AsyncClient:
    """Client with authentication headers."""
    client.headers.update(auth_headers)
    return client


# =============================================================================
# MOCK SERVICES FIXTURES
# =============================================================================

class MockRedis:
    """Mock Redis client for testing."""
    
    def __init__(self):
        self._data = {}
    
    async def get(self, key: str):
        return self._data.get(key)
    
    async def set(self, key: str, value: str, ex: int = None):
        self._data[key] = value
    
    async def delete(self, *keys):
        for key in keys:
            self._data.pop(key, None)
    
    async def ping(self):
        return True
    
    async def close(self):
        pass


@pytest.fixture
def mock_redis():
    """Provide mock Redis client."""
    return MockRedis()


# =============================================================================
# HELPER FIXTURES
# =============================================================================

@pytest.fixture
def sample_file_bytes() -> bytes:
    """Sample executable file bytes for attachment testing."""
    return b"MZ\x90\x00\x03\x00\x00\x00" + b"\x00" * 100


@pytest.fixture
def sample_pdf_bytes() -> bytes:
    """Sample PDF file bytes."""
    return b"%PDF-1.4\n%\xe2\xe3\xcf\xd3" + b"\x00" * 100


@pytest.fixture
def sample_image_bytes() -> bytes:
    """Sample image file bytes (PNG header)."""
    return b"\x89PNG\r\n\x1a\n" + b"\x00" * 50