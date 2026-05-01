
import asyncio
import os
import sys
from sqlalchemy import text

# Add the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine

async def fix_schema():
    print("🔧 Fixing database schema...")
    
    async with engine.begin() as conn:
        # 1. Create organizations table
        print("Checking 'organizations' table...")
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS organizations (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL UNIQUE,
                domain VARCHAR(255),
                description TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (now() at time zone 'utc'),
                updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (now() at time zone 'utc')
            );
        """))
        
        # 2. Add organization_id to users
        print("Checking 'users.organization_id' column...")
        try:
            await conn.execute(text("""
                ALTER TABLE users 
                ADD COLUMN IF NOT EXISTS organization_id INTEGER REFERENCES organizations(id),
                ADD COLUMN IF NOT EXISTS department VARCHAR(255);
            """))
        except Exception as e:
            print(f"Error adding organization_id to users: {e}")

        # 3. Create mail_accounts table
        print("Checking 'mail_accounts' table...")
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS mail_accounts (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                email VARCHAR(255) NOT NULL,
                imap_server VARCHAR(255) NOT NULL,
                imap_port INTEGER NOT NULL,
                username VARCHAR(255) NOT NULL,
                encrypted_password VARCHAR(500) NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                use_ssl BOOLEAN DEFAULT TRUE,
                folder VARCHAR(255) DEFAULT 'INBOX',
                sync_interval_minutes INTEGER DEFAULT 15,
                last_sync_at TIMESTAMP WITHOUT TIME ZONE,
                error_message TEXT,
                created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (now() at time zone 'utc'),
                updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (now() at time zone 'utc')
            );
        """))

        # 4. Update email_analyses table (matches SQLAlchemy model EmailAnalysis.__tablename__)
        print("Checking 'email_analyses' columns...")
        try:
            await conn.execute(text("""
                ALTER TABLE email_analyses
                ADD COLUMN IF NOT EXISTS mail_account_id INTEGER REFERENCES mail_accounts(id),
                ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES users(id);
            """))
        except Exception as e:
            print(f"Error updating email_analysis: {e}")

    print("✅ Database schema fixed successfully!")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(fix_schema())
