import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.VERINET_API_URL || "http://127.0.0.1:8080";

export async function GET(
  request: NextRequest,
  context: { params: Promise<{ address: string }> }
) {
  try {
    const params = await context.params;
    const { address } = params;
    const { searchParams } = new URL(request.url);
    const network = searchParams.get("network") || "optimism";

    console.log("Passport API route - address:", address, "network:", network);

    if (!address) {
      return NextResponse.json(
        { error: "Missing address parameter" },
        { status: 400 }
      );
    }

    // Validate address format before making backend request
    if (!isValidEthereumAddress(address)) {
      return NextResponse.json(
        { error: "Invalid Ethereum address format. Address must be 42 characters starting with 0x." },
        { status: 400 }
      );
    }

    const backendUrl = `${BACKEND_URL}/passport/status/${encodeURIComponent(address)}?network=${encodeURIComponent(network)}`;
    console.log("Calling backend URL:", backendUrl);

    const res = await fetch(backendUrl, {
      method: "GET",
      headers: {
        "Accept": "application/json",
      },
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

    console.error("Passport API route error:", message);

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

// Helper function to validate Ethereum address format
function isValidEthereumAddress(address: string): boolean {
  return (
    typeof address === "string" &&
    address.startsWith("0x") &&
    address.length === 42 &&
    /^0x[a-fA-F0-9]{40}$/.test(address)
  );
}