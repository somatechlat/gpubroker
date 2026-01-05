/**
 * Eye of God - Tenant List Page
 * 
 * VIBE Rules Applied:
 * - Rule 10: Theme Integrity
 * - Rule 19: Single screen with all data visible
 */
'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import '@/styles/eog-style-guide.css';

interface Tenant {
    id: string;
    name: string;
    subdomain: string;
    plan: 'free' | 'pro' | 'enterprise';
    usersCount: number;
    podsCount: number;
    status: 'active' | 'suspended' | 'trial';
    createdAt: string;
}

export default function TenantsPage() {
    const [tenants, setTenants] = useState<Tenant[]>([]);
    const [loading, setLoading] = useState(true);
    const [searchQuery, setSearchQuery] = useState('');
    const [filterPlan, setFilterPlan] = useState<string>('all');
    const [filterStatus, setFilterStatus] = useState<string>('all');

    useEffect(() => {
        const fetchTenants = async () => {
            try {
                const response = await fetch('/api/admin/tenants');
                if (response.ok) {
                    const data = await response.json();
                    setTenants(data.tenants || []);
                } else {
                    // Mock data for development
                    setTenants([
                        { id: '1', name: 'Acme Corp', subdomain: 'acme', plan: 'pro', usersCount: 15, podsCount: 8, status: 'active', createdAt: 'Jan 15, 2026' },
                        { id: '2', name: 'TechStart Inc', subdomain: 'techstart', plan: 'enterprise', usersCount: 50, podsCount: 25, status: 'active', createdAt: 'Jan 10, 2026' },
                        { id: '3', name: 'AI Research Lab', subdomain: 'ailab', plan: 'free', usersCount: 3, podsCount: 1, status: 'trial', createdAt: 'Jan 20, 2026' },
                        { id: '4', name: 'DataCorp Solutions', subdomain: 'datacorp', plan: 'pro', usersCount: 20, podsCount: 12, status: 'active', createdAt: 'Dec 28, 2025' },
                        { id: '5', name: 'CloudNine Systems', subdomain: 'cloudnine', plan: 'pro', usersCount: 8, podsCount: 4, status: 'active', createdAt: 'Dec 15, 2025' },
                    ]);
                }
            } catch {
                setTenants([]);
            } finally {
                setLoading(false);
            }
        };

        fetchTenants();
    }, []);

    const filteredTenants = tenants.filter(tenant => {
        const matchesSearch = tenant.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
            tenant.subdomain.toLowerCase().includes(searchQuery.toLowerCase());
        const matchesPlan = filterPlan === 'all' || tenant.plan === filterPlan;
        const matchesStatus = filterStatus === 'all' || tenant.status === filterStatus;
        return matchesSearch && matchesPlan && matchesStatus;
    });

    const getPlanBadgeClass = (plan: string) => {
        switch (plan) {
            case 'enterprise': return 'badge-info';
            case 'pro': return 'badge-success';
            default: return 'badge-warning';
        }
    };

    const getStatusBadgeClass = (status: string) => {
        switch (status) {
            case 'active': return 'badge-success';
            case 'trial': return 'badge-warning';
            case 'suspended': return 'badge-error';
            default: return '';
        }
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
                    <Link href="/admin/config" className="sidebar-link" title="Configuration">
                        <svg width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                            <circle cx="12" cy="12" r="3" />
                            <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42" />
                        </svg>
                    </Link>
                    <Link href="/admin/audit" className="sidebar-link" title="Audit Logs">
                        <svg width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                            <path d="M14 2v6h6" />
                        </svg>
                    </Link>
                </nav>
            </aside>

            {/* Main Content */}
            <main className="main-content">
                {/* Header */}
                <div className="page-header">
                    <div>
                        <h1 className="page-title">Tenant Management</h1>
                        <p className="text-sm text-muted">{tenants.length} tenants registered</p>
                    </div>
                    <Link href="/admin/tenants/new" className="btn btn-success">
                        + Create Tenant
                    </Link>
                </div>

                {/* Filters */}
                <div className="card mb-6">
                    <div className="card-body">
                        <div className="flex gap-4">
                            <div style={{ flex: 1 }}>
                                <input
                                    type="text"
                                    className="form-input"
                                    placeholder="Search tenants..."
                                    value={searchQuery}
                                    onChange={(e) => setSearchQuery(e.target.value)}
                                />
                            </div>
                            <select
                                className="form-input form-select"
                                style={{ width: '150px' }}
                                value={filterPlan}
                                onChange={(e) => setFilterPlan(e.target.value)}
                            >
                                <option value="all">All Plans</option>
                                <option value="free">Free</option>
                                <option value="pro">Pro</option>
                                <option value="enterprise">Enterprise</option>
                            </select>
                            <select
                                className="form-input form-select"
                                style={{ width: '150px' }}
                                value={filterStatus}
                                onChange={(e) => setFilterStatus(e.target.value)}
                            >
                                <option value="all">All Status</option>
                                <option value="active">Active</option>
                                <option value="trial">Trial</option>
                                <option value="suspended">Suspended</option>
                            </select>
                        </div>
                    </div>
                </div>

                {/* Tenant Table */}
                <div className="card">
                    <div className="card-body" style={{ padding: 0 }}>
                        {loading ? (
                            <div style={{ padding: '40px', textAlign: 'center' }}>Loading...</div>
                        ) : (
                            <table className="table">
                                <thead>
                                    <tr>
                                        <th>Tenant Name</th>
                                        <th>Plan</th>
                                        <th>Users</th>
                                        <th>PODs</th>
                                        <th>Status</th>
                                        <th>Created</th>
                                        <th>Actions</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {filteredTenants.map((tenant) => (
                                        <tr key={tenant.id}>
                                            <td>
                                                <div style={{ fontWeight: 500 }}>{tenant.name}</div>
                                                <div className="text-sm text-muted">{tenant.subdomain}.gpubroker.site</div>
                                            </td>
                                            <td>
                                                <span className={`badge ${getPlanBadgeClass(tenant.plan)}`}>
                                                    {tenant.plan.charAt(0).toUpperCase() + tenant.plan.slice(1)}
                                                </span>
                                            </td>
                                            <td>{tenant.usersCount}</td>
                                            <td>{tenant.podsCount}</td>
                                            <td>
                                                <span className={`badge ${getStatusBadgeClass(tenant.status)}`}>
                                                    {tenant.status.charAt(0).toUpperCase() + tenant.status.slice(1)}
                                                </span>
                                            </td>
                                            <td className="text-muted">{tenant.createdAt}</td>
                                            <td>
                                                <div className="flex gap-2">
                                                    <Link href={`/admin/tenants/${tenant.id}`} className="btn btn-secondary" style={{ padding: '4px 12px', fontSize: '12px' }}>
                                                        Edit
                                                    </Link>
                                                </div>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        )}
                    </div>
                </div>
            </main>
        </div>
    );
}
