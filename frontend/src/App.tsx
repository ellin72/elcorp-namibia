import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './shared/contexts/AuthContext';
import { ToastNotifications } from './shared/components/Toast';
import { ProtectedRoute } from './shared/components/ProtectedRoute';

// Lazy load portals for code splitting
const UserPortal = React.lazy(() => import('./apps/user-portal'));
const StaffPortal = React.lazy(() => import('./apps/staff-portal'));
const AdminPortal = React.lazy(() => import('./apps/admin-portal'));

const UnauthorizedPage = () => (
    <div className="d-flex align-items-center justify-content-center" style={{ minHeight: '100vh' }}>
        <div className="text-center">
            <h1 className="display-1">403</h1>
            <p className="lead">Unauthorized Access</p>
            <p className="text-muted">You don't have permission to access this page.</p>
            <a href="/user/login" className="btn btn-primary">
                Back to Login
            </a>
        </div>
    </div>
);

const NotFoundPage = () => (
    <div className="d-flex align-items-center justify-content-center" style={{ minHeight: '100vh' }}>
        <div className="text-center">
            <h1 className="display-1">404</h1>
            <p className="lead">Page Not Found</p>
            <p className="text-muted">The page you're looking for doesn't exist.</p>
            <a href="/user" className="btn btn-primary">
                Go Home
            </a>
        </div>
    </div>
);

export const App: React.FC = () => {
    return (
        <AuthProvider>
            <ToastNotifications />
            <Router>
                <Routes>
                    {/* User Portal */}
                    <Route
                        path="/user/*"
                        element={
                            <React.Suspense fallback={<div>Loading...</div>}>
                                <ProtectedRoute requiredRole="user">
                                    <UserPortal />
                                </ProtectedRoute>
                            </React.Suspense>
                        }
                    />

                    {/* Staff Portal */}
                    <Route
                        path="/staff/*"
                        element={
                            <React.Suspense fallback={<div>Loading...</div>}>
                                <ProtectedRoute requiredRole="staff">
                                    <StaffPortal />
                                </ProtectedRoute>
                            </React.Suspense>
                        }
                    />

                    {/* Admin Portal */}
                    <Route
                        path="/admin/*"
                        element={
                            <React.Suspense fallback={<div>Loading...</div>}>
                                <ProtectedRoute requiredRole="admin">
                                    <AdminPortal />
                                </ProtectedRoute>
                            </React.Suspense>
                        }
                    />

                    {/* Error Pages */}
                    <Route path="/unauthorized" element={<UnauthorizedPage />} />
                    <Route path="/404" element={<NotFoundPage />} />

                    {/* Default Redirect */}
                    <Route path="/" element={<Navigate to="/user/dashboard" replace />} />
                    <Route path="*" element={<Navigate to="/404" replace />} />
                </Routes>
            </Router>
        </AuthProvider>
    );
};

export default App;
