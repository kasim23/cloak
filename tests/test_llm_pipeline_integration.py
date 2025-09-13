#!/usr/bin/env python3
"""
Integration tests for the simplified LLM-first pipeline.

Tests the complete flow: Text → LLM Entity Detection → Visual Redaction → Output
This replaces the complex regex/spaCy pipeline with a single LLM-driven approach.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

class TestLLMPipelineIntegration:
    """Test the complete LLM-first pipeline integration."""
    
    @pytest.fixture 
    def sample_document(self):
        """Create a temporary document for testing."""
        content = """
        Personal Data Sheet
        
        Employee: Sarah Johnson  
        Department: Engineering
        Employee ID: EMP-2024-001
        SSN: 987-65-4321
        Phone: (555) 987-6543
        Email: sarah.johnson@techcorp.com
        Bank Account: 123456789012
        Routing: 987654321
        Emergency Contact: Mike Johnson (555) 123-4567
        """
        
        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
        temp_file.write(content)
        temp_file.close()
        
        yield Path(temp_file.name)
        
        # Cleanup
        Path(temp_file.name).unlink()
    
    def test_pipeline_scan_mode(self, sample_document):
        """Test pipeline in scan mode - detection only, no modification."""
        # This will fail initially until we implement the new pipeline
        from cloak.engine.pipeline import Pipeline
        from cloak.config import CloakConfig
        
        config = CloakConfig()
        pipeline = Pipeline(config)
        
        # Scan with custom prompt
        result = pipeline.scan_file(
            sample_document, 
            prompt="identify all personal identifiers but ignore company information"
        )
        
        # Should detect multiple entities
        assert len(result.entities) >= 6
        
        # Should classify entities correctly based on prompt
        entity_texts = [e.text for e in result.entities]
        assert "Sarah Johnson" in entity_texts
        assert "987-65-4321" in entity_texts  # SSN
        assert "sarah.johnson@techcorp.com" in entity_texts
        assert "123456789012" in entity_texts  # Bank account
        
        # Should understand context - might keep "Engineering" as company info
        # This is where LLM shows superiority over regex patterns
    
    def test_pipeline_redact_mode(self, sample_document):
        """Test pipeline in redaction mode - creates redacted output."""
        from cloak.engine.pipeline import Pipeline
        from cloak.config import CloakConfig
        
        config = CloakConfig()
        pipeline = Pipeline(config)
        
        # Create temporary output file
        output_path = sample_document.parent / "redacted_output.txt"
        
        try:
            # Redact with selective prompt
            result = pipeline.process_file(
                sample_document,
                output_path,
                prompt="redact SSN and bank information, keep name and company details"
            )
            
            # Should succeed
            assert result.success
            assert output_path.exists()
            
            # Check output content
            output_content = output_path.read_text()
            
            # Name should be preserved
            assert "Sarah Johnson" in output_content
            assert "Engineering" in output_content
            assert "techcorp.com" in output_content  # Company domain preserved
            
            # Sensitive data should be redacted (replaced with masks)
            assert "987-65-4321" not in output_content  # SSN masked
            assert "123456789012" not in output_content  # Bank account masked
            
            # Should contain mask characters or redaction markers
            assert "█" in output_content or "[REDACTED]" in output_content or "****" in output_content
            
        finally:
            if output_path.exists():
                output_path.unlink()
    
    def test_pipeline_with_unsupported_entity_types(self, sample_document):
        """Test pipeline's ability to handle entity types not in original regex system."""
        # Add content with custom entities to the document
        custom_content = """
        
        Additional Information:
        Discord: SarahDev#1234
        GitHub: github.com/sarah-dev
        Crypto Wallet: bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh
        Steam ID: STEAM_0:1:23456789
        License Plate: ABC-123
        """
        
        # Append to sample document
        with open(sample_document, 'a') as f:
            f.write(custom_content)
        
        from cloak.engine.pipeline import Pipeline
        from cloak.config import CloakConfig
        
        config = CloakConfig() 
        pipeline = Pipeline(config)
        
        result = pipeline.scan_file(
            sample_document,
            prompt="redact all gaming accounts, crypto wallets, and social media handles"
        )
        
        # Should detect custom entities that regex system couldn't handle
        entity_texts = [e.text for e in result.entities]
        
        # These would have been impossible with pure regex/spaCy approach
        assert any("SarahDev#1234" in text for text in entity_texts)
        assert any("bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh" in text for text in entity_texts) 
        assert any("STEAM_0:1:23456789" in text for text in entity_texts)
        
        # Actions should be mask for these custom entities
        for entity in result.entities:
            if any(custom in entity.text for custom in ["SarahDev", "bc1qxy", "STEAM_"]):
                assert entity.action == "mask"
    
    def test_pipeline_contextual_understanding(self, sample_document):
        """Test pipeline's contextual understanding vs rigid regex rules."""
        from cloak.engine.pipeline import Pipeline
        from cloak.config import CloakConfig
        
        config = CloakConfig()
        pipeline = Pipeline(config)
        
        # Test context-aware prompt
        result = pipeline.scan_file(
            sample_document,
            prompt="I'm sharing this with HR for benefits enrollment, hide financial info but keep work-related details"
        )
        
        # LLM should understand HR context
        entity_actions = {e.text: e.action for e in result.entities}
        
        # Work-related should be kept
        if "Sarah Johnson" in entity_actions:
            assert entity_actions["Sarah Johnson"] == "none"  # Employee name OK for HR
        if "Engineering" in entity_actions:
            assert entity_actions["Engineering"] == "none"  # Department OK for HR
        
        # Financial should be hidden  
        if "123456789012" in entity_actions:
            assert entity_actions["123456789012"] == "mask"  # Bank account hidden
        if "987-65-4321" in entity_actions:
            assert entity_actions["987-65-4321"] == "mask"  # SSN might be hidden
    
    @patch('cloak.nl.llm_entity_detector.requests.Session.post')
    def test_pipeline_api_failure_graceful_degradation(self, mock_post, sample_document):
        """Test pipeline behavior when LLM API fails."""
        # Mock API failure
        mock_post.side_effect = Exception("API timeout")
        
        from cloak.engine.pipeline import Pipeline
        from cloak.config import CloakConfig
        
        config = CloakConfig()
        pipeline = Pipeline(config)
        
        result = pipeline.scan_file(sample_document, prompt="test prompt")
        
        # Should not crash, should return fallback result
        assert hasattr(result, 'entities')
        assert hasattr(result, 'success')
        assert result.confidence == "low"  # Indicates fallback was used
    
    def test_pipeline_performance_comparison(self, sample_document):
        """Test to compare performance vs old regex/spaCy system (when available)."""
        import time
        from cloak.engine.pipeline import Pipeline
        from cloak.config import CloakConfig
        
        config = CloakConfig()
        pipeline = Pipeline(config)
        
        # Time the new LLM-first approach
        start_time = time.time()
        result = pipeline.scan_file(sample_document, prompt="redact all personal information")
        llm_time = time.time() - start_time
        
        # Should complete in reasonable time (< 5 seconds for small document)
        assert llm_time < 5.0
        
        # Should detect reasonable number of entities
        assert len(result.entities) >= 5
        assert len(result.entities) <= 20  # Shouldn't be excessive
    
    def test_pipeline_with_empty_prompt(self, sample_document):
        """Test pipeline with empty prompt - should default to redact all sensitive."""
        from cloak.engine.pipeline import Pipeline
        from cloak.config import CloakConfig
        
        config = CloakConfig()
        pipeline = Pipeline(config)
        
        result = pipeline.scan_file(sample_document, prompt="")
        
        # Should detect entities and default to masking sensitive ones
        assert len(result.entities) >= 5
        
        # Most entities should be marked for masking by default
        mask_count = sum(1 for e in result.entities if e.action == "mask")
        total_count = len(result.entities)
        
        # At least 60% should be marked for masking (conservative estimate)
        assert mask_count / total_count >= 0.6
    
    def test_pipeline_config_integration(self, sample_document):
        """Test that pipeline respects configuration settings."""
        from cloak.engine.pipeline import Pipeline
        from cloak.config import CloakConfig
        
        # Test with custom config
        config = CloakConfig()
        # Assume we add LLM-specific config options
        pipeline = Pipeline(config)
        
        result = pipeline.scan_file(sample_document, prompt="test")
        
        # Should respect configuration
        assert hasattr(result, 'cost_estimate')
        assert result.cost_estimate >= 0
    
    def test_batch_processing_efficiency(self):
        """Test processing multiple documents efficiently.""" 
        # Create multiple test documents
        documents = []
        for i in range(3):
            content = f"""
            Document {i}
            Name: Person {i}
            SSN: {i}{i}{i}-{i}{i}-{i}{i}{i}{i}
            Email: person{i}@test.com
            """
            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
            temp_file.write(content)
            temp_file.close()
            documents.append(Path(temp_file.name))
        
        try:
            from cloak.engine.pipeline import Pipeline
            from cloak.config import CloakConfig
            
            config = CloakConfig()
            pipeline = Pipeline(config)
            
            # Process all documents
            results = []
            for doc in documents:
                result = pipeline.scan_file(doc, prompt="redact SSN only")
                results.append(result)
            
            # All should succeed
            assert all(hasattr(r, 'entities') for r in results)
            assert all(len(r.entities) >= 2 for r in results)  # Name + SSN minimum
            
        finally:
            # Cleanup
            for doc in documents:
                if doc.exists():
                    doc.unlink()


