"use client";

import React, { useEffect, useRef, useState } from "react";
import Link from "next/link";

type ChatMessage = {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  imageUrl?: string;
};

export const UI: React.FC = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [image, setImage] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const onSend = async () => {
    if (!input && !image) return;
    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: input,
      imageUrl: image ? URL.createObjectURL(image) : undefined,
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setImage(null);
    setLoading(true);

    const form = new FormData();
    form.append("message", userMsg.content);
    if (image) form.append("image", image);

    const res = await fetch("/api/chat", { method: "POST", body: form });

    if (!res.ok || !res.body) {
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: "Error from server",
        },
      ]);
      setLoading(false);
      return;
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let assistantText = "";
    // naive text streaming
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      assistantText += decoder.decode(value, { stream: true });
      setMessages((prev) => {
        const last = prev[prev.length - 1];
        if (last && last.role === "assistant") {
          return [...prev.slice(0, -1), { ...last, content: assistantText }];
        }
        return [
          ...prev,
          {
            id: crypto.randomUUID(),
            role: "assistant",
            content: assistantText,
          },
        ];
      });
    }
    setLoading(false);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 via-red-50/30 to-purple-50/30">
      <div className="max-w-7xl mx-auto p-6 space-y-12">
        {/* Hero Section */}
        <div className="text-center space-y-8 py-16">
          <div className="relative">
            <div className="w-28 h-28 rounded-full flex items-center justify-center mx-auto mb-8 shadow-subtle bg-white/70 border border-white/20">
              <span className="text-6xl">🚀</span>
            </div>
            <div className="absolute -top-2 -right-2 w-8 h-8 rounded-full flex items-center justify-center bg-gradient-to-r from-[#fa0f00] to-[#6e56cf]">
              <span className="text-white text-sm">✨</span>
            </div>
          </div>

          <h1 className="text-5xl md:text-6xl font-bold leading-tight">
            Creative Automation Pipeline
          </h1>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto leading-relaxed">
            Transform your marketing campaigns with AI-powered creative
            generation. Upload a brief and watch as we create multiple variants
            automatically.
          </p>

          {/* Quick Action Buttons */}
          <div className="flex justify-center space-x-6 pt-8">
            <Link href="/upload" className="btn-primary">
              <span className="flex items-center space-x-3">
                <span className="text-2xl">📋</span>
                <span>Upload Brief</span>
              </span>
            </Link>
            <Link href="/dashboard" className="btn-secondary">
              <span className="flex items-center space-x-3">
                <span className="text-2xl">📊</span>
                <span>View Dashboard</span>
              </span>
            </Link>
          </div>
        </div>

        {/* Features Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 py-12">
          <div className="group bg-white/70 backdrop-blur-sm rounded-2xl p-8 shadow-xl border border-white/20">
            <div className="w-12 h-12 bg-primary/15 text-primary rounded-xl flex items-center justify-center mb-5">
              <span className="text-3xl">🎨</span>
            </div>
            <h3 className="text-xl font-semibold mb-3">
              AI-Powered Generation
            </h3>
            <p className="text-gray-700 leading-relaxed">
              Automatically generate creative assets in multiple aspect ratios
              using advanced AI models with intelligent fallback systems.
            </p>
          </div>

          <div className="group bg-white/70 backdrop-blur-sm rounded-2xl p-8 shadow-xl border border-white/20">
            <div className="w-12 h-12 bg-purple-100 text-purple-600 rounded-xl flex items-center justify-center mb-5">
              <span className="text-3xl">⚡</span>
            </div>
            <h3 className="text-xl font-semibold mb-3">Real-time Processing</h3>
            <p className="text-gray-700 leading-relaxed">
              Monitor your pipeline in real-time with live updates, status
              tracking, and comprehensive event monitoring.
            </p>
          </div>

          <div className="group bg-white/70 backdrop-blur-sm rounded-2xl p-8 shadow-xl border border-white/20">
            <div className="w-12 h-12 bg-red-100 text-red-600 rounded-xl flex items-center justify-center mb-5">
              <span className="text-3xl">🔍</span>
            </div>
            <h3 className="text-xl font-semibold mb-3">Quality Assurance</h3>
            <p className="text-gray-700 leading-relaxed">
              AI agents monitor output quality and diversity, ensuring your
              creatives meet brand compliance and quality standards.
            </p>
          </div>
        </div>

        {/* Enhanced Features Section */}
        <div className="bg-white/70 backdrop-blur-sm rounded-2xl p-10 text-gray-900 shadow-xl border border-white/20">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-semibold mb-2">
              Advanced Capabilities
            </h2>
            <p className="text-gray-600 max-w-3xl mx-auto">
              Our pipeline goes beyond basic generation with enterprise-grade
              features
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <div className="text-center">
              <div className="w-10 h-10 bg-red-100 text-red-600 rounded-xl flex items-center justify-center mx-auto mb-3">
                <span className="text-2xl">🌍</span>
              </div>
              <h4 className="font-medium mb-1">Global Localization</h4>
              <p className="text-gray-600 text-sm">
                Multi-language support with cultural adaptation
              </p>
            </div>
            <div className="text-center">
              <div className="w-10 h-10 bg-red-100 text-red-600 rounded-xl flex items-center justify-center mx-auto mb-3">
                <span className="text-2xl">🛡️</span>
              </div>
              <h4 className="font-medium mb-1">Brand Compliance</h4>
              <p className="text-gray-600 text-sm">
                Automated logo detection and brand guidelines
              </p>
            </div>
            <div className="text-center">
              <div className="w-10 h-10 bg-red-100 text-red-600 rounded-xl flex items-center justify-center mx-auto mb-3">
                <span className="text-2xl">⚖️</span>
              </div>
              <h4 className="font-medium mb-1">Legal Filtering</h4>
              <p className="text-gray-600 text-sm">
                Content safety and prohibited word detection
              </p>
            </div>
            <div className="text-center">
              <div className="w-10 h-10 bg-purple-100 text-purple-600 rounded-xl flex items-center justify-center mx-auto mb-3">
                <span className="text-2xl">📈</span>
              </div>
              <h4 className="font-medium mb-1">Performance Analytics</h4>
              <p className="text-gray-600 text-sm">
                Real-time metrics and quality scoring
              </p>
            </div>
          </div>
        </div>

        {/* Getting Started Section */}
        <div className="bg-white/70 backdrop-blur-sm rounded-2xl p-10 shadow-xl border border-white/20">
          <h3 className="text-2xl font-semibold text-center mb-8">
            🚀 Getting Started
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            <div className="space-y-6">
              <h4 className="text-lg font-semibold mb-2">
                1. Start the Pipeline
              </h4>
              <div className="space-y-3 text-gray-700">
                <div className="flex items-center space-x-3">
                  <div className="w-6 h-6 bg-primary/15 text-primary rounded-full flex items-center justify-center">
                    <span className="text-xs">1</span>
                  </div>
                  <p>
                    Run{" "}
                    <code className="bg-white/70 px-2 py-1 rounded text-gray-900 font-mono border border-white/20">
                      make run-services
                    </code>{" "}
                    to start Kafka
                  </p>
                </div>
                <div className="flex items-center space-x-3">
                  <div className="w-6 h-6 bg-red-100 text-red-600 rounded-full flex items-center justify-center">
                    <span className="text-xs">2</span>
                  </div>
                  <p>
                    Start pipeline worker:{" "}
                    <code className="bg-white/70 px-2 py-1 rounded text-gray-900 font-mono border border-white/20">
                      uv run python main.py
                    </code>
                  </p>
                </div>
                <div className="flex items-center space-x-3">
                  <div className="w-6 h-6 bg-red-100 text-red-600 rounded-full flex items-center justify-center">
                    <span className="text-xs">3</span>
                  </div>
                  <p>
                    Start agent worker:{" "}
                    <code className="bg-card px-2 py-1 rounded text-foreground font-mono ring-1 ring-border/60">
                      uv run python agent_graph.py
                    </code>
                  </p>
                </div>
              </div>
            </div>
            <div className="space-y-6">
              <h4 className="text-lg font-semibold mb-2">
                2. Upload & Monitor
              </h4>
              <div className="space-y-3 text-gray-700">
                <div className="flex items-center space-x-3">
                  <div className="w-6 h-6 bg-purple-100 text-purple-600 rounded-full flex items-center justify-center">
                    <span className="text-xs">1</span>
                  </div>
                  <p>
                    Go to{" "}
                    <Link
                      href="/upload"
                      className="text-red-600 hover:underline font-medium"
                    >
                      Upload Page
                    </Link>{" "}
                    to submit a brief
                  </p>
                </div>
                <div className="flex items-center space-x-3">
                  <div className="w-6 h-6 bg-purple-100 text-purple-600 rounded-full flex items-center justify-center">
                    <span className="text-xs">2</span>
                  </div>
                  <p>
                    Monitor progress on the{" "}
                    <Link
                      href="/dashboard"
                      className="text-red-600 hover:underline font-medium"
                    >
                      Dashboard
                    </Link>
                  </p>
                </div>
                <div className="flex items-center space-x-3">
                  <div className="w-6 h-6 bg-accent/15 text-accent rounded-full flex items-center justify-center">
                    <span className="text-xs">3</span>
                  </div>
                  <p>Watch real-time events and generated assets</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Call to Action */}
        <div className="text-center py-12">
          <h3 className="text-2xl font-semibold mb-4">
            Ready to Transform Your Creative Process?
          </h3>
          <p className="text-gray-600 mb-8 max-w-2xl mx-auto">
            Join the future of creative automation and see your campaigns come
            to life with AI-powered generation.
          </p>
          <Link
            href="/upload"
            className="inline-flex items-center space-x-3 btn-primary"
          >
            <span>🚀</span>
            <span>Get Started Now</span>
          </Link>
        </div>
      </div>
    </div>
  );
};
