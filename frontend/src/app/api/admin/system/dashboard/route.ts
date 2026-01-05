/**
 * Eye of God - Admin Dashboard API Route (Mock)
 * 
 * TODO: Replace with real Django Ninja backend integration
 */
import { NextResponse } from 'next/server';

export async function GET() {
    // TODO: Replace with real Django Ninja backend call to /api/v2/admin/system/dashboard
    return NextResponse.json({
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
