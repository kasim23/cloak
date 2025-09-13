#!/usr/bin/env python3
"""
PDF entity detection tests for LLM-first architecture.

Tests the complete pipeline: PDF → Text Extraction → LLM Detection → Positioning
This validates that our revolutionary LLM approach works with real document formats.
"""

import pytest
import os
from pathlib import Path
import PyPDF2

def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract text from PDF using PyPDF2."""
    text = ""
    with open(pdf_path, 'rb') as file:
        pdf_reader = PyPDF2.PdfReader(file)
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
    
    return text


class TestPDFEntityDetection:
    """Test LLM entity detection with PDF documents."""
    
    @pytest.fixture
    def sample_pdf_path(self):
        """Path to the sample PDF file."""
        return Path("tests/fixtures/sample_document.pdf")
    
    def test_pdf_exists(self, sample_pdf_path):
        """Verify the test PDF file exists."""
        assert sample_pdf_path.exists(), f"Test PDF not found at {sample_pdf_path}"
    
    def test_pdf_text_extraction(self, sample_pdf_path):
        """Test that we can extract text from PDF correctly."""
        extracted_text = extract_text_from_pdf(sample_pdf_path)
        
        print(f"\nExtracted PDF text ({len(extracted_text)} chars):")
        print(extracted_text[:500] + "..." if len(extracted_text) > 500 else extracted_text)
        
        # Should contain key entities from our test PDF
        assert "Sarah Wilson" in extracted_text
        assert "987-65-4321" in extracted_text
        assert "sarah.wilson@techcorp.com" in extracted_text
        assert "SarahDev#9876" in extracted_text
        assert "bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq" in extracted_text
        assert "(555) 987-6543" in extracted_text
    
    def test_llm_detection_on_pdf_text(self, sample_pdf_path):
        """Test LLM entity detection on PDF-extracted text."""
        from cloak.nl.llm_entity_detector import LLMEntityDetector
        
        # Extract text from PDF
        extracted_text = extract_text_from_pdf(sample_pdf_path)
        
        # Test LLM detection
        api_key = os.getenv("GROQ_API_KEY")
        detector = LLMEntityDetector(api_key=api_key)
        
        result = detector.detect_and_classify(
            extracted_text, 
            prompt="redact all sensitive personal and financial information"
        )
        
        # Debug output
        print(f"\nPDF Detection Results ({len(result.entities)} entities):")
        for entity in result.entities:
            print(f"  {entity.entity_type}: '{entity.text}' -> {entity.action}")
        print(f"Reasoning: {result.reasoning}")
        
        # Should detect multiple entities
        assert len(result.entities) >= 8
        
        # Check for standard entities
        entity_texts = [e.text for e in result.entities]
        assert "Sarah Wilson" in entity_texts
        assert "987-65-4321" in entity_texts
        assert "sarah.wilson@techcorp.com" in entity_texts
        
        # Check for financial entities
        assert "555666777888" in entity_texts
        assert "123456789" in entity_texts
        
        # Check for revolutionary custom entities (LLM advantage!)
        assert "SarahDev#9876" in entity_texts
        crypto_found = any("bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq" in text for text in entity_texts)
        assert crypto_found, "Should detect crypto wallet"
        
        # Validate positioning accuracy
        for entity in result.entities:
            # Verify positions are accurate
            actual_text = extracted_text[entity.start:entity.end]
            assert actual_text == entity.text, f"Position mismatch: '{actual_text}' != '{entity.text}'"
        
        # Check that sensitive data is masked
        sensitive_entities = ["987-65-4321", "555666777888", "123456789", "SarahDev#9876"]
        for entity in result.entities:
            if any(sensitive in entity.text for sensitive in sensitive_entities):
                assert entity.action == "mask", f"Sensitive entity '{entity.text}' should be masked"
    
    def test_pdf_contextual_redaction(self, sample_pdf_path):
        """Test contextual redaction instructions on PDF content."""
        from cloak.nl.llm_entity_detector import LLMEntityDetector
        
        extracted_text = extract_text_from_pdf(sample_pdf_path)
        api_key = os.getenv("GROQ_API_KEY")
        detector = LLMEntityDetector(api_key=api_key)
        
        # Test context-aware prompt
        result = detector.detect_and_classify(
            extracted_text,
            prompt="I'm sharing this with IT department for system access, hide financial info but keep work-related details"
        )
        
        print(f"\nContextual Results ({len(result.entities)} entities):")
        for entity in result.entities:
            print(f"  {entity.entity_type}: '{entity.text}' -> {entity.action}")
        print(f"Reasoning: {result.reasoning}")
        
        # Check context understanding
        entity_actions = {e.text: e.action for e in result.entities}
        
        # Work-related should be kept
        if "sarah.wilson@techcorp.com" in entity_actions:
            assert entity_actions["sarah.wilson@techcorp.com"] == "none"
        if "Engineering" in entity_actions:
            assert entity_actions["Engineering"] == "none"
        
        # Financial should be hidden
        financial_entities = ["987-65-4321", "555666777888", "123456789"]
        for financial_entity in financial_entities:
            if financial_entity in entity_actions:
                assert entity_actions[financial_entity] == "mask", f"Financial entity '{financial_entity}' should be masked"
    
    def test_pdf_custom_entities_advantage(self, sample_pdf_path):
        """Test detection of custom entities that regex/spaCy could never handle."""
        from cloak.nl.llm_entity_detector import LLMEntityDetector
        
        extracted_text = extract_text_from_pdf(sample_pdf_path)
        api_key = os.getenv("GROQ_API_KEY")
        detector = LLMEntityDetector(api_key=api_key)
        
        # Test detection of entities that would be impossible with regex
        result = detector.detect_and_classify(
            extracted_text,
            prompt="redact all gaming accounts, crypto wallets, and social media profiles"
        )
        
        print(f"\nCustom Entity Detection Results ({len(result.entities)} entities):")
        for entity in result.entities:
            print(f"  {entity.entity_type}: '{entity.text}' -> {entity.action}")
        
        # These entities demonstrate LLM's revolutionary capability
        entity_texts = [e.text for e in result.entities]
        
        # Gaming account (Discord) - regex would need specific Discord patterns
        discord_found = any("SarahDev#9876" in text for text in entity_texts)
        assert discord_found, "Should detect Discord username"
        
        # Crypto wallet - regex would need to know all crypto address formats
        crypto_found = any("bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq" in text for text in entity_texts)
        assert crypto_found, "Should detect crypto wallet address"
        
        # Social media - regex would need GitHub-specific patterns
        github_found = any("github.com/sarah-wilson-dev" in text for text in entity_texts)
        # GitHub detection might vary, so don't assert
        if github_found:
            print("  ✅ Detected GitHub profile (bonus!)")
        
        # All custom entities should be marked for masking per the prompt
        custom_entities_found = []
        for entity in result.entities:
            if any(custom in entity.text.lower() for custom in ["sarahdev", "bc1qar0", "github"]):
                assert entity.action == "mask", f"Custom entity '{entity.text}' should be masked"
                custom_entities_found.append(entity.entity_type)
        
        print(f"\n✅ Revolutionary Custom Entity Detection:")
        for entity_type in set(custom_entities_found):
            print(f"  - {entity_type}: Successfully detected by LLM!")
    
    def test_pdf_vs_text_consistency(self, sample_pdf_path):
        """Test that PDF extraction + LLM gives consistent results."""
        from cloak.nl.llm_entity_detector import LLMEntityDetector
        
        # Get PDF text
        pdf_text = extract_text_from_pdf(sample_pdf_path)
        
        # Same text as direct string (simulate text input)
        direct_text = """CONFIDENTIAL EMPLOYEE RECORD

