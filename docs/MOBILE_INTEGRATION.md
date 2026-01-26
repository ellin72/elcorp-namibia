# Mobile Integration Guide

## Overview

The Elcorp Namibia backend provides a comprehensive API for mobile app integration with security, device tracking, and token management built in.

## API Versioning

All mobile endpoints use the `/api/v1/` namespace:

```
https://api.elcorp.com/api/v1/...
```

This allows future versions (`/api/v2/`) to coexist without breaking existing clients.

---

## Authentication Flow

### 1. User Login

**Endpoint**: `POST /api/v1/auth/login`

**Request**:

```json
{
  "email": "user@example.com",
  "password": "password123",
  "device_id": "device_ABC123XYZ"  // Optional but recommended
}
```

**Response** (201):

```json
{
  "success": true,
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "user": {
      "id": 1,
      "username": "john_doe",
      "email": "user@example.com",
      "full_name": "John Doe",
      "role": "user",
      "is_admin": false
    }
  },
  "message": "Login successful"
}
```

### 2. Using Access Tokens

Include the access token in all authenticated requests:

```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Token Expiry**: 15 minutes

### 3. Refreshing Tokens

When access token expires, use the refresh token:

**Endpoint**: `POST /api/v1/auth/refresh`

**Request**:

```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response** (200):

```json
{
  "success": true,
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  },
  "message": "Token refreshed successfully"
}
```

**Refresh Token Expiry**: 7 days

### 4. Logout

**Endpoint**: `POST /api/v1/auth/logout`

**Headers**:

```
Authorization: Bearer <access_token>
X-Device-ID: device_ABC123XYZ
```

**Response** (200):

```json
{
  "success": true,
  "data": {},
  "message": "Logout successful"
}
```

This invalidates the token for the current device only.

### 5. Logout from All Devices

**Endpoint**: `POST /api/v1/auth/logout-everywhere`

**Headers**:

```
Authorization: Bearer <access_token>
```

**Response** (200):

```json
{
  "success": true,
  "data": {},
  "message": "Logged out from all devices successfully"
}
```

This invalidates all tokens for the user across all devices.

---

## Device ID Management

The `X-Device-ID` header tracks which device is making requests:

```
X-Device-ID: device_1234567890_abcdef
```

### Generating Device ID

On first app launch:

```javascript
function getOrCreateDeviceId() {
  let deviceId = localStorage.getItem('device_id');
  if (!deviceId) {
    deviceId = `device_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    localStorage.setItem('device_id', deviceId);
  }
  return deviceId;
}
```

### Benefits

1. **Logout Everywhere**: Server knows which tokens belong to which device
2. **Rate Limiting**: Per-device rate limits prevent abuse
3. **Security**: Compromised token on one device doesn't affect others
4. **User Experience**: See active sessions, revoke specific devices

---

## Token Refresh Strategy

### Automatic Refresh (Recommended)

```javascript
// Setup axios interceptor to auto-refresh
api.interceptors.response.use(
  response => response,
  async error => {
    const originalRequest = error.config;
    
    // If 401 and not already retrying
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      
      try {
        const refreshToken = localStorage.getItem('refresh_token');
        const response = await axios.post('/api/v1/auth/refresh', {
          refresh_token: refreshToken
        });
        
        const newAccessToken = response.data.data.access_token;
        localStorage.setItem('access_token', newAccessToken);
        
        // Retry original request with new token
        originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
        return axios(originalRequest);
      } catch (refreshError) {
        // Refresh failed, redirect to login
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }
    
    return Promise.reject(error);
  }
);
```

### Token Expiry Handling

Monitor token expiry and refresh before it expires:

```javascript
function startTokenRefreshTimer() {
  const token = localStorage.getItem('access_token');
  const decoded = jwtDecode(token);
  const expiresIn = decoded.exp * 1000 - Date.now();
  
  // Refresh 1 minute before expiry
  setTimeout(() => {
    refreshAccessToken();
  }, expiresIn - 60000);
}
```

---

## Rate Limiting

### Limits per Endpoint

| Endpoint | Rate Limit |
|----------|-----------|
| `/auth/login` | 5 requests/minute |
| `/auth/register` | 3 requests/minute |
| `/auth/refresh` | 10 requests/minute |
| `/auth/logout` | 10 requests/minute |
| Other endpoints | 30 requests/minute (default) |

### Handling Rate Limit (429)

```json
{
  "success": false,
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Too many requests. Please try again later."
  }
}
```

**Solution**: Implement exponential backoff retry:

```javascript
async function retryWithBackoff(fn, maxRetries = 3) {
  let lastError;
  for (let i = 0; i < maxRetries; i++) {
    try {
      return await fn();
    } catch (error) {
      if (error.response?.status === 429) {
        lastError = error;
        const delay = Math.pow(2, i) * 1000; // 1s, 2s, 4s
        await new Promise(resolve => setTimeout(resolve, delay));
      } else {
        throw error;
      }
    }
  }
  throw lastError;
}
```

---

## Error Response Format

All errors follow consistent format:

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable message",
    "details": {}  // Optional, context-specific details
  }
}
```

