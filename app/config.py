"""
Configuration module for the Job Search API.

Uses Pydantic BaseSettings to load configuration from environment variables.
All settings can be overridden by setting the corresponding environment variable.
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    Environment variables are automatically loaded and validated.
    Default values are provided for local development.
    """
    
    # OpenSearch Configuration
    opensearch_host: str = Field(
        default="opensearch",
        description="OpenSearch hostname"
    )
    opensearch_port: int = Field(
        default=9200,
        description="OpenSearch port number"
    )
    opensearch_index: str = Field(
        default="jobs",
        description="Name of the jobs index in OpenSearch"
    )
    
    # Optional: OpenSearch authentication (for production)
    opensearch_username: str = Field(
        default="",
        description="OpenSearch username (optional)"
    )
    opensearch_password: str = Field(
        default="",
        description="OpenSearch password (optional)"
    )
    
    # API Configuration
    api_title: str = Field(
        default="Job Search API",
        description="API title for documentation"
    )
    api_version: str = Field(
        default="1.0.0",
        description="API version"
    )
    api_description: str = Field(
        default="FastAPI-based Job Search API with OpenSearch backend",
        description="API description for documentation"
    )
    
    # Pagination defaults
    default_page_size: int = Field(
        default=10,
        description="Default number of results per page"
    )
    max_page_size: int = Field(
        default=100,
        description="Maximum number of results per page"
    )

    class Config:
        # Load from .env file
        env_file = ".env"
        env_file_encoding = "utf-8"
        # Allow environment variables to override .env file
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    
    Uses lru_cache to ensure settings are loaded only once
    and reused across the application.
    
    Returns:
        Settings: Application settings instance
    """
    return Settings()
