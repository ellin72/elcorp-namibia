# Service Request Workflow System

## Overview

The Service Request system provides a complete workflow for managing user requests through submission, review, approval, and completion stages. It integrates with the RBAC (Role-Based Access Control) system to enforce strict permission controls at each workflow stage.

## Architecture

### Database Models

#### ServiceRequest

The main model representing a service request with the following attributes:

```python
- id: UUID (primary key)
- title: String (required)
- description: Text (required)
- category: String - one of: compliance, support, inquiry, complaint, other
- status: String - draft, submitted, in_review, approved, rejected, completed
- priority: String - low, normal, high, urgent
- created_by: FK -> User (creator)
- assigned_to: FK -> User (nullable, assigned staff member)
- created_at: DateTime
- updated_at: DateTime
```

#### ServiceRequestHistory

Audit trail for all changes to service requests:

```python
- id: Integer (primary key)
- service_request_id: FK -> ServiceRequest
- action: String (submitted, reviewed, approved, rejected, assigned, completed)
- old_status: String
- new_status: String
- changed_by: FK -> User
- details: JSON (additional context)
- timestamp: DateTime
```

### Workflow States

```
┌─────────┐
│  DRAFT  │ (User can edit, only creator)
└────┬────┘
     │ submit
     ▼
┌──────────────┐
│  SUBMITTED   │ (User cannot edit)
└────┬─────────┘
     │ move_to_review (Staff)
     ▼
┌────────────┐
│ IN_REVIEW  │ (Staff reviewing)
└──┬──────┬──┘
   │      │
   │ (Admin Decision)
   │      │
   ▼      ▼
┌────────┐ ┌──────────┐
│APPROVED│ │ REJECTED │
└───┬────┘ └──────────┘
    │
    │ mark_complete
    ▼
┌──────────┐
│COMPLETED │ (Final state)
└──────────┘
```

## State Transition Rules

### Draft → Submitted

- **Who**: Creator (User)
- **Condition**: Request must be in DRAFT status
- **Action**: `POST /api/service-requests/{id}/submit`
- **Triggers**: Email notification to creator

### Submitted → In Review

- **Who**: Staff member
- **Condition**: Request must be SUBMITTED
- **Action**: `PATCH /api/service-requests/{id}/status` with status=`in_review`
- **Audit**: Logged with staff member ID

### In Review → Approved/Rejected

- **Who**: Admin only
- **Condition**: Request must be IN_REVIEW
- **Actions**:
  - Approve: `PATCH /api/service-requests/{id}/status` with status=`approved`
  - Reject: `PATCH /api/service-requests/{id}/status` with status=`rejected`
- **Triggers**: Email notification to creator

### Approved → Completed

- **Who**: Admin only
- **Condition**: Request must be APPROVED
- **Action**: `PATCH /api/service-requests/{id}/status` with status=`completed`
- **Triggers**: Final status email notification

## Role-Based Access Control

### User Role

- **Permissions**:
  - Create new service requests (always DRAFT status)
  - Edit own DRAFT requests
  - Submit own DRAFT requests
  - View own requests
  - View request history for own requests

- **Restricted Actions**:
  - Cannot edit submitted/approved/rejected requests
  - Cannot change status of any request
  - Cannot view other users' requests
  - Cannot delete requests

### Staff Role

- **Permissions**:
  - View assigned service requests
  - View all submitted requests
  - Move requests from SUBMITTED to IN_REVIEW
  - Add notes/comments during review
  - View request details and history

- **Restricted Actions**:
  - Cannot approve or reject
  - Cannot change priority or category
  - Cannot delete requests
  - Cannot view draft requests from other users

### Admin Role

- **Permissions**:
  - View all service requests (regardless of status)
  - Change request status (in_review, approved, rejected, completed)
  - Assign requests to staff
  - Delete service requests
  - View complete audit trail
  - Edit request properties after creation
  - Add internal notes

- **Restricted Actions**:
  - Cannot undelete deleted requests (soft-delete recommended)

## Email Notifications

### Triggers and Recipients

#### 1. Request Submitted

- **Recipient**: Request creator
- **Subject**: [Elcorp] Service Request Submitted: {title}
- **Content**:
  - Request ID
  - Title, category, priority
  - Confirmation that request is under review

#### 2. Status Changed (Approval/Rejection)

- **Recipient**: Request creator
- **Subject**: [Elcorp] Service Request {Status}: {title}
- **Content**:
  - Request ID
  - Previous and new status
  - Admin notes (if provided)
  - Next steps

#### 3. Request Assigned

- **Recipient**: Assigned staff member
- **Subject**: [Elcorp] New Service Request Assigned: {title}
- **Content**:
  - Request ID and details
  - Priority and category
  - Requested action (review and move to in_review)

## Audit Logging

All actions are logged with:

- **Timestamp**: When action occurred
- **User**: Who performed the action
- **Action**: Type of action (submitted, status_changed, assigned, deleted)
- **Details**: JSON object with context
  - Status changes include old and new status
  - Assignments include staff member ID
  - Deletions include soft-deleted request details

## API Endpoints

### User Endpoints

#### Create Service Request

```
POST /api/service-requests
Content-Type: application/json

{
  "title": "Request Title",
  "description": "Detailed description",
  "category": "support|compliance|inquiry|complaint|other",
  "priority": "low|normal|high|urgent"  (optional, default: normal)
}

Response: 201 Created
{
  "id": "uuid-string",
  "title": "...",
  "status": "draft",
  "created_at": "...",
  "updated_at": "..."
}
```

#### Get My Service Requests

