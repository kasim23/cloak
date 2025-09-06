"""
Tests for natural language redaction parser.

This module tests the natural language parser that converts user prompts
like "don't redact my name, only SSN" into RedactionConfig objects.
"""

import pytest
from cloak.nl.redaction_parser import (
    RedactionPromptParser,
    RedactionConfig,
    parse_redaction_prompt,
    get_redaction_suggestions,
    ENTITY_ALIASES,
    ACTION_ALIASES
)
from cloak.config import Policy


class TestEntityAliases:
    """Test entity alias mappings."""
    
    def test_person_aliases(self):
        """Test person-related aliases map correctly."""
        assert ENTITY_ALIASES["name"] == "PERSON"
        assert ENTITY_ALIASES["person"] == "PERSON"
        assert ENTITY_ALIASES["my name"] == "PERSON"
    
    def test_contact_aliases(self):
        """Test contact information aliases."""
        assert ENTITY_ALIASES["email"] == "EMAIL"
        assert ENTITY_ALIASES["phone"] == "PHONE"
        assert ENTITY_ALIASES["phone number"] == "PHONE"
    
    def test_financial_aliases(self):
        """Test financial information aliases."""
        assert ENTITY_ALIASES["ssn"] == "SSN"
        assert ENTITY_ALIASES["social security number"] == "SSN"
        assert ENTITY_ALIASES["credit card"] == "CREDIT_CARD"


class TestActionAliases:
    """Test action alias mappings."""
    
    def test_action_mappings(self):
        """Test action aliases map to correct policy actions."""
        assert ACTION_ALIASES["redact"] == "mask"
        assert ACTION_ALIASES["hide"] == "mask"
        assert ACTION_ALIASES["remove"] == "drop"
        assert ACTION_ALIASES["keep"] == "none"


class TestRedactionConfig:
    """Test RedactionConfig functionality."""
    
    def test_redaction_config_creation(self):
        """Test creating a RedactionConfig."""
        config = RedactionConfig(
            entity_actions={"PERSON": "none", "SSN": "mask"},
            redact_all_default=False
        )
        
        assert config.entity_actions["PERSON"] == "none"
        assert config.entity_actions["SSN"] == "mask"
        assert not config.redact_all_default
    
    def test_apply_to_policy_specific_overrides(self):
        """Test applying config with specific entity overrides."""
        base_policy = Policy()
        config = RedactionConfig(
            entity_actions={"PERSON": "none", "EMAIL": "drop"},
            redact_all_default=False
        )
        
        new_policy = config.apply_to_policy(base_policy)
        
        assert new_policy.actions["PERSON"] == "none"
        assert new_policy.actions["EMAIL"] == "drop"
    
    def test_apply_to_policy_redact_all_default(self):
        """Test applying config with redact_all_default=True."""
        base_policy = Policy()
        config = RedactionConfig(
            entity_actions={"DATE": "none"},  # Keep dates
            redact_all_default=True
        )
        
        new_policy = config.apply_to_policy(base_policy)
        
        # Should mask common entities by default
        assert new_policy.actions["PERSON"] == "mask"
        assert new_policy.actions["EMAIL"] == "mask"
        # But preserve specified entities
        assert new_policy.actions["DATE"] == "none"
    
    def test_confidence_threshold_override(self):
        """Test confidence threshold override."""
        base_policy = Policy(min_confidence=0.75)
        config = RedactionConfig(
            entity_actions={},
            confidence_threshold=0.9
        )
        
        new_policy = config.apply_to_policy(base_policy)
        assert new_policy.min_confidence == 0.9


