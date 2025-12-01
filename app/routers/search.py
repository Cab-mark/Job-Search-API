"""
Search Router for Job Search API

Contains all endpoints related to job search functionality:
- GET /jobs - Search for jobs with optional filters and pagination
- GET /jobs/{id} - Get a specific job by ID
- POST /jobs - Create a new job posting (local development only)
"""

import logging
import math
import uuid
from typing import Optional, List, Dict, Any, Union
from fastapi import APIRouter, HTTPException, Query, Path

from app.models import Job, JobSearchResponse, JobCreateRequest
from app.config import get_settings
from app.opensearch_client import get_opensearch_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs", tags=["jobs"])


def build_search_query(
    q: Optional[str] = None,
    filters: Optional[Dict[str, Union[str, List[str]]]] = None
) -> Dict[str, Any]:
    """
    Build an OpenSearch query from search parameters.
    
    Args:
        q: Search query string for full-text search
        filters: Dictionary of field filters
        
    Returns:
        OpenSearch query body
    """
    must_clauses = []
    filter_clauses = []
    
    # Full-text search across multiple fields
    if q:
        must_clauses.append({
            "multi_match": {
                "query": q,
                "fields": [
                    "title^3",  # Boost title matches
                    "description",
                    "organisation^2",
                    "location",
                    "summary",
                    "profession",
                    "grade"
                ],
                "type": "best_fields",
                "fuzziness": "AUTO"
            }
        })
    
    # Apply filters
    if filters:
        for field, value in filters.items():
            if isinstance(value, list):
                # Multiple values: use terms query
                filter_clauses.append({
                    "terms": {
                        f"{field}.keyword" if field in ["title", "organisation", "location", "profession", "salary", "closingDate"] else field: value
                    }
                })
            else:
                # Single value: use term query
                filter_clauses.append({
                    "term": {
                        f"{field}.keyword" if field in ["title", "organisation", "location", "profession", "salary", "closingDate"] else field: value
                    }
                })
    
    # Build the query
    if must_clauses or filter_clauses:
        query = {
            "bool": {}
        }
        if must_clauses:
            query["bool"]["must"] = must_clauses
        if filter_clauses:
            query["bool"]["filter"] = filter_clauses
    else:
        # Match all if no query or filters
        query = {"match_all": {}}
    
    return query


@router.get("", response_model=JobSearchResponse)
async def search_jobs(
    q: Optional[str] = Query(None, description="Search query for full-text search"),
    organisation: Optional[str] = Query(None, description="Filter by organisation"),
    location: Optional[str] = Query(None, description="Filter by location"),
    grade: Optional[str] = Query(None, description="Filter by grade"),
    assignmentType: Optional[str] = Query(None, description="Filter by assignment type"),
    profession: Optional[str] = Query(None, description="Filter by profession"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    pageSize: int = Query(None, ge=1, le=100, description="Number of results per page")
) -> JobSearchResponse:
    """
    Search for jobs with optional query, filters, and pagination.
    
    The search performs full-text search across title, description, organisation,
    location, summary, profession, and grade fields.
    
    Filters can be applied to narrow down results by specific field values.
    
    Returns:
        JobSearchResponse containing paginated results and metadata
    """
    settings = get_settings()
    client = get_opensearch_client()
    
    # Use default page size if not specified
    if pageSize is None:
        pageSize = settings.default_page_size
    
    # Build filters from query parameters
    filters: Dict[str, str] = {}
    if organisation:
        filters["organisation"] = organisation
    if location:
        filters["location"] = location
    if grade:
        filters["grade"] = grade
    if assignmentType:
        filters["assignmentType"] = assignmentType
    if profession:
        filters["profession"] = profession
    
    # Build the search query
    query = build_search_query(q=q, filters=filters if filters else None)
    
    # Calculate pagination
    from_index = (page - 1) * pageSize
    
    # Execute search
    try:
        response = client.search(
            index=settings.opensearch_index,
            body={
                "query": query,
                "from": from_index,
                "size": pageSize,
                "sort": [
                    {"_score": {"order": "desc"}},
                    {"id": {"order": "asc"}}
                ]
            }
        )
        
        # Extract results
        hits = response.get("hits", {})
        total_hits = hits.get("total", {})
        total = total_hits.get("value", 0) if isinstance(total_hits, dict) else total_hits
        
        results = []
        for hit in hits.get("hits", []):
            source = hit.get("_source", {})
            results.append(Job(**source))
        
        # Calculate total pages
        total_pages = math.ceil(total / pageSize) if total > 0 else 0
        
        return JobSearchResponse(
            results=results,
            total=total,
            page=page,
            pageSize=pageSize,
            totalPages=total_pages,
            query=q,
            appliedFilters=filters if filters else None
        )
        
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/{job_id}", response_model=Job)
async def get_job(
    job_id: str = Path(..., description="The unique job identifier")
) -> Job:
    """
    Get a specific job by its ID.
    
    Args:
        job_id: The unique identifier of the job
        
    Returns:
        Job: The job document
        
    Raises:
        HTTPException: 404 if job not found
    """
    settings = get_settings()
    client = get_opensearch_client()
    
    try:
        # Search for the job by ID
        response = client.search(
            index=settings.opensearch_index,
            body={
                "query": {
                    "term": {
                        "id": job_id
                    }
                }
            }
        )
        
        hits = response.get("hits", {}).get("hits", [])
        
        if not hits:
            raise HTTPException(status_code=404, detail=f"Job with id '{job_id}' not found")
        
        source = hits[0].get("_source", {})
        return Job(**source)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve job: {str(e)}")


@router.post("", response_model=Job, status_code=201)
async def create_job(job: JobCreateRequest) -> Job:
    """
    Create a new job posting.
    
    This endpoint is intended for local development and testing purposes.
    In production, jobs would typically be indexed through a separate data pipeline.
    
    Args:
        job: Job data to create
        
    Returns:
        Job: The created job with generated ID
    """
    settings = get_settings()
    client = get_opensearch_client()
    
    # Generate a unique ID
    job_id = str(uuid.uuid4())
    
    # Create the job document
    job_data = job.model_dump()
    job_data["id"] = job_id
    
    try:
        # Index the document
        client.index(
            index=settings.opensearch_index,
            body=job_data,
            id=job_id,
            refresh=True  # Refresh immediately for local dev
        )
        
        logger.info(f"Created job with id: {job_id}")
        return Job(**job_data)
        
    except Exception as e:
        logger.error(f"Failed to create job: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create job: {str(e)}")
