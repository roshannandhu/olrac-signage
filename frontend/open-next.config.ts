// Cloudflare adapter for Next.js. Replaces @cloudflare/next-on-pages, which caps out at
// Next 15.5.2 and cannot build this app at all -- OpenNext is what Cloudflare maintains now.
//
// Defaults are deliberate: this dashboard is a client-rendered SPA that talks to the
// FastAPI backend over the network, so it needs no incremental cache, no tag revalidation
// and no queue. Add them here only if server-side data fetching is ever introduced.
import { defineCloudflareConfig } from "@opennextjs/cloudflare";

export default defineCloudflareConfig();
