/**
 * Eye of God - Create Tenant Wizard
 * 
 * 4-Step wizard for creating new tenants:
 * 1. Organization Info
 * 2. Plan Selection
 * 3. Limits Configuration
 * 4. Admin User Creation
 */
'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import '@/styles/eog-style-guide.css';

type WizardStep = 1 | 2 | 3 | 4;

interface TenantForm {
    // Step 1: Organization
    name: string;
    subdomain: string;
    industry: string;
    description: string;
    // Step 2: Plan
    plan: 'free' | 'pro' | 'enterprise';
    // Step 3: Limits
    rateLimitRps: number;
    maxPods: number;
    maxUsers: number;
    storageGb: number;
    // Step 4: Admin
    adminEmail: string;
    adminName: string;
    adminPhone: string;
    sendWelcomeEmail: boolean;
}

interface ValidationState {
    name: 'idle' | 'valid' | 'invalid';
    subdomain: 'idle' | 'valid' | 'invalid' | 'checking';
    adminEmail: 'idle' | 'valid' | 'invalid';
    adminName: 'idle' | 'valid' | 'invalid';
}

const PLAN_DEFAULTS = {
    free: { rateLimitRps: 10, maxPods: 1, maxUsers: 3, storageGb: 5 },
    pro: { rateLimitRps: 100, maxPods: 10, maxUsers: 25, storageGb: 100 },
    enterprise: { rateLimitRps: 1000, maxPods: 50, maxUsers: 1000, storageGb: 1000 }
};

