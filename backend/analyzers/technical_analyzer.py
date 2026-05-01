"""
Technical Email Analyzer
Comprehensive analysis of email headers, SPF, DKIM, DMARC
"""
import logging
import re
import asyncio
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
import email
from email import policy
from email.parser import BytesParser
import dns.resolver
import dns.exception

from utils.spf_checker import verify_spf, check_spf_alignment
from utils.dkim_checker import verify_dkim, check_dkim_alignment
from utils.email_validator import extract_domain_from_email, normalize_email

logger = logging.getLogger(__name__)


class TechnicalAnalyzer:
    """
    Comprehensive technical analysis of email headers

    Performs:
    - SPF validation
    - DKIM verification
    - DMARC policy check with alignment
    - Display name spoofing detection
    - Email routing analysis
    - Header anomaly detection
    """

    def __init__(self):
        self.dns_resolver = dns.resolver.Resolver()
        self.dns_resolver.timeout = 5.0
        self.dns_resolver.lifetime = 5.0

    async def check_headers(
        self,
        raw_email: Optional[bytes] = None,
        headers: Dict[str, str] = {},
        body: Optional[str] = None,
        sender_ip: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Comprehensive header analysis including SPF, DKIM, DMARC, Spoofing, and Arc Checks.
        """
        logger.info("Starting comprehensive header analysis")
        start_time = datetime.utcnow()

        try:
            if raw_email:
                msg, parsed_headers, parsed_body = self._parse_raw_email(raw_email)
                headers = parsed_headers or headers or {}
                body = parsed_body or body
            else:
                msg = None
                headers = headers or {}

            from_address = headers.get("From", "")
            to_address = headers.get("To", "")
            return_path = headers.get("Return-Path", "")

            from_email = self._extract_email_address(from_address)
            return_path_email = self._extract_email_address(return_path)

            from_domain = extract_domain_from_email(from_email) if from_email else None
            return_path_domain = extract_domain_from_email(return_path_email) if return_path_email else None

            # SPF / DKIM / DMARC
            spf_result = await (self.verify_spf(from_email, sender_ip) if sender_ip and from_email else self._skip_check("SPF", "Missing sender_ip or from_email"))
            dkim_result = await (self.verify_dkim(raw_email) if raw_email else self._skip_check("DKIM", "Raw email required"))
            dmarc_result = await (self.check_dmarc(from_domain, spf_result, dkim_result) if from_domain else self._skip_check("DMARC", "Missing from_domain"))

            # Other checks in parallel
            spoofing_result, routing_result = await asyncio.gather(
                self.detect_display_name_spoofing(from_address, from_domain) if from_address else self._skip_check("Display Name", "Missing from_address"),
                self.analyze_routing(headers),
            )

            header_anomalies = self._detect_header_anomalies(headers)

            # --- MERGE PARANOID CHECKS ---
            # 1. Reply-To Mismatch (Merge into spoofing_result)
            reply_to = headers.get("Reply-To")
            if reply_to:
                mismatch_indicator = self._check_reply_to_mismatch(headers.get("From", ""), reply_to)
                if mismatch_indicator:
                    if isinstance(spoofing_result, dict):
                        spoofing_result.setdefault("indicators", []).append(mismatch_indicator)
                        spoofing_result["score"] = min(spoofing_result.get("score", 100) - 50, 50)
            
            # 2. Homoglyph / Mixed Script Check (Merge into header_anomalies)
            if self._contains_homoglyphs(headers.get("From", "")) or (body and self._contains_homoglyphs(body[:500])):
                if isinstance(header_anomalies, dict):
                     header_anomalies.setdefault("issues", []).append("Detected mixed scripts (Homoglyphs)")
                     header_anomalies["score"] = min(header_anomalies.get("score", 100) - 30, 70)

            spf_alignment = None
            dkim_alignment = None
            if from_domain and return_path_domain and isinstance(spf_result, dict):
                spf_alignment = await check_spf_alignment(from_domain, return_path_domain)
            if from_domain and isinstance(dkim_result, dict) and dkim_result.get("signing_domain"):
                dkim_alignment = check_dkim_alignment(from_domain, dkim_result["signing_domain"])

            auth_score = self._calculate_auth_score(spf_result, dkim_result, dmarc_result, spf_alignment, dkim_alignment)
            
            # Recalculate risk level to include new spoofing/anomaly scores
            risk_level = self._determine_risk_level(auth_score, spoofing_result, header_anomalies)
            
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000

            return {
                "authentication": {
                    "spf": spf_result if isinstance(spf_result, dict) else {"skipped": True},
                    "dkim": dkim_result if isinstance(dkim_result, dict) else {"skipped": True},
                    "dmarc": dmarc_result if isinstance(dmarc_result, dict) else {"skipped": True},
                    "spf_alignment": spf_alignment,
                    "dkim_alignment": dkim_alignment,
                    "score": auth_score,
                },
                "spoofing": spoofing_result if isinstance(spoofing_result, dict) else {"skipped": True},
                "routing": routing_result if isinstance(routing_result, dict) else {"skipped": True},
                "header_anomalies": header_anomalies,
                "risk_level": risk_level,
                "summary": self._create_summary(auth_score, risk_level, spf_result, dkim_result, dmarc_result, spoofing_result),
                "timestamp": datetime.utcnow().isoformat(),
                "processing_time_ms": round(processing_time, 2),
            }

        except Exception as e:
            logger.error(f"Error in check_headers: {e}", exc_info=True)
            return {"error": str(e), "timestamp": datetime.utcnow().isoformat()}

    async def _skip_check(self, check_name: str, reason: str) -> Dict:
        return {"skipped": True, "reason": reason, "check": check_name}

    def _parse_raw_email(self, raw_email: bytes) -> Tuple[email.message.Message, Dict, str]:
        try:
            msg = BytesParser(policy=policy.default).parsebytes(raw_email)
            headers = {k: msg.get(k, "") for k in msg.keys()}
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        payload = part.get_payload(decode=True)
                        if payload:
                            body = payload.decode("utf-8", errors="ignore")
                            break
            else:
                payload = msg.get_payload(decode=True)
                if payload:
                    body = payload.decode("utf-8", errors="ignore")
            return msg, headers, body
        except Exception as e:
            logger.error(f"Error parsing raw email: {e}")
            return None, {}, ""

    def _extract_email_address(self, header_value: str) -> str:
        if not header_value:
            return ""
        match = re.search(r"<([^>]+)>", header_value)
        if match:
            return match.group(1).strip()
        return header_value.strip()

    async def verify_spf(self, sender_email: str, sender_ip: str) -> Dict:
        try:
            return await verify_spf(sender_email, sender_ip)
        except Exception as e:
            logger.error(f"SPF verification error: {e}")
            return {"error": str(e), "result": "error"}

    async def verify_dkim(self, raw_email: bytes) -> Dict:
        try:
            return await verify_dkim(raw_email)
        except Exception as e:
            logger.error(f"DKIM verification error: {e}")
            return {"error": str(e), "result": "error"}

    async def check_dmarc(self, domain: str, spf: Dict, dkim: Dict) -> Dict:
        """
        Check DMARC policy for domain and evaluate alignment with SPF/DKIM results.
        """
        try:
            dmarc_domain = f"_dmarc.{domain}"
            answers = await asyncio.get_event_loop().run_in_executor(None, self._query_dmarc_record, dmarc_domain)

            if not answers:
                return {
                    "present": False,
                    "policy": None,
                    "subdomain_policy": None,
                    "percentage": 100,
                    "alignment_spf_pass": False,
                    "alignment_dkim_pass": False,
                    "details": f"No DMARC record for {domain}",
                }

            record = answers[0]
            policy_info = self._parse_dmarc_record(record)

            aspf = policy_info.get("aspf", "r")
            adkim = policy_info.get("adkim", "r")
            from_domain = domain or ""
            spf_domain = spf.get("domain") if isinstance(spf, dict) else None
            dkim_domain = None
            if isinstance(dkim, dict):
                dkim_domain = dkim.get("signing_domain") or dkim.get("domain")

            def relaxed_match(a, b):
                return bool(a and b and a.lower().endswith(b.lower()))

            alignment_spf_pass = False
            if isinstance(spf, dict) and spf.get("result") == "pass" and spf_domain:
                alignment_spf_pass = (spf_domain.lower() == from_domain.lower()) if aspf == "s" else relaxed_match(spf_domain, from_domain)

            alignment_dkim_pass = False
            if isinstance(dkim, dict) and dkim.get("result") == "pass" and dkim_domain:
                alignment_dkim_pass = (dkim_domain.lower() == from_domain.lower()) if adkim == "s" else relaxed_match(dkim_domain, from_domain)

            return {
                "present": True,
                "record": record,
                "policy": policy_info.get("p"),
                "subdomain_policy": policy_info.get("sp"),
                "percentage": int(policy_info.get("pct", 100)),
                "alignment_spf": aspf,
                "alignment_dkim": adkim,
                "alignment_spf_pass": alignment_spf_pass,
                "alignment_dkim_pass": alignment_dkim_pass,
                "report_addresses": policy_info.get("rua", []),
                "forensic_addresses": policy_info.get("ruf", []),
                "details": self._get_dmarc_details(policy_info),
            }
        except Exception as e:
            logger.error(f"DMARC check error: {e}")
            return {"error": str(e), "present": False}

    def _query_dmarc_record(self, dmarc_domain: str) -> List[str]:
        try:
            answers = self.dns_resolver.resolve(dmarc_domain, "TXT")
            records = []
            for rdata in answers:
                txt_value = str(rdata).strip('"')
                if txt_value.startswith("v=DMARC1"):
                    records.append(txt_value)
            return records
        except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.exception.Timeout):
            return []
        except Exception as e:
            logger.error(f"DMARC DNS query error: {e}")
            return []

    def _parse_dmarc_record(self, record: str) -> Dict:
        try:
            tags = {}
            parts = record.split(";")
            for part in parts:
                if "=" in part:
                    k, v = part.strip().split("=", 1)
                    tags[k] = v
            # Split rua/ruf by comma
            if "rua" in tags:
                tags["rua"] = [addr.strip() for addr in tags["rua"].split(",") if addr.strip()]
            if "ruf" in tags:
                tags["ruf"] = [addr.strip() for addr in tags["ruf"].split(",") if addr.strip()]
            return tags
        except Exception as e:
            logger.error(f"Error parsing DMARC record: {e}")
            return {}

    def _get_dmarc_details(self, policy_info: Dict) -> str:
        parts = []
        if "p" in policy_info:
            parts.append(f"Policy={policy_info.get('p')}")
        if "sp" in policy_info:
            parts.append(f"Subdomain={policy_info.get('sp')}")
        if "pct" in policy_info:
            parts.append(f"pct={policy_info.get('pct')}")
        return "; ".join(parts) if parts else "No DMARC details"

    async def detect_display_name_spoofing(self, from_header: str, from_domain: Optional[str]) -> Dict:
        """
        Detect display name spoofing with enhanced checks:
        - Display name vs domain mismatch
        - Homograph attacks (mixed cyrillic/latin)
        - Suspicious TLDs
        - Punycode domain detection
        """
        spoofed = False
        reasons = []
        score = 100
        
        try:
            # Check for display name vs domain mismatch
            if from_domain:
                name_part = re.sub(r"<.*?>", "", from_header).strip().strip('"')
                if name_part and from_domain.lower() not in name_part.lower():
                    reasons.append("Display name does not reference sender domain")
                    spoofed = True
                    score -= 15
            
            # Homograph Attack Detection (mixed cyrillic/latin characters)
            if from_domain:
                homograph_result = self._detect_homograph_attack(from_domain)
                if homograph_result["is_homograph"]:
                    reasons.append(f"Homograph attack detected: {homograph_result['details']}")
                    spoofed = True
                    score -= 40  # High penalty - serious attack
            
            # Check display name for homograph attacks too
            if name_part:
                display_homograph = self._detect_homograph_attack(name_part)
                if display_homograph["is_homograph"]:
                    reasons.append(f"Display name contains mixed scripts: {display_homograph['details']}")
                    spoofed = True
                    score -= 25
            
            # Suspicious TLD Check
            if from_domain:
                tld_result = self._check_suspicious_tld(from_domain)
                if tld_result["suspicious"]:
                    reasons.append(f"Suspicious TLD: {tld_result['tld']} ({tld_result['reason']})")
                    score -= tld_result["penalty"]
            
            # Punycode domain detection (internationalized domain)
            if from_domain and from_domain.startswith("xn--"):
                reasons.append("Punycode (internationalized) domain detected")
                score -= 20
                
        except Exception as e:
            logger.error(f"Display name spoofing check error: {e}")
            
        return {
            "spoofed": spoofed or score < 70,
            "reasons": reasons,
            "score": max(0, score),
            "risk_level": "high" if score < 50 else "medium" if score < 80 else "low"
        }

    def _detect_homograph_attack(self, text: str) -> Dict:
        """
        Detect homograph attacks using mixed script detection.
        Returns True if text contains suspicious mix of Latin and Cyrillic.
        """
        if not text:
            return {"is_homograph": False, "details": ""}
        
        # Common homograph character pairs (Cyrillic lookalikes for Latin)
        # Cyrillic: а, с, е, о, р, х, у, В, Н, К, М, Т, А, Е, О, Р, С, Х
        # Latin:    a, c, e, o, p, x, y, B, H, K, M, T, A, E, O, P, C, X
        cyrillic_chars = set('аАсСеЕоОрРхХуУВНКМТ')
        latin_chars = set('aAcCeEoOpPxXyYBHKMT')
        
        has_cyrillic = False
        has_latin = False
        suspicious_chars = []
        
        for char in text:
            if char in cyrillic_chars:
                has_cyrillic = True
                suspicious_chars.append(char)
            elif char in latin_chars:
                has_latin = True
        
        # Mixed script is suspicious
        is_homograph = has_cyrillic and has_latin
        
        # Also check for pure cyrillic trying to look like latin domain
        if not is_homograph and has_cyrillic:
            # Check if it looks like a known domain
            known_domains = ["google", "microsoft", "apple", "amazon", "yandex", 
                           "sberbank", "vtb", "gosuslugi", "nalog", "pfr"]
            text_lower = text.lower()
            for domain in known_domains:
                # Very rough similarity check
                if len(text_lower) == len(domain) and text_lower != domain:
                    is_homograph = True
                    suspicious_chars = list(set(text_lower) & cyrillic_chars)
                    break
        
        return {
            "is_homograph": is_homograph,
            "has_cyrillic": has_cyrillic,
            "has_latin": has_latin,
            "suspicious_chars": suspicious_chars[:5],
            "details": f"Mixed Cyrillic/Latin characters: {', '.join(suspicious_chars[:3])}" if is_homograph else ""
        }

    def _check_suspicious_tld(self, domain: str) -> Dict:
        """
        Check if domain uses a suspicious or high-risk TLD.
        """
        # Extract TLD
        parts = domain.lower().split(".")
        if len(parts) < 2:
            return {"suspicious": False, "tld": "", "reason": "", "penalty": 0}
        
        tld = parts[-1]
        
        # High-risk TLDs (commonly used in phishing)
        high_risk_tlds = {
            "xyz": ("Very common in spam/phishing", 25),
            "top": ("High abuse rate", 25),
            "click": ("Phishing-associated TLD", 30),
            "link": ("Phishing-associated TLD", 25),
            "work": ("Spam-associated TLD", 20),
            "tk": ("Free TLD, high abuse", 30),
            "ml": ("Free TLD, high abuse", 30),
            "ga": ("Free TLD, high abuse", 30),
            "cf": ("Free TLD, high abuse", 30),
            "gq": ("Free TLD, high abuse", 30),
            "buzz": ("Spam-associated TLD", 20),
            "club": ("Moderate abuse rate", 15),
            "online": ("Moderate abuse rate", 15),
            "site": ("Moderate abuse rate", 15),
            "website": ("Moderate abuse rate", 15),
            "space": ("Moderate abuse rate", 15),
            "pw": ("High abuse rate", 25),
            "cc": ("Moderate abuse rate", 15),
            "ws": ("Moderate abuse rate", 15),
            "info": ("Elevated abuse rate", 10),
            "biz": ("Elevated abuse rate", 10),
        }
        
        if tld in high_risk_tlds:
            reason, penalty = high_risk_tlds[tld]
            return {"suspicious": True, "tld": f".{tld}", "reason": reason, "penalty": penalty}
        
        # Trusted government TLDs (bonus)
        trusted_tlds = {"gov", "mil", "edu", "gov.ru", "ac.ru"}
        if tld in trusted_tlds or domain.endswith(".gov.ru"):
            return {"suspicious": False, "tld": f".{tld}", "reason": "Trusted TLD", "penalty": -5}
        
        return {"suspicious": False, "tld": f".{tld}", "reason": "", "penalty": 0}

    async def analyze_routing(self, headers: Dict[str, str]) -> Dict:
        try:
            received_headers = [v for k, v in headers.items() if k.lower() == "received"]
            hop_count = len(received_headers)
            issues = []
            score = 100
            hops = []

            for received in received_headers:
                hop_info = self._parse_received_header(received)
                hops.append(hop_info)
                if hop_info.get("ip") and self._is_private_ip(hop_info["ip"]):
                    issues.append(f"Private IP in public relay path: {hop_info['ip']}")
                    score -= 15

            time_anomalies = self._check_time_anomalies(hops)
            if time_anomalies:
                issues.extend(time_anomalies)
                score -= 10 * len(time_anomalies)

            return {
                "hop_count": hop_count,
                "hops": hops[:5],
                "issues": issues,
                "score": max(0, score),
                "suspicious": score < 70,
                "details": self._get_routing_details(hop_count, issues),
            }
        except Exception as e:
            logger.error(f"Routing analysis error: {e}")
            return {"error": str(e)}

    def _parse_received_header(self, received: str) -> Dict:
        ip_match = re.search(r"\[(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\]", received)
        ip = ip_match.group(1) if ip_match else None
        from_match = re.search(r"from\s+([^\s]+)", received, re.IGNORECASE)
        hostname = from_match.group(1) if from_match else None
        time_match = re.search(r";?\s*(.+)$", received)
        timestamp = time_match.group(1).strip() if time_match else None
        return {"ip": ip, "hostname": hostname, "timestamp": timestamp, "raw": received[:100]}

    def _is_private_ip(self, ip: str) -> bool:
        try:
            import ipaddress

            return ipaddress.ip_address(ip).is_private
        except Exception:
            return False

    def _check_time_anomalies(self, hops: List[Dict]) -> List[str]:
        """
        Check for time-based anomalies in email routing.
        
        Detects:
        - Backwards time travel (later hop has earlier timestamp)
        - Large time gaps between hops
        - Timestamps in the future
        """
        anomalies = []
        parsed_times = []
        
        for hop in hops:
            ts = hop.get("timestamp")
            if not ts:
                continue
            try:
                # Try multiple date formats
                from email.utils import parsedate_to_datetime
                dt = parsedate_to_datetime(ts)
                parsed_times.append((hop, dt))
            except Exception:
                # Try alternative parsing
                try:
                    from dateutil import parser as date_parser
                    dt = date_parser.parse(ts, fuzzy=True)
                    parsed_times.append((hop, dt))
                except Exception:
                    continue
        
        if len(parsed_times) < 2:
            return anomalies
        
        # Check for backwards time (later hops should have later timestamps)
        for i in range(1, len(parsed_times)):
            prev_hop, prev_time = parsed_times[i-1]
            curr_hop, curr_time = parsed_times[i]
            
            # Time should progress forward in email routing
            time_diff = (curr_time - prev_time).total_seconds()
            
            if time_diff < -300:  # More than 5 min backwards
                anomalies.append(f"Time anomaly: backwards time travel ({abs(int(time_diff))}s)")
            elif time_diff > 86400:  # More than 24 hours gap
                anomalies.append(f"Time anomaly: large gap ({int(time_diff/3600)}h between hops)")
        
        # Check for future timestamps
        now = datetime.utcnow()
        for hop, dt in parsed_times:
            if dt.replace(tzinfo=None) > now + timedelta(hours=1):
                anomalies.append("Time anomaly: future timestamp detected")
                break
        
        return anomalies

    def _get_routing_details(self, hop_count: int, issues: List[str]) -> str:
        if not issues:
            return f"Routing OK: {hop_count} hops, no anomalies"
        return f"Routing Issues: {hop_count} hops - {'; '.join(issues)}"

    def _detect_header_anomalies(self, headers: Dict[str, str]) -> Dict:
        """
        Detect header anomalies with enhanced checks:
        - Missing required headers
        - Return-Path mismatch
        - Suspicious X-Mailer/User-Agent
        - Multiple Received headers analysis
        - Suspicious custom headers
        """
        anomalies = []
        score = 100
        
        # Required headers check
        required = ["From", "To", "Date", "Message-ID"]
        for header in required:
            if header not in headers:
                anomalies.append(f"Missing required header: {header}")
                score -= 15

        # Return-Path vs From domain mismatch
        if "Return-Path" in headers and "From" in headers:
            return_path = self._extract_email_address(headers["Return-Path"])
            from_addr = self._extract_email_address(headers["From"])
            if return_path and from_addr:
                return_domain = extract_domain_from_email(return_path)
                from_domain = extract_domain_from_email(from_addr)
                if return_domain and from_domain and return_domain != from_domain:
                    anomalies.append(f"Return-Path domain ({return_domain}) differs from From ({from_domain})")
                    score -= 20

        # X-Mailer analysis (suspicious mail clients)
        x_mailer = headers.get("X-Mailer", "").lower()
        if x_mailer:
            suspicious_mailers = [
                ("phpmailer", "PHP bulk mailer", 15),
                ("python", "Script-based sending", 10),
                ("perl", "Script-based sending", 10),
                ("swiftmailer", "PHP bulk mailer", 15),
                ("sendmail", "Direct sendmail (unusual)", 5),
                ("mass mailer", "Bulk mail tool", 25),
                ("mailchimp", "Marketing platform", 5),
                ("campaign", "Marketing campaign tool", 10),
                ("newsletter", "Newsletter tool", 5),
            ]
            for mailer, reason, penalty in suspicious_mailers:
                if mailer in x_mailer:
                    anomalies.append(f"Suspicious X-Mailer: {reason} ({headers.get('X-Mailer', '')[:50]})")
                    score -= penalty
                    break
        
        # User-Agent analysis
        user_agent = headers.get("User-Agent", "").lower()
        if user_agent:
            suspicious_agents = [
                ("curl", "Command-line HTTP tool", 20),
                ("wget", "Command-line download tool", 20),
                ("python-requests", "Automated script", 15),
                ("scrapy", "Web scraping tool", 25),
                ("bot", "Automated bot", 15),
            ]
            for agent, reason, penalty in suspicious_agents:
                if agent in user_agent:
                    anomalies.append(f"Suspicious User-Agent: {reason}")
                    score -= penalty
                    break

        # Check for missing Message-ID or suspicious format
        message_id = headers.get("Message-ID", "")
        if message_id:
            # Suspicious if Message-ID doesn't contain @ or <
            if "@" not in message_id or "<" not in message_id:
                anomalies.append("Malformed Message-ID header")
                score -= 10
        
        # Check for suspicious custom headers
        suspicious_headers = {
            "X-PHP-Script": ("PHP script origin", 15),
            "X-PHP-Originating-Script": ("PHP script origin", 15),
            "X-Spam-Status": ("Already flagged as spam", 20),
            "X-Spam-Flag": ("Spam flag present", 20),
            "X-Virus-Scanned": ("", 0),  # Not suspicious, just informational
        }
        for header_name, (reason, penalty) in suspicious_headers.items():
            if header_name in headers and penalty > 0:
                anomalies.append(f"Suspicious header: {header_name} ({reason})")
                score -= penalty

        # Count Received headers (too many or too few is suspicious)
        received_count = sum(1 for k in headers.keys() if k.lower() == "received")
        if received_count == 0:
            anomalies.append("No Received headers (direct injection?)")
            score -= 25
        elif received_count > 15:
            anomalies.append(f"Excessive Received headers ({received_count}) - possible relay abuse")
            score -= 15

        # Check for Reply-To that differs from From (already in context, but critical)
        if "Reply-To" in headers and "From" in headers:
            reply_to = self._extract_email_address(headers["Reply-To"])
            from_addr = self._extract_email_address(headers["From"])
            if reply_to and from_addr:
                reply_domain = extract_domain_from_email(reply_to)
                from_domain = extract_domain_from_email(from_addr)
                if reply_domain and from_domain and reply_domain != from_domain:
                    anomalies.append(f"Reply-To domain ({reply_domain}) differs from From ({from_domain})")
                    score -= 20

        return {
            "anomalies": anomalies, 
            "score": max(0, score), 
            "suspicious": score < 70,
            "anomaly_count": len(anomalies)
        }

    def _check_reply_to_mismatch(self, from_header: str, reply_to: str) -> Optional[str]:
        """Checks if Reply-To is suspiciously different from From address"""
        from utils.email_validator import extract_email_address
        
        f_addr = extract_email_address(from_header)
        r_addr = extract_email_address(reply_to)
        
        if not f_addr or not r_addr: return None
        
        if f_addr.lower() == r_addr.lower(): return None
        
        # Domain mismatch?
        f_domain = f_addr.split('@')[-1]
        r_domain = r_addr.split('@')[-1]
        
        if f_domain != r_domain:
            # Common pattern: From: boss@company.com, Reply-To: boss@gmail.com
            return f"Reply-To domain mismatch: {f_domain} vs {r_domain}"
            
        return None

    def _contains_homoglyphs(self, text: str) -> bool:
        """
        Quick check for mixed Cyrillic and Latin characters in the same word.
        This is a common evasion technique.
        """
        import re
        if not text: return False
        
        # Simple heuristic: word containing both Latin [a-zA-Z] and Cyrillic [а-яА-Я]
        # Exclude common mixed cases like model names (Format-123 is fine, but "Mосква" with Latin M is bad)
        
        words = text.split()
        mixed_count = 0
        
        for word in words:
            # Check if word has latin AND cyrillic
            has_latin = bool(re.search(r'[a-zA-Z]', word))
            has_cyrillic = bool(re.search(r'[а-яА-ЯёЁ]', word))
            if has_latin and has_cyrillic:
                return True
                
        return False

    def _calculate_auth_score(
        self,
        spf: Dict,
        dkim: Dict,
        dmarc: Dict,
        spf_alignment: Optional[Dict],
        dkim_alignment: Optional[Dict],
    ) -> int:
        total_score = 0
        weight_sum = 0

        if isinstance(spf, dict) and "score" in spf:
            total_score += spf["score"] * 0.25
            weight_sum += 0.25
        if isinstance(dkim, dict) and "score" in dkim:
            total_score += dkim["score"] * 0.30
            weight_sum += 0.30
        if isinstance(dmarc, dict) and dmarc.get("present"):
            policy = dmarc.get("policy", "none") or "none"
            policy_scores = {"reject": 100, "quarantine": 75, "none": 50}
            total_score += policy_scores.get(policy, 0) * 0.15
            weight_sum += 0.15
        if spf_alignment and spf_alignment.get("aligned"):
            total_score += 100 * 0.15
            weight_sum += 0.15
        if dmarc.get("alignment_spf_pass") or dmarc.get("alignment_dkim_pass"):
            total_score += 100 * 0.15
            weight_sum += 0.15
        if dkim_alignment and dkim_alignment.get("aligned"):
            total_score += 100 * 0.15
            weight_sum += 0.15

        if weight_sum > 0:
            return int(total_score / weight_sum)
        return 0

    def _determine_risk_level(self, auth_score: int, spoofing: Dict, header_anomalies: Dict) -> str:
        if auth_score >= 85:
            risk = "low"
        elif auth_score >= 65:
            risk = "medium"
        elif auth_score >= 40:
            risk = "high"
        else:
            risk = "critical"

        if isinstance(spoofing, dict) and spoofing.get("spoofed"):
            if risk == "low":
                risk = "medium"
            elif risk == "medium":
                risk = "high"

        if isinstance(header_anomalies, dict) and header_anomalies.get("suspicious"):
            if risk == "low":
                risk = "medium"

        return risk

    def _create_summary(self, auth_score: int, risk_level: str, spf: Dict, dkim: Dict, dmarc: Dict, spoofing: Dict) -> str:
        lines = []
        lines.append(f"Authentication Score: {auth_score}/100")
        lines.append(f"Risk Level: {risk_level.upper()}")
        if isinstance(spf, dict):
            lines.append(f"SPF: {spf.get('result', 'unknown').upper()}")
        if isinstance(dkim, dict):
            lines.append(f"DKIM: {dkim.get('result', 'unknown').upper()}")
        if isinstance(dmarc, dict):
            policy = dmarc.get("policy", "none")
            lines.append(f"DMARC: {str(policy).upper()}")
        if isinstance(spoofing, dict) and spoofing.get("spoofed"):
            lines.append("Possible Display Name Spoofing")
        return " | ".join(lines)


technical_analyzer = TechnicalAnalyzer()
