import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",

  // /dashboard has no overview of its own; it lands on the content library. Done at the
  // routing layer rather than with redirect() inside app/dashboard/page.tsx, which
  // rendered a server component that threw NEXT_REDIRECT before producing any children.
  // React's dev-only RSC timing then measures that component with end = -Infinity —
  // start is clamped to 0, end is not — and performance.measure() throws
  // "cannot have a negative time stamp" over the whole dev overlay.
  async redirects() {
    return [
      { source: "/dashboard", destination: "/dashboard/content", permanent: false },
    ];
  },
  turbopack: {
    root: __dirname,
  },
  experimental: {
    // Wraps route navigations in document.startViewTransition(); the animation
    // itself lives in globals.css under ::view-transition-*.
    viewTransition: true,
  },
  images: {
    unoptimized: true,
    remotePatterns: [
      { protocol: "http", hostname: "localhost" },
      { protocol: "http", hostname: "127.0.0.1" },
      { protocol: "https", hostname: "**" },
    ],
  },
};

export default nextConfig;
