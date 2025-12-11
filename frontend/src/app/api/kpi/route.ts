import { NextResponse } from 'next/server'

const KPI_API_URL = process.env.KPI_API_URL || process.env.NEXT_PUBLIC_KPI_API_URL || ''

export async function GET() {
  if (!KPI_API_URL) {
    return NextResponse.json(
      { error: 'kpi_backend_not_configured', message: 'Set KPI_API_URL or NEXT_PUBLIC_KPI_API_URL to point to the KPI service (/insights/market).' },
      { status: 503 }
    )
  }

  try {
    const target = `${KPI_API_URL.replace(/\/$/, '')}/insights/market`
    const res = await fetch(target, { cache: 'no-store' })
    const bodyText = await res.text()

    return new NextResponse(bodyText, {
      status: res.status,
      headers: {
        'content-type': res.headers.get('content-type') || 'application/json'
      }
    })
  } catch (err: any) {
    return NextResponse.json(
      { error: 'kpi_proxy_error', message: String(err?.message || err) },
      { status: 502 }
    )
  }
}
