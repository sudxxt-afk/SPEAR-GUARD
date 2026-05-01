
import asyncio
from sqlalchemy import select
from database import AsyncSessionLocal, User
import sys

async def check_admin():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.email == "admin@spear-guard.com"))
        user = result.scalars().first()
        if user:
            print(f"FOUND: User {user.email} exists. Role: {user.role}")
            print(f"Hash start: {user.hashed_password[:10]}...")
        else:
            print("NOT FOUND: User admin@spear-guard.com does not exist.")

if __name__ == "__main__":
    asyncio.run(check_admin())
