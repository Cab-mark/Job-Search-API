"""
Search Router for Job Search API

Contains endpoints related to job search functionality:
- GET /jobs - Search for jobs with optional filters and pagination

This module uses Pydantic models from the jobs-data-contracts package.
"""

import logging
import math
import json
from datetime import date
from typing import Optional, List, Dict, Any, Union
from fastapi import APIRouter, HTTPException, Query

from jobs_data_contracts.search import (
    JobSearchResponse,
    JobResultItem,
    Profession,
    Grade,
    Assignments,
    WorkingPattern,
    WorkLocation,
    Salary,
    FixedLocation,
    Approach,
)
from app.config import get_settings
from app.opensearch_client import get_opensearch_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs", tags=["jobs"])


def build_search_query(
    q: Optional[str] = None,
    organisation: Optional[str] = None,
    professions: Optional[List[str]] = None,
    grades: Optional[List[str]] = None,
    assignments: Optional[List[str]] = None,
    working_patterns: Optional[List[str]] = None,
    work_locations: Optional[List[str]] = None,
    salary_min: Optional[float] = None,
    salary_max: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Build an OpenSearch query from search parameters.
    
    Args:
        q: Search query string for full-text search
        organisation: Organisation filter
        professions: List of professions to filter by
        grades: List of grades to filter by
        assignments: List of assignment types to filter by
        working_patterns: List of working patterns to filter by
        work_locations: List of work locations to filter by
        salary_min: Minimum salary filter
        salary_max: Maximum salary filter
        
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
    
    # Organisation filter (exact match on keyword field)
    if organisation:
        filter_clauses.append({
            "term": {
                "organisation.keyword": organisation
            }
        })
    
    # Profession filter (multi-select)
    if professions:
        filter_clauses.append({
            "terms": {
                "profession.keyword": professions
            }
        })
    
    # Grade filter (multi-select)
    if grades:
        filter_clauses.append({
            "terms": {
                "grade": grades
            }
        })
    
    # Assignment type filter (multi-select)
    if assignments:
        filter_clauses.append({
            "terms": {
                "assignmentType": assignments
            }
        })
    
    # Working pattern filter (multi-select)
    if working_patterns:
        filter_clauses.append({
            "terms": {
                "workingPattern": working_patterns
            }
        })
    
    # Work location filter (multi-select)
    if work_locations:
        filter_clauses.append({
            "terms": {
                "workLocation": work_locations
            }
        })
    
    # Salary range filter
    if salary_min is not None or salary_max is not None:
        range_filter = {"salary.minimum": {}}
        if salary_min is not None:
            range_filter["salary.minimum"]["gte"] = salary_min
        if salary_max is not None:
            range_filter["salary.minimum"]["lte"] = salary_max
        filter_clauses.append({"range": range_filter})
    
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


def opensearch_hit_to_job_result_item(hit: Dict[str, Any]) -> JobResultItem:
    """
    Convert an OpenSearch hit to a JobResultItem.
    
    This function handles the mapping between the OpenSearch document structure
    and the JobResultItem Pydantic model from jobs-data-contracts.
    
    Note: The current OpenSearch data may have a different structure than expected.
    This function provides a basic mapping that may need adjustment based on
    actual data in the index.
    
    Args:
        hit: OpenSearch hit dictionary
        
    Returns:
        JobResultItem: Mapped job result item
    """
    source = hit.get("_source", {})
    
    # Extract basic fields
    job_id = source.get("id", "")
    external_id = source.get("externalId", source.get("id", ""))
    title = source.get("title", "")
    organisation = source.get("organisation", "")
    
    # Handle location - try to parse as FixedLocation, fallback to simple structure
    location_data = source.get("location", [])
    if isinstance(location_data, str):
        # Legacy format: convert string to FixedLocation
        location = [FixedLocation(
            town_name=location_data,
            region="Unknown",
            latitude=0.0,
            longitude=0.0
        )]
    elif isinstance(location_data, list) and location_data:
        # Already in array format
        try:
            location = [FixedLocation(**loc) if isinstance(loc, dict) else FixedLocation(
                town_name=str(loc),
                region="Unknown",
                latitude=0.0,
                longitude=0.0
            ) for loc in location_data]
        except Exception as e:
            logger.warning(f"Failed to parse location data: {e}, using fallback")
            location = [FixedLocation(
                town_name=str(location_data[0]) if location_data else "Unknown",
                region="Unknown",
                latitude=0.0,
                longitude=0.0
            )]
    else:
        location = [FixedLocation(
            town_name="Unknown",
            region="Unknown",
            latitude=0.0,
            longitude=0.0
        )]
    
    # Handle working pattern - convert to enum
    working_pattern_data = source.get("workingPattern", [])
    if isinstance(working_pattern_data, str):
        working_pattern_data = [working_pattern_data]
    working_pattern = [
        WorkingPattern(wp) if wp in ["Full-time", "Part-time"] else WorkingPattern.full_time
        for wp in (working_pattern_data if working_pattern_data else ["Full-time"])
    ]
    
    # Handle assignment type - convert to enum
    assignment_type_str = source.get("assignmentType", "Permanent")
    try:
        assignment_type = Assignments(assignment_type_str)
    except ValueError:
        assignment_type = Assignments.permanent
    
    # Handle salary - convert to structured format
    salary_data = source.get("salary")
    if isinstance(salary_data, dict) and "minimum" in salary_data:
        salary = Salary(**salary_data)
    elif isinstance(salary_data, str):
        # Parse salary string (e.g., "£45,000")
        try:
            salary_value = float(salary_data.replace("£", "").replace(",", ""))
            salary = Salary(minimum=salary_value, currency="GBP", currency_symbol="£")
        except (ValueError, AttributeError):
            salary = Salary(minimum=0.0, currency="GBP", currency_symbol="£")
    else:
        salary = Salary(minimum=0.0, currency="GBP", currency_symbol="£")
    
    # Handle work location - convert to enum
    work_location_data = source.get("workLocation", [])
    if isinstance(work_location_data, str):
        work_location_data = [work_location_data]
    work_location = [
        WorkLocation(wl) if wl in ["Home based", "Office based"] else WorkLocation.office_based
        for wl in (work_location_data if work_location_data else ["Office based"])
    ]
    
    # Handle grade - can be enum or string
    grade_str = source.get("grade", "")
    try:
        grade = Grade(grade_str)
    except ValueError:
        grade = grade_str or "Unknown"
    
    # Handle closing date - convert to date
    closing_date_str = source.get("closingDate", "")
    try:
        closing_date = date.fromisoformat(closing_date_str)
    except (ValueError, TypeError):
        # Fallback: try to parse common date formats or use far future
        closing_date = date(2099, 12, 31)
    
    # Handle profession - convert to enum
    profession_str = source.get("profession", "")
    try:
        profession = Profession(profession_str)
    except ValueError:
        # Default to first profession if not found
        profession = Profession.actuary
    
    # Handle approach - convert to enum
    approach_str = source.get("approach", "Internal")
    try:
        approach = Approach(approach_str)
    except ValueError:
        approach = Approach.internal
    
    return JobResultItem(
        id=job_id,
        external_id=external_id,
        title=title,
        organisation=organisation,
        location=location,
        working_pattern=working_pattern,
        assignment_type=assignment_type,
        salary=salary,
        work_location=work_location,
        grade=grade,
        closing_date=closing_date,
        profession=profession,
        approach=approach,
    )


@router.get("", response_model=JobSearchResponse)
async def search_jobs(
    q: Optional[str] = Query(None, description="Search query for full-text search"),
    organisation: Optional[str] = Query(None, description="Filter by organisation"),
    professions: Optional[List[str]] = Query(None, description="Filter by professions (multi-select)"),
    grades: Optional[List[str]] = Query(None, description="Filter by grades (multi-select)"),
    assignments: Optional[List[str]] = Query(None, description="Filter by assignment types (multi-select)"),
    working_patterns: Optional[List[str]] = Query(None, alias="workingPatterns", description="Filter by working patterns (multi-select)"),
    work_locations: Optional[List[str]] = Query(None, alias="workLocations", description="Filter by work locations (multi-select)"),
    salary_min: Optional[float] = Query(None, alias="salaryMin", description="Minimum salary filter", ge=0),
    salary_max: Optional[float] = Query(None, alias="salaryMax", description="Maximum salary filter", ge=0),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(None, alias="pageSize", ge=1, le=100, description="Number of results per page")
) -> JobSearchResponse:
    """
    Search for jobs with optional query, filters, and pagination.
    
    The search performs full-text search across title, description, organisation,
    location, summary, profession, and grade fields.
    
    Filters can be applied to narrow down results by specific field values.
    Array filters (professions, grades, assignments, working patterns, work locations)
    support multiple values.
    
    Returns:
        JobSearchResponse containing paginated results and metadata
    """
    settings = get_settings()
    client = get_opensearch_client()
    
    # Use default page size if not specified
    if page_size is None:
        page_size = settings.default_page_size
    
    # Build the search query
    query = build_search_query(
        q=q,
        organisation=organisation,
        professions=professions,
        grades=grades,
        assignments=assignments,
        working_patterns=working_patterns,
        work_locations=work_locations,
        salary_min=salary_min,
        salary_max=salary_max,
    )
    
    # Calculate pagination
    from_index = (page - 1) * page_size
    
    # Execute search
    try:
        response = client.search(
            index=settings.opensearch_index,
            body={
                "query": query,
                "from": from_index,
                "size": page_size,
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
            try:
                results.append(opensearch_hit_to_job_result_item(hit))
            except Exception as e:
                logger.error(f"Failed to map job result: {e}, hit: {hit.get('_source', {}).get('id', 'unknown')}")
                # Skip jobs that fail to map
                continue
        
        # Calculate total pages
        total_pages = math.ceil(total / page_size) if total > 0 else 0
        
        # Build applied filters string
        applied_filters_parts = []
        if organisation:
            applied_filters_parts.append(f"organisation={organisation}")
        if professions:
            applied_filters_parts.append(f"professions={','.join(professions)}")
        if grades:
            applied_filters_parts.append(f"grades={','.join(grades)}")
        if assignments:
            applied_filters_parts.append(f"assignments={','.join(assignments)}")
        if working_patterns:
            applied_filters_parts.append(f"workingPatterns={','.join(working_patterns)}")
        if work_locations:
            applied_filters_parts.append(f"workLocations={','.join(work_locations)}")
        if salary_min is not None:
            applied_filters_parts.append(f"salaryMin={salary_min}")
        if salary_max is not None:
            applied_filters_parts.append(f"salaryMax={salary_max}")
        
        applied_filters = "; ".join(applied_filters_parts) if applied_filters_parts else ""
        
        return JobSearchResponse(**{
            "results": results,
            "total": total,
            "page": page,
            "pageSize": page_size,
            "totalPages": total_pages,
            "query": q or "",
            "appliedFilters": applied_filters,
        })
        
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")
