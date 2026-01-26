# Service Request System - Quick Start Guide

## What You're Getting

A complete, production-ready Service Request workflow system for the Elcorp Namibia platform that includes:

✅ Full database models with audit trail  
✅ 10+ REST API endpoints with role-based access control  
✅ Complete workflow state machine (Draft → Submitted → In Review → Approved/Rejected → Completed)  
✅ Email notifications for all major events  
✅ Comprehensive audit logging  
✅ 50+ test cases covering all scenarios  

## Setup Instructions

### 1. Database Migration

The migration file is already created at:
```
migrations/versions/20260126_add_service_request.py
```

Apply the migration:
```bash
cd elcorp-namibia
flask db upgrade
```

This creates two tables:
- `service_request` - Main request table
- `service_request_history` - Audit trail table

### 2. Configuration

Ensure your `.env` file has email configuration:
```env
MAIL_SERVER=smtp.example.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@example.com
MAIL_PASSWORD=your-password
ADMINS=["admin@example.com"]
```

### 3. Test Setup

Add the "staff" role to your seed data:

In `tests/conftest.py`, the staff role is already added to the seed_roles fixture.

## API Usage Examples

### User: Create a Service Request

```bash
curl -X POST http://localhost:5000/api/service-requests \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "title": "Account Access Issue",
    "description": "Cannot login to my dashboard",
    "category": "support",
    "priority": "high"
  }'
```

**Response (201 Created):**
```json
{
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "title": "Account Access Issue",
    "description": "Cannot login to my dashboard",
    "category": "support",
    "priority": "high",
    "status": "draft",
    "created_by": 123,
    "assigned_to": null,
    "created_at": "2026-01-26T12:00:00",
    "updated_at": "2026-01-26T12:00:00"
  },
  "message": "Service request created successfully"
}
```

### User: Submit the Request

```bash
curl -X POST http://localhost:5000/api/service-requests/550e8400-e29b-41d4-a716-446655440000/submit \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response (200 OK):**
```json
{
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "submitted",
    "updated_at": "2026-01-26T12:01:00"
  },
  "message": "Service request submitted successfully"
}
```

**Action**: Creator receives email notification of submission

### Admin: View All Requests

```bash
curl -X GET "http://localhost:5000/api/service-requests?status=submitted&page=1" \
  -H "Authorization: Bearer ADMIN_TOKEN"
```

**Response:**
```json
{
  "data": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "title": "Account Access Issue",
      "category": "support",
      "priority": "high",
      "status": "submitted",
      "created_by": 123,
      "creator_name": "John Doe",
      "assigned_to": null,
      "created_at": "2026-01-26T12:00:00",
      "updated_at": "2026-01-26T12:01:00"
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 1,
    "total_pages": 1
  }
}
```

### Admin: Assign to Staff

```bash
curl -X POST http://localhost:5000/api/service-requests/550e8400-e29b-41d4-a716-446655440000/assign \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -d '{
    "assigned_to": 456
  }'
```

**Response:**
```json
{
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "assigned_to": 456,
    "assignee_name": "Jane Staff",
    "updated_at": "2026-01-26T12:02:00"
  },
  "message": "Service request assigned successfully"
}
```

**Action**: Assigned staff member receives email notification

### Staff: Move to Review

```bash
curl -X PATCH http://localhost:5000/api/service-requests/550e8400-e29b-41d4-a716-446655440000/status \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer STAFF_TOKEN" \
  -d '{
    "status": "in_review",
    "notes": "Currently investigating the issue"
  }'
```

**Response:**
```json
{
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "in_review",
    "updated_at": "2026-01-26T12:03:00"
  },
  "message": "Service request status updated successfully"
}
```

### Admin: Approve Request

```bash
curl -X PATCH http://localhost:5000/api/service-requests/550e8400-e29b-41d4-a716-446655440000/status \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -d '{
    "status": "approved",
    "notes": "Issue resolved. Account has been re-enabled."
  }'
```

**Action**: Creator receives email notification of approval with resolution notes

### Admin: Complete Request

```bash
curl -X PATCH http://localhost:5000/api/service-requests/550e8400-e29b-41d4-a716-446655440000/status \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -d '{
    "status": "completed",
    "notes": "Request has been completed"
  }'
```

## Running Tests

### All Service Request Tests
```bash
pytest tests/test_service_requests.py -v
```

### Test Specific Functionality
```bash
# Test permissions
pytest tests/test_service_requests.py::TestServiceRequestPermissions -v

