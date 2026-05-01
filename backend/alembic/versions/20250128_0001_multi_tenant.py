"""Add multi-tenant models (Organization, MailAccount)

Revision ID: 20250128_0001_multi_tenant
Revises: 20251211_01_add_body_and_headers
Create Date: 2025-01-28 19:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20250128_0001_multi_tenant'
down_revision = '20251211_01'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create organizations table
    op.create_table(
        'organizations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('domain', sa.String(length=255), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_organizations_id'), 'organizations', ['id'], unique=False)
    op.create_index(op.f('ix_organizations_domain'), 'organizations', ['domain'], unique=False)
    op.create_unique_constraint('uq_organizations_name', 'organizations', ['name'])

    # Create mail_accounts table
    op.create_table(
        'mail_accounts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('provider', sa.String(length=50), nullable=True, default='custom'),
        sa.Column('imap_server', sa.String(length=255), nullable=False),
        sa.Column('imap_port', sa.Integer(), nullable=True, default=993),
        sa.Column('imap_use_ssl', sa.Boolean(), nullable=True, default=True),
        sa.Column('username', sa.String(length=255), nullable=False),
        sa.Column('encrypted_password', sa.Text(), nullable=False),
        sa.Column('folder', sa.String(length=255), nullable=True, default='INBOX'),
        sa.Column('sync_interval_minutes', sa.Integer(), nullable=True, default=5),
        sa.Column('max_emails_per_sync', sa.Integer(), nullable=True, default=50),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('status', sa.String(length=50), nullable=True, default='pending'),
        sa.Column('last_sync_at', sa.DateTime(), nullable=True),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('total_emails_synced', sa.Integer(), nullable=True, default=0),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_mail_accounts_id'), 'mail_accounts', ['id'], unique=False)
    op.create_index(op.f('ix_mail_accounts_user_id'), 'mail_accounts', ['user_id'], unique=False)

    # Add organization_id to users table
    op.add_column('users', sa.Column('organization_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_users_organization_id',
        'users', 'organizations',
        ['organization_id'], ['id'],
        ondelete='SET NULL'
    )

    # Add mail_account_id to email_analyses table
    op.add_column('email_analyses', sa.Column('mail_account_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_email_analyses_mail_account_id'), 'email_analyses', ['mail_account_id'], unique=False)
    op.create_foreign_key(
        'fk_email_analyses_mail_account_id',
        'email_analyses', 'mail_accounts',
        ['mail_account_id'], ['id'],
        ondelete='SET NULL'
    )

    # Add organization_id to trusted_registry for org-scoped entries
    op.add_column('trusted_registry', sa.Column('organization_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_trusted_registry_organization_id'), 'trusted_registry', ['organization_id'], unique=False)
    op.create_foreign_key(
        'fk_trusted_registry_organization_id',
        'trusted_registry', 'organizations',
        ['organization_id'], ['id'],
        ondelete='CASCADE'
    )

    # Add organization_id to threat_alerts
    op.add_column('threat_alerts', sa.Column('organization_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_threat_alerts_organization_id'), 'threat_alerts', ['organization_id'], unique=False)
    op.create_foreign_key(
        'fk_threat_alerts_organization_id',
        'threat_alerts', 'organizations',
        ['organization_id'], ['id'],
        ondelete='CASCADE'
    )


def downgrade() -> None:
    # Remove foreign keys and columns in reverse order
    
    # threat_alerts
    op.drop_constraint('fk_threat_alerts_organization_id', 'threat_alerts', type_='foreignkey')
    op.drop_index(op.f('ix_threat_alerts_organization_id'), table_name='threat_alerts')
    op.drop_column('threat_alerts', 'organization_id')

    # trusted_registry
    op.drop_constraint('fk_trusted_registry_organization_id', 'trusted_registry', type_='foreignkey')
    op.drop_index(op.f('ix_trusted_registry_organization_id'), table_name='trusted_registry')
    op.drop_column('trusted_registry', 'organization_id')

    # email_analyses
    op.drop_constraint('fk_email_analyses_mail_account_id', 'email_analyses', type_='foreignkey')
    op.drop_index(op.f('ix_email_analyses_mail_account_id'), table_name='email_analyses')
    op.drop_column('email_analyses', 'mail_account_id')

    # users
    op.drop_constraint('fk_users_organization_id', 'users', type_='foreignkey')
    op.drop_column('users', 'organization_id')

    # mail_accounts
    op.drop_index(op.f('ix_mail_accounts_user_id'), table_name='mail_accounts')
    op.drop_index(op.f('ix_mail_accounts_id'), table_name='mail_accounts')
    op.drop_table('mail_accounts')

    # organizations
    op.drop_constraint('uq_organizations_name', 'organizations', type_='unique')
    op.drop_index(op.f('ix_organizations_domain'), table_name='organizations')
    op.drop_index(op.f('ix_organizations_id'), table_name='organizations')
    op.drop_table('organizations')
