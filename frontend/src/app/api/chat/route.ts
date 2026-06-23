import { NextRequest, NextResponse } from "next/server";

const AI_SERVICE_URL = process.env.AI_SERVICE_URL ?? "http://localhost:8000";
const INTERNAL_API_KEY = process.env.INTERNAL_API_KEY ?? "";

export async function POST(req: NextRequest) {
  const body = await req.json();

  const upstream = await fetch(`${AI_SERVICE_URL}/query/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-API-Key": INTERNAL_API_KEY },
    body: JSON.stringify({ question: body.question }),
    signal: AbortSignal.timeout(100_000),
  });

  if (!upstream.ok || !upstream.body) {
    return NextResponse.json(
      { error: "AI service error" },
      { status: upstream.status }
    );
  }

  // Pass the SSE stream straight through. Returning upstream.body (a
  // ReadableStream) instead of awaiting .json() means each chunk flows to the
  // browser as it arrives — no buffering. The anti-buffering headers stop
  // proxies (Vercel) from holding the response.
  return new Response(upstream.body, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      "Connection": "keep-alive",
      "X-Accel-Buffering": "no",
    },
  });
}
