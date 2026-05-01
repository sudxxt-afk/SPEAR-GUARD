"""
Contextual Email Analyzer
Analyzes email context: keywords, urgency, time of day, and recipient relationships.
"""
import logging
from typing import Dict, Optional, List
from datetime import datetime
from utils.email_validator import extract_domain_from_email

logger = logging.getLogger(__name__)

class ContextualAnalyzer:
    def __init__(self):
        # Extended phishing keywords (60+ phrases in RU/EN)
        self.suspicious_keywords = [
            # Urgency / Срочность
            "urgent", "срочно", "немедленно", "immediately", "asap", "важно", 
            "important", "critical", "критично", "action required", "требуется действие",
            "last chance", "последний шанс", "expires today", "истекает сегодня",
            "limited time", "ограниченное время", "act now", "действуйте сейчас",
            
            # Credentials / Учётные данные
            "password", "пароль", "verify", "подтвердите", "confirm", "подтверждение",
            "login", "войти", "credentials", "учётные данные", "authenticate", "аутентификация",
            "update your", "обновите ваш", "reset password", "сбросить пароль",
            
            # Account threats / Угрозы аккаунту
            "account", "аккаунт", "suspended", "заблокирован", "locked", "заморожен",
            "disabled", "отключён", "unauthorized", "несанкционированный", "access denied",
            "will be closed", "будет закрыт", "unusual activity", "подозрительная активность",
            
            # Financial / Финансовые
            "payment", "платёж", "invoice", "счёт", "refund", "возврат", "transaction",
            "transfer", "перевод", "bank", "банк", "card", "карта", "billing", "оплата",
            
            # Clickbait / Кликбейт
            "click here", "нажмите здесь", "open attachment", "откройте вложение",
            "download", "скачать", "view document", "посмотреть документ",
            
            # Scam / Мошенничество
            "prize", "приз", "lottery", "лотерея", "winner", "выигрыш", "congratulations",
            "поздравляем", "free", "бесплатно", "gift", "подарок", "inheritance", "наследство",
            
            # Authority impersonation / Имперсонация
            "security team", "служба безопасности", "it department", "отдел ит",
            "administrator", "администратор", "tech support", "техподдержка"
        ]

    async def analyze(
        self,
        from_address: str,
        to_address: str,
        subject: str,
        headers: Optional[Dict[str, str]] = None,
        body_preview: Optional[str] = None,
        body_html: Optional[str] = None
    ) -> Dict:
        """
        Validate contextual constraints using deterministic heuristics
        """
        logger.debug(f"Validating context for {from_address} -> {to_address}")

        issues = []
        score = 100
        headers = headers or {}
        
        # Combine subject and body for text analysis
        full_text = f"{subject} {body_preview or ''}"
        
        # 1. Fuzzy Keyword Matching
        fuzzy_issues = self._check_fuzzy_keywords(full_text)
        if fuzzy_issues:
            issues.extend(fuzzy_issues)
            score -= min(10 * len(fuzzy_issues), 40)

        # 2. Homoglyph Detection (Cyrillic/Latin mix)
        homoglyph_issues = self._check_homoglyphs(full_text)
        if homoglyph_issues:
            issues.extend(homoglyph_issues)
            score -= min(15 * len(homoglyph_issues), 45)

        # 3. Link Hygiene (if HTML body is provided or can be extracted)
        # Note: simplistic extraction from body_preview if body_html not passed
        content_to_scan = body_html if body_html else body_preview
        if content_to_scan and ('<a' in content_to_scan or 'http' in content_to_scan):
            link_issues = self._check_link_hygiene(content_to_scan)
            if link_issues:
                issues.extend(link_issues)
                score -= 30  # High penalty for deceptive links

        # 4. Old checks retain value (Reply-To mismatch is still gold standard)
        
        # Check Reply-To domain mismatch
        reply_to = headers.get("Reply-To", "")
        if reply_to:
            reply_to_email = self._extract_email_from_header(reply_to)
            from_email = self._extract_email_from_header(from_address)
            
            if reply_to_email and from_email:
                reply_to_domain = extract_domain_from_email(reply_to_email)
                from_domain = extract_domain_from_email(from_email)
                
                if reply_to_domain and from_domain and reply_to_domain != from_domain:
                    issues.append(f"Reply-To domain mismatch: {reply_to_domain} != {from_domain}")
                    score -= 25

        # Check government domain policy
        to_domain = extract_domain_from_email(to_address)
        from_domain = extract_domain_from_email(from_address)

        if from_domain and from_domain.endswith(".gov.ru") and to_domain and not to_domain.endswith(".gov.ru"):
            issues.append("Government sender to non-government recipient")
            score -= 5

        # Time of day check
        current_hour_utc = datetime.utcnow().hour
        current_hour_msk = (current_hour_utc + 3) % 24
        if current_hour_msk < 6 or current_hour_msk > 22:
            issues.append(f"Email analyzed at unusual hour: {current_hour_msk}:00 MSK")
            score -= 10

        # Caps Lock check (simple heuristic)
        if len(subject) > 10:
             caps_ratio = sum(1 for c in subject if c.isupper()) / len(subject)
             if caps_ratio > 0.5:
                 issues.append(f"Excessive capitalization in subject ({caps_ratio*100:.0f}%)")
                 score -= 15

        return {
            "valid": score >= 60,
            "score": max(0, score),
            "issues": issues,
            "details": f"Context validation: {len(issues)} issues found"
        }

    def _check_fuzzy_keywords(self, text: str) -> List[str]:
        """Find keywords using fuzzy matching (Levenshtein distance)"""
        import difflib
        
        found_issues = []
        words = text.lower().split()
        
        # Optimization: only check words longer than 4 chars effectively
        # and checking a subset of dangerous keywords for performance
        critical_keywords = [k for k in self.suspicious_keywords if len(k) > 4]
        
        for word in words:
            if len(word) < 4: continue
            
            # Check exact match first
            if word in self.suspicious_keywords:
                found_issues.append(f"Suspicious keyword found: '{word}'")
                continue
                
            # Fuzzy match
            # get_close_matches uses Ratcliff/Obershelp, good enough for "fuzzy"
            matches = difflib.get_close_matches(word, critical_keywords, n=1, cutoff=0.8)
            if matches:
                found_issues.append(f"Fuzzy keyword match: '{word}' ~= '{matches[0]}'")
                
        return list(set(found_issues)) # Deduplicate

    def _check_homoglyphs(self, text: str) -> List[str]:
        """Check for mixed Cyrillic/Latin scripts in single words"""
        import re
        
        issues = []
        words = text.split()
        
        # Regex for Cyrillic and Latin
        cyrillic_pattern = re.compile(r'[а-яА-ЯёЁ]')
        latin_pattern = re.compile(r'[a-zA-Z]')
        
        for word in words:
            # Skip short words or obviously mixed things like "part-2"
            if len(word) < 4 or not word.isalnum(): 
                continue
                
            has_cyr = bool(cyrillic_pattern.search(word))
            has_lat = bool(latin_pattern.search(word))
            
            if has_cyr and has_lat:
                issues.append(f"Possible homoglyph attack (mixed scripts): '{word}'")
                
        return list(set(issues))

    def _check_link_hygiene(self, html_content: str) -> List[str]:
        """Parse HTML to find deceptive links (text vs href mismatch) using standard library"""
        from html.parser import HTMLParser
        import re
        
        issues = []
        
        class LinkExtractor(HTMLParser):
            def __init__(self):
                super().__init__()
                self.links = []
                self.in_anchor = False
                self.current_href = None
                self.current_text = []

            def handle_starttag(self, tag, attrs):
                if tag == 'a':
                    self.in_anchor = True
                    for name, value in attrs:
                        if name == 'href':
                            self.current_href = value
                    self.current_text = []

            def handle_endtag(self, tag):
                if tag == 'a' and self.in_anchor:
                    if self.current_href:
                        self.links.append((self.current_href, "".join(self.current_text).strip()))
                    self.in_anchor = False
                    self.current_href = None

            def handle_data(self, data):
                if self.in_anchor:
                    self.current_text.append(data)

        try:
            parser = LinkExtractor()
            parser.feed(html_content)
            
            for href, text in parser.links:
                # If text looks like a domain/url
                # Heuristic: contains dot, no spaces, starts with http or www or ends with .com/ru/etc
                if re.match(r'^(http|www|[a-zA-Z0-9-]+\.[a-z]{2,})', text):
                    
                    # Extract domain from text and href
                    text_domain = text
                    if "://" in text:
                        try:
                            text_domain = text.split("/")[2]
                        except: pass
                    elif "/" in text: # handle cases like "google.com/login"
                         text_domain = text.split("/")[0]

                    href_domain = ""
                    if "://" in href:
                        try:
                            href_domain = href.split("/")[2]
                        except: pass
                    
                    # Clean domains (remove www.)
                    text_domain = text_domain.replace("www.", "").lower()
                    href_domain = href_domain.replace("www.", "").lower()
                    
                    # Compare
                    if text_domain and href_domain and text_domain != href_domain:
                        # Allow subdomains/redirects if base matches? For now strict.
                        # Exclude obvious relative paths or anchors
                        if not href.startswith("/") and not href.startswith("#") and "mailto:" not in href:
                            issues.append(f"Deceptive link: Text says '{text_domain}' but leads to '{href_domain}'")

        except Exception as e:
            logger.error(f"Link hygiene check error: {e}")
            
        return issues

    def _extract_email_from_header(self, header_value: str) -> str:
        """Extract email address from header like 'Name <email@domain.com>'"""
        import re
        if not header_value:
            return ""
        match = re.search(r'<([^>]+)>', header_value)
        if match:
            return match.group(1).strip()
        if '@' in header_value:
            return header_value.strip()
        return ""

# Singleton instance
contextual_analyzer = ContextualAnalyzer()

