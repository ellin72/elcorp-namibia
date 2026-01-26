# Dashboard & Analytics Documentation

## Overview

The ELCorp Namibia Service Request system includes comprehensive dashboard and analytics endpoints for monitoring, tracking, and analyzing service request workflows. Dashboards provide role-based views with RBAC enforcement, advanced filtering, and export capabilities.

**Key Features:**

- Role-based dashboards (Admin, Staff, User)
- Real-time analytics and aggregations
- Advanced filtering with multiple criteria
- Pagination and sorting support
- CSV and PDF export functionality
- Performance optimization with database indices
- Audit trail and compliance tracking

## Architecture

### Analytics Service Layer

The `analytics_service.py` module provides business logic for aggregating and analyzing service request data:

```
app/services/analytics_service.py
├── Aggregation Functions (by status, category, priority)
├── Time-based Analysis (created/completed per day, avg resolution time)
├── Distribution Analysis (staff workload, category trends)
├── Filtering & Search (advanced filters with pagination)
└── Dashboard Summaries (pre-computed metrics)
```

### Database Optimization

Performance is optimized through strategic indices on frequently-queried columns:

```sql
-- Indices created by migration 20260126_add_indices.py
CREATE INDEX idx_service_request_status ON service_request(status);
CREATE INDEX idx_service_request_priority ON service_request(priority);
CREATE INDEX idx_service_request_created_at ON service_request(created_at);
-- Additional indices: created_by, assigned_to (from previous migration)
```

### Export Service Layer

The `export_service.py` module handles data export to various formats:

```
app/services/export_service.py
├── CSV Exports
│   ├── Service requests export
│   └── Staff performance export
├── PDF Exports
│   ├── Service requests report
│   └── Analytics summary report
└── Filename Management
```

## Dashboard Endpoints

### Admin Dashboard

**Purpose:** Provide comprehensive view of all service requests and system health for administrators.

#### 1. GET /api/dashboard/admin/summary

**Description:** Comprehensive metrics dashboard showing overall system status.

**Authentication:** Requires admin role

**Query Parameters:** None

**Response:**

```json
{
  "total_requests": 150,
  "open_requests": 45,
  "in_progress_requests": 38,
  "completed_requests": 67,
  "unassigned_requests": 12,
  "overdue_requests": 8,
  "high_priority_requests": 23,
  "avg_resolution_time_days": 4.2,
  "approval_rate_percent": 92.5,
  "status_breakdown": {
    "open": 45,
    "in_progress": 38,
    "completed": 67
  },
  "category_breakdown": {
    "hardware": 45,
    "software": 60,
    "network": 25,
    "other": 20
  },
  "priority_breakdown": {
    "high": 23,
    "medium": 78,
    "low": 49
  }
}
```

**Status Codes:**

- `200 OK` - Successfully retrieved summary
- `403 Forbidden` - User lacks admin role
- `500 Internal Server Error` - Server error

---

#### 2. GET /api/dashboard/admin/trends

**Description:** Historical trends showing request creation and completion rates over time.

**Authentication:** Requires admin role

**Query Parameters:**

- `days` (optional, default=30): Number of days to analyze (integer, 1-365)

**Response:**

```json
{
  "created_per_day": [
    {
      "date": "2026-01-20",
      "count": 5
    },
    {
      "date": "2026-01-21",
      "count": 8
    }
  ],
  "completed_per_day": [
    {
      "date": "2026-01-20",
      "count": 3
    },
    {
      "date": "2026-01-21",
      "count": 6
    }
  ],
  "category_trends": {
    "hardware": [5, 6, 4, 7, ...],
    "software": [8, 7, 9, 6, ...]
  }
}
```

**Example Requests:**

```bash
# Last 30 days (default)
curl -H "Authorization: Bearer <token>" \
  http://localhost:5000/api/dashboard/admin/trends

# Last 7 days
curl -H "Authorization: Bearer <token>" \
  http://localhost:5000/api/dashboard/admin/trends?days=7

# Last 90 days
curl -H "Authorization: Bearer <token>" \
  http://localhost:5000/api/dashboard/admin/trends?days=90
```

**Status Codes:**

- `200 OK` - Successfully retrieved trends
- `400 Bad Request` - Invalid days parameter
- `403 Forbidden` - User lacks admin role

---

#### 3. GET /api/dashboard/admin/workload

**Description:** Staff workload distribution showing requests assigned to each team member.

