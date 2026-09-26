import path from "node:path";
import type {NextConfig} from "next";

const isProduction = process.env.NODE_ENV === "production";

export const contentSecurityPolicy = [
  "default-src 'self'",
  "base-uri 'self'",
  "connect-src 'self' https://gateway.umami.is",
  "font-src 'self'",
  "form-action 'self'",
  "frame-ancestors 'none'",
  "img-src 'self' data: blob:",
  "object-src 'none'",
  "script-src 'self' 'unsafe-inline' https://cloud.umami.is",
  "style-src 'self' 'unsafe-inline'",
].join("; ");

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
          value: contentSecurityPolicy,
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
    root: path.resolve(__dirname),
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
