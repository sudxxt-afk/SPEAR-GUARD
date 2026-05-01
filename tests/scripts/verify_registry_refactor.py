import asyncio
import logging
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from services.registry_checker import RegistryChecker
from database import get_db

logging.basicConfig(level=logging.INFO)

async def main():
    print("Initializing DB session...")
    async for db in get_db():
        print("Initializing RegistryChecker...")
        checker = RegistryChecker(db)
        
        print("Running check_incoming_email...")
        try:
            result = await checker.check_incoming_email(
                from_address="test@example.com",
                to_address="recipient@example.com",
                subject="Test Subject",
                ip_address="127.0.0.1",
                headers={"Subject": "Test Subject"},
                body_preview="This is a test body.",
                use_cache=False
            )
            print("Check result:", result)
        except Exception as e:
            print("Error:", e)
            import traceback
            traceback.print_exc()
        break # Only need one session

if __name__ == "__main__":
    asyncio.run(main())
