import asyncio
import sys
import os

# Add parent directory to path to import backend modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import AsyncSessionLocal, TrustedRegistry
from sqlalchemy import select
from datetime import datetime

# TRUSTED CORRESPONDENTS (Russia & Tech Giants)
# Format: (email, organization, trust_level)
# Level 1: Max Trust (Ministries, Internal)
# Level 2: High Trust (Banks, Partners)
# Level 3: Medium Trust (Common Services)

TRUSTED_DATA = [
    # GOV.RU
    ("admin@gosuslugi.ru", "Gosuslugi Portal", 1),
    ("support@gosuslugi.ru", "Gosuslugi Support", 1),
    ("no-reply@gosuslugi.ru", "Gosuslugi Notifications", 1),
    ("nalog@nalog.ru", "Federal Tax Service", 1),
    ("info@fsb.gov.ru", "FSB Russia", 1),
    ("press@mvd.gov.ru", "MVD Russia", 1),
    ("mail@ministry.gov.ru", "Ministry Generic", 1),
    ("pension@pfr.gov.ru", "Pension Fund", 1),
    ("info@cbr.ru", "Central Bank of Russia", 1),
    
    # Major Russian Companies
    ("info@sberbank.ru", "Sberbank", 2),
    ("support@sberbank.ru", "Sberbank Support", 2),
    ("business@sberbank.ru", "Sberbank Business", 2),
    ("info@gazprom.ru", "Gazprom", 2),
    ("press@rosneft.ru", "Rosneft", 2),
    ("support@yandex.ru", "Yandex", 2),
    ("no-reply@yandex.ru", "Yandex Notifications", 2),
    ("team@vk.com", "VK Team", 2),
    ("support@vk.com", "VK Support", 2),
    ("info@ozon.ru", "Ozon", 3),
    ("help@wildberries.ru", "Wildberries", 3),
    
    # Global Tech (Infrastructure)
    ("no-reply@accounts.google.com", "Google Accounts", 1),
    ("notification@google.com", "Google Services", 2),
    ("security@microsoft.com", "Microsoft Security", 1),
    ("verify@twitter.com", "X (Twitter) Verification", 3),
    ("security@facebookmail.com", "Meta Security", 2),
    ("notifications@github.com", "GitHub", 2),
    ("support@slack.com", "Slack", 2),
    ("zoom@zoom.us", "Zoom", 2),
]

async def seed_registry():
    print(f"🚀 Starting Trusted Registry population...")
    async with AsyncSessionLocal() as db:
        added = 0
        skipped = 0
        
        for email, org, level in TRUSTED_DATA:
            domain = email.split('@')[1]
            
            # Check existence
            result = await db.execute(
                select(TrustedRegistry).where(TrustedRegistry.email_address == email)
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                print(f"⏩ Skipping {email} (already exists)")
                skipped += 1
                continue
            
            # Create new entry
            entry = TrustedRegistry(
                email_address=email,
                domain=domain,
                organization_name=org,
                trust_level=level,
                is_verified=True,
                is_active=True,
                status="active",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(entry)
            added += 1
            print(f"✅ Added {email} ({org}) - Level {level}")
        
        await db.commit()
        print(f"\n🎉 Finished! Added: {added}, Skipped: {skipped}")

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(seed_registry())
