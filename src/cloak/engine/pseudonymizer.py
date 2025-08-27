from __future__ import annotations
import hmac, hashlib, base64, os
from dataclasses import dataclass

@dataclass
class Pseudonymizer:
    """
    Generates deterministic, non-reversible aliases like Person_8F21B3C2.

    - Uses HMAC-SHA256 over (entity_type | lowercase(text)) with a salt.
    - If CLOAK_SALT env var is set, pseudonyms are stable ACROSS runs.
      Otherwise, salt may be set by the caller for per-run stability.
    """
    salt: bytes
    prefix_map: dict[str, str] = None

    def __post_init__(self) -> None:
        if self.prefix_map is None:
            self.prefix_map = {
                "PERSON": "Person",
                "ORG": "Org",
                "LOC": "Loc",
                "GPE": "Loc",
                "ACCOUNT": "Account",
            }

    @staticmethod
    def _norm(text: str) -> str:
        return " ".join(text.strip().split()).lower()

    def alias(self, entity_type: str, text: str, length: int = 8) -> str:
        prefix = self.prefix_map.get(entity_type, "Ent")
        msg = f"{entity_type}|{self._norm(text)}".encode("utf-8")
        digest = hmac.new(self.salt, msg, hashlib.sha256).digest()
        # base32 (letters+digits), upper, strip padding, then take N chars
        code = base64.b32encode(digest).decode("ascii").rstrip("=").upper()[:length]
        return f"{prefix}_{code}"

def pseudonymizer_from_env(default_salt: bytes | None = None) -> Pseudonymizer:
    """
    Prefer a user-provided salt (CLOAK_SALT) for cross-run stability.
    Falls back to the given default salt (per-run stability).
    """
    env = os.getenv("CLOAK_SALT")
    salt = env.encode("utf-8") if env else (default_salt or os.urandom(16))
    return Pseudonymizer(salt=salt)
