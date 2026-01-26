# Elcorp Namibia - Frontend Architecture

## Executive Summary

This document outlines the frontend architecture for building three independent portals (User, Staff, Admin) with modern best practices for mobile-first development, accessibility, and security.

## Architecture Decision: React + Vite

**Rationale:**

- **Separation of Concerns**: Frontend and backend are independent, allowing parallel development
- **Mobile-First**: React ecosystem has excellent mobile libraries (React Native compatible patterns)
- **Developer Experience**: Vite provides fast HMR and optimized builds
- **Scalability**: Three portals can share code (components, hooks, API client) but deploy independently
- **JWT Authentication**: Native support via context API and secure token management
- **Testing**: Mature ecosystem (React Testing Library, Vitest, Playwright)

**NOT Flask Templates because:**

- Server-rendered templates make mobile API hardening complex
- Would require duplicating auth logic (server + client)
- Mobile apps (iOS/Android) would have different integration needs
- Scaling to multiple portals becomes harder with one monolithic app

---

## Project Structure

```
elcorp-namibia/
├── frontend/                           # New React + Vite app
│   ├── src/
│   │   ├── apps/                       # Three independent portals
│   │   │   ├── user-portal/
│   │   │   │   ├── components/
│   │   │   │   ├── pages/
│   │   │   │   ├── hooks/
│   │   │   │   └── index.tsx
│   │   │   ├── staff-portal/
│   │   │   └── admin-portal/
│   │   ├── shared/                     # Shared across portals
│   │   │   ├── components/             # Auth, Layout, Toast, Modal, etc.
│   │   │   ├── hooks/                  # useAuth, useApi, useNotifications
│   │   │   ├── contexts/               # AuthContext
│   │   │   ├── api/                    # axios client + endpoints
│   │   │   ├── types/                  # TypeScript interfaces
│   │   │   ├── utils/                  # helpers, validators
│   │   │   └── styles/                 # global CSS/SCSS
│   │   └── main.tsx                    # Entry point with routing
│   ├── public/                         # Static assets
│   ├── tests/                          # E2E + integration tests
│   ├── vite.config.ts
│   ├── package.json
│   ├── tsconfig.json
│   └── .env.example
└── backend/                            # Existing Flask app
    └── (enhanced with /api/v1, JWT, mobile features)
```

---

## Technology Stack

### Frontend

- **Framework**: React 18+ with TypeScript
- **Build Tool**: Vite
- **Routing**: React Router v6
- **UI Framework**: Bootstrap React (react-bootstrap) or Shadcn/ui (headless, more control)
- **HTTP Client**: Axios with interceptors
- **State Management**: React Context API + useReducer (no Redux for this scope)
- **Forms**: React Hook Form + Zod validation
- **Notifications**: React Hot Toast or Custom Toast
- **Testing**: Vitest, React Testing Library (unit), Playwright (E2E)
- **Styling**: Tailwind CSS + CSS Modules for component-scoped styles
- **Build**: TypeScript, ESLint, Prettier

### Backend Enhancements

- **API Versioning**: `/api/v1` namespace
- **Authentication**: JWT (access + refresh tokens)
- **Rate Limiting**: Per-device (not just IP)
- **Security**: CORS, CSRF (if needed), headers
- **Device Tracking**: Device ID for logout-everywhere feature

---

## Authentication Flow

### JWT Token Strategy

```
User Login (POST /api/v1/auth/login)
  ↓
Backend returns:
  - access_token (JWT, 15 minutes expiry)
  - refresh_token (HttpOnly cookie or localStorage, 7 days expiry)
  - user { id, role, name, email }
  ↓
Frontend stores access_token in memory
  - refresh_token in secure storage (HttpOnly cookie preferred, or localStorage)
  ↓
On each API request:
  - Inject Authorization: Bearer <access_token> header
  ↓
If 401 Unauthorized:
  - Automatically refresh using refresh_token
  - Retry original request
  - If refresh fails, redirect to login
  ↓
Logout (POST /api/v1/auth/logout)
  - Backend invalidates refresh_token
  - Clear tokens from client
  - Redirect to login
```

