
import asyncio
import random
import os
import sys
from datetime import datetime, timedelta
from database import AsyncSessionLocal, User, EmailAnalysis, TrustedRegistry, Alert, ThreatAlert, Organization, EmployeeTrustScore, Base, engine
from sqlalchemy import text, select
from auth.permissions import get_password_hash

# Add parent directory to path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def reset_db(session):
    print("🗑️  Cleaning database...")
    # Order matters for foreign keys
    try:
        await session.execute(text("TRUNCATE TABLE email_analysis, emails, alerts, threat_alerts, employee_trust_scores, users, organizations RESTART IDENTITY CASCADE"))
        await session.commit()
    except Exception as e:
        print(f"Warning during truncate: {e}")

async def seed_presentation_data():
    async with AsyncSessionLocal() as session:
        try:
            await reset_db(session)

            # 1. Create Organization
            org = Organization(
                name="Spear-Guard Global Corp",
                domain="spear-guard.com",
                subscription_plan="enterprise",
                settings={"risk_threshold": 70}
            )
            session.add(org)
            await session.flush()
            print("✓ Organization created")

            # 2. Create Key Users
            users = [
                {
                    "email": "admin@spear-guard.com",
                    "full_name": "Security Officer",
                    "role": "admin",
                    "dept": "Security Ops"
                },
                {
                    "email": "ceo@spear-guard.com",
                    "full_name": "Alexei Petrov",
                    "role": "employee",
                    "dept": "Executive"
                },
                {
                    "email": "finance@spear-guard.com",
                    "full_name": "Maria Ivanova",
                    "role": "employee",
                    "dept": "Finance"
                }
            ]

            db_users = {}
            for u in users:
                user = User(
                    email=u["email"],
                    full_name=u["full_name"],
                    hashed_password=get_password_hash("demo123"),
                    role=u["role"],
                    organization_id=org.id,
                    department=u["dept"]
                )
                session.add(user)
                db_users[u["email"]] = user
            
            await session.flush()
            
            # 3. Create Trust Scores
            # Maria (Finance) is High Risk (clicker)
            ts_maria = EmployeeTrustScore(
                user_id=db_users["finance@spear-guard.com"].id,
                trust_score=45.0, # BAD
                trend="down",
                total_emails_scanned=1240,
                phishing_simulations_failed=2,
                top_communication_partners=["bank-client.ru", "unknown-sender.net"],
                last_updated=datetime.utcnow()
            )
            session.add(ts_maria)

            # CEO is Safe
            ts_ceo = EmployeeTrustScore(
                user_id=db_users["ceo@spear-guard.com"].id,
                trust_score=92.0, # GOOD
                trend="up",
                total_emails_scanned=5800,
                phishing_simulations_failed=0,
                top_communication_partners=["investors.com", "board.org"],
                last_updated=datetime.utcnow()
            )
            session.add(ts_ceo)
            print("✓ Users & Trust Scores created")

            # 4. Golden Scenarios (The meat of the demo)

            # Scenario A: CEO Fraud (Kill Chain)
            # This is the "Attack" video email - EXACT MATCH TO PRESENTATION
            analysis_ceo_fraud = EmailAnalysis(
                message_id="msg_attack_001",
                from_address="aleksey.petrov.ceo@mail.ru", # Real looking freemail
                to_address="finance@spear-guard.com",
                subject="Срочно / Project Alpha",
                content_preview="Мария, я сейчас на встрече с инвесторами. Срочно проведи оплату по договору для Project Alpha, иначе сорвем сделку. Детали в WhatsApp.",
                risk_score=98.5,
                risk_level="CRITICAL",
                status="danger",
                
                # Breakdown
                technical_score=60.0, # Reply-To mismatch
                linguistic_score=100.0, # KILL CHAIN
                behavioral_score=95.0, # Anomaly
                
                # Detailed JSONs
                technical_result={
                    "authentication": {"spf": "pass", "dkim": "pass"},
                    "spoofing": {"score": 50, "indicators": ["Reply-To Mismatch: mail.ru vs spear-guard.com"]},
                    "header_anomalies": {"score": 80}
                },
                linguistic_result={
                    "risk_score": 100,
                    "risk_level": "CRITICAL",
                    "attack_type": "bec_fraud",
                    "indicators": ["🔥 KILL CHAIN: CEO Fraud Pattern Detected", "Ургентность: 'Срочно'", "Переход в мессенджер: 'WhatsApp'", "Финансы: 'оплату по договору'"],
                    "explanation": "ВНИМАНИЕ: Обнаружен паттерн атаки 'CEO Fraud'. Хакер использует авторитет (CEO) и срочность, чтобы заставить сотрудника совершить финансовую операцию в обход процедур."
                },
                
                analyzed_at=datetime.utcnow() - timedelta(minutes=5)
            )
            session.add(analysis_ceo_fraud)

            # Scenario B: Safe Email
            analysis_safe = EmailAnalysis(
                message_id="msg_safe_002",
                from_address="jira@spear-guard.com",
                to_address="finance@spear-guard.com",
                subject="JIRA: New comments on ticket FIN-123",
                content_preview="User Alex posted a comment: 'Please attach the invoice for Q3.'",
                risk_score=5.0,
                risk_level="SAFE",
                status="safe",
                technical_score=100.0,
                linguistic_score=2.0,
                analyzed_at=datetime.utcnow() - timedelta(minutes=12)
            )
            session.add(analysis_safe)
            
            # Scenario C: Credential Phishing
            analysis_cred = EmailAnalysis(
                message_id="msg_phish_003",
                from_address="security-alert@microsoft-support-verify.com",
                to_address="ceo@spear-guard.com",
                subject="Action Required: Password Expiry",
                content_preview="Your password expires in 2 hours. Click here to keep your current password.",
                risk_score=92.0,
                risk_level="CRITICAL",
                status="danger",
                linguistic_result={
                    "risk_score": 92,
                    "attack_type": "credential_phishing", 
                    "indicators": ["🔥 KILL CHAIN: Credential Harvesting", "Urgency: 'expires in 2 hours'", "Link: 'Click here'"],
                    "explanation": "Попытка кражи учетных данных через создание искусственной срочности (expiry)."
                },
                analyzed_at=datetime.utcnow() - timedelta(hours=2)
            )
            session.add(analysis_cred)

            # 5. Background Noise (Stats)
            # Create 30 safe emails over last 7 days using REAL domains
            real_senders = [
                ("rospotrebnadzor@gosuslugi.ru", "Госуслуги: Статус заявления"),
                ("no-reply@sberbank.ru", "СберБанк: Выписка по карте *4455"),
                ("check@ofd-yandex.ru", "Яндекс.ОФД: Чек прихода"),
                ("newsletter@habr.com", "Хабр: Лучшее за неделю"),
                ("billing@cloud.yandex.ru", "Yandex Cloud: Счет на оплату"),
                ("info@ozon.ru", "Ozon: Заказ ожидает в пункте выдачи"),
                ("support@tbank.ru", "Т-Банк: Кэшбэк за февраль"),
                ("buhgalteria@kontur.ru", "Контур.Экстерн: Отчет сдан"),
                ("hr@headhunter.ru", "hh.ru: Новые вакансии для вас"),
                ("team@slack.com", "Slack: New login from Chrome"),
                ("security@google.com", "Google: Security alert for your linked account"),
                ("delivery@samokat.ru", "Самокат: Ваш заказ доставлен")
            ]

            for i in range(35):
                d = datetime.utcnow() - timedelta(days=random.randint(0, 7), hours=random.randint(0, 23))
                sender_email, subj = random.choice(real_senders)
                
                a = EmailAnalysis(
                    message_id=f"msg_bg_{i}",
                    from_address=sender_email,
                    to_address="admin@spear-guard.com",
                    subject=subj, # Realistic subject
                    risk_score=random.uniform(0, 15), # Mostly safe
                    risk_level="SAFE",
                    status="safe",
                    analyzed_at=d
                )
                session.add(a)

            await session.commit()
            print("✓ Scenarios (CEO Fraud, Safe, Phish) & History created")
            print("\n★★★ PRESENTATION DATA READY ★★★")
            print("Use 'admin@spear-guard.com' / 'demo123' to login.")

        except Exception as e:
            await session.rollback()
            print(f"✗ Error: {e}")
            raise

if __name__ == "__main__":
    asyncio.run(seed_presentation_data())
