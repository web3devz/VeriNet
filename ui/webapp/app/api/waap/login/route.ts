import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.VERINET_API_URL || "http://127.0.0.1:8080";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    const res = await fetch(`${BACKEND_URL}/waap/login`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Accept": "application/json",
      },
      body: JSON.stringify(body),
    });

    const data = await res.json();

    if (!res.ok) {
      return NextResponse.json(
        data,
        { status: res.status }
      );
    }

    return NextResponse.json(data);
  } catch (error: unknown) {
    // If the backend is not running, return a descriptive error
    const message =
      error instanceof Error ? error.message : "Unknown error";

    if (message.includes("ECONNREFUSED") || message.includes("fetch failed")) {
      return NextResponse.json(
        {
          error:
            "VeriNet API backend is not running. Start it with: python api/server.py --port 8080",
        },
        { status: 503 }
      );
    }

    return NextResponse.json({ error: message }, { status: 500 });
  }
}