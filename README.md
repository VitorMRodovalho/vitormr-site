# vitormr.dev

Personal site of Vitor M. Rodovalho, PMP® — Senior Cost Manager at Linesight, Founder of the AI & PM Research Hub (Núcleo IA & GP) under PMI Brazil.

## Stack

- **Astro 6.3** (zero-JS-by-default static-site generator)
- **Tailwind CSS v4** (CSS-first config)
- **MDX** for rich content authoring (project case studies, writing)
- **TypeScript 6.0** strict mode
- **Biome 2.4** for lint + format
- **Cloudflare Workers Static Assets** for deployment via `wrangler.toml`

## Local development

Requires Node 22+ and pnpm 10+.

```bash
pnpm install
pnpm dev          # local dev server on :4321
pnpm build        # produces ./dist
pnpm preview      # serves ./dist locally
pnpm typecheck    # astro check
pnpm check:ci     # biome check (no fixes)
pnpm pii:scan     # full-repo PII scan
pnpm pii:test     # smoke test for the PII scanner
```

## Sibling sites

- [orenu.vitormr.dev](https://orenu.vitormr.dev/) — family fintech (Access-gated)
- [panorama.vitormr.dev](https://panorama.vitormr.dev/) — open-source IT asset + fleet management
- [meridianiq.vitormr.dev](https://meridianiq.vitormr.dev/) — open-source schedule intelligence
- [nucleoia.vitormr.dev](https://nucleoia.vitormr.dev/) — AI & PM Research Hub (PMI Brazil)
- [sarahrodovalho.com](https://sarahrodovalho.com/) — Sarah F. Rodovalho's site (designed and developed by Vitor; cross-referenced from her About page footer)

## Maintenance

- Dependencies via pnpm + lockfile + Dependabot
- Content updates: edit MDX in `src/content/`
- Deploy: auto via Cloudflare Workers Static Assets on push to `main`

## License

Content (text, photos, project descriptions) © Vitor M. Rodovalho. All rights reserved.
Code (Astro components, build configuration) is incidental to the content; no separate license file. Reuse with attribution welcome via direct contact.
