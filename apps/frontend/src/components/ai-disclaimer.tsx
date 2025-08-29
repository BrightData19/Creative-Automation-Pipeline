"use client";

import { useEffect, useState } from "react";

export default function AiDisclaimer() {
  const [hidden, setHidden] = useState<boolean>(false);

  useEffect(() => {
    try {
      const v = localStorage.getItem("aiDisclaimerHidden");
      if (v === "1") setHidden(true);
    } catch {}
  }, []);

  if (hidden) return null;

  return (
    <div className="fixed inset-x-0 bottom-0 z-50">
      <div className="mx-auto max-w-7xl px-4 pb-3 pt-3">
        <div className="flex items-start md:items-center justify-between gap-4 rounded-xl shadow-xl border border-white/30 bg-gradient-to-r from-[#fa0f00] to-[#6e56cf] text-white p-4 backdrop-blur-md">
          <p className="text-xs md:text-sm leading-relaxed">
            This tool uses AI to generate and enhance creative assets. Outputs may contain inaccuracies or
            require review. Always validate brand/legal compliance before publishing.
          </p>
          <div className="flex items-center gap-2 shrink-0">
            <a
              href="/docs"
              className="hidden md:inline-flex text-xs font-semibold bg-white/15 hover:bg-white/25 px-3 py-1.5 rounded-lg"
            >
              Learn more
            </a>
            <button
              onClick={() => {
                try { localStorage.setItem("aiDisclaimerHidden", "1"); } catch {}
                setHidden(true);
              }}
              className="text-xs font-semibold bg-white text-[#fa0f00] hover:brightness-105 px-3 py-1.5 rounded-lg"
            >
              Got it
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

