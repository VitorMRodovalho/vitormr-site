# vitormr-site — Agent Context

Loaded automatically by Claude/Cursor/Cline/Aider (2025-2026 convention). **Read this before making changes.**

This file holds the **operating principles** for any AI agent working in this repo. For project state, stack, commands, and the "where to look first" map, read [`CLAUDE.md`](./CLAUDE.md) — that's the dense source of truth.

## Two-layer doc structure

- **Root `AGENTS.md` (this file):** harness engineering principles, operating rules, guardrails.
- **Root `CLAUDE.md`:** project state, stack, sibling-site coordination, PII boundary, file structure.
- **`reports/personal-sites/*.md`** (in the parent `rodovalho-finance` private repo): requirements briefs.

If anything here conflicts with `CLAUDE.md`, follow `CLAUDE.md` — it's closer to the code.

## What this is

Personal/professional site for **Vitor M. Rodovalho, PMP®** — Senior Cost Manager at Linesight + Founder of AI & PM Research Hub (Núcleo IA & GP) at PMI Brazil + open-source builder. Strategic frame per ADR-023 §D4.2 in `rodovalho-finance` parent repo: independently-citable surface that amplifies discoverability of his work + supports EB-2 NIW evidence narrative. Live at https://vitormr.dev/ behind Cloudflare.

**Stack:** Astro 6.3 + Tailwind v4 + MDX + TypeScript 6 + Biome 2.4 + Cloudflare Workers Static Assets (`wrangler.toml` `[assets]` + `worker.js`). pnpm package manager (locked). No backend, no database, no analytics — static-only.

