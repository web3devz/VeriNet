import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.VERINET_API_URL || "http://127.0.0.1:8080";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const claim = body?.claim?.trim();

    if (!claim) {
      return NextResponse.json(
        { error: "Missing 'claim' field." },
        { status: 400 }
      );
    }

    if (claim.length > 2000) {
      return NextResponse.json(
        { error: "Claim too long (max 2000 chars)." },
        { status: 400 }
      );
    }

    const res = await fetch(`${BACKEND_URL}/verify`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ claim }),
    });

    if (!res.ok) {
      const errText = await res.text().catch(() => "Backend error");
      return NextResponse.json(
        { error: `Backend returned ${res.status}: ${errText}` },
        { status: res.status }
      );
    }

    const data = await res.json();
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
