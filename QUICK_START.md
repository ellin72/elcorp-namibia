# Quick Start Guide - Elcorp Namibia Frontend & API

## 🚀 5-Minute Setup

### Prerequisites

- Node.js 18+ and npm
- Python 3.9+ and pip
- PostgreSQL or SQLite (for database)

---

## Backend Setup (Flask)

### 1. Install Dependencies

```bash
cd /path/to/elcorp-namibia
pip install -r requirements.txt
```

### 2. Create/Update .env

```bash
# Copy the existing .env and add JWT config
cat >> .env << EOF

# JWT Configuration
JWT_SECRET_KEY=your-very-secret-key-here-change-in-production
JWT_ACCESS_TOKEN_EXPIRES=900
JWT_REFRESH_TOKEN_EXPIRES=604800

# CORS for Frontend
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
EOF
```

### 3. Run Migrations

```bash
flask db upgrade
```

### 4. Seed Default Data (if needed)

```bash
python -c "
from app import create_app, db
from app.models import Role

app = create_app()
with app.app_context():
    if not Role.query.first():
        db.session.add(Role(name='admin', description='Administrator'))
        db.session.add(Role(name='staff', description='Staff Member'))
        db.session.add(Role(name='user', description='Regular User'))
        db.session.commit()
        print('Roles created!')
"
```

### 5. Start Backend

```bash
python -m flask run
# Server runs on http://localhost:5000
```

---

## Frontend Setup (React + Vite)

### 1. Navigate to Frontend

```bash
cd frontend
```

### 2. Install Dependencies

```bash
npm install
```

### 3. Create .env (Copy from example)

```bash
cp .env.example .env
# Update if needed (default values work for local dev)
```

### 4. Start Dev Server

```bash
npm run dev
# Frontend runs on http://localhost:5173
```

---

## 🎯 Access the Portals

### User Portal

👤 **URL**: <http://localhost:5173/user/login>

**Test Credentials** (after creating a user via register):

- Email: <user@example.com>
- Password: (your password)

**Pages**:

- Login: `/user/login`
- Register: `/user/register`
- Dashboard: `/user/dashboard`
- Profile: `/user/profile`
- Service Requests: `/user/service-requests`

### Staff Portal

👨‍💼 **URL**: <http://localhost:5173/staff>

(Placeholder - under development)

### Admin Portal

👑 **URL**: <http://localhost:5173/admin>

(Placeholder - under development)

---

## 🧪 Test the API

### 1. Register a User

```bash
curl -X POST http://localhost:5000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "John Doe",
    "username": "johndoe",
    "email": "john@example.com",
    "phone": "+234805555555",
    "password": "SecurePassword123!"
  }'
```

### 2. Login

```bash
curl -X POST http://localhost:5000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "password": "SecurePassword123!",
    "device_id": "device_12345"
  }'

# Response:
# {
#   "success": true,
#   "data": {
#     "access_token": "eyJ...",
#     "refresh_token": "eyJ...",
#     "user": {...}
#   }
# }
```

### 3. Get Current User

```bash
curl -X GET http://localhost:5000/api/v1/me \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "X-Device-ID: device_12345"
```

### 4. Create Service Request

```bash
curl -X POST http://localhost:5000/api/v1/service-requests \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "X-Device-ID: device_12345" \
  -d '{
    "title": "VIN Verification",
    "description": "Need to verify vehicle identification number",
    "category": "compliance",
    "priority": "high"
  }'
```

---

## 📚 Key Files to Know

### Frontend

**Configuration**:

- `frontend/package.json` - Dependencies
- `frontend/.env` - Environment variables
- `frontend/vite.config.ts` - Vite configuration

**Core**:

- `frontend/src/App.tsx` - Main router
- `frontend/src/main.tsx` - Entry point
- `frontend/src/shared/contexts/AuthContext.tsx` - Auth state

**Components**:

- `frontend/src/shared/components/` - Reusable components
- `frontend/src/shared/api/client.ts` - Axios instance

**Portals**:

- `frontend/src/apps/user-portal/` - User portal routes
- `frontend/src/apps/staff-portal/` - Staff portal routes
- `frontend/src/apps/admin-portal/` - Admin portal routes

### Backend

**API v1**:

- `app/api_v1/__init__.py` - Blueprint definition
- `app/api_v1/auth_routes.py` - JWT endpoints
- `app/api_v1/users_routes.py` - User endpoints
- `app/api_v1/service_requests_routes.py` - Request endpoints

