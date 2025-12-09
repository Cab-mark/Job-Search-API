"""
Tests for the Job Search API

These tests verify the API endpoints and models work correctly.
Tests use httpx for async HTTP testing with FastAPI's TestClient.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from app.main import app
from app.models import HealthResponse

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


class TestSearchEndpoints:
    """Tests for the /jobs search endpoints."""
    
    @patch('app.routers.search.get_opensearch_client')
    def test_search_jobs_returns_response(self, mock_client):
        """GET /jobs should return JobSearchResponse structure."""
        # Mock OpenSearch response with data matching JobResultItem structure
        mock_client.return_value.search.return_value = {
            "hits": {
                "total": {"value": 1},
                "hits": [
                    {
                        "_source": {
                            "id": "test-123",
                            "externalId": "ext-123",
                            "title": "Test Job",
                            "organisation": "Test Org",
                            "location": [
                                {
                                    "townName": "London",
                                    "region": "London",
                                    "latitude": 51.5074,
                                    "longitude": -0.1278
                                }
                            ],
                            "workingPattern": ["Full-time"],
                            "assignmentType": "Permanent",
                            "salary": {
                                "minimum": 45000,
                                "currency": "GBP",
                                "currencySymbol": "£"
                            },
                            "workLocation": ["Office based"],
                            "grade": "Grade 7",
                            "closingDate": "2025-12-31",
                            "profession": "Digital and Data",
                            "approach": "Internal"
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
        assert "query" in data
        assert "appliedFilters" in data
    
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
        
        response = client.get("/jobs?grades=Grade%207&organisation=HMRC")
        assert response.status_code == 200
        data = response.json()
        assert data["appliedFilters"] is not None
        assert "Grade 7" in data["appliedFilters"] or "grades" in data["appliedFilters"]
    
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
    
    @patch('app.routers.search.get_opensearch_client')
    def test_search_jobs_with_array_filters(self, mock_client):
        """GET /jobs should support array filters for professions, grades, etc."""
        mock_client.return_value.search.return_value = {
            "hits": {
                "total": {"value": 0},
                "hits": []
            }
        }
        
        response = client.get("/jobs?professions=Digital%20and%20Data&professions=Policy&grades=Grade%207")
        assert response.status_code == 200
        data = response.json()
        assert data["appliedFilters"] is not None
    
    @patch('app.routers.search.get_opensearch_client')
    def test_search_jobs_with_salary_range(self, mock_client):
        """GET /jobs should support salary range filters."""
        mock_client.return_value.search.return_value = {
            "hits": {
                "total": {"value": 0},
                "hits": []
            }
        }
        
        response = client.get("/jobs?salaryMin=30000&salaryMax=50000")
        assert response.status_code == 200
        data = response.json()
        assert data["appliedFilters"] is not None
        assert "salaryMin" in data["appliedFilters"]
        assert "salaryMax" in data["appliedFilters"]
