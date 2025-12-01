"""
Tests for the Job Search API

These tests verify the API endpoints and models work correctly.
Tests use httpx for async HTTP testing with FastAPI's TestClient.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from app.main import app
from app.models import Job, JobSearchResponse, JobCreateRequest, HealthResponse


# Create test client
client = TestClient(app)


class TestHealthEndpoint:
    """Tests for the /health endpoint."""
    
    def test_health_check_returns_status(self):
        """Health endpoint should return a status."""
        with patch('app.main.check_opensearch_connection', return_value=True):
            response = client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert "status" in data
            assert "opensearch_connected" in data
            assert "timestamp" in data
    
    def test_health_check_degraded_when_opensearch_down(self):
        """Health endpoint should report degraded when OpenSearch is down."""
        with patch('app.main.check_opensearch_connection', return_value=False):
            response = client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "degraded"
            assert data["opensearch_connected"] is False


class TestRootEndpoint:
    """Tests for the root / endpoint."""
    
    def test_root_returns_api_info(self):
        """Root endpoint should return API info."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data
        assert "docs" in data


class TestJobModels:
    """Tests for Pydantic models."""
    
    def test_job_model_required_fields(self):
        """Job model should require all mandatory fields."""
        job_data = {
            "id": "123",
            "title": "Policy Advisor",
            "description": "A test job description",
            "organisation": "Ministry of Defence",
            "location": "London",
            "grade": "Grade 7",
            "assignmentType": "Permanent",
            "personalSpec": "Required qualifications",
            "contacts": False,
            "recruitmentEmail": "recruitment@test.gov.uk"
        }
        job = Job(**job_data)
        assert job.id == "123"
        assert job.title == "Policy Advisor"
        assert job.contacts is False
    
    def test_job_model_optional_fields(self):
        """Job model should handle optional fields correctly."""
        job_data = {
            "id": "456",
            "title": "Senior Developer",
            "description": "A senior role",
            "organisation": "HMRC",
            "location": "Newcastle",
            "grade": "Grade 6",
            "assignmentType": "Fixed Term",
            "personalSpec": "Experience required",
            "contacts": True,
            "contactName": "John Smith",
            "contactEmail": "john.smith@test.gov.uk",
            "recruitmentEmail": "recruitment@test.gov.uk",
            "salary": "£55,000",
            "closingDate": "31 December 2025",
            "jobNumbers": 3
        }
        job = Job(**job_data)
        assert job.contactName == "John Smith"
        assert job.salary == "£55,000"
        assert job.jobNumbers == 3
    
    def test_job_search_response_model(self):
        """JobSearchResponse should contain results and pagination."""
        job_data = {
            "id": "789",
            "title": "Test Job",
            "description": "Description",
            "organisation": "Test Org",
            "location": "Test Location",
            "grade": "Grade 7",
            "assignmentType": "Permanent",
            "personalSpec": "Spec",
            "contacts": False,
            "recruitmentEmail": "test@test.gov.uk"
        }
        response = JobSearchResponse(
            results=[Job(**job_data)],
            total=1,
            page=1,
            pageSize=10,
            totalPages=1
        )
        assert len(response.results) == 1
        assert response.total == 1
        assert response.totalPages == 1
    
    def test_job_create_request_model(self):
        """JobCreateRequest should work without id field."""
        create_data = {
            "title": "New Position",
            "description": "A new role",
            "organisation": "Cabinet Office",
            "location": "Whitehall",
            "grade": "SEO",
            "assignmentType": "Permanent",
            "personalSpec": "Requirements",
            "contacts": False,
            "recruitmentEmail": "jobs@cabinet.gov.uk"
        }
        request = JobCreateRequest(**create_data)
        assert request.title == "New Position"
        # Ensure id is not a field on JobCreateRequest
        assert not hasattr(request, 'id') or request.model_fields.get('id') is None


