# Elcorp Namibia

A secure, scalable Flask platform for vehicle identity management and tokenized governance.

## Flagship Products

- **Elcar** – Blockchain-based VIN registry with audit trails
- **Elcoin** – Native token powering compliance, payments, and governance

## Features

- ✅ Role-based access control (Admin, Staff, User)
- ✅ 2FA and password reuse protection
- ✅ Real-time governance dashboard
- ✅ Admin panel with audit logs
- ✅ REST API with 14 comprehensive endpoints
- ✅ User profile management (CRUD)
- ✅ Secure password reset functionality
- ✅ Request rate limiting and CSRF protection
- ✅ **Service Request Workflow System** – Complete submission, review, approval workflow with email notifications

## System Requirements

- Python 3.10+
- SQLite (development), PostgreSQL (production)
- pip and virtualenv

## Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/ellin72/elcorp-namibia.git
cd elcorp-namibia
```

### 2. Create Virtual Environment

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS/Linux
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure Environment

```bash
cp .env.example .env
# Edit .env with your settings
```

### 5. Initialize Database

```bash
flask db upgrade
python reset_db.py
```

### 6. Run Application

```bash
flask run
```

Visit `http://localhost:5000`

## Project Structure

```
elcorp-namibia/
├── app/
│   ├── api/                    # REST API (NEW)
│   │   ├── __init__.py
│   │   ├── routes.py           # 14 endpoints
│   │   └── utils.py            # Response formatting
│   ├── auth/                   # Authentication
│   ├── dashboard/              # User dashboard
│   ├── main/                   # Public routes
│   ├── vin/                    # VIN management
│   ├── admin/                  # Admin panel
│   ├── __init__.py             # Flask factory
│   ├── models.py               # Database models
│   ├── security.py             # RBAC decorators
│   ├── extensions.py           # Flask extensions
│   ├── templates/              # Jinja2 templates
│   ├── static/                 # CSS/JS/images
│   └── logs/                   # Application logs
├── tests/                      # Pytest suite
│   ├── conftest.py
│   ├── test_api.py             # API tests
│   ├── test_auth.py            # Auth tests
│   └── test_models_rbac.py     # Model tests
├── migrations/                 # Alembic migrations
├── requirements.txt            # Python dependencies
├── .env.example                # Configuration template
├── wsgi.py                     # WSGI entry point
└── reset_db.py                 # Database initialization
```

## User Roles

| Role | Permissions |
|------|-------------|
| **Admin** | Full system access, user management, role assignment |
| **Staff** | Verify records, generate reports, access governance |
| **User** | View own profile, register vehicles, submit records |

## REST API Documentation

### Base URL

```
http://localhost:5000/api/v1
```

### Health Check

```bash
GET /api/v1/health
```

Response:

```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "timestamp": "2024-01-25T10:30:00"
  }
}
```

### Users Endpoints

#### List Users (Admin only)

```bash
GET /api/v1/users?page=1&per_page=20&search=query&role=admin
```

**Query Parameters:**

- `page`: Page number (default: 1)
- `per_page`: Items per page (default: 20, max: 100)
- `search`: Search by username, email, or full_name
- `role`: Filter by role (user, staff, admin)
- `active`: Filter by active status (true/false)

**Response:**

```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "username": "john_doe",
      "email": "john@example.com",
      "full_name": "John Doe",
      "role": "user",
      "is_active": true,
      "last_login": "2024-01-25T10:00:00",
      "created_at": "2024-01-20T12:00:00"
    }
  ],
  "pagination": {
    "total": 100,
    "page": 1,
    "per_page": 20,
    "pages": 5
  }
}
```

#### Get User

```bash
GET /api/v1/users/{id}
```

Users can view their own profile. Admins can view any user.

#### Create User (Admin only)

```bash
POST /api/v1/users
Content-Type: application/json

{
  "username": "newuser",
  "email": "user@example.com",
  "full_name": "Full Name",
  "phone": "1234567890",
  "password": "SecurePass123!",
  "organization": "Company",
  "role": "user"
}
```

**Response:** `201 Created`

