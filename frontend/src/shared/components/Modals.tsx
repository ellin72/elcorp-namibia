import React from 'react';
import { Modal, Button, Form } from 'react-bootstrap';

interface FormModalProps {
    show: boolean;
    title: string;
    onHide: () => void;
    onSubmit: (data: Record<string, unknown>) => void | Promise<void>;
    children: React.ReactNode;
    submitLabel?: string;
    isLoading?: boolean;
}

export const FormModal: React.FC<FormModalProps> = ({
    show,
    title,
    onHide,
    onSubmit,
    children,
    submitLabel = 'Save',
    isLoading = false,
}) => {
    const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
        e.preventDefault();
        const formData = new FormData(e.currentTarget);
        const data = Object.fromEntries(formData);
        await onSubmit(data);
    };

    return (
        <Modal show={show} onHide={onHide} centered>
            <Modal.Header closeButton>
                <Modal.Title>{title}</Modal.Title>
            </Modal.Header>
            <Form onSubmit={handleSubmit}>
                <Modal.Body>{children}</Modal.Body>
                <Modal.Footer>
                    <Button variant="secondary" onClick={onHide} disabled={isLoading}>
                        Cancel
                    </Button>
                    <Button variant="primary" type="submit" disabled={isLoading}>
                        {isLoading ? 'Saving...' : submitLabel}
                    </Button>
                </Modal.Footer>
            </Form>
        </Modal>
    );
};

interface ConfirmModalProps {
    show: boolean;
    title: string;
    message: string;
    onHide: () => void;
    onConfirm: () => void | Promise<void>;
    isLoading?: boolean;
    variant?: 'danger' | 'warning' | 'info';
}

export const ConfirmModal: React.FC<ConfirmModalProps> = ({
    show,
    title,
    message,
    onHide,
    onConfirm,
    isLoading = false,
    variant = 'warning',
}) => {
    return (
        <Modal show={show} onHide={onHide} centered>
            <Modal.Header closeButton>
                <Modal.Title>{title}</Modal.Title>
            </Modal.Header>
            <Modal.Body>{message}</Modal.Body>
            <Modal.Footer>
                <Button variant="secondary" onClick={onHide} disabled={isLoading}>
                    Cancel
                </Button>
                <Button variant={variant} onClick={onConfirm} disabled={isLoading}>
                    {isLoading ? 'Processing...' : 'Confirm'}
                </Button>
            </Modal.Footer>
        </Modal>
    );
};
