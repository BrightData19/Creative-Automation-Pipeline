import { NextRequest, NextResponse } from "next/server";
import { publish } from "@/lib/kafka";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { campaign_name, product, decision, reviewer } = body || {};
    if (!campaign_name || !product || !decision) {
      return NextResponse.json({ ok: false, error: "Missing fields" }, { status: 400 });
    }
    const event = {
      event_id: crypto.randomUUID(),
      ts: new Date().toISOString(),
      campaign_name,
      product,
      decision, // "approved" | "rejected"
      reviewer: reviewer || "anonymous",
    };
    await publish("approvals.decision.v1", event);
    return NextResponse.json({ ok: true, event_id: event.event_id });
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    return NextResponse.json({ ok: false, error: msg }, { status: 500 });
  }
}

export async function GET(req: NextRequest) {
  try {
    const { searchParams } = new URL(req.url);
    const campaign_name = searchParams.get("campaign_name");
    const product = searchParams.get("product");
    const decision = searchParams.get("decision");
    const reviewer = searchParams.get("reviewer") || "slack";
    if (!campaign_name || !product || !decision) {
      return NextResponse.json({ ok: false, error: "Missing fields" }, { status: 400 });
    }
    const event = {
      event_id: crypto.randomUUID(),
      ts: new Date().toISOString(),
      campaign_name,
      product,
      decision,
      reviewer,
    };
    await publish("approvals.decision.v1", event);
    return NextResponse.json({ ok: true, event_id: event.event_id });
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    return NextResponse.json({ ok: false, error: msg }, { status: 500 });
  }
}