export default function CreateTenantWizard() {
    const router = useRouter();
    const [step, setStep] = useState<WizardStep>(1);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const [form, setForm] = useState<TenantForm>({
        name: '',
        subdomain: '',
        industry: '',
        description: '',
        plan: 'pro',
        rateLimitRps: 100,
        maxPods: 10,
        maxUsers: 25,
        storageGb: 100,
        adminEmail: '',
        adminName: '',
        adminPhone: '',
        sendWelcomeEmail: true,
    });

    const [validation, setValidation] = useState<ValidationState>({
        name: 'idle',
        subdomain: 'idle',
        adminEmail: 'idle',
        adminName: 'idle',
    });

    const validateName = (name: string) => {
        if (name.length >= 3) {
            setValidation(prev => ({ ...prev, name: 'valid' }));
        } else if (name.length > 0) {
            setValidation(prev => ({ ...prev, name: 'invalid' }));
        } else {
            setValidation(prev => ({ ...prev, name: 'idle' }));
        }
    };

    const validateSubdomain = async (subdomain: string) => {
        if (subdomain.length === 0) {
            setValidation(prev => ({ ...prev, subdomain: 'idle' }));
            return;
        }

        const subdomainRegex = /^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$/;
        if (!subdomainRegex.test(subdomain) && subdomain.length > 0) {
            setValidation(prev => ({ ...prev, subdomain: 'invalid' }));
            return;
        }

        // TODO: Replace with real API check
        setValidation(prev => ({ ...prev, subdomain: 'checking' }));
        setTimeout(() => {
            setValidation(prev => ({ ...prev, subdomain: 'valid' }));
        }, 500);
    };

    const validateEmail = (email: string) => {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (email.length === 0) {
            setValidation(prev => ({ ...prev, adminEmail: 'idle' }));
        } else if (emailRegex.test(email)) {
            setValidation(prev => ({ ...prev, adminEmail: 'valid' }));
        } else {
            setValidation(prev => ({ ...prev, adminEmail: 'invalid' }));
        }
    };

    const handlePlanChange = (plan: 'free' | 'pro' | 'enterprise') => {
        const defaults = PLAN_DEFAULTS[plan];
        setForm(prev => ({
            ...prev,
            plan,
            rateLimitRps: defaults.rateLimitRps,
            maxPods: defaults.maxPods,
            maxUsers: defaults.maxUsers,
            storageGb: defaults.storageGb,
        }));
    };

    const canProceed = (currentStep: WizardStep): boolean => {
        switch (currentStep) {
            case 1:
                return validation.name === 'valid' && validation.subdomain === 'valid';
            case 2:
                return !!form.plan;
            case 3:
                return form.rateLimitRps > 0 && form.maxPods > 0 && form.maxUsers > 0;
            case 4:
                return validation.adminEmail === 'valid' && form.adminName.length >= 2;
            default:
                return false;
        }
    };

    const handleSubmit = async () => {
        setLoading(true);
        setError(null);

        try {
            const response = await fetch('/api/admin/tenants', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(form),
            });

            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.message || 'Failed to create tenant');
            }

            router.push('/admin/tenants');
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to create tenant');
            setLoading(false);
        }
    };

    const getInputClassName = (field: keyof ValidationState): string => {
        const base = 'form-input';
        const state = validation[field];
        if (state === 'valid') return `${base} is-valid`;
        if (state === 'invalid') return `${base} is-invalid`;
        return base;
    };

    return (
        <div style={{ display: 'flex', minHeight: '100vh' }}>
            {/* Sidebar */}
            <aside className="sidebar">
                <div className="sidebar-logo">
                    <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
                        <circle cx="16" cy="16" r="14" stroke="currentColor" strokeWidth="2" />
                        <circle cx="16" cy="16" r="6" fill="currentColor" />
                    </svg>
                </div>
                <nav className="sidebar-nav">
                    <Link href="/admin/dashboard" className="sidebar-link" title="Dashboard">
                        <svg width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                            <rect x="3" y="3" width="7" height="7" rx="1" />
                            <rect x="14" y="3" width="7" height="7" rx="1" />
                            <rect x="3" y="14" width="7" height="7" rx="1" />
                            <rect x="14" y="14" width="7" height="7" rx="1" />
                        </svg>
                    </Link>
                    <Link href="/admin/tenants" className="sidebar-link active" title="Tenants">
                        <svg width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                            <path d="M19 21V5a2 2 0 0 0-2-2H7a2 2 0 0 0-2 2v16" />
                            <path d="M1 21h22" />
                        </svg>
                    </Link>
                </nav>
            </aside>

            {/* Main Content */}
            <main className="main-content">
                <div style={{ maxWidth: '600px', margin: '0 auto' }}>
                    {/* Header */}
                    <div className="mb-6">
                        <h1 className="page-title">Create New Tenant</h1>
                        <p className="text-sm text-muted">Step {step} of 4</p>
                    </div>

                    {/* Wizard Steps Indicator */}
                    <div className="wizard-steps">
                        <div className={`wizard-step ${step === 1 ? 'active' : step > 1 ? 'completed' : ''}`}>
                            <span className="wizard-step-number">{step > 1 ? '✓' : '1'}</span>
                            <span>Organization</span>
                        </div>
                        <div className="wizard-divider" />
                        <div className={`wizard-step ${step === 2 ? 'active' : step > 2 ? 'completed' : ''}`}>
                            <span className="wizard-step-number">{step > 2 ? '✓' : '2'}</span>
                            <span>Plan</span>
                        </div>
                        <div className="wizard-divider" />
                        <div className={`wizard-step ${step === 3 ? 'active' : step > 3 ? 'completed' : ''}`}>
                            <span className="wizard-step-number">{step > 3 ? '✓' : '3'}</span>
                            <span>Limits</span>
                        </div>
                        <div className="wizard-divider" />
                        <div className={`wizard-step ${step === 4 ? 'active' : ''}`}>
                            <span className="wizard-step-number">4</span>
                            <span>Admin</span>
                        </div>
                    </div>

                    {/* Form Card */}
                    <div className="card">
                        <div className="card-body">
                            {/* Step 1: Organization Info */}
                            {step === 1 && (
                                <div>
                                    <div className="form-group">
                                        <label className="form-label">
                                            Organization Name <span className="required">*</span>
                                        </label>
                                        <input
                                            type="text"
                                            className={getInputClassName('name')}
                                            placeholder="Enter organization name"
                                            value={form.name}
                                            onChange={(e) => {
                                                setForm(prev => ({ ...prev, name: e.target.value }));
                                                validateName(e.target.value);
                                            }}
                                        />
                                        {validation.name === 'valid' && (
                                            <div className="validation-message success">
                                                <svg className="validation-icon" fill="currentColor" viewBox="0 0 20 20">
                                                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                                                </svg>
                                                Valid name
                                            </div>
                                        )}
                                    </div>

                                    <div className="form-group">
                                        <label className="form-label">
                                            Subdomain <span className="required">*</span>
                                        </label>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                            <input
                                                type="text"
                                                className={getInputClassName('subdomain')}
                                                placeholder="yourcompany"
                                                value={form.subdomain}
                                                onChange={(e) => {
                                                    const value = e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, '');
                                                    setForm(prev => ({ ...prev, subdomain: value }));
                                                    validateSubdomain(value);
                                                }}
                                                style={{ flex: 1 }}
                                            />
                                            <span className="text-muted">.gpubroker.site</span>
                                        </div>
                                        {validation.subdomain === 'valid' && (
                                            <div className="validation-message success">
                                                <svg className="validation-icon" fill="currentColor" viewBox="0 0 20 20">
                                                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                                                </svg>
                                                Subdomain available
                                            </div>
                                        )}
                                        {validation.subdomain === 'checking' && (
                                            <div className="validation-message">Checking availability...</div>
                                        )}
                                    </div>

                                    <div className="form-group">
                                        <label className="form-label">Industry</label>
                                        <select
                                            className="form-input form-select"
                                            value={form.industry}
                                            onChange={(e) => setForm(prev => ({ ...prev, industry: e.target.value }))}
                                        >
                                            <option value="">Select industry</option>
                                            <option value="technology">Technology</option>
                                            <option value="finance">Finance</option>
                                            <option value="healthcare">Healthcare</option>
                                            <option value="education">Education</option>
                                            <option value="retail">Retail</option>
                                            <option value="other">Other</option>
                                        </select>
                                    </div>

                                    <div className="form-group">
                                        <label className="form-label">Description</label>
                                        <textarea
                                            className="form-input"
                                            rows={3}
                                            placeholder="Brief description of the organization"
                                            value={form.description}
                                            onChange={(e) => setForm(prev => ({ ...prev, description: e.target.value }))}
                                        />
                                    </div>
                                </div>
                            )}

                            {/* Step 2: Plan Selection */}
                            {step === 2 && (
                                <div className="grid grid-cols-3" style={{ gap: '16px' }}>
                                    {(['free', 'pro', 'enterprise'] as const).map((plan) => (
                                        <div
                                            key={plan}
                                            onClick={() => handlePlanChange(plan)}
                                            style={{
                                                padding: '24px 16px',
                                                borderRadius: 'var(--radius-lg)',
                                                border: form.plan === plan ? '2px solid var(--color-success)' : '2px solid var(--color-border)',
                                                cursor: 'pointer',
                                                textAlign: 'center',
                                                backgroundColor: form.plan === plan ? 'var(--color-success-light)' : 'var(--color-bg-card)',
                                            }}
                                        >
                                            <h3 style={{ marginBottom: '8px', textTransform: 'uppercase' }}>{plan}</h3>
                                            <div style={{ fontSize: '24px', fontWeight: 700, marginBottom: '16px' }}>
                                                ${plan === 'free' ? '0' : plan === 'pro' ? '40' : '99'}
                                                <span style={{ fontSize: '14px', fontWeight: 400 }}>/mo</span>
                                            </div>
                                            <ul style={{ textAlign: 'left', fontSize: '14px', listStyle: 'none' }}>
                                                <li>• {PLAN_DEFAULTS[plan].maxUsers} Users</li>
                                                <li>• {PLAN_DEFAULTS[plan].maxPods} PODs</li>
                                                <li>• {PLAN_DEFAULTS[plan].storageGb} GB Storage</li>
                                            </ul>
                                        </div>
                                    ))}
                                </div>
                            )}

                            {/* Step 3: Limits Configuration */}
                            {step === 3 && (
                                <div>
                                    <div className="form-group">
                                        <label className="form-label">Rate Limit (requests/second)</label>
                                        <input
                                            type="number"
                                            className="form-input"
                                            value={form.rateLimitRps}
                                            onChange={(e) => setForm(prev => ({ ...prev, rateLimitRps: parseInt(e.target.value) || 0 }))}
                                        />
                                    </div>
                                    <div className="form-group">
                                        <label className="form-label">Max PODs</label>
                                        <input
                                            type="number"
                                            className="form-input"
                                            value={form.maxPods}
                                            onChange={(e) => setForm(prev => ({ ...prev, maxPods: parseInt(e.target.value) || 0 }))}
                                        />
                                    </div>
                                    <div className="form-group">
                                        <label className="form-label">Max Users</label>
                                        <input
                                            type="number"
                                            className="form-input"
                                            value={form.maxUsers}
                                            onChange={(e) => setForm(prev => ({ ...prev, maxUsers: parseInt(e.target.value) || 0 }))}
                                        />
                                    </div>
                                    <div className="form-group">
                                        <label className="form-label">Storage (GB)</label>
                                        <input
                                            type="number"
                                            className="form-input"
                                            value={form.storageGb}
                                            onChange={(e) => setForm(prev => ({ ...prev, storageGb: parseInt(e.target.value) || 0 }))}
                                        />
                                    </div>
                                </div>
                            )}

                            {/* Step 4: Admin User */}
                            {step === 4 && (
                                <div>
                                    <div className="form-group">
                                        <label className="form-label">
                                            Admin Email <span className="required">*</span>
                                        </label>
                                        <input
                                            type="email"
                                            className={getInputClassName('adminEmail')}
                                            placeholder="admin@company.com"
                                            value={form.adminEmail}
                                            onChange={(e) => {
                                                setForm(prev => ({ ...prev, adminEmail: e.target.value }));
                                                validateEmail(e.target.value);
                                            }}
                                        />
                                        {validation.adminEmail === 'valid' && (
                                            <div className="validation-message success">
                                                <svg className="validation-icon" fill="currentColor" viewBox="0 0 20 20">
                                                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                                                </svg>
                                                Valid email
                                            </div>
                                        )}
                                    </div>

                                    <div className="form-group">
                                        <label className="form-label">
                                            Admin Name <span className="required">*</span>
                                        </label>
                                        <input
                                            type="text"
                                            className="form-input"
                                            placeholder="Full name"
                                            value={form.adminName}
                                            onChange={(e) => setForm(prev => ({ ...prev, adminName: e.target.value }))}
                                        />
                                    </div>

                                    <div className="form-group">
                                        <label className="form-label">Phone (optional)</label>
                                        <input
                                            type="tel"
                                            className="form-input"
                                            placeholder="+1 (555) 123-4567"
                                            value={form.adminPhone}
                                            onChange={(e) => setForm(prev => ({ ...prev, adminPhone: e.target.value }))}
                                        />
                                    </div>

                                    <div className="form-group">
                                        <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
                                            <input
                                                type="checkbox"
                                                checked={form.sendWelcomeEmail}
                                                onChange={(e) => setForm(prev => ({ ...prev, sendWelcomeEmail: e.target.checked }))}
                                            />
                                            Send welcome email with login credentials
                                        </label>
                                    </div>

                                    {error && (
                                        <div className="validation-message error" style={{ marginTop: '16px' }}>
                                            {error}
                                        </div>
                                    )}
                                </div>
                            )}

                            {/* Wizard Actions */}
                            <div className="wizard-actions">
                                <button
                                    type="button"
                                    className="btn btn-secondary"
                                    onClick={() => step === 1 ? router.push('/admin/tenants') : setStep((step - 1) as WizardStep)}
                                    disabled={loading}
                                >
                                    {step === 1 ? 'Cancel' : 'Back'}
                                </button>
                                <button
                                    type="button"
                                    className="btn btn-primary"
                                    onClick={() => step === 4 ? handleSubmit() : setStep((step + 1) as WizardStep)}
                                    disabled={!canProceed(step) || loading}
                                >
                                    {loading ? 'Creating...' : step === 4 ? 'Create Tenant' : 'Next'}
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </main>
        </div>
    );
}
