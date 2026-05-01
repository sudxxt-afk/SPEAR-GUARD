"""
AI-Powered Linguistic Analyzer using Google Gemini

Analyzes email content for signs of social engineering:
- Urgency and threat
- Authority impersonation
- Suspicious instructions
- Psychological triggers
"""
import logging
import os
import json
from typing import Dict, Any, Optional

try:
    import google.generativeai as genai
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False

logger = logging.getLogger(__name__)

class LinguisticAnalyzer:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.model = None
        
        if not HAS_GEMINI:
            logger.warning("google-generativeai library not installed. AI analysis disabled.")
            return

        if not self.api_key:
            logger.warning("GEMINI_API_KEY not found in environment. AI analysis disabled.")
            return

        if self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                # Use generic 'flash' alias which usually points to the stable 1.5 Flash
                self.model = genai.GenerativeModel('gemini-flash-latest')
                logger.info("Gemini AI Analyzer initialized with model gemini-flash-latest")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini Client: {e}")

    async def analyze_text(self, text: str, sender: str = "", subject: str = "") -> Dict[str, Any]:
        """
        Analyze email text using Gemini AI with fallback to rule-based analysis.
        Returns a dictionary with risk score and explanation.
        """
        # Run Rule-Based Analysis first (as baseline)
        rule_result = self._fallback_analysis(text, subject, sender)
        rule_score = rule_result.get("risk_score", 0)

        # If AI is not available, return rule result
        if not self.model:
            return rule_result

        # Truncate text to avoid token limits
        content_fragment = text[:10000]

        prompt = f"""
        You are SPEAR-GUARD AI, an elite Cyber-Psychologist and Threat Intelligence Engine. Your goal is to detect Zero-Day Social Engineering and Sophisticated Phishing attacks targeting Russian enterprises.

        **ANALYSIS EXAMPLES:**
        *Case 1: Fake HR Update* -> Reason: Urgency, Impersonation. Verdict: HIGH RISK.
        *Case 2: CEO Fraud* -> Reason: Role Mismatch, Bypass Protocol. Verdict: CRITICAL RISK.

        **ROLE-ACTION CONSISTENCY MATRIX:**
        Use this logic to detect anomalous requests:
        - **IT Support:** CANNOT request passwords or urgent payments.
        - **Government (FNS, FSB):** NEVER request payments/data via email links.
        - **CEO:** RARELY sends "urgent payment" requests to random employees.

        **CURRENT TARGET:**
        Subject: {subject}
        From: {sender}
        Body Fragment:
        {content_fragment}

        **TASK:**
        1. Analyze Sender Authenticity (spoofing).
        2. Check Role-Action Consistency (is this request normal for this role?).
        3. Identify Psychological Triggers (Urgency, Fear, Greed).
        4. Detect Linguistic Anomalies.

        **FINAL VERDICT:**
        Return strictly valid JSON:
        {{
            "risk_score": <float 0-100>,
            "risk_level": <enum: SAFE, LOW, MEDIUM, HIGH, CRITICAL>,
            "summary": "<Short expert verdict in Russian>",
            "indicators": ["<Specific trigger found>", ...],
            "explanation": "<Detailed walkthrough for user in Russian. Explain WHY it is dangerous.>",
            "analysis_type": "ai-generated"
        }}
        Do not use markdown code blocks.
        """

        try:
            # Synchronous call wrapped in async endpoint (FastAPI handles threadpool)
            # or ideally run in executor. For simplicity here:
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.1,
                    response_mime_type="application/json"
                )
            )

            if response.text:
                try:
                    # Cleanup markdown if present
                    clean_text = response.text.strip().replace('```json', '').replace('```', '')
                    analysis_result = json.loads(clean_text)
                    
                    # HYBRID SCORING: Take the higher score
                    ai_score = analysis_result.get("risk_score", 0)
                    
                    if rule_score > ai_score:
                        # Boost AI result with rule findings
                        analysis_result["risk_score"] = float(rule_score)
                        analysis_result["risk_level"] = rule_result["risk_level"]
                        analysis_result["analysis_type"] = "hybrid (rules dominant)"
                        analysis_result["indicators"] = list(set(analysis_result.get("indicators", []) + rule_result.get("indicators", [])))
                        analysis_result["explanation"] += f"\n\n[Правила]: {rule_result['explanation']}"
                    
                    return analysis_result
                except json.JSONDecodeError:
                    logger.error(f"Gemini returned invalid JSON: {response.text[:100]}")
                    return rule_result # Fallback to rules on JSON error
            else:
                return rule_result # Fallback on empty response

        except Exception as e:
            logger.error(f"Gemini analysis failed: {e}")
            return rule_result # Fallback on API error

    def _fallback_analysis(self, text: str, subject: str = "", sender: str = "", error_message: str = None) -> Dict[str, Any]:
        """
        Rule-based fallback analysis when Gemini AI is unavailable.
        Checks for common phishing indicators without AI.
        """
        score = 0
        indicators = []
        combined_text = f"{subject} {text}".lower()
        
        # 1. URGENCY indicators (RU/EN)
        urgency_phrases = [
            ("срочно", 15), ("немедленно", 15), ("urgent", 12), ("immediately", 12),
            ("asap", 10), ("важно", 8), ("important", 8), ("критично", 12),
            ("в течение 24 часов", 15), ("within 24 hours", 15),
            ("последний шанс", 12), ("last chance", 12), ("истекает", 10),
            ("expires", 10), ("deadline", 15), ("действуйте сейчас", 12),
            ("act now", 12), ("не откладывайте", 15), ("не терпит", 15),
            ("matter is urgent", 20), ("до конца дня", 10), ("end of day", 10)
        ]
        cat_score = 0
        for phrase, points in urgency_phrases:
            if phrase in combined_text:
                cat_score += points
                indicators.append(f"Urgency: '{phrase}'")
        score += min(cat_score, 40) # Cap urgency contribution at 40
        
        # 2. FEAR/THREATS indicators
        threat_phrases = [
            ("заблокирован", 20), ("suspended", 18), ("blocked", 18),
            ("будет удален", 18), ("will be deleted", 18), ("аккаунт закрыт", 20),
            ("account closed", 20), ("несанкционированный доступ", 20),
            ("unauthorized access", 20), ("подозрительная активность", 15),
            ("suspicious activity", 15), ("штраф", 15), ("penalty", 12),
            ("legal action", 18), ("судебное", 18), ("police", 15), ("полиция", 15)
        ]
        cat_score = 0
        for phrase, points in threat_phrases:
            if phrase in combined_text:
                cat_score += points
                indicators.append(f"Threat: '{phrase}'")
        score += min(cat_score, 50) # Cap threats at 50
        
        # 3. AUTHORITY impersonation
        authority_phrases = [
            ("служба безопасности", 15), ("security team", 12), ("it department", 10),
            ("отдел ит", 10), ("administrator", 12), ("администратор", 12),
            ("tech support", 10), ("техподдержка", 10), ("ceo", 15), ("директор", 12),
            ("генеральный", 12), ("от имени", 10), ("on behalf of", 10),
            ("госуслуги", 15), ("налоговая", 15), ("пенсионный фонд", 12),
            ("фсб", 20), ("мвд", 18), ("government", 12), ("правительство", 12),
            ("support", 10), ("поддержка", 10)
        ]
        cat_score = 0
        for phrase, points in authority_phrases:
            if phrase in combined_text:
                cat_score += points
                indicators.append(f"Authority claim: '{phrase}'")
        score += min(cat_score, 40) # Cap authority at 40
        
        # 4. SUSPICIOUS INSTRUCTIONS
        instruction_phrases = [
            ("нажмите здесь", 15), ("click here", 12), ("click the link", 12),
            ("перейдите по ссылке", 12), ("скачайте", 12), ("download", 10),
            ("откройте вложение", 15), ("open attachment", 15),
            ("введите пароль", 18), ("enter password", 18), ("verify your", 15),
            ("подтвердите", 12), ("confirm your identity", 15),
            ("update your account", 15), ("обновите данные", 12),
            ("send money", 25), ("переведите", 20), ("bitcoin", 25), ("криптовалют", 20),
            ("whatsapp", 25), ("вотсап", 25), ("личн", 10), ("номер", 5), # Simplified matching
            ("банк-клиент", 25), ("bank-client", 25), ("реквизит", 15), ("invoice", 15),
            ("оплат", 15), ("payment", 15), ("инвестор", 10), ("investor", 10)
        ]
        cat_score = 0
        for phrase, points in instruction_phrases:
            if phrase in combined_text:
                cat_score += points
                indicators.append(f"Suspicious instruction: '{phrase}'")
        score += min(cat_score, 80) # Increased cap for instructions
        
        # 5. CAPS Check
        caps_ratio = sum(1 for c in text if c.isupper()) / max(len(text), 1)
        if caps_ratio > 0.3 and len(text) > 50:
            score += 10
            indicators.append("Excessive CAPS usage")
        
        # --- PARANOID MODE: KILL CHAIN DETECTION ---
        # Detect specific combinations that indicate a sophisticated attack
        attack_type = "generic"
        
        # Scenario 1: BEC / CEO Fraud (Authority + Financial + Urgency)
        has_authority = any("Authority" in i for i in indicators)
        has_money = any("instruction" in i for i in indicators)
        has_urgency = any("Urgency" in i for i in indicators)
        
        if has_authority and has_money and has_urgency:
            score = 100 # MAX SCORE
            risk_level = "CRITICAL"
            indicators.insert(0, "🔥 KILL CHAIN: CEO Fraud Pattern Detected")
            attack_type = "bec_fraud"
            
        # Scenario 2: Account Takeover (Threat + Instruction + Link)
        has_threat = any("Threat" in i for i in indicators)
        has_link = "http" in combined_text or "click" in combined_text or "нажмите" in combined_text
        
        if has_threat and (has_link or has_money):
            score = max(score, 90)
            risk_level = "CRITICAL"
            indicators.insert(0, "🔥 KILL CHAIN: Credential Harvesting Pattern")
            attack_type = "credential_phishing"

        if score >= 60: risk_level = "CRITICAL"
        elif score >= 40: risk_level = "HIGH"
        elif score >= 25: risk_level = "MEDIUM"
        elif score >= 10: risk_level = "LOW"
        else: risk_level = "SAFE"
        
        final_score = min(score, 100)
        
        return {
            "risk_score": float(final_score),
            "risk_level": risk_level,
            "summary": f"Анализ на основе правил: найдено {len(indicators)} индикаторов" if indicators else "Подозрительные паттерны не обнаружены",
            "indicators": indicators[:5],
            "explanation": f"ВНИМАНИЕ: Обнаружен паттерн атаки '{attack_type}'. Выявлено: {', '.join(indicators[:3])}" if indicators else "Письмо не содержит явных словарных индикаторов фишинга",
            "analysis_type": "rule-based",
            "attack_type": attack_type, # Exposed for AnalysisService
            "device_info": {"error": error_message} if error_message else None
        }

# Singleton instance
linguistic_analyzer = LinguisticAnalyzer()
