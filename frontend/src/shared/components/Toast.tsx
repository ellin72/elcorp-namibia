import React from 'react';
import Toast from 'react-bootstrap/Toast';
import ToastContainer from 'react-bootstrap/ToastContainer';
import toast, { Toaster } from 'react-hot-toast';

export const ToastNotifications: React.FC = () => {
    return <Toaster position="top-right" reverseOrder={false} />;
};

interface ToastProps {
    message: string;
    type?: 'success' | 'error' | 'info' | 'warning';
    duration?: number;
}

export const showToast = ({ message, type = 'info', duration = 3000 }: ToastProps) => {
    switch (type) {
        case 'success':
            toast.success(message, { duration });
            break;
        case 'error':
            toast.error(message, { duration });
            break;
        case 'warning':
            toast(message, { icon: '⚠️', duration });
            break;
        default:
            toast(message, { duration });
    }
};
