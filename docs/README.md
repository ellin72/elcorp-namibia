# Documentation Index

This folder contains comprehensive documentation for the Elcorp Namibia platform.

## Quick Navigation

### Getting Started

- **[Service Request Quick Start](SERVICE_REQUEST_QUICK_START.md)** - Setup and basic usage examples (5 min read)
- **[Architecture Overview](architecture.md)** - System architecture and design

### Service Request System

- **[Service Request System](SERVICE_REQUEST_SYSTEM.md)** - Complete technical documentation
  - Database models and schema
  - Workflow state machine
  - API endpoints with examples
  - RBAC permission matrix
  - Testing guide
  - Security considerations

### Root Level Documentation

- **[README.md](../README.md)** - Project overview and features
- **[DEVELOPER_GUIDE.md](../DEVELOPER_GUIDE.md)** - Developer quick reference
- **[IMPLEMENTATION_SUMMARY.md](../IMPLEMENTATION_SUMMARY.md)** - Technical implementation details
- **[PROJECT_COMPLETION_CHECKLIST.md](../PROJECT_COMPLETION_CHECKLIST.md)** - Feature verification
- **[DOCUMENTATION_INDEX.md](../DOCUMENTATION_INDEX.md)** - Documentation navigation (root level)
- **[SECURITY.md](../SECURITY.md)** - Security practices and guidelines
- **[CONTRIBUTING.md](../CONTRIBUTING.md)** - Contribution guidelines

## Service Request System

### For Users

Learn how to submit and track service requests:

- Creating a new service request
- Submitting for review
- Tracking status and receiving notifications

**→ [Service Request Quick Start](SERVICE_REQUEST_QUICK_START.md)**

### For Developers

Integrate the service request system into your application:

- REST API endpoints and request/response formats
- Database models and relationships
- Permission and RBAC rules
- Email notification system
- Audit logging

**→ [Service Request System](SERVICE_REQUEST_SYSTEM.md)**

### For DevOps/Admin

Deploy and maintain the service request system:

- Database migration steps
- Configuration requirements
- Email service setup
- Monitoring and logging

**→ [Service Request Quick Start - Setup Section](SERVICE_REQUEST_QUICK_START.md#setup-instructions)**

### For QA/Testing

Test and validate the service request system:

- Test suite overview
- Running tests
- Test coverage
- Permission matrix verification

**→ [Service Request System - Testing](SERVICE_REQUEST_SYSTEM.md#testing)**

## Database Models

### Current Models

- **User** - User accounts and authentication
- **Role** - User roles (User, Staff, Admin)
- **ServiceRequest** - Main service request model *(NEW)*
- **ServiceRequestHistory** - Audit trail for requests *(NEW)*
- **UserProfile** - Extended user information
- **VinRecord** - Vehicle VIN records
- **Vehicle** - Vehicle information
- **Transaction** - User transactions
- **AuditLog** - General audit logging
- **PasswordHistory** - Password change history
- **PasswordResetAudit** - Password reset attempt logging

See [SERVICE_REQUEST_SYSTEM.md](SERVICE_REQUEST_SYSTEM.md#database-models) for ServiceRequest models.

## REST API

### Service Request Endpoints *(NEW)*

#### User Endpoints

- `POST /api/service-requests` - Create new request
- `GET /api/service-requests/mine` - List own requests
- `GET /api/service-requests/{id}` - Get request details
- `PUT /api/service-requests/{id}` - Update draft request
- `POST /api/service-requests/{id}/submit` - Submit request

#### Staff Endpoints

- `GET /api/service-requests/assigned` - List assigned requests
- `PATCH /api/service-requests/{id}/status` - Update status to in_review

#### Admin Endpoints

- `GET /api/service-requests` - List all requests
- `POST /api/service-requests/{id}/assign` - Assign to staff
- `PATCH /api/service-requests/{id}/status` - Approve/reject/complete
- `DELETE /api/service-requests/{id}` - Delete request

See [SERVICE_REQUEST_SYSTEM.md](SERVICE_REQUEST_SYSTEM.md#api-endpoints) for full API documentation.

## Files Structure

```
elcorp-namibia/
├── docs/
│   ├── README.md (this file)
│   ├── architecture.md
│   ├── SERVICE_REQUEST_SYSTEM.md
│   └── SERVICE_REQUEST_QUICK_START.md
├── app/
│   ├── models.py (contains ServiceRequest, ServiceRequestHistory)
│   ├── email_service.py (NEW - email notifications)
│   ├── api/routes.py (contains 10+ new service request endpoints)
│   ├── security.py (RBAC decorators)
│   └── ...
├── migrations/
│   └── versions/
│       └── 20260126_add_service_request.py (NEW)
├── tests/
│   └── test_service_requests.py (NEW - 50+ test cases)
└── README.md (main project README)
```

## Key Features Added

### Service Request System (January 26, 2026)

1. **Database Models**
   - ServiceRequest with UUID primary key
   - ServiceRequestHistory for audit trail
   - Status tracking and workflow support

2. **REST API Endpoints**
   - 10 new endpoints with full RBAC
   - Request/response validation
   - Error handling and logging

3. **Workflow Engine**
   - State machine implementation
   - Permission-based transitions
   - Audit trail tracking

4. **Notifications**
   - Email on submission
   - Email on approval/rejection
   - Email on assignment
   - Configurable mail settings

5. **Testing**
   - 50+ test cases
   - Unit tests for models
   - Permission tests for RBAC
   - Workflow transition tests
   - API endpoint tests
   - Audit logging tests

6. **Documentation**
   - Complete API reference
   - Quick start guide
   - Architecture overview
   - Test coverage guide

## Getting Help

### Common Questions

**Q: How do I set up the service request system?**
A: Follow [Service Request Quick Start](SERVICE_REQUEST_QUICK_START.md)

**Q: What are the API endpoints?**
A: See [Service Request System - API Endpoints](SERVICE_REQUEST_SYSTEM.md#api-endpoints)

**Q: How does the workflow work?**
A: See [Service Request System - Workflow States](SERVICE_REQUEST_SYSTEM.md#workflow-states)

**Q: How do permissions work?**
A: See [Service Request System - RBAC](SERVICE_REQUEST_SYSTEM.md#role-based-access-control)

**Q: How do I run the tests?**
A: See [Service Request Quick Start - Running Tests](SERVICE_REQUEST_QUICK_START.md#running-tests)

### Need More Help?

- Check [SECURITY.md](../SECURITY.md) for security questions
- Check [CONTRIBUTING.md](../CONTRIBUTING.md) for contribution guidelines
- Check [DEVELOPER_GUIDE.md](../DEVELOPER_GUIDE.md) for developer setup

## Documentation Standards

All documentation follows these standards:

1. **Clarity** - Use clear, simple language
2. **Examples** - Include code examples and curl commands
3. **Structure** - Organize with clear headings and sections
4. **Links** - Link to related documentation
5. **Completeness** - Cover common use cases and edge cases

## Last Updated

- **Service Request System**: January 26, 2026
- **Root Documentation**: January 25, 2026
- **Architecture**: January 25, 2026

## Version Information

- **Elcorp Namibia**: v1.0
- **Service Request System**: v1.0
- **Python**: 3.10+
- **Flask**: 3.0.3
- **PostgreSQL**: 12+
