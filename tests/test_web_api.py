"""
Tests for the web API endpoints.

This module tests the FastAPI application endpoints for document
redaction, user management, and file processing.

TODO: Database Integration Testing
- Currently using mocked database dependencies for unit testing
- Need to add integration tests with real database setup:
  1. Create test database fixtures with SQLite in-memory
  2. Test full user workflow with database persistence
  3. Test usage tracking and tier limitations
  4. Test processing job storage and retrieval
  5. Test database transaction handling and rollbacks
"""

import io
from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient

from cloak.web.api import app, get_db
from cloak.engine.pipeline import Span


@pytest.fixture
def client():
    """Create test client for FastAPI app."""
    # Override the database dependency for testing to avoid database initialization issues
    # TODO: Replace with proper test database setup for integration testing
    def override_get_db():
        return None  # Mock database session
    
    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture  
def mock_auth_user():
    """Mock authenticated user for testing."""
    from cloak.web.database import User
    import uuid
    
    return User(
        id=uuid.uuid4(),
        email="test@example.com",
        full_name="Test User",
        tier="FREE",
        monthly_documents_processed=0,
        monthly_limit=10,
        is_active=True,
        email_verified=True
    )


class TestBasicEndpoints:
    """Test basic API endpoints."""
    
    def test_root_endpoint(self, client):
        """Test the root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "Cloak API" in data["message"]
    
    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "cloak-api"
    
    def test_redaction_suggestions(self, client):
        """Test getting redaction suggestions."""
        response = client.get("/suggestions")
        assert response.status_code == 200
        data = response.json()
        assert "suggestions" in data
        assert isinstance(data["suggestions"], list)
        assert len(data["suggestions"]) > 0


class TestAuthenticationRequired:
    """Test endpoints that require authentication."""
    
    def test_profile_without_auth(self, client):
        """Test profile endpoint without authentication."""
        response = client.get("/profile")
        assert response.status_code == 403  # FastAPI returns 403 for missing auth
    
    def test_redact_without_auth(self, client):
        """Test redaction endpoint without authentication."""
        # Create a test file
        test_file = ("test.txt", "Hello world", "text/plain")
        
        response = client.post(
            "/redact",
            files={"file": test_file}
        )
        assert response.status_code == 403


class TestAuthenticatedEndpoints:
    """Test endpoints with mocked authentication."""
    
    @patch('cloak.web.api.get_current_user')
    def test_get_profile(self, mock_get_user, client, mock_auth_user):
        """Test getting user profile."""
        mock_get_user.return_value = mock_auth_user
        
        response = client.get(
            "/profile",
            headers={"Authorization": "Bearer fake-token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@example.com"
        assert data["tier"] == "FREE"
        assert data["monthly_limit"] == 10
    
    @patch('cloak.web.api.get_current_user')
    @patch('cloak.web.api.pipeline')
    def test_redact_preview_only(self, mock_pipeline, mock_get_user, client, mock_auth_user):
        """Test document redaction with preview only."""
        mock_get_user.return_value = mock_auth_user
        
        # Mock the pipeline to return some test spans
        test_spans = [
            Span(start=6, end=10, text="John", type="PERSON", confidence=0.9),
            Span(start=23, end=34, text="555-1234", type="PHONE", confidence=0.95)
        ]
        mock_pipeline.scan_text.return_value = test_spans
        
        # Create test file
        test_content = "Hello John, call me at 555-1234"
        test_file = ("test.txt", test_content, "text/plain")
        
        response = client.post(
            "/redact",
            files={"file": test_file},
            data={"preview_only": "true", "prompt": "redact all personal info"},
            headers={"Authorization": "Bearer fake-token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "preview_text" in data
        assert data["entities_detected"] == 2
        assert "█" in data["preview_text"]  # Should contain redaction blocks
    
    @patch('cloak.web.api.get_current_user')
    @patch('cloak.web.api.pipeline')
    @patch('cloak.web.api.visual_redactor')
    def test_redact_full_processing(self, mock_visual_redactor, mock_pipeline, mock_get_user, client, mock_auth_user):
        """Test full document redaction processing."""
        mock_get_user.return_value = mock_auth_user
        
        # Mock pipeline
        test_spans = [
            Span(start=6, end=10, text="John", type="PERSON", confidence=0.9)
        ]
        mock_pipeline.scan_text.return_value = test_spans
        
        # Mock visual redactor
        from cloak.visual.redactor import RedactionResult
        mock_result = RedactionResult(
            success=True,
            output_path="/tmp/test.png",
            redacted_count=1,
            file_size_bytes=1024
        )
        mock_visual_redactor.redact_document.return_value = mock_result
        
        # Create test file
        test_content = "Hello John"
        test_file = ("test.txt", test_content, "text/plain")
        
        response = client.post(
            "/redact",
            files={"file": test_file},
            data={"preview_only": "false"},
            headers={"Authorization": "Bearer fake-token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["entities_detected"] == 1
        assert data["entities_redacted"] == 1
    
    @patch('cloak.web.api.get_current_user')
    def test_redact_file_size_limit(self, mock_get_user, client, mock_auth_user):
        """Test file size limit enforcement."""
        # Set user to have exceeded limits
        mock_auth_user.monthly_documents_processed = 10  # At limit
        mock_auth_user.monthly_limit = 10
        mock_get_user.return_value = mock_auth_user
        
        # Create test file
        test_file = ("test.txt", "Hello world", "text/plain")
        
        response = client.post(
            "/redact",
            files={"file": test_file},
            headers={"Authorization": "Bearer fake-token"}
        )
        
        assert response.status_code == 403
        assert "limit" in response.json()["detail"].lower()
    
    @patch('cloak.web.api.get_current_user')
    def test_redact_unsupported_file_type(self, mock_get_user, client, mock_auth_user):
        """Test unsupported file type handling."""
        mock_get_user.return_value = mock_auth_user
        
        # Create unsupported file type
        test_file = ("test.xyz", "Hello world", "application/unknown")
        
        response = client.post(
            "/redact",
            files={"file": test_file},
            headers={"Authorization": "Bearer fake-token"}
        )
        
        assert response.status_code == 403
        assert "not supported" in response.json()["detail"].lower()
    
    @patch('cloak.web.api.get_current_user')
    def test_get_job_status(self, mock_get_user, client, mock_auth_user):
        """Test getting job status."""
        mock_get_user.return_value = mock_auth_user
        
        job_id = "test-job-123"
        response = client.get(
            f"/jobs/{job_id}",
            headers={"Authorization": "Bearer fake-token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == job_id
        assert "status" in data
    
    @patch('cloak.web.api.get_current_user')
    def test_download_nonexistent_file(self, mock_get_user, client, mock_auth_user):
        """Test downloading non-existent redacted file."""
        mock_get_user.return_value = mock_auth_user
        
        job_id = "nonexistent-job"
        response = client.get(
            f"/jobs/{job_id}/download",
            headers={"Authorization": "Bearer fake-token"}
        )
        
        assert response.status_code == 404


class TestDevelopmentEndpoints:
    """Test development-only endpoints."""
    
    @patch('cloak.web.api.pipeline')
    def test_dev_test_redaction(self, mock_pipeline, client):
        """Test development redaction endpoint."""
        # Mock pipeline response
        test_spans = [
            Span(start=6, end=16, text="John Smith", type="PERSON", confidence=0.9),
            Span(start=31, end=42, text="123-45-6789", type="SSN", confidence=0.95),
            Span(start=56, end=72, text="john@example.com", type="EMAIL", confidence=0.98)
        ]
        mock_pipeline.scan_text.return_value = test_spans
        
        response = client.get("/dev/test-redaction")
        
        assert response.status_code == 200
        data = response.json()
        assert "original" in data
        assert "preview" in data
        assert "entities_detected" in data
        assert "spans" in data
        assert data["entities_detected"] == 3
        assert len(data["spans"]) == 3


class TestErrorHandling:
    """Test error handling scenarios."""
    
    @patch('cloak.web.api.get_current_user')
    def test_redact_no_file(self, mock_get_user, client, mock_auth_user):
        """Test redaction endpoint with no file provided."""
        mock_get_user.return_value = mock_auth_user
        
        response = client.post(
            "/redact",
            headers={"Authorization": "Bearer fake-token"}
        )
        
        # Should fail due to missing required file parameter
        assert response.status_code == 422  # Unprocessable Entity
    
    @patch('cloak.web.api.get_current_user')
    @patch('cloak.web.api.pipeline')
    def test_redact_processing_error(self, mock_pipeline, mock_get_user, client, mock_auth_user):
        """Test handling of processing errors."""
        mock_get_user.return_value = mock_auth_user
        
        # Make pipeline raise an exception
        mock_pipeline.scan_text.side_effect = Exception("Processing failed")
        
        test_file = ("test.txt", "Hello world", "text/plain")
        
        response = client.post(
            "/redact",
            files={"file": test_file},
            headers={"Authorization": "Bearer fake-token"}
        )
        
        assert response.status_code == 500
        assert "internal server error" in response.json()["detail"].lower()