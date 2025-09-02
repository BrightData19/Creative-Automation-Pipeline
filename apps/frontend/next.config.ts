import type { NextConfig } from "next";
import { loadEnvConfig } from "@next/env";
import path from "path";

// In a monorepo, also load env files from the repo root so
// vars in ".env" at the root are available to the frontend.
const monorepoRoot = path.resolve(__dirname, "..", "..");
loadEnvConfig(monorepoRoot, process.env.NODE_ENV !== "production");

const nextConfig: NextConfig = {
  /* config options here */
};

export default nextConfig;
