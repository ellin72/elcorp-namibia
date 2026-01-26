import React from 'react';
import Spinner from 'react-bootstrap/Spinner';

interface LoadingSpinnerProps {
    message?: string;
    fullScreen?: boolean;
}

export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
    message = 'Loading...',
    fullScreen = false,
}) => {
    const content = (
        <div className="d-flex flex-column align-items-center justify-content-center gap-3">
            <Spinner animation="border" role="status" variant="primary">
                <span className="visually-hidden">Loading...</span>
            </Spinner>
            {message && <p className="text-muted">{message}</p>}
        </div>
    );

    if (fullScreen) {
        return (
            <div style={{ minHeight: '100vh' }} className="d-flex align-items-center justify-content-center">
                {content}
            </div>
        );
    }

    return <div className="p-4">{content}</div>;
};