class TestLLMPipelineVsLegacyComparison:
    """Compare LLM-first pipeline with legacy regex/spaCy approach."""
    
    def test_entity_coverage_comparison(self):
        """Compare entity detection coverage between old and new systems."""
        # This test documents what we gain by switching to LLM
        test_text = """
        Multi-format Entity Test:
        
        Traditional entities (old system could detect):
        - Email: test@example.com  
        - Phone: (555) 123-4567
        - SSN: 123-45-6789
        - Credit Card: 4111 1111 1111 1111
        
        Custom entities (only LLM can detect):
        - Discord: MyUser#1234
        - Crypto: bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh
        - Minecraft UUID: 550e8400-e29b-41d4-a716-446655440000
        - Twitch Stream Key: live_123456789_abcdefghijklmnop
        - Custom Employee ID: TECH-ENG-2024-0042
        """
        
        from cloak.engine.pipeline import Pipeline
        from cloak.config import CloakConfig
        
        config = CloakConfig()
        pipeline = Pipeline(config)
        
        result = pipeline.scan_text(
            test_text,
            prompt="redact all identifiers and account information"
        )
        
        entity_texts = [e.text for e in result.entities]
        
        # Should detect traditional entities
        assert "test@example.com" in entity_texts
        assert "(555) 123-4567" in entity_texts
        assert "123-45-6789" in entity_texts
        
        # Should detect custom entities (LLM advantage!)
        assert any("MyUser#1234" in text for text in entity_texts)
        assert any("bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh" in text for text in entity_texts)
        assert any("TECH-ENG-2024-0042" in text for text in entity_texts)
        
        # LLM should detect MORE entity types than regex ever could
        assert len(result.entities) >= 7  # Traditional + Custom entities


if __name__ == "__main__":
    pytest.main([__file__, "-v"])