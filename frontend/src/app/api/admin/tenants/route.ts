/**
 * Eye of God - Admin Tenants API Route (Mock)
 * 
 * TODO: Replace with real Django Ninja backend integration
 */
import { NextResponse } from 'next/server';

// Mock tenants data
const mockTenants = [
    { id: '1', name: 'Acme Corp', subdomain: 'acme', plan: 'pro', usersCount: 15, podsCount: 8, status: 'active', createdAt: 'Jan 15, 2026' },
    { id: '2', name: 'TechStart Inc', subdomain: 'techstart', plan: 'enterprise', usersCount: 50, podsCount: 25, status: 'active', createdAt: 'Jan 10, 2026' },
    { id: '3', name: 'AI Research Lab', subdomain: 'ailab', plan: 'free', usersCount: 3, podsCount: 1, status: 'trial', createdAt: 'Jan 20, 2026' },
    { id: '4', name: 'DataCorp Solutions', subdomain: 'datacorp', plan: 'pro', usersCount: 20, podsCount: 12, status: 'active', createdAt: 'Dec 28, 2025' },
    { id: '5', name: 'CloudNine Systems', subdomain: 'cloudnine', plan: 'pro', usersCount: 8, podsCount: 4, status: 'active', createdAt: 'Dec 15, 2025' },
];

export async function GET() {
    // TODO: Replace with real Django Ninja backend call to /api/v2/admin/tenants
    return NextResponse.json({ tenants: mockTenants });
}

export async function POST(request: Request) {
    try {
        const body = await request.json();

        // Validate required fields
        if (!body.name || !body.subdomain || !body.adminEmail) {
            return NextResponse.json(
                { message: 'Name, subdomain, and admin email are required' },
                { status: 400 }
            );
        }

        // Mock tenant creation
        // TODO: Replace with real Django Ninja backend call to POST /api/v2/admin/tenants
        const newTenant = {
            id: String(mockTenants.length + 1),
            name: body.name,
            subdomain: body.subdomain,
            plan: body.plan || 'free',
            usersCount: 1,
            podsCount: 0,
            status: 'active',
            createdAt: new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }),
        };

        return NextResponse.json({
            success: true,
            tenant: newTenant,
            message: 'Tenant created successfully'
        });
    } catch {
        return NextResponse.json(
            { message: 'Internal server error' },
            { status: 500 }
        );
    }
}
