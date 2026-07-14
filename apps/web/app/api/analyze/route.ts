export async function POST(request: Request) {
  const upstream = `${process.env.API_BASE_URL ?? "http://api:8000"}/api/workbooks/analyze`;
  const formData = await request.formData();
  const response = await fetch(upstream, {
    method: "POST",
    body: formData,
    cache: "no-store",
  });

  return new Response(response.body, {
    status: response.status,
    headers: { "content-type": response.headers.get("content-type") ?? "application/json" },
  });
}
