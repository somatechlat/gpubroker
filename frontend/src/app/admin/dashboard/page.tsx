/**
 * Eye of God - System Dashboard
 * 
 * VIBE Rules Applied:
 * - Rule 10: Theme Integrity - Uses design tokens
 * - Rule 19: Single screen with all KPIs visible
 * - Rule 25: Pattern Mirroring from reference images
 */
'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import '@/styles/eog-style-guide.css';

interface DashboardData {
    totalTenants: number;
    activePods: number;
    monthlyRevenue: number;
    systemHealth: number;
    recentActivity: Activity[];
}

interface Activity {
    id: string;
    tenant: string;
    action: string;
    timestamp: string;
    status: 'success' | 'warning' | 'error';
}

export default function EyeOfGodDashboard() {
    const [data, setData] = useState<DashboardData | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        // TODO: Replace with real API call
        const fetchDashboardData = async () => {
            try {
                const response = await fetch('/api/admin/system/dashboard');
                if (response.ok) {
                    const dashboardData = await response.json();
                    setData(dashboardData);
                } else {
                    // Mock data for development
                    setData({
                        totalTenants: 12,
                        activePods: 47,
                        monthlyRevenue: 14290,
                        systemHealth: 99.9,
                        recentActivity: [
                            { id: '1', tenant: 'Acme Corp', action: 'Tenant created', timestamp: '5m ago', status: 'success' },
                            { id: '2', tenant: 'TechStart Inc', action: 'Plan upgraded to Pro', timestamp: '1h ago', status: 'success' },
                            { id: '3', tenant: 'AI Research Lab', action: 'POD deployed', timestamp: '2h ago', status: 'success' },
                            { id: '4', tenant: 'DataCorp', action: 'User added', timestamp: '3h ago', status: 'success' },
                            { id: '5', tenant: 'CloudNine', action: 'Payment received', timestamp: '4h ago', status: 'success' },
                        ]
                    });
                }
            } catch {
                // Mock data fallback
                setData({
                    totalTenants: 12,
                    activePods: 47,
                    monthlyRevenue: 14290,
                    systemHealth: 99.9,
                    recentActivity: []
                });
            } finally {
                setLoading(false);
            }
        };

        fetchDashboardData();
    }, []);

    if (loading) {
        return (
            <div className="flex items-center justify-center" style={{ minHeight: '100vh' }}>
                <p>Loading dashboard...</p>
            </div>
        );
    }

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
                    <Link href="/admin/dashboard" className="sidebar-link active" title="Dashboard">
                        <svg width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                            <rect x="3" y="3" width="7" height="7" rx="1" />
                            <rect x="14" y="3" width="7" height="7" rx="1" />
                            <rect x="3" y="14" width="7" height="7" rx="1" />
                            <rect x="14" y="14" width="7" height="7" rx="1" />
                        </svg>
                    </Link>
                    <Link href="/admin/tenants" className="sidebar-link" title="Tenants">
                        <svg width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                            <path d="M19 21V5a2 2 0 0 0-2-2H7a2 2 0 0 0-2 2v16" />
                            <path d="M1 21h22" />
                            <path d="M9 7h1M9 11h1M9 15h1M14 7h1M14 11h1M14 15h1" />
                        </svg>
                    </Link>
                    <Link href="/admin/config" className="sidebar-link" title="Configuration">
                        <svg width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                            <circle cx="12" cy="12" r="3" />
                            <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" />
                        </svg>
                    </Link>
                    <Link href="/admin/audit" className="sidebar-link" title="Audit Logs">
                        <svg width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                            <path d="M14 2v6h6" />
                            <path d="M16 13H8M16 17H8M10 9H8" />
                        </svg>
                    </Link>
                </nav>
            </aside>

            {/* Main Content */}
            <main className="main-content">
                {/* Header */}
                <div className="page-header">
                    <div>
                        <h1 className="page-title">Good Morning, Admin</h1>
                        <p className="text-sm text-muted">System Overview</p>
                    </div>
                    <div className="flex items-center gap-4">
                        <div style={{
                            width: '40px',
                            height: '40px',
                            borderRadius: '50%',
                            backgroundColor: 'var(--color-border)',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center'
                        }}>
                            <svg width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                                <circle cx="12" cy="7" r="4" />
                            </svg>
                        </div>
                    </div>
                </div>

                {/* KPI Cards */}
                <div className="grid grid-cols-4 mb-6">
                    <div className="kpi-card">
                        <div className="flex items-center justify-between mb-2">
                            <span className="kpi-label">Total Tenants</span>
                            <svg width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                                <path d="M19 21V5a2 2 0 0 0-2-2H7a2 2 0 0 0-2 2v16" />
                                <path d="M1 21h22" />
                            </svg>
                        </div>
                        <div className="kpi-value">{data?.totalTenants || 0}</div>
                    </div>

                    <div className="kpi-card">
                        <div className="flex items-center justify-between mb-2">
                            <span className="kpi-label">Active PODs</span>
                            <svg width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                                <rect x="4" y="4" width="16" height="16" rx="2" />
                                <path d="M9 9h6v6H9z" />
                            </svg>
                        </div>
                        <div className="kpi-value">{data?.activePods || 0}</div>
                    </div>

                    <div className="kpi-card">
                        <div className="flex items-center justify-between mb-2">
                            <span className="kpi-label">Revenue (MTD)</span>
                            <svg width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                                <circle cx="12" cy="12" r="10" />
                                <path d="M12 6v12M9 9h6M9 15h6" />
                            </svg>
                        </div>
                        <div className="kpi-value">${data?.monthlyRevenue.toLocaleString() || 0}</div>
                    </div>

                    <div className="kpi-card" style={{ backgroundColor: 'var(--color-success-light)' }}>
                        <div className="flex items-center justify-between mb-2">
                            <span className="kpi-label">System Health</span>
                            <svg width="20" height="20" fill="none" stroke="var(--color-success)" strokeWidth="2" viewBox="0 0 24 24">
                                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                                <path d="M22 4 12 14.01l-3-3" />
                            </svg>
                        </div>
                        <div className="kpi-value" style={{ color: 'var(--color-success)' }}>{data?.systemHealth}%</div>
                        <span className="text-sm" style={{ color: 'var(--color-success-text)' }}>Online</span>
                    </div>
                </div>

                {/* Recent Activity */}
                <div className="card">
                    <div className="card-header">
                        <div className="flex items-center justify-between">
                            <h2 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 600 }}>Recent Tenant Activity</h2>
                            <Link href="/admin/audit" className="btn btn-secondary" style={{ padding: '8px 16px', fontSize: '14px' }}>
                                View All
                            </Link>
                        </div>
                    </div>
                    <div className="card-body" style={{ padding: 0 }}>
                        <table className="table">
                            <thead>
                                <tr>
                                    <th>Tenant</th>
                                    <th>Action</th>
                                    <th>Time</th>
                                    <th>Status</th>
                                </tr>
                            </thead>
                            <tbody>
                                {data?.recentActivity.map((activity) => (
                                    <tr key={activity.id}>
                                        <td style={{ fontWeight: 500 }}>{activity.tenant}</td>
                                        <td>{activity.action}</td>
                                        <td className="text-muted">{activity.timestamp}</td>
                                        <td>
                                            <span className={`badge badge-${activity.status}`}>
                                                {activity.status === 'success' ? 'Success' : activity.status}
                                            </span>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            </main>
        </div>
    );
}
