# UTM attribution conventions — vitormr.dev

> **Audience:** Vitor (divulgation + EB-2 NIW evidence-narrative tracking),
> AI agents (consistency across sessions).
> **Why:** every link shared — LinkedIn post, PMI talk QR, email signature,
> GitHub README cross-link, sibling-subdomain footer — should be tagged so
> `/admin/metrics` (or the Cloudflare Web Analytics dashboard) shows clean
> per-channel attribution. Untagged links collapse into "direct" and
> become invisible. Mirrors `sarah-rodovalho-site` conventions where they
> overlap; diverges where Vitor's channels are different.
> **Last updated:** 2026-05-19.

---

## TL;DR — the 3 params Vitor uses

Every shared URL gets these three query parameters:

```
?utm_source=<channel>&utm_medium=<format>&utm_campaign=<context>
```

| Param | What it answers | Examples |
|---|---|---|
| `utm_source` | **Where did the click come from?** | `linkedin`, `pmi`, `qr`, `email`, `github`, `subdomain` |
| `utm_medium` | **What kind of placement?** | `post`, `bio`, `talk-slide`, `talk-handout`, `readme`, `signature`, `footer` |
| `utm_campaign` | **What event / push / context?** | `launch-2026-05`, `pmi-summit-2026-XX`, `niw-evidence`, `general` |

Two more params exist (`utm_term`, `utm_content`) — ignore unless A/B
testing two variants of the same link. Not needed in v1.

---

## Naming convention — opinionated picks

Lowercase, hyphens, no spaces. Vocabularies kept stable so attribution
doesn't fragment across spelling variants.

### `utm_source` — channel of origin

| Source | Use when |
|---|---|
| `linkedin` | Anything Vitor posts on LinkedIn (feed post, comment, article, profile bio link). |
| `pmi` | PMI Brazilian Chapter channels (Slack, WhatsApp groups, event pages, Núcleo IA & GP communications). |
| `qr` | Any printed or projected QR code (talk slides, business card, handouts, posters). |
| `email` | Personal email signature or one-off intro emails. |
| `github` | GitHub repo READMEs / wiki / About sections that link back to vitormr.dev (e.g., panorama, meridianiq, ai-pm-research-hub). |
| `subdomain` | Sibling subdomains under vitormr.dev umbrella linking back to apex (orenu, panorama, meridianiq, nucleoia footers). |
| `whatsapp` | WhatsApp shares (close network, professional groups). |
| `talks` | Recordings on YouTube / Vimeo / event pages where the talk lives. |
| `direct` | Auto-filled by CF for visits with no referrer / no UTM. **Never set manually.** |

### `utm_medium` — format / placement

| Medium | Use when |
|---|---|
| `post` | Social media post (LinkedIn feed, etc.). |
| `bio` | Profile bio link (LinkedIn "Featured" or summary). |
| `talk-slide` | QR code shown on a presentation slide. |
| `talk-handout` | QR on a printed or PDF handout at a talk. |
| `readme` | A repo's README footer / About section cross-link. |
| `signature` | Email signature. |
| `footer` | Sibling subdomain footer cross-link. |
| `dm` | Direct message (WhatsApp, LinkedIn InMail). |
| `chip` | Small in-product affordance (e.g., "Built by Vitor → vitormr.dev"). |

### `utm_campaign` — context / event

Format: `<event-or-context>-<YYYY-MM>` (kebab-case + year-month) where the
event has a fixed date. `general` for always-on placements.

| Campaign | Use when |
|---|---|
| `launch-2026-05` | Initial site divulgation push (if/when one happens). |
| `pmi-summit-2026-XX` | PMI conference talk QR (replace XX with month). |
| `niw-evidence` | Referrals embedded in EB-2 NIW evidence packet documents (lets you see whether reviewers actually clicked through). |
| `general` | Default for ongoing channels (LinkedIn bio link, email signature, GitHub README) where there's no specific event. |

**Rule of thumb:** if you can't predict the campaign 6 months from now,
use `general`. Don't invent campaign names mid-flight unless there's a
real event tied to it.

---

## QR code recipe — per-event template

For PMI talks, the closing slide gets a QR code with attribution baked
in. Two acceptable shapes:

### Option A — homepage with UTM (simplest)

```
https://vitormr.dev/?utm_source=qr&utm_medium=talk-slide&utm_campaign=pmi-summit-2026-08
```

### Option B — deep-link to a specific page (when the talk is about that subject)

```
https://vitormr.dev/projects/nucleo-ia-gp/?utm_source=qr&utm_medium=talk-slide&utm_campaign=pmi-summit-2026-08
```

Use Option B when the talk maps to a specific project / writing
already on the site. Audience benefits from landing directly on the
relevant page instead of the homepage.

### What `/admin/metrics` (or CF dashboard) will show after the talk

- **Top pages** row for `/?utm_source=qr&utm_medium=talk-slide&utm_campaign=pmi-summit-2026-08`
  → exact count of QR scans during/after the talk window.
- **Top referrers** row consolidating by source/medium/campaign.
- **30-day sparkline** → a visible spike on the day of the talk.
- **Top countries** for that campaign → who actually scanned.