### Common Error Codes

| Code | Status | Meaning |
|------|--------|---------|
| `UNAUTHORIZED` | 401 | Invalid/expired token |
| `INVALID_CREDENTIALS` | 401 | Wrong email/password |
| `FORBIDDEN` | 403 | Insufficient permissions |
| `NOT_FOUND` | 404 | Resource not found |
| `VALIDATION_ERROR` | 422 | Input validation failed |
| `CONFLICT` | 409 | Resource already exists |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |
| `INTERNAL_ERROR` | 500 | Server error |

---

## Offline-Safe Patterns

### Request Queuing

When offline, queue requests and retry when online:

```javascript
class RequestQueue {
  constructor() {
    this.queue = [];
    this.online = navigator.onLine;
    
    window.addEventListener('online', () => this.onOnline());
    window.addEventListener('offline', () => this.online = false);
  }
  
  async request(config) {
    if (this.online) {
      return axios(config);
    } else {
      // Queue for retry
      return new Promise((resolve, reject) => {
        this.queue.push({ config, resolve, reject });
      });
    }
  }
  
  async onOnline() {
    this.online = true;
    const queue = this.queue.splice(0); // Clear queue
    
    for (const { config, resolve, reject } of queue) {
      try {
        const response = await axios(config);
        resolve(response);
      } catch (error) {
        reject(error);
      }
    }
  }
}
```

### Local Caching

Cache frequently accessed data:

```javascript
const cache = new Map();

async function getCachedUser(userId) {
  if (cache.has(`user_${userId}`)) {
    return cache.get(`user_${userId}`);
  }
  
  const response = await axios.get(`/api/v1/users/${userId}`);
  cache.set(`user_${userId}`, response.data);
  
  return response.data;
}
```

---

## User Endpoints

### Get Current User

**Endpoint**: `GET /api/v1/me`

**Headers**: `Authorization: Bearer <token>`

**Response** (200):

```json
{
  "success": true,
  "data": {
    "id": 1,
    "username": "john_doe",
    "email": "user@example.com",
    "full_name": "John Doe",
    "phone": "+234805555555",
    "role": "user",
    "is_admin": false,
    "last_login": "2026-01-26T10:30:00",
    "created_at": "2026-01-20T15:00:00"
  }
}
```

### Get User Profile

**Endpoint**: `GET /api/v1/me/profile`

**Response** (200):

```json
{
  "success": true,
  "data": {
    "user_id": 1,
    "bio": "Service request creator",
    "profile_picture_url": "https://...",
    "country": "Namibia",
    "city": "Windhoek",
    "phone_verified": true,
    "email_verified": true,
    "created_at": "2026-01-20T15:00:00",
    "updated_at": "2026-01-26T10:30:00"
  }
}
```

### Update User Profile

**Endpoint**: `PUT /api/v1/me/profile`

**Request**:

```json
{
  "bio": "Updated bio",
  "country": "Namibia",
  "city": "Swakopmund"
}
```