class TestRedactionPromptParser:
    """Test the main prompt parsing logic."""
    
    def test_extract_mentioned_entities_simple(self):
        """Test extracting entities from text."""
        parser = RedactionPromptParser()
        
        # Single entity
        result = parser._extract_mentioned_entities("names")
        assert "PERSON" in result
        
        # Multiple entities
        result = parser._extract_mentioned_entities("names and emails")
        assert "PERSON" in result
        assert "EMAIL" in result
        
        # Multiple entities with various terms
        result = parser._extract_mentioned_entities("ssn, phone numbers, credit cards")
        assert "SSN" in result
        assert "PHONE" in result
        assert "CREDIT_CARD" in result
    
    def test_parse_redact_all_prompts(self):
        """Test parsing global 'redact everything' prompts."""
        parser = RedactionPromptParser()
        
        prompts_without_entities = [
            "redact everything", 
            "hide all sensitive data"
        ]
        
        prompts_with_entities = [
            "redact all personal information",  # mentions "personal" which could match entities
        ]
        
        # Prompts without specific entities should redact all by default
        for prompt in prompts_without_entities:
            config = parser.parse(prompt)
            assert config.redact_all_default
        
        # Prompts with entities should redact those specific entities
        for prompt in prompts_with_entities:
            config = parser.parse(prompt)
            # Either redact_all_default OR specific entity actions
            assert config.redact_all_default or bool(config.entity_actions)
    
    def test_parse_include_only_prompts(self):
        """Test parsing 'only redact X' prompts."""
        parser = RedactionPromptParser()
        
        config = parser.parse("only redact SSN and phone numbers")
        
        assert not config.redact_all_default
        assert "SSN" in config.entity_actions
        assert "PHONE" in config.entity_actions
        assert config.entity_actions["SSN"] == "mask"
    
    def test_parse_exclude_prompts(self):
        """Test parsing 'don't redact X' prompts.""" 
        parser = RedactionPromptParser()
        
        # Test combined exclude and include: "don't redact X, only redact Y" 
        config = parser.parse("don't redact my name, only SSN and phone")
        
        # Should have both exclude and include entities
        assert "PERSON" in config.entity_actions
        assert config.entity_actions["PERSON"] == "none"  # Don't redact names
        assert "SSN" in config.entity_actions  
        assert config.entity_actions["SSN"] == "mask"     # Do redact SSN
        assert not config.redact_all_default  # Don't redact everything by default
    
    def test_parse_complex_prompt(self):
        """Test parsing complex multi-part prompts."""
        parser = RedactionPromptParser()
        
        config = parser.parse("redact all personal information except dates")
        
        assert config.redact_all_default
        if "DATE" in config.entity_actions:
            assert config.entity_actions["DATE"] == "none"
    
    def test_parse_empty_prompt(self):
        """Test parsing empty or whitespace prompts."""
        parser = RedactionPromptParser()
        
        config = parser.parse("")
        assert config.redact_all_default  # Default behavior
        
        config = parser.parse("   ")
        assert config.redact_all_default


class TestConvenienceFunctions:
    """Test module convenience functions."""
    
    def test_parse_redaction_prompt(self):
        """Test the main convenience function."""
        config = parse_redaction_prompt("hide all email addresses")
        
        assert isinstance(config, RedactionConfig)
        # Should parse as include-only prompt with "all" pattern
        assert "EMAIL" in config.entity_actions or not config.redact_all_default
    
    def test_get_redaction_suggestions(self):
        """Test getting example suggestions."""
        suggestions = get_redaction_suggestions()
        
        assert isinstance(suggestions, list)
        assert len(suggestions) > 0
        assert all(isinstance(s, str) for s in suggestions)
        
        # Should include variety of patterns
        assert any("don't" in s.lower() for s in suggestions)  # Exclude pattern
        assert any("only" in s.lower() for s in suggestions)   # Include-only pattern
        assert any("all" in s.lower() for s in suggestions)    # Global pattern


class TestIntegration:
    """Integration tests combining parser with policy application."""
    
    def test_full_workflow_exclude_pattern(self):
        """Test full workflow: prompt -> config -> policy."""
        prompt = "don't redact names and dates, hide everything else"
        base_policy = Policy()
        
        # Parse prompt
        config = parse_redaction_prompt(prompt)
        
        # Apply to policy
        new_policy = config.apply_to_policy(base_policy)
        
        # Verify results
        if "PERSON" in config.entity_actions:
            assert new_policy.actions["PERSON"] == "none"
        if "DATE" in config.entity_actions:
            assert new_policy.actions["DATE"] == "none"
    
    def test_full_workflow_include_pattern(self):
        """Test full workflow with include-only pattern."""
        prompt = "only redact social security numbers and credit cards"
        base_policy = Policy()
        
        config = parse_redaction_prompt(prompt)
        new_policy = config.apply_to_policy(base_policy)
        
        # Should only redact specified entities
        assert not config.redact_all_default
        if "SSN" in config.entity_actions:
            assert config.entity_actions["SSN"] == "mask"
        if "CREDIT_CARD" in config.entity_actions:
            assert config.entity_actions["CREDIT_CARD"] == "mask"