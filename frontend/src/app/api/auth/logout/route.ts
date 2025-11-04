import { NextResponse } from 'next/server'

export async function POST() {
  const response = NextResponse.json({ ok: true })
  // Clear cookie
  response.headers.set('Set-Cookie', `gpbroker_session=; Path=/; HttpOnly; Max-Age=0`)
  return response
}