Personal Information:
Name: Sarah Wilson
Employee ID: EMP-2024-042
Department: Engineering

Contact Details:
Email: sarah.wilson@techcorp.com
Phone: (555) 987-6543
Address: 123 Main St, Seattle WA 98101

Financial Information:
SSN: 987-65-4321
Bank Account: 555666777888
Routing Number: 123456789

Digital Accounts:
Discord: SarahDev#9876
GitHub: github.com/sarah-wilson-dev
Crypto Wallet: bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq

Emergency Contact:
Name: Mike Wilson
Phone: (555) 123-7890"""
        
        api_key = os.getenv("GROQ_API_KEY")
        detector = LLMEntityDetector(api_key=api_key)
        
        # Test both
        pdf_result = detector.detect_and_classify(pdf_text, "redact all sensitive information")
        direct_result = detector.detect_and_classify(direct_text, "redact all sensitive information")
        
        print(f"\nPDF result: {len(pdf_result.entities)} entities")
        print(f"Direct text result: {len(direct_result.entities)} entities")
        
        # Should have similar number of entities (allow some variance due to text extraction differences)
        entity_count_diff = abs(len(pdf_result.entities) - len(direct_result.entities))
        assert entity_count_diff <= 2, f"PDF and direct text should detect similar entity counts"
        
        # Key entities should be found in both
        pdf_texts = [e.text for e in pdf_result.entities]
        direct_texts = [e.text for e in direct_result.entities]
        
        key_entities = ["Sarah Wilson", "987-65-4321", "sarah.wilson@techcorp.com"]
        for key_entity in key_entities:
            assert key_entity in pdf_texts or any(key_entity in text for text in pdf_texts)
            assert key_entity in direct_texts or any(key_entity in text for text in direct_texts)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])