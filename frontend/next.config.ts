import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // No `output` setting on purpose. "standalone" produced a Node server (see the old
  // frontend/Dockerfile), which Cloudflare cannot run; the OpenNext adapter builds its
  // own Worker bundle from the default output and needs this left alone. Static export
  // is not an option either -- five routes use [id] segments with no generateStaticParams,
  // and redirects() below is unsupported by it.

  // Next normalises away a trailing slash with a 308 before rewrites run. FastAPI
  // registers its collection routes WITH the slash and answers the slashless form with a
  // 307 back to it -- built as an absolute URL from the address it was reached on. Proxied,
  // the two bounce off each other and the FastAPI leg hands the browser the internal
  // 127.0.0.1 address, which no client can reach: the dashboard showed "Your library is
  // empty" because every collection fetch died on that redirect.
  //
  // Skipping the normalisation lets /api/content/ reach FastAPI exactly as written, which
  // matches its route and returns 200 with no redirect from either side.
  skipTrailingSlashRedirect: true,

  // Development only: serve the API from this same origin.
  //
  // api.ts rewrites a localhost API host to window.location.hostname, so a dev server
  // reached through a public tunnel resolves its API to that same public host. Proxying
  // /api here is what makes that resolution land somewhere real -- and being same-origin,
  // it sidesteps CORS entirely rather than needing a tunnel host added to an allow-list
  // that changes every time the tunnel restarts.
  //
  // Guarded on NODE_ENV because the deployed build must keep calling the real API host;
  // rewriting /api to localhost there would point every visitor at their own machine.
  async rewrites() {
    if (process.env.NODE_ENV !== "development") return [];
    const target = process.env.DEV_API_PROXY_TARGET || "http://127.0.0.1:8000";
    // Two rules, slash-first. FastAPI registers its collection endpoints WITH a trailing
    // slash (GET /api/screens/), and the :path* capture silently drops the empty final
    // segment -- so a single slashless rule rewrote /api/screens/ to /api/screens, which
    // FastAPI answered with a 307 back to the slashed form built from its own internal
    // address. Matching the slashed form explicitly keeps the request intact.
    return [
      { source: "/api/:path*/", destination: `${target}/api/:path*/` },
      { source: "/api/:path*", destination: `${target}/api/:path*` },
    ];
  },

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
  // The dev server treats requests from an origin other than localhost as cross-origin and
  // refuses to serve its internal dev endpoints to them. Reached through a tunnel the page
  // still server-renders -- which is why it looked fine -- but the client bundle never
  // attaches, so nothing is interactive: no handler runs, dropdowns do not open, and the
  // login form falls back to a native GET that puts the credentials in the URL.
  // Listed hosts are dev-only tunnels; this has no effect on a production build.
  allowedDevOrigins: [
    "*.trycloudflare.com",
    "measured-cruz-aerial-purposes.trycloudflare.com",
  ],

  turbopack: {
    root: __dirname,
  },
  experimental: {
    // viewTransition disabled: it wraps route navigations in document.startViewTransition(),
    // and with it on the client bundle never attached to the server-rendered markup --
    // React's internal props key was absent from every node, so no handler ran. The login
    // form then fell back to a native GET submit, which is how credentials ended up in the
    // URL query string and why the page appeared to "redirect back to login".
    // viewTransition: true,
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
