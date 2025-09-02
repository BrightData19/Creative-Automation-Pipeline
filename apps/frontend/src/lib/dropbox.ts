// Install required dependencies:
// npm install node-fetch @types/node-fetch dropbox
import fetch from "node-fetch";
import { Dropbox, DropboxResponse } from "dropbox";

// Proper fetch polyfill for Node.js environment
if (typeof globalThis !== "undefined" && !globalThis.fetch) {
  globalThis.fetch = fetch as any;
  // globalThis.Headers = fetch.Headers as any;
  // globalThis.Request = fetch.Request as any;
  // globalThis.Response = fetch.Response as any;
}

// Initialize Dropbox using refresh token + app credentials
const dbx = new Dropbox({
  clientId: process.env.DROPBOX_APP_KEY,
  clientSecret: process.env.DROPBOX_APP_SECRET,
  refreshToken: process.env.DROPBOX_REFRESH_TOKEN,
  fetch: fetch as any,
});

function norm(p: string): string {
  let out = "/" + p.replace(/^\/+/, "");
  out = out.replace(/\/+/g, "/"); // Fixed regex to replace all occurrences
  if (out.length > 1 && out.endsWith("/")) out = out.slice(0, -1);
  return out;
}

export async function ensureFolder(path: string): Promise<void> {
  const np = norm(path);
  try {
    await dbx.filesGetMetadata({ path: np });
  } catch {
    try {
      await dbx.filesCreateFolderV2({ path: np });
    } catch {
      // ignore if already exists
    }
  }
}

export function dropboxRoot(): string {
  const root = process.env.DROPBOX_ROOT || "/Apps/CreativeAutomation";
  let out = "/" + root.replace(/^\/+/, "");
  out = out.replace(/\/+/g, "/");
  if (out.length > 1 && out.endsWith("/")) out = out.slice(0, -1);
  return out;
}

export async function listFolder(path: string): Promise<string[]> {
  const np = norm(path);
  const out: string[] = [];
  try {
    let res = await dbx.filesListFolder({ path: np });
    out.push(...res.result.entries.map((e: any) => e.name));
    while (res.result.has_more) {
      res = await dbx.filesListFolderContinue({ cursor: res.result.cursor });
      out.push(...res.result.entries.map((e: any) => e.name));
    }
  } catch (e) {
    // If folder not found, return empty list
    return [];
  }
  return out;
}

export async function downloadBytes(path: string): Promise<Buffer> {
  const np = norm(path);
  const res = await dbx.filesDownload({ path: np });
  // dropbox SDK returns different shapes depending on env; normalize to Buffer
  const anyRes: any = res;
  if (anyRes.result?.fileBinary) {
    const bin = anyRes.result.fileBinary as ArrayBuffer | string;
    return Buffer.isBuffer(bin)
      ? (bin as Buffer)
      : typeof bin === "string"
      ? Buffer.from(bin, "binary")
      : Buffer.from(new Uint8Array(bin as ArrayBuffer));
  }
  if (anyRes.result?.fileBlob) {
    const ab = await (anyRes.result.fileBlob as Blob).arrayBuffer();
    return Buffer.from(new Uint8Array(ab));
  }
  throw new Error("Unexpected Dropbox download result shape");
}

export async function readJson<T = any>(path: string): Promise<T> {
  const buf = await downloadBytes(path);
  return JSON.parse(buf.toString("utf-8")) as T;
}

