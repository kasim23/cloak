from __future__ import annotations

from pathlib import Path
from typing import Dict, Literal, Optional
import yaml
from pydantic import BaseModel, Field

# ---- Entity schema used across the engine ----
EntityType = Literal[
    "PERSON","ORG","LOC","EMAIL","PHONE","ACCOUNT","IP","SSN","CREDIT_CARD","SECRET","DATE","OTHER"
]

# ---- Policy (what to do with each entity) ----
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
    min_confidence: float = 0.75 # global floor (detectors can have their own too)


# ---- Detector configs (toggle and tune without code changes) ----
class HFConfig(BaseModel):
    enabled: bool = False
    model: str = "dslim/bert-base-NER"
    min_confidence: float = 0.65
    window_chars: int = 2000
    overlap_chars: int = 200
    aggregation: Literal["simple", "max", "average"] = "simple"
    device: Literal["auto", "cpu"] = "auto"

class SpacyConfig(BaseModel):
    enabled: bool = True
    model: str = "en_core_web_sm"
    min_confidence: float = 0.0  # small model doesn’t expose scores; keep 0.0

class RegexPacks(BaseModel):
    pii: bool = True       # EMAIL, PHONE, SSN, CREDIT_CARD, IBAN, etc.
    secrets: bool = True   # API keys, AWS, GitHub tokens…
    network: bool = True   # IP, IPv6, MAC, URL

class EntityRulerConfig(BaseModel):
    enabled: bool = True
    address_patterns: bool = True
    id_patterns: bool = True

class Detectors(BaseModel):
    regex: bool = True
    regex_packs: RegexPacks = Field(default_factory=RegexPacks)
    spacy: SpacyConfig = Field(default_factory=SpacyConfig)
    hf: HFConfig = Field(default_factory=HFConfig)
    spacy_ruler: EntityRulerConfig = Field(default_factory=EntityRulerConfig)

# ---- Root config ----
class CloakConfig(BaseModel):
    policy: Policy = Field(default_factory=Policy)
    detectors: Detectors = Field(default_factory=Detectors)

# ---- Loader ----
def load_config(path: Optional[Path]) -> CloakConfig:
    if not path:
        return CloakConfig()
    data = yaml.safe_load(Path(path).read_text())
    return CloakConfig(**data)
