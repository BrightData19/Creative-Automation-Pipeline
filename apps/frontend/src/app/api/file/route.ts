import { NextRequest } from "next/server";
import { dropboxRoot, downloadBytes } from "@/lib/dropbox";
import fs from "node:fs/promises";
import path from "node:path";

function guessContentType(p: string): string {
  const ext = p.toLowerCase().split(".").pop() || "";
  switch (ext) {
    case "jpg":
    case "jpeg":
      return "image/jpeg";
    case "png":
      return "image/png";
    case "gif":
      return "image/gif";
    case "webp":
      return "image/webp";
    case "svg":
      return "image/svg+xml";
    default:
      return "application/octet-stream";
  }
}

export async function GET(req: NextRequest) {
  try {
    const { searchParams } = new URL(req.url);
    const raw = searchParams.get("path");
    if (!raw) {
      return new Response(JSON.stringify({ ok: false, error: "Missing path" }), { status: 400 });
    }
    const STORAGE_BACKEND = (process.env.STORAGE_BACKEND || "dropbox").toLowerCase();
    let buf: Buffer;
    let ct = guessContentType(raw);

    if (raw.startsWith("dropbox:")) {
      const rel = raw.replace(/^dropbox:/, "");
      const p = rel.startsWith("/") ? rel : `${rel}`;
      const full = `${dropboxRoot()}${p.startsWith("/") ? "" : "/"}${p}`;
      buf = await downloadBytes(full);
    } else if (raw.startsWith("local:")) {
      const rel = raw.replace(/^local:/, "");
      const base = process.env.LOCAL_ROOT || "local_storage";
      const full = path.join(base, rel.replace(/^\/+/, ""));
      buf = await fs.readFile(full);
    } else if (STORAGE_BACKEND === "local") {
      // Allow bare relative for local
      const base = process.env.LOCAL_ROOT || "local_storage";
      const full = path.join(base, raw.replace(/^\/+/, ""));
      buf = await fs.readFile(full);
    } else {
      // Assume Dropbox absolute within root
      const full = `${dropboxRoot()}${raw.startsWith("/") ? "" : "/"}${raw}`;
      buf = await downloadBytes(full);
    }

    return new Response(buf, {
      status: 200,
      headers: {
        "Content-Type": ct,
        "Cache-Control": "public, max-age=60",
      },
    });
  } catch (e: any) {
    const msg = e?.message || String(e);
    return new Response(JSON.stringify({ ok: false, error: msg }), { status: 500 });
  }
}