```json
{
  "success": true,
  "message": "User created successfully",
  "data": {
    "id": 2,
    "username": "newuser",
    "email": "user@example.com"
  }
}
```

#### Update User

```bash
PUT /api/v1/users/{id}
Content-Type: application/json

{
  "full_name": "New Name",
  "phone": "0987654321",
  "organization": "New Company"
}
```

Non-admin users can only update their own profile.

#### Delete User (Admin only)

```bash
DELETE /api/v1/users/{id}
```

Soft-deletes the user (marks as inactive).

#### Update User Role (Admin only)

```bash
PUT /api/v1/users/{id}/role
Content-Type: application/json

{
  "role": "staff"
}
```

### Profiles Endpoints

#### Get Profile

```bash
GET /api/v1/profiles/{user_id}
```

Users can view their own profile. Admins can view any user's.

**Response:**

```json
{
  "success": true,
  "data": {
    "user_id": 1,
    "bio": "Software developer from Namibia",
    "profile_picture_url": "https://...",
    "date_of_birth": "1990-05-15",
    "country": "Namibia",
    "city": "Windhoek",
    "phone_verified": true,
    "email_verified": true,
    "created_at": "2024-01-20T12:00:00",
    "last_updated": "2024-01-25T10:00:00"
  }
}
```

#### Update Profile

```bash
PUT /api/v1/profiles/{user_id}
Content-Type: application/json

{
  "bio": "Updated bio",
  "profile_picture_url": "https://...",
  "date_of_birth": "1990-05-15",
  "country": "Namibia",
  "city": "Windhoek"
}
```

#### Current User Endpoints

```bash
GET /api/v1/me                   # Get current user info
GET /api/v1/me/profile           # Get current user's profile
PUT /api/v1/me/profile           # Update current user's profile
```

### Roles Endpoints

#### List Roles

```bash
GET /api/v1/roles
```

**Response:**

```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "name": "user",
      "description": "Default regular user role",
      "user_count": 50
    },
    {
      "id": 2,
      "name": "staff",
      "description": "Staff member with verification powers",
      "user_count": 10
    },
    {
      "id": 3,
      "name": "admin",
      "description": "Administrator with full access",
      "user_count": 2
    }
  ]
}
```

## Response Format

### Success Response

```json
{
  "success": true,
  "data": { },
  "message": "Optional message",
  "pagination": {
    "total": 100,
    "page": 1,
    "per_page": 20,
    "pages": 5
  }
}
```

### Error Response

```json
{
  "success": false,
  "message": "Error description",
  "errors": {
    "field_name": "error message"
  }
}
```

## Database Models

### User

- Authentication and profile information
- Roles and permissions
- Wallet address (UUID)
- 2FA secret
- Account status tracking

### UserProfile

- Extended user information
- Bio, location, verification status
- Profile picture URL
- Creation and update timestamps

### Role

- Admin, Staff, User
- Permissions through role name checking

### Other Models

- PasswordHistory - Tracks previous password hashes
- AuditLog - Records user actions and system events
- Vehicle - Vehicle information linked to users
- PasswordResetAudit - Tracks password reset attempts
- VinRecord - VIN record management
- Transaction - Transaction history

## Testing

### Run All Tests

```bash
pytest
```

### Run Specific Test File

```bash
pytest tests/test_api.py -v
pytest tests/test_auth.py -v
pytest tests/test_models_rbac.py -v
```

### With Coverage Report

```bash
pytest --cov=app --cov-report=html
```

Tests use an in-memory SQLite database with auto-seeded roles.

**Test Coverage:**

- API endpoints (15+ test cases)
- Authentication flows (10+ test cases)
- Database models (15+ test cases)
- RBAC and authorization

## Security Features

### Password Security

- Bcrypt hashing (cost factor 12)
- Password history prevents reuse of N passwords
- Password reset tokens expire after 1 hour
- Secure password generation with validation

### Authentication

- Session-based authentication
- HttpOnly session cookies
- CSRF protection on all forms
- 2FA support with TOTP (pyotp)
- Secure password reset via email tokens

### Rate Limiting

- Login attempts: 10 per minute
- Registration: 5 per minute
- Password change: 5 per minute
- API request limiting (configurable)