---

## Sibling-subdomain footer cross-links

Each of the 4 sibling subdomains (orenu, panorama, meridianiq, nucleoia)
has a footer crediting vitormr.dev as developer. Tag those links so
referrals back to the apex are attributed cleanly:

```
https://vitormr.dev/?utm_source=subdomain&utm_medium=footer&utm_campaign=general
```

Per-subdomain disambiguation if needed (e.g., to see which subdomain
drives the most apex referrals):

```
https://vitormr.dev/?utm_source=subdomain&utm_medium=footer&utm_campaign=panorama
https://vitormr.dev/?utm_source=subdomain&utm_medium=footer&utm_campaign=orenu
```

Subdomain footers are public surfaces — keep the UTM stable so
attribution accumulates over time, not per-edit.

---

## LinkedIn divulgation — template

LinkedIn post bodies:

```
https://vitormr.dev/?utm_source=linkedin&utm_medium=post&utm_campaign=launch-2026-05
```

LinkedIn profile bio link (always-on, doesn't change):

```
https://vitormr.dev/?utm_source=linkedin&utm_medium=bio&utm_campaign=general
```

The two appear as distinct rows in attribution — separates always-on
discovery from event-driven post traffic.

---

## GitHub README cross-link — template

For each of the public repos linking back to vitormr.dev (panorama,
meridianiq, ai-pm-research-hub, SnipeScheduler-FleetManager, etc.):

```
[Vitor M. Rodovalho](https://vitormr.dev/?utm_source=github&utm_medium=readme&utm_campaign=general) — author
```

Per-repo disambiguation if you want to see which repo drives the most
referrals:

```
?utm_source=github&utm_medium=readme&utm_campaign=panorama
?utm_source=github&utm_medium=readme&utm_campaign=meridianiq
```

---

## Email signature — template

```
Vitor M. Rodovalho, PMP®
vitormr.dev/?utm_source=email&utm_medium=signature&utm_campaign=general
```

Hide the query string visually by hyperlinking the URL text. Recipients
get attribution; rendered link is clean.

---

## EB-2 NIW evidence packet — special campaign

For URLs embedded in petition exhibits or recommendation letters that
reference vitormr.dev as evidence surface, use:

```
https://vitormr.dev/?utm_source=email&utm_medium=signature&utm_campaign=niw-evidence
```

(or `utm_source=qr` / `utm_medium=talk-handout` if delivered another way).

Why: lets you see — without identifying individuals — whether reviewers
or affiants are actually clicking through to verify claims. Aggregate
signal, no PII, fits within the existing cookieless analytics.

---

## Anti-patterns (don't do these)

- ❌ **Manually setting `utm_source=direct`** — that's an artifact of "no
  UTM + no referrer," not a value to set. CF logs untagged + no-referrer
  visits as direct by default.
- ❌ **Inventing new sources/mediums per post** (`linkedin-may-2026`,
  `linkedin-niw-launch`, `linkedin-talk-promo`). Use the vocab above;
  vary `utm_campaign` instead.
- ❌ **Spaces or special characters** in any param. CF GraphQL aggregates
  by literal string match; `?utm_campaign=PMI Talk` and
  `?utm_campaign=pmi-talk` count as different rows.
- ❌ **UTMs inside internal site links** between pages of vitormr.dev.
  UTMs are for inbound traffic only; cross-page navigation pollutes the
  data.
- ❌ **Shortened URLs that hide the UTM** (`bit.ly/vitor-talk`). The
  shortener captures attribution upstream and the destination URL just
  sees the shortener as referrer. If you must use a shortener (e.g., for
  QR code density), make sure it preserves UTM params on redirect —
  Bitly and similar do this by default.

---

## How to test a tagged link before sharing

```bash
curl -sI "https://vitormr.dev/?utm_source=qr&utm_medium=talk-slide&utm_campaign=pmi-summit-2026-08" | head -5
```

Expected: `HTTP/2 200`. The visit will show up on the Cloudflare Web
Analytics dashboard (or `/admin/metrics` if/when that lands) within
~2–10 minutes.

---

## Adding new vocabulary

If a new channel/event comes up that doesn't fit the tables above:

1. Add a row in the appropriate section of this doc (PR with `docs(utm):` prefix).
2. Use the new value in the first link that goes out — don't backfill old links.
3. Mention in commit message so future agents see the convention extension.

Keeps the vocabulary stable + auditable.

---

## Cross-site alignment with sarah-rodovalho-site

Where Vitor and Sarah's channels overlap (LinkedIn, QR, email, PMI),
the vocabulary is intentionally aligned. Differences:

| Concept | vitormr.dev | sarahrodovalho.com |
|---|---|---|
| Newsletter source | n/a (no Substack today) | `newsletter` |
| Academic source | n/a | `arcc`, `aia` |
| GitHub-repo source | `github` | n/a (no public repos) |
| Subdomain source | `subdomain` (4 sibling apps) | n/a |
| EB campaign | `niw-evidence` (EB-2 NIW) | (parallel use case if/when ever shipped on her side) |

Both sites share `general` as the always-on default and
`launch-2026-MM` for time-stamped pushes.
