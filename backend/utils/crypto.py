"""
Crypto utilities for secure storage of sensitive data.
Uses Fernet symmetric encryption for IMAP passwords.

IMPORTANT: The ENCRYPTION_KEY must be kept secure and consistent.
If the key is changed, all encrypted passwords will become invalid.
"""
import os
import base64
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import logging

logger = logging.getLogger(__name__)


def get_encryption_key() -> bytes:
    """
    Get or derive the encryption key from environment.

    The ENCRYPTION_KEY should be a valid Fernet key (32 url-safe base64-encoded bytes).
    If not provided, we derive one from SECRET_KEY using PBKDF2.

    BUG-15 fix: fail fast in production if SECRET_KEY uses the dev default.
    BUG-16 fix: ENCRYPTION_SALT is now read from environment (per-deployment).
    """
    encryption_key = os.getenv("ENCRYPTION_KEY")

    if encryption_key:
        # Use provided Fernet key directly
        return encryption_key.encode()

    # Derive from SECRET_KEY if ENCRYPTION_KEY not set
    secret_key = os.getenv("SECRET_KEY")

    # BUG-15 fix: fail fast if using the dev fallback key in non-dev env
    environment = os.getenv("ENVIRONMENT", "development")
    if not secret_key:
        if environment != "development":
            raise ValueError(
                "SECRET_KEY environment variable must be set in production. "
                "Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
            )
        secret_key = "dev-secret-key-change-in-production"

    if secret_key == "dev-secret-key-change-in-production" and environment != "development":
        raise ValueError(
            "SECRET_KEY is set to the default dev value in a non-development environment. "
            "Set a secure SECRET_KEY in .env before deploying."
        )

    # BUG-16 fix: use per-deployment salt from environment, not hardcoded
    salt = os.getenv("ENCRYPTION_SALT", "spear-guard-salt-v1").encode()
    if len(salt) < 8:
        raise ValueError("ENCRYPTION_SALT must be at least 8 characters")

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )

    key = base64.urlsafe_b64encode(kdf.derive(secret_key.encode()))
    return key


# Initialize Fernet cipher
_fernet: Fernet | None = None


def get_fernet() -> Fernet:
    """Get or create the Fernet cipher instance."""
    global _fernet
    if _fernet is None:
        key = get_encryption_key()
        _fernet = Fernet(key)
    return _fernet


def encrypt_password(plain_password: str) -> str:
    """
    Encrypt a password for secure storage.
    
    Args:
        plain_password: The plain text password
        
    Returns:
        Base64-encoded encrypted password string
    """
    if not plain_password:
        raise ValueError("Password cannot be empty")
    
    fernet = get_fernet()
    encrypted = fernet.encrypt(plain_password.encode())
    return encrypted.decode()


def decrypt_password(encrypted_password: str) -> str:
    """
    Decrypt a stored password.
    
    Args:
        encrypted_password: The encrypted password string
        
    Returns:
        The decrypted plain text password
        
    Raises:
        ValueError: If decryption fails (invalid key or corrupted data)
    """
    if not encrypted_password:
        raise ValueError("Encrypted password cannot be empty")
    
    try:
        fernet = get_fernet()
        decrypted = fernet.decrypt(encrypted_password.encode())
        return decrypted.decode()
    except InvalidToken as e:
        logger.error("Failed to decrypt password - invalid token or key mismatch")
        raise ValueError("Failed to decrypt password. The encryption key may have changed.") from e


def generate_encryption_key() -> str:
    """
    Generate a new Fernet encryption key.
    Use this to create the ENCRYPTION_KEY for .env file.
    
    Returns:
        A url-safe base64-encoded 32-byte key string
    """
    key = Fernet.generate_key()
    return key.decode()


# =============================================================================
# CLI for key generation
# =============================================================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "generate":
        print("Generated ENCRYPTION_KEY for .env:")
        print(generate_encryption_key())
    else:
        # Test encryption/decryption
        test_password = "test_password_123"
        print(f"Original: {test_password}")
        
        encrypted = encrypt_password(test_password)
        print(f"Encrypted: {encrypted}")
        
        decrypted = decrypt_password(encrypted)
        print(f"Decrypted: {decrypted}")
        
        assert test_password == decrypted, "Encryption/decryption roundtrip failed!"
        print("✓ Encryption test passed!")
