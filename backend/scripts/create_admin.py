
import asyncio
import os
import sys
from sqlalchemy import select

# Add the parent directory to sys.path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import AsyncSessionLocal, User
from auth.permissions import get_password_hash, UserRole

async def create_admin():
    email = input("Enter admin email (default: admin@spear-guard.gov.ru): ").strip() or "admin@spear-guard.gov.ru"
    password = input("Enter admin password (default: admin123): ").strip() or "admin123"
    
    async with AsyncSessionLocal() as db:
        # Check if user exists
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        
        if user:
            print(f"User {email} already exists. Updating role to ADMIN...")
            user.role = UserRole.ADMIN
            user.hashed_password = get_password_hash(password)
            user.is_active = True
        else:
            print(f"Creating new admin user {email}...")
            user = User(
                email=email,
                full_name="System Administrator",
                hashed_password=get_password_hash(password),
                role=UserRole.ADMIN,
                is_active=True,
                organization_id=None # Admins can be global or belong to an org
            )
            db.add(user)
        
        await db.commit()
        print(f"✅ Admin user {email} successfully configured!")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(create_admin())