### Authorization

- Role-based access control on all endpoints
- Field-level permission checking
- Cross-user data access validation
- Admin-only operation protection

### Audit Logging

- Password reset attempt tracking
- User action audit trail
- IP address logging for security events
- Detailed logs in `app/logs/`

## Environment Variables

| Variable | Default | Notes |
|----------|---------|-------|
| FLASK_ENV | development | development, testing, production |
| SECRET_KEY | dev-key | Change in production |
| DATABASE_URL | sqlite:///elcorp.db | Use PostgreSQL in production |
| MAIL_SERVER | smtp.gmail.com | Email server |
| MAIL_PORT | 587 | Email port |
| MAIL_USERNAME | - | Email account |
| MAIL_PASSWORD | - | App password |
| MAIL_DEFAULT_SENDER | From MAIL_USERNAME | Default sender |
| PASSWORD_RESET_TOKEN_EXPIRY | 3600 | Seconds until token expires |
| PASSWORD_HISTORY_COUNT | 5 | Number of passwords to check |
| REQUIRE_2FA_REAUTH | false | Require 2FA for sensitive ops |
| API_ITEMS_PER_PAGE | 20 | Default page size |
| ADMINS | - | Comma-separated admin emails |

## Database Migrations

```bash
# Create new migration
flask db migrate -m "Description"

# Apply migration
flask db upgrade

# Rollback last migration
flask db downgrade

# Check current revision
flask db current

# View migration history
flask db history
```

## Logging

Application logs are saved to `app/logs/`:

- `app.log` - General application logs
- `api.log` - REST API endpoint logs
- `password_reset_audit.log` - Password reset audit trail

## Production Deployment

### Prerequisites

1. Python 3.10+
2. PostgreSQL database
3. Email service (Gmail, SendGrid, etc.)
4. SSL/TLS certificate for HTTPS

### Using Gunicorn

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 wsgi:app
```

### Docker Deployment

```dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "wsgi:app"]
```

## Troubleshooting

### "No module named 'app'"

Ensure you're running from the project root and virtualenv is activated.

```bash
# Verify virtualenv is activated
which python  # or where python.exe on Windows
# Should show path inside .venv
```

### Database errors

```bash
# Reset database (development only)
python reset_db.py
```

### Import or dependency errors

```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### Tests fail

```bash
# Run with verbose output
pytest -vv --tb=short
```

### Port already in use

```bash
# Use a different port
flask run --port 5001

# Or kill process on port 5000
lsof -i :5000  # Linux/Mac
kill -9 <PID>
```

## Contributing

1. Create a feature branch (`git checkout -b feature/name`)
2. Make changes and write tests
3. Commit changes (`git commit -am 'Add feature'`)
4. Push to branch (`git push origin feature/name`)
5. Create a Pull Request

## Additional Documentation

For more detailed information, see:

- **[DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md)** - Developer quick reference and code patterns
- **[IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)** - Technical implementation details
- **[PROJECT_COMPLETION_CHECKLIST.md](PROJECT_COMPLETION_CHECKLIST.md)** - Feature verification checklist
- **[DOCUMENTATION_INDEX.md](DOCUMENTATION_INDEX.md)** - Complete documentation navigation
- **[docs/SERVICE_REQUEST_SYSTEM.md](docs/SERVICE_REQUEST_SYSTEM.md)** - Service Request Workflow System documentation
- **[docs/SERVICE_REQUEST_QUICK_START.md](docs/SERVICE_REQUEST_QUICK_START.md)** - Service Request quick start guide
- **[docs/DASHBOARD_GUIDE.md](docs/DASHBOARD_GUIDE.md)** - Dashboards and Analytics documentation

## Service Request Workflow System

A complete workflow management system for handling user requests through submission, review, approval, and completion stages:

### Key Features

- User request submission with draft save capability
- Role-based workflow transitions (User → Staff → Admin)
- Automated email notifications for all status changes
- Complete audit trail with ServiceRequestHistory tracking
- Comprehensive REST API with 10+ endpoints
- Full RBAC permission enforcement

### Quick Links

