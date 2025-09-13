"""
LLM-first entity detection and action assignment.

This revolutionary approach replaces the complex regex/spaCy detection pipeline
with a single LLM call that both detects entities AND assigns actions based on
natural language prompts.

Key advantages:
- Unlimited entity types (crypto wallets, Discord usernames, custom IDs)
- Context awareness ("I'm applying for a job, hide personal info") 
- Natural language control vs rigid pattern matching
- Simpler architecture: Text + Prompt → LLM → [Entities + Actions]
"""

from __future__ import annotations

import json
import logging
import os
import re
import requests
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Groq API configuration
GROQ_API_BASE = "https://api.groq.com/openai/v1"
GROQ_MODEL = "llama-3.3-70b-versatile"  # Latest Llama model on Groq

@dataclass
class DetectedEntity:
    """Entity found by LLM with position and action."""
    start: int
    end: int
    text: str
    entity_type: str
    action: str  # mask, none
    confidence: float

@dataclass
class LLMDetectionResult:
    """Complete result from LLM entity detection."""
    entities: List[DetectedEntity]
    reasoning: str
    confidence: str  # high, medium, low
    cost_estimate: float = 0.0
    success: bool = True


class LLMEntityDetector:
    """
    LLM-powered entity detection and action assignment.
    
    Replaces the entire regex/spaCy detection pipeline with a single intelligent
    LLM call that understands context and can detect ANY entity type described
    in natural language.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize detector with Groq API key."""
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        self.session = requests.Session()
        
        if self.api_key:
            self.session.headers.update({
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            })
    
    def detect_and_classify(self, text: str, prompt: str = "") -> LLMDetectionResult:
        """
        Detect entities and assign actions using LLM.
        
        This is the revolutionary single call that replaces the entire
        regex/spaCy detection pipeline.
        
        Args:
            text: Document text to analyze
            prompt: User's natural language instruction
            
        Returns:
            LLMDetectionResult with entities, positions, and actions
        """
        if not self.api_key:
            logger.warning("No Groq API key - using fallback")
            return self._fallback_result("No API key provided")
        
        if not text or not text.strip():
            return LLMDetectionResult(
                entities=[],
                reasoning="Empty document",
                confidence="high"
            )
        
        try:
            # Build the system prompt for entity detection + action assignment
            system_prompt = self._build_system_prompt()
            user_prompt = self._build_user_prompt(text, prompt)
            
            # Make single LLM call for complete analysis
            response = self._call_groq_api(system_prompt, user_prompt)
            
            # Parse structured response
            return self._parse_llm_response(response, text)
            
        except Exception as e:
            logger.error(f"LLM entity detection failed: {e}")
            return self._fallback_result(f"API error: {str(e)}")
    
    def get_cost_estimate(self, text: str, prompt: str = "") -> float:
        """Estimate cost for processing this text."""
        # Rough estimation: ~1 token per 4 characters
        input_tokens = len(text + prompt) // 4
        # Add system prompt tokens (~500)
        total_tokens = input_tokens + 500
        
        # Groq pricing is very cheap - approximately $0.0001 per 1K tokens
        return (total_tokens / 1000) * 0.0001
    
    def _build_system_prompt(self) -> str:
        """Build system prompt for entity detection and action assignment."""
        return """You are an expert at analyzing documents to detect sensitive entities and determining appropriate redaction actions based on user instructions.

Your task: Analyze the provided document text and user instruction to:
1. Identify ALL sensitive entities in the text (any personally identifiable information, credentials, etc.)
2. Determine the appropriate action for each entity based on the user's instruction
3. Return precise character positions for text replacement

Entity types you can detect (not limited to these):
- PERSON: Names of people
- ORG: Organization/company names
- LOC: Locations and addresses  
- EMAIL: Email addresses
- PHONE: Phone numbers
- SSN: Social security numbers
- CREDIT_CARD: Credit card numbers
- ACCOUNT: Bank account numbers, routing numbers
- CRYPTO: Cryptocurrency wallets, addresses
- GAMING: Discord usernames, Steam IDs, gaming accounts
- SOCIAL: Social media handles, profiles
- IP: IP addresses
- SECRET: API keys, passwords, tokens
- DATE: Dates (if sensitive)
- CUSTOM: Any other sensitive identifier the user mentions

Available actions:
- mask: Replace with black boxes/redaction (████)
- none: Keep as-is (don't redact)

Default behavior (if user gives no specific instruction):
- Redact most sensitive entities (SSN, credit cards, secrets, accounts)
- Keep less sensitive entities (names, organizations, general dates)

Context understanding:
- "I'm applying for a job" → Keep professional info (name, company), hide personal identifiers
- "Sharing with HR" → Keep work-related info, hide financial data  
- "Public posting" → Hide most personal info, keep generic information
- "Financial review" → Keep financial info, hide other personal data

Response format (JSON only, no explanation):
{
  "entities": [
    {
      "text": "John Smith",
      "type": "PERSON", 
      "action": "none",
      "confidence": 0.95
    },
    {
      "text": "123-45-6789",
      "type": "SSN",
      "action": "mask", 
      "confidence": 0.99
    }
  ],
  "reasoning": "User wants to keep names but hide sensitive identifiers",
  "confidence": "high"
}

IMPORTANT: Focus on accurately identifying entity text content and types. Character positions will be calculated automatically."""
    
    def _build_user_prompt(self, text: str, user_instruction: str) -> str:
        """Build user prompt with document text and instruction."""
        instruction_text = user_instruction.strip() if user_instruction else "Use default redaction settings"
        
        return f"""Document text to analyze:
---
{text}
---

User instruction: "{instruction_text}"

Analyze this document and return the JSON response with all sensitive entities found."""
    
    def _call_groq_api(self, system_prompt: str, user_prompt: str) -> str:
        """Make API call to Groq Llama 3.3-70B."""
        url = f"{GROQ_API_BASE}/chat/completions"
        
        payload = {
            "model": GROQ_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.1,  # Low temperature for consistent analysis
            "max_tokens": 2000,  # Enough for entity lists
            "response_format": {"type": "json_object"}  # Force JSON response
        }
        
        logger.info(f"Making Groq API call for entity detection")
        response = self.session.post(url, json=payload, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        
        logger.info(f"Groq API response received, content length: {len(content)}")
        logger.debug(f"Raw LLM response: {content}")
        return content
    
    def _parse_llm_response(self, response_content: str, original_text: str) -> LLMDetectionResult:
        """Parse LLM JSON response into DetectedEntity objects (two-phase approach)."""
        try:
            data = json.loads(response_content)
            
            entities = []
            for entity_data in data.get("entities", []):
                entity_text = entity_data["text"]
                entity_type = entity_data.get("type", "OTHER")
                action = entity_data.get("action", "mask")
                confidence = float(entity_data.get("confidence", 0.8))
                
                # Phase 2: Find accurate positions using Python string search
                positions = self._find_entity_positions(original_text, entity_text)
                
                # Create DetectedEntity for each occurrence
                for start, end in positions:
                    entities.append(DetectedEntity(
                        start=start,
                        end=end,
                        text=original_text[start:end],
                        entity_type=entity_type,
                        action=action,
                        confidence=confidence
                    ))
            
            return LLMDetectionResult(
                entities=entities,
                reasoning=data.get("reasoning", ""),
                confidence=data.get("confidence", "medium"),
                success=True
            )
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"Failed to parse LLM response: {e}")
            logger.error(f"Response content: {response_content}")
            return self._fallback_result(f"Parse error: {str(e)}")
    
    def _find_entity_positions(self, text: str, entity_text: str) -> List[Tuple[int, int]]:
        """
        Find all accurate positions of entity text in the original text.
        
        This is Phase 2 of the two-phase approach - Python handles precise 
        positioning while LLM handles semantic understanding.
        """
        positions = []
        entity_text_clean = entity_text.strip()
        
        # Method 1: Exact string match (most common case)
        start_pos = 0
        while True:
            pos = text.find(entity_text_clean, start_pos)
            if pos == -1:
                break
            positions.append((pos, pos + len(entity_text_clean)))
            start_pos = pos + 1
        
        # Method 2: Handle minor whitespace variations if exact match fails
        if not positions:
            # Try with normalized whitespace
            normalized_entity = re.sub(r'\s+', r'\\s+', re.escape(entity_text_clean))
            pattern = re.compile(normalized_entity, re.IGNORECASE)
            
            for match in pattern.finditer(text):
                positions.append((match.start(), match.end()))
        
        # Method 3: Handle partial matches for complex entities (like URLs)
        if not positions and len(entity_text_clean) > 10:
            # For long entities, try to find substring matches
            # This helps with entities like long crypto addresses or URLs
            words = entity_text_clean.split()
            if len(words) > 1:
                # Try to find the first and last words, then get the span between
                first_word = words[0]
                last_word = words[-1]
                
                first_pos = text.find(first_word)
                last_pos = text.find(last_word, first_pos)
                
                if first_pos != -1 and last_pos != -1:
                    start = first_pos
                    end = last_pos + len(last_word)
                    # Validate that this span contains most of our entity
                    span_text = text[start:end]
                    if entity_text_clean[:10] in span_text and entity_text_clean[-10:] in span_text:
                        positions.append((start, end))
        
        if not positions:
            logger.warning(f"Could not find entity '{entity_text_clean}' in text")
        
        return positions
    
    def _fallback_result(self, reason: str) -> LLMDetectionResult:
        """Return fallback result when LLM fails."""
        return LLMDetectionResult(
            entities=[],
            reasoning=f"LLM unavailable: {reason}",
            confidence="low",
            success=False
        )


