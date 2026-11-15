
import { NextRequest, NextResponse } from "next/server";


function getApiConfig() {
  const apiUrl = process.env.API_BASE_URL;
  const apiKey = process.env.APP_API_KEY;

  if (!apiUrl || !apiKey) {
    return null;
  }

  return { apiUrl, apiKey };
}

async function getUpstreamError(response: Response) {
  try {
    return await response.json();
  } catch {
    return { detail: `Backend request failed (${response.status}).` };
  }
}

// List documents from FastAPI.
export async function GET() {
  const config = getApiConfig();

  if (!config) {
    return NextResponse.json(
      { detail: "API configuration is missing on the server." },
      { status: 500 }
    );
  }

  try {
    const upstream = await fetch(`${config.apiUrl}/documents`, {
      method: "GET",
      headers: {
        "X-API-Key": config.apiKey,
      },
      cache: "no-store",
      signal: AbortSignal.timeout(15000),
    });

    const body = upstream.ok
      ? await upstream.json()
      : await getUpstreamError(upstream);

    return NextResponse.json(body, {
      status: upstream.status,
    });
  } catch (error) {
    console.error("Document listing request failed:", error);

    return NextResponse.json(
      { detail: "Unable to retrieve documents from the AI service." },
      { status: 502 }
    );
  }
}

// Upload a PDF to FastAPI.
export async function POST(request: NextRequest) {
  const config = getApiConfig();

  if (!config) {
    return NextResponse.json(
      { detail: "API configuration is missing on the server." },
      { status: 500 }
    );
  }

  let formData: FormData;

  try {
    formData = await request.formData();
  } catch {
    return NextResponse.json(
      { detail: "Invalid multipart upload request." },
      { status: 400 }
    );
  }

  const file = formData.get("file");

  if (!(file instanceof File) || file.size === 0) {
    return NextResponse.json(
      { detail: "Please select a PDF file to upload." },
      { status: 422 }
    );
  }

  if (!file.name.toLowerCase().endsWith(".pdf")) {
    return NextResponse.json(
      { detail: "Only PDF files are supported." },
      { status: 422 }
    );
  }

  if (file.size > 10 * 1024 * 1024) {
    return NextResponse.json(
      { detail: "The PDF must be 10 MB or smaller." },
      { status: 413 }
    );
  }

  try {
    const upstream = await fetch(
      `${config.apiUrl}/documents/upload`,
      {
        method: "POST",
        headers: {
          "X-API-Key": config.apiKey,
        },
        body: formData,
        cache: "no-store",
        signal: AbortSignal.timeout(90000),
      }
    );

    const body = upstream.ok
      ? await upstream.json()
      : await getUpstreamError(upstream);

    return NextResponse.json(body, {
      status: upstream.status,
    });
  } catch (error) {
    console.error("Document upload request failed:", error);

    return NextResponse.json(
      { detail: "Unable to upload the document to the AI service." },
      { status: 502 }
    );
  }
}
