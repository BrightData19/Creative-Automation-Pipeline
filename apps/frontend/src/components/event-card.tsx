"use client";

import React, { useState } from "react";

type Props = {
  event: Record<string, unknown>;
};

const getTopicColor = (topic: string) => {
  // Adobe brand feel: primary red for pipeline, purple for assets, amber for alerts
  if (topic.includes("pipeline.status"))
    return "from-[#fa0f00] to-[#c70d00] border-red-200";
  if (topic.includes("assets.created"))
    return "from-[#6e56cf] to-[#5b4bb2] border-purple-200";
  if (topic.includes("compliance"))
    return "from-emerald-500 to-emerald-600 border-emerald-200";
  if (topic.includes("alerts"))
    return "from-amber-500 to-amber-600 border-amber-200";
  if (topic.includes("briefs.ingest"))
    return "from-[#ff4a3f] to-[#fa0f00] border-red-200";
  return "from-gray-500 to-gray-600 border-gray-200";
};

const getTopicIcon = (topic: string) => {
  if (topic.includes("pipeline.status")) return "⚙️";
  if (topic.includes("assets.created")) return "🎨";
  if (topic.includes("ready_for_publish")) return "🚀";
  if (topic.includes("compliance")) return "✅";
  if (topic.includes("alerts")) return "⚠️";
  if (topic.includes("briefs.ingest")) return "📋";
  return "📄";
};

const formatTimestamp = (ts: unknown) => {
  if (ts && typeof ts === "string") {
    try {
      const date = new Date(ts);
      const now = new Date();
      const diffMs = now.getTime() - date.getTime();
      const diffMins = Math.floor(diffMs / 60000);
      const diffSecs = Math.floor((diffMs % 60000) / 1000);

      if (diffMins < 1) {
        return `${diffSecs}s ago`;
      } else if (diffMins < 60) {
        return `${diffMins}m ago`;
      } else {
        return date.toLocaleTimeString([], {
          hour: "2-digit",
          minute: "2-digit",
        });
      }
    } catch {
      return String(ts);
    }
  }
  return "Unknown time";
};

const getTopicName = (topic: string) => {
  if (topic.includes("pipeline.status")) return "Pipeline Status";
  if (topic.includes("assets.created")) return "Assets Created";
  if (topic.includes("ready_for_publish")) return "Ready for Publish";
  if (topic.includes("compliance")) return "Compliance";
  if (topic.includes("alerts")) return "Alert";
  if (topic.includes("briefs.ingest")) return "Brief Ingested";
  return topic;
};

const getStatusBadge = (stage: unknown) => {
  if (!stage) return null;

  const stageStr = String(stage).toLowerCase();

  if (stageStr.includes("complete") || stageStr.includes("success")) {
    return "bg-emerald-100 text-emerald-800 border-emerald-200";
  } else if (stageStr.includes("error") || stageStr.includes("failed")) {
    return "bg-red-100 text-red-800 border-red-200";
  } else if (
    stageStr.includes("processing") ||
    stageStr.includes("generating")
  ) {
    return "bg-purple-100 text-purple-800 border-purple-200";
  } else if (stageStr.includes("pending") || stageStr.includes("waiting")) {
    return "bg-amber-100 text-amber-800 border-amber-200";
  }

  return "bg-gray-100 text-gray-800 border-gray-200";
};

