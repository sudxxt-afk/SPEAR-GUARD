
import asyncio
import os
import sys
from sqlalchemy import text, select

# Add the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine, AsyncSessionLocal, User
from auth.permissions import get_password_hash, UserRole

async def setup_system():
    print("🚀 Starting system setup...")
    
    # --------------------------------------------------------------------------
    # 1. Fix Database Schema
    # --------------------------------------------------------------------------
    print("\n🔧 Checking database schema...")
    
    async with engine.begin() as conn:
        # Create organizations table
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
        
        # Add organization_id to users
        try:
            await conn.execute(text("""
                ALTER TABLE users 
                ADD COLUMN IF NOT EXISTS organization_id INTEGER REFERENCES organizations(id),
                ADD COLUMN IF NOT EXISTS department VARCHAR(255);
            """))
            print("  ✓ Column users.organization_id checked/added")
        except Exception as e:
            print(f"  Warning adding users.organization_id: {e}")

        # Create mail_accounts table
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
        print("  ✓ Table mail_accounts checked/created")

        # Update email_analyses table (Plural!)
        try:
            await conn.execute(text("""
                ALTER TABLE email_analyses 
                ADD COLUMN IF NOT EXISTS mail_account_id INTEGER REFERENCES mail_accounts(id),
                ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES users(id);
            """))
            print("  ✓ Table email_analyses updated")
        except Exception as e:
            print(f"  Warning updating email_analyses: {e}")

    # --------------------------------------------------------------------------
    # 2. Setup Admin User
    # --------------------------------------------------------------------------
    print("\n👤 Configuring Admin user...")
    
    # Use interactive input if no args provided, or defaults/env vars
    email = "admin@spear-guard.gov.ru"
    password = "admin"
    
    # Check if run interactively (simple check)
    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
         email = input("Enter admin email (default: admin@spear-guard.gov.ru): ").strip() or email
         password = input("Enter admin password (default: admin): ").strip() or password

    async with AsyncSessionLocal() as db:
        # Check if user exists
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        
        hashed_pw = get_password_hash(password)
        
        if user:
            print(f"  User {email} found. Promoting to ADMIN...")
            user.role = UserRole.ADMIN
            user.hashed_password = hashed_pw
            user.is_active = True
        else:
            print(f"  Creating new admin user {email}...")
            user = User(
                email=email,
                full_name="System Administrator",
                hashed_password=hashed_pw,
                role=UserRole.ADMIN,
                is_active=True,
                organization_id=None
            )
            db.add(user)
        
        await db.commit()
        print(f"  ✅ Admin user {email} successfully configured!")
        print(f"  🔑 Password: {password}")

    print("\n✨ Setup completed! You can now log in.")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    try:
        asyncio.run(setup_system())
    except Exception as e:
        print(f"\n❌ Error during setup: {e}")
        import traceback
        traceback.print_exc()