**Sibling sites:** stack symmetry with `sarah-rodovalho-site` (Sarah's site). This is one of 5 properties under the `vitormr.dev` umbrella — see `CLAUDE.md` for the full topology (orenu / panorama / meridianiq / nucleoia subdomains). Architectural conventions are coordinated across all of them.

## Harness engineering principles (adopted 2026-05-19)

Anchored on Anthropic's three engineering posts:
- [Building Effective Agents](https://www.anthropic.com/research/building-effective-agents) (2024)
- [Effective Context Engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) (Nov 2025)
- [Effective Harnesses for Long-Running Agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) (Mar 2026)

**1. Workflow first, agent second.** Most edits in this repo are deterministic (copy edit, MDX update, watermark variant addition, content collection wiring). Reserve agentic flow for narrative arc decisions, voice/tone calibration, design-token tradeoffs — frame as "recommendation + tradeoffs", not "A or B?".

**2. Context is finite.** Long content-class plans (publications / engagements / awards / community-service rollouts) live in the parent repo's `reports/personal-sites/*.md`. Index, then read the section being touched. For MDX edits, read frontmatter first then the prose block — not the whole file.

**3. Persist outside the model.** State lives in: git commits, MDX content collections under `src/content/`, scripts in `scripts/sync_*.py`, and ADRs in the parent repo. Old session detail → handoff docs in `rodovalho-finance` memory dir.

**4. Validate, don't trust.** Every completion claim must be proven:
```bash
pnpm exec astro check    # typecheck — 0 errors, 0 warnings, 0 hints
pnpm exec biome check    # lint + format
pnpm build               # builds N pages — verify count if added/removed
pnpm pii:scan            # PII regex scan (also in pre-commit + CI)
```
CI runs the same gates. All green to merge.

**5. Defense-in-depth markers ≠ enforcement.** *Critical operational lesson, 2026-05-19 (sibling-site incident).* `noIndex` meta + sitemap exclusion + `robots.txt Disallow` are crawler guidelines, not enforcement. If any route on this site claims to be "gated", verify with `curl -I <url>` from an anonymous shell. Expected for a CF Access gate: HTTP 302 → `cdn-cgi/access/login`. Anything else = not gated. PR descriptions and code comments are not evidence; curl is.

**6. Workers Static Assets bypass the Worker by default.** When `main = worker.js` co-exists with `[assets] directory = dist/`, matched asset paths skip the Worker handler unless `run_worker_first = true` is set in `wrangler.toml`. The `www → apex` 301 redirect (PR #31 / fix `39594b8`) requires this flag. *This is load-bearing — never remove without replacing the Worker logic at the edge level (DNS-level redirect rule on the zone).* Test post-deploy with anonymous curl on both `www.` and apex.

**7. Plan for context reset.** Session-end ritual:
1. Update or close any open PR / branch.
2. Update parent repo's `project_open_actions.md` if cross-repo state changed.
3. ADR-worthy changes get an ADR in `rodovalho-finance/decisions/`, not here.

**8. The ACI is the design.** Aesthetic discipline:
- Cool-blue palette in `src/styles/global.css` (distinct from Sarah's warm-stone)
- Newsreader serif display + Inter body (bundled via `@fontsource`, never Google Fonts CDN — see `/privacy/`)
- Watermark layer (`WatermarkLayer.astro`) with per-page variants — currently 7 live (home · DAX · Orenu · MeridianIQ · Panorama · methodologies · case-studies)
- Schema.org Person JSON-LD on every page (BaseLayout)
- HTML-native interactions (theme toggle = vanilla details/summary)

**9. Guardrails in layers:**
- **PII boundary** (per CLAUDE.md, enforced via `scripts/pii-scan.sh` pre-commit + CI): blocks USCIS receipts, SSN/CPF, personal email leaks, phone, salary, immigration case status. Allowed: name, headshot, PMP cert number (already on CV), Leesburg VA city, professional email `vitor@vitormr.dev`.
- **OPSEC discipline:** commit messages must not reference "EB1/EB2 evidence" or petition framing (memory `feedback_opsec_commit_language_eb1.md` from 2026-05-12 — public GitHub commit history is indexed). Use neutral framing: "OneDrive personal archive", "professional record", etc.
- **Sibling-site cross-link discipline:** vitormr.dev cross-links freely to Vitor's own properties (orenu, panorama, meridianiq, nucleoia). It does NOT cross-link to Sarah's site at the navigation level — the two sites are paired-but-separate. Footer credit to Sarah is OK if Sarah authorizes.
- **Audit:** material decisions become ADRs in the parent repo.

## Conventions (enforced)

1. **Commit trailer:** `Assisted-By: Claude (Anthropic) <noreply@anthropic.com>` on every commit. **NEVER `Co-Authored-By: Claude…`** — same convention as `rodovalho-finance` (ADR-010) and `sarah-rodovalho-site`.
2. **Decision framing:** "recommendation + why + tradeoffs", not "A or B?". User makes the call after seeing the framing.
3. **Content discipline:** every claim must be independently verifiable (employer LinkedIn, GitHub repos, PMP cert number, public PMI roles, public talks). No marketing puffery.
4. **Language:** English primary. Vitor's primary audience is US recruiters / immigration counsel / PMI international.

## Validation gates (mandatory before merge to `main`)

```bash
pnpm exec astro check
pnpm exec biome check
pnpm build
pnpm pii:scan
```

After merge, Cloudflare Workers Builds auto-deploys `main` → `https://vitormr.dev/`. The "Workers Builds" GitHub check is sticky and may stay in_progress — verify production with `curl -I` instead.

## When to consult external sources

- `CLAUDE.md` — stack details, PII regex, sibling-site topology
- ADR-023 + ADR-024 / ADR-024.1 in `rodovalho-finance/decisions/` — strategic frame + content-class auto-sync pattern
- `reports/personal-sites/2026-05-09-vitormr-site-requirements.md` (parent repo) — content brief
- Astro 6 docs (`https://docs.astro.build`) when touching Content Layer, Image Service, or new integration
- Cloudflare Workers Static Assets docs when touching `wrangler.toml` `[assets]` or `worker.js`
- `feedback_cloudflare_workers_run_worker_first.md` memory note for the SEO fix lesson
- **Do not search "how to fix [error]" before checking git log + CLAUDE.md first.**

---

*Initial adoption: 2026-05-19. Complements `CLAUDE.md` (project state) and the parent repo's `rodovalho-finance/AGENTS.md`.*