- **[Service Request System Documentation](docs/SERVICE_REQUEST_SYSTEM.md)** - Complete API docs and workflow rules
- **[Service Request Quick Start](docs/SERVICE_REQUEST_QUICK_START.md)** - Setup guide with curl examples
- **[Test Suite](tests/test_service_requests.py)** - 50+ test cases covering all scenarios

### Workflow States

```
Draft → Submitted → In Review → Approved/Rejected → Completed
```

### Roles

- **User**: Create and submit requests
- **Staff**: Review and move requests to in_review
- **Admin**: Approve/reject/complete requests and assign to staff

## Dashboards & Analytics

Comprehensive analytics and monitoring dashboards with role-based views, advanced filtering, and export capabilities.

### Features

- **Admin Dashboard** - System-wide metrics, trends, staff workload, SLA tracking
- **Staff Dashboard** - Personal workload, assigned requests, performance metrics
- **Filtered Requests** - Advanced filtering with multiple criteria (status, priority, category, date range)
- **CSV/PDF Exports** - Generate reports for requests, performance, and analytics
- **Real-time Analytics** - 15+ aggregation functions (status counts, trends, averages)
- **Performance Optimized** - Database indices on frequently-queried columns

### Quick Start

```bash
# Admin summary dashboard
curl -H "Authorization: Bearer <token>" \
  http://localhost:5000/api/dashboard/admin/summary

# Staff workload (last 30 days)
curl -H "Authorization: Bearer <token>" \
  http://localhost:5000/api/dashboard/admin/workload?days=30

# Filtered requests (open, high priority)
curl -H "Authorization: Bearer <token>" \
  "http://localhost:5000/api/dashboard/requests/filtered?status=open&priority=high"

# Export to CSV
curl -H "Authorization: Bearer <token>" \
  "http://localhost:5000/api/dashboard/export/requests?format=csv" -o requests.csv
```

### Dashboard Endpoints

**Admin Only:**

- `GET /api/dashboard/admin/summary` - System metrics and overview
- `GET /api/dashboard/admin/trends` - Historical trends (requests created/completed)
- `GET /api/dashboard/admin/workload` - Staff workload distribution
- `GET /api/dashboard/admin/sla-breaches` - Overdue requests tracking

**Staff:**

- `GET /api/dashboard/staff/summary` - Personal summary
- `GET /api/dashboard/staff/my-workload` - Assigned requests with filtering
- `GET /api/dashboard/staff/performance` - Completion metrics and trends

**Shared:**

- `GET /api/dashboard/requests/filtered` - Advanced filtering (role-scoped)
- `GET /api/dashboard/export/requests` - CSV/PDF export

### Filtering Options

```
status    - open, in_progress, completed
priority  - high, medium, low
category  - hardware, software, network, other
date_from - YYYY-MM-DD
date_to   - YYYY-MM-DD
assigned_to - Staff user ID (admin only)
sort_by   - created, updated, priority, status
sort_order - asc, desc
page      - Page number (default 1)
per_page  - Items per page (default 10, max 100)
```

### Complete Documentation

See **[docs/DASHBOARD_GUIDE.md](docs/DASHBOARD_GUIDE.md)** for:

- Detailed endpoint reference with all parameters
- Filter combinations and examples
- RBAC enforcement rules
- Export functionality guide
- Performance optimization tips
- Integration examples (HTML, React)
- Troubleshooting

## Project Statistics

| Metric | Value |
|--------|-------|
| REST API Endpoints | 32+ (14 original + 10 service request + 8 dashboard) |
| Dashboard Endpoints | 8 (4 admin + 3 staff + 1 shared) |
| Analytics Functions | 15+ (aggregations, trends, distribution) |
| Database Models | 11 (added ServiceRequest, ServiceRequestHistory) |
| Database Indices | 5 (status, priority, created_at, created_by, assigned_to) |
| Test Cases | 135+ (35+ original + 50+ service request + 50+ dashboard) |
| Lines of API Code | 1,800+ |
| Lines of Test Code | 2,000+ |
| Lines of Documentation | 4,500+ |
| RBAC Decorators | 6+ |

## License

Proprietary - Elcorp Namibia

## Support

For issues, questions, or contributions, please contact the development team.
