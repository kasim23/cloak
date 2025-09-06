"""
FastAPI web application for Cloak document redaction service.

This module provides REST API endpoints for:
- Document upload and processing
- User authentication and management  
- Redaction configuration via natural language
- Visual redaction with black boxes
- Usage tracking and tier limitations
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import Optional, List
import uuid

from fastapi import FastAPI, File, UploadFile, Depends, HTTPException, status, Form
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import io

# Internal imports
from ..config import CloakConfig
from ..engine.pipeline import Pipeline
from ..nl.redaction_parser import parse_redaction_prompt
from ..visual.redactor import VisualRedactor, create_redacted_preview
from .database import (
    User, ProcessingJob, ProcessingStatus, 
    get_user_limits, can_process_file,
    create_session_factory, create_database_engine, init_database
)

logger = logging.getLogger(__name__)

# Pydantic models for API requests/responses
class RedactionRequest(BaseModel):
    """Request model for document redaction."""
    prompt: Optional[str] = None
    preview_only: bool = False

class RedactionResponse(BaseModel):
    """Response model for redaction operations."""
    job_id: str
    success: bool
    message: str
    preview_text: Optional[str] = None
    entities_detected: int = 0
    entities_redacted: int = 0
    processing_time_seconds: Optional[float] = None

class UserProfile(BaseModel):
    """User profile information."""
    id: str
    email: str
    full_name: Optional[str]
    tier: str
    monthly_documents_processed: int
    monthly_limit: int
    has_usage_remaining: bool

class ProcessingJobResponse(BaseModel):
    """Processing job status response."""
    job_id: str
    status: str
    original_filename: str
    entities_detected: int
    entities_redacted: int
    created_at: str
    error_message: Optional[str] = None

# FastAPI app configuration
app = FastAPI(
    title="Cloak API",
    description="Privacy-first document redaction service",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Security
security = HTTPBearer()

# Global configuration
cloak_config = CloakConfig()
pipeline = Pipeline(cloak_config)
visual_redactor = VisualRedactor()

# Database setup (will be configured at startup)
db_engine = None
SessionLocal = None

@app.on_event("startup")
async def startup_event():
    """Initialize database and other startup tasks."""
    global db_engine, SessionLocal
    
    # Initialize database (use SQLite for development)
    database_url = "sqlite:///./cloak.db"
    db_engine = create_database_engine(database_url, echo=False)
    SessionLocal = create_session_factory(db_engine)
    init_database(db_engine)
    
    logger.info("Cloak API started successfully")

# Dependency to get database session
def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Mock authentication for MVP (replace with real auth later)
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """
    Get current authenticated user.
    
    This is a mock implementation for MVP. In production, this would:
    - Validate JWT token
    - Look up user in database
    - Handle OAuth integration
    """
    # Mock user for development
    mock_user = User(
        id=uuid.uuid4(),
        email="test@example.com",
        full_name="Test User",
        tier="FREE",
        monthly_documents_processed=0,
        monthly_limit=10,
        is_active=True,
        email_verified=True
    )
    return mock_user

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Cloak API - Privacy-first document redaction",
        "version": "0.1.0",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "cloak-api"}

@app.get("/profile", response_model=UserProfile)
async def get_user_profile(current_user: User = Depends(get_current_user)):
    """Get current user profile and usage information."""
    return UserProfile(
        id=str(current_user.id),
        email=current_user.email,
        full_name=current_user.full_name,
        tier=current_user.tier.value,
        monthly_documents_processed=current_user.monthly_documents_processed,
        monthly_limit=current_user.monthly_limit,
        has_usage_remaining=current_user.has_usage_remaining
    )

@app.post("/redact", response_model=RedactionResponse)
async def redact_document(
    file: UploadFile = File(...),
    prompt: Optional[str] = Form(None),
    preview_only: bool = Form(False),
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    Redact sensitive information from uploaded document.
    
    Args:
        file: Document to redact
        prompt: Natural language redaction instructions (optional)
        preview_only: If True, return text preview without processing
        
    Returns:
        RedactionResponse with job details and results
    """
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No file provided"
            )
        
        # Read file content
        file_content = await file.read()
        file_size = len(file_content)
        file_type = Path(file.filename).suffix.lower().lstrip('.')
        
        # Check user limits
        can_process, reason = can_process_file(current_user, file_size, file_type)
        if not can_process:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=reason
            )
        
        # Create processing job
        job_id = str(uuid.uuid4())
        
        # Process document
        text_content = file_content.decode('utf-8', errors='ignore')
        
        # Apply natural language customization if provided
        config = cloak_config
        if prompt:
            redaction_config = parse_redaction_prompt(prompt)
            config = cloak_config.model_copy()
            config.policy = redaction_config.apply_to_policy(config.policy)
        
        # Update pipeline with custom config
        custom_pipeline = Pipeline(config)
        
        # Detect entities
        spans = custom_pipeline.scan_text(text_content)
        
        if preview_only:
            # Return text preview with redaction blocks
            preview_text = create_redacted_preview(spans, text_content)
            
            return RedactionResponse(
                job_id=job_id,
                success=True,
                message="Preview generated successfully",
                preview_text=preview_text,
                entities_detected=len(spans),
                entities_redacted=len(spans)
            )
        
        else:
            # Perform actual visual redaction
            result = visual_redactor.redact_document(
                input_path=io.BytesIO(file_content),
                spans=spans,
                output_path=f"/tmp/redacted_{job_id}.png",  # Temporary file
                file_type=file_type
            )
            
            if result.success:
                # Update user usage (in production, this would be in a database transaction)
                current_user.monthly_documents_processed += 1
                
                return RedactionResponse(
                    job_id=job_id,
                    success=True,
                    message="Document redacted successfully",
                    entities_detected=len(spans),
                    entities_redacted=result.redacted_count,
                    processing_time_seconds=1.0  # Mock timing
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Redaction failed: {result.error_message}"
                )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error in redact_document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@app.get("/jobs/{job_id}")
