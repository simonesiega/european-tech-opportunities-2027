import path from "node:path";
import type {NextConfig} from "next";

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
          key: "Strict-Transport-Security",
          value: "max-age=63072000; includeSubDomains; preload",
        },
      ]
    : []),
];

const nextConfig: NextConfig = {
  allowedDevOrigins: ["127.0.0.1", "localhost"],
  output: "standalone",
  turbopack: {
    root: path.resolve(__dirname),
  },
  async headers() {
    return [{source: "/:path*", headers: securityHeaders}];
  },
};

export default nextConfig;
