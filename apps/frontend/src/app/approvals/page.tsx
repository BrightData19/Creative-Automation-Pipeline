"use client";

import React, { useEffect, useMemo, useState } from "react";

type Variant = {
  ratio: string;
  path: string;
  target_market?: string;
  compliance_score?: number;
};

type Product = {
  name: string;
  variants: Variant[];
};

export default function ApprovalsPage() {
  const [campaign, setCampaign] = useState("");
  const [reviewer, setReviewer] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [products, setProducts] = useState<Product[]>([]);
  const [decisions, setDecisions] = useState<Record<string, "approved" | "rejected" | undefined>>({});

  const canLoad = useMemo(() => campaign.trim().length > 0, [campaign]);

  async function loadCampaign() {
    if (!canLoad) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`/api/outputs?campaign=${encodeURIComponent(campaign)}`);
      const data = await res.json();
      if (!data.ok) {
        throw new Error(data.error || "Failed to load outputs");
      }
      setProducts(data.products || []);
    } catch (e: any) {
      setError(e?.message || String(e));
    } finally {
      setLoading(false);
    }
  }

  async function decide(product: string, decision: "approved" | "rejected") {
    try {
      const body = {
        campaign_name: campaign,
        product,
        decision,
        reviewer: reviewer || "ui",
      };
      const res = await fetch("/api/approvals", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (!res.ok || !data.ok) throw new Error(data.error || "Approval failed");
      setDecisions((prev) => ({ ...prev, [product]: decision }));
    } catch (e: any) {
      alert(e?.message || String(e));
    }
  }

  return (
    <main className="min-h-screen bg-gradient-to-br from-gray-50 via-rose-50/30 to-purple-50/30 py-8">
      <div className="mx-auto max-w-7xl px-6 space-y-8">
        <div className="text-center space-y-4">
          <h1 className="text-5xl font-bold bg-gradient-to-r from-gray-900 via-red-800 to-purple-800 bg-clip-text text-transparent">
            Approvals
          </h1>
          <p className="text-gray-600 text-lg">Human-in-the-loop review and approval of generated assets</p>
        </div>

        <div className="bg-white/70 backdrop-blur-sm rounded-2xl p-6 border border-white/20 shadow-xl">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-end">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Campaign</label>
              <input
                type="text"
                placeholder="e.g., Indian Monsoon Refresh 2024"
                value={campaign}
                onChange={(e) => setCampaign(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-red-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Reviewer</label>
              <input
                type="text"
                placeholder="Your name (optional)"
                value={reviewer}
                onChange={(e) => setReviewer(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-purple-500"
              />
            </div>
            <div className="flex gap-3">
              <button
                disabled={!canLoad || loading}
                onClick={loadCampaign}
                className="px-5 py-2 rounded-lg font-semibold text-white disabled:opacity-50"
                style={{ backgroundColor: "var(--color-primary)" }}
              >
                {loading ? "Loading..." : "Load"}
              </button>
              <button
                onClick={() => { setProducts([]); setDecisions({}); setError(null); }}
                className="px-4 py-2 rounded-lg border border-gray-300 text-sm"
              >
                Clear
              </button>
            </div>
          </div>
          {error && (
            <div className="mt-3 text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg p-3">{error}</div>
          )}
        </div>

        {products.length === 0 ? (
          <div className="text-center py-24">
            <div className="w-24 h-24 bg-gradient-to-br from-gray-100 to-gray-200 rounded-full flex items-center justify-center mx-auto mb-6">
              <span className="text-4xl">🧪</span>
            </div>
            <h3 className="text-2xl font-bold text-gray-900 mb-2">No products loaded</h3>
            <p className="text-gray-600">Enter a campaign name and click Load to review assets.</p>
          </div>
        ) : (
          <div className="space-y-8">
            {products.map((p) => (
              <div key={p.name} className="bg-white/70 backdrop-blur-sm rounded-2xl p-6 border border-white/20 shadow-xl">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h3 className="text-xl font-bold text-gray-900">{p.name}</h3>
                    {typeof decisions[p.name] !== "undefined" && (
                      <div className={`text-sm mt-1 ${decisions[p.name] === "approved" ? "text-emerald-700" : "text-red-700"}`}>
                        {decisions[p.name] === "approved" ? "Approved" : "Rejected"}
                      </div>
                    )}
                  </div>
                  <div className="flex gap-3">
                    <button
                      onClick={() => decide(p.name, "approved")}
                      className="px-4 py-2 rounded-lg text-white font-semibold bg-emerald-600 hover:bg-emerald-700"
                    >
                      Approve
                    </button>
                    <button
                      onClick={() => decide(p.name, "rejected")}
                      className="px-4 py-2 rounded-lg text-white font-semibold bg-red-600 hover:bg-red-700"
                    >
                      Reject
                    </button>
                  </div>
                </div>

                {p.variants.length === 0 ? (
                  <div className="text-gray-600 text-sm">No variants found for this product.</div>
                ) : (
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
                    {p.variants.map((v, idx) => (
                      <div key={idx} className="rounded-xl border border-gray-200 bg-white shadow-sm overflow-hidden">
                        <div className="aspect-square bg-gray-100">
                          {/* proxy image via API to support Dropbox/local */}
                          {/* eslint-disable-next-line @next/next/no-img-element */}
                          <img
                            src={`/api/file?path=${encodeURIComponent(v.path)}`}
                            alt={`${p.name} ${v.ratio}`}
                            className="w-full h-full object-cover"
                          />
                        </div>
                        <div className="p-3 text-sm text-gray-700 flex items-center justify-between">
                          <div>
                            <div className="font-medium">{v.ratio}</div>
                            {v.target_market && <div className="text-gray-500">{v.target_market}</div>}
                          </div>
                          {typeof v.compliance_score === "number" && (
                            <div className="text-xs px-2 py-1 rounded bg-emerald-50 text-emerald-700 border border-emerald-200">
                              Score {(v.compliance_score * 100).toFixed(0)}%
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}

