import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";
import { publish } from "@/lib/kafka";
import { uploadBuffer, ensureFolder } from "@/lib/dropbox";
import fs from "fs/promises";
import path from "path";

function slugify(s: string) {
  return s
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

const BriefSchema = z.object({
  campaign_name: z.string(),
  brand_name: z.string().optional().nullable(),
  brand_palette: z.array(z.string()).optional().nullable(),
  target_market: z.string(),
  target_audience: z.string(),
  campaign_message: z.string(),
  products: z
    .array(
      z.object({
        name: z.string(),
        image: z.string().nullable().optional(),
      })
    )
    .min(2),
  logo_path: z.string().nullable().optional(),
  inbox_folder: z.string(),
});

export async function POST(req: NextRequest) {
  try {
    const STORAGE_BACKEND = (
      process.env.STORAGE_BACKEND || "dropbox"
    ).toLowerCase();
    const contentType = req.headers.get("content-type") || "";
    let brief: z.infer<typeof BriefSchema>;
    let uploadedAssets: { name: string; dropboxPath: string }[] = [];

    if (contentType.includes("multipart/form-data")) {
      const form = await req.formData();
      const briefStr = form.get("brief");
      if (typeof briefStr !== "string")
        throw new Error("Missing brief JSON in form field 'brief'");
      brief = BriefSchema.parse(JSON.parse(briefStr));

      // Upload assets to Dropbox under /assets/<campaign>
      // Determine storage backend and target directory
      const dropboxRoot =
        process.env.DROPBOX_ROOT || "/Apps/CreativeAutomation";
      const localRoot = process.env.LOCAL_ROOT || "local_storage";
      const campaignRel = `/assets/${brief.campaign_name}`;

      if (STORAGE_BACKEND === "dropbox") {
        const campaignDir = campaignRel; // relative path within Dropbox root
        await ensureFolder(campaignDir);

        for (const [key, value] of form.entries()) {
          if (
            key !== "brief" &&
            key !== "mapping" &&
            value instanceof File &&
            value.size > 0
          ) {
            const arrayBuffer = await value.arrayBuffer();
            const buf = Buffer.from(arrayBuffer);
            const destPath = `${campaignDir}/${value.name}`;
            await uploadBuffer(buf, destPath);
            uploadedAssets.push({
              name: value.name,
              dropboxPath: `dropbox:${destPath}`,
            });
          }
        }
        // set inbox_folder for Dropbox
        (brief as any).inbox_folder = `dropbox:${campaignRel}`;
      } else {
        // Local storage fallback (no Dropbox credentials required)
        const campaignFsDir = path.join(localRoot, campaignRel);
        await fs.mkdir(campaignFsDir, { recursive: true });

        for (const [key, value] of form.entries()) {
          if (
            key !== "brief" &&
            key !== "mapping" &&
            value instanceof File &&
            value.size > 0
          ) {
            const arrayBuffer = await value.arrayBuffer();
            const buf = Buffer.from(arrayBuffer);
            const destFsPath = path.join(campaignFsDir, value.name);
            await fs.writeFile(destFsPath, buf);
            uploadedAssets.push({
              name: value.name,
              dropboxPath: `local:${campaignRel}/${value.name}`,
            });
          }
        }
        // set inbox_folder for Local
        (brief as any).inbox_folder = `local:${campaignRel}`;
      }

      // Infer logo_path and product images when filenames match
      const lowerNames = uploadedAssets.map((a) => ({
        ...a,
        slug: slugify(a.name),
      }));
      // inbox_folder already set per backend above

      // Parse explicit mapping if present
      const mappingRaw = form.get("mapping");
      let mapping: any = null;
      if (typeof mappingRaw === "string") {
        try {
          mapping = JSON.parse(mappingRaw);
        } catch {}
      }

      // logo via mapping or fallback filename token "logo"
      if (mapping?.logoFile) {
        const matched = uploadedAssets.find((a) => a.name === mapping.logoFile);
        if (matched) (brief as any).logo_path = matched.dropboxPath;
      } else {
        const logo = lowerNames.find((a) => a.slug.includes("logo"));
        if (logo) (brief as any).logo_path = logo.dropboxPath;
      }

      // match images to products by name slug
      for (const p of brief.products) {
        const pslug = slugify(p.name);
        let hit = null;
        if (mapping?.productMap && mapping.productMap[p.name]) {
          hit =
            uploadedAssets.find((a) => a.name === mapping.productMap[p.name]) ||
            null;
        }
        if (!hit) {
          const bySlug = lowerNames.find((a) => a.slug.includes(pslug));
          if (bySlug) hit = bySlug;
        }
        if (hit) (p as any).image = (hit as any).dropboxPath || hit;
      }

      // Force-generate-new toggle
      if (mapping?.force_generate_new === true) {
        (brief as any).force_generate_new = true;
      }
    } else {
      const body = await req.json();
      brief = BriefSchema.parse(body);
    }

    const event = {
      event_id: crypto.randomUUID(),
      ts: new Date().toISOString(),
      ...brief,
    };
    await publish("briefs.ingest.v1", event);
    return NextResponse.json({
      ok: true,
      event_id: event.event_id,
      assets: uploadedAssets,
    });
  } catch (err: unknown) {
    console.error("POST /api/briefs error", err);
    const message = err instanceof Error ? err.message : "Invalid request";
    return NextResponse.json({ ok: false, error: message }, { status: 400 });
  }
}
