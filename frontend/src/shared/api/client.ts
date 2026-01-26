import axios, { AxiosInstance, InternalAxiosRequestConfig, AxiosResponse } from 'axios';
import { ApiErrorResponse, ApiSuccessResponse } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000/api/v1';

// Token management utilities
const tokenStorage = {
    getAccessToken: () => sessionStorage.getItem('access_token'),
    setAccessToken: (token: string) => sessionStorage.setItem('access_token', token),
    getRefreshToken: () => localStorage.getItem('refresh_token'),
    setRefreshToken: (token: string) => localStorage.setItem('refresh_token', token),
    clearTokens: () => {
        sessionStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('device_id');
    },
};

// Device ID management
const deviceStorage = {
    getDeviceId: () => {
        let deviceId = localStorage.getItem('device_id');
        if (!deviceId) {
            deviceId = `device_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
            localStorage.setItem('device_id', deviceId);
        }
        return deviceId;
    },
};

// Create axios instance
export const apiClient: AxiosInstance = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

// Track token refresh to avoid multiple simultaneous refresh attempts
let isRefreshing = false;
let failedQueue: Array<{
    resolve: (token: string) => void;
    reject: (error: unknown) => void;
}> = [];

const processQueue = (token: string | null, error: unknown = null) => {
    failedQueue.forEach((prom) => {
        if (error) {
            prom.reject(error);
        } else if (token) {
            prom.resolve(token);
        }
    });
    failedQueue = [];
};

// Request interceptor: inject auth token and device ID
apiClient.interceptors.request.use(
    (config: InternalAxiosRequestConfig) => {
        const token = tokenStorage.getAccessToken();
        const deviceId = deviceStorage.getDeviceId();

        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }

        config.headers['X-Device-ID'] = deviceId;
        config.headers['X-Requested-With'] = 'XMLHttpRequest';

        return config;
    },
    (error) => Promise.reject(error)
);

// Response interceptor: handle 401 and refresh token
apiClient.interceptors.response.use(
    (response: AxiosResponse) => response,
    async (error) => {
        const originalRequest = error.config as InternalAxiosRequestConfig & {
            _retry?: boolean;
        };

        // Handle 401 Unauthorized
        if (error.response?.status === 401 && !originalRequest._retry) {
            if (isRefreshing) {
                // Queue the request to be retried after token refresh
                return new Promise((resolve, reject) => {
                    failedQueue.push({
                        resolve: (token: string) => {
                            originalRequest.headers.Authorization = `Bearer ${token}`;
                            resolve(apiClient(originalRequest));
                        },
                        reject: (err) => reject(err),
                    });
                });
            }

            originalRequest._retry = true;
            isRefreshing = true;

            const refreshToken = tokenStorage.getRefreshToken();
            if (refreshToken) {
                try {
                    const response = await axios.post(`${API_BASE_URL}/auth/refresh`, {
                        refresh_token: refreshToken,
                    });

                    const { access_token } = response.data.data;
                    tokenStorage.setAccessToken(access_token);

                    originalRequest.headers.Authorization = `Bearer ${access_token}`;

                    // Retry failed requests
                    processQueue(access_token);
                    isRefreshing = false;

                    return apiClient(originalRequest);
                } catch (refreshError) {
                    // Refresh failed, clear tokens and redirect to login
                    tokenStorage.clearTokens();
                    processQueue(null, refreshError);
                    isRefreshing = false;

                    // Trigger logout event (handled by AuthContext)
                    window.dispatchEvent(new CustomEvent('auth:expired'));

                    return Promise.reject(refreshError);
                }
            } else {
                // No refresh token, clear and logout
                tokenStorage.clearTokens();
                isRefreshing = false;
                window.dispatchEvent(new CustomEvent('auth:expired'));
                return Promise.reject(error);
            }
        }

        return Promise.reject(error);
    }
);

// API endpoints wrapper
export const api = {
    // Auth endpoints
    auth: {
        login: (email: string, password: string, deviceId?: string) =>
            apiClient.post<ApiSuccessResponse<{
                access_token: string;
                refresh_token?: string;
                user: any;
            }>>('/auth/login', { email, password, device_id: deviceId }),

        register: (data: Record<string, unknown>) =>
            apiClient.post<ApiSuccessResponse<{ user: any }>>('/auth/register', data),

        logout: () => apiClient.post('/auth/logout'),

        logoutEverywhere: () => apiClient.post('/auth/logout-everywhere'),

        refresh: (refreshToken: string) =>
            apiClient.post<ApiSuccessResponse<{ access_token: string }>>('/auth/refresh', {
                refresh_token: refreshToken,
            }),
    },

    // User endpoints
    users: {
        list: (params?: Record<string, unknown>) =>
            apiClient.get<ApiSuccessResponse<any[]>>('/users', { params }),

        get: (userId: number) => apiClient.get<ApiSuccessResponse<any>>(`/users/${userId}`),

        update: (userId: number, data: Record<string, unknown>) =>
            apiClient.put<ApiSuccessResponse<any>>(`/users/${userId}`, data),

        delete: (userId: number) => apiClient.delete(`/users/${userId}`),

        updateRole: (userId: number, roleId: number) =>
            apiClient.put<ApiSuccessResponse<any>>(`/users/${userId}/role`, { role_id: roleId }),

        getCurrent: () => apiClient.get<ApiSuccessResponse<any>>('/me'),

        getProfile: (userId: number) =>
            apiClient.get<ApiSuccessResponse<any>>(`/profiles/${userId}`),

        updateProfile: (userId: number, data: Record<string, unknown>) =>
            apiClient.put<ApiSuccessResponse<any>>(`/profiles/${userId}`, data),

        getCurrentProfile: () => apiClient.get<ApiSuccessResponse<any>>('/me/profile'),

        updateCurrentProfile: (data: Record<string, unknown>) =>
            apiClient.put<ApiSuccessResponse<any>>('/me/profile', data),
    },

    // Service requests
    serviceRequests: {
        list: (params?: Record<string, unknown>) =>
            apiClient.get<ApiSuccessResponse<any[]>>('/service-requests', { params }),

        getMine: (params?: Record<string, unknown>) =>
            apiClient.get<ApiSuccessResponse<any[]>>('/service-requests/mine', { params }),

        getAssigned: (params?: Record<string, unknown>) =>
            apiClient.get<ApiSuccessResponse<any[]>>('/service-requests/assigned', { params }),

        get: (requestId: string) =>
            apiClient.get<ApiSuccessResponse<any>>(`/service-requests/${requestId}`),

        create: (data: Record<string, unknown>) =>
            apiClient.post<ApiSuccessResponse<any>>('/service-requests', data),

        update: (requestId: string, data: Record<string, unknown>) =>
            apiClient.put<ApiSuccessResponse<any>>(`/service-requests/${requestId}`, data),

        updateStatus: (requestId: string, status: string, notes?: string) =>
            apiClient.patch<ApiSuccessResponse<any>>(`/service-requests/${requestId}/status`, {
                status,
                notes,
            }),

        assign: (requestId: string, staffId: number) =>
            apiClient.post<ApiSuccessResponse<any>>(`/service-requests/${requestId}/assign`, {
                assigned_to: staffId,
            }),

        delete: (requestId: string) =>
            apiClient.delete(`/service-requests/${requestId}`),

        submit: (requestId: string) =>
            apiClient.post(`/service-requests/${requestId}/submit`),
    },

    // Roles
    roles: {
        list: () => apiClient.get<ApiSuccessResponse<any[]>>('/roles'),
    },

    // Health check
    health: {
        check: () => apiClient.get('/health'),
    },
};

// Utility to handle errors consistently
export const handleApiError = (error: unknown): string => {
    if (axios.isAxiosError(error)) {
        if (error.response?.data) {
            const data = error.response.data as ApiErrorResponse;
            return data.error?.message || error.message;
        }
        return error.message;
    }
    return 'An unexpected error occurred';
};

export { tokenStorage, deviceStorage };
