import { NextResponse } from 'next/server'

const BACKEND_URL = process.env.PROVIDER_API_URL || process.env.NEXT_PUBLIC_PROVIDER_API_URL || ''

export async function GET(req: Request) {
  if (!BACKEND_URL) {
    return NextResponse.json(
      { error: 'Provider backend not configured', message: 'Set PROVIDER_API_URL or NEXT_PUBLIC_PROVIDER_API_URL in your environment to enable provider data proxying.' },
      { status: 503 }
    )
  }

  try {
    const url = new URL(req.url)
    const qs = url.search
    const target = `${BACKEND_URL}/providers${qs}`

    const incomingHeaders: Record<string, string> = {}
    // forward Authorization header if present
    const auth = req.headers.get('authorization')
    if (auth) incomingHeaders['authorization'] = auth

    // forward cookies from incoming request to backend so auth works server-to-server
    const cookie = req.headers.get('cookie')
    if (cookie) incomingHeaders['cookie'] = cookie

    const res = await fetch(target, {
      method: 'GET',
      headers: incomingHeaders,
      cache: 'no-store'
    })

    const body = await res.text()
    return new NextResponse(body, { status: res.status, headers: { 'content-type': res.headers.get('content-type') || 'application/json' } })
  } catch (err: any) {
    return NextResponse.json({ error: 'proxy_error', message: String(err.message || err) }, { status: 502 })
  }
}
