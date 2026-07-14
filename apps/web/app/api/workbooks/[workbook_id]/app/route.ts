import { NextResponse } from "next/server";

const API_BASE_URL = process.env.API_BASE_URL ?? "http://api:8000";

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ workbook_id: string }> },
) {
  const { workbook_id } = await params;
  const upstream = await fetch(`${API_BASE_URL}/api/workbooks/${workbook_id}/app`, { cache: "no-store" });
  return new NextResponse(await upstream.text(), {
    status: upstream.status,
    headers: { "content-type": upstream.headers.get("content-type") ?? "application/json" },
  });
}
