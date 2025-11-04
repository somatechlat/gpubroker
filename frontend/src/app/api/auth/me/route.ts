import { NextResponse } from 'next/server'

const AUTH_API_URL = process.env.AUTH_API_URL || process.env.NEXT_PUBLIC_AUTH_API_URL || ''

export async function GET(req: Request) {
  if (!AUTH_API_URL) {
    return NextResponse.json({ error: 'auth_backend_not_configured' }, { status: 503 })
  }

  try {
    const target = `${AUTH_API_URL}/auth/me`
    const headers: Record<string, string> = {}
    const cookie = req.headers.get('cookie')
    if (cookie) headers['cookie'] = cookie

    const res = await fetch(target, { method: 'GET', headers, cache: 'no-store' })
    const body = await res.text()
    return new NextResponse(body, { status: res.status, headers: { 'content-type': res.headers.get('content-type') || 'application/json' } })
  } catch (err: any) {
    return NextResponse.json({ error: 'proxy_error', message: String(err.message || err) }, { status: 502 })
  }
}