// Primary method: Use Dropbox SDK (recommended)
export async function uploadBuffer(
  buffer: Buffer,
  path: string
): Promise<DropboxResponse<any>> {
  try {
    // Validate refresh credentials exist
    if (
      !process.env.DROPBOX_REFRESH_TOKEN ||
      !process.env.DROPBOX_APP_KEY ||
      !process.env.DROPBOX_APP_SECRET
    ) {
      throw new Error(
        "Dropbox credentials missing: set DROPBOX_REFRESH_TOKEN, DROPBOX_APP_KEY, DROPBOX_APP_SECRET"
      );
    }

    // Use the SDK method for better reliability
    const result = await dbx.filesUpload({
      path: norm(path),
      contents: buffer,
      mode: { ".tag": "add" }, // Proper mode specification
      autorename: true,
      mute: false,
    });

    return result;
  } catch (error: any) {
    // Enhanced error handling
    let errorMessage = "Unknown Dropbox error";

    if (error.error) {
      // Dropbox API error
      if (typeof error.error === "string") {
        errorMessage = error.error;
      } else if (error.error.error_summary) {
        errorMessage = error.error.error_summary;
      } else if (error.error.error) {
        errorMessage = JSON.stringify(error.error.error);
      }
    } else if (error.message) {
      errorMessage = error.message;
    }

    throw new Error(`Dropbox upload failed: ${errorMessage}`);
  }
}

// Alternative method: Direct API call with proper error handling
export async function uploadBufferDirect(
  buffer: Buffer,
  path: string,
  accessToken?: string
): Promise<DropboxResponse<any>> {
  try {
    // Use provided token or environment variable; otherwise derive via refresh
    let token = accessToken || process.env.DROPBOX_ACCESS_TOKEN;
    if (!token) {
      try {
        const authAny = (dbx as unknown as { auth?: any }).auth;
        if (authAny?.checkAndRefreshAccessToken) {
          await authAny.checkAndRefreshAccessToken();
        }
        if (authAny?.getAccessToken) {
          token = authAny.getAccessToken();
        }
      } catch {}
    }

    if (!token) {
      throw new Error("Access token is required (or configure refresh credentials)");
    }

    // Validate token format (basic check)
    if (!token.startsWith("sl.") && !token.startsWith("aal_")) {
      console.warn(
        'Warning: Access token may be malformed. Dropbox tokens typically start with "sl." or "aal_"'
      );
    }

    const response = await fetch(
      "https://content.dropboxapi.com/2/files/upload",
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Dropbox-API-Arg": JSON.stringify({
            path: norm(path),
            mode: "add",
            autorename: true,
            mute: false,
          }),
          "Content-Type": "application/octet-stream",
        },
        body: buffer,
      }
    );

    // Handle non-OK responses
    if (!response.ok) {
      const responseText = await response.text();

      let errorDetails;
      try {
        errorDetails = JSON.parse(responseText);
      } catch {
        // If response is not JSON, create structured error
        errorDetails = {
          error: responseText,
          status: response.status,
          statusText: response.statusText,
        };
      }

      throw new Error(
        `Dropbox API Error (${response.status}): ${JSON.stringify(
          errorDetails
        )}`
      );
    }

    // Parse successful response
    const responseText = await response.text();
    try {
      return JSON.parse(responseText) as DropboxResponse<any>;
    } catch (parseError) {
      throw new Error(
        `Invalid JSON response from Dropbox: ${responseText.substring(
          0,
          200
        )}...`
      );
    }
  } catch (error: any) {
    // Re-throw custom errors as-is
    if (
      error.message.includes("Dropbox API Error") ||
      error.message.includes("Access token")
    ) {
      throw error;
    }

    // Handle other errors
    const errorMessage = error.message || "Unknown error occurred";
    throw new Error(`Dropbox upload failed: ${errorMessage}`);
  }
}

// Utility function to validate access token
export function validateAccessToken(token: string): boolean {
  if (!token || typeof token !== "string") {
    return false;
  }

  // Basic format validation for Dropbox tokens
  return (
    token.startsWith("sl.") || token.startsWith("aal_") || token.length > 20
  );
}

// Usage example:
/*
try {
  const result = await uploadBuffer(bufferData, '/path/to/file.txt');
  console.log('Upload successful:', result);
} catch (error) {
  console.error('Upload failed:', error.message);
}
*/
