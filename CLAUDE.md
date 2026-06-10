# Project: vitormr-site

**Mission**: Personal/professional site for Vitor M. Rodovalho, PMP® — Senior Cost Manager at Linesight + Founder of AI & PM Research Hub (Núcleo IA & GP) at PMI Brazil + open-source builder. Strategic frame: independently-citable surface that amplifies discoverability of his work + supports EB-2 NIW evidence narrative. Per ADR-023 §D4.2 in `rodovalho-finance` parent repo (private).

## Stack

- Astro 6.3 + Tailwind v4 + MDX + TypeScript 6.0 + Biome 2.4
- Cloudflare Workers Static Assets via `wrangler.toml` `[assets]` mode
- pnpm package manager (locked)
- Stack symmetry with `sarah-rodovalho-site` (paired sites under `vitormr.dev` umbrella)

## Conventions

- **Commit trailer**: `Assisted-By: Claude (Anthropic) <noreply@anthropic.com>` on every assisted commit. **NEVER** `Co-Authored-By: Claude…`. Same as Orenu / `rodovalho-finance` / `sarah-rodovalho-site`.
- **Author of record**: Vitor Maia Rodovalho.
- **Content discipline**: every claim must be independently verifiable (employer LinkedIn pages, GitHub repos, PMP certification number, public PMI roles, public talks). No marketing puffery, no recommendation framing.
- **PII boundary** (enforced via pre-commit hook):
  - **Allowed**: name, headshot, role, employers, public projects, GitHub repos, LinkedIn URL, PMP cert number (already on CV), Leesburg VA city, professional email `vitor@vitormr.dev` (Email Routing target)
  - **Blocked**: USCIS receipt numbers (`[A-Z]{3}\d{10}`), SSN/CPF, personal outlook/gmail, phone, salary, immigration case status, family member details
- **Language**: English primary. PT secondary deferred (Vitor's primary audience is U.S. recruiters / immigration counsel / PMI international).

## Sibling site coordination

This site is one of 5 properties under `vitormr.dev` umbrella:
- `vitormr.dev` (apex) — this repo (personal hub)
- `orenu.vitormr.dev` — family fintech (rodovalho-finance/app, Cloudflare Worker, Access-gated)
- `panorama.vitormr.dev` — open-source IT/fleet management (`panorama` repo)
- `meridianiq.vitormr.dev` — open-source schedule intelligence (`meridianiq` repo)
- `nucleoia.vitormr.dev` — AI & PM Research Hub (`ai-pm-research-hub` repo, private newer iteration `ai-pm-hub-v2`)

`sarahrodovalho.com` is paired-but-separate: independent site with cross-reference attribution to vitormr.dev as developer.

## File structure

- `src/pages/` — Astro routes (`index.astro`, `about.astro`, `experience.astro`, `projects/`, etc.)
- `src/layouts/BaseLayout.astro` — site-wide HTML wrapper with Schema.org Person markup
- `src/content/` — MDX content collections (schemas in `src/content.config.ts`)
- `src/styles/global.css` — Tailwind v4 config + design tokens (cool-blue palette, distinct from Sarah's warm-stone)
- `public/` — static assets (favicon, headshot, downloads)
- `astro.config.mjs` — Astro config (NO @astrojs/cloudflare adapter; pure-static)
- `wrangler.toml` — Workers Static Assets `[assets]` config
- `biome.json` — lint + format config
- `scripts/pii-scan.sh` — pre-commit + CI PII regex scanner
- `tests/pii-scan.test.sh` — smoke test for the scanner

## Sources of truth (read for content drops)

- LinkedIn: https://www.linkedin.com/in/vitor-rodovalho-pmp/
- GitHub: https://github.com/VitorMRodovalho
- Requirements brief: `reports/personal-sites/2026-05-09-vitormr-site-requirements.md` (in rodovalho-finance private repo)
- Career narrative: 5-phase arc 2007-present (see brief §2)
- Current role: Senior Cost Manager · Linesight · Sterling, VA · April 2026 – present

## CI gates (GitHub Actions)

- `pnpm install --frozen-lockfile`
- `pnpm typecheck` (astro check)
- `pnpm check:ci` (biome)
- `pnpm build` (astro build)
- `pnpm audit --audit-level high`
- `pnpm pii:test` + full-repo `bash scripts/pii-scan.sh --all`

## Out of scope (deferred PRs)

- V03+ content drops — see brief §10 sequence
- Vitor's professional headshot (image asset gated em Vitor)
- Per-project deep architecture pages (case-study one-pagers v1; deepen v2 if value justifies)
- AI playground / live demos (Astro Islands cover; defer until specific demo concrete)
- Sarah's site cross-ref attribution (separate PR-S08 in `sarah-rodovalho-site` repo, post-vitormr-launch)

## Portfolio PMO (knowledge loop)

- This repo lives under Vitor's portfolio PMO at `~/projects` (the parent
  `CLAUDE.md` there governs PMO mode; machine-global skills at
  `~/.claude/skills/`, SSOT = `AI-PMO-Framework/skills/`).
- It carries a standing `[LL]` lessons-learned-intake issue; log reusable
  lessons there so the PMO can harvest them (`pmo-sync.sh harvest`).