# Backward compatibility functions
def detect_entities_with_llm(text: str, prompt: str = "", api_key: Optional[str] = None) -> LLMDetectionResult:
    """
    Convenience function for LLM entity detection.
    
    Args:
        text: Document text to analyze
        prompt: Natural language instruction for redaction
        api_key: Optional Groq API key (uses env var if None)
        
    Returns:
        LLMDetectionResult with entities and actions
    """
    detector = LLMEntityDetector(api_key=api_key)
    return detector.detect_and_classify(text, prompt)


# Example usage and testing
if __name__ == "__main__":
    # Test the detector with sample data
    test_text = """
    Personal Information:
    Name: Alice Johnson
    SSN: 555-44-3333
    Email: alice.johnson@company.com
    Account: 987654321
    Discord: AliceGamer#1234
    Crypto Wallet: bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh
    """
    
    detector = LLMEntityDetector()
    
    print("🧪 Testing LLM Entity Detector")
    print("=" * 50)
    
    # Test 1: Default behavior
    print("Test 1: Default redaction")
    result = detector.detect_and_classify(test_text)
    print(f"Found {len(result.entities)} entities")
    for entity in result.entities:
        print(f"  {entity.entity_type}: '{entity.text}' -> {entity.action}")
    print(f"Reasoning: {result.reasoning}")
    print()
    
    # Test 2: Selective prompt
    print("Test 2: Selective prompt")
    result = detector.detect_and_classify(test_text, "keep name and email, hide everything else")
    print(f"Found {len(result.entities)} entities")
    for entity in result.entities:
        print(f"  {entity.entity_type}: '{entity.text}' -> {entity.action}")
    print(f"Reasoning: {result.reasoning}")
    print()
    
    # Test 3: Context-aware prompt
    print("Test 3: Context-aware prompt")
    result = detector.detect_and_classify(test_text, "I'm applying for a job, hide personal identifiers but keep professional info")
    print(f"Found {len(result.entities)} entities")
    for entity in result.entities:
        print(f"  {entity.entity_type}: '{entity.text}' -> {entity.action}")
    print(f"Reasoning: {result.reasoning}")
    print()
    
    print("✅ Manual testing complete")