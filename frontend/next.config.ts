import type { NextConfig } from "next";
import { resolve } from "node:path";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  webpack(config) {
    // SnarkJS publishes a dedicated browser bundle. Point every build graph at
    // it so Webpack does not traverse the library's Node-only worker shim.
    config.resolve.alias = {
      ...config.resolve.alias,
      snarkjs: resolve(process.cwd(), "node_modules/snarkjs/build/browser.esm.js"),
      ffjavascript: resolve(
        process.cwd(),
        "node_modules/ffjavascript/build/browser.esm.js",
      ),
    };
    return config;
  },
  async headers() {
    return [
      {
        source: "/zk/:artifact*",
        headers: [
          {
            key: "Cache-Control",
            // Fixed artifact names must revalidate periodically so a ceremony
            // rotation cannot strand browsers on a stale proving key.
            value: "public, max-age=3600, stale-while-revalidate=86400",
          },
          { key: "X-Content-Type-Options", value: "nosniff" },
        ],
      },
      {
        source: "/:path*",
        headers: [
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "DENY" },
          {
            key: "Permissions-Policy",
            value: "camera=(), microphone=(), geolocation=(), payment=()",
          },
        ],
      },
    ];
  },
};

export default nextConfig;
