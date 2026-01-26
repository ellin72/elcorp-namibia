import React from 'react';
import { Alert } from 'react-bootstrap';

interface ErrorAlertProps {
    title?: string;
    message: string;
    onDismiss?: () => void;
    variant?: 'danger' | 'warning';
}

export const ErrorAlert: React.FC<ErrorAlertProps> = ({
    title = 'Error',
    message,
    onDismiss,
    variant = 'danger',
}) => {
    return (
        <Alert variant={variant} dismissible={!!onDismiss} onClose={onDismiss} role="alert">
            <Alert.Heading>{title}</Alert.Heading>
            <p>{message}</p>
        </Alert>
    );
};

interface SuccessAlertProps {
    title?: string;
    message: string;
    onDismiss?: () => void;
}

export const SuccessAlert: React.FC<SuccessAlertProps> = ({
    title = 'Success',
    message,
    onDismiss,
}) => {
    return (
        <Alert variant="success" dismissible={!!onDismiss} onClose={onDismiss} role="alert">
            <Alert.Heading>{title}</Alert.Heading>
            <p>{message}</p>
        </Alert>
    );
};
