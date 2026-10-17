import path from "node:path";
import type {NextConfig} from "next";
import {contentSecurityPolicy} from "./src/lib/content-security-policy";

const isProduction = process.env.NODE_ENV === "production";

const securityHeaders = [
  {key: "X-Content-Type-Options", value: "nosniff"},
  {key: "Referrer-Policy", value: "strict-origin-when-cross-origin"},
  {key: "X-Frame-Options", value: "DENY"},
  {key: "Cross-Origin-Opener-Policy", value: "same-origin"},
  {key: "Cross-Origin-Resource-Policy", value: "same-origin"},
  {key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()"},
  ...(isProduction
    ? [
        {
          key: "Content-Security-Policy",
          value: contentSecurityPolicy(),
        },
        {
          key: "Strict-Transport-Security",
          value: "max-age=63072000; includeSubDomains; preload",
        },
      ]
    : []),
];

const nextConfig: NextConfig = {
  allowedDevOrigins: ["127.0.0.1", "localhost"],
  distDir: process.env.NEXT_DIST_DIR ?? ".next",
  output: "standalone",
  turbopack: {
    // Dev imports shared geography; production keeps its website-rooted standalone layout.
    root: path.resolve(__dirname, isProduction ? "." : ".."),
  },
  async headers() {
    return [{source: "/:path*", headers: securityHeaders}];
  },
  async redirects() {
    return [
      {
        source: "/:path*",
        has: [{type: "host", value: "opportunities2027.simonesiega.com"}],
        destination: "https://techopportunities.eu/:path*",
        permanent: true,
      },
    ];
  },
};

export default nextConfig;
