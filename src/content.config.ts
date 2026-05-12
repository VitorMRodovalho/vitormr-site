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
 * no screenshots, no real artifact reproduction); content drawn only
 * from externally-disclosable prior-program work. Optional inline ASCII
 * data-flow diagram for cases where flow narrative helps comprehension.
 *
 * Compliance posture: current-employer programs are intentionally out
 * of scope — sector-only on /about.
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
 * `writing` — long-form essays + technical notes. MDX-bodied; Schema.org
 * BlogPosting on detail page via schemaJsonLd prop on BaseLayout.
 *
 * Compliance posture: same as case-studies family — no client-confidential
 * artifacts.
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
 * where Vitor authored it. Current-employer scope only.
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

/**
 * `awards` — honors, scholarships, nominations, leadership memberships.
 * Distinct from `credentials` (verifiable permission-to-practice /
 * knowledge attestation) and `experience` (employment timeline): an
 * award is recognition received for past achievement or appointment.
 *
 * Schema mirrors sarah-rodovalho-site's `awards` collection so the same
 * sync_awards.py script can target both sites with no field translation
 * (the `evidenceCategory` field is omitted on Vitor's side — internal
 * cross-referencing is Sarah-only). The `status` enum captures the
 * nominee/finalist/received distinction (Vitor's PMI LATAM 2025
 * Nominee case + future workflows).
 */
const awards = defineCollection({
  loader: glob({ pattern: "**/*.mdx", base: "./src/content/awards" }),
  schema: ({ image }) =>
    z
      .object({
        title: z.string(),
        organization: z.string(),
        organizationUrl: z.url().optional(),
        scope: z.enum([
          "international",
          "professional-leadership",
          "honor-society",
          "team-award",
          "academic-honor",
          "competitive-scholarship",
        ]),
        status: z.enum(["received", "nominee", "finalist"]).default("received"),
        subcategory: z.string().optional(),
        period: z.string(),
        yearAwarded: z.number().int().min(2000).max(2100).optional(),
        description: z.string(),
        externalUrl: z.url().optional(),
        heroImage: image().optional(),
        heroImageAlt: z.string().optional(),
        order: z.number().int().default(100),
      })
      .refine((data) => !data.heroImage || data.heroImageAlt, {
        message: "heroImageAlt is required when heroImage is set",
        path: ["heroImageAlt"],
      }),
});

/**
 * `credentials` — professional licenses, certifications, designations,
 * and competence-based memberships. Distinct from `awards` (recognition
 * received for past achievement) and `experience` (employment timeline):
 * a credential is a verifiable permission-to-practice or knowledge-
 * attestation issued by a governing body.
 *
 * Schema mirrors sarah-rodovalho-site's `credentials` collection exactly
 * so the same sync_credentials.py script can target both sites with no
 * code changes — just a different --content-dir + --person invocation.
 *
 * Compliance posture: credential identifiers (PMP #, CMAA #, CONFEA #,
 * etc.) are stored only in Orenu's dim_credential.credential_id_private
 * column (never synced to public sites). The MDX `credentialId` field
 * is reserved for credentials whose IDs are designed to be looked up
 * against a public registry (e.g., NCARB Record, CAU registry).
 */
const credentials = defineCollection({
  loader: glob({ pattern: "**/*.mdx", base: "./src/content/credentials" }),
  schema: z.object({
    title: z.string(),
    organization: z.string(),
    organizationUrl: z.url().optional(),
    kind: z.enum(["license", "certification", "designation", "membership"]),
    status: z.enum(["active", "in-progress", "expired"]).default("active"),
    credentialId: z.string().optional(),
    issuedDate: z.string().optional(),
    validThrough: z.string().optional(),
    verifyUrl: z.url().optional(),
    description: z.string().optional(),
    order: z.number().int().default(100),
  }),
});

export const collections = {
  experience,
  projects,
  powerbi,
  caseStudies,
  writing,
  methodologies,
  credentials,
  awards,
};
