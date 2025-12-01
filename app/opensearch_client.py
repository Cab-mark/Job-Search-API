"""
OpenSearch Client Module

Provides functionality for connecting to OpenSearch and managing the jobs index.
The index mapping is designed to match the TypeScript JobResult interface exactly.
"""

import logging
from typing import Optional, Dict, Any
from opensearchpy import OpenSearch
from opensearchpy.exceptions import NotFoundError, RequestError

from app.config import get_settings

logger = logging.getLogger(__name__)

# Global OpenSearch client instance
_client: Optional[OpenSearch] = None


def get_opensearch_client() -> OpenSearch:
    """
    Get or create the OpenSearch client instance.
    
    Returns:
        OpenSearch: Configured OpenSearch client
    """
    global _client
    
    if _client is None:
        settings = get_settings()
        
        # Build the host configuration
        hosts = [
            {
                'host': settings.opensearch_host,
                'port': settings.opensearch_port,
            }
        ]
        
        # Configure authentication if provided
        http_auth = None
        if settings.opensearch_username and settings.opensearch_password:
            http_auth = (settings.opensearch_username, settings.opensearch_password)
        
        _client = OpenSearch(
            hosts=hosts,
            http_auth=http_auth,
            use_ssl=False,  # Disabled for local development
            verify_certs=False,  # Disabled for local development
            ssl_show_warn=False,
            timeout=30,
            max_retries=3,
            retry_on_timeout=True,
        )
        
        logger.info(f"OpenSearch client created for {settings.opensearch_host}:{settings.opensearch_port}")
    
    return _client


def get_jobs_index_mapping() -> Dict[str, Any]:
    """
    Get the OpenSearch index mapping for the jobs index.
    
    This mapping reflects the TypeScript Job interface from nextjs_govuk_experiment exactly:
    - keyword fields for IDs and enum-like values
    - text fields for searchable strings (with keyword subfield for exact matching)
    - integer for numeric fields (jobNumbers)
    - boolean for boolean fields (contacts)
    
    Returns:
        Dict containing the index mapping configuration
    """
    return {
        "mappings": {
            "properties": {
                # Job ID - keyword for exact matching
                "id": {
                    "type": "keyword"
                },
                # Job title - text for full-text search, keyword for sorting/aggregations
                "title": {
                    "type": "text",
                    "fields": {
                        "keyword": {
                            "type": "keyword"
                        }
                    }
                },
                # Job description - text for full-text search
                "description": {
                    "type": "text"
                },
                # Organisation - text for full-text search, keyword for filtering
                "organisation": {
                    "type": "text",
                    "fields": {
                        "keyword": {
                            "type": "keyword"
                        }
                    }
                },
                # Location - text for full-text search, keyword for filtering
                "location": {
                    "type": "text",
                    "fields": {
                        "keyword": {
                            "type": "keyword"
                        }
                    }
                },
                # Grade - keyword for filtering (e.g., 'Grade 7', 'Senior Executive Officer')
                "grade": {
                    "type": "keyword"
                },
                # Assignment type - keyword for filtering (e.g., 'Permanent', 'Fixed Term Appointment (FTA)')
                "assignmentType": {
                    "type": "keyword"
                },
                # Personal specification - text for full-text search
                "personalSpec": {
                    "type": "text"
                },
                # Nationality requirement - text for full-text search
                "nationalityRequirement": {
                    "type": "text"
                },
                # Summary - text for full-text search
                "summary": {
                    "type": "text"
                },
                # Apply URL - keyword
                "applyUrl": {
                    "type": "keyword"
                },
                # Benefits - text for full-text search
                "benefits": {
                    "type": "text"
                },
                # Profession - keyword for filtering (e.g., 'Policy')
                "profession": {
                    "type": "text",
                    "fields": {
                        "keyword": {
                            "type": "keyword"
                        }
                    }
                },
                # Apply detail - text for full-text search
                "applyDetail": {
                    "type": "text"
                },
                # Salary - text (stored as string like '£45,000')
                "salary": {
                    "type": "text",
                    "fields": {
                        "keyword": {
                            "type": "keyword"
                        }
                    }
                },
                # Closing date - text (stored as string like '20 December 2025')
                "closingDate": {
                    "type": "text",
                    "fields": {
                        "keyword": {
                            "type": "keyword"
                        }
                    }
                },
                # Job numbers - integer for number of positions available
                "jobNumbers": {
                    "type": "integer"
                },
                # Contacts - boolean flag indicating if contact details are available
                "contacts": {
                    "type": "boolean"
                },
                # Contact name - text
                "contactName": {
                    "type": "text",
                    "fields": {
                        "keyword": {
                            "type": "keyword"
                        }
                    }
                },
                # Contact email - keyword
                "contactEmail": {
                    "type": "keyword"
                },
                # Contact phone - keyword
                "contactPhone": {
                    "type": "keyword"
                },
                # Recruitment email - keyword
                "recruitmentEmail": {
                    "type": "keyword"
                }
            }
        },
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 0,  # 0 replicas for local development
            "index": {
                "refresh_interval": "1s"
            }
        }
    }


def ensure_index_exists() -> bool:
    """
    Ensure the jobs index exists in OpenSearch.
    
    Creates the index with the proper mapping if it doesn't exist.
    
    Returns:
        bool: True if index exists or was created successfully
    
    Raises:
        Exception: If unable to create or verify the index
    """
    settings = get_settings()
    client = get_opensearch_client()
    index_name = settings.opensearch_index
    
    try:
        # Check if index already exists
        if client.indices.exists(index=index_name):
            logger.info(f"Index '{index_name}' already exists")
            return True
        
        # Create the index with mapping
        mapping = get_jobs_index_mapping()
        client.indices.create(index=index_name, body=mapping)
        logger.info(f"Index '{index_name}' created successfully")
        return True
        
    except RequestError as e:
        # Index might already exist (race condition)
        if "resource_already_exists_exception" in str(e):
            logger.info(f"Index '{index_name}' already exists (concurrent creation)")
            return True
        logger.error(f"Failed to create index '{index_name}': {e}")
        raise
    except Exception as e:
        logger.error(f"Error ensuring index exists: {e}")
        raise


def check_opensearch_connection() -> bool:
    """
    Check if OpenSearch is reachable.
    
    Returns:
        bool: True if OpenSearch is connected and responding
    """
    try:
        client = get_opensearch_client()
        info = client.info()
        logger.debug(f"OpenSearch connected: {info.get('cluster_name', 'unknown')}")
        return True
    except Exception as e:
        logger.warning(f"OpenSearch connection check failed: {e}")
        return False


def close_client() -> None:
    """
    Close the OpenSearch client connection.
    
    Should be called during application shutdown.
    """
    global _client
    if _client is not None:
        _client.close()
        _client = None
        logger.info("OpenSearch client closed")
