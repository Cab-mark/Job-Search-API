"""
Pydantic Models for the Job Search API

Local models for non-jobs-domain responses.
Job domain models are imported from the jobs-data-contracts package.
"""

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """
    Response model for health check endpoint.
    """
    status: str = Field(..., description="Health status")
    opensearch_connected: bool = Field(..., description="OpenSearch connection status")
    timestamp: str = Field(..., description="Current timestamp (ISO 8601)")