---

## Service Requests

### Get My Service Requests

**Endpoint**: `GET /api/v1/service-requests/mine?page=1&per_page=20`

**Response** (200):

```json
{
  "success": true,
  "data": [
    {
      "id": "sr-uuid-1",
      "title": "VIN Verification Request",
      "description": "Need to verify vehicle VIN",
      "category": "compliance",
      "status": "submitted",
      "priority": "high",
      "assigned_to": null,
      "created_at": "2026-01-26T09:00:00",
      "updated_at": "2026-01-26T09:00:00"
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 5,
    "pages": 1
  }
}
```

### Create Service Request

**Endpoint**: `POST /api/v1/service-requests`

**Request**:

```json
{
  "title": "VIN Verification",
  "description": "Need to verify vehicle identification number",
  "category": "compliance",
  "priority": "high"
}
```

**Response** (201):

```json
{
  "success": true,
  "data": {
    "id": "sr-uuid-123",
    "title": "VIN Verification",
    "status": "draft",
    "created_at": "2026-01-26T10:30:00"
  },
  "message": "Service request created successfully"
}
```

### Get Service Request Details

**Endpoint**: `GET /api/v1/service-requests/{request_id}`

**Response** (200):

```json
{
  "success": true,
  "data": {
    "id": "sr-uuid-123",
    "title": "VIN Verification",
    "description": "Need to verify vehicle identification number",
    "category": "compliance",
    "status": "submitted",
    "priority": "high",
    "assigned_to": null,
    "created_by": 1,
    "created_at": "2026-01-26T10:30:00",
    "updated_at": "2026-01-26T10:30:00"
  }
}
```

---

## Headers

All requests should include:

```
Content-Type: application/json
Authorization: Bearer <access_token>  // For authenticated endpoints
X-Device-ID: device_ABC123XYZ        // Recommended for all mobile requests
X-Requested-With: XMLHttpRequest     // Helps identify mobile clients
User-Agent: MyApp/1.0                // App name and version
```

---

## Best Practices

### 1. Security

- ✅ Always use HTTPS in production
- ✅ Never expose tokens in URLs or logs
- ✅ Store refresh tokens securely (encrypted storage if possible)
- ✅ Clear tokens on logout
- ✅ Validate SSL certificates

### 2. Performance

- ✅ Implement request caching
- ✅ Queue requests when offline
- ✅ Use pagination (default 20 items/page)
- ✅ Minimize payload sizes
- ✅ Gzip compress responses

### 3. Reliability

- ✅ Implement auto-refresh for tokens
- ✅ Retry failed requests with exponential backoff
- ✅ Handle 429 (rate limit) gracefully
- ✅ Show offline indicator to user
- ✅ Queue critical requests (like service request creation)

### 4. User Experience

- ✅ Show loading states for async operations
- ✅ Display error messages from API
- ✅ Implement pull-to-refresh for lists
- ✅ Deep link to requests (share request ID)
- ✅ Handle network timeouts gracefully

---

## Environment Configuration

### Production

```
API_BASE_URL=https://api.elcorp.com/api/v1
ENABLE_LOGGING=true
ENABLE_ANALYTICS=true
```

### Development

```
API_BASE_URL=http://localhost:5000/api/v1
ENABLE_LOGGING=true
ENABLE_ANALYTICS=false
```

---

## Troubleshooting

### Token Refresh Loop

If getting infinite 401 errors:

1. Check refresh token validity
2. Verify token is being stored correctly
3. Check system clock synchronization
4. Clear cache and retry

### Rate Limiting

If getting 429 errors:

1. Implement exponential backoff
2. Queue requests
3. Check for duplicate requests
4. Contact support if limit seems wrong

### CORS Errors

If getting CORS errors:

1. Verify frontend origin in server config
2. Check headers are correctly sent
3. Ensure Content-Type is application/json
4. Try preflight request

---

## Support

For API issues:

- Email: <api-support@elcorp.com>
- Slack: #api-support channel
- Documentation: <https://docs.elcorp.com/api>