**Authentication:** Requires admin role

**Query Parameters:**

- `page` (optional, default=1): Page number for pagination
- `per_page` (optional, default=10): Items per page (max 100)

**Response:**

```json
{
  "staff_workload": [
    {
      "staff_id": 5,
      "staff_name": "John Doe",
      "assigned_count": 12,
      "completed_count": 8,
      "in_progress_count": 4,
      "completion_rate_percent": 66.7,
      "avg_resolution_time_days": 3.5,
      "high_priority_assigned": 3
    },
    {
      "staff_id": 6,
      "staff_name": "Jane Smith",
      "assigned_count": 15,
      "completed_count": 12,
      "in_progress_count": 3,
      "completion_rate_percent": 80.0,
      "avg_resolution_time_days": 2.8,
      "high_priority_assigned": 5
    }
  ],
  "total": 2,
  "pages": 1
}
```

---

#### 4. GET /api/dashboard/admin/sla-breaches

**Description:** Track SLA violations (overdue requests).

**Authentication:** Requires admin role

**Query Parameters:**

- `page` (optional, default=1): Page number
- `per_page` (optional, default=10): Items per page
- `priority` (optional): Filter by priority (high, medium, low)

**Response:**

```json
{
  "sla_breaches": [
    {
      "id": 45,
      "title": "Critical System Down",
      "priority": "high",
      "status": "in_progress",
      "created_at": "2026-01-18T10:30:00",
      "due_date": "2026-01-20T10:30:00",
      "days_overdue": 6,
      "assigned_to": "John Doe"
    }
  ],
  "total_breaches": 8,
  "high_priority_breaches": 3,
  "pages": 1
}
```

---

### Staff Dashboard

**Purpose:** Provide personalized view of assigned work for staff members.

#### 1. GET /api/dashboard/staff/summary

**Description:** Personal summary for staff member showing their workload metrics.

**Authentication:** Requires staff role

**Response:**

```json
{
  "assigned_requests": 12,
  "completed_requests": 8,
  "in_progress_requests": 4,
  "completion_rate_percent": 66.7,
  "avg_resolution_time_days": 3.5,
  "my_overdue_requests": 1,
  "high_priority_assigned": 3
}
```

---

#### 2. GET /api/dashboard/staff/my-workload

**Description:** Detailed list of all requests assigned to the current staff member.

**Authentication:** Requires staff role

**Query Parameters:**

- `status` (optional): Filter by status (open, in_progress, completed)
- `priority` (optional): Filter by priority (high, medium, low)
- `sort_by` (optional, default=created): Sort field (created, updated, priority)
- `sort_order` (optional, default=desc): Sort order (asc, desc)
- `page` (optional, default=1): Page number
- `per_page` (optional, default=10): Items per page

**Response:**

```json
{
  "requests": [
    {
      "id": 45,
      "title": "Printer Not Working",
      "description": "Office printer on 2nd floor is not responding",
      "category": "hardware",
      "priority": "high",
      "status": "in_progress",
      "created_at": "2026-01-20T08:00:00",
      "due_date": "2026-01-22T17:00:00",
      "created_by": "Jane Smith",
      "updated_at": "2026-01-21T10:30:00"
    }
  ],
  "total": 12,
  "pages": 2
}
```

**Example Requests:**

```bash
# All assigned requests
curl -H "Authorization: Bearer <token>" \
  http://localhost:5000/api/dashboard/staff/my-workload

# Only in-progress requests, high priority first
curl -H "Authorization: Bearer <token>" \
  "http://localhost:5000/api/dashboard/staff/my-workload?status=in_progress&sort_by=priority&sort_order=desc"

# Page 2 with 5 items per page
curl -H "Authorization: Bearer <token>" \
  "http://localhost:5000/api/dashboard/staff/my-workload?page=2&per_page=5"
```

---

#### 3. GET /api/dashboard/staff/performance

**Description:** Performance metrics for the current staff member.

**Authentication:** Requires staff role

**Query Parameters:**

- `days` (optional, default=30): Historical period to analyze

**Response:**

```json
{
  "assigned_count": 50,
  "completed_count": 40,
  "completion_rate_percent": 80.0,
  "avg_resolution_time_days": 2.8,
  "requests_completed_this_period": 15,
  "completion_trend": [
    {"date": "2026-01-20", "completed": 2},
    {"date": "2026-01-21", "completed": 3}
  ]
}
```