# Test workflow transitions
pytest tests/test_service_requests.py::TestServiceRequestWorkflow -v

# Test API endpoints
pytest tests/test_service_requests.py::TestServiceRequestAPIEndpoints -v
```

### Generate Coverage Report
```bash
pytest tests/test_service_requests.py --cov=app --cov-report=html
```

## Files Created/Modified

### New Files
- `app/email_service.py` - Email notification functions
- `app/models.py` - Added ServiceRequest and ServiceRequestHistory models
- `migrations/versions/20260126_add_service_request.py` - Database migration
- `tests/test_service_requests.py` - Comprehensive test suite
- `docs/SERVICE_REQUEST_SYSTEM.md` - Complete documentation

### Modified Files
- `app/api/routes.py` - Added 10+ new endpoints
- `tests/conftest.py` - Added staff role to seeding

## Database Schema

### service_request Table
```sql
CREATE TABLE service_request (
  id VARCHAR(36) PRIMARY KEY,
  title VARCHAR(255) NOT NULL,
  description TEXT NOT NULL,
  category VARCHAR(50) NOT NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'draft',
  priority VARCHAR(10) NOT NULL DEFAULT 'normal',
  created_by INTEGER NOT NULL REFERENCES user(id),
  assigned_to INTEGER REFERENCES user(id),
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL,
  INDEX ix_service_request_created_by (created_by),
  INDEX ix_service_request_assigned_to (assigned_to)
);
```

### service_request_history Table
```sql
CREATE TABLE service_request_history (
  id INTEGER PRIMARY KEY AUTO_INCREMENT,
  service_request_id VARCHAR(36) NOT NULL REFERENCES service_request(id),
  action VARCHAR(100) NOT NULL,
  old_status VARCHAR(20),
  new_status VARCHAR(20),
  changed_by INTEGER NOT NULL REFERENCES user(id),
  details JSON,
  timestamp DATETIME NOT NULL,
  INDEX ix_service_request_history_service_request_id (service_request_id)
);
```

## Validation Rules

### Categories
- `compliance` - Compliance-related requests
- `support` - User support requests
- `inquiry` - General inquiries
- `complaint` - Complaints or issues
- `other` - Other types

### Statuses
- `draft` - Initial state, creator can edit
- `submitted` - User submitted, waiting for review
- `in_review` - Staff reviewing
- `approved` - Admin approved, ready to complete
- `rejected` - Admin rejected
- `completed` - Final state

### Priorities
- `low` - Low priority
- `normal` - Normal priority (default)
- `high` - High priority
- `urgent` - Urgent priority

## Permission Matrix

| Action | User | Staff | Admin |
|--------|------|-------|-------|
| Create Request | ✅ | ✅ | ✅ |
| Edit Draft | Creator Only | ❌ | ✅ |
| Submit Request | Creator | ❌ | ❌ |
| Move to Review | ❌ | ✅ | ❌ |
| Approve/Reject | ❌ | ❌ | ✅ |
| Mark Complete | ❌ | ❌ | ✅ |
| Assign Staff | ❌ | ❌ | ✅ |
| Delete Request | ❌ | ❌ | ✅ |
| View Own | ✅ | ✅ | ✅ |
| View All | ❌ | ✅ | ✅ |

## Common Issues and Solutions

### Issue: "Staff role not found"
**Solution**: Ensure `tests/conftest.py` has the staff role in seed_roles

### Issue: "Email notifications not sending"
**Solution**: Check `.env` for valid MAIL_* configuration

### Issue: Tests failing on model imports
**Solution**: Ensure ServiceRequest is imported in `app/__init__.py` for the app factory

### Issue: Migration fails
**Solution**: Ensure database has `user` and `role` tables first

## Next Steps

1. **Test the API**: Use the curl examples above to test functionality
2. **Frontend Integration**: Create UI forms for submitting requests
3. **Dashboard**: Create staff dashboard for reviewing requests
4. **Analytics**: Add request metrics and reporting
5. **Automation**: Add automatic escalation and SLA tracking

## Support

For detailed API documentation, see [docs/SERVICE_REQUEST_SYSTEM.md](SERVICE_REQUEST_SYSTEM.md)

For general development guide, see [DEVELOPER_GUIDE.md](../DEVELOPER_GUIDE.md)