```
GET /api/service-requests/mine?status=submitted&priority=high&page=1&per_page=20

Response: 200 OK
{
  "data": [
    {
      "id": "uuid",
      "title": "...",
      "category": "...",
      "priority": "...",
      "status": "...",
      "created_at": "...",
      "updated_at": "..."
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 5,
    "total_pages": 1
  }
}
```

#### Get Request Details

```
GET /api/service-requests/{id}

Response: 200 OK
{
  "data": {
    "id": "uuid",
    "title": "...",
    "description": "...",
    "category": "...",
    "priority": "...",
    "status": "...",
    "created_by": 123,
    "creator_name": "John Doe",
    "assigned_to": 456,
    "assignee_name": "Jane Staff",
    "created_at": "...",
    "updated_at": "..."
  }
}
```

#### Update Service Request (Draft Only)

```
PUT /api/service-requests/{id}
Content-Type: application/json

{
  "title": "Updated Title",
  "description": "Updated description",
  "category": "support",
  "priority": "high"
}

Response: 200 OK
```

#### Submit Service Request

```
POST /api/service-requests/{id}/submit

Response: 200 OK
{
  "data": {
    "id": "uuid",
    "status": "submitted",
    "updated_at": "..."
  },
  "message": "Service request submitted successfully"
}
```

### Staff Endpoints

#### Get Assigned Service Requests

```
GET /api/service-requests/assigned?status=submitted&page=1

Response: 200 OK
{
  "data": [
    {
      "id": "uuid",
      "title": "...",
      "priority": "...",
      "status": "...",
      "created_by": 123,
      "creator_name": "...",
      "created_at": "..."
    }
  ],
  "pagination": {...}
}
```

#### Update Request Status (Staff can move to in_review)

```
PATCH /api/service-requests/{id}/status
Content-Type: application/json

{
  "status": "in_review",
  "notes": "Currently reviewing this request"
}

Response: 200 OK
{
  "data": {
    "id": "uuid",
    "status": "in_review",
    "updated_at": "..."
  }
}
```

### Admin Endpoints

#### Get All Service Requests

```
GET /api/service-requests?status=approved&priority=high&category=support&page=1

Response: 200 OK
{
  "data": [
    {
      "id": "uuid",
      "title": "...",
      "category": "...",
      "priority": "...",
      "status": "...",
      "created_by": 123,
      "creator_name": "...",
      "assigned_to": 456,
      "assignee_name": "...",
      "created_at": "...",
      "updated_at": "..."
    }
  ],
  "pagination": {...}
}
```

#### Assign Service Request

```
POST /api/service-requests/{id}/assign
Content-Type: application/json

{
  "assigned_to": 456  // User ID of staff member
}

Response: 200 OK
{
  "data": {
    "id": "uuid",
    "assigned_to": 456,
    "assignee_name": "Jane Staff",
    "updated_at": "..."
  }
}
```

#### Update Status (Admin can approve/reject/complete)

```
PATCH /api/service-requests/{id}/status
Content-Type: application/json

{
  "status": "approved|rejected|completed",
  "notes": "Admin decision notes"
}

Response: 200 OK
```

#### Delete Service Request

```
DELETE /api/service-requests/{id}

Response: 200 OK
{
  "message": "Service request deleted successfully"
}
```

## Error Responses

### 400 Bad Request

```json
{
  "error": "Invalid category. Must be one of: compliance, support, inquiry, complaint, other",
  "code": 400
}
```

### 401 Unauthorized

```json
{
  "error": "Authentication required",
  "code": 401
}
```

### 403 Forbidden

```json
{
  "error": "You do not have permission to access this request",
  "code": 403
}
```

### 404 Not Found

```json
{
  "error": "Service request not found",
  "code": 404
}
```

## Testing

### Unit Tests

Test individual model methods:

```bash
pytest tests/test_service_requests.py::TestServiceRequestModel -v
```

### Permission Tests

Test RBAC enforcement:

```bash
pytest tests/test_service_requests.py::TestServiceRequestPermissions -v
```

### Workflow Tests

Test state transitions:

```bash
pytest tests/test_service_requests.py::TestServiceRequestWorkflow -v
```

### Integration Tests

Test API endpoints:

```bash
pytest tests/test_service_requests.py::TestServiceRequestAPIEndpoints -v
```

### Run All Service Request Tests

```bash
pytest tests/test_service_requests.py -v
```

## Implementation Checklist

- [x] Create ServiceRequest model with all required fields
- [x] Create ServiceRequestHistory audit model
- [x] Create Alembic migration
- [x] Implement API endpoints with RBAC
- [x] Implement workflow state transitions
- [x] Add email notifications
- [x] Add audit logging
- [x] Write comprehensive tests
- [x] Document API endpoints
- [x] Document workflow rules

## Security Considerations

1. **Data Access**: All queries enforce user-level access control
2. **State Transitions**: Only valid transitions allowed per role
3. **Audit Trail**: All state changes are logged immutably
4. **Email Security**: Notifications use authenticated mail service
5. **SQL Injection**: All queries use parameterized statements (SQLAlchemy)
6. **CSRF Protection**: API endpoints validate request origin

## Performance Considerations

1. **Database Indexes**:
   - `created_by` and `assigned_to` indexed for quick lookups
   - `service_request_id` indexed in history table

2. **Pagination**: All list endpoints use pagination (default 20, max 100)

3. **Query Optimization**:
   - Use `lazy='dynamic'` for large relationships
   - Implement query filtering early

## Future Enhancements

1. **Soft Deletes**: Implement soft deletion for data recovery
2. **Bulk Operations**: Allow bulk status updates
3. **Custom Fields**: Support custom metadata per request
4. **SLA Tracking**: Track and alert on SLA breaches
5. **Escalation**: Automatic escalation for overdue requests
6. **Webhooks**: External system notifications
7. **Attachments**: File attachments for requests and responses
