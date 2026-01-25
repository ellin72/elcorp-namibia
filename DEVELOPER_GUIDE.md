# Elcorp Namibia - Developer Quick Reference

## Project Setup (First Time)

```bash
# 1. Clone and navigate
git clone https://github.com/ellin72/elcorp-namibia.git
cd elcorp-namibia

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate      # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env with your settings

# 5. Initialize database
flask db upgrade
python reset_db.py

# 6. Run application
flask run
```

## Common Development Commands

```bash
# Run application
flask run

# Interactive shell
flask shell

# Database migrations
flask db init              # First time only
flask db migrate -m "..."  # Create migration
flask db upgrade           # Apply migration
flask db downgrade         # Revert migration

# Run tests
pytest                     # All tests
pytest tests/test_api.py   # Specific file
pytest -v                  # Verbose
pytest --cov=app           # With coverage

# Database reset (dev only)
python reset_db.py
```

## API Quick Reference

### Base URL

```
http://localhost:5000/api/v1
```

### Example Requests

```bash
# List all users (admin only)
curl -H "Content-Type: application/json" \
  http://localhost:5000/api/v1/users

# Create user (admin only)
curl -X POST http://localhost:5000/api/v1/users \
  -H "Content-Type: application/json" \
  -d '{
    "username": "newuser",
    "email": "new@test.com",
    "full_name": "New User",
    "phone": "1234567890",
    "password": "SecurePass123!",
    "role": "user"
  }'

# Get current user
curl http://localhost:5000/api/v1/me

# Update own profile
curl -X PUT http://localhost:5000/api/v1/me/profile \
  -H "Content-Type: application/json" \
  -d '{"bio": "My bio", "city": "Windhoek"}'

# List roles
curl http://localhost:5000/api/v1/roles
```

## Code Patterns

### Using RBAC Decorators

```python
from app.security import require_role, require_admin, can_access_user

# Admin-only endpoint
@app.route('/admin')
@require_admin
def admin_panel():
    return "Admin area"

# Multiple role options
@app.route('/staff-or-admin')
@require_role('staff', 'admin')
def staff_area():
    return "Staff/Admin area"

# Check permissions in code
from app.security import is_admin
if is_admin(current_user):
    # Do admin stuff

# Check cross-user access
if can_access_user(user_id):
    # User can access this data
```

### Creating API Endpoints

```python
from app.api.utils import (
    api_response, api_error, get_pagination_params,
    paginate_query, validate_request_json
)
from app.security import require_role
from flask import request

@bp.route("/endpoint", methods=["GET"])
@login_required
@require_role('user')
def list_items():
    # Get pagination
    page, per_page = get_pagination_params()
    
    # Build query
    query = Model.query
    
    # Apply filters
    search = request.args.get('search', '').strip()
    if search:
        query = query.filter(Model.name.ilike(f"%{search}%"))
    
    # Paginate
    items, pagination_info = paginate_query(query, page, per_page)
    
    # Return response
    return api_response(
        data=[item.to_dict() for item in items],
        paginate=pagination_info
    )

@bp.route("/endpoint", methods=["POST"])
@login_required
@require_admin
def create_item():
    # Validate JSON
    data, status, error = validate_request_json(
        required_fields=['name', 'email']
    )
    if error:
        return api_error(error, status)
    
    # Create and save
    item = Model(name=data['name'], email=data['email'])
    db.session.add(item)
    db.session.commit()
    
    # Return response
    return api_response(
        data={'id': item.id},
        message="Item created successfully",
        status_code=201
    )
```

### Creating Models

```python
from app.extensions import db
from datetime import datetime

class MyModel(db.Model):
    __tablename__ = 'my_table'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, 
                          default=datetime.utcnow, 
                          onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<MyModel {self.name}>"
```

### Writing Tests

```python
import pytest
import json
from app import db
from app.models import User, Role

class TestMyFeature:
    """Test my feature."""
    
    @pytest.fixture
    def user_with_role(self, app):
        """Create test user."""
        with app.app_context():
            role = Role.query.filter_by(name='user').first()
            user = User(
                username='testuser',
                email='test@test.com',
                phone='1234567890',
                full_name='Test User',
                role=role
            )
            user.set_password('password123')
            db.session.add(user)
            db.session.commit()
            return user
    
    def test_something(self, client, user_with_role):
        """Test something."""
        with client:
            # Login
            client.post('/auth/login', data={
                'username': 'testuser',
                'password': 'password123'
            }, follow_redirects=True)
            
            # Make request
            response = client.get('/api/v1/me')
            
            # Assert
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['data']['email'] == 'test@test.com'
```

