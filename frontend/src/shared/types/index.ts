/**
 * Core TypeScript types for Elcorp Namibia frontend
 */

export interface Role {
    id: number;
    name: 'admin' | 'staff' | 'user';
    description?: string;
}

export interface User {
    id: number;
    username: string;
    email: string;
    full_name: string;
    phone: string;
    organization?: string;
    is_active: boolean;
    is_admin: boolean;
    role: Role;
    last_login?: string;
    created_at: string;
}

export interface UserProfile {
    user_id: number;
    bio?: string;
    profile_picture_url?: string;
    location_country?: string;
    location_city?: string;
    date_of_birth?: string;
    email_verified: boolean;
    phone_verified: boolean;
    created_at: string;
    updated_at: string;
}

export interface AuthResponse {
    success: boolean;
    data: {
        access_token: string;
        refresh_token?: string;
        user: User;
    };
}

export interface ServiceRequestStatus {
    status: 'pending' | 'assigned' | 'in_progress' | 'waiting_for_user' | 'completed' | 'cancelled';
    timestamp: string;
    updated_by?: string;
    notes?: string;
}

export interface ServiceRequest {
    id: string;
    user_id: number;
    assigned_to?: number;
    title: string;
    description: string;
    priority: 'low' | 'medium' | 'high' | 'critical';
    status: 'pending' | 'assigned' | 'in_progress' | 'waiting_for_user' | 'completed' | 'cancelled';
    category?: string;
    attachments?: string[];
    sla_target_date?: string;
    sla_breached: boolean;
    sla_response_minutes: number;
    sla_resolution_minutes: number;
    created_at: string;
    updated_at: string;
    created_by?: User;
    assigned_to_user?: User;
    history?: ServiceRequestHistory[];
}

export interface ServiceRequestHistory {
    id: number;
    service_request_id: string;
    old_status?: string;
    new_status?: string;
    action: string;
    notes?: string;
    changed_by_user?: User;
    changed_at: string;
}

export interface Notification {
    id: number;
    user_id: number;
    title: string;
    message: string;
    type: 'request_assigned' | 'status_updated' | 'sla_warning' | 'system';
    related_request_id?: string;
    is_read: boolean;
    created_at: string;
    read_at?: string;
}

export interface PaginatedResponse<T> {
    data: T[];
    pagination: {
        page: number;
        per_page: number;
        total: number;
        pages: number;
    };
}

export interface ApiErrorResponse {
    success: false;
    error: {
        code: string;
        message: string;
        details?: Record<string, unknown>;
    };
}

export interface ApiSuccessResponse<T> {
    success: true;
    data: T;
    message?: string;
}

export interface AuthContextType {
    user: User | null;
    token: string | null;
    isAuthenticated: boolean;
    isLoading: boolean;
    login: (email: string, password: string, deviceId?: string) => Promise<void>;
    logout: () => Promise<void>;
    logoutEverywhere: () => Promise<void>;
    register: (data: RegisterFormData) => Promise<void>;
    refreshToken: () => Promise<boolean>;
    setUser: (user: User | null) => void;
}

export interface RegisterFormData {
    full_name: string;
    username: string;
    email: string;
    phone: string;
    password: string;
    confirm_password: string;
    organization?: string;
    agree_terms: boolean;
}

export interface LoginFormData {
    email: string;
    password: string;
    rememberMe?: boolean;
}

export interface PasswordChangeData {
    current_password: string;
    new_password: string;
    confirm_password: string;
}

export interface PerformanceMetrics {
    requests_handled: number;
    average_resolution_time: number;
    sla_compliance_rate: number;
    pending_count: number;
}

export interface DashboardStats {
    total_requests: number;
    pending_count: number;
    in_progress_count: number;
    sla_breached_count: number;
    assigned_to_staff: number;
}
