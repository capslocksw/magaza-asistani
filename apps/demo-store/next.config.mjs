/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "export",
  trailingSlash: true,
  images: { unoptimized: true },
  transpilePackages: ["@magaza/contracts"],
  env: {
    NEXT_PUBLIC_BRAND: process.env.BRAND ?? "yapi-market",
    // AGENT_URL (see .env.example): empty -> the scripted mock-agent on :8787.
    NEXT_PUBLIC_AGENT_URL: process.env.NEXT_PUBLIC_AGENT_URL ?? process.env.AGENT_URL ?? "",
  },
  // Lint and type checks run in `make check`; the build only compiles.
  eslint: { ignoreDuringBuilds: true },
};

export default nextConfig;
