# Deployment Guide

## Local Development

### Prerequisites
- Python 3.11+
- PostgreSQL 15+ (or use Docker)
- pip or Poetry

### Quick Start

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Set up environment:**
```bash
# .env file already configured
# Update DATABASE_URL if needed
```

3. **Run the application:**
```bash
# Option 1: Direct execution
python app/main.py

# Option 2: Using uvicorn
python -m uvicorn app.main:app --reload

# Option 3: Using module
python -m app.main
```

4. **Access the API:**
- API Docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

## Docker Deployment

### Using Docker Compose (Recommended)

```bash
# Start all services (API + PostgreSQL)
docker-compose up -d

# View logs
docker-compose logs -f api

# Stop services
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

### Using Docker Standalone

```bash
# Build the image
docker build -t integration-platform-api .

# Run PostgreSQL
docker run -d \
  --name postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=integration_platform \
  -p 5432:5432 \
  postgres:15-alpine

# Run the API
docker run -d \
  --name integration-api \
  --link postgres:db \
  -p 8000:8000 \
  -e DATABASE_URL=postgresql://postgres:postgres@db:5432/integration_platform \
  integration-platform-api
```

## Testing

### Run Tests Locally

```bash
# Install test dependencies
pip install -r requirements-dev.txt

# Run all tests
pytest app/tests/ -v

# Run with coverage
pytest app/tests/ --cov=app --cov-report=html

# Run specific test file
pytest app/tests/test_clients.py -v
```

### Test Results

Current test coverage: **76%**

- ✅ 23 tests passing
- ✅ Health endpoints (4 tests)
- ✅ Client endpoints (13 tests)
- ✅ Security module (6 tests)

## CI/CD with GitHub Actions

The project includes a GitHub Actions workflow that runs on every push and pull request.

### Workflow Steps

1. **Test Job**
   - Sets up Python 3.11
   - Starts PostgreSQL service
   - Runs pytest with coverage
   - Uploads coverage to Codecov

2. **Lint Job**
   - Runs ruff for code quality
   - Runs black for formatting
   - Runs mypy for type checking

3. **Build Job**
   - Builds Docker image
   - Tests the Docker image
   - Caches layers for faster builds

### Triggering CI

```bash
# Push to main or develop
git push origin main

# Create pull request
git checkout -b feature/my-feature
git push origin feature/my-feature
# Then create PR on GitHub
```

## Production Deployment

### Environment Variables

Required environment variables for production:

```bash
# Application
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Database
DATABASE_URL=postgresql://user:password@host:5432/dbname
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20

# Security (IMPORTANT: Change these!)
SECRET_KEY=<generate-32-char-secret>
ENCRYPTION_KEY=<generate-fernet-key>

# External API
EXTERNAL_API_URL=https://api.production.com
EXTERNAL_API_TIMEOUT=30

# CORS
CORS_ORIGINS=https://yourdomain.com
```

### Generate Production Keys

```python
# Generate Fernet encryption key
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())

# Generate secret key
import secrets
print(secrets.token_urlsafe(32))
```

### Cloud Deployment Options

#### Azure

```bash
# Azure Container Apps
az containerapp up \
  --name integration-platform-api \
  --resource-group my-rg \
  --environment my-env \
  --image integration-platform-api:latest \
  --target-port 8000 \
  --ingress external
```

#### AWS

```bash
# AWS Elastic Container Service (ECS)
aws ecs create-service \
  --cluster my-cluster \
  --service-name integration-api \
  --task-definition integration-api:1 \
  --desired-count 2 \
  --launch-type FARGATE
```

#### Google Cloud

```bash
# Google Cloud Run
gcloud run deploy integration-platform-api \
  --image gcr.io/project/integration-platform-api \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

## Health Checks

The application provides multiple health endpoints for monitoring:

### Basic Health
```bash
curl http://localhost:8000/health
```

### Readiness Probe
```bash
# Use for Kubernetes/container orchestration
curl http://localhost:8000/health/ready
```

### Detailed Status
```bash
curl http://localhost:8000/status
```

## Database Migrations

While the app auto-creates tables on startup, for production use Alembic:

```bash
# Initialize Alembic (already configured)
alembic init alembic

# Create migration
alembic revision --autogenerate -m "Initial migration"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Monitoring

### Structured Logging

Logs are output in JSON format in production:

```json
{
  "timestamp": "2024-01-01T00:00:00",
  "level": "info",
  "event": "request_received",
  "request_id": "uuid-here",
  "method": "POST",
  "path": "/api/v1/clients",
  "app_name": "Integration Platform API",
  "environment": "production"
}
```

### Metrics Endpoints

- `/status` - Application metrics
- `/health/ready` - Readiness status
- Database connection pooling stats in logs

## Troubleshooting

### Common Issues

**Database connection failed:**
```bash
# Check PostgreSQL is running
docker-compose ps

# Check DATABASE_URL is correct
echo $DATABASE_URL
```

**Import errors:**
```bash
# Ensure you're in the project root
cd /path/to/integration-platform-api

# Run with module syntax
python -m uvicorn app.main:app --reload
```

**Tests failing:**
```bash
# Clean test database
rm test.db

# Reinstall dependencies
pip install -r requirements-dev.txt
```

## Security Best Practices

1. **Never commit `.env` file**
2. **Rotate encryption keys regularly**
3. **Use HTTPS in production**
4. **Enable rate limiting**
5. **Implement authentication for `/clients/{id}/credentials` endpoint**
6. **Keep dependencies updated**

## Performance Tuning

### Database Connection Pooling

```python
# In .env
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20
```

### Async Workers

```bash
# Run with multiple workers
uvicorn app.main:app \
  --workers 4 \
  --host 0.0.0.0 \
  --port 8000
```

### Caching

Consider adding Redis for:
- API response caching
- Rate limiting
- Session storage
