# Job Search API

A FastAPI-based REST API for searching job listings, designed to work with OpenSearch and integrate seamlessly with the Next.js frontend application ([nextjs_govuk_experiment](https://github.com/Cab-mark/nextjs_govuk_experiment)).

## Overview

This API acts as an interface between the UI and the search engine (OpenSearch). It provides endpoints for:

- Searching jobs with full-text search and filters
- Health check for monitoring

**Note:** This API uses Pydantic models from the [jobs-data-contracts](https://pypi.org/project/jobs-data-contracts/) PyPI package to ensure schema consistency across services.

## Data Contracts

The API uses standardized Pydantic models from the `jobs-data-contracts` package:
- **JobSearchRequest**: Query parameters for job search (filters, pagination, sorting)
- **JobSearchResponse**: Paginated search results with metadata
- **JobResultItem**: Individual job details in search results

This ensures schema alignment with other services in the jobs platform ecosystem.

## Project Structure

```
Job-Search-API/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application entry point
│   ├── config.py            # Settings using Pydantic BaseSettings
│   ├── models.py            # Pydantic models matching TypeScript interface
│   ├── opensearch_client.py # OpenSearch client and index management
│   └── routers/
│       ├── __init__.py
│       └── search.py        # Job search endpoints
├── tests/
│   ├── __init__.py
│   └── test_api.py          # API tests
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── README.md
```

## Quick Start

### Prerequisites

- Docker and Docker Compose
- (Optional) Python 3.11+ for local development without Docker

### Running with Docker Compose

1. **Clone the repository**
   ```bash
   git clone https://github.com/Cab-mark/Job-Search-API.git
   cd Job-Search-API
   ```

2. **Copy environment configuration**
   ```bash
   cp .env.example .env
   ```

3. **Start the services**
   ```bash
   docker-compose up --build
   ```

4. **Verify the API is running**
   - API: http://localhost:8000
   - API Documentation (Swagger): http://localhost:8000/docs
   - API Documentation (ReDoc): http://localhost:8000/redoc
   - OpenSearch: http://localhost:9200

### Running Locally (Development)

1. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Start OpenSearch** (using Docker)
   ```bash
   docker-compose up opensearch -d
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env if needed (default settings work with docker-compose OpenSearch)
   ```

5. **Run the API**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

## Loading Test Data

**Note:** Job creation is now handled by a separate indexer service. This API is read-only for job search.

To manually index test data, use the OpenSearch API directly or the indexer service.

## API Endpoints

### Health Check

```bash
# Check API health
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "healthy",
  "opensearch_connected": true,
  "timestamp": "2025-12-01T16:00:00.000Z"
}
```

### Search Jobs

```bash
# Search all jobs
curl "http://localhost:8000/jobs"

# Search with query
curl "http://localhost:8000/jobs?q=policy"

# Search with filters (single values)
curl "http://localhost:8000/jobs?organisation=Ministry%20of%20Defence"

# Search with array filters (multi-select)
curl "http://localhost:8000/jobs?grades=Grade%207&grades=Grade%206&professions=Digital%20and%20Data"

# Search with salary range
curl "http://localhost:8000/jobs?salaryMin=30000&salaryMax=50000"

# Search with pagination
curl "http://localhost:8000/jobs?page=1&pageSize=20"

# Combined search
curl "http://localhost:8000/jobs?q=developer&grades=Grade%207&page=1&pageSize=10"
```

**Query Parameters:**
- `q` - Full-text search query
- `page` - Page number (1-indexed, default: 1)
- `pageSize` - Results per page (default: 10, max: 100)
- `organisation` - Filter by organisation name
- `professions` - Filter by professions (can specify multiple)
- `grades` - Filter by grades (can specify multiple)
- `assignments` - Filter by assignment types (can specify multiple)
- `workingPatterns` - Filter by working patterns (can specify multiple: "Full-time", "Part-time")
- `workLocations` - Filter by work locations (can specify multiple: "Home based", "Office based")
- `salaryMin` - Minimum salary filter (numeric)
- `salaryMax` - Maximum salary filter (numeric)

Response:
```json
{
  "results": [
    {
      "id": "1567",
      "externalId": "ext-1567",
      "title": "Policy Advisor",
      "organisation": "Ministry of Defence",
      "location": [
        {
          "townName": "Bristol",
          "region": "South West",
          "latitude": 51.4545,
          "longitude": -2.5879
        }
      ],
      "workingPattern": ["Full-time"],
      "assignmentType": "Fixed Term Appointment (FTA)",
      "salary": {
        "minimum": 45000,
        "currency": "GBP",
        "currencySymbol": "£"
      },
      "workLocation": ["Office based"],
      "grade": "Grade 7",
      "dateClosing": "2025-12-20",
      "profession": "Policy",
      "approach": "Internal"
    }
  ],
  "total": 1,
  "page": 1,
  "pageSize": 10,
  "totalPages": 1,
  "query": "",
  "appliedFilters": ""
}
```

## Running Tests

```bash
# Install test dependencies
pip install -r requirements.txt

# Run tests
pytest tests/ -v
```

## Configuration

Environment variables can be set in `.env` or passed directly:

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENSEARCH_HOST` | OpenSearch hostname | `opensearch` |
| `OPENSEARCH_PORT` | OpenSearch port | `9200` |
| `OPENSEARCH_INDEX` | Index name for jobs | `jobs` |
| `OPENSEARCH_USERNAME` | OpenSearch username (optional) | - |
| `OPENSEARCH_PASSWORD` | OpenSearch password (optional) | - |
| `DEFAULT_PAGE_SIZE` | Default results per page | `10` |
| `MAX_PAGE_SIZE` | Maximum results per page | `100` |

## Development Notes

- Security is **disabled** in OpenSearch for local development. Enable security for production deployments.
- CORS is configured to allow all origins. Restrict this in production.
- The API uses async/await patterns for optimal performance.
- All models use Pydantic v2 for validation and serialization.

## Future Deployment

This repository is designed to be deployed to AWS. While cloud infrastructure is not included yet, the application is containerized and ready for:

- AWS ECS/Fargate
- AWS EKS (Kubernetes)
- AWS Lambda with API Gateway (with modifications)
- Amazon OpenSearch Service

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
