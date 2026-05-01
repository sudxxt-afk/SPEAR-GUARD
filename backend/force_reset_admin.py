
import asyncio
import os
import sys
from sqlalchemy import select

# Add the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import AsyncSessionLocal, User
from auth.permissions import get_password_hash, UserRole

async def reset():
    email = "admin@spear-guard.gov.ru"
    password = "admin123"
    
    print(f"Resetting {email} to {password}...")
    
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        
        if user:
            user.hashed_password = get_password_hash(password)
            user.role = UserRole.ADMIN
            user.is_active = True
            print("User found. Updated password.")
        else:
            print("User NOT found. Creating...")
            user = User(
                email=email,
                full_name="System Administrator",
                hashed_password=get_password_hash(password),
                role=UserRole.ADMIN,
                is_active=True,
                organization_id=None
            )
            db.add(user)
        
        await db.commit()
        print("Done.")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(reset())