### Logout Everywhere

- User can see "Active Sessions" in profile
- Click "Logout from All Devices" → POST `/api/v1/auth/logout-everywhere`
- Backend invalidates all device tokens for that user
- All sessions automatically redirected to login on next API call

---

## Role-Based Routing

```typescript
// ProtectedRoute component
<ProtectedRoute role="user">
  <UserDashboard />
</ProtectedRoute>

// Checks:
1. User is authenticated (valid JWT)
2. User has required role
3. Otherwise: redirect to login or unauthorized page
```

### Roles

- **admin**: Access to /admin portal, all management features
- **staff**: Access to /staff portal, assigned service requests, performance metrics
- **user**: Access to /user portal, create requests, view own requests

---

## API Client Architecture

### Axios Interceptors

```typescript
// request interceptor
- Inject JWT access_token header
- Add X-Device-ID, User-Agent for mobile tracking
- Add request timestamp for logging

// response interceptor
- Catch 401 errors
- If 401: trigger token refresh
- If refresh succeeds: retry original request
- If refresh fails: logout user, redirect to login

// error handler
- Normalize error response to consistent format
- Log errors (non-sensitive data only)
- Return user-friendly error messages
```

---

## Security Considerations

### CSRF Protection

- If using cookies: Implement CSRF tokens (Flask-WTF provides this)
- If using JWT in Authorization header: CSRF not required (tokens not sent in cookies)
- Recommendation: Use JWT in header, Accept POST/PUT/DELETE requests only from authenticated origins

### XSS Prevention

- React escapes HTML by default
- Use `dangerouslySetInnerHTML` only for trusted content
- Sanitize user input with DOMPurify if rendering HTML content
- Content Security Policy (CSP) headers from backend

### Token Storage

- **Access Token**: Memory (cleared on refresh) - convenient, secure
- **Refresh Token**: HttpOnly cookie (preferred) or localStorage
- **HttpOnly Cookies**: Immune to XSS, but vulnerable to CSRF
- **JWT in Header**: Standard practice, requires CSRF protection if cookies also present

### Secure Password Reset

- Backend generates time-limited token
- Frontend shows form with token in URL
- User submits new password
- Backend validates token, updates password, invalidates all tokens

---

## Accessibility & UX

### WCAG 2.1 AA Compliance

- ✅ Semantic HTML (header, nav, main, footer, section, article)
- ✅ ARIA labels for images, buttons, form inputs
- ✅ Keyboard navigation (Tab through all interactive elements)
- ✅ Color contrast ratios ≥ 4.5:1 for text
- ✅ Focus indicators visible
- ✅ Form validation messages linked to inputs (aria-describedby)
- ✅ Skip-to-main link for keyboard users

### Mobile-First Design

- Start with mobile layout, enhance for larger screens
- Touch-friendly buttons (48px minimum)
- Hamburger menu for mobile navigation
- Responsive images (srcset)
- Optimized font sizes (16px minimum for input fields)

### User Experience

- Loading states for all async operations
- Error messages clear and actionable
- Toast notifications for feedback
- Optimistic UI updates where safe
- Breadcrumb navigation for orientation
- Empty states with helpful messages

---

## Mobile Readiness

### API Versioning

- All endpoints under `/api/v1/`
- Future changes: `/api/v2/` with backward compatibility plan
- Mobile apps hardcode version; easy to support multiple versions simultaneously

### Device Tracking

- `X-Device-ID` header for mobile requests (generated on first login)
- Backend tracks device tokens, enables logout-everywhere
- Optional: device name/type for "active sessions" view

### Rate Limiting

