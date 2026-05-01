
import asyncio
import random
import os
import sys
from datetime import datetime, timedelta
from database import AsyncSessionLocal, User, EmailAnalysis, Organization, EmployeeTrustScore, Base, engine, TrustedRegistry
from sqlalchemy import text
from auth.permissions import get_password_hash

# Add parent directory to path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def reset_db(session):
    print("🗑️  Cleaning database...")
    try:
        await session.execute(text("TRUNCATE TABLE email_analyses, mail_accounts, alerts, threat_alerts, employee_trust_scores, users, organizations, trusted_registry RESTART IDENTITY CASCADE"))
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
                description="Enterprise License - Demo Account"
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
            ts_maria = EmployeeTrustScore(
                user_id=db_users["finance@spear-guard.com"].id,
                trust_score=45.0,
                trend="down",
                total_emails_scanned=1240,
                phishing_simulations_failed=2,
                top_communication_partners=["bank-client.ru", "unknown-sender.net"],
                last_updated=datetime.utcnow()
            )
            session.add(ts_maria)

            ts_ceo = EmployeeTrustScore(
                user_id=db_users["ceo@spear-guard.com"].id,
                trust_score=92.0,
                trend="up",
                total_emails_scanned=5800,
                phishing_simulations_failed=0,
                top_communication_partners=["investors.com", "board.org"],
                last_updated=datetime.utcnow()
            )
            session.add(ts_ceo)
            print("✓ Users & Trust Scores created")

            # 4. Golden Record: CEO Fraud (Top Priority)
            print("Creating Golden Record (CEO Fraud)...")
            golden_analysis = EmailAnalysis(
                message_id="msg_golden_ceo_fraud",
                from_address="a.petrov@gov-agency.ru", 
                to_address="finance@spear-guard.com",
                user_id=db_users["finance@spear-guard.com"].id,
                subject="СРОЧНО: Корректировка данных по гособоронзаказу / Проект \"Сириус\"",
                body_preview="Коллеги, добрый день. По результатам утреннего совещания в министерстве возникла необходимость экстренно перепроверить реквизиты контрагентов по проекту \"Сириус\" в рамках гособоронзаказа. Связано с новыми санкционными рисками.\n\nЯ сейчас на закрытом заседании, телефоны сдали, поэтому пишу с резервного канала. Прошу срочно подготовить сводную таблицу по всем платежам за последний квартал и отправить мне в WhatsApp на номер +79990000000. Это критично сделать в течение часа, чтобы я успел согласовать данные до подписания протокола.\n\nЕсли возникнут вопросы - не звоните, пишите в мессенджер. Вопрос на личном контроле у замминистра.",
                
                # Scores requested by user
                risk_score=96.0,
                status="danger",
                
                # Detailed breakdown
                technical_score=90.0,
                linguistic_score=96.0,
                behavioral_score=95.0,
                contextual_score=85.0,
                
                analysis_details={
                    "feature_importance": {
                        "urgency": 0.92,
                        "tone_analysis": 0.88,
                        "channel_anomaly": 0.95,
                        "semantic_similarity": 0.89
                    },
                    "linguistic_result": {
                        "risk_score": 96,
                        "risk_level": "CRITICAL",
                        "indicators": [
                            "🔥 KILL CHAIN: CEO Fraud Pattern Detected",
                            "Ургентность: 'СРОЧНО', 'в течение часа'",
                            "Канал увода: 'WhatsApp'",
                            "Давление авторитетом: 'закрытом заседании'"
                        ],
                        "explanation": "Внимание: Обнаружена высокая концентрация маркеров психологического давления. Текст письма содержит попытку перевода коммуникации в неконтролируемый мессенджер. Стилистический вектор текста на 84% отклоняется от типичных сообщений данного отправителя."
                    },
                    "highlight_keywords": {
                        "critical": ["СРОЧНО", "в течение часа", "приостановлено"],
                        "warning": ["WhatsApp", "не смогу ответить"]
                    }
                },
                
                analyzed_at=datetime.utcnow() # Latest email
            )
            session.add(golden_analysis)

            # 5. Background Noise (34-35 emails)
            print("Generating background noise...")
            
            real_senders = [
                ("rospotrebnadzor@gosuslugi.ru", "Госуслуги: Статус заявления", 0.0),
                ("no-reply@sberbank.ru", "СберБанк: Выписка по карте *4455", 0.0),
                ("check@ofd-yandex.ru", "Яндекс.ОФД: Чек прихода", 1.0),
                ("newsletter@habr.com", "Хабр: Лучшее за неделю", 2.0),
                ("billing@cloud.yandex.ru", "Yandex Cloud: Счет на оплату", 0.0),
                ("info@ozon.ru", "Ozon: Заказ ожидает в пункте выдачи", 1.0),
                ("support@tbank.ru", "Т-Банк: Кэшбэк за февраль", 0.0),
                ("buhgalteria@kontur.ru", "Контур.Экстерн: Отчет сдан", 0.0),
                ("hr@headhunter.ru", "hh.ru: Новые вакансии для вас", 3.0),
                ("team@slack.com", "Slack: New login from Chrome", 5.0),
                ("security@google.com", "Google: Security alert for your linked account", 15.0), # Warning
                ("delivery@samokat.ru", "Самокат: Ваш заказ доставлен", 0.0),
                ("spam@untrusted-marketing.com", "Вам доступен кредит под 0%", 65.0), # Spam/Phish
                ("support@microsoft-verify.uk", "Action: Verify your Outlook account", 88.0) # Phish
            ]

            # Generate ~34 emails
            for i in range(35):
                # Spread over last 7 days, avoiding the immediate "now" slot of the Golden Record
                minutes_back = random.randint(30, 7 * 24 * 60) 
                d = datetime.utcnow() - timedelta(minutes=minutes_back)
                
                sender, subj, base_risk = random.choice(real_senders)
                
                # Add some variance to risk
                final_risk = max(0, min(100, base_risk + random.uniform(-2, 5)))
                
                status = "safe"
                if final_risk > 50:
                    status = "warning"
                if final_risk > 80:
                    status = "danger"

                analysis = EmailAnalysis(
                    message_id=f"msg_bg_{i}",
                    from_address=sender,
                    to_address="finance@spear-guard.com" if random.random() > 0.5 else "admin@spear-guard.com",
                    user_id=db_users["finance@spear-guard.com"].id if random.random() > 0.5 else db_users["admin@spear-guard.com"].id,
                    subject=subj,
                    body_preview="This is an automated background email for demonstration purposes...",
                    risk_score=final_risk,
                    status=status,
                    technical_score=max(0, 100 - final_risk), # Inverse correlation for simplicity
                    linguistic_score=final_risk,
                    behavioral_score=final_risk * 0.8,
                    analyzed_at=d,
                    analysis_details={"generated": True}
                )
                session.add(analysis)

            # 6. Seed Trusted Registry (Specific Russian List)
            print("Seeding Trusted Registry (Specific Russian entries)...")
            
            # Format: (email, Organization Name, Trust Level)
            trusted_entries = [
                ("info@minobrnauki.gov.ru", "Минобрнауки", 1),
                ("info@minzdrav.gov.ru", "Минздрав", 1),
                ("ministry@mid.ru", "МИД РФ", 1),
                ("urog@mil.ru", "Минобороны", 1),
                ("stat@gks.ru", "Росстат", 1),
                ("pr@minfin.gov.ru", "Минфин", 1),
                ("postman@rosneft.ru", "Роснефть", 2),
                ("rzd@rzd.ru", "РЖД", 2),
                ("ir@rosneft.ru", "Роснефть (IR)", 2),
                ("shareholders@rosneft.ru", "Роснефть (Акционеры)", 2),
                ("press@center.rzd.ru", "РЖД (Пресс-центр)", 2),
                ("expertiza@mintrans.ru", "Минтранс (Экспертиза)", 1),
                ("info@vladoblgaz.ru", "Газпром регион (Владоблгаз)", 2),
                ("sel-secret@vladoblgaz.ru", "Газпром регион (Секретариат)", 2),
                ("findep@adm.kaluga.ru", "Администрация Калужской обл", 1),
                ("depfin@adm44.ru", "Администрация Костромской обл", 1),
                ("inter-students@minobrnauki.gov.ru", "Минобрнауки (Студенты)", 1),
                ("dip@mid.ru", "МИД РФ (ДИП)", 1),
                ("support@nalog.ru", "ФНС (Поддержка)", 1),
                ("obr@nalog.ru", "ФНС (Обращения)", 1),
                ("press@gazprom.ru", "Газпром (Пресса)", 2),
                ("info@gazprom.ru", "Газпром (Общий)", 2),
                ("pr@sberbank.ru", "Сбербанк (Пресса)", 2),
                ("support@sberbank.ru", "Сбербанк (Поддержка)", 2),
                ("info@rostec.ru", "Ростех", 1),
                ("press@rostec.ru", "Ростех (Пресса)", 1),
                ("info@aeroflot.ru", "Аэрофлот", 2),
                ("pr@aeroflot.ru", "Аэрофлот (Пресса)", 2),
                ("info@lk.ru", "Лукойл", 2),
                ("press@lukoil.com", "Лукойл (Int)", 2),
                ("info@rusal.ru", "Русал", 2),
                ("ir@rusal.ru", "Русал (IR)", 2),
                ("info@alrosa.ru", "Алроса", 2),
                ("press@alrosa.ru", "Алроса (Пресса)", 2),
                ("info@transneft.ru", "Транснефть", 2),
                ("contact@fssprus.ru", "ФССП", 1),
                ("info@rkn.gov.ru", "Роскомнадзор", 1),
                ("info@fas.gov.ru", "ФАС", 1),
                ("info@mintrud.ru", "Минтруд", 1),
                ("info@minenergo.gov.ru", "Минэнерго", 1),
                ("info@mcx.ru", "Минсельхоз", 1),
                ("info@minpromtorg.gov.ru", "Минпромторг", 1),
                ("info@economy.gov.ru", "Минэкономразвития", 1),
                ("info@mvd.ru", "МВД", 1),
                ("info@mchs.gov.ru", "МЧС", 1),
                ("info@minjust.ru", "Минюст", 1),
                ("info@rosstat.gov.ru", "Росстат", 1),
                ("info@government.ru", "Правительство РФ", 1),
                ("info@kremlin.ru", "Кремль", 1),
                ("info@fsb.ru", "ФСБ", 1),
                ("info@rosatom.ru", "Росатом", 1),
                ("press@rosatom.ru", "Росатом (Пресса)", 1),
                ("ir@rosatom.ru", "Росатом (Инвесторы)", 1),
                ("npa@roscosmos.ru", "Роскосмос", 1),
                ("rostelecom@rt.ru", "Ростелеком", 2),
                ("pr@rt.ru", "Ростелеком (PR)", 2),
                ("mail@alfabank.ru", "Альфа-Банк", 2),
                ("client@russianpost.ru", "Почта России", 1),
                ("media@cbr.ru", "ЦБ РФ", 1),
                ("office@digital.gov.ru", "Минцифры", 1),
                ("udmail@fsin.su", "ФСИН", 1),
                ("press@fsin.su", "ФСИН (Пресса)", 1),
                ("info@vtb.ru", "ВТБ", 2),
                ("info@novatek.ru", "Новатэк", 2),
                ("press@tatneft.ru", "Татнефть", 2),
                ("info@sovcomflot.ru", "Совкомфлот", 2),
                ("info@bashneft.ru", "Башнефть", 2),
                ("info@rusnano.ru", "Роснано", 1),
                ("info@glavkosmos.ru", "Главкосмос", 1),
                ("ir@nornik.ru", "Норникель (IR)", 2),
                ("ESG@nornik.ru", "Норникель (ESG)", 2),
                ("gmk@nornik.ru", "Норникель", 2),
                ("pr@nornik.ru", "Норникель (PR)", 2),
                ("rezume@polyus.com", "Полюс (HR)", 2),
                ("ver-hr@polyus.com", "Полюс Вернинское", 2),
                ("post@magnit.ru", "Магнит", 2),
                ("info@x5.ru", "X5 Group", 2),
                ("rosgvard@fgup-ohrana.ru", "Росгвардия (Охрана)", 1),
                ("priemnaya_fso@gov.ru", "ФСО", 1),
                ("skd@nornik.ru", "Норникель (СКД)", 2),
                ("students@polyus.com", "Полюс (Студенты)", 2),
                ("podbor@polyus.com", "Полюс (Подбор)", 2),
                ("info@rrost.ru", "Регистратор РОСТ", 2),
                ("moscow@kept.ru", "Kept (Аудит)", 2),
                ("mail@ins-union.ru", "ВСС", 2),
                ("kinstrakh@ingo.ru", "Ингосстрах", 2),
                ("info@uvz.ru", "Уралвагонзавод", 1),
                ("info@oaoosk.ru", "ОСК", 1),
                ("info@rude.ru", "Рособоронэкспорт", 1)
            ]

            # Remove potential duplicates based on email
            seen_emails = set()
            unique_entries = []
            for email, name, level in trusted_entries:
                email_lower = email.lower().strip()
                if email_lower not in seen_emails:
                    seen_emails.add(email_lower)
                    unique_entries.append((email_lower, name, level))

            for email, name, level in unique_entries:
                domain = email.split('@')[-1]
                entry = TrustedRegistry(
                    organization_id=org.id,
                    email_address=email,
                    domain=domain,
                    organization_name=name,
                    trust_level=level, 
                    added_by=db_users["admin@spear-guard.com"].id,
                    is_verified=True,
                    is_active=True,
                    status="active",
                    total_emails=random.randint(10, 5000),
                    last_email_at=datetime.utcnow() - timedelta(days=random.randint(1, 30))
                )
                session.add(entry)

            print("✓ Trusted Registry seeded.")

            # 7. Create ACTIVE ALERTS for high risk emails
            print("Creating Active Alerts for Dashboard...")
            from database import Alert
            
            # For Golden Record
            golden_alert = Alert(
                user_id=golden_analysis.user_id,
                email_analysis_id=golden_analysis.id,
                alert_type="CEO_FRAUD",
                severity="CRITICAL",
                title=f"CRITICAL: CEO Fraud Suspected from {golden_analysis.from_address}",
                description="Высокая вероятность социальной инженерии. Обнаружена попытка имперсонации руководителя с требованием срочных финансовых действий.",
                message=golden_analysis.body_preview,
                recipient_email=golden_analysis.to_address,
                sender_email=golden_analysis.from_address,
                action_taken="PENDING",
                status="OPEN", # Make it active
                created_at=datetime.utcnow()
            )
            session.add(golden_alert)

            # For Background Threats (just 1 or 2)
            bg_threats = [x for x in session.new if isinstance(x, EmailAnalysis) and x.risk_score > 80 and x != golden_analysis]
            for threat in bg_threats[:2]: # Add alerts for up to 2 bg threats
                alert = Alert(
                    user_id=threat.user_id,
                    email_analysis_id=threat.id,
                    alert_type="PHISHING_DETECTED",
                    severity="HIGH",
                    title=f"High Risk Email Detected: {threat.subject}",
                    description=f"Automated threat detection system flagged email with score {threat.risk_score}",
                    message=threat.body_preview,
                    recipient_email=threat.to_address,
                    sender_email=threat.from_address,
                    action_taken="PENDING",
                    status="OPEN",
                    created_at=threat.analyzed_at
                )
                session.add(alert)
            
            await session.commit()
            print("✓ Alerts created.")

            print("\n★★★ PRESENTATION DATA READY ★★★")
            print(f"Total emails: {35 + 1}")
            print(f"Trusted Registry: {len(unique_entries)} entries")
            print(f"Golden Record: {golden_analysis.subject} (Risk: {golden_analysis.risk_score})")

        except Exception as e:
            await session.rollback()
            print(f"✗ Error: {e}")
            raise

if __name__ == "__main__":
    # Ensure tables exist
    asyncio.run(seed_presentation_data())
