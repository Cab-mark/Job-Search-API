# Job Search API

A FastAPI-based REST API for searching job listings, designed to work with OpenSearch and integrate seamlessly with the Next.js frontend application ([nextjs_govuk_experiment](https://github.com/Cab-mark/nextjs_govuk_experiment)).

## Overview

This API acts as an interface between the UI and the search engine (OpenSearch). It provides endpoints for:

- Searching jobs with full-text search and filters
- Retrieving individual job details by ID
- Creating new job postings (for development/testing)

## TypeScript Interface Alignment

The Pydantic models in this API are designed to match exactly the TypeScript `Job` interface from the Next.js frontend:

```typescript
// From nextjs_govuk_experiment/app/lib/mockJobs.ts
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
```

All API responses serialize exactly to this interface shape, ensuring seamless integration.

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

You can load test data using the POST /jobs endpoint:

```bash
# Create a sample job
curl -X POST http://localhost:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Policy Advisor",
    "description": "This is a fantastic job for a policy professional...",
    "organisation": "Ministry of Defence",
    "location": "3 Glass Wharf, Bristol, BS2 OEL",
    "grade": "Grade 7",
    "assignmentType": "Fixed Term Appointment (FTA)",
    "personalSpec": "Some personal specification text",
    "contacts": false,
    "recruitmentEmail": "recruitment@civilservice.gov.uk",
    "salary": "£45,000",
    "closingDate": "20 December 2025"
  }'
```

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

# Search with filters
curl "http://localhost:8000/jobs?grade=Grade%207&organisation=Ministry%20of%20Defence"

# Search with pagination
curl "http://localhost:8000/jobs?page=1&pageSize=20"

# Combined search
curl "http://localhost:8000/jobs?q=developer&grade=Grade%207&page=1&pageSize=10"
```

Response:
```json
{
  "results": [
    {
      "id": "1567",
      "title": "Policy Advisor",
      "description": "This is a fantastic job...",
      "organisation": "Ministry of Defence",
      "location": "3 Glass Wharf, Bristol, BS2 OEL",
      "grade": "Grade 7",
      "assignmentType": "Fixed Term Appointment (FTA)",
      "personalSpec": "Some personal specification text",
      "contacts": false,
      "recruitmentEmail": "recruitment@civilservice.gov.uk",
      "salary": "£45,000",
      "closingDate": "20 December 2025"
    }
  ],
  "total": 1,
  "page": 1,
  "pageSize": 10,
  "totalPages": 1,
  "query": null,
  "appliedFilters": null
}
```

### Get Job by ID

```bash
curl http://localhost:8000/jobs/1567
```

### Create Job

```bash
curl -X POST http://localhost:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Senior Developer",
    "description": "Join our team...",
    "organisation": "HMRC",
    "location": "Newcastle upon Tyne",
    "grade": "Grade 6",
    "assignmentType": "Permanent",
    "personalSpec": "Required experience...",
    "contacts": true,
    "contactName": "Jane Doe",
    "contactEmail": "jane.doe@hmrc.gov.uk",
    "recruitmentEmail": "recruitment@hmrc.gov.uk",
    "salary": "£55,000 - £65,000",
    "closingDate": "15 January 2026",
    "jobNumbers": 3
  }'
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

[Add your license here]
