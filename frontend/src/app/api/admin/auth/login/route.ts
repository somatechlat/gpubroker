/**
 * Eye of God - Admin Auth API Route (Mock)
 * 
 * TODO: Replace with real Django Ninja backend integration
 */
import { NextResponse } from 'next/server';

export async function POST(request: Request) {
    try {
        const body = await request.json();
        const { email, password, mfa_code } = body;

        // Mock validation - Replace with real auth
        if (!email || !password) {
            return NextResponse.json(
                { message: 'Email and password are required' },
                { status: 400 }
            );
        }

        // Mock super admin credentials for development
        // TODO: Replace with real backend call to /api/v2/admin/auth/login
        if (email === 'admin@gpubroker.com' && password === 'superadmin123!') {
            if (!mfa_code) {
                return NextResponse.json({ requires_mfa: true });
            }

            if (mfa_code === '123456') {
                return NextResponse.json({
                    success: true,
                    token: 'mock_jwt_token_' + Date.now(),
                    user: {
                        id: '1',
                        email: 'admin@gpubroker.com',
                        name: 'System Administrator',
                        role: 'super_admin'
                    }
                });
            } else {
                return NextResponse.json(
                    { message: 'Invalid MFA code' },
                    { status: 401 }
                );
            }
        }

        return NextResponse.json(
            { message: 'Invalid credentials' },
            { status: 401 }
        );
    } catch {
        return NextResponse.json(
            { message: 'Internal server error' },
            { status: 500 }
        );
    }
}
