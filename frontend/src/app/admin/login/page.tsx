/**
 * Eye of God - Super Admin Login Page
 * 
 * VIBE Rules Applied:
 * - Rule 3: Django Ninja for API, Lit for components (using React for Next.js compatibility)
 * - Rule 10: Theme Integrity - Uses design tokens from eog-style-guide.css
 * - Rule 18: Mocked API calls for now, will connect to real backend
 * - Rule 19: Radical UX Simplification - Single screen, minimal friction
 */
'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import '@/styles/eog-style-guide.css';

interface FormState {
    email: string;
    password: string;
    mfaCode: string;
}

interface ValidationState {
    email: 'idle' | 'valid' | 'invalid';
    password: 'idle' | 'valid' | 'invalid';
    mfaCode: 'idle' | 'valid' | 'invalid';
}

export default function EyeOfGodLoginPage() {
    const router = useRouter();
    const [form, setForm] = useState<FormState>({
        email: '',
        password: '',
        mfaCode: ''
    });
    const [validation, setValidation] = useState<ValidationState>({
        email: 'idle',
        password: 'idle',
        mfaCode: 'idle'
    });
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [showMfa, setShowMfa] = useState(false);

    const validateEmail = (email: string): boolean => {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    };

    const handleEmailChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const value = e.target.value;
        setForm(prev => ({ ...prev, email: value }));
        if (value.length > 0) {
            setValidation(prev => ({
                ...prev,
                email: validateEmail(value) ? 'valid' : 'invalid'
            }));
        } else {
            setValidation(prev => ({ ...prev, email: 'idle' }));
        }
    };

    const handlePasswordChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const value = e.target.value;
        setForm(prev => ({ ...prev, password: value }));
        if (value.length > 0) {
            setValidation(prev => ({
                ...prev,
                password: value.length >= 12 ? 'valid' : 'invalid'
            }));
        } else {
            setValidation(prev => ({ ...prev, password: 'idle' }));
        }
    };

    const handleMfaChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const value = e.target.value.replace(/\D/g, '').slice(0, 6);
        setForm(prev => ({ ...prev, mfaCode: value }));
        if (value.length > 0) {
            setValidation(prev => ({
                ...prev,
                mfaCode: value.length === 6 ? 'valid' : 'invalid'
            }));
        } else {
            setValidation(prev => ({ ...prev, mfaCode: 'idle' }));
        }
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);
        setLoading(true);

        try {
            // TODO: Replace with real API call to /api/v2/admin/auth/login
            // For now, mocking the authentication flow
            const response = await fetch('/api/admin/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    email: form.email,
                    password: form.password,
                    mfa_code: showMfa ? form.mfaCode : undefined
                })
            });

            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.message || 'Authentication failed');
            }

            const data = await response.json();

            if (data.requires_mfa && !showMfa) {
                setShowMfa(true);
                setLoading(false);
                return;
            }

            // Redirect to dashboard on success
            router.push('/admin/dashboard');
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Authentication failed');
            setLoading(false);
        }
    };

    const getInputClassName = (field: keyof ValidationState): string => {
        const base = 'form-input';
        if (validation[field] === 'valid') return `${base} is-valid`;
        if (validation[field] === 'invalid') return `${base} is-invalid`;
        return base;
    };

    return (
        <div className="auth-page">
            <div className="auth-card">
                <div className="auth-logo">
                    <h1>GPUBROKER</h1>
                    <p className="subtitle">Eye of God - System Administration</p>
                </div>

                <form className="auth-form" onSubmit={handleSubmit}>
                    {/* Email Field */}
                    <div className="form-group">
                        <label className="form-label">
                            Email <span className="required">*</span>
                        </label>
                        <input
                            type="email"
                            className={getInputClassName('email')}
                            placeholder="admin@gpubroker.com"
                            value={form.email}
                            onChange={handleEmailChange}
                            required
                            disabled={loading}
                        />
                        {validation.email === 'valid' && (
                            <div className="validation-message success">
                                <svg className="validation-icon" fill="currentColor" viewBox="0 0 20 20">
                                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                                </svg>
                                Valid email
                            </div>
                        )}
                    </div>

                    {/* Password Field */}
                    <div className="form-group">
                        <label className="form-label">
                            Password <span className="required">*</span>
                        </label>
                        <input
                            type="password"
                            className={getInputClassName('password')}
                            placeholder="Minimum 12 characters"
                            value={form.password}
                            onChange={handlePasswordChange}
                            required
                            disabled={loading}
                        />
                        {validation.password === 'valid' && (
                            <div className="validation-message success">
                                <svg className="validation-icon" fill="currentColor" viewBox="0 0 20 20">
                                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                                </svg>
                                Valid password
                            </div>
                        )}
                        {validation.password === 'invalid' && (
                            <div className="validation-message error">
                                <svg className="validation-icon" fill="currentColor" viewBox="0 0 20 20">
                                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                                </svg>
                                Password must be at least 12 characters
                            </div>
                        )}
                    </div>

                    {/* MFA Field - Shown after initial auth */}
                    {showMfa && (
                        <div className="form-group">
                            <label className="form-label">
                                MFA Code <span className="required">*</span>
                            </label>
                            <input
                                type="text"
                                className={getInputClassName('mfaCode')}
                                placeholder="6-digit code"
                                value={form.mfaCode}
                                onChange={handleMfaChange}
                                required
                                disabled={loading}
                                maxLength={6}
                            />
                            {validation.mfaCode === 'valid' && (
                                <div className="validation-message success">
                                    <svg className="validation-icon" fill="currentColor" viewBox="0 0 20 20">
                                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                                    </svg>
                                    Valid MFA code
                                </div>
                            )}
                        </div>
                    )}

                    {/* Error Message */}
                    {error && (
                        <div className="validation-message error">
                            <svg className="validation-icon" fill="currentColor" viewBox="0 0 20 20">
                                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                            </svg>
                            {error}
                        </div>
                    )}

                    {/* Submit Button */}
                    <button
                        type="submit"
                        className="btn btn-primary w-full"
                        disabled={loading || validation.email !== 'valid' || validation.password !== 'valid'}
                    >
                        {loading ? 'Authenticating...' : 'Authenticate'}
                    </button>
                </form>

                <div className="auth-footer">
                    Authorized administrators only
                </div>
            </div>
        </div>
    );
}