class TestSearchEndpoints:
    """Tests for the /jobs search endpoints."""
    
    @patch('app.routers.search.get_opensearch_client')
    def test_search_jobs_returns_response(self, mock_client):
        """GET /jobs should return JobSearchResponse structure."""
        # Mock OpenSearch response
        mock_client.return_value.search.return_value = {
            "hits": {
                "total": {"value": 1},
                "hits": [
                    {
                        "_source": {
                            "id": "test-123",
                            "title": "Test Job",
                            "description": "Test Description",
                            "organisation": "Test Org",
                            "location": "London",
                            "grade": "Grade 7",
                            "assignmentType": "Permanent",
                            "personalSpec": "Spec",
                            "contacts": False,
                            "recruitmentEmail": "test@test.gov.uk"
                        }
                    }
                ]
            }
        }
        
        response = client.get("/jobs")
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "total" in data
        assert "page" in data
        assert "pageSize" in data
        assert "totalPages" in data
    
    @patch('app.routers.search.get_opensearch_client')
    def test_search_jobs_with_query(self, mock_client):
        """GET /jobs with query parameter should pass query to OpenSearch."""
        mock_client.return_value.search.return_value = {
            "hits": {
                "total": {"value": 0},
                "hits": []
            }
        }
        
        response = client.get("/jobs?q=policy")
        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "policy"
    
    @patch('app.routers.search.get_opensearch_client')
    def test_search_jobs_with_filters(self, mock_client):
        """GET /jobs with filter parameters should apply filters."""
        mock_client.return_value.search.return_value = {
            "hits": {
                "total": {"value": 0},
                "hits": []
            }
        }
        
        response = client.get("/jobs?grade=Grade%207&organisation=HMRC")
        assert response.status_code == 200
        data = response.json()
        assert data["appliedFilters"] is not None
        assert "grade" in data["appliedFilters"]
        assert "organisation" in data["appliedFilters"]
    
    @patch('app.routers.search.get_opensearch_client')
    def test_search_jobs_pagination(self, mock_client):
        """GET /jobs should support pagination parameters."""
        mock_client.return_value.search.return_value = {
            "hits": {
                "total": {"value": 50},
                "hits": []
            }
        }
        
        response = client.get("/jobs?page=2&pageSize=20")
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 2
        assert data["pageSize"] == 20


class TestGetJobById:
    """Tests for the GET /jobs/{id} endpoint."""
    
    @patch('app.routers.search.get_opensearch_client')
    def test_get_job_by_id_found(self, mock_client):
        """GET /jobs/{id} should return job when found."""
        mock_client.return_value.search.return_value = {
            "hits": {
                "hits": [
                    {
                        "_source": {
                            "id": "job-123",
                            "title": "Found Job",
                            "description": "Description",
                            "organisation": "Test Org",
                            "location": "London",
                            "grade": "Grade 7",
                            "assignmentType": "Permanent",
                            "personalSpec": "Spec",
                            "contacts": False,
                            "recruitmentEmail": "test@test.gov.uk"
                        }
                    }
                ]
            }
        }
        
        response = client.get("/jobs/job-123")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "job-123"
        assert data["title"] == "Found Job"
    
    @patch('app.routers.search.get_opensearch_client')
    def test_get_job_by_id_not_found(self, mock_client):
        """GET /jobs/{id} should return 404 when not found."""
        mock_client.return_value.search.return_value = {
            "hits": {
                "hits": []
            }
        }
        
        response = client.get("/jobs/nonexistent")
        assert response.status_code == 404


class TestCreateJob:
    """Tests for the POST /jobs endpoint."""
    
    @patch('app.routers.search.get_opensearch_client')
    def test_create_job_success(self, mock_client):
        """POST /jobs should create a job and return it with generated id."""
        mock_client.return_value.index.return_value = {"result": "created"}
        
        job_data = {
            "title": "New Job",
            "description": "A new position",
            "organisation": "Cabinet Office",
            "location": "London",
            "grade": "Grade 7",
            "assignmentType": "Permanent",
            "personalSpec": "Requirements",
            "contacts": False,
            "recruitmentEmail": "jobs@cabinet.gov.uk"
        }
        
        response = client.post("/jobs", json=job_data)
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["title"] == "New Job"
        assert data["organisation"] == "Cabinet Office"