**Database**:

- `app/models.py` - Models (including DeviceToken)
- `migrations/` - Database migrations

**Configuration**:

- `app/__init__.py` - Flask app setup with CORS

---

## 🔑 Important Headers

### For All API Requests

```
Content-Type: application/json
X-Device-ID: device_abc123xyz  // Recommended for mobile
X-Requested-With: XMLHttpRequest
```

### For Authenticated Requests

```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

---

## 🛠️ Common Commands

### Frontend

```bash
npm run dev          # Start dev server
npm run build        # Production build
npm run preview      # Preview production build
npm run lint         # Check code quality
npm run format       # Auto-format code
npm run test         # Run tests
npm run e2e          # Run E2E tests
```

### Backend

```bash
flask run            # Start server
flask db migrate     # Create migration
flask db upgrade     # Run migrations
python -m pytest     # Run tests
```

---

## 📖 Documentation

### Main Documents

- [Frontend Architecture](./FRONTEND_ARCHITECTURE.md) - Design decisions and structure
- [Mobile Integration Guide](./docs/MOBILE_INTEGRATION.md) - API reference for mobile
- [Frontend Setup](./frontend/README.md) - Frontend-specific setup
- [Implementation Complete](./IMPLEMENTATION_COMPLETE.md) - Full summary

---

## 🐛 Troubleshooting

### CORS Errors

- Ensure backend has CORS enabled: check `app/__init__.py`
- Verify frontend origin in `.env`'s `CORS_ORIGINS`
- Backend must be running on port 5000

### 401 Unauthorized Errors

- Token may have expired (15 min expiry)
- Check Authorization header format: `Bearer <token>`
- Verify device_id is being sent as header

### Cannot Find /api/v1/

- Check backend is running (flask run)
- Verify URL is correct: `http://localhost:5000/api/v1/...`
- Check FLASK_ENV is not blocking the v1 blueprint

### Frontend Won't Load

- Check Node.js version (18+)
- Clear node_modules: `rm -rf node_modules && npm install`
- Check port 5173 isn't in use: `lsof -i :5173`

---

## 🔐 Default Roles

After seeding, these roles are available:

- **admin**: Full access to all portals and endpoints
- **staff**: Access to staff portal, handle service requests
- **user**: Access to user portal, create requests

---

## 📱 Mobile Integration

### For Mobile Apps

1. Use `http://localhost:5000/api/v1/` endpoints
2. Include `X-Device-ID` header with device identifier
3. Store refresh token securely (encrypted storage)
4. Implement automatic token refresh on 401
5. Handle offline scenarios with request queuing

See [Mobile Integration Guide](./docs/MOBILE_INTEGRATION.md) for details.

---

## 🚀 Next Steps

### 1. Complete User Portal Pages

- Register page with email verification
- Dashboard with service request stats
- Service request creation form
- Request status tracking
- Notifications inbox

### 2. Implement Staff Portal

- Dashboard with assigned requests
- Status update functionality
- Performance metrics
- Request reassignment

### 3. Build Admin Portal

- User management (CRUD)
- Role assignment
- Service request control
- Reports and exports
- Audit log viewer

### 4. Add Features

- Real-time notifications (WebSocket)
- File uploads
- Advanced reporting with charts
- 2FA management
- Email notifications

---

## 📞 Support

### Documentation

- [Full API Reference](./docs/MOBILE_INTEGRATION.md)
- [Frontend Architecture](./FRONTEND_ARCHITECTURE.md)
- [Implementation Details](./IMPLEMENTATION_COMPLETE.md)

### Code Examples

- **Login Flow**: `frontend/src/apps/user-portal/pages/LoginPage.tsx`
- **Auth Context**: `frontend/src/shared/contexts/AuthContext.tsx`
- **API Client**: `frontend/src/shared/api/client.ts`
- **JWT Routes**: `app/api_v1/auth_routes.py`

---

## ✅ Checklist

- [ ] Backend running on port 5000
- [ ] Frontend running on port 5173
- [ ] Database migrations applied
- [ ] Default roles seeded
- [ ] CORS configured
- [ ] JWT config in .env
- [ ] User registered
- [ ] Can login via UI
- [ ] API endpoints responding
- [ ] Tokens being generated

---

**Ready to start development!** 🎉
