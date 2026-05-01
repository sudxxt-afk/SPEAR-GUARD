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

def extract_domain_from_email(email: str) -> Optional[str]:
    """Extract domain from email address
    
    Returns:
        Domain string if valid email format, None otherwise
    """
    if not email or "@" not in email:
        return None
    domain = email.split("@")[1].lower()
    # Basic validation - domain should have at least one dot
    if "." not in domain:
        return None
    return domain


def normalize_email(email: str) -> str:
    """Normalize email address (lowercase, strip whitespace)"""
    return email.strip().lower()


def is_valid_email_format(email: str) -> bool:
    """Basic email format validation"""
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return bool(re.match(pattern, email))
