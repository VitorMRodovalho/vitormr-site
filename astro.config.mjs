// @ts-check
import mdx from "@astrojs/mdx";
import sitemap from "@astrojs/sitemap";
import tailwindcss from "@tailwindcss/vite";
import { defineConfig } from "astro/config";

// Astro 6.3 config — pure-static site for vitormr.dev served via Cloudflare
// Workers Static Assets (see wrangler.toml).
//
// NO @astrojs/cloudflare adapter: with output: "static", the adapter would
// emit a server bundle that conflicts with `npx wrangler deploy` static-only
// mode. Pattern validated on sarahrodovalho.com — same stack, same approach.

export default defineConfig({
  // Astro v7 mudou o padrao de compressHTML de true para 'jsx', o que colapsa
  // whitespace entre elementos inline. Fixado em true para preservar a
  // renderizacao da v6 — trocar a regra e decisao separada.
  compressHTML: true,
  site: "https://vitormr.dev",
  output: "static",
  integrations: [
    mdx(),
    sitemap({
      // Exclude /admin/* from sitemap. CF Access at the edge is the real
      // gate; this just prevents accidental advertisement to crawlers.
      filter: (page) => !page.includes("/admin"),
    }),
  ],
  vite: {
    plugins: [tailwindcss()],
  },
});
