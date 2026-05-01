"""
Email technical validation utilities
SPF, DKIM, IP reputation checks
"""
import re
import logging
from typing import Dict, Optional, Tuple
from datetime import datetime
import ipaddress

logger = logging.getLogger(__name__)



# Utility functions for email parsing

def extract_domain_from_email(email: str) -> str:
    """Extract domain from email address"""
    if "@" in email:
        return email.split("@")[1].lower()
    return ""


def normalize_email(email: str) -> str:
    """Normalize email address (lowercase, strip whitespace)"""
    return email.strip().lower()


def is_valid_email_format(email: str) -> bool:
    """Basic email format validation"""
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return bool(re.match(pattern, email))
