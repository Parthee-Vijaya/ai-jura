"""
Database module for AI Compliance Platform.

This module provides database connectivity, ORM models, and data access layers
for both PostgreSQL (relational data) and Qdrant (vector embeddings).
"""

from .connection import engine, SessionLocal, get_db, init_db
from .models import Base, AssessmentRecord, ComplianceCheck, UserSession, LegalDocumentRecord
from .qdrant_client import get_qdrant_client, init_qdrant
from .repository import AssessmentRepository
from .vector_store import VectorStore

__all__ = [
    # Database connection
    "engine",
    "SessionLocal",
    "get_db",
    "init_db",
    # ORM Models
    "Base",
    "AssessmentRecord",
    "ComplianceCheck",
    "UserSession",
    "LegalDocumentRecord",
    # Qdrant
    "get_qdrant_client",
    "init_qdrant",
    # Repositories
    "AssessmentRepository",
    # Vector Store
    "VectorStore",
]
