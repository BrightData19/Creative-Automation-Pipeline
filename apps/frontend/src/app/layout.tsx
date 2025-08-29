import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";
import AiDisclaimer from "@/components/ai-disclaimer";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Creative Automation Pipeline",
  description: "AI-powered creative automation platform for global campaigns",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${geistSans.variable} ${geistMono.variable} antialiased bg-background text-foreground`}>
        <header className="sticky top-0 z-50 border-b border-border/60 bg-background/70 backdrop-blur-xl supports-[backdrop-filter]:bg-background/60">
          <nav className="mx-auto max-w-7xl flex items-center justify-between p-5">
            <div className="flex items-center space-x-8">
              <Link href="/" className="flex items-center space-x-3 group">
                <div className="w-9 h-9 rounded-xl flex items-center justify-center shadow-subtle ring-1 ring-border/60 bg-card group-hover:scale-105 transition-transform">
                  <span className="text-lg font-bold" style={{ color: "var(--color-primary)" }}>●</span>
                </div>
                <div>
                  <div className="text-lg font-semibold">
                    Creative Automation
                  </div>
                  <div className="text-xs text-muted font-medium">
                    Pipeline Dashboard
                  </div>
                </div>
              </Link>
            </div>

            <div className="flex items-center space-x-1">
              <Link
                href="/"
                className="px-3 py-2 text-sm font-medium text-foreground/80 hover:text-foreground hover:bg-card rounded-lg transition-colors"
              >
                Home
              </Link>
              <Link
                href="/upload"
                className="px-3 py-2 text-sm font-medium text-foreground/80 hover:text-foreground hover:bg-card rounded-lg transition-colors"
              >
                Upload Brief
              </Link>
              <Link
                href="/dashboard"
                className="px-4 py-2 text-sm font-semibold text-white rounded-lg shadow-subtle transition-colors"
                style={{ backgroundColor: "var(--color-primary)" }}
              >
                Dashboard
              </Link>
            </div>
          </nav>
        </header>
        {children}
        {/* AI Disclaimer banner visible across pages */}
        <AiDisclaimer />
      </body>
    </html>
  );
}
