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

export const collections = { experience };
