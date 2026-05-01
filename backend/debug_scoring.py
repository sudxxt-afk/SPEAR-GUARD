import asyncio
import os
import sys

# Setup path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from analyzers.linguistic_analyzer import linguistic_analyzer
from analyzers.technical_analyzer import technical_analyzer

async def debug_analysis():
    print("--- DEBUGGING START ---")
    
    # Sample Data (CEO Fraud)
    subject = "Конфиденциально: Срочный вопрос / Project Alpha"
    body = """Привет,

Я сейчас на встрече с инвесторами, говорить по телефону не могу.
Возникла непредвиденная ситуация с закрытием сделки по проекту Alpha.

Мне нужно, чтобы ты срочно провел платеж контрагенту, иначе мы потеряем контракт.
Это вопрос государственной важности, не терпит отлагательств. 
Никому пока не сообщай, держим в тайне до подписания.

Свяжись со мной в WhatsApp по моему личному номеру +79990000000 для получения реквизитов.
Жду сообщение в ближайшие 10 минут.

--
Алексей Петров
Генеральный Директор
Spear-Guard Inc.
Sent from my iPad"""
    
    sender = "ceo.spearguard@gmail.com" # Simulating external spoof
    
    print(f"\nAnalyzing Text:\n{body[:100]}...")
    
    # 1. Linguistic
    ling_res = await linguistic_analyzer.analyze_text(body, sender=sender, subject=subject)
    print("\n[LINGUISTIC RESULT]")
    print(f"Score: {ling_res.get('risk_score')}")
    print(f"Indicators: {ling_res.get('indicators')}")
    
    # 2. Technical (Simulated headers)
    headers = {
        "From": f"Алексей Петров <{sender}>",
        "To": "employee@spear-guard.gov.ru",
        "Subject": subject,
        "X-Mailer": "iPad Mail (16E233)"
    }
    tech_res = await technical_analyzer.check_headers(headers=headers)
    print("\n[TECHNICAL RESULT]")
    print(f"Auth Score: {tech_res.get('authentication', {}).get('score')}")
    print(f"Spoof Score: {tech_res.get('spoofing', {}).get('score')}")
    print(f"Headers Score: {tech_res.get('header_anomalies', {}).get('score')}")
    
    t_auth = tech_res.get('authentication', {}).get('score', 0)
    t_spoof = tech_res.get('spoofing', {}).get('score', 100)
    t_head = tech_res.get('header_anomalies', {}).get('score', 100)
    
    final_tech = min(t_auth, t_spoof, t_head)
    print(f"Calculated Min Tech Score: {final_tech}")

if __name__ == "__main__":
    asyncio.run(debug_analysis())
