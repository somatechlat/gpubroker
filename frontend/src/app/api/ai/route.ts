import { NextResponse } from 'next/server'

export async function POST(req: Request) {
  const AI_API_URL = process.env.AI_API_URL || process.env.NEXT_PUBLIC_AI_API_URL
  if (!AI_API_URL) return NextResponse.json({ error: 'AI_API_URL not configured' }, { status: 503 })
  const body = await req.text()
  try {
    const res = await fetch(AI_API_URL, { method: 'POST', headers: { 'content-type': req.headers.get('content-type') || 'application/json' }, body, credentials: 'include' })
    const json = await res.json()
    return NextResponse.json(json, { status: res.status })
  } catch (e: any) {
    return NextResponse.json({ error: e.message || 'ai proxy error' }, { status: 502 })
  }
}
