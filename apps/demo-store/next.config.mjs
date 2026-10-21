/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "export",
  trailingSlash: true,
  images: { unoptimized: true },
  transpilePackages: ["@magaza/contracts"],
  env: { NEXT_PUBLIC_BRAND: process.env.BRAND ?? "yapi-market" },
  // Lint and type checks run in `make check`; the build only compiles.
  eslint: { ignoreDuringBuilds: true },
};

export default nextConfig;