---

### Shared Filtering Endpoint

#### GET /api/dashboard/requests/filtered

**Description:** Advanced filtering endpoint with role-based access control. Users see own requests, staff see assigned requests, admins see all.

**Authentication:** Requires login (any authenticated user)

**Query Parameters:**

- `status` (optional): Filter by status (open, in_progress, completed)
- `priority` (optional): Filter by priority (high, medium, low)
- `category` (optional): Filter by category
- `date_from` (optional): Filter by date (YYYY-MM-DD format)
- `date_to` (optional): Filter by date (YYYY-MM-DD format)
- `assigned_to` (optional): Filter by assignee (staff ID) - admin only
- `sort_by` (optional, default=created): Sort field (created, updated, priority)
- `sort_order` (optional, default=desc): Sort order (asc, desc)
- `page` (optional, default=1): Page number
- `per_page` (optional, default=10): Items per page

**Response:**

```json
{
  "requests": [
    {
      "id": 45,
      "title": "Request Title",
      "description": "Request description",
      "category": "hardware",
      "priority": "high",
      "status": "in_progress",
      "created_at": "2026-01-20T08:00:00",
      "due_date": "2026-01-22T17:00:00",
      "assigned_to": "John Doe"
    }
  ],
  "total": 50,
  "pages": 5,
  "current_page": 1,
  "per_page": 10
}
```

**Example Requests:**

```bash
# All open requests
curl -H "Authorization: Bearer <token>" \
  "http://localhost:5000/api/dashboard/requests/filtered?status=open"

# High priority requests created in January 2026
curl -H "Authorization: Bearer <token>" \
  "http://localhost:5000/api/dashboard/requests/filtered?priority=high&date_from=2026-01-01&date_to=2026-01-31"

# Hardware requests assigned to staff member 5 (admin only)
curl -H "Authorization: Bearer <token>" \
  "http://localhost:5000/api/dashboard/requests/filtered?category=hardware&assigned_to=5"

# Network issues sorted by priority, descending
curl -H "Authorization: Bearer <token>" \
  "http://localhost:5000/api/dashboard/requests/filtered?category=network&sort_by=priority&sort_order=desc"
```

---

## Filtering & Search

### Filter Criteria

All filtering endpoints support the following criteria:

| Filter | Type | Values | Example |
|--------|------|--------|---------|
| `status` | String | open, in_progress, completed | `?status=open` |
| `priority` | String | high, medium, low | `?priority=high` |
| `category` | String | hardware, software, network, other | `?category=hardware` |
| `date_from` | Date | YYYY-MM-DD | `?date_from=2026-01-01` |
| `date_to` | Date | YYYY-MM-DD | `?date_to=2026-01-31` |
| `assigned_to` | Integer | Staff user ID | `?assigned_to=5` |
| `sort_by` | String | created, updated, priority, status | `?sort_by=priority` |
| `sort_order` | String | asc, desc | `?sort_order=desc` |
| `page` | Integer | 1+ | `?page=2` |
| `per_page` | Integer | 1-100 | `?per_page=25` |

### Common Filter Combinations

```bash
# All critical hardware issues assigned to John (user 5)
?status=open&priority=high&category=hardware&assigned_to=5

# Software requests in January, sorted by creation date (newest first)
?category=software&date_from=2026-01-01&date_to=2026-01-31&sort_by=created&sort_order=desc

# Completed requests from last 30 days, most recently updated first
?status=completed&date_from=2025-12-27&date_to=2026-01-26&sort_by=updated&sort_order=desc

# All unassigned requests, sorted by priority
?assigned_to=null&sort_by=priority&sort_order=desc
```

---

## Pagination

All list endpoints support pagination:

```json
{
  "requests": [...],
  "total": 150,           // Total items matching filter
  "pages": 15,            // Total pages
  "current_page": 1,      // Current page number
  "per_page": 10          // Items per page
}
```

**Pagination Examples:**

```bash
# Get first 10 items (default)
curl http://localhost:5000/api/dashboard/requests/filtered

# Get 25 items per page
curl http://localhost:5000/api/dashboard/requests/filtered?per_page=25

# Get page 3 with 10 items
curl http://localhost:5000/api/dashboard/requests/filtered?page=3&per_page=10

# Get last page
curl http://localhost:5000/api/dashboard/requests/filtered?page=15&per_page=10
```

