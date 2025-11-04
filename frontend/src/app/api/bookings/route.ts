import { NextResponse } from 'next/server'

export async function POST(req: Request) {
  const BOOKINGS_API_URL = process.env.BOOKINGS_API_URL || process.env.NEXT_PUBLIC_BOOKINGS_API_URL
  if (!BOOKINGS_API_URL) {
    return NextResponse.json({ error: 'BOOKINGS_API_URL not configured' }, { status: 503 })
  }

  const body = await req.text()
  const target = `${BOOKINGS_API_URL.replace(/\/$/, '')}/bookings`

  try {
    const res = await fetch(target, {
      method: 'POST',
      headers: {
        // forward content-type
        'content-type': req.headers.get('content-type') || 'application/json'
      },
      body,
      credentials: 'include'
    })
    const text = await res.text()
    return new NextResponse(text, { status: res.status, headers: { 'content-type': res.headers.get('content-type') || 'application/json' } })
  } catch (e: any) {
    return NextResponse.json({ error: e.message || 'booking proxy error' }, { status: 502 })
  }
}
