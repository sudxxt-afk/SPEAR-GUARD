import asyncio
import random
from datetime import datetime, timedelta
from sqlalchemy import select
from database import AsyncSessionLocal, User, EmailAnalysis, TrustedRegistry, Alert, ThreatAlert
from auth.permissions import get_password_hash

async def seed_data():
    async with AsyncSessionLocal() as session:
        try:
            # 1. Create Admin User
            result = await session.execute(select(User).where(User.email == "admin@spear-guard.gov.ru"))
            admin = result.scalars().first()
            if not admin:
                admin = User(
                    email="admin@spear-guard.gov.ru",
                    full_name="Администратор Безопасности",
                    hashed_password=get_password_hash("admin123"),
                    role="security_officer",
                    organization="ГКИБ",
                    department="Департамент анализа угроз"
                )
                session.add(admin)
                print("✓ Admin user created")
            else:
                print("! Admin user already exists, skipping")

            await session.flush()

            # 2. Seed Trusted Registry
            registry_data = [
                ("gosuslugi.ru", "Госуслуги", 1),
                ("nalog.gov.ru", "ФНС России", 1),
                ("mil.ru", "Минобороны", 2),
                ("sberbank.ru", "Сбербанк", 1),
                ("yandex-team.ru", "Yandex Support", 3),
            ]
            for domain, org, level in registry_data:
                email = f"support@{domain}"
                stmt = select(TrustedRegistry).where(TrustedRegistry.email_address == email)
                exists = (await session.execute(stmt)).scalars().first()
                if not exists:
                    session.add(TrustedRegistry(
                        email_address=email,
                        domain=domain,
                        organization_name=org,
                        trust_level=level,
                        is_verified=True,
                        status="active"
                    ))
            print("✓ Trusted registry entries processed")

            await session.flush()

            # 3. Seed Email Analyses (only if empty to avoid bloat)
            check_analysis = (await session.execute(select(EmailAnalysis).limit(1))).scalars().first()
            if not check_analysis:
                subjects = [
                    "Срочное обновление безопасности",
                    "Отчет по инцидентам за неделю",
                    "Запрос на предоставление доступа",
                    "Смена пароля вашей учетной записи",
                    "Новое распоряжение №123-ФЗ"
                ]
                senders = ["phish@attacker.com", "legit@gosuslugi.ru", "fake-admin@domain.io", "hr@mil.ru", "support@sber-secure.ru"]
                
                for i in range(20):
                    score = random.randint(0, 100)
                    status = "safe" if score < 30 else "caution" if score < 60 else "warning" if score < 85 else "danger"
                    
                    analysis = EmailAnalysis(
                        message_id=f"msg_{i}_{random.randint(1000, 9999)}",
                        from_address=random.choice(senders),
                        to_address="admin@spear-guard.gov.ru",
                        subject=random.choice(subjects),
                        risk_score=float(score),
                        status=status,
                        technical_score=float(random.randint(0, 100)),
                        linguistic_score=float(random.randint(0, 100)),
                        behavioral_score=float(random.randint(0, 100)),
                        contextual_score=float(random.randint(0, 100)),
                        analyzed_at=datetime.utcnow() - timedelta(hours=random.randint(0, 48))
                    )
                    session.add(analysis)
                print("✓ Email analyses seeded")
            else:
                print("! Email analyses exist, skipping")

            # 4. Seed Alerts (only if empty)
            check_alerts = (await session.execute(select(Alert).limit(1))).scalars().first()
            if not check_alerts:
                alert_types = ["Geographic Anomaly", "Credential Phish", "Urgency Detection", "Mismatched Sender"]
                for i in range(10):
                    alert = Alert(
                        alert_type=random.choice(alert_types),
                        severity=random.choice(["LOW", "MEDIUM", "HIGH", "CRITICAL"]),
                        title=f"Обнаружена угроза #{i+100}",
                        description="Система зафиксировала подозрительную активность, характерную для фишинговой атаки.",
                        recipient_email="admin@spear-guard.gov.ru",
                        sender_email="phish@attacker.com",
                        status="OPEN",
                        created_at=datetime.utcnow() - timedelta(minutes=random.randint(10, 1440))
                    )
                    session.add(alert)
                print("✓ Alerts seeded")
            else:
                print("! Alerts exist, skipping")

            await session.commit()
            print("\n★★★ База данных успешно подготовлена! ★★★")
            print("Логин: admin@spear-guard.gov.ru")
            print("Пароль: admin123")

        except Exception as e:
            await session.rollback()
            print(f"✗ Ошибка при сидировании: {e}")
            raise

if __name__ == "__main__":
    asyncio.run(seed_data())