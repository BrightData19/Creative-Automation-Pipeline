"use client";

import React, { useCallback, useMemo, useState } from "react";
import { useDropzone } from "react-dropzone";

export default function UploadPage() {
  const [jsonText, setJsonText] = useState<string>(
    "// Paste your brief JSON here or drop a .json file above\n\n"
  );
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<{
    ok: boolean;
    event_id?: string;
    error?: string;
  } | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [assets, setAssets] = useState<File[]>([]);
  const [logoFile, setLogoFile] = useState<string>("");
  const [productMap, setProductMap] = useState<Record<string, string>>({});
  const [forceGenerate, setForceGenerate] = useState(
    (process.env.NEXT_PUBLIC_FORCE_GENERATE_NEW_DEFAULT || "false").toLowerCase() ===
      "true"
  );

  // ===== Dropzones =====
  const onBriefDrop = useCallback((acceptedFiles: File[]) => {
    const file = acceptedFiles[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      const content = String(reader.result);
      setJsonText(content);
      // Validate JSON immediately
      try {
        JSON.parse(content);
        setValidationError(null);
      } catch (err) {
        setValidationError("Invalid JSON format");
      }
    };
    reader.readAsText(file);
  }, []);

  const jsonDZ = useDropzone({
    onDrop: onBriefDrop,
    accept: { "application/json": [".json"] },
    maxFiles: 1,
  });

  const assetsDZ = useDropzone({
    onDrop: (files) => {
      if (!files?.length) return;
      setAssets((prev) => {
        // Deduplicate by name+size for a smoother UX
        const existing = new Set(prev.map((f) => f.name + "|" + f.size));
        const next = [...prev];
        for (const f of files) {
          const key = f.name + "|" + f.size;
          if (!existing.has(key)) next.push(f);
        }
        return next;
      });
    },
    accept: {
      "image/*": [],
      "application/pdf": [".pdf"],
      "video/*": [],
    },
    maxFiles: 50,
  });

  // ===== Utils & derived state =====
  const validateJSON = (text: string): boolean => {
    try {
      JSON.parse(text);
      setValidationError(null);
      return true;
    } catch (err) {
      setValidationError("Invalid JSON format");
      return false;
    }
  };

  const products = useMemo<string[]>(() => {
    try {
      const obj = JSON.parse(jsonText);
      if (obj && Array.isArray(obj.products)) {
        return obj.products.map((p: any) => String(p.name || "")).filter(Boolean);
      }
    } catch {}
    return [];
  }, [jsonText]);

  const totalAssetSizeMB = useMemo(() => {
    const bytes = assets.reduce((sum, f) => sum + f.size, 0);
    return (bytes / (1024 * 1024)).toFixed(2);
  }, [assets]);

  function removeAsset(fileName: string) {
    setAssets((prev) => prev.filter((f) => f.name !== fileName));
    setProductMap((prev) => {
      const next = { ...prev };
      Object.keys(next).forEach((k) => {
        if (next[k] === fileName) delete next[k];
      });
      return next;
    });
    setLogoFile((prev) => (prev === fileName ? "" : prev));
  }

  function clearAssets() {
    setAssets([]);
    setLogoFile("");
    setProductMap({});
  }

  function clearForm() {
    setJsonText("// Paste your brief JSON here or drop a .json file above\n\n");
    setValidationError(null);
    clearAssets();
    setResult(null);
    setForceGenerate(
      (process.env.NEXT_PUBLIC_FORCE_GENERATE_NEW_DEFAULT || "false").toLowerCase() ===
        "true"
    );
  }

  // ===== Submit =====
  async function submitBrief() {
    if (!validateJSON(jsonText)) {
      return;
    }

    setSubmitting(true);
    setResult(null);
    try {
      let res: Response;
      if (assets.length > 0) {
        const fd = new FormData();
        fd.append("brief", jsonText);
        assets.forEach((f) => fd.append("assets", f));
        const mapping = {
          logoFile: logoFile || undefined,
          productMap,
          force_generate_new: forceGenerate,
        };
        fd.append("mapping", JSON.stringify(mapping));
        res = await fetch("/api/briefs", { method: "POST", body: fd });
      } else {
        const body = JSON.parse(jsonText);
        body.force_generate_new = forceGenerate;
        res = await fetch("/api/briefs", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });
      }
      const data = await res.json();
      setResult(data);

      if (data.ok) {
        // Clear the form on success
        setJsonText("// Brief submitted successfully!\n\n");
        setAssets([]);
        setLogoFile("");
        setProductMap({});
      }
    } catch (err: unknown) {
      setResult({
        ok: false,
        error: err instanceof Error ? err.message : "Network error occurred",
      });
    } finally {
      setSubmitting(false);
    }
  }

  function loadExample() {
    const example = {
      campaign_name: "Autumn Promo",
      target_market: "US Northeast",
      target_audience: "Young professionals in urban areas",
      campaign_message: "Cozy styles for cooler days",
      products: [
        { name: "Wool Sweater", image: null },
        { name: "Corduroy Jacket", image: null },
        { name: "Chelsea Boots", image: null },
      ],
      logo_path: null,
      inbox_folder: "dropbox:/assets/seasonal/autumn",
    };
    const exampleText = JSON.stringify(example, null, 2);
    setJsonText(exampleText);
    setValidationError(null);
  }

  const handleTextChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const newText = e.target.value;
    setJsonText(newText);
    // Clear validation error when user starts typing
    if (validationError) {
      setValidationError(null);
    }
  };

  return (
    <main className="min-h-screen bg-gradient-to-br from-gray-50 via-red-50/30 to-purple-50/30 py-8">
      <div className="mx-auto max-w-6xl px-6 space-y-8">
        {/* Hero Header */}
        <div className="text-center space-y-4">
          <h1 className="text-5xl font-bold bg-gradient-to-r from-gray-900 via-red-800 to-purple-800 bg-clip-text text-transparent">
            Campaign Brief Upload
          </h1>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto leading-relaxed">
            Transform your campaign ideas into stunning visual assets with our
            AI-powered creative automation pipeline
          </p>
        </div>

        {/* Main Upload Section */}
        <div className="bg-white/70 backdrop-blur-sm rounded-2xl shadow-xl border border-white/20 overflow-hidden">
          <div className="p-8 border-b border-white/20 bg-gradient-to-r from-gray-50/50 to-red-50/50">
            <h2 className="text-2xl font-bold text-gray-900 mb-2">
              Upload Your Brief
            </h2>
            <p className="text-gray-600">
              Drop a JSON file or paste your campaign brief to get started
            </p>
          </div>

          {/* Content */}
          <div className="p-8 space-y-8">
            {/* Brief Dropzone */}
            <div
              {...jsonDZ.getRootProps()}
              className={`relative border-2 border-dashed rounded-2xl p-12 text-center cursor-pointer transition-all duration-300 hover:shadow-xl focus:outline-none focus:ring-4 focus:ring-red-500/20 ${
                jsonDZ.isDragActive
                  ? "bg-gradient-to-r from-red-50 to-purple-50 border-red-400 shadow-xl scale-105"
                  : "bg-gradient-to-r from-gray-50 to-red-50/30 border-gray-300 hover:border-red-400 hover:scale-[1.02]"
              }`}
              aria-label="Upload campaign brief JSON"
            >
              <input {...jsonDZ.getInputProps()} />
              <div className="space-y-4">
                <div className="text-6xl">📄</div>
                {jsonDZ.isDragActive ? (
                  <div className="space-y-2">
                    <p className="text-xl font-bold text-red-600">
                      Drop your brief here!
                    </p>
                    <p className="text-red-500">Release to upload</p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    <p className="text-xl font-bold text-gray-700">
                      Drag &amp; drop your <code>brief.json</code> here
                    </p>
                    <p className="text-gray-500 text-lg">or click to browse files</p>
                    <div className="flex justify-center gap-3 text-sm text-gray-500">
                      <span className="px-2 py-0.5 rounded-full bg-gray-100">JSON</span>
                      <span className="px-2 py-0.5 rounded-full bg-gray-100">Max 1 file</span>
                    </div>
                  </div>
                )}
              </div>
              <div className="absolute top-3 right-3 text-xs text-gray-500">
                Tip: Provide products to enable asset mapping below
              </div>
            </div>

            {/* Actions */}
            <div className="flex flex-wrap justify-center gap-3">
              <button
                onClick={loadExample}
                className="group px-5 py-3 rounded-xl border-2 border-gray-300 text-gray-700 bg-white hover:bg-gray-50 hover:border-gray-400 transition-all duration-300 font-semibold shadow-lg hover:shadow-xl active:scale-95"
              >
                <span className="inline-flex items-center gap-2">
                  <span className="text-lg">📋</span>
                  <span>Load Example</span>
                </span>
              </button>
              <button
                onClick={clearForm}
                className="group px-5 py-3 rounded-xl border-2 border-gray-300 text-gray-700 bg-white hover:bg-gray-50 hover:border-gray-400 transition-all duration-300 font-semibold shadow-lg hover:shadow-xl active:scale-95"
              >
                <span className="inline-flex items-center gap-2">
                  <span className="text-lg">🧼</span>
                  <span>Reset Form</span>
                </span>
              </button>
              <button
                onClick={submitBrief}
                disabled={submitting || !!validationError}
                className="group px-8 py-3 rounded-xl bg-gradient-to-r from-[#fa0f00] to-[#6e56cf] text-white font-semibold hover:brightness-110 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-300 shadow-xl hover:shadow-2xl active:scale-[0.98] disabled:active:scale-100"
              >
                {submitting ? (
                  <span className="inline-flex items-center gap-3">
                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                    <span>Processing...</span>
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-2">
                    <span className="text-lg">🚀</span>
                    <span>Submit Brief</span>
                  </span>
                )}
              </button>
            </div>

            {/* Assets Uploader - modern */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-semibold text-gray-900">Attach Assets (optional)</h3>
                  <p className="text-sm text-gray-600">Logos, product images, PDFs, or video clips</p>
                </div>
                {assets.length > 0 && (
                  <div className="text-xs text-gray-600 bg-gray-100 px-2 py-1 rounded-lg">
                    {assets.length} file{assets.length > 1 ? "s" : ""} • {totalAssetSizeMB} MB
                  </div>
                )}
              </div>

              <div
                {...assetsDZ.getRootProps()}
                className={`border-2 border-dashed rounded-2xl p-8 text-center transition-all duration-300 cursor-pointer hover:shadow-md focus:outline-none focus:ring-4 focus:ring-purple-500/20 ${
                  assetsDZ.isDragActive
                    ? "bg-gradient-to-r from-purple-50 to-red-50 border-purple-400"
                    : "bg-white/70 border-gray-300 hover:border-purple-400"
                }`}
                aria-label="Attach creative assets"
              >
                <input {...assetsDZ.getInputProps()} />
                <div className="flex flex-col items-center gap-2">
                  <div className="text-4xl">📦</div>
                  <div className="font-medium text-gray-800">
                    Drag &amp; drop assets, or <span className="underline">browse</span>
                  </div>
                  <div className="text-xs text-gray-500">
                    Accepted: images, PDF, video • Up to 50 files
                  </div>
                </div>
              </div>

              {assets.length > 0 && (
                <>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-600">Preview &amp; manage</span>
                    <button
                      type="button"
                      onClick={clearAssets}
                      className="text-sm text-red-600 hover:text-red-700 underline"
                    >
                      Clear all
                    </button>
                  </div>

                  <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
                    {assets.map((f) => {
                      const isImg = f.type.startsWith("image/");
                      const isVideo = f.type.startsWith("video/");
                      const url = URL.createObjectURL(f);
                      return (
                        <div key={f.name} className="relative border rounded-xl p-2 bg-white/60 shadow-sm">
                          <button
                            type="button"
                            onClick={() => removeAsset(f.name)}
                            className="absolute -top-2 -right-2 h-6 w-6 rounded-full bg-white shadow ring-1 ring-gray-200 text-gray-700 hover:bg-gray-50"
                            aria-label={`Remove ${f.name}`}
                            title="Remove"
                          >
                            ×
                          </button>
                          <div className="w-full h-28 bg-gray-100 rounded-lg overflow-hidden flex items-center justify-center mb-2">
                            {isImg ? (
                              <img
                                src={url}
                                alt={f.name}
                                className="w-full h-full object-cover"
                                onLoad={(e) => URL.revokeObjectURL((e.target as HTMLImageElement).src)}
                              />
                            ) : isVideo ? (
                              <video
                                src={url}
                                className="w-full h-full object-cover"
                                muted
                                playsInline
                                onLoadedData={(e) => URL.revokeObjectURL((e.target as HTMLVideoElement).src!)}
                              />
                            ) : (
                              <div className="text-gray-500 text-xs px-2">PDF / File</div>
                            )}
                          </div>
                          <div className="truncate text-xs font-medium text-gray-800">{f.name}</div>
                          <div className="text-[10px] text-gray-500">{Math.round(f.size / 1024)} KB</div>
                        </div>
                      );
                    })}
                  </div>

                  {/* Mapping Controls */}
                  <div className="mt-6 space-y-4">
                    <h4 className="text-base font-semibold text-gray-900">Map Assets</h4>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Logo file</label>
                        <select
                          className="w-full border rounded-lg p-2 bg-white"
                          value={logoFile}
                          onChange={(e) => setLogoFile(e.target.value)}
                        >
                          <option value="" className="text-black">(none)</option>
                          {assets.map((f) => (
                            <option key={f.name} value={f.name} className="text-black">
                              {f.name}
                            </option>
                          ))}
                        </select>
                      </div>
                      {products.map((pname) => (
                        <div key={pname}>
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            Product image for: {pname}
                          </label>
                          <select
                            className="w-full border rounded-lg p-2 bg-white"
                            value={productMap[pname] || ""}
                            onChange={(e) =>
                              setProductMap({ ...productMap, [pname]: e.target.value })
                            }
                          >
                            <option value="">(none)</option>
                            {assets.map((f) => (
                              <option key={f.name} value={f.name}>
                                {f.name}
                              </option>
                            ))}
                          </select>
                        </div>
                      ))}
                    </div>
                    <div className="flex items-center gap-3 mt-1">
                      <input
                        id="forceNew"
                        type="checkbox"
                        className="w-4 h-4 accent-purple-600"
                        checked={forceGenerate}
                        onChange={(e) => setForceGenerate(e.target.checked)}
                      />
                      <label htmlFor="forceNew" className="text-sm text-gray-700">
                        Force generate new images even if assets are present
                      </label>
                    </div>
                  </div>
                </>
              )}
            </div>

            {/* JSON Editor */}
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <label className="text-xl font-semibold text-gray-800">
                  Campaign Brief JSON
                </label>
                <div className="flex items-center gap-3">
                  <div className="text-sm text-gray-600 bg-gray-100 px-3 py-1 rounded-lg">
                    {jsonText.length} characters
                  </div>
                  <div aria-live="polite" className="sr-only">
                    {validationError ? "Invalid JSON" : "Valid JSON"}
                  </div>
                  {validationError && (
                    <div className="text-red-700 text-sm font-medium flex items-center gap-2 bg-red-50 px-3 py-1 rounded-lg border border-red-200">
                      <span>⚠️</span>
                      <span>Invalid JSON</span>
                    </div>
                  )}
                </div>
              </div>
              <div className="relative">
                <textarea
                  className={`w-full h-96 border-2 text-black rounded-xl p-6 font-mono text-sm transition-all duration-300 focus:outline-none focus:ring-4 focus:ring-blue-500/20 resize-none ${
                    validationError
                      ? "border-red-300 focus:ring-red-500/20"
                      : "border-gray-300 focus:border-blue-500"
                  }`}
                  value={jsonText}
                  onChange={handleTextChange}
                  placeholder="Paste your campaign brief JSON here..."
                  spellCheck={false}
                />
                <div className="absolute top-4 right-4 text-xs text-gray-400 bg-white/80 px-2 py-1 rounded">
                  JSON
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Result Display */}
        {result && (
          <div
            className={`bg-white/70 backdrop-blur-sm rounded-2xl border-2 p-8 shadow-xl ${
              result.ok
                ? "border-emerald-300 bg-emerald-50/50"
                : "border-red-300 bg-red-50/50"
            }`}
          >
            <div className="flex items-center gap-4">
              <div
                className={`w-16 h-16 rounded-full flex items-center justify-center ${
                  result.ok ? "bg-emerald-100" : "bg-red-100"
                }`}
              >
                <span
                  className={`text-3xl ${
                    result.ok ? "text-emerald-600" : "text-red-600"
                  }`}
                >
                  {result.ok ? "✅" : "❌"}
                </span>
              </div>
              <div className="flex-1">
                <h3
                  className={`font-bold text-2xl mb-2 ${
                    result.ok ? "text-emerald-800" : "text-red-800"
                  }`}
                >
                  {result.ok
                    ? "Brief Submitted Successfully!"
                    : "Submission Failed"}
                </h3>
                <p
                  className={`text-lg ${
                    result.ok ? "text-emerald-700" : "text-red-700"
                  }`}
                >
                  {result.ok ? (
                    <>
                      Event ID:{" "}
                      <code className="bg-emerald-200 px-3 py-1 rounded-lg font-mono text-emerald-800">
                        {result.event_id}
                      </code>
                    </>
                  ) : (
                    result.error
                  )}
                </p>
                {result.ok && (
                  <p className="text-emerald-600 mt-2">
                    🎉 Your campaign is now being processed by the AI pipeline!
                  </p>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Help Section - modernized */}
        <div className="rounded-2xl p-8 border bg-white/70 shadow-sm">
          <h3 className="text-2xl font-bold text-gray-900 mb-6 text-center">
            💡 How to Use This Form
          </h3>
          <ol className="grid grid-cols-1 md:grid-cols-4 gap-6">
            {[
              { n: "1", title: "Upload or Paste", desc: "Drag & drop a JSON file or paste your brief directly into the editor." },
              { n: "2", title: "Load Example", desc: "Click “Load Example” to see a sample structure to start from." },
              { n: "3", title: "Attach Assets", desc: "Add logos, product photos, PDFs/videos, and map them to products." },
              { n: "4", title: "Submit & Track", desc: "Submit the brief and monitor progress from your dashboard." },
            ].map((s) => (
              <li key={s.n} className="relative bg-gradient-to-b from-gray-50 to-white rounded-xl border p-5">
                <div className="absolute -top-3 left-5 w-8 h-8 bg-rose-100 rounded-lg flex items-center justify-center">
                  <span className="text-rose-600 text-sm">{s.n}</span>
                </div>
                <h4 className="font-semibold text-gray-900 mt-2">{s.title}</h4>
                <p className="text-gray-600 text-sm mt-1">{s.desc}</p>
              </li>
            ))}
          </ol>
          <div className="mt-6">
            <details className="group bg-gray-50 border rounded-xl p-4">
              <summary className="cursor-pointer font-medium text-gray-800 flex items-center justify-between">
                Required fields in JSON
                <span className="text-sm text-gray-500 group-open:hidden">show</span>
                <span className="text-sm text-gray-500 hidden group-open:inline">hide</span>
              </summary>
              <pre className="mt-3 text-sm text-gray-800 bg-white rounded-lg p-4 overflow-x-auto">
{`{
  "campaign_name": "...",
  "target_market": "...",
  "target_audience": "...",
  "campaign_message": "...",
  "products": [{"name": "..." }],
  "inbox_folder": "dropbox:/...",
  "logo_path": null
}`}
              </pre>
            </details>
          </div>
        </div>

        {/* Quick Actions - refined */}
        <div className="rounded-2xl p-8 text-center bg-gradient-to-r from-[#ffefe9] to-[#eee8ff] border">
          <h3 className="text-2xl font-bold mb-3 text-gray-900">
            Ready to Monitor Progress?
          </h3>
          <p className="text-gray-700 max-w-2xl mx-auto mb-6">
            After submitting your brief, head to the dashboard to watch the AI
            transform your ideas into visual assets in real-time.
          </p>
          <div className="flex flex-wrap justify-center gap-3">
            <a
              href="/dashboard"
              className="inline-flex items-center gap-2 px-6 py-3 bg-[#fa0f00] text-white font-semibold rounded-xl hover:brightness-110 transition-all duration-200 shadow-lg hover:shadow-xl active:scale-95"
            >
              <span>📊</span>
              <span>Go to Dashboard</span>
            </a>
            <button
              onClick={clearForm}
              className="inline-flex items-center gap-2 px-6 py-3 bg-white text-gray-800 font-semibold rounded-xl border hover:bg-gray-50 transition-all duration-200 shadow-lg hover:shadow-xl active:scale-95"
            >
              <span>🔄</span>
              <span>Start Over</span>
            </button>
          </div>
        </div>
      </div>
    </main>
  );
}