async def get_job_status(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get processing job status and details."""
    # Mock response for MVP (in production, query database)
    return ProcessingJobResponse(
        job_id=job_id,
        status="completed",
        original_filename="document.txt",
        entities_detected=5,
        entities_redacted=5,
        created_at="2024-01-01T00:00:00Z"
    )

@app.get("/jobs/{job_id}/download")
async def download_redacted_document(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """Download the redacted document."""
    try:
        # In production, look up job in database and return the file
        output_path = f"/tmp/redacted_{job_id}.png"
        
        if not Path(output_path).exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Redacted document not found or expired"
            )
        
        def file_generator():
            with open(output_path, "rb") as f:
                yield from f
        
        return StreamingResponse(
            file_generator(),
            media_type="image/png",
            headers={"Content-Disposition": f"attachment; filename=redacted_{job_id}.png"}
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error downloading file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to download file"
        )

@app.get("/suggestions")
async def get_redaction_suggestions():
    """Get example redaction prompts to help users."""
    from ..nl.redaction_parser import get_redaction_suggestions
    
    return {
        "suggestions": get_redaction_suggestions()
    }

@app.post("/analyze-prompt")
async def analyze_prompt(request: dict):
    """Analyze a natural language prompt to show what entities will be redacted/kept."""
    from ..nl.redaction_parser import RedactionPromptParser
    
    prompt = request.get("prompt", "").strip()
    if not prompt:
        return {
            "entities_to_redact": [],
            "entities_to_keep": [],
            "unrecognized_terms": [],
            "confidence": "high"
        }
    
    try:
        parser = RedactionPromptParser()
        result = parser.parse_redaction_prompt(prompt)
        
        # Convert the parsed result into a user-friendly format
        entities_to_redact = []
        entities_to_keep = []
        
        for entity_type, action in result.entity_actions.items():
            if action == "redact":
                entities_to_redact.append(entity_type)
            elif action == "keep":
                entities_to_keep.append(entity_type)
        
        # Determine confidence based on how much we could parse
        total_words = len(prompt.split())
        recognized_patterns = len(entities_to_redact) + len(entities_to_keep)
        confidence = "high" if recognized_patterns > 0 else "low"
        
        return {
            "entities_to_redact": entities_to_redact,
            "entities_to_keep": entities_to_keep,
            "unrecognized_terms": [],  # Could be enhanced to detect unrecognized terms
            "confidence": confidence,
            "parsed_intent": result.intent
        }
    
    except Exception as e:
        return {
            "entities_to_redact": [],
            "entities_to_keep": [],
            "unrecognized_terms": [prompt],
            "confidence": "low",
            "error": str(e)
        }

# Development endpoints (remove in production)
@app.get("/dev/test-redaction")
async def test_redaction():
    """Test endpoint for development."""
    test_text = "Hello John Smith, your SSN is 123-45-6789 and email is john@example.com"
    spans = pipeline.scan_text(test_text)
    preview = create_redacted_preview(spans, test_text)
    
    return {
        "original": test_text,
        "preview": preview,
        "entities_detected": len(spans),
        "spans": [{"text": s.text, "type": s.type, "confidence": s.confidence} for s in spans]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)