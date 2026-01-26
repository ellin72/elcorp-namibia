# Elcorp Namibia Frontend

Frontend React + Vite application with three independent portals: User, Staff, and Admin.

## Prerequisites

- Node.js 18+ and npm/yarn
- Flask backend running on `http://localhost:5000`

## Setup

```bash
cd frontend
npm install
```

## Environment Variables

Create `.env` file:

```env
VITE_API_BASE_URL=http://localhost:5000/api/v1
VITE_APP_NAME=Elcorp Namibia
VITE_ENABLE_NOTIFICATIONS=true
```

## Development

```bash
npm run dev
```

Access the portals:

- User Portal: <http://localhost:5173/user>
- Staff Portal: <http://localhost:5173/staff>
- Admin Portal: <http://localhost:5173/admin>

## Building

```bash
npm run build
npm run preview
```

## Testing

```bash
npm run test              # Unit tests
npm run test:ui         # Test UI
npm run test:coverage   # Coverage report
npm run e2e             # E2E tests
npm run e2e:ui          # E2E test UI
```

## Code Quality

```bash
npm run lint            # ESLint
npm run format          # Prettier
npm run type-check      # TypeScript
```

## Project Structure

```
src/
├── apps/                 # Three portals
│   ├── user-portal/
│   ├── staff-portal/
│   └── admin-portal/
├── shared/              # Shared code
│   ├── components/
│   ├── hooks/
│   ├── contexts/
│   ├── api/
│   ├── types/
│   ├── utils/
│   └── styles/
├── test/                # Test setup
└── main.tsx            # Entry point
```

## API Integration

The frontend expects the Flask backend to provide:

### Authentication Endpoints

- `POST /api/v1/auth/login` - User login
- `POST /api/v1/auth/register` - User registration
- `POST /api/v1/auth/logout` - User logout
- `POST /api/v1/auth/refresh` - Refresh JWT token
- `POST /api/v1/auth/logout-everywhere` - Logout all devices

### User Endpoints

- `GET /api/v1/users` - List users (admin)
- `GET /api/v1/users/{id}` - Get user
- `PUT /api/v1/users/{id}` - Update user (admin)
- `GET /api/v1/me` - Current user
- `GET /api/v1/me/profile` - Current user profile
- `PUT /api/v1/me/profile` - Update profile

### Service Request Endpoints

- `GET /api/v1/service-requests` - List all (admin/staff)
- `GET /api/v1/service-requests/mine` - User's requests
- `GET /api/v1/service-requests/assigned` - Assigned to staff
- `POST /api/v1/service-requests` - Create request
- `GET /api/v1/service-requests/{id}` - Get request
- `PUT /api/v1/service-requests/{id}` - Update request
- `PATCH /api/v1/service-requests/{id}/status` - Update status

See [MOBILE_INTEGRATION.md](../docs/MOBILE_INTEGRATION.md) for detailed API specs.

## Deployment

### Vercel/Netlify

```bash
npm run build
# Deploy dist/ folder
```

### Docker

```bash
docker build -f Dockerfile.frontend -t elcorp-frontend .
docker run -p 3000:80 elcorp-frontend
```

## Contributing

- Follow ESLint rules
- Format with Prettier
- Write tests for new features
- Use TypeScript strict mode
- Semantic HTML for accessibility

## License

Proprietary - Elcorp Namibia
