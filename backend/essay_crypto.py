"""Versioned encryption helpers for protected essay sources."""

import base64
import os

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

_ENCRYPT_V3 = b'\x02'


def _derive_fernet(password, salt):
    """Derive a Fernet key from a password and random salt."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(), length=32, salt=salt, iterations=100000,
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode('utf-8')))


def encrypt_content(plaintext, password):
    """Encrypt Markdown using PBKDF2-SHA256 and Fernet."""
    salt = os.urandom(16)
    token = Fernet(_derive_fernet(password, salt)).encrypt(plaintext.encode('utf-8'))
    return base64.b64encode(_ENCRYPT_V3 + salt + token).decode('ascii')


def decrypt_content(encrypted_b64, password):
    """Decrypt v3 content, raising ValueError for invalid or wrong passwords."""
    raw = base64.b64decode(encrypted_b64)
    if not raw or raw[0] != 2 or len(raw) <= 17:
        raise ValueError('Unknown or legacy encryption format — re-encrypt with v3 Fernet')
    try:
        return Fernet(_derive_fernet(password, raw[1:17])).decrypt(raw[17:]).decode('utf-8')
    except InvalidToken:
        raise ValueError('Wrong password or corrupted data')