---

## Export Functionality

### CSV Exports

#### Export Service Requests to CSV

```bash
# Export all requests (admin only)
curl -H "Authorization: Bearer <token>" \
  http://localhost:5000/api/dashboard/export/requests?format=csv \
  -o requests.csv

# Export filtered requests
curl -H "Authorization: Bearer <token>" \
  "http://localhost:5000/api/dashboard/export/requests?format=csv&status=completed&date_from=2026-01-01" \
  -o completed_requests.csv
```

**CSV Format:**

```
ID,Title,Description,Category,Priority,Status,Created By,Created At,Assigned To,Due Date
1,Printer Issue,Printer on 2nd floor,hardware,high,open,Jane Smith,2026-01-20 08:00:00,John Doe,2026-01-22
2,Software License,Need Office license,software,medium,in_progress,Bob Johnson,2026-01-19 10:30:00,Jane Smith,2026-01-25
```

#### Export Staff Performance to CSV

```bash
curl -H "Authorization: Bearer <token>" \
  http://localhost:5000/api/dashboard/export/staff-performance?format=csv \
  -o staff_performance.csv
```

**CSV Format:**

```
Staff Member,Assigned Requests,Completed Requests,In Progress,Completion Rate (%),Average Resolution Time (Days)
John Doe,12,8,4,66.7,3.5
Jane Smith,15,12,3,80.0,2.8
```

### PDF Exports

#### Export Service Requests Report

```bash
# Export as formatted PDF report
curl -H "Authorization: Bearer <token>" \
  http://localhost:5000/api/dashboard/export/requests?format=pdf \
  -o requests_report.pdf
```

**PDF Contents:**

- Report title and generation timestamp
- Summary statistics (total, open, completed, high priority)
- Detailed table of all requests
- Professional formatting with ELCorp branding

#### Export Analytics Summary

```bash
curl -H "Authorization: Bearer <token>" \
  http://localhost:5000/api/dashboard/export/analytics?format=pdf \
  -o analytics_report.pdf
```

**PDF Contents:**

- Key metrics summary
- Status breakdown table
- Category breakdown table
- Professional report formatting

---

## Background Tasks (Future Enhancement)

For large exports (1000+ requests), the system supports background task processing:

```python
# Enqueue large export as background task (with Celery)
task = export_task.delay(
    filter_params={'status': 'completed'},
    export_format='pdf',
    user_id=current_user.id
)

# User receives email with download link when ready
# Typical processing time: < 5 minutes for 10,000 requests
```

---

## RBAC (Role-Based Access Control)

### Role Permissions

| Endpoint | Admin | Staff | User | Notes |
|----------|-------|-------|------|-------|
| `/api/dashboard/admin/*` | ✅ | ❌ | ❌ | Admin only |
| `/api/dashboard/staff/summary` | ❌ | ✅ | ❌ | Staff only |
| `/api/dashboard/staff/my-workload` | ❌ | ✅ | ❌ | Staff only |
| `/api/dashboard/staff/performance` | ❌ | ✅ | ❌ | Staff only |
| `/api/dashboard/requests/filtered` | ✅ (all) | ✅ (assigned) | ✅ (own) | Scoped access |
| `/api/dashboard/export/*` | ✅ | ✅ (own) | ❌ | Limited to own data for staff |

### Access Control Examples

```python
# Admin sees all data
GET /api/dashboard/requests/filtered
# Returns: All 500 requests in system

# Staff sees only assigned requests
GET /api/dashboard/requests/filtered
# Returns: Only 12 requests assigned to this staff member

# User sees only own requests (created)
GET /api/dashboard/requests/filtered
# Returns: Only 3 requests created by this user
```

---

## Error Handling

### Common Error Responses

**401 Unauthorized**

```json
{
  "status": "error",
  "message": "Authentication required",
  "code": "unauthorized"
}
```

**403 Forbidden**

```json
{
  "status": "error",
  "message": "User does not have admin role",
  "code": "forbidden"
}
```

**400 Bad Request**

```json
{
  "status": "error",
  "message": "Invalid page parameter: must be positive integer",
  "code": "validation_error"
}
```

**500 Internal Server Error**

```json
{
  "status": "error",
  "message": "An error occurred processing your request",
  "code": "server_error"
}
```

---

## Performance Tips

### Query Optimization

