"""
Pydantic Models for the Job Search API

These models are designed to match the TypeScript interface for job search results
from the Next.js frontend application (nextjs_govuk_experiment).

TypeScript Interface Reference (source of truth from app/lib/mockJobs.ts):
---------------------------------------------------------------------------
export interface Job {
  id: string;
  title: string;
  description: string;
  organisation: string;
  location: string;
  grade: string;
  assignmentType: string;
  personalSpec: string;
  nationalityRequirement?: string;
  summary?: string;
  applyUrl?: string;
  benefits?: string;
  profession?: string;
  applyDetail?: string;
  salary?: string;
  closingDate?: string;
  jobNumbers?: number;
  contacts: boolean;
  contactName?: string;
  contactEmail?: string;
  contactPhone?: string;
  recruitmentEmail: string;
}
---------------------------------------------------------------------------
"""

from typing import Optional, List, Dict, Union
from pydantic import BaseModel, Field, ConfigDict


class Job(BaseModel):
    """
    Represents a job posting.
    This model matches the TypeScript Job interface exactly from nextjs_govuk_experiment.
    
    All field names are kept identical to the TypeScript interface to ensure
    seamless integration with the Next.js frontend.
    """
    id: str = Field(..., description="Unique job identifier")
    title: str = Field(..., description="Job title")
    description: str = Field(..., description="Full job description")
    organisation: str = Field(..., description="Organisation/department posting the job")
    location: str = Field(..., description="Job location (e.g., 'Birmingham, Leeds, London')")
    grade: str = Field(..., description="Civil service grade (e.g., 'Grade 7', 'Senior Executive Officer')")
    assignmentType: str = Field(..., description="Type of assignment (e.g., 'Permanent', 'Fixed Term Appointment (FTA)')")
    personalSpec: str = Field(..., description="Personal specification requirements")
    nationalityRequirement: Optional[str] = Field(None, description="Nationality requirements for the role")
    summary: Optional[str] = Field(None, description="Brief summary of the role")
    applyUrl: Optional[str] = Field(None, description="URL to apply for the job")
    benefits: Optional[str] = Field(None, description="Benefits offered with the role")
    profession: Optional[str] = Field(None, description="Profession category (e.g., 'Policy')")
    applyDetail: Optional[str] = Field(None, description="Detailed application instructions")
    salary: Optional[str] = Field(None, description="Salary information (e.g., '£45,000')")
    closingDate: Optional[str] = Field(None, description="Application closing date")
    jobNumbers: Optional[int] = Field(None, description="Number of positions available")
    contacts: bool = Field(..., description="Whether contact details are available")
    contactName: Optional[str] = Field(None, description="Contact person name")
    contactEmail: Optional[str] = Field(None, description="Contact email address")
    contactPhone: Optional[str] = Field(None, description="Contact phone number")
    recruitmentEmail: str = Field(..., description="Recruitment team email address")

    # Allow population by field name to maintain TypeScript interface compatibility
    model_config = ConfigDict(populate_by_name=True)


class JobSearchResponse(BaseModel):
    """
    Response model for job search queries.
    Contains paginated results and metadata about the search.
    """
    results: List[Job] = Field(default_factory=list, description="List of job results")
    total: int = Field(..., description="Total number of matching jobs", ge=0)
    page: int = Field(..., description="Current page number", ge=1)
    pageSize: int = Field(..., description="Number of results per page", ge=1)
    totalPages: int = Field(..., description="Total number of pages", ge=0)
    query: Optional[str] = Field(None, description="Search query used")
    appliedFilters: Optional[Dict[str, Union[str, List[str]]]] = Field(
        None, description="Filters applied to search"
    )


class JobCreateRequest(BaseModel):
    """
    Request model for creating a new job posting.
    Similar to Job but without the id field (auto-generated).
    """
    title: str = Field(..., description="Job title")
    description: str = Field(..., description="Full job description")
    organisation: str = Field(..., description="Organisation/department posting the job")
    location: str = Field(..., description="Job location")
    grade: str = Field(..., description="Civil service grade")
    assignmentType: str = Field(..., description="Type of assignment")
    personalSpec: str = Field(..., description="Personal specification requirements")
    nationalityRequirement: Optional[str] = Field(None, description="Nationality requirements")
    summary: Optional[str] = Field(None, description="Brief summary of the role")
    applyUrl: Optional[str] = Field(None, description="URL to apply for the job")
    benefits: Optional[str] = Field(None, description="Benefits offered")
    profession: Optional[str] = Field(None, description="Profession category")
    applyDetail: Optional[str] = Field(None, description="Detailed application instructions")
    salary: Optional[str] = Field(None, description="Salary information")
    closingDate: Optional[str] = Field(None, description="Application closing date")
    jobNumbers: Optional[int] = Field(None, description="Number of positions available")
    contacts: bool = Field(default=False, description="Whether contact details are available")
    contactName: Optional[str] = Field(None, description="Contact person name")
    contactEmail: Optional[str] = Field(None, description="Contact email address")
    contactPhone: Optional[str] = Field(None, description="Contact phone number")
    recruitmentEmail: str = Field(..., description="Recruitment team email address")


class HealthResponse(BaseModel):
    """
    Response model for health check endpoint.
    """
    status: str = Field(..., description="Health status")
    opensearch_connected: bool = Field(..., description="OpenSearch connection status")
    timestamp: str = Field(..., description="Current timestamp (ISO 8601)")
