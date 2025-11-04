import { NextResponse } from 'next/server'

const AUTH_API_URL = process.env.AUTH_API_URL || process.env.NEXT_PUBLIC_AUTH_API_URL || ''

export async function POST(req: Request) {
  if (!AUTH_API_URL) {
    return NextResponse.json({ error: 'auth_backend_not_configured' }, { status: 503 })
  }

  try {
    const body = await req.json()
    const res = await fetch(`${AUTH_API_URL}/auth/login`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(body)
    })

    const data = await res.json()
    if (!res.ok) {
      return NextResponse.json({ error: 'login_failed', detail: data }, { status: res.status })
    }

    // Set HttpOnly cookie with the access token. In production set Secure and SameSite appropriately.
  const token = data.access_token || data.token
  const maxAge = data.expires_in || 3600
  // In production you should set Secure and SameSite=strict; for local dev we'll keep it lax
  const secureFlag = process.env.NODE_ENV === 'production' ? '; Secure; SameSite=Strict' : ''
  const cookie = `gpbroker_session=${token}; Path=/; HttpOnly; Max-Age=${maxAge}${secureFlag}`

  const response = NextResponse.json({ ok: true })
  response.headers.set('Set-Cookie', cookie)
  return response
  } catch (err: any) {
    return NextResponse.json({ error: 'proxy_error', message: String(err.message || err) }, { status: 502 })
  }
}
