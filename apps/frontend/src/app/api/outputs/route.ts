import { NextRequest, NextResponse } from "next/server";
import { listFolder, readJson, dropboxRoot } from "@/lib/dropbox";
import fs from "node:fs/promises";
import path from "node:path";

type Variant = {
  ratio: string;
  path: string; // dropbox: or local:
  target_market?: string;
  compliance_score?: number;
};

type Product = {
  name: string;
  variants: Variant[];
};

export async function GET(req: NextRequest) {
  try {
    const { searchParams } = new URL(req.url);
    const campaign = searchParams.get("campaign");
    if (!campaign) {
      return NextResponse.json({ ok: false, error: "Missing campaign" }, { status: 400 });
    }
    const STORAGE_BACKEND = (process.env.STORAGE_BACKEND || "dropbox").toLowerCase();
    const LOCAL_ROOT = process.env.LOCAL_ROOT || "local_storage";

    const outputsRel = `/outputs/${campaign}`;
    const skipDirs = new Set(["finalized", "messages", "carousels", "videos", "approvals", "ingested"]);

    async function listRootNames(): Promise<string[]> {
      if (STORAGE_BACKEND === "local") {
        const base = path.join(LOCAL_ROOT, outputsRel.replace(/^\/+/, ""));
        try {
          const entries = await fs.readdir(base, { withFileTypes: true });
          return entries.filter((e) => e.isDirectory()).map((e) => e.name);
        } catch {
          return [];
        }
      } else {
        return await listFolder(`${dropboxRoot()}${outputsRel}`);
      }
    }

    async function listRatioNames(productSlug: string): Promise<string[]> {
      const rel = `${outputsRel}/${productSlug}`;
      if (STORAGE_BACKEND === "local") {
        const base = path.join(LOCAL_ROOT, rel.replace(/^\/+/, ""));
        try {
          const entries = await fs.readdir(base, { withFileTypes: true });
          return entries.filter((e) => e.isDirectory()).map((e) => e.name);
        } catch {
          return [];
        }
      } else {
        return await listFolder(`${dropboxRoot()}${rel}`);
      }
    }

    async function listFiles(dirRel: string): Promise<string[]> {
      if (STORAGE_BACKEND === "local") {
        const base = path.join(LOCAL_ROOT, dirRel.replace(/^\/+/, ""));
        try {
          const entries = await fs.readdir(base, { withFileTypes: true });
          return entries.filter((e) => e.isFile()).map((e) => e.name);
        } catch {
          return [];
        }
      } else {
        return await listFolder(`${dropboxRoot()}${dirRel}`);
      }
    }

    async function readLineage(dirRel: string, basename: string): Promise<any | null> {
      const lineageRel = `${dirRel}/${basename}.json`;
      if (STORAGE_BACKEND === "local") {
        const base = path.join(LOCAL_ROOT, lineageRel.replace(/^\/+/, ""));
        try {
          const raw = await fs.readFile(base, "utf-8");
          return JSON.parse(raw);
        } catch {
          return null;
        }
      } else {
        try {
          return await readJson(`${dropboxRoot()}${lineageRel}`);
        } catch {
          return null;
        }
      }
    }

    const productSlugs = (await listRootNames()).filter((n) => !skipDirs.has(n));
    const products: Product[] = [];
    for (const slug of productSlugs) {
      const variants: Variant[] = [];
      const ratios = await listRatioNames(slug);
      for (const r of ratios) {
        const dirRel = `${outputsRel}/${slug}/${r}`;
        const files = await listFiles(dirRel);
        for (const f of files) {
          if (!/\.(jpg|jpeg|png|webp|gif)$/i.test(f)) continue;
          const basename = f.replace(/\.(jpg|jpeg|png|webp|gif)$/i, "");
          const lineage = await readLineage(dirRel, basename);
          const item: Variant = {
            ratio: r.replace(/x/g, ":"),
            path:
              STORAGE_BACKEND === "local"
                ? `local:${dirRel}/${f}`
                : `dropbox:${dirRel}/${f}`,
            target_market: lineage?.market,
            compliance_score: lineage?.compliance_score,
          };
          variants.push(item);
        }
      }
      products.push({ name: slug.replace(/_/g, " "), variants });
    }

    return NextResponse.json({ ok: true, campaign, products });
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    return NextResponse.json({ ok: false, error: msg }, { status: 500 });
  }
}

