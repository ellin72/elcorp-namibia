# Operations & Reliability Guide

Comprehensive guide for production operations, monitoring, SLA management, and disaster recovery.

## Table of Contents

1. [Background Processing](#background-processing)
2. [SLA Management](#sla-management)
3. [Monitoring & Observability](#monitoring--observability)
4. [Backup & Disaster Recovery](#backup--disaster-recovery)
5. [Security Hardening](#security-hardening)
6. [Troubleshooting](#troubleshooting)

---

## Background Processing

### Architecture

The system uses **Celery** with **Redis** broker for async task processing:

```
Request → Flask App → Task Queue (Redis) → Celery Workers → Database
                                         ↓
                                    Retry Logic
                                    Dead Letter Queue
```

### Task Types

**Email Queue** (`email`)

- Send notifications
- Password reset emails
- Status update emails
- Max retries: 3, Retry delay: 60s exponential backoff

**Report Queue** (`reports`)

- Generate analytics reports
- PDF generation
- File compression
- Max retries: 3, Retry delay: 300s

**Export Queue** (`exports`)

- CSV/PDF export generation
- Large data processing
- Background job for UI
- Max retries: 2, Retry delay: 300s

**Analytics Queue** (`analytics`)

- SLA breach checks (every 5 minutes)
- Trend calculations
- Performance metrics
- Max retries: 1

**Backup Queue** (`backup`)

- Database backups (nightly)
- Encrypted storage
- Cleanup old backups
- Max retries: 2, Retry delay: 300s

**Default Queue** (`default`)

- Audit log persistence
- Health checks
- Other async operations
- Max retries: 3

### Running Workers

**Docker Compose** (Recommended)

```bash
docker-compose -f docker-compose.production.yml up -d celery_worker_default celery_worker_email celery_beat
```

**Manual Start** (Development)

```bash
# Default worker
celery -A app.celery_app worker --queues=default --concurrency=4 --loglevel=info

# Email worker
celery -A app.celery_app worker --queues=email --concurrency=2 --loglevel=info

# Beat scheduler (periodic tasks)
celery -A app.celery_app beat --loglevel=info
```

### Task Monitoring

**Check queued tasks:**

```bash
celery -A app.celery_app inspect active
celery -A app.celery_app inspect scheduled
celery -A app.celery_app inspect reserved
```

**Purge queue** (careful!):

```bash
celery -A app.celery_app purge
```

**Monitor in real-time:**

```bash
pip install flower
celery -A app.celery_app events --broker=redis://localhost:6379/0
```

### Retry Logic

Tasks automatically retry on failure with exponential backoff:

```python
# Example: Email task retry
Attempt 1: Fails → Wait 60s → Retry
Attempt 2: Fails → Wait 120s → Retry  
Attempt 3: Fails → Wait 240s → Retry
Attempt 4: Fails → Move to Dead Letter Queue
```

**Dead Letter Queue (DLQ):**

- Failed tasks moved after max retries
- Monitored for manual intervention
- Must be processed manually or task will be lost

---

## SLA Management

### SLA Definitions

Define SLA targets per category and priority:

```python
# Example: Hardware SLA
SLADefinition(
    category='hardware',
    priority='high',
    response_time_hours=2,      # Must acknowledge within 2 hours
    resolution_time_hours=8,    # Must resolve within 8 hours
    is_active=True
)

# Example: Software SLA
SLADefinition(
    category='software',
    priority='medium',
    response_time_hours=4,
    resolution_time_hours=24,
    is_active=True
)
```

**Create SLA via API** (Admin only):

```bash
curl -X POST http://localhost:5000/api/v1/sla/definitions \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "category": "network",
    "priority": "high",
    "response_time_hours": 1,
    "resolution_time_hours": 4
  }'
```

### SLA Breach Detection

**Automatic Detection** (Every 5 minutes)

```python
# Scheduled task: check_sla_breaches
breaches = SLAService.check_all_breaches()
# Returns: [
#   {
#     'request_id': 123,
#     'title': 'Critical System Down',
#     'priority': 'high',
#     'breaches': [
#       {'type': 'response', 'hours_overdue': 0.5},
#       {'type': 'resolution', 'hours_overdue': 2.3}
#     ]
#   }
# ]
```

**Manual Check:**

```bash
# Get SLA metrics for request
GET /api/v1/service-requests/123/sla-metrics

# Response:
{
  "sla_metrics": [
    {
      "status": "in_progress",
      "response_sla_met": true,
      "resolution_sla_met": false,
      "is_breached": true,
      "breach_type": "resolution"
    }
  ]
}
```

### SLA Exemptions

Grant exemptions when breaches are unavoidable:

```python
# Example: Customer blocking issue
SLAService.grant_exemption(
    request_id=123,
    reason="Waiting for customer to provide access credentials",
    exemption_type='resolution',  # 'response', 'resolution', or 'both'
    duration_hours=24,             # NULL = indefinite
    granted_by_id=admin_user.id
)
```

**View Active Exemptions:**

```bash
GET /api/v1/service-requests/123/sla-exemptions
```

### SLA Metrics & Reporting

**Get breach statistics** (last 30 days):

```bash
GET /api/v1/analytics/sla-statistics?days=30

# Response:
{
  "total_breaches": 5,
  "response_breaches": 2,
  "resolution_breaches": 3,
  "breaches_by_priority": {
    "high": 3,
    "medium": 2
  }
}
```

**Admin Dashboard SLA Widget:**

```bash
GET /api/dashboard/admin/sla-breaches?page=1&per_page=10
```

---

## Monitoring & Observability

### Health Check Endpoint

**Endpoint:** `GET /health`

**Response:**

```json
{
  "status": "healthy",
  "timestamp": "2026-01-26T10:30:00",
  "components": {
    "database": "healthy",
    "celery": "healthy",
    "redis": "healthy"
  },
  "version": "1.0.0",
  "environment": "production"
}
```

**Status Codes:**

- `200 OK` - All systems healthy
- `503 Service Unavailable` - One or more components down
- Database must be healthy; Celery/Redis can be degraded

**Docker Health Check:**

```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD curl -f http://localhost:5000/health || exit 1
```

### Prometheus Metrics

**Endpoint:** `GET /metrics`

Returns Prometheus-format metrics for monitoring:

```
# HTTP Metrics
app_requests_total{method="GET",endpoint="/api/dashboard/admin/summary",status="200"} 1250
app_request_duration_seconds_bucket{method="GET",endpoint="/api/dashboard/...",le="0.1"} 800

# Business Metrics
service_requests_created_total{category="hardware",priority="high"} 145
service_requests_completed_total{category="hardware",priority="high"} 132
service_requests_active{category="hardware",priority="high",status="open"} 13
sla_breaches_total{category="hardware",priority="high",breach_type="resolution"} 5

# Celery Metrics
celery_tasks_total{task_name="send_email_async",status="success"} 2540
celery_task_duration_seconds_bucket{task_name="persist_audit_log",le="0.1"} 45678

# Error Metrics
app_errors_total{error_type="database_error",severity="error"} 12
auth_failures_total{method="password",reason="invalid_credentials"} 23
auth_failed{method="2fa",reason="timeout"} 5
```

### Grafana Dashboards

Pre-built dashboards available in `/monitoring/grafana/`:

1. **System Health Dashboard**
   - API response times
   - Error rates by endpoint
   - Worker status and queue depth

2. **Business Metrics Dashboard**
   - Requests by status/priority/category
   - SLA breach trends
   - Resolution time trends

3. **Infrastructure Dashboard**
   - Database connection pool
   - Redis memory usage
   - CPU/memory by container

### Structured Logging

All logs are in JSON format for easy parsing:

```json
{
  "timestamp": "2026-01-26T10:30:00.123456",
  "type": "http_request",
  "method": "GET",
  "path": "/api/dashboard/admin/summary",
  "status": 200,
  "duration_ms": 45.2,
  "user_id": 5,
  "correlation_id": "a1b2c3d4-e5f6-7890"
}
```

**Log files:**

- `/app/logs/app.log` - General application logs
- `/app/logs/api.log` - API endpoint logs
- `/app/logs/celery.log` - Celery task logs
- `/app/logs/errors.log` - Error logs

### Request Correlation

Each request gets unique correlation ID for distributed tracing:

```bash
# Custom correlation ID
curl -H "X-Correlation-ID: my-unique-id" http://localhost:5000/api/test

# Auto-generated if not provided
# ID appears in all logs and responses
```

### Sentry Integration

Error tracking with Sentry for production monitoring:

```bash
# Set Sentry DSN
export SENTRY_DSN=https://examplePublicKey@o0.ingest.sentry.io/0

# Automatic error capture:
# - Unhandled exceptions
# - Failed Celery tasks
# - Database errors
# - 5xx HTTP responses
```

---

## Backup & Disaster Recovery

### Automated Backups

**Schedule:** Daily at 2 AM UTC (configurable via Celery Beat)

**Location:** `/backups/` directory (configure via `BACKUP_DIR`)

**Process:**

1. `pg_dump` database to SQL
2. Compress with gzip
3. Encrypt with AES-256-CBC
4. Store with timestamp

**File naming:** `backup_YYYYMMDD_HHMMSS.sql.gz.enc`

### Creating Manual Backup

```bash
# Using backup script
bash scripts/backup_database.sh

# Using direct command
pg_dump $DATABASE_URL | gzip > backup_manual.sql.gz

# With encryption
pg_dump $DATABASE_URL | gzip | openssl enc -aes-256-cbc -salt -out backup.sql.gz.enc
```

### Listing Backups

```bash
ls -lh /backups/
# Output:
# backup_20260124_020000.sql.gz.enc (450M)
# backup_20260125_020000.sql.gz.enc (455M)
# backup_20260126_020000.sql.gz.enc (460M)
```

### Restoring from Backup

**Full Recovery:**

```bash
bash scripts/restore_database.sh /backups/backup_20260126_020000.sql.gz.enc

# Prompts for encryption password and confirmation
# Drops existing schema and restores from backup
```

**Point-in-time Recovery:**

```bash
# 1. Restore to most recent backup
bash scripts/restore_database.sh /backups/backup_latest.sql.gz.enc

# 2. Check recovery status
psql $DATABASE_URL -c "SELECT COUNT(*) FROM service_request;"

# 3. Run migrations if needed
flask db upgrade
```

### Backup Verification

**Automatic (part of backup process):**

```bash
file /backups/backup_20260126_020000.sql.gz.enc
# Output: gzip compressed data

openssl enc -d -aes-256-cbc -in backup.sql.gz.enc -pass pass:test 2>&1 | head -c 100
# Decryption test (fails with wrong password, but file is readable)
```

**Manual Verification:**

```bash
# Test decrypt
openssl enc -d -aes-256-cbc -in backup.sql.gz.enc -out test_backup.sql.gz
gunzip test_backup.sql.gz

# Check schema
head -50 test_backup.sql
# Should show "CREATE TABLE" statements

# Count records (no restore needed)
zcat test_backup.sql.gz | grep "INSERT INTO" | wc -l
```

### Retention Policy

**Default:** 30 days

**Configure:**

```bash
export RETENTION_DAYS=30  # Modify as needed
```

**Automatic cleanup:**

- Backups older than 30 days deleted daily
- Frees up disk space
- Recent backups always available

### Disaster Recovery Runbook

**Scenario: Database corruption**

1. **Alert:** Monitoring detects database error
2. **Assess:** Check backup integrity

   ```bash
   bash scripts/restore_database.sh /backups/backup_latest.sql.gz.enc
   ```

3. **Restore:** Run restore script in staging first
4. **Verify:** Test app functionality
5. **Cutover:** Redirect traffic to restored database
6. **Post-Mortem:** Investigate root cause

---

## Security Hardening

### Container Security

**Dockerfile Security Features:**

- Non-root user (UID 1000)
- Read-only filesystem (except /tmp, /run)
- Dropped Linux capabilities
- Resource limits enforced
- No privilege escalation

**Run container securely:**

```bash
docker run \
  --read-only \
  --cap-drop=ALL \
  --cap-add=NET_BIND_SERVICE \
  --user=1000:1000 \
  --memory=512m \
  --cpus=1 \
  elcorp-app:latest
```

### Redis Security

**Configuration** (`redis.conf`):

```conf
# Require password
requirepass ${REDIS_PASSWORD}

# Disable dangerous commands
rename-command FLUSHDB ""
rename-command FLUSHALL ""
rename-command CONFIG "CONFIG_${RANDOM}"

# Bind to localhost only
bind 127.0.0.1

# Enable persistence
appendonly yes
```

### PostgreSQL Security

**Best Practices:**

```sql
-- Create application user (not superuser)
CREATE ROLE elcorp WITH LOGIN PASSWORD 'strong_password';

-- Grant only needed permissions
GRANT CONNECT ON DATABASE elcorp_db TO elcorp;
GRANT USAGE ON SCHEMA public TO elcorp;
GRANT CREATE ON SCHEMA public TO elcorp;

-- Enable SSL connections
ssl = on
ssl_cert_file = '/path/to/server.crt'
ssl_key_file = '/path/to/server.key'
```

### Rate Limiting

**Auth Endpoint Protection:**

```
/login:           5 attempts per 15 minutes
/register:        3 attempts per 60 minutes  
/password-reset:  5 attempts per 60 minutes
```

**Brute Force Detection:**

- Monitors failed attempts by IP
- Blocks after 5 failures in 5 minutes
- Admin alert on suspicious activity

### TLS/SSL

**Enable HTTPS:**

```bash
# Generate certificates
certbot certonly --standalone -d api.example.com

# Update environment
export SSL_CERT_FILE=/etc/letsencrypt/live/api.example.com/fullchain.pem
export SSL_KEY_FILE=/etc/letsencrypt/live/api.example.com/privkey.pem

# Gunicorn auto-detects certificates
```

---

## Troubleshooting

### Issues & Solutions

**Problem: Celery tasks not running**

```
Check 1: Is Redis running?
$ redis-cli ping
PONG

Check 2: Are workers running?
$ celery -A app.celery_app inspect active
{u'celery@hostname': {...}}

Check 3: Check worker logs
$ tail -f celery_worker.log

Check 4: Purge and restart
$ celery -A app.celery_app purge
$ celery -A app.celery_app worker --loglevel=debug
```

**Problem: Database backup failing**

```
Check 1: DATABASE_URL set?
$ echo $DATABASE_URL
postgresql://user:pass@host/db

Check 2: Backup directory writable?
$ ls -ld /backups/
drwxrwxr-x 2 user user 4096 Jan 26 10:30 /backups/

Check 3: pg_dump available?
$ which pg_dump
/usr/bin/pg_dump

Check 4: Disk space available?
$ df -h /backups/
Filesystem      Size  Used Avail Use% Mounted on
/dev/sda1       100G   45G   55G  45% /
```

**Problem: SLA breaches not detecting**

```
Check 1: SLA definitions exist?
$ psql $DATABASE_URL -c "SELECT * FROM sla_definition;"

Check 2: SLA metrics being created?
$ psql $DATABASE_URL -c "SELECT * FROM sla_metric WHERE is_breached=true;"

Check 3: Celery beat scheduler running?
$ celery -A app.celery_app beat --loglevel=debug

Check 4: Check task logs
$ grep "check_sla_breaches" celery.log
```

**Problem: Health check returning 503**

```
Check 1: Database connectivity
$ psql $DATABASE_URL -c "SELECT 1;"

Check 2: Redis connectivity
$ redis-cli -h localhost ping
PONG

Check 3: Check logs for errors
$ tail -f app/logs/app.log

Check 4: Check component individually
$ curl http://localhost:5432  # Test database port
$ curl http://localhost:6379  # Test Redis port
```

### Performance Optimization

**Slow Dashboard Queries:**

```sql
-- Add indices for dashboard queries
CREATE INDEX idx_service_request_status_created ON service_request(status, created_at);
CREATE INDEX idx_service_request_priority_created ON service_request(priority, created_at);
CREATE INDEX idx_sla_metric_breached_created ON sla_metric(is_breached, created_at);
```

**Celery Queue Backlog:**

```python
# Monitor queue depth
celery -A app.celery_app inspect active_queues

# Scale workers
docker-compose -f docker-compose.production.yml scale celery_worker_default=4
```

**Database Connection Pool:**

```python
# Configure pool size in app config
SQLALCHEMY_ENGINE_OPTIONS = {
    'pool_size': 20,
    'pool_recycle': 3600,
    'pool_pre_ping': True,
}
```

---

## References

- [Celery Documentation](https://docs.celeryproject.org/)
- [PostgreSQL Backup/Restore](https://www.postgresql.org/docs/current/backup-dump.html)
- [Prometheus Monitoring](https://prometheus.io/docs/)
- [Docker Security](https://docs.docker.com/engine/security/)
