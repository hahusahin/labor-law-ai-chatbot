import { NextRequest, NextResponse } from "next/server";

const AI_SERVICE_URL = process.env.AI_SERVICE_URL ?? "http://localhost:8000";
const INTERNAL_API_KEY = process.env.INTERNAL_API_KEY ?? "";

export async function POST(req: NextRequest) {
  const body = await req.json();

  const upstream = await fetch(`${AI_SERVICE_URL}/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-API-Key": INTERNAL_API_KEY },
    body: JSON.stringify({ question: body.question }),
    signal: AbortSignal.timeout(100_000),
  });

  if (!upstream.ok) {
    return NextResponse.json(
      { error: "AI service error" },
      { status: upstream.status }
    );
  }

  const data = await upstream.json();
  return NextResponse.json(data);
}
