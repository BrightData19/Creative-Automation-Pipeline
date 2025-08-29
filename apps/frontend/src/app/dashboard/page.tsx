"use client";

import React, { useEffect, useState } from "react";
import { connectEvents, type GatewayEvent } from "@/lib/sse";
import { EventCard } from "@/components/event-card";

export default function DashboardPage() {
  const [events, setEvents] = useState<GatewayEvent[]>([]);
  const [connectionStatus, setConnectionStatus] = useState<
    "connecting" | "connected" | "error"
  >("connecting");

  useEffect(() => {
    const unsub = connectEvents(
      (evt) => {
        setEvents((prev) => [evt, ...prev].slice(0, 200));
        setConnectionStatus("connected");
      },
      (err) => {
        const msg = err instanceof Error ? err.message : (err as any)?.type || "SSE error";
        console.error("SSE connection error:", msg);
        setConnectionStatus("error");
      },
      () => {
        // Connection is open; we may still be waiting for first event
        setConnectionStatus("connected");
      }
    );
    return () => unsub();
  }, []);

  const getConnectionStatusColor = () => {
    switch (connectionStatus) {
      case "connected":
        return "text-emerald-600 bg-emerald-50 border-emerald-200";
      case "error":
        return "text-red-600 bg-red-50 border-red-200";
      default:
        return "text-amber-600 bg-amber-50 border-amber-200";
    }
  };

  const getConnectionStatusIcon = () => {
    switch (connectionStatus) {
      case "connected":
        return "🟢";
      case "error":
        return "🔴";
      default:
        return "🟡";
    }
  };

  const getConnectionStatusText = () => {
    switch (connectionStatus) {
      case "connected":
        return "Live";
      case "error":
        return "Disconnected";
      default:
        return "Connecting...";
    }
  };

  const pipelineEvents = events.filter((e) => e.topic === "pipeline.status.v1");
  const assetEvents = events.filter((e) => e.topic === "assets.created.v1");
  const alertEvents = events.filter((e) => e.topic === "alerts.v1");
  const briefEvents = events.filter((e) => e.topic === "briefs.ingest.v1");
  const complianceEvents = events.filter((e) => e.topic === "compliance.v1");
  const approvalsReqEvents = events.filter((e) => e.topic === "approvals.request.v1");
  const approvalsDecEvents = events.filter((e) => e.topic === "approvals.decision.v1");
  const perfEvents = events.filter((e) => e.topic === "performance.metrics.v1");

  // Derived metrics from compliance for visualization
  const avgCompliance = (() => {
    const scores = complianceEvents
      .map((e: any) => e.compliance_report?.overall_score)
      .filter((x: any) => typeof x === "number") as number[];
    if (scores.length === 0) return 0;
    return scores.reduce((a, b) => a + b, 0) / scores.length;
  })();

  const piiIssues = (() => {
    let total = 0;
    for (const e of complianceEvents as any[]) {
      const pc = e.compliance_report?.compliance_breakdown?.privacy_compliance;
      if (pc?.pii_items) {
        total += Object.values(pc.pii_items).reduce((acc: number, arr: any) => acc + (Array.isArray(arr) ? arr.length : 0), 0);
      }
    }
    return total;
  })();

  const ethicsIssues = (() => {
    let total = 0;
    for (const e of complianceEvents as any[]) {
      const ec = e.compliance_report?.compliance_breakdown?.ethics_compliance;
      if (Array.isArray(ec?.issues)) total += ec.issues.length;
    }
    return total;
  })();

  const avgCTR = (() => {
    const arr = (perfEvents as any[]).map((e) => e.metrics?.ctr).filter((x: any) => typeof x === "number");
    if (arr.length === 0) return 0;
    return (arr.reduce((a: number, b: number) => a + b, 0) / arr.length) * 100;
  })();
  const avgCPA = (() => {
    const arr = (perfEvents as any[]).map((e) => e.metrics?.cpa).filter((x: any) => typeof x === "number");
    if (arr.length === 0) return 0;
    return arr.reduce((a: number, b: number) => a + b, 0) / arr.length;
  })();

  // Topic filters for observability view
  const [topicFilters, setTopicFilters] = useState<Record<string, boolean>>({
    all: true,
    "briefs.ingest.v1": true,
    "pipeline.status.v1": true,
    "assets.created.v1": true,
    "compliance.v1": true,
    "alerts.v1": true,
    other: true,
  });

  const toggleFilter = (key: string) => {
    setTopicFilters((prev) => {
      if (key === "all") {
        const next: Record<string, boolean> = {} as any;
        Object.keys(prev).forEach((k) => (next[k] = true));
        return next;
      }
      const next = { ...prev, [key]: !prev[key], all: false };
      // if all others true after toggle, mark all=true for UX
      const keys = Object.keys(next).filter((k) => k !== "all");
      if (keys.every((k) => next[k])) next.all = true;
      return next;
    });
  };

  const visibleEvents = events.filter((e) => {
    if (topicFilters.all) return true;
    const t = (e.topic as string) || "unknown";
    return t in topicFilters ? !!topicFilters[t] : !!topicFilters.other;
  });

  return (
    <main className="min-h-screen bg-gradient-to-br from-gray-50 via-red-50/30 to-purple-50/30 py-8">
      <div className="mx-auto max-w-7xl px-6 space-y-8">
        {/* Hero Header */}
        <div className="text-center space-y-4">
          <h1 className="text-5xl font-bold bg-gradient-to-r from-gray-900 via-red-800 to-purple-800 bg-clip-text text-transparent">
            Pipeline Dashboard
          </h1>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto leading-relaxed">
            Real-time monitoring of your AI-powered creative automation
            pipeline. Watch as campaigns transform from briefs to stunning
            visual assets.
          </p>
        </div>

        {/* Connection Status */}
        <div className="flex justify-center">
          <div
            className={`inline-flex items-center space-x-3 px-6 py-3 rounded-full border-2 ${getConnectionStatusColor()} shadow-sm`}
          >
            <span className="text-lg">{getConnectionStatusIcon()}</span>
            <span className="font-semibold">{getConnectionStatusText()}</span>
            <div className="text-xs opacity-75">
              Gateway:{" "}
              {process.env.NEXT_PUBLIC_GATEWAY_URL || "http://localhost:3001"}
            </div>
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-6">
          <div className="group bg-white/70 backdrop-blur-sm rounded-2xl p-6 border border-white/20 shadow-xl hover:shadow-2xl transition-all duration-300 hover:scale-105">
            <div className="flex items-center justify-between mb-4">
              <div className="w-12 h-12 bg-gradient-to-br from-[#fa0f00] to-[#c70d00] rounded-xl flex items-center justify-center shadow-lg">
                <span className="text-white text-xl">📊</span>
              </div>
              <div className="text-3xl font-bold text-red-600 group-hover:text-red-700 transition-colors">
                {events.length}
              </div>
            </div>
            <div className="text-sm font-medium text-red-700">
              Total Events
            </div>
            <div className="text-xs text-red-600/70 mt-1">
              Real-time activity
            </div>
          </div>

          <div className="group bg-white/70 backdrop-blur-sm rounded-2xl p-6 border border-white/20 shadow-xl hover:shadow-2xl transition-all duration-300 hover:scale-105">
            <div className="flex items-center justify-between mb-1">
              <div className="w-12 h-12 bg-gradient-to-br from-emerald-500 to-emerald-600 rounded-xl flex items-center justify-center shadow-lg">
                <span className="text-white text-xl">🛡️</span>
              </div>
              <div className="text-3xl font-bold text-emerald-600 group-hover:text-emerald-700 transition-colors">
                {(avgCompliance * 100).toFixed(0)}%
              </div>
            </div>
            <div className="text-sm font-medium text-emerald-700">Avg Compliance</div>
            <div className="text-xs text-emerald-600/70 mt-1">Weighted score</div>
          </div>

          <div className="group bg-white/70 backdrop-blur-sm rounded-2xl p-6 border border-white/20 shadow-xl hover:shadow-2xl transition-all duration-300 hover:scale-105">
            <div className="flex items-center justify-between mb-1">
              <div className="w-12 h-12 bg-gradient-to-br from-red-500 to-red-600 rounded-xl flex items-center justify-center shadow-lg">
                <span className="text-white text-xl">🧩</span>
              </div>
              <div className="text-3xl font-bold text-red-600 group-hover:text-red-700 transition-colors">{piiIssues}</div>
            </div>
            <div className="text-sm font-medium text-red-700">PII Flags</div>
            <div className="text-xs text-red-600/70 mt-1">Total detected</div>
          </div>

          <div className="group bg-white/70 backdrop-blur-sm rounded-2xl p-6 border border-white/20 shadow-xl hover:shadow-2xl transition-all duration-300 hover:scale-105">
            <div className="flex items-center justify-between mb-1">
              <div className="w-12 h-12 bg-gradient-to-br from-purple-500 to-purple-600 rounded-xl flex items-center justify-center shadow-lg">
                <span className="text-white text-xl">⚖️</span>
              </div>
              <div className="text-3xl font-bold text-purple-600 group-hover:text-purple-700 transition-colors">{ethicsIssues}</div>
            </div>
            <div className="text-sm font-medium text-purple-700">Ethics Flags</div>
            <div className="text-xs text-purple-600/70 mt-1">Total detected</div>
          </div>

          <div className="group bg-white/70 backdrop-blur-sm rounded-2xl p-6 border border-white/20 shadow-xl hover:shadow-2xl transition-all duration-300 hover:scale-105">
            <div className="flex items-center justify-between mb-4">
              <div className="w-12 h-12 bg-gradient-to-br from-[#6e56cf] to-[#5b4bb2] rounded-xl flex items-center justify-center shadow-lg">
                <span className="text-white text-xl">⚙️</span>
              </div>
              <div className="text-3xl font-bold text-purple-600 group-hover:text-purple-700 transition-colors">
                {pipelineEvents.length}
              </div>
            </div>
            <div className="text-sm font-medium text-purple-700">
              Pipeline Updates
            </div>
            <div className="text-xs text-purple-600/70 mt-1">
              Processing status
            </div>
          </div>

          <div className="group bg-white/70 backdrop-blur-sm rounded-2xl p-6 border border-white/20 shadow-xl hover:shadow-2xl transition-all duration-300 hover:scale-105">
            <div className="flex items-center justify-between mb-4">
              <div className="w-12 h-12 bg-gradient-to-br from-[#6e56cf] to-[#5b4bb2] rounded-xl flex items-center justify-center shadow-lg">
                <span className="text-white text-xl">🎨</span>
              </div>
              <div className="text-3xl font-bold text-purple-600 group-hover:text-purple-700 transition-colors">
                {assetEvents.length}
              </div>
            </div>
            <div className="text-sm font-medium text-purple-700">
              Assets Created
            </div>
            <div className="text-xs text-purple-600/70 mt-1">
              Generated content
            </div>
          </div>

          <div className="group bg-white/70 backdrop-blur-sm rounded-2xl p-6 border border-white/20 shadow-xl hover:shadow-2xl transition-all duration-300 hover:scale-105">
            <div className="flex items-center justify-between mb-4">
              <div className="w-12 h-12 bg-gradient-to-br from-red-500 to-red-600 rounded-xl flex items-center justify-center shadow-lg">
                <span className="text-white text-xl">📋</span>
              </div>
              <div className="text-3xl font-bold text-red-600 group-hover:text-red-700 transition-colors">
                {briefEvents.length}
              </div>
            </div>
            <div className="text-sm font-medium text-red-700">Briefs Ingested</div>
            <div className="text-xs text-red-600/70 mt-1">Campaign starts</div>
          </div>

          <div className="group bg-white/70 backdrop-blur-sm rounded-2xl p-6 border border-white/20 shadow-xl hover:shadow-2xl transition-all duration-300 hover:scale-105">
            <div className="flex items-center justify-between mb-4">
              <div className="w-12 h-12 bg-gradient-to-br from-emerald-500 to-emerald-600 rounded-xl flex items-center justify-center shadow-lg">
                <span className="text-white text-xl">✅</span>
              </div>
              <div className="text-3xl font-bold text-emerald-600 group-hover:text-emerald-700 transition-colors">
                {complianceEvents.length}
              </div>
            </div>
            <div className="text-sm font-medium text-emerald-700">Compliance Checks</div>
            <div className="text-xs text-emerald-600/70 mt-1">Reports processed</div>
          </div>

          <div className="group bg-white/70 backdrop-blur-sm rounded-2xl p-6 border border-white/20 shadow-xl hover:shadow-2xl transition-all duration-300 hover:scale-105">
            <div className="flex items-center justify-between mb-4">
              <div className="w-12 h-12 bg-gradient-to-br from-amber-500 to-amber-600 rounded-xl flex items-center justify-center shadow-lg">
                <span className="text-white text-xl">⚠️</span>
              </div>
              <div className="text-3xl font-bold text-amber-600 group-hover:text-amber-700 transition-colors">
                {alertEvents.length}
              </div>
            </div>
            <div className="text-sm font-medium text-amber-700">Alerts</div>
            <div className="text-xs text-amber-600/70 mt-1">
              System notifications
            </div>
          </div>

          <div className="group bg-white/70 backdrop-blur-sm rounded-2xl p-6 border border-white/20 shadow-xl hover:shadow-2xl transition-all duration-300 hover:scale-105">
            <div className="flex items-center justify-between mb-4">
              <div className="w-12 h-12 bg-gradient-to-br from-red-500 to-red-600 rounded-xl flex items-center justify-center shadow-lg">
                <span className="text-white text-xl">📝</span>
              </div>
              <div className="text-3xl font-bold text-red-600 group-hover:text-red-700 transition-colors">
                {approvalsReqEvents.length}
              </div>
            </div>
            <div className="text-sm font-medium text-red-700">Approvals Requested</div>
            <div className="text-xs text-red-600/70 mt-1">Awaiting decisions</div>
          </div>

          <div className="group bg-white/70 backdrop-blur-sm rounded-2xl p-6 border border-white/20 shadow-xl hover:shadow-2xl transition-all duration-300 hover:scale-105">
            <div className="flex items-center justify-between mb-4">
              <div className="w-12 h-12 bg-gradient-to-br from-emerald-500 to-emerald-600 rounded-xl flex items-center justify-center shadow-lg">
                <span className="text-white text-xl">✅</span>
              </div>
              <div className="text-3xl font-bold text-emerald-600 group-hover:text-emerald-700 transition-colors">
                {approvalsDecEvents.length}
              </div>
            </div>
            <div className="text-sm font-medium text-emerald-700">Approvals Decisions</div>
            <div className="text-xs text-emerald-600/70 mt-1">Approved / Rejected</div>
          </div>

          <div className="group bg-white/70 backdrop-blur-sm rounded-2xl p-6 border border-white/20 shadow-xl hover:shadow-2xl transition-all duration-300 hover:scale-105">
            <div className="flex items-center justify-between mb-1">
              <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-blue-600 rounded-xl flex items-center justify-center shadow-lg">
                <span className="text-white text-xl">📈</span>
              </div>
              <div className="text-3xl font-bold text-blue-600 group-hover:text-blue-700 transition-colors">
                {avgCTR.toFixed(1)}%
              </div>
            </div>
            <div className="text-sm font-medium text-blue-700">Average CTR</div>
            <div className="text-xs text-blue-600/70 mt-1">Across performance events</div>
          </div>

          <div className="group bg-white/70 backdrop-blur-sm rounded-2xl p-6 border border-white/20 shadow-xl hover:shadow-2xl transition-all duration-300 hover:scale-105">
            <div className="flex items-center justify-between mb-1">
              <div className="w-12 h-12 bg-gradient-to-br from-amber-500 to-amber-600 rounded-xl flex items-center justify-center shadow-lg">
                <span className="text-white text-xl">💰</span>
              </div>
              <div className="text-3xl font-bold text-amber-600 group-hover:text-amber-700 transition-colors">
                ${avgCPA.toFixed(2)}
              </div>
            </div>
            <div className="text-sm font-medium text-amber-700">Average CPA</div>
            <div className="text-xs text-amber-600/70 mt-1">Across performance events</div>
          </div>
        </div>

        {/* Topic Filters */}
        <div className="bg-white/70 backdrop-blur-sm rounded-2xl p-4 border border-white/20 shadow-sm">
          <div className="flex flex-wrap items-center gap-3">
            {([
              { key: "all", label: "All" },
              { key: "briefs.ingest.v1", label: "Briefs" },
              { key: "pipeline.status.v1", label: "Pipeline" },
              { key: "assets.created.v1", label: "Assets" },
              { key: "compliance.v1", label: "Compliance" },
              { key: "alerts.v1", label: "Alerts" },
              { key: "approvals.request.v1", label: "Approvals Req" },
              { key: "approvals.decision.v1", label: "Approvals Dec" },
              { key: "performance.metrics.v1", label: "Performance" },
              { key: "ready_for_publish.v1", label: "Ready to Publish" },
              { key: "other", label: "Other" },
            ] as const).map(({ key, label }) => (
              <button
                key={key}
                onClick={() => toggleFilter(key)}
                className={`px-3 py-1.5 rounded-full text-sm font-medium border ${
                  topicFilters[key]
                    ? "bg-red-50/60 text-red-700 border-red-200"
                    : "bg-white/60 text-gray-600 border-gray-200"
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        {/* Events Section */}
          <div className="bg-white/70 backdrop-blur-sm rounded-2xl shadow-xl border border-white/20 overflow-hidden">
          <div className="p-8 border-b border-white/20 bg-gradient-to-r from-gray-50/50 to-red-50/50">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-2xl font-bold text-gray-900">
                  Live Events
                </h2>
                <p className="text-gray-600 mt-2">
                  Real-time events from your pipeline, updated as they happen
                </p>
              </div>
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 bg-emerald-500 rounded-full animate-pulse"></div>
                <span className="text-sm text-emerald-600 font-medium">
                  Live
                </span>
              </div>
            </div>
          </div>

          <div className="p-8">
            {visibleEvents.length === 0 ? (
              <div className="text-center py-16">
                <div className="w-24 h-24 bg-gradient-to-br from-gray-100 to-gray-200 rounded-full flex items-center justify-center mx-auto mb-6">
                  <span className="text-4xl">📊</span>
                </div>
                <h3 className="text-2xl font-bold text-gray-900 mb-4">
                  Waiting for Events
                </h3>
                <p className="text-gray-600 max-w-2xl mx-auto text-lg leading-relaxed mb-8">
                  Your dashboard is ready to display real-time pipeline
                  activity. Start your services and submit a brief to see the
                  magic happen.
                </p>

                <div className="bg-gradient-to-r from-red-50 to-purple-50 rounded-2xl p-6 border border-red-200/50 max-w-4xl mx-auto">
                  <h4 className="text-lg font-semibold text-gray-900 mb-4 text-center">
                    🚀 Quick Start Guide
                  </h4>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <div className="text-center">
                      <div className="w-12 h-12 bg-red-100 rounded-xl flex items-center justify-center mx-auto mb-3">
                        <span className="text-xl">🔧</span>
                      </div>
                      <h5 className="font-semibold text-gray-900 mb-2">
                        Start Services
                      </h5>
                      <p className="text-sm text-gray-600">
                        Run{" "}
                        <code className="bg-red-100 px-2 py-1 rounded text-red-800">
                          make run-services
                        </code>{" "}
                        to start Kafka
                      </p>
                    </div>
                    <div className="text-center">
                      <div className="w-12 h-12 bg-purple-100 rounded-xl flex items-center justify-center mx-auto mb-3">
                        <span className="text-xl">⚡</span>
                      </div>
                      <h5 className="font-semibold text-gray-900 mb-2">
                        Launch Workers
                      </h5>
                      <p className="text-sm text-gray-600">
                        Start pipeline and agent workers in separate terminals
                      </p>
                    </div>
                    <div className="text-center">
                      <div className="w-12 h-12 bg-rose-100 rounded-xl flex items-center justify-center mx-auto mb-3">
                        <span className="text-xl">📤</span>
                      </div>
                      <h5 className="font-semibold text-gray-900 mb-2">
                        Submit Brief
                      </h5>
                      <p className="text-sm text-gray-600">
                        Go to upload page and submit your campaign brief
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="space-y-6">
                {visibleEvents.map((e, idx) => (
                  <EventCard key={(e.event_id ?? idx) + "-" + idx} event={e} />
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Quick Actions */}
        <div className="bg-gradient-to-r from-[#fa0f00] to-[#6e56cf] rounded-2xl p-8 text-white shadow-2xl">
          <div className="text-center space-y-4">
            <h3 className="text-2xl font-bold">Ready to Create?</h3>
            <p className="text-white/80 max-w-2xl mx-auto">
              Submit your first campaign brief and watch the AI transform your
              ideas into stunning visual assets.
            </p>
            <div className="flex justify-center space-x-4">
              <a
                href="/upload"
                className="px-6 py-3 bg-white text-[#fa0f00] font-semibold rounded-xl hover:bg-gray-50 transition-all duration-200 shadow-lg hover:shadow-xl"
              >
                Upload Brief
              </a>
              <a
                href="/"
                className="px-6 py-3 border-2 border-white/30 text-white font-semibold rounded-xl hover:bg-white/10 transition-all duration-200"
              >
                Learn More
              </a>
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
