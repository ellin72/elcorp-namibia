import React, { createContext, useReducer, useCallback, useEffect } from 'react';
import { User, AuthContextType, RegisterFormData } from '../types';
import { api, tokenStorage, deviceStorage } from '../api/client';
import axios from 'axios';

interface AuthState {
    user: User | null;
    token: string | null;
    isLoading: boolean;
    error: string | null;
}

type AuthAction =
    | { type: 'LOGIN_START' }
    | { type: 'LOGIN_SUCCESS'; payload: { user: User; token: string } }
    | { type: 'LOGIN_FAILURE'; payload: string }
    | { type: 'LOGOUT' }
    | { type: 'REGISTER_START' }
    | { type: 'REGISTER_SUCCESS' }
    | { type: 'REGISTER_FAILURE'; payload: string }
    | { type: 'TOKEN_REFRESH_SUCCESS'; payload: string }
    | { type: 'SET_USER'; payload: User }
    | { type: 'CLEAR_ERROR' };

const initialState: AuthState = {
    user: null,
    token: tokenStorage.getAccessToken(),
    isLoading: false,
    error: null,
};

const authReducer = (state: AuthState, action: AuthAction): AuthState => {
    switch (action.type) {
        case 'LOGIN_START':
        case 'REGISTER_START':
            return { ...state, isLoading: true, error: null };

        case 'LOGIN_SUCCESS':
            return {
                ...state,
                user: action.payload.user,
                token: action.payload.token,
                isLoading: false,
                error: null,
            };

        case 'LOGIN_FAILURE':
        case 'REGISTER_FAILURE':
            return { ...state, isLoading: false, error: action.payload };

        case 'REGISTER_SUCCESS':
            return { ...state, isLoading: false, error: null };

        case 'LOGOUT':
            return { user: null, token: null, isLoading: false, error: null };

        case 'TOKEN_REFRESH_SUCCESS':
            return { ...state, token: action.payload };

        case 'SET_USER':
            return { ...state, user: action.payload };

        case 'CLEAR_ERROR':
            return { ...state, error: null };

        default:
            return state;
    }
};

export const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
    children: React.ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
    const [state, dispatch] = useReducer(authReducer, initialState);

    // Handle token expiry event
    useEffect(() => {
        const handleTokenExpiry = () => {
            dispatch({ type: 'LOGOUT' });
            tokenStorage.clearTokens();
            window.location.href = '/user/login';
        };

        window.addEventListener('auth:expired', handleTokenExpiry);
        return () => window.removeEventListener('auth:expired', handleTokenExpiry);
    }, []);

    const login = useCallback(
        async (email: string, password: string, deviceId?: string) => {
            dispatch({ type: 'LOGIN_START' });
            try {
                const response = await api.auth.login(email, password, deviceId || deviceStorage.getDeviceId());
                const { access_token, refresh_token, user } = response.data.data;

                tokenStorage.setAccessToken(access_token);
                if (refresh_token) {
                    tokenStorage.setRefreshToken(refresh_token);
                }

                dispatch({
                    type: 'LOGIN_SUCCESS',
                    payload: { user, token: access_token },
                });
            } catch (error) {
                const message = axios.isAxiosError(error)
                    ? error.response?.data?.error?.message || 'Login failed'
                    : 'Login failed';
                dispatch({ type: 'LOGIN_FAILURE', payload: message });
                throw error;
            }
        },
        []
    );

    const logout = useCallback(async () => {
        try {
            await api.auth.logout();
        } catch (error) {
            console.error('Logout error:', error);
        } finally {
            tokenStorage.clearTokens();
            dispatch({ type: 'LOGOUT' });
        }
    }, []);

    const logoutEverywhere = useCallback(async () => {
        try {
            await api.auth.logoutEverywhere();
        } catch (error) {
            console.error('Logout everywhere error:', error);
            throw error;
        } finally {
            tokenStorage.clearTokens();
            dispatch({ type: 'LOGOUT' });
        }
    }, []);

    const register = useCallback(async (data: RegisterFormData) => {
        dispatch({ type: 'REGISTER_START' });
        try {
            await api.auth.register(data);
            dispatch({ type: 'REGISTER_SUCCESS' });
        } catch (error) {
            const message = axios.isAxiosError(error)
                ? error.response?.data?.error?.message || 'Registration failed'
                : 'Registration failed';
            dispatch({ type: 'REGISTER_FAILURE', payload: message });
            throw error;
        }
    }, []);

    const refreshToken = useCallback(async (): Promise<boolean> => {
        const refreshToken = tokenStorage.getRefreshToken();
        if (!refreshToken) {
            dispatch({ type: 'LOGOUT' });
            return false;
        }

        try {
            const response = await api.auth.refresh(refreshToken);
            const { access_token } = response.data.data;
            tokenStorage.setAccessToken(access_token);
            dispatch({ type: 'TOKEN_REFRESH_SUCCESS', payload: access_token });
            return true;
        } catch (error) {
            console.error('Token refresh failed:', error);
            tokenStorage.clearTokens();
            dispatch({ type: 'LOGOUT' });
            return false;
        }
    }, []);

    const setUser = useCallback((user: User | null) => {
        if (user) {
            dispatch({ type: 'SET_USER', payload: user });
        }
    }, []);

    const value: AuthContextType = {
        user: state.user,
        token: state.token,
        isAuthenticated: !!state.token && !!state.user,
        isLoading: state.isLoading,
        login,
        logout,
        logoutEverywhere,
        register,
        refreshToken,
        setUser,
    };

    return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = (): AuthContextType => {
    const context = React.useContext(AuthContext);
    if (!context) {
        throw new Error('useAuth must be used within AuthProvider');
    }
    return context;
};
