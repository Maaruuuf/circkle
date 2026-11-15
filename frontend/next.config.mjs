/** @type {import('next').NextConfig} */
const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8001";
const isDev = process.env.NODE_ENV !== "production";

// 'unsafe-inline' for scripts is required by Next.js hydration unless you add nonces.
// 'unsafe-eval' is only needed by the dev server (React refresh).
const contentSecurityPolicy = [
  "default-src 'self'",
  `script-src 'self' 'unsafe-inline'${isDev ? " 'unsafe-eval'" : ""}`,
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data: blob: https:",
  "font-src 'self' data:",
  "connect-src 'self'",
  "frame-ancestors 'none'",
  "base-uri 'self'",
  "form-action 'self'",
].join("; ");

const nextConfig = {
  output: "standalone",
  poweredByHeader: false,
  reactStrictMode: true,
  // The browser only ever talks to the Next.js origin. These rewrites forward
  // API calls to FastAPI, so cookies are same-site and no CORS is needed.
  async rewrites() {
    return [
      { source: "/api/:path*", destination: `${BACKEND_URL}/api/:path*` },
      { source: "/media/:path*", destination: `${BACKEND_URL}/media/:path*` },
    ];
  },
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
          ...(isDev ? [] : [{ key: "Content-Security-Policy", value: contentSecurityPolicy }]),
        ],
      },
    ];
  },
};

export default nextConfig;