## File Locations

### Database Models

- File: `app/models.py`
- Key classes: User, Role, UserProfile, Vehicle, etc.

### API Routes

- File: `app/api/routes.py`
- Base URL: `/api/v1`

### API Utilities

- File: `app/api/utils.py`
- Functions: Response formatting, pagination, validation

### Security/RBAC

- File: `app/security.py`
- Decorators: `@require_role`, `@require_admin`

### Templates

- Directory: `app/templates/`
- Auth templates: `app/templates/auth/`
- Dashboard: `app/templates/dashboard/`

### Tests

- Directory: `tests/`
- Test fixtures: `tests/conftest.py`
- API tests: `tests/test_api.py`
- Auth tests: `tests/test_auth.py`
- Model tests: `tests/test_models_rbac.py`

### Configuration

- Environment: `.env` (copy from `.env.example`)
- App factory: `app/__init__.py`
- Extensions: `app/extensions.py`

### Logs

- Directory: `app/logs/`
- App log: `app.log`
- API log: `api.log`
- Audit log: `password_reset_audit.log`

## Database

### User Roles

- **admin** - Full access
- **staff** - Verification and reports
- **user** - Standard user access

### Key Tables

- `user` - User accounts
- `user_profile` - Extended user info
- `role` - Role definitions
- `password_history` - Password tracking
- `audit_log` - Action logging
- `vehicle` - Vehicle records

### Common Queries

```python
# Get user by email
user = User.query.filter_by(email='user@example.com').first()

# Get all admins
admins = User.query.join(Role).filter(Role.name == 'admin').all()

# Get user's profile
profile = user.profile  # Relationship

# Get users by role
users = User.query.join(Role).filter(Role.name == 'staff').all()

# Search users
users = User.query.filter(
    User.username.ilike('%search%') | 
    User.email.ilike('%search%')
).all()
```

## Debugging

### Enable Debug Mode

```python
# In .env
FLASK_ENV=development

# Run with debug
FLASK_DEBUG=1 flask run
```

### Flask Shell

```bash
flask shell

# In shell
from app.models import User
user = User.query.first()
print(user)
```

### View Logs

```bash
# Watch logs
tail -f app/logs/app.log
tail -f app/logs/api.log
tail -f app/logs/password_reset_audit.log
```

## Troubleshooting

### Import Error

- Ensure virtualenv is activated
- Run `pip install -r requirements.txt`

### Database Error

- Check DATABASE_URL in .env
- Run `flask db upgrade`
- Or reset: `python reset_db.py`

### Test Failure

- Run with verbose: `pytest -vv`
- Check test fixtures in conftest.py
- Use `--tb=short` for shorter tracebacks

### Port Already in Use

```bash
# Change port
flask run --port 5001

# Or find and kill process on 5000
lsof -i :5000
kill -9 <PID>
```

## Environment Variables

**Development (.env)**

```env
FLASK_ENV=development
SECRET_KEY=dev-secret-key
DATABASE_URL=sqlite:///elcorp.db
MAIL_SERVER=smtp.gmail.com
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=app-password
PASSWORD_RESET_TOKEN_EXPIRY=3600
PASSWORD_HISTORY_COUNT=5
```

**Testing (pytest auto-configures)**

```env
FLASK_ENV=testing
DATABASE_URL=sqlite:///:memory:
```

## Git Workflow

```bash
# Create feature branch
git checkout -b feature/my-feature

# Make changes
git add .
git commit -m "Add my feature"

# Push and create PR
git push origin feature/my-feature

# After review, merge to main
git checkout main
git pull
git merge feature/my-feature
```

## Performance Tips

- Use pagination for large lists (default 20 per page)
- Index frequently searched columns
- Use lazy loading for relationships when appropriate
- Monitor logs for slow queries

## Security Reminders

- ✅ Always use `@login_required` on protected endpoints
- ✅ Always use `@require_role()` for role-based endpoints
- ✅ Never commit `.env` file
- ✅ Keep SECRET_KEY secret
- ✅ Use bcrypt for passwords (via `user.set_password()`)
- ✅ Validate all user input
- ✅ Use CSRF tokens on forms
- ✅ Enable HTTPS in production

---

**Last Updated:** January 25, 2026
