import asyncio
import os
import sys

# Add parent directory to path to allow imports, mimicking presentation_seed.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import AsyncSessionLocal
from sqlalchemy import text

async def check():
    print("Connecting to database...")
    async with AsyncSessionLocal() as session:
        print("--- DB COUNTS ---")
        try:
            res = await session.execute(text("SELECT count(*) FROM email_analyses"))
            print(f"Emails: {res.scalar()}")
            
            res = await session.execute(text("SELECT count(*) FROM trusted_registry"))
            print(f"Trusted Registry: {res.scalar()}")
            
            res = await session.execute(text("SELECT count(*) FROM alerts"))
            print(f"Alerts: {res.scalar()}")
            
            res = await session.execute(text("SELECT count(*) FROM users"))
            print(f"Users: {res.scalar()}")
            
            res = await session.execute(text("SELECT id, email FROM users WHERE email='admin@spear-guard.com'"))
            user = res.fetchone()
            if user:
                print(f"Admin User Found: ID={user[0]}, Email={user[1]}")
            else:
                print("Admin User NOT Found")

        except Exception as e:
            print(f"Error details: {e}")

if __name__ == "__main__":
    asyncio.run(check())