- Per-device rate limiting (configurable per endpoint)
- Public endpoints: looser limits
- Auth endpoints: strict limits (brute force protection)
- User endpoints: moderate limits

### Token Refresh

- Automatic background refresh before expiry
- Handles offline → online transitions gracefully
- Retry failed requests after token refresh

### Offline Patterns

- Detect connection status (navigator.onLine)
- Queue failed requests, retry when online
- Show offline indicator to user
- Cache critical data (user profile, recent requests)

### Error Response Format

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Email is invalid",
    "details": {
      "field": "email",
      "issue": "invalid_format"
    }
  }
}
```

---

## State Management Strategy

### Local State

- React `useState` for component-level state
- `useReducer` for complex component state

### Global State (Shared)

- **AuthContext**: Current user, token, login/logout
- **NotificationsContext**: Toast notifications (optional)
- **AppContext**: App-wide settings (theme, language)

### Server State (API)

- React Query (TanStack Query) for caching, sync
- Or: Custom hooks with useEffect + useState

### Preference

For this project: **React Context + Custom Hooks** (simpler than Redux, sufficient for three portals)

---

## Testing Strategy

### Unit Tests (Vitest + React Testing Library)

- Component rendering
- User interactions (click, input, form submission)
- Custom hooks logic
- Utility functions

### Integration Tests

- Auth flow (register → login → access protected page)
- Role-based routing (user cannot access admin routes)
- API calls with mock responses
- Token refresh on 401

### E2E Tests (Playwright)

- Real browser, real backend
- Main workflows per portal:
  - **User**: Register → Create Request → View Status
  - **Staff**: View Assigned → Update Status
  - **Admin**: Manage Users → View Reports
- Mobile viewport testing

---

## Deployment

### Frontend Deployment Options

1. **Vercel/Netlify**: Ideal for Vite React apps, automatic deployments
2. **AWS S3 + CloudFront**: Static hosting with CDN
3. **Same server as backend**: Serve from Flask (behind /frontend path)
4. **Docker**: Containerize frontend, orchestrate with backend

### Build & Optimization

- Vite tree-shaking, code splitting
- Lazy-load portals (code splitting per route)
- Image optimization (WebP, responsive sizes)
- Gzip compression

### CI/CD

- GitHub Actions (run tests, build, deploy)
- Pre-commit hooks: ESLint, Prettier, type-check
- Semantic versioning, release notes

---

## Feature Rollout

### Phase 1: MVP (Week 1-2)

- React + Vite setup
- Shared auth, API client, components
- User portal: login, profile, create request, view requests
- Basic styling (Bootstrap)

### Phase 2: Staff & Admin (Week 3)

- Staff portal: assigned requests, status update, performance
- Admin portal: user management, request control
- Role-based routing

### Phase 3: Mobile & Polish (Week 4)

- Mobile-first responsive design
- Accessibility audit + fixes
- E2E tests
- Documentation

### Phase 4: Hardening (Week 5+)

- API versioning, rate limiting per device
- Token refresh, logout-everywhere
- Advanced features (notifications, reports export)
- Performance optimization

---

## Documentation

### For Developers

- [Frontend Setup](./docs/FRONTEND_SETUP.md) - Get started guide
- [Mobile Integration](./docs/MOBILE_INTEGRATION.md) - API + mobile app patterns
- [UX Flows](./docs/UX_FLOWS.md) - User workflows, wireframes
- [Component Library](./docs/COMPONENTS.md) - Available components, usage examples

### For Users

- Portal UI includes tooltips, help links
- In-app notifications explain actions
- Error messages suggest remediation

---

## Next Steps

1. Create React + Vite project
2. Setup TypeScript, ESLint, Prettier
3. Build auth context + API client
4. Create shared components (Button, Card, Modal, Toast)
5. Implement User portal MVP
6. Implement Staff & Admin portals
7. Hardening: API versioning, JWT, mobile features
8. Testing: unit, integration, E2E
9. Documentation & deployment
