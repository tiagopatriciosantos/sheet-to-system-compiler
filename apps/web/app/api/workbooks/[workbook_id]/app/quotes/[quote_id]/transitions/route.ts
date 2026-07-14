import { NextResponse } from "next/server";

const API_BASE_URL = process.env.API_BASE_URL ?? "http://api:8000";

export async function POST(
  request: Request,
  { params }: { params: Promise<{ workbook_id: string; quote_id: string }> },
) {
  const { workbook_id, quote_id } = await params;
  const upstream = await fetch(`${API_BASE_URL}/api/workbooks/${workbook_id}/app/quotes/${quote_id}/transitions`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: await request.text(),
    cache: "no-store",
  });
  return new NextResponse(await upstream.text(), {
    status: upstream.status,
    headers: { "content-type": upstream.headers.get("content-type") ?? "application/json" },
  });
}
