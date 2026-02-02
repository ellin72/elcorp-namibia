# Deployment & Operations Guide

**Version**: 1.0  
**Target Environment**: Production  
**Deployment Platforms**: Docker, Railway/Render, Supabase, AWS ECS

---

## Table of Contents

1. [Local Development Setup](#local-development-setup)
2. [Docker & Containerization](#docker--containerization)
3. [Database Deployment](#database-deployment)
4. [CI/CD Pipeline](#cicd-pipeline)
5. [Production Deployment](#production-deployment)
6. [Monitoring & Observability](#monitoring--observability)
7. [Operations Runbooks](#operations-runbooks)
8. [Disaster Recovery](#disaster-recovery)

---

## Local Development Setup

### Prerequisites

```bash
# System requirements
- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Docker Desktop (optional, for containers)
- Node.js 18+ (for frontend)
```

### 1. Clone & Environment

```bash
git clone https://github.com/ellin72/elcorp-namibia.git
cd elcorp-namibia

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Create .env file
cp .env.example .env

# Edit .env with local values
FLASK_ENV=development
SECRET_KEY=dev-change-in-production
DATABASE_URL=postgresql://elcorp:password@localhost:5432/elcorp_dev
REDIS_URL=redis://localhost:6379/0
```

### 2. Install Dependencies

```bash
pip install -r backend/requirements.txt

# Optional: Install development tools
pip install black flake8 mypy pytest-cov
```

### 3. Database Initialization

```bash
# Create database
createdb elcorp_dev

# Run migrations
cd backend
alembic upgrade head

# Seed initial roles
python scripts/seed_roles.py

# Create admin user
python scripts/create_admin.py
```

### 4. Run Application

```bash
# Start backend
cd backend
flask run --port 8000

# In another terminal, start frontend
cd frontend
npm install
npm run dev

# In another terminal, start Celery worker (optional)
celery -A src.elcorp.jobs.celery_app worker --loglevel=info

# Start Celery beat (for scheduled tasks)
celery -A src.elcorp.jobs.celery_app beat --loglevel=info
```

### 5. Verify Setup

```bash
# Test backend
curl http://localhost:8000/health

# Test frontend
open http://localhost:5173

# Test API
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"..."}'
```

---

## Docker & Containerization

### Backend Dockerfile

```dockerfile
# backend/Dockerfile

FROM python:3.11-slim as base

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Set Python flags
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src ./src
COPY migrations ./migrations
COPY wsgi.py .

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# Run with gunicorn
CMD ["gunicorn", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "4", \
     "--worker-class", "sync", \
     "--timeout", "120", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "--log-level", "info", \
     "wsgi:app"]
```

### Frontend Dockerfile

```dockerfile
# frontend/Dockerfile

FROM node:18-alpine as builder

WORKDIR /app

# Copy package files
COPY package.json package-lock.json ./

# Install dependencies
RUN npm ci

# Copy source
COPY . .

# Build
RUN npm run build

# Production image
FROM node:18-alpine

WORKDIR /app

# Install serve to run the app
RUN npm install -g serve

# Copy built assets from builder
COPY --from=builder /app/dist ./dist

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost:3000 || exit 1

# Expose port
EXPOSE 3000

# Run
CMD ["serve", "-s", "dist", "-l", "3000"]
```

### Docker Compose

```yaml
# docker-compose.yml

version: '3.9'

services:
  # PostgreSQL Database
  postgres:
    image: postgres:15-alpine
    container_name: elcorp_postgres
    environment:
      POSTGRES_DB: elcorp
      POSTGRES_USER: elcorp
      POSTGRES_PASSWORD: ${DB_PASSWORD:-dev_password}
      PGDATA: /var/lib/postgresql/data/pgdata
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/init_db.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U elcorp"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - elcorp_network

  # Redis Cache
  redis:
    image: redis:7-alpine
    container_name: elcorp_redis
    command: redis-server --requirepass ${REDIS_PASSWORD:-redis_password}
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - elcorp_network

  # Flask Backend
  backend:
    build:
      context: .
      dockerfile: backend/Dockerfile
    container_name: elcorp_backend
    ports:
      - "8000:8000"
    environment:
      FLASK_APP: wsgi.py
      FLASK_ENV: ${FLASK_ENV:-development}
      DATABASE_URL: postgresql://elcorp:${DB_PASSWORD:-dev_password}@postgres:5432/elcorp
      REDIS_URL: redis://:${REDIS_PASSWORD:-redis_password}@redis:6379/0
      SECRET_KEY: ${SECRET_KEY}
      JWT_SECRET: ${JWT_SECRET}
    volumes:
      - ./backend:/app/backend
      - ./logs:/app/logs
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - elcorp_network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # React Frontend
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: elcorp_frontend
    ports:
      - "3000:3000"
    environment:
      VITE_API_URL: http://backend:8000/api/v1
    depends_on:
      - backend
    networks:
      - elcorp_network

  # Celery Worker
  celery_worker:
    build:
      context: .
      dockerfile: backend/Dockerfile
    container_name: elcorp_celery_worker
    command: celery -A src.elcorp.jobs.celery_app worker --loglevel=info
    environment:
      FLASK_APP: wsgi.py
      FLASK_ENV: ${FLASK_ENV:-development}
      DATABASE_URL: postgresql://elcorp:${DB_PASSWORD:-dev_password}@postgres:5432/elcorp
      REDIS_URL: redis://:${REDIS_PASSWORD:-redis_password}@redis:6379/0
    depends_on:
      - postgres
      - redis
    networks:
      - elcorp_network
    restart: always

  # Celery Beat (Scheduled Tasks)
  celery_beat:
    build:
      context: .
      dockerfile: backend/Dockerfile
    container_name: elcorp_celery_beat
    command: celery -A src.elcorp.jobs.celery_app beat --loglevel=info
    environment:
      FLASK_APP: wsgi.py
      FLASK_ENV: ${FLASK_ENV:-development}
      DATABASE_URL: postgresql://elcorp:${DB_PASSWORD:-dev_password}@postgres:5432/elcorp
      REDIS_URL: redis://:${REDIS_PASSWORD:-redis_password}@redis:6379/0
    depends_on:
      - postgres
      - redis
    networks:
      - elcorp_network
    restart: always

volumes:
  postgres_data:
    driver: local
  redis_data:
    driver: local

networks:
  elcorp_network:
    driver: bridge
```

### Build & Run

```bash
# Build images
docker-compose build

# Start services
docker-compose up -d

# View logs
docker-compose logs -f backend

# Stop services
docker-compose down

# Clean up (remove volumes)
docker-compose down -v
```

---

## Database Deployment

### PostgreSQL Setup (Supabase or Self-Hosted)

#### Supabase (Recommended for MVP)

```bash
# 1. Create Supabase project
# https://app.supabase.com

# 2. Get connection string
# Settings → Database → Connection String → PostgreSQL

# 3. Update .env
DATABASE_URL=postgresql://postgres:password@db.supabasedb.co:5432/postgres

# 4. Run migrations
cd backend
alembic upgrade head

# 5. Seed data
python scripts/seed_roles.py
```

#### Self-Hosted PostgreSQL (AWS RDS / Digital Ocean)

```bash
# Create RDS instance
aws rds create-db-instance \
  --db-instance-identifier elcorp-prod \
  --db-instance-class db.t4g.micro \
  --engine postgres \
  --engine-version 15.4 \
  --master-username postgres \
  --master-user-password "${DB_PASSWORD}" \
  --allocated-storage 100 \
  --storage-type gp3 \
  --publicly-accessible false \
  --vpc-security-group-ids sg-xxxxx

# Get endpoint
aws rds describe-db-instances --db-instance-identifier elcorp-prod

# Connect and run migrations
psql -h elcorp-prod.xxxxx.amazonaws.com -U postgres
CREATE DATABASE elcorp;

# From Python
alembic upgrade head
```

### Database Backup Strategy

```bash
# scripts/backup_database.sh

#!/bin/bash

BACKUP_DIR="/backups/elcorp"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/elcorp_$TIMESTAMP.sql.gz"

# Create backup
pg_dump "$DATABASE_URL" | gzip > "$BACKUP_FILE"

# Upload to S3
aws s3 cp "$BACKUP_FILE" "s3://elcorp-backups/database/"

# Keep only last 30 days
find "$BACKUP_DIR" -type f -mtime +30 -delete

echo "Backup completed: $BACKUP_FILE"
```

### Automated Backups (RDS)

```bash
# Enable automated backups
aws rds modify-db-instance \
  --db-instance-identifier elcorp-prod \
  --backup-retention-period 30 \
  --preferred-backup-window "03:00-04:00" \
  --apply-immediately

# Test restore
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier elcorp-prod-restore \
  --db-snapshot-identifier elcorp-prod-snapshot
```

---

## CI/CD Pipeline

### GitHub Actions Workflow

```yaml
# .github/workflows/ci.yml

name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15-alpine
        env:
          POSTGRES_DB: elcorp_test
          POSTGRES_USER: elcorp
          POSTGRES_PASSWORD: testpass
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

      redis:
        image: redis:7-alpine
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 6379:6379

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r backend/requirements.txt
          pip install pytest pytest-cov black flake8 mypy

      - name: Lint with Black
        run: black --check backend/

      - name: Lint with flake8
        run: flake8 backend/ --max-line-length=100

      - name: Type check with mypy
        run: mypy backend/ --ignore-missing-imports
        continue-on-error: true

      - name: Run tests
        run: |
          cd backend
          pytest tests/ --cov=src/elcorp --cov-report=xml --cov-report=html
        env:
          DATABASE_URL: postgresql://elcorp:testpass@localhost:5432/elcorp_test
          REDIS_URL: redis://localhost:6379/0
          FLASK_ENV: testing

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./backend/coverage.xml
          flags: unittests
          fail_ci_if_error: true

      - name: SCA - Check dependencies
        run: |
          pip install safety
          safety check --json > safety-report.json
        continue-on-error: true

      - name: SAST - Bandit scan
        run: |
          pip install bandit
          bandit -r backend/src/ -f json -o bandit-report.json
        continue-on-error: true

  build:
    needs: test
    runs-on: ubuntu-latest
    if: github.event_name == 'push'

    steps:
      - uses: actions/checkout@v3

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v2

      - name: Login to GHCR
        uses: docker/login-action@v2
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build and push backend
        uses: docker/build-push-action@v4
        with:
          context: .
          file: ./backend/Dockerfile
          push: true
          tags: |
            ghcr.io/${{ github.repository }}/backend:latest
            ghcr.io/${{ github.repository }}/backend:${{ github.sha }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

      - name: Build and push frontend
        uses: docker/build-push-action@v4
        with:
          context: ./frontend
          file: ./frontend/Dockerfile
          push: true
          tags: |
            ghcr.io/${{ github.repository }}/frontend:latest
            ghcr.io/${{ github.repository }}/frontend:${{ github.sha }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

### Deployment Workflow

```yaml
# .github/workflows/deploy.yml

name: Deploy to Production

on:
  push:
    branches: [main]
  workflow_dispatch:

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3

      - name: Deploy to Railway (Backend)
        run: |
          npm install -g @railway/cli
          railway up \
            --service backend \
            --environment production
        env:
          RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}

      - name: Deploy to Vercel (Frontend)
        run: |
          npm install -g vercel
          vercel deploy \
            --prod \
            --token ${{ secrets.VERCEL_TOKEN }}

      - name: Database migrations
        run: |
          ssh -i ${{ secrets.DEPLOY_KEY }} ubuntu@${{ secrets.PROD_SERVER }} \
            "cd /app && alembic upgrade head"

      - name: Run smoke tests
        run: |
          bash scripts/smoke_tests.sh
        env:
          API_URL: https://api.elcorp.na

      - name: Notify Slack
        uses: 8398a7/action-slack@v3
        with:
          status: ${{ job.status }}
          webhook_url: ${{ secrets.SLACK_WEBHOOK }}
          text: 'Deployment to production: ${{ job.status }}'
        if: always()
```

---

## Production Deployment

### Railway.app (Recommended)

```bash
# 1. Install Railway CLI
npm install -g @railway/cli

# 2. Login
railway login

# 3. Create project
railway init

# 4. Add services
railway service add postgres
railway service add redis

# 5. Configure environment
railway variable add DATABASE_URL=postgresql://...
railway variable add REDIS_URL=redis://...
railway variable add SECRET_KEY=...

# 6. Deploy backend
railway up --service backend

# 7. Deploy frontend (or use Vercel)
railway up --service frontend
```

### Render.com

```bash
# 1. Connect GitHub repository
# https://dashboard.render.com

# 2. Create Web Service
# - Name: elcorp-backend
# - Build command: pip install -r requirements.txt
# - Start command: gunicorn wsgi:app

# 3. Add environment variables
# - DATABASE_URL=postgresql://...
# - REDIS_URL=redis://...

# 4. Deploy
# Renders automatically on push to main
```

### AWS ECS (More Complex)

```bash
# 1. Create ECR repository
aws ecr create-repository --repository-name elcorp-backend

# 2. Push image
docker build -t elcorp-backend:latest backend/
docker tag elcorp-backend:latest ${AWS_ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/elcorp-backend:latest
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com
docker push ${AWS_ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/elcorp-backend:latest

# 3. Create ECS cluster
aws ecs create-cluster --cluster-name elcorp-production

# 4. Register task definition
aws ecs register-task-definition --cli-input-json file://task-definition.json

# 5. Create service
aws ecs create-service \
  --cluster elcorp-production \
  --service-name elcorp-backend \
  --task-definition elcorp-backend \
  --desired-count 3 \
  --launch-type FARGATE

# 6. Setup load balancer (ALB)
aws elbv2 create-load-balancer --name elcorp-alb --subnets subnet-1 subnet-2
```

---

## Monitoring & Observability

### Prometheus Metrics

```python
# backend/src/elcorp/shared/infrastructure/monitoring.py

from prometheus_client import Counter, Histogram, Gauge
import time

# Metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration',
    ['method', 'endpoint']
)

database_connections = Gauge(
    'database_connections',
    'Active database connections'
)

cache_hits = Counter(
    'cache_hits_total',
    'Cache hits',
    ['cache_name']
)

# Flask middleware
from flask import request, g

@app.before_request
def before_request():
    g.start_time = time.time()

@app.after_request
def after_request(response):
    duration = time.time() - g.start_time
    http_requests_total.labels(
        method=request.method,
        endpoint=request.endpoint or 'unknown',
        status=response.status_code
    ).inc()
    http_request_duration.labels(
        method=request.method,
        endpoint=request.endpoint or 'unknown'
    ).observe(duration)
    return response

# Expose metrics endpoint
from prometheus_client import generate_latest
@app.route("/metrics", methods=["GET"])
def metrics():
    return generate_latest()
```

### Sentry Error Tracking

```python
# backend/src/elcorp/main.py

import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
from sentry_sdk.integrations.celery import CeleryIntegration

sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    integrations=[
        FlaskIntegration(),
        CeleryIntegration(),
    ],
    traces_sample_rate=0.1,
    environment=os.getenv("FLASK_ENV"),
    release=os.getenv("APP_VERSION"),
)

# Errors automatically captured
```

### Structured Logging

```python
# backend/src/elcorp/shared/util/logger.py

import logging
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    """Format logs as JSON for aggregation."""
    
    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)

# Usage
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logger.addHandler(handler)

logger.info("User login", extra={"user_id": 123, "ip": "192.168.1.1"})
```

### Log Aggregation (ELK / Datadog)

```yaml
# fluentd/fluent.conf - Collect logs from containers

<source>
  @type tail
  path /var/log/elcorp/*.log
  pos_file /var/log/fluentd-containers.log.pos
  tag docker.*
  <parse>
    @type json
    time_format %Y-%m-%dT%H:%M:%S.%NZ
  </parse>
</source>

<match docker.**>
  @type elasticsearch
  @id output_elasticsearch
  @log_level info
  include_tag_key true
  host "#{ENV['FLUENT_ELASTICSEARCH_HOST']}"
  port "#{ENV['FLUENT_ELASTICSEARCH_PORT']}"
  path "#{ENV['FLUENT_ELASTICSEARCH_PATH']}"
  logstash_format true
  logstash_prefix elcorp
  include_timestamp false
  <buffer>
    @type file
    path /var/log/fluentd-buffers/elasticsearch.system.buffer
    flush_mode interval
    retry_type exponential_backoff
    flush_interval 1s
  </buffer>
</match>
```

---

## Operations Runbooks

### Incident Response

#### Scenario: Database Connection Pool Exhausted

```bash
# 1. Check database connections
SELECT count(*) FROM pg_stat_activity;

# 2. Check active connections by user
SELECT usename, count(*) FROM pg_stat_activity GROUP BY usename;

# 3. Kill idle connections
SELECT pg_terminate_backend(pid) 
FROM pg_stat_activity 
WHERE state = 'idle' AND query_start < now() - interval '10 minutes';

# 4. Restart Flask backend service
docker-compose restart backend

# 5. Monitor recovery
curl http://localhost:8000/health
```

#### Scenario: High Memory Usage

```bash
# 1. Check container memory
docker stats

# 2. Increase memory limit in docker-compose
# Change: mem_limit: 2g

# 3. Identify memory leak in Python
pip install memory_profiler
python -m memory_profiler backend/src/elcorp/main.py

# 4. Check for unclosed DB connections
# Ensure connection pooling is configured:
SQLALCHEMY_ENGINE_OPTIONS = {
    "pool_pre_ping": True,
    "pool_size": 10,
    "pool_recycle": 3600,
}
```

#### Scenario: Slow API Responses

```bash
# 1. Check slow query log
SELECT query, mean_time FROM pg_stat_statements 
ORDER BY mean_time DESC LIMIT 10;

# 2. Add missing indexes
CREATE INDEX idx_service_request_status_date 
ON service_request(status, created_at DESC);

# 3. Profile Flask endpoint
from flask_debugtoolbar import DebugToolbarExtension
toolbar = DebugToolbarExtension(app)

# 4. Check Redis cache hit rate
redis-cli INFO stats | grep hits

# 5. Increase cache TTL for frequently accessed data
```

---

## Disaster Recovery

### Recovery Time Objective (RTO): < 4 hours
### Recovery Point Objective (RPO): < 1 hour

### Backup Schedule

```bash
# Daily database backups
0 3 * * * /scripts/backup_database.sh  # 3 AM daily

# Weekly full backups
0 2 * * 0 /scripts/backup_full.sh      # Sunday 2 AM

# Upload to S3
0 4 * * * aws s3 sync /backups s3://elcorp-backups/

# Test restore weekly
0 5 * * 0 /scripts/test_restore.sh     # Sunday 5 AM
```

### Restore Procedure

```bash
# 1. List available backups
aws s3 ls s3://elcorp-backups/database/

# 2. Download backup
aws s3 cp s3://elcorp-backups/database/elcorp_20260201_030000.sql.gz .

# 3. Decompress
gunzip elcorp_20260201_030000.sql.gz

# 4. Drop current database
dropdb elcorp

# 5. Restore from backup
createdb elcorp
psql elcorp < elcorp_20260201_030000.sql

# 6. Verify
psql -d elcorp -c "SELECT COUNT(*) FROM \"user\";"

# 7. Run migrations (in case new ones were added)
alembic upgrade head
```

### Database Failover (Multi-Region)

```bash
# 1. Setup read replica (AWS RDS)
aws rds create-db-instance-read-replica \
  --db-instance-identifier elcorp-prod-replica \
  --source-db-instance-identifier elcorp-prod \
  --availability-zone us-west-2a

# 2. Monitor replication lag
aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS \
  --metric-name AuroraBinlogReplicaLag \
  --dimensions Name=DBClusterIdentifier,Value=elcorp-prod \
  --start-time 2026-02-01T00:00:00Z \
  --end-time 2026-02-02T00:00:00Z \
  --period 300 \
  --statistics Average

# 3. Promote replica on disaster
aws rds promote-read-replica --db-instance-identifier elcorp-prod-replica

# 4. Update connection string
# Update DATABASE_URL in production environment
```

---

## Production Checklist

- [ ] Database automated backups configured
- [ ] Prometheus metrics exported
- [ ] Sentry error tracking enabled
- [ ] Log aggregation (ELK/Datadog) set up
- [ ] SSL/TLS certificates issued (Let's Encrypt)
- [ ] CDN configured (CloudFront/Cloudflare)
- [ ] Rate limiting enabled
- [ ] WAF rules deployed
- [ ] Security headers configured
- [ ] CORS properly restricted
- [ ] Secrets managed (environment variables only)
- [ ] Audit logging tested
- [ ] Disaster recovery tested
- [ ] Load testing completed (1000+ concurrent users)
- [ ] Security audit completed
- [ ] Compliance checklist passed
- [ ] On-call runbooks documented
- [ ] Incident response plan in place

---

**Document Version**: 1.0  
**Last Updated**: February 2, 2026
