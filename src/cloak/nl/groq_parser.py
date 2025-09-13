"""
Groq LLM-based parser for redaction customization prompts.

This module replaces the keyword-based parser with Groq API calls using
Llama 3.1-70B for superior natural language understanding.

Features:
- Uses Groq's free tier (14,400 tokens/day)
- Graceful fallback to default redaction when API unavailable
- Structured JSON response parsing for entity-action mapping
- Error handling and logging for monitoring
"""

from __future__ import annotations

import json
import logging
import requests
from dataclasses import dataclass
from typing import Dict, List, Optional
from ..config import Policy

logger = logging.getLogger(__name__)

# Groq API configuration
GROQ_API_BASE = "https://api.groq.com/openai/v1"
GROQ_MODEL = "llama-3.3-70b-versatile"  # Llama 3.3-70B versatile (current available model)

@dataclass
class RedactionConfig:
    """Configuration for customized redaction based on LLM prompt parsing."""
    
    # Entity-specific actions (overrides defaults)
    entity_actions: Dict[str, str]
    
    # Global settings
    redact_all_default: bool = True
    
    # Confidence and metadata
    confidence: str = "high"  # high, medium, low
    reasoning: str = ""
    
    def apply_to_policy(self, base_policy: Policy) -> Policy:
        """Apply this redaction config to a base policy, returning a new policy."""
        new_actions = base_policy.actions.copy()
        
        # Apply entity-specific overrides (MVP: simplified to mask/none only)
        for entity, action in self.entity_actions.items():
            if entity in new_actions:  # Only update valid entity types
                # For MVP, convert all redaction actions to mask (black boxes)
                if action != "none":
                    new_actions[entity] = "mask"
                else:
                    new_actions[entity] = "none"
            
        # If user wants to redact everything by default, set unspecified entities to mask
        if self.redact_all_default:
            for entity in ["PERSON", "ORG", "LOC", "EMAIL", "PHONE", "SSN", "CREDIT_CARD", "SECRET"]:
                if entity not in self.entity_actions:
                    new_actions[entity] = "mask"
        
        return Policy(
            actions=new_actions,
            min_confidence=base_policy.min_confidence
        )


class GroqLLMParser:
    """LLM-based parser using Groq API for natural language redaction customization."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize Groq parser with API key."""
        self.api_key = api_key
        self.session = requests.Session()
        if api_key:
            self.session.headers.update({"Authorization": f"Bearer {api_key}"})
    
    def parse(self, prompt: str) -> RedactionConfig:
        """
        Parse a natural language prompt into a RedactionConfig using Groq LLM.
        
        Args:
            prompt: Natural language redaction instruction
            
        Returns:
            RedactionConfig with entity-action mappings
            
        Raises:
            GroqAPIError: When API call fails (should be caught for fallback)
        """
        if not self.api_key:
            logger.warning("No Groq API key provided, falling back to default")
            return self._fallback_config()
        
        try:
            # Construct structured prompt for the LLM
            system_prompt = self._build_system_prompt()
            user_prompt = f"User instruction: '{prompt}'"
            
            # Call Groq API
            response = self._call_groq_api(system_prompt, user_prompt)
            
            # Parse LLM response
            return self._parse_llm_response(response, prompt)
            
        except Exception as e:
            logger.error(f"Groq API error: {e}")
            return self._fallback_config()
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt that instructs the LLM how to parse redaction requests."""
        return """You are an expert at parsing natural language instructions for document redaction.

Your task: Convert user instructions into specific entity-action mappings for document redaction.

Available entity types:
- PERSON: Names of people
- ORG: Organization/company names  
- LOC: Locations and addresses
- EMAIL: Email addresses
- PHONE: Phone numbers
- SSN: Social security numbers
- CREDIT_CARD: Credit card numbers
- ACCOUNT: Bank account numbers, routing numbers
- IP: IP addresses
- SECRET: API keys, passwords, tokens
- DATE: Dates
- OTHER: Other sensitive information

