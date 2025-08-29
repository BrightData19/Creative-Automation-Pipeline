import { Dropbox } from "dropbox";

// Simple fetch implementation for Dropbox API calls
async function dropboxFetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  const response = await fetch(input, {
    ...init,
    headers: {
      ...init?.headers,
      'Authorization': `Bearer ${process.env.DROPBOX_ACCESS_TOKEN}`,
      'Content-Type': 'application/octet-stream',
    },
  });
  return response;
}

// Initialize Dropbox client with our custom fetch
const dbx = new Dropbox({
  accessToken: process.env.DROPBOX_ACCESS_TOKEN,
  fetch: dropboxFetch as any,
});

function norm(p: string) {
  let out = "/" + p.replace(/^\/+/, "");
  out = out.replace(/\/+/, "/");
  if (out.length > 1 && out.endsWith("/")) out = out.slice(0, -1);
  return out;
}

export async function ensureFolder(path: string) {
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

export async function uploadBuffer(path: string, data: Buffer) {
  const np = norm(path);
  try {
    const response = await dropboxFetch('https://content.dropboxapi.com/2/files/upload', {
      method: 'POST',
      headers: {
        'Dropbox-API-Arg': JSON.stringify({
          path: np,
          mode: { '.tag': 'overwrite' },
        }),
      },
      body: data,
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error_summary || 'Upload failed');
    }

    return await response.json();
  } catch (error: any) {
    throw new Error(`Dropbox upload failed: ${error.message}`);
  }
}