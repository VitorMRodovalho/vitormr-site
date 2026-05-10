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
 *  - `role` constrained to the badge taxonomy (Founder / Author / Maintainer /
 *    Contributor) so the role-pill class renders consistently
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
    role: z.enum(["Founder", "Author", "Maintainer", "Contributor"]),
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

export const collections = { experience, projects, powerbi };
