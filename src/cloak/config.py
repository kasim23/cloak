from __future__ import annotations

from pathlib import Path
from typing import Dict, Literal, Optional
import yaml
from pydantic import BaseModel, Field

EntityType = Literal[
    "PERSON","ORG","LOC","EMAIL","PHONE","ACCOUNT","IP","SSN","CREDIT_CARD","SECRET","DATE","OTHER"
]

class Policy(BaseModel):
    actions: Dict[EntityType, str] = Field(
        default_factory=lambda: {
            "EMAIL": "mask",
            "PHONE": "mask",
            "PERSON": "pseudonymize",
            "ORG": "pseudonymize",
            "LOC": "pseudonymize",
            "CREDIT_CARD": "drop",
            "SSN": "drop",
            "IP": "mask",
            "SECRET": "drop",
            "DATE": "none",
            "ACCOUNT": "hash",
            "OTHER": "none",
        }
    )
    min_confidence: float = 0.75


class CloakConfig(BaseModel):
    policy: Policy = Field(default_factory=Policy)


def load_config(path: Optional[Path]) -> CloakConfig:
    if not path:
        return CloakConfig()
    data = yaml.safe_load(Path(path).read_text())
    return CloakConfig(**data)