export function EventCard({ event }: Props) {
  const [isExpanded, setIsExpanded] = useState(false);

  const ts = formatTimestamp(event.ts);
  const topic =
    event.topic && typeof event.topic === "string" ? event.topic : "Unknown";
  const topicColor = getTopicColor(topic);
  const topicIcon = getTopicIcon(topic);
  const topicName = getTopicName(topic);

  return (
    <div className="group bg-white/80 backdrop-blur-sm rounded-2xl border border-gray-200/50 shadow-lg hover:shadow-xl transition-all duration-300 overflow-hidden">
      {/* Header */}
      <div className={`bg-gradient-to-r ${topicColor} p-6 text-white`}>
        <div className="flex items-start justify-between">
          <div className="flex items-center space-x-4">
            <div className="w-12 h-12 bg-white/20 rounded-xl flex items-center justify-center backdrop-blur-sm">
              <span className="text-2xl">{topicIcon}</span>
            </div>
            <div>
              <h3 className="text-xl font-bold">{topicName}</h3>
              <p className="text-white/80 font-mono text-sm">{topic}</p>
            </div>
          </div>
          <div className="text-right">
            <div className="bg-white/20 backdrop-blur-sm px-3 py-2 rounded-lg border border-white/30">
              <div className="text-sm font-semibold">{ts}</div>
            </div>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="p-6 space-y-4">
        {/* Campaign Info */}
        {event.campaign_name && (
          <div className="bg-gradient-to-r from-gray-50 to-red-50/30 rounded-xl p-4 border border-gray-200/50">
            <div className="flex items-center space-x-3 mb-2">
              <div className="w-8 h-8 bg-red-100 rounded-lg flex items-center justify-center">
                <span className="text-red-600 text-sm">📢</span>
              </div>
              <div className="text-sm font-semibold text-gray-700">
                Campaign
              </div>
            </div>
            <div className="text-lg font-bold text-gray-900 ml-11">
              {String(event.campaign_name)}
            </div>
          </div>
        )}

        {/* Product Info */}
        {event.product && (
          <div className="bg-gradient-to-r from-gray-50 to-purple-50/30 rounded-xl p-4 border border-gray-200/50">
            <div className="flex items-center space-x-3 mb-2">
              <div className="w-8 h-8 bg-purple-100 rounded-lg flex items-center justify-center">
                <span className="text-purple-600 text-sm">🏷️</span>
              </div>
              <div className="text-sm font-semibold text-gray-700">Product</div>
            </div>
            <div className="text-lg font-medium text-gray-900 ml-11">
              {String(event.product)}
            </div>
          </div>
        )}

        {/* Stage/Status Info */}
        {event.stage && (
          <div className="bg-gradient-to-r from-gray-50 to-red-50/30 rounded-xl p-4 border border-gray-200/50">
            <div className="flex items-center space-x-3 mb-3">
              <div className="w-8 h-8 bg-red-100 rounded-lg flex items-center justify-center">
                <span className="text-red-600 text-sm">📊</span>
              </div>
              <div className="text-sm font-semibold text-gray-700">Status</div>
            </div>
            <div className="ml-11 space-y-2">
              <div className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium border ${getStatusBadge(event.stage)}">
                {String(event.stage)}
              </div>
              {event.detail && (
                <div className="text-sm text-gray-600 bg-white/60 rounded-lg p-3 border border-gray-200/50">
                  {String(event.detail)}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Variants Info */}
        {event.variants && Array.isArray(event.variants) && (
          <div className="bg-gradient-to-r from-gray-50 to-rose-50/30 rounded-xl p-4 border border-gray-200/50">
            <div className="flex items-center space-x-3 mb-3">
              <div className="w-8 h-8 bg-rose-100 rounded-lg flex items-center justify-center">
                <span className="text-rose-600 text-sm">🖼️</span>
              </div>
              <div className="text-sm font-semibold text-gray-700">
                Variants ({event.variants.length})
              </div>
            </div>
            <div className="ml-11 space-y-2">
              {event.variants.map((variant: any, idx: number) => (
                <div
                  key={idx}
                  className="flex items-center justify-between bg-white/60 rounded-lg p-3 border border-gray-200/50"
                >
                  <div className="flex items-center space-x-2">
                    <span className="text-xs font-medium text-gray-500 bg-gray-100 px-2 py-1 rounded">
                      {variant.ratio}
                    </span>
                    <span className="text-sm text-gray-700 font-mono">
                      {variant.path}
                    </span>
                  </div>
                  <div className="w-3 h-3 bg-[#fa0f00] rounded-full"></div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Compliance Info */}
        {event.compliance_report && (
          <div className="bg-gradient-to-r from-gray-50 to-emerald-50/30 rounded-xl p-4 border border-gray-200/50">
            <div className="flex items-center space-x-3 mb-3">
              <div className="w-8 h-8 bg-emerald-100 rounded-lg flex items-center justify-center">
                <span className="text-emerald-600 text-sm">✅</span>
              </div>
              <div className="text-sm font-semibold text-gray-700">Compliance</div>
            </div>
            <div className="ml-11 space-y-2 text-sm text-gray-800">
              <div>
                Score: <span className="font-semibold">{String((event as any).compliance_report?.overall_score ?? "-")}</span>
              </div>
              {Array.isArray((event as any).compliance_report?.all_issues) && (
                <div>
                  Issues: <span className="font-semibold">{(event as any).compliance_report.all_issues.length}</span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Approvals Decision */}
        {topic.includes("approvals.decision") && (
          <div className="bg-gradient-to-r from-gray-50 to-blue-50/30 rounded-xl p-4 border border-gray-200/50">
            <div className="flex items-center space-x-3 mb-2">
              <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center">
                <span className="text-blue-600 text-sm">🗳️</span>
              </div>
              <div className="text-sm font-semibold text-gray-700">Approval Decision</div>
            </div>
            <div className="ml-11 text-sm text-gray-800 space-y-1">
              <div>Decision: <span className="font-semibold">{String((event as any).decision ?? "-")}</span></div>
              { (event as any).reviewer && <div>Reviewer: <span className="font-mono">{String((event as any).reviewer)}</span></div> }
            </div>
          </div>
        )}

        {/* Ready for Publish */}
        {topic.includes("ready_for_publish") && (
          <div className="bg-gradient-to-r from-gray-50 to-emerald-50/30 rounded-xl p-4 border border-gray-200/50">
            <div className="flex items-center space-x-3 mb-2">
              <div className="w-8 h-8 bg-emerald-100 rounded-lg flex items-center justify-center">
                <span className="text-emerald-600 text-sm">🚀</span>
              </div>
              <div className="text-sm font-semibold text-gray-700">Ready for Publish</div>
            </div>
            <div className="ml-11 text-sm text-gray-800 space-y-1">
              <div>Artifacts: {(event as any).artifacts?.length ?? 0}</div>
            </div>
          </div>
        )}

        {/* Error Info */}
        {event.error && (
          <div className="bg-gradient-to-r from-red-50 to-red-100/50 rounded-xl p-4 border border-red-200/50">
            <div className="flex items-center space-x-3 mb-2">
              <div className="w-8 h-8 bg-red-100 rounded-lg flex items-center justify-center">
                <span className="text-red-600 text-sm">❌</span>
              </div>
              <div className="text-sm font-semibold text-red-700">Error</div>
            </div>
            <div className="text-red-800 text-sm ml-11 bg-white/60 rounded-lg p-3 border border-red-200/50">
              {String(event.error)}
            </div>
          </div>
        )}

        {/* Expandable Raw Data */}
        <div className="border-t border-gray-200/50 pt-4">
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="w-full flex items-center justify-between p-3 bg-gray-50 hover:bg-gray-100 rounded-xl transition-colors duration-200 group"
          >
            <div className="flex items-center space-x-2">
              <span className="text-gray-600">📊</span>
              <span className="text-sm font-medium text-gray-700">
                View Raw Data
              </span>
            </div>
            <div
              className={`transform transition-transform duration-200 ${
                isExpanded ? "rotate-180" : ""
              }`}
            >
              <svg
                className="w-4 h-4 text-gray-500"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M19 9l-7 7-7-7"
                />
              </svg>
            </div>
          </button>

          {isExpanded && (
            <div className="mt-3 bg-gray-50 rounded-xl p-4 border border-gray-200/50">
              <pre className="text-xs text-gray-600 overflow-x-auto whitespace-pre-wrap bg-white rounded-lg p-3 border border-gray-200/50">
                {JSON.stringify(event, null, 2)}
              </pre>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
