import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Container, Form, Button, Card, Col, Row, Alert } from 'react-bootstrap';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useAuth } from '../../../shared/contexts/AuthContext';
import { showToast } from '../../../shared/components/Toast';

const loginSchema = z.object({
    email: z.string().email('Invalid email address'),
    password: z.string().min(6, 'Password must be at least 6 characters'),
});

type LoginFormData = z.infer<typeof loginSchema>;

const LoginPage: React.FC = () => {
    const navigate = useNavigate();
    const location = useLocation();
    const { login, isLoading } = useAuth();
    const [error, setError] = useState<string | null>(null);
    const {
        register,
        handleSubmit,
        formState: { errors },
    } = useForm<LoginFormData>({
        resolver: zodResolver(loginSchema),
    });

    const onSubmit = async (data: LoginFormData) => {
        setError(null);
        try {
            await login(data.email, data.password);
            const from = (location.state?.from?.pathname as string) || '/user/dashboard';
            navigate(from, { replace: true });
            showToast({ message: 'Logged in successfully', type: 'success' });
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Login failed';
            setError(message);
            showToast({ message, type: 'error' });
        }
    };

    return (
        <div className="min-vh-100 d-flex align-items-center justify-content-center bg-light">
            <Container maxWidth="sm" className="py-4">
                <Row className="justify-content-center">
                    <Col xs={12} sm={10} md={8}>
                        <Card className="shadow-lg border-0">
                            <Card.Body className="p-5">
                                <h1 className="h3 mb-4 text-center">Elcorp Namibia</h1>
                                <p className="text-center text-muted mb-4">User Portal Login</p>

                                {error && (
                                    <Alert variant="danger" onDismiss={() => setError(null)}>
                                        {error}
                                    </Alert>
                                )}

                                <Form onSubmit={handleSubmit(onSubmit)} noValidate>
                                    <Form.Group className="mb-3">
                                        <Form.Label htmlFor="email">Email Address</Form.Label>
                                        <Form.Control
                                            id="email"
                                            type="email"
                                            placeholder="Enter your email"
                                            {...register('email')}
                                            isInvalid={!!errors.email}
                                            disabled={isLoading}
                                            aria-describedby="email-error"
                                        />
                                        {errors.email && (
                                            <Form.Control.Feedback type="invalid" id="email-error">
                                                {errors.email.message}
                                            </Form.Control.Feedback>
                                        )}
                                    </Form.Group>

                                    <Form.Group className="mb-4">
                                        <Form.Label htmlFor="password">Password</Form.Label>
                                        <Form.Control
                                            id="password"
                                            type="password"
                                            placeholder="Enter your password"
                                            {...register('password')}
                                            isInvalid={!!errors.password}
                                            disabled={isLoading}
                                            aria-describedby="password-error"
                                        />
                                        {errors.password && (
                                            <Form.Control.Feedback type="invalid" id="password-error">
                                                {errors.password.message}
                                            </Form.Control.Feedback>
                                        )}
                                    </Form.Group>

                                    <Button
                                        variant="primary"
                                        type="submit"
                                        className="w-100 mb-3"
                                        disabled={isLoading}
                                    >
                                        {isLoading ? 'Logging in...' : 'Login'}
                                    </Button>
                                </Form>

                                <div className="text-center">
                                    <p className="text-muted small">
                                        Don't have an account?{' '}
                                        <a href="/user/register" className="text-decoration-none">
                                            Register here
                                        </a>
                                    </p>
                                    <a href="#forgot" className="text-decoration-none small">
                                        Forgot password?
                                    </a>
                                </div>
                            </Card.Body>
                        </Card>
                    </Col>
                </Row>
            </Container>
        </div>
    );
};

export default LoginPage;
