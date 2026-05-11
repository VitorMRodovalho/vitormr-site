import { defineCollection } from "astro:content";
import { glob } from "astro/loaders";
import { z } from "astro/zod";

/**
 * `experience` — curated employment timeline.
 *
 * Source-of-truth: CV + LinkedIn (extracted 2026-05-09 to memory file
 * `project_vitor_cv_linkedin_github_extraction.md`). 7 highlighted positions
 * from a 9-position career — full chronology lives on LinkedIn for
 * completeness.
 *
 * Schema design notes:
 *  - `period` free text (matches sarah-rodovalho-site convention; e.g.
 *    "Apr 2026 – present", "2010 – 2019")
 *  - `industry` enum supports visual badges (rail, data-center, real-estate,
 *    higher-ed, mining)
 *  - `highlights` = bulleted impact statements with quantitative detail when
 *    public-disclosed (e.g., $279M change orders, R$338M GDV — all on
 *    Vitor's public LinkedIn)
 *  - `isCurrent` flips a "Current role" badge on the listing page
 */
const experience = defineCollection({
  loader: glob({ pattern: "**/*.mdx", base: "./src/content/experience" }),
  schema: z.object({
    role: z.string(),
    organization: z.string(),
    organizationUrl: z.url().optional(),
    period: z.string(),
    location: z.string(),
    industry: z.enum(["data-center", "rail", "higher-ed", "real-estate", "mining"]),
    summary: z.string(),
    highlights: z.array(z.string()).default([]),
    isCurrent: z.boolean().default(false),
    order: z.number().int().default(100),
  }),
});

/**
 * `projects` — Tier-1 case studies for the /projects hub + per-project pages.
 *
 * Schema design notes:
 *  - One-pager case study format: problem → approach → impact → stack → links
 *  - `role` constrained to the badge taxonomy (Founder / Co-founder / Author /
 *    Maintainer / Contributor) so the role-pill class renders consistently.
 *    "Co-founder" is reserved for collective initiatives where Vitor is one
 *    of multiple founders; sole-founder solo work uses "Founder".
 *  - `status` is free text (e.g., "v4.3.0 in production", "Pre-alpha · pilot
 *    prep", "Private platform · invite-only beta planned")
 *  - `links.live` is the live deployment URL; `links.repo` the GitHub repo
 *  - `nameAlt` is the secondary-language name (e.g., "Núcleo IA & GP" for
 *    the EN-primary "AI & PM Research Hub")
 */
const projects = defineCollection({
  loader: glob({ pattern: "**/*.mdx", base: "./src/content/projects" }),
  schema: z.object({
    name: z.string(),
    nameAlt: z.string().optional(),
    role: z.enum(["Founder", "Co-founder", "Author", "Maintainer", "Contributor"]),
    tagline: z.string(),
    summary: z.string(),
    problem: z.string(),
    approach: z.string(),
    impact: z.string(),
    license: z.string().optional(),
    status: z.string(),
    techStack: z.array(z.string()).default([]),
    industry: z.string().optional(),
    links: z
      .object({
        live: z.url().optional(),
        repo: z.url().optional(),
        docs: z.url().optional(),
      })
      .optional(),
    order: z.number().int().default(100),
  }),
});

/**
 * `powerbi` — Tier 2 catalog of anonymized Power BI artifacts (4 suites,
 * ~6,151 DAX measures across Brazilian real-estate development +
 * construction + BPO operations). All MIT, all anonymized — knowledge
 * artifacts (DAX, M, schemas, relationships), NOT runnable .pbix.
 *
 * Schema notes:
 *  - `dashboards` is an ordered list of objects (name + measures + focus)
 *  - `totalMeasures` denormalized for hub page sorting/display
 *  - `highlights` are bullet impact statements (e.g., "1-master to
 *    9-variants pattern", "SVG gauge in DAX")
 */
const powerbi = defineCollection({
  loader: glob({ pattern: "**/*.mdx", base: "./src/content/powerbi" }),
  schema: z.object({
    name: z.string(),
    tagline: z.string(),
    summary: z.string(),
    dashboardCount: z.number().int().min(1),
    totalMeasures: z.number().int().min(1),
    dashboards: z.array(
      z.object({
        name: z.string(),
        measures: z.number().int().min(0),
        focus: z.string(),
      }),
    ),
    highlights: z.array(z.string()).default([]),
    techStack: z.array(z.string()).default([]),
    repoUrl: z.url(),
    order: z.number().int().default(100),
  }),
});

/**
 * `caseStudies` — Tier 2 portfolio family of selected professional
 * programs Vitor delivered. Pure-text card treatment (no client logos,
 * no screenshots, no real artifact reproduction); content lifted from
 * Vitor's AECOM-cleared resume so external-marketing-cleared. Optional
 * inline ASCII data-flow diagram for cases where flow narrative helps
 * comprehension (currently Trinus Databricks Lakehouse).
 *
 * Compliance posture: no Linesight (active NDA — sector-only on /about).
 */
const caseStudies = defineCollection({
  loader: glob({ pattern: "**/*.mdx", base: "./src/content/case-studies" }),
  schema: z.object({
    name: z.string(),
    client: z.string(),
    role: z.string(),
    period: z.string(),
    employer: z.string().optional(),
    scopeHeadline: z.string(),
    tagline: z.string(),
    summary: z.string(),
    context: z.string(),
    roleNarrative: z.string(),
    methodology: z.array(z.string()).default([]),
    stack: z.array(z.string()).default([]),
    inlineDiagram: z.string().optional(),
    order: z.number().int().default(100),
  }),
});

/**
 * `writing` — long-form essays + technical notes. Started as a stub post-V09a
 * (council product-leader rec: "even 1 anchor post passes the original-
 * contribution Kazarian test"). MDX-bodied; Schema.org BlogPosting on
 * detail page via schemaJsonLd prop on BaseLayout.
 *
 * Compliance posture: same as case-studies family — no client-confidential
 * artifacts. Linesight sector-only.
 */
const writing = defineCollection({
  loader: glob({ pattern: "**/*.mdx", base: "./src/content/writing" }),
  schema: z.object({
    title: z.string(),
    subtitle: z.string().optional(),
    description: z.string(),
    publishedAt: z.string(),
    updatedAt: z.string().optional(),
    revision: z.string().optional(),
    tags: z.array(z.string()).default([]),
    estimatedReadMinutes: z.number().int().min(1),
    order: z.number().int().default(100),
    status: z.enum(["draft", "living", "published"]).default("living"),
  }),
});

/**
 * `methodologies` — Tier 2 portfolio family of abstract patterns from
 * Vitor's career work. Distinct from `caseStudies` which keeps the
 * named programs intact: `methodologies` strips away the client + dollar
 * figures + program names and articulates the reusable pattern.
 *
 * Compliance posture: NO client names, NO project names, NO dollar
 * figures. The methodology is named for the PATTERN, not the engagement
 * where Vitor authored it. Linesight scope-only.
 */
const methodologies = defineCollection({
  loader: glob({ pattern: "**/*.mdx", base: "./src/content/methodologies" }),
  schema: z.object({
    name: z.string(),
    domain: z.string(),
    tagline: z.string(),
    principle: z.string(),
    summary: z.string(),
    context: z.string(),
    mechanism: z.array(z.string()).default([]),
    applicability: z.array(z.string()).default([]),
    antiPattern: z.string().optional(),
    stackAgnostic: z.boolean().default(true),
    order: z.number().int().default(100),
  }),
});

export const collections = { experience, projects, powerbi, caseStudies, writing, methodologies };
