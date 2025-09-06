"""
Database models and schema for Cloak web application.

This module defines the database schema using SQLAlchemy for user management,
usage tracking, and processing logs. Designed to support:
- User accounts with OAuth integration
- Tiered pricing (free/paid/enterprise)
- Usage tracking and limits
- Processing audit logs (without storing sensitive content)
- Future team/organization features
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SQLEnum,
    Float,
    Integer,
    String,
    Text,
    UUID,
    create_engine,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


class UserTier(str, Enum):
    """User subscription tiers."""
    FREE = "free"
    PAID = "paid"
    ENTERPRISE = "enterprise"


class ProcessingStatus(str, Enum):
    """Document processing job status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class User(Base):
    """
    User account model.
    
    Supports both email/password and OAuth authentication.
    Tracks usage and subscription tier for billing/limits.
    """
    __tablename__ = "users"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    
    # Authentication
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # None for OAuth users
    
    # OAuth integration
    oauth_provider: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # 'google', 'github', etc.
    oauth_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Profile
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Subscription and limits
    tier: Mapped[UserTier] = mapped_column(SQLEnum(UserTier), default=UserTier.FREE, nullable=False)
    monthly_documents_processed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    monthly_limit: Mapped[int] = mapped_column(Integer, default=10, nullable=False)  # Free tier: 10/month
    
    # Account status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<User(email='{self.email}', tier='{self.tier}')>"

    @property
    def has_usage_remaining(self) -> bool:
        """Check if user has remaining usage for current month."""
        return self.monthly_documents_processed < self.monthly_limit

    def reset_monthly_usage(self) -> None:
        """Reset monthly usage counter (called by background job)."""
        self.monthly_documents_processed = 0


class ProcessingJob(Base):
    """
    Document processing job tracking.
    
    Stores metadata about document processing without storing
    the actual document content for privacy compliance.
    """
    __tablename__ = "processing_jobs"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    
    # User relationship
    user_id: Mapped[uuid.UUID] = mapped_column(UUID, nullable=False, index=True)
    
    # Job details
    status: Mapped[ProcessingStatus] = mapped_column(SQLEnum(ProcessingStatus), default=ProcessingStatus.PENDING, nullable=False)
    
    # Document metadata (no sensitive content)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)  # 'pdf', 'docx', 'txt', etc.
    
    # Processing configuration
    redaction_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # User's NL prompt
    entities_detected: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    entities_redacted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Performance metrics
    processing_time_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Error handling
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<ProcessingJob(id='{self.id}', status='{self.status}', filename='{self.original_filename}')>"


class UsageLog(Base):
    """
    Daily aggregated usage statistics.
    
    Used for analytics, billing, and rate limiting.
    Aggregated by day to reduce storage overhead.
    """
    __tablename__ = "usage_logs"

    # Composite primary key (user + date)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, nullable=False, index=True)
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True, nullable=False)
    
    # Aggregated metrics
    documents_processed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_file_size_bytes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_entities_detected: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_entities_redacted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_processing_time_seconds: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self) -> str:
        return f"<UsageLog(user_id='{self.user_id}', date='{self.date.date()}', docs={self.documents_processed})>"


# Database configuration and session management
def create_database_engine(database_url: str, echo: bool = False):
    """Create SQLAlchemy engine with proper configuration."""
    return create_engine(
        database_url,
        echo=echo,
        pool_pre_ping=True,  # Verify connections before use
        pool_recycle=3600,   # Recycle connections after 1 hour
    )


def create_session_factory(engine):
    """Create session factory for database operations."""
    return sessionmaker(bind=engine, expire_on_commit=False)


def init_database(engine):
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)


# Tier limits configuration
TIER_LIMITS = {
    UserTier.FREE: {
        "monthly_documents": 10,
        "max_file_size_mb": 5,
        "supported_formats": ["txt", "pdf"],
        "features": ["basic_redaction"],
    },
    UserTier.PAID: {
        "monthly_documents": 500,
        "max_file_size_mb": 50,
        "supported_formats": ["txt", "pdf", "docx", "png", "jpg"],
        "features": ["basic_redaction", "custom_prompts", "batch_processing"],
    },
    UserTier.ENTERPRISE: {
        "monthly_documents": 10000,
        "max_file_size_mb": 100,
        "supported_formats": ["txt", "pdf", "docx", "png", "jpg", "xlsx"],
        "features": ["basic_redaction", "custom_prompts", "batch_processing", "api_access", "audit_logs", "team_management"],
    },
}


def get_user_limits(tier: UserTier) -> dict:
    """Get usage limits for a user tier."""
    return TIER_LIMITS.get(tier, TIER_LIMITS[UserTier.FREE])


def can_process_file(user: User, file_size_bytes: int, file_type: str) -> tuple[bool, str]:
    """
    Check if user can process a file given their tier limits.
    
    Returns:
        tuple: (can_process: bool, reason: str)
    """
    limits = get_user_limits(user.tier)
    
    # Check monthly document limit
    if not user.has_usage_remaining:
        return False, f"Monthly limit of {user.monthly_limit} documents exceeded"
    
    # Check file size limit
    max_size_bytes = limits["max_file_size_mb"] * 1024 * 1024
    if file_size_bytes > max_size_bytes:
        return False, f"File size exceeds {limits['max_file_size_mb']}MB limit for {user.tier} tier"
    
    # Check supported format
    if file_type.lower() not in limits["supported_formats"]:
        return False, f"File type '{file_type}' not supported in {user.tier} tier"
    
    return True, "OK"