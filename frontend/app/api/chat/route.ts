import { NextResponse } from "next/server";
import { API_URL } from "@/mock/api";

export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  try {
    const backendUrl =
      process.env.METRICMIND_API_URL ||
      process.env.NEXT_PUBLIC_METRICMIND_API_URL ||
      API_URL;

    if (!backendUrl || backendUrl.trim() === "") {
      return NextResponse.json(
        {
          error:
            "Backend API URL is not configured. Please set the METRICMIND_API_URL environment variable in your frontend/.env.local file.",
          configured: false,
        },
        { status: 503 }
      );
    }

    const body = await request.json().catch(() => ({}));
    const question = typeof body?.question === "string" ? body.question.trim() : "";

    if (!question) {
      return NextResponse.json(
        { error: "Question is required." },
        { status: 400 }
      );
    }

    // Set a 30 second timeout for AI querying and SQL execution
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 30000);

    let upstreamResponse: Response;
    try {
      upstreamResponse = await fetch(backendUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify({
          question,
          conversation_id: body?.conversation_id,
        }),
        signal: controller.signal,
      });
    } catch (fetchErr: unknown) {
      clearTimeout(timeoutId);

      const err = fetchErr as Error;
      if (err.name === "AbortError") {
        return NextResponse.json(
          {
            error:
              "Backend API timed out while processing your question. The query took longer than 30 seconds to execute.",
          },
          { status: 504 }
        );
      }

      console.error("Backend connection failure:", err.message);
      return NextResponse.json(
        {
          error:
            "Unable to connect to the MetricMind backend API. Please verify that the backend server is running and accessible at the configured URL.",
          details: err.message,
        },
        { status: 502 }
      );
    } finally {
      clearTimeout(timeoutId);
    }

    const contentType = upstreamResponse.headers.get("content-type") || "";

    if (!contentType.includes("application/json")) {
      const text = await upstreamResponse.text();
      console.error(
        `Backend returned non-JSON (${upstreamResponse.status}):`,
        text.slice(0, 300)
      );

      return NextResponse.json(
        {
          error: `The backend returned an unexpected response format (${upstreamResponse.status}).`,
          status: upstreamResponse.status,
        },
        { status: 502 }
      );
    }

    const data = await upstreamResponse.json();

    if (!upstreamResponse.ok) {
      const errorMsg =
        typeof data?.error === "string"
          ? data.error
          : typeof data?.detail === "string"
          ? data.detail
          : typeof data?.message === "string"
          ? data.message
          : `Backend error (${upstreamResponse.status})`;

      return NextResponse.json(
        { error: errorMsg, raw: data },
        { status: upstreamResponse.status }
      );
    }

    return NextResponse.json(data, {
      status: 200,
      headers: { "Cache-Control": "no-store" },
    });
  } catch (error) {
    console.error("API proxy error:", error);

    const errorMessage =
      error instanceof Error ? error.message : "Internal server error";

    return NextResponse.json(
      {
        error: `Failed to process request: ${errorMessage}`,
      },
      { status: 500 }
    );
  }
}