1. **Use Indexes:** Dashboard queries use indices on status, priority, created_at for fast filtering
2. **Limit Date Ranges:** When possible, specify `date_from` and `date_to` to reduce scanned data
3. **Pagination:** Always paginate large result sets; avoid fetching 1000+ items at once

### Caching Strategy

```python
# Cache admin summary for 5 minutes
@cache.cached(timeout=300, key_prefix='admin_summary')
def admin_summary():
    return build_summary()

# Cache trends for 1 hour (less frequently accessed)
@cache.cached(timeout=3600, key_prefix='trends_')
def admin_trends(days):
    return calculate_trends(days)
```

### Recommended Limits

- `per_page`: Default 10, max 100 (higher values = slower queries)
- `days` parameter: Default 30 (analyzing 365+ days may be slow with large datasets)
- Concurrent requests: Limit to 10 per user to prevent API overload

---

## Analytics Metrics Explained

### Average Resolution Time

Time from request creation to completion (in days).

```
Average = Sum(completion_date - creation_date) / Completed Requests Count
```

**Example:**

- Request A: Created Jan 1, Completed Jan 5 = 4 days
- Request B: Created Jan 2, Completed Jan 8 = 6 days
- Average = (4 + 6) / 2 = 5 days

### Completion Rate

Percentage of requests that have been completed.

```
Completion Rate = (Completed / Total) × 100
```

**Example:**

- 40 completed out of 50 total = 80% completion rate

### SLA Breaches

Requests where due date has passed but status is not completed.

```
Overdue = Requests WHERE due_date < NOW() AND status != 'completed'
```

---

## Integration Examples

### Dashboard in Web App

```html
<!-- Admin Dashboard Card -->
<div class="dashboard-card">
  <h2>System Overview</h2>
  <p>Total Requests: <span id="total-count">-</span></p>
  <p>Open: <span id="open-count">-</span></p>
  <p>Avg Resolution: <span id="avg-resolution">-</span> days</p>
</div>

<script>
fetch('/api/dashboard/admin/summary')
  .then(r => r.json())
  .then(data => {
    document.getElementById('total-count').textContent = data.total_requests;
    document.getElementById('open-count').textContent = data.open_requests;
    document.getElementById('avg-resolution').textContent = data.avg_resolution_time_days;
  });
</script>
```

### Filtered Requests in React

```jsx
const [requests, setRequests] = useState([]);
const [filters, setFilters] = useState({ status: 'open', page: 1 });

useEffect(() => {
  const query = new URLSearchParams(filters).toString();
  fetch(`/api/dashboard/requests/filtered?${query}`)
    .then(r => r.json())
    .then(data => setRequests(data.requests));
}, [filters]);
```

### Export Feature

```bash
# Generate and download CSV
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:5000/api/dashboard/export/requests?format=csv&status=completed" \
  -o "completed_requests_$(date +%Y%m%d).csv"
```

---

## Troubleshooting

### Dashboard Returns 403 Forbidden

**Cause:** User does not have required role

**Solution:**

1. Verify user has `admin` or `staff` role assigned
2. Check role assignment in database: `SELECT * FROM user_role WHERE user_id = X;`

### Slow Endpoint Response

**Cause:** Large dataset, missing indices, or unoptimized query

**Solution:**

1. Add date range filters to limit data
2. Verify database indices exist: `\d service_request` in psql
3. Check query logs for N+1 queries
4. Consider pagination to smaller page sizes

### Export Returns Empty File

**Cause:** No matching data for filters

**Solution:**

1. Verify filters match existing requests
2. Try without filters first: `?format=csv`
3. Check that user has permission to see data (RBAC)

---

## Maintenance

### Database Maintenance

```sql
-- Analyze table for query optimization
ANALYZE service_request;

-- Reindex to maintain performance
REINDEX INDEX idx_service_request_status;
```

### Log Rotation

Dashboard operations are logged to:

- `logs/dashboard.log` - All dashboard API requests
- `logs/analytics.log` - Analytics calculations
- `logs/export.log` - Export operations

---

## Future Enhancements

1. **Real-time Updates:** WebSocket support for live dashboard updates
2. **Custom Reports:** User-defined report templates
3. **Email Scheduling:** Automatic report delivery to stakeholders
4. **Dashboard Customization:** Allow users to customize metric display
5. **Advanced Charting:** Interactive charts for trend visualization
6. **Predictive Analytics:** Forecast completion times and resource needs
