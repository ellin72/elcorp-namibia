import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from '../../shared/contexts/AuthContext';

// Pages will be lazy-loaded
const LoginPage = React.lazy(() => import('./pages/LoginPage'));
const RegisterPage = React.lazy(() => import('./pages/RegisterPage'));
const DashboardPage = React.lazy(() => import('./pages/DashboardPage'));
const ProfilePage = React.lazy(() => import('./pages/ProfilePage'));
const ServiceRequestsPage = React.lazy(() => import('./pages/ServiceRequestsPage'));
const ServiceRequestDetailPage = React.lazy(() => import('./pages/ServiceRequestDetailPage'));
const NotificationsPage = React.lazy(() => import('./pages/NotificationsPage'));

const UserPortal: React.FC = () => {
    const { isAuthenticated } = useAuth();

    return (
        <React.Suspense fallback={<div>Loading...</div>}>
            <Routes>
                {/* Public routes */}
                <Route path="login" element={<LoginPage />} />
                <Route path="register" element={<RegisterPage />} />

                {/* Protected routes */}
                {isAuthenticated && (
                    <>
                        <Route path="dashboard" element={<DashboardPage />} />
                        <Route path="profile" element={<ProfilePage />} />
                        <Route path="service-requests" element={<ServiceRequestsPage />} />
                        <Route path="service-requests/:id" element={<ServiceRequestDetailPage />} />
                        <Route path="notifications" element={<NotificationsPage />} />
                    </>
                )}

                {/* Default redirect */}
                <Route path="/" element={<Navigate to="dashboard" replace />} />
            </Routes>
        </React.Suspense>
    );
};

export default UserPortal;
