import { NextResponse } from 'next/server'

const AI_API_URL = process.env.AI_API_URL || process.env.NEXT_PUBLIC_AI_API_URL || ''

export async function POST(req: Request) {
  if (!AI_API_URL) {
    return NextResponse.json({ error: 'ai_backend_not_configured' }, { status: 503 })
  }

  try {
    const body = await req.json()
    const res = await fetch(`${AI_API_URL.replace(/\/$/, '')}/ai/parse-workload`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(body),
    })
    const text = await res.text()
    return new NextResponse(text, { status: res.status, headers: { 'content-type': res.headers.get('content-type') || 'application/json' } })
  } catch (err: any) {
    return NextResponse.json({ error: 'ai_proxy_error', message: String(err?.message || err) }, { status: 502 })
  }
}
