from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float, Text, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
import os
from typing import AsyncGenerator

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/spearguard")

# Create async engine
engine = create_async_engine(
    DATABASE_URL,
    echo=True if os.getenv("ENVIRONMENT") == "development" else False,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# Base class for all models
class Base(DeclarativeBase):
    pass


# Dependency for getting database session
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency function that yields database sessions
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# =============================================================================
# ORGANIZATION & USER HIERARCHY
# =============================================================================

class Organization(Base):
    """
    Организация - группирует пользователей для data isolation.
    Security Officers видят данные только своей организации.
    """
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False)
    domain = Column(String(255), index=True)  # e.g., "gov.ru" - для auto-assign при регистрации
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    users = relationship("User", back_populates="organization_rel")


class User(Base):
    """
    Пользователь системы с ролевой моделью:
    - admin: полный доступ ко всем организациям
    - security_officer: доступ к данным своей организации
    - employee: доступ только к своим данным
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    
    # Role-based access control
    role = Column(String(50), default="employee")  # admin, security_officer, employee
    
    # Organization link (for data isolation)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    department = Column(String(255))
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    organization_rel = relationship("Organization", back_populates="users")
    mail_accounts = relationship("MailAccount", back_populates="owner", cascade="all, delete-orphan")


# =============================================================================
# PERSONAL MAIL ACCOUNTS (IMAP Integration)
# =============================================================================

class MailAccount(Base):
    """
    Персональный почтовый аккаунт пользователя.
    Каждый пользователь может подключить несколько ящиков.
    Пароли хранятся в зашифрованном виде (Fernet).
    """
    __tablename__ = "mail_accounts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Display info
    name = Column(String(255))  # e.g., "Рабочая почта"
    email = Column(String(255), nullable=False)
    
    # Provider presets
    provider = Column(String(50), default="custom")  # gmail, outlook, yandex, mailru, custom
    
    # IMAP Connection Details
    imap_server = Column(String(255), nullable=False)
    imap_port = Column(Integer, default=993)
    imap_use_ssl = Column(Boolean, default=True)
    username = Column(String(255), nullable=False)
    encrypted_password = Column(Text, nullable=False)  # Encrypted with Fernet
    
    # Sync settings
    folder = Column(String(255), default="INBOX")
    sync_interval_minutes = Column(Integer, default=5)
    max_emails_per_sync = Column(Integer, default=50)
    
    # State
    is_active = Column(Boolean, default=True)
    status = Column(String(50), default="pending")  # pending, connected, syncing, auth_error, error
    last_sync_at = Column(DateTime)
    last_error = Column(Text)
    total_emails_synced = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    owner = relationship("User", back_populates="mail_accounts")
    email_analyses = relationship("EmailAnalysis", back_populates="mail_account")


# =============================================================================
# EMAIL ANALYSIS (Updated with user/account isolation)
# =============================================================================

class EmailAnalysis(Base):
    """
    Результат анализа письма.
    Теперь привязан к конкретному пользователю и почтовому аккаунту.
    """
    __tablename__ = "email_analyses"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(String(255), index=True)  # Removed unique constraint (same email can be in multiple accounts)
    
    # User & Account isolation
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    mail_account_id = Column(Integer, ForeignKey("mail_accounts.id"), nullable=True, index=True)
    
    # Email metadata
    from_address = Column(String(255), index=True, nullable=False)
    to_address = Column(String(255), index=True, nullable=False)
    subject = Column(Text)
    body_preview = Column(Text)
    
    # Risk assessment
    risk_score = Column(Float, default=0.0)
    status = Column(String(50))  # safe, caution, warning, danger, blocked
    
    # Registry check results
    in_registry = Column(Boolean, default=False)
    trust_level = Column(Integer, default=0)  # 0-3
    
    # Analysis scores breakdown
    technical_score = Column(Float, default=0.0)
    linguistic_score = Column(Float, default=0.0)
    behavioral_score = Column(Float, default=0.0)
    contextual_score = Column(Float, default=0.0)
    
    analysis_details = Column(JSONB)

    # Raw data
    body_text = Column(Text)
    raw_headers = Column(JSONB)
    raw_email_path = Column(String(512))
    
    analyzed_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    mail_account = relationship("MailAccount", back_populates="email_analyses")


# =============================================================================
# TRUSTED REGISTRY (Updated with organization scope)
# =============================================================================

class TrustedRegistry(Base):
    """
    Реестр доверенных отправителей.
    Может быть глобальным (organization_id=NULL) или привязанным к организации.
    """
    __tablename__ = "trusted_registry"

    id = Column(Integer, primary_key=True, index=True)
    
    # Scope: NULL = global, otherwise organization-specific
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)
    
    email_address = Column(String(255), index=True, nullable=False)
    domain = Column(String(255), index=True, nullable=False)
    organization_name = Column(String(255))
    trust_level = Column(Integer, default=1)  # 1: max trust, 2: high, 3: medium
    added_by = Column(Integer, ForeignKey("users.id"))
    approved_by = Column(Integer, ForeignKey("users.id"))
    is_verified = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    status = Column(String(50), default="active")  # active, pending, quarantine
    total_emails = Column(Integer, default=0)
    last_email_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# =============================================================================
# PHISHING REPORTS & ALERTS (Updated with user isolation)
# =============================================================================

class PhishingReport(Base):
    """
    Отчёт о фишинге от пользователя.
    """
    __tablename__ = "phishing_reports"

    id = Column(Integer, primary_key=True, index=True)
    reporter_id = Column(Integer, ForeignKey("users.id"), index=True)
    message_id = Column(String(255), index=True)
    from_address = Column(String(255), index=True, nullable=False)
    subject = Column(Text)
    reason = Column(Text)
    status = Column(String(50), default="pending")  # pending, investigating, confirmed, false_positive
    severity = Column(String(50))  # low, medium, high, critical
    investigated_by = Column(Integer, ForeignKey("users.id"))
    resolved_at = Column(DateTime)
    reported_at = Column(DateTime, default=datetime.utcnow)


class ThreatAlert(Base):
    """
    Глобальные алерты об угрозах (уровень организации).
    """
    __tablename__ = "threat_alerts"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)
    alert_type = Column(String(50), nullable=False)  # spear_phishing, mass_phishing, compromised_account
    severity = Column(String(50), nullable=False)  # low, medium, high, critical
    title = Column(String(255), nullable=False)
    description = Column(Text)
    affected_users = Column(Integer, default=0)
    source_address = Column(String(255))
    indicators = Column(Text)  # JSON stored as text
    status = Column(String(50), default="active")  # active, investigating, resolved
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime)


class Alert(Base):
    """
    Алерт по конкретному письму (привязан к пользователю).
    """
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    email_analysis_id = Column(Integer, ForeignKey("email_analyses.id"), nullable=True, index=True)
    alert_type = Column(String(100), nullable=False)
    severity = Column(String(20), nullable=False)  # LOW/MEDIUM/HIGH/CRITICAL
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    message = Column(Text, nullable=True)
    recipient_email = Column(String(255), nullable=False)
    sender_email = Column(String(255), nullable=False)
    action_taken = Column(String(50), nullable=False, default="PENDING")
    status = Column(String(50), nullable=False, default="OPEN")
    acknowledged_at = Column(DateTime, nullable=True)
    acknowledged_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# =============================================================================
# DATABASE INITIALIZATION
# =============================================================================

# =============================================================================
# TRUST SCORES
# =============================================================================

class EmployeeTrustScore(Base):
    """
    Рейтинг доверия сотрудника на основе его поведения.
    """
    __tablename__ = "employee_trust_scores"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    trust_score = Column(Float, default=70.0)  # 0-100
    trend = Column(String(50), default="stable")  # up, down, stable
    total_emails_scanned = Column(Integer, default=0)
    phishing_simulations_failed = Column(Integer, default=0)
    top_communication_partners = Column(JSONB, default=list) # List of domains
    last_updated = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User")


async def init_db():
    """
    Initialize database tables
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✓ Database tables created successfully")


if __name__ == "__main__":
    import asyncio
    asyncio.run(init_db())
