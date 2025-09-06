"""
Natural language parser for redaction customization prompts.

This module extends the existing CLI command parser to handle web app
redaction customization prompts like:
- "redact all personal information"
- "don't redact my name, only SSN and phone numbers"
- "hide email addresses and credit card numbers"
- "remove all sensitive data except dates"

The parser produces a RedactionConfig that can be applied to the Policy
to customize which entities get redacted and how.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Literal, Optional, Set, Tuple

from ..config import Policy

# Entity type mappings for natural language
ENTITY_ALIASES = {
    # Names and people
    "name": "PERSON",
    "names": "PERSON", 
    "person": "PERSON",
    "people": "PERSON",
    "my name": "PERSON",
    
    # Organizations
    "company": "ORG",
    "companies": "ORG",
    "organization": "ORG",
    "org": "ORG",
    
    # Locations
    "address": "LOC",
    "addresses": "LOC",
    "location": "LOC",
    "place": "LOC",
    
    # Contact info
    "email": "EMAIL",
    "emails": "EMAIL", 
    "email address": "EMAIL",
    "phone": "PHONE",
    "phone number": "PHONE",
    "phone numbers": "PHONE",
    "telephone": "PHONE",
    
    # Financial
    "ssn": "SSN",
    "social security": "SSN",
    "social security number": "SSN",
    "credit card": "CREDIT_CARD",
    "credit cards": "CREDIT_CARD",
    "card number": "CREDIT_CARD",
    "account": "ACCOUNT",
    "account number": "ACCOUNT",
    
    # Technical
    "ip": "IP",
    "ip address": "IP",
    "secret": "SECRET",
    "secrets": "SECRET",
    "api key": "SECRET",
    "password": "SECRET",
    "token": "SECRET",
    
    # Dates
    "date": "DATE",
    "dates": "DATE",
}

# Action mappings
ACTION_ALIASES = {
    "redact": "mask",
    "hide": "mask", 
    "mask": "mask",
    "remove": "drop",
    "delete": "drop",
    "drop": "drop",
    "hash": "hash",
    "pseudonymize": "pseudonymize",
    "replace": "pseudonymize",
    "keep": "none",
    "preserve": "none",
    "leave": "none",
}

RedactionAction = Literal["mask", "drop", "hash", "pseudonymize", "none"]


@dataclass
class RedactionConfig:
    """Configuration for customized redaction based on natural language prompt."""
    
    # Entity-specific actions (overrides defaults)
    entity_actions: Dict[str, RedactionAction]
    
    # Global settings
    redact_all_default: bool = True  # True = redact everything by default, False = keep by default
    
    # Confidence adjustment
    confidence_threshold: Optional[float] = None

    def apply_to_policy(self, base_policy: Policy) -> Policy:
        """Apply this redaction config to a base policy, returning a new policy."""
        new_actions = base_policy.actions.copy()
        
        # Apply entity-specific overrides
        for entity, action in self.entity_actions.items():
            new_actions[entity] = action
            
        # If user wants to redact everything by default, set unspecified entities to mask
        if self.redact_all_default:
            for entity in ["PERSON", "ORG", "LOC", "EMAIL", "PHONE", "SSN", "CREDIT_CARD", "SECRET"]:
                if entity not in self.entity_actions:
                    new_actions[entity] = "mask"
        
        return Policy(
            actions=new_actions,
            min_confidence=self.confidence_threshold or base_policy.min_confidence
        )


class RedactionPromptParser:
    """Parser for natural language redaction customization prompts."""
    
    def __init__(self):
        # Intent keywords for simpler, more reliable parsing
        self._exclude_keywords = ["don't", "do not", "keep", "preserve", "leave", "except", "but not"]
        self._include_only_keywords = ["only", "just"]
        self._global_keywords = ["all", "everything", "all personal", "all sensitive", "personal information", "sensitive data"]

    def parse(self, prompt: str) -> RedactionConfig:
        """
        Parse a natural language prompt into a RedactionConfig using simple keyword extraction.
        
        Examples:
        - "redact all personal information" -> redact everything
        - "don't redact my name, only SSN and phone" -> keep names, redact SSN/phone  
        - "hide email addresses and credit cards" -> redact only email/credit cards
        """
        prompt = prompt.strip().lower()
        
        # Extract all mentioned entities
        mentioned_entities = self._extract_mentioned_entities(prompt)
        
        # Determine intent based on keywords
        has_exclude_intent = any(keyword in prompt for keyword in self._exclude_keywords)
        has_include_only_intent = any(keyword in prompt for keyword in self._include_only_keywords)
        has_global_intent = any(keyword in prompt for keyword in self._global_keywords)
        
        # Determine configuration based on intent
        entity_actions = {}
        
        if has_global_intent and has_exclude_intent:
            # "redact all personal information except dates"
            for entity in mentioned_entities:
                entity_actions[entity] = "none"  # Keep mentioned entities
            redact_all_default = True
            
        elif has_exclude_intent and has_include_only_intent:
            # "don't redact my name, only SSN and phone"
            # Split entities: assume first part is to exclude, second part is to include
            exclude_entities, include_entities = self._split_entities_by_intent(prompt, mentioned_entities)
            for entity in exclude_entities:
                entity_actions[entity] = "none"
            for entity in include_entities:
                entity_actions[entity] = "mask"
            redact_all_default = False
            
        elif has_exclude_intent:
            # "don't redact names and dates"
            for entity in mentioned_entities:
                entity_actions[entity] = "none"
            redact_all_default = True
            
        elif has_include_only_intent:
            # "only redact SSN and phone numbers"
            for entity in mentioned_entities:
                entity_actions[entity] = "mask"
            redact_all_default = False
            
        elif has_global_intent and not mentioned_entities:
            # "redact all personal information" (no specific entities mentioned)
            redact_all_default = True
            
        elif mentioned_entities:
            # "hide email addresses and credit cards" or "hide all email addresses"
            for entity in mentioned_entities:
                entity_actions[entity] = "mask"
            redact_all_default = False
            
        else:
            # No clear intent, use safe default
            redact_all_default = True
        
        return RedactionConfig(
            entity_actions=entity_actions,
            redact_all_default=redact_all_default
        )

    def _extract_mentioned_entities(self, prompt: str) -> List[str]:
        """
        Extract all entity types mentioned in the prompt using simple keyword matching.
        
        This is much more reliable than regex patterns.
        """
        entities = []
        
        # Check each entity alias to see if it's mentioned in the prompt
        # Sort by length descending to match longer phrases first (e.g., "email address" before "email")
        sorted_aliases = sorted(ENTITY_ALIASES.items(), key=lambda x: len(x[0]), reverse=True)
        
        for alias, entity_type in sorted_aliases:
            if alias in prompt:
                if entity_type not in entities:
                    entities.append(entity_type)
        
        return entities
    
    def _split_entities_by_intent(self, prompt: str, mentioned_entities: List[str]) -> Tuple[List[str], List[str]]:
        """
        Split entities into exclude vs include based on position relative to keywords.
        
        For prompts like "don't redact my name, only SSN and phone"
        - Entities before "only" -> exclude (keep)  
        - Entities after "only" -> include (redact)
        """
        exclude_entities = []
        include_entities = []
        
        # Simple heuristic: find position of "only" keyword
        only_pos = -1
        for keyword in self._include_only_keywords:
            pos = prompt.find(keyword)
            if pos != -1:
                only_pos = pos
                break
        
        if only_pos == -1:
            # No "only" found, treat all as include entities
            return [], mentioned_entities
        
        # Check which entities appear before vs after "only"
        for entity_type in mentioned_entities:
            # Find the first alias for this entity that appears in the prompt
            entity_pos = -1
            for alias, etype in ENTITY_ALIASES.items():
                if etype == entity_type and alias in prompt:
                    entity_pos = prompt.find(alias)
                    break
            
            if entity_pos != -1:
                if entity_pos < only_pos:
                    exclude_entities.append(entity_type)
                else:
                    include_entities.append(entity_type)
            else:
                # Default to include if position unclear
                include_entities.append(entity_type)
        
        return exclude_entities, include_entities


def parse_redaction_prompt(prompt: str) -> RedactionConfig:
    """
    Convenience function to parse a redaction prompt.
    
    Args:
        prompt: Natural language redaction instruction
        
    Returns:
        RedactionConfig that can be applied to a Policy
        
    Examples:
        >>> config = parse_redaction_prompt("don't redact my name, only SSN")
        >>> policy = config.apply_to_policy(base_policy)
    """
    parser = RedactionPromptParser()
    return parser.parse(prompt)


def get_redaction_suggestions() -> List[str]:
    """Get example redaction prompts for UI guidance."""
    return [
        "Redact all personal information",
        "Don't redact my name, only SSN and phone numbers", 
        "Hide email addresses and credit card numbers",
        "Remove all sensitive data except dates",
        "Only redact social security numbers",
        "Keep names and addresses, hide everything else",
        "Redact financial information only",
    ]


# Example usage for testing
if __name__ == "__main__":
    # Test various prompts
    test_prompts = [
        "redact all personal information",
        "don't redact my name, only SSN and phone numbers", 
        "hide email addresses and credit cards",
        "remove all sensitive data except dates",
        "only redact social security numbers",
        "keep names but hide email",
    ]
    
    parser = RedactionPromptParser()
    for prompt in test_prompts:
        config = parser.parse(prompt)
        print(f"Prompt: '{prompt}'")
        print(f"Config: {config}")
        print()