Available actions (MVP - simplified):
- mask: Replace with ████ (black boxes) 
- none: Keep as-is (don't redact)

Note: Enterprise features (pseudonymize, hash, drop) available in CLI but simplified for web MVP

Response format (JSON only):
{
  "entity_actions": {"PERSON": "none", "ACCOUNT": "mask"},
  "redact_all_default": false,
  "confidence": "high",
  "reasoning": "User wants to keep names but hide financial information"
}

Examples:
- "don't redact my name, only account numbers" → {"PERSON": "none", "ACCOUNT": "mask"}, redact_all_default: false
- "redact everything except dates" → {"DATE": "none"}, redact_all_default: true  
- "hide financial info but keep company names" → {"ACCOUNT": "mask", "CREDIT_CARD": "mask", "SSN": "mask", "ORG": "none"}, redact_all_default: false

Respond with JSON only, no explanations."""

    def _call_groq_api(self, system_prompt: str, user_prompt: str) -> str:
        """Make API call to Groq and return response text."""
        url = f"{GROQ_API_BASE}/chat/completions"
        
        payload = {
            "model": GROQ_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.1,  # Low temperature for consistent parsing
            "max_tokens": 500,
            "response_format": {"type": "json_object"}  # Force JSON response
        }
        
        response = self.session.post(url, json=payload, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        return data["choices"][0]["message"]["content"]
    
    def _parse_llm_response(self, response_text: str, original_prompt: str) -> RedactionConfig:
        """Parse the LLM JSON response into a RedactionConfig."""
        try:
            data = json.loads(response_text)
            
            return RedactionConfig(
                entity_actions=data.get("entity_actions", {}),
                redact_all_default=data.get("redact_all_default", True),
                confidence=data.get("confidence", "medium"),
                reasoning=data.get("reasoning", "")
            )
            
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Failed to parse LLM response: {e}")
            return self._fallback_config()
    
    def _fallback_config(self) -> RedactionConfig:
        """Return safe fallback configuration when LLM fails."""
        return RedactionConfig(
            entity_actions={},
            redact_all_default=True,  # Safe default: redact everything
            confidence="low",
            reasoning="LLM unavailable - using safe default"
        )


# Backwards compatibility - keep the same interface
def parse_redaction_prompt(prompt: str, groq_api_key: Optional[str] = None) -> RedactionConfig:
    """
    Convenience function to parse a redaction prompt using Groq LLM.
    
    Args:
        prompt: Natural language redaction instruction
        groq_api_key: Optional Groq API key (fallback to default if None)
        
    Returns:
        RedactionConfig that can be applied to a Policy
        
    Examples:
        >>> config = parse_redaction_prompt("don't redact my name, only SSN")
        >>> policy = config.apply_to_policy(base_policy)
    """
    parser = GroqLLMParser(groq_api_key)
    return parser.parse(prompt)


def get_redaction_suggestions() -> List[str]:
    """Get example redaction prompts for UI guidance (enhanced for LLM)."""
    return [
        "Don't redact names, only financial information",
        "Hide all personal info but keep company names", 
        "Redact everything except dates and locations",
        "Only hide social security numbers and credit cards",
        "Keep names and emails, redact everything else",
        "Hide financial data but preserve business information",
        "Redact contact info only (phones and emails)",
    ]


# Example usage for testing
if __name__ == "__main__":
    # Test various prompts with mock API key
    test_prompts = [
        "don't redact my name, only account numbers and routing numbers",
        "hide all financial information but keep company names", 
        "redact everything except dates",
        "only hide social security numbers",
        "keep names but hide all contact information",
    ]
    
    parser = GroqLLMParser("mock-api-key")  # Will fallback for testing
    for prompt in test_prompts:
        config = parser.parse(prompt)
        print(f"Prompt: '{prompt}'")
        print(f"Config: {config}")
        print()