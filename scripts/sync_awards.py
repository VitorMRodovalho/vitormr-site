#!/usr/bin/env python3
"""
sync_awards.py — ADR-024.1 Phase 3a Orenu → site awards sync.

Per ADR-024.1 Phase 3a. Fourth source table in the ADR-024 sync pipeline;
mirrors the architecture of sync_credentials.py with awards-specific
match strategy:

  - Source table: public.dim_award (15 rows currently: 3 Vitor + 12 Sarah).
  - Matching: Orenu `title` → MDX `title` via substring (either direction
    handles short-Orenu/long-MDX AND long-Orenu/short-MDX patterns;
    same approach as sync_credentials).
  - PRESENCE-AWARE only — no field auto-overwrite. Sarah's awards
    content schema doesn't have the `status` or `yearAwarded` fields
    that Orenu adds; Vitor's has them. Phase 3a sync stays presence-
    aware to avoid asymmetric drift. Field authority migrates in
    Phase 3a.1 once schema parity is established.
  - Drift warnings on title + organization mismatches.

Run modes:
  python scripts/sync_awards.py                    # dry-run
  python scripts/sync_awards.py --apply            # no-op in Phase 3a

Environment:
  ORENU_DATABASE_URL — read-only Postgres URL (CI secret).

Exit codes:
  0 — perfect match
  1 — warnings: stubs needed / orphan MDX / drift
  2 — fatal error
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import psycopg2

from sync_publications import (  # type: ignore[import]
    HOUSEHOLD_ID,
    parse_frontmatter,
    title_matches,
)

DEFAULT_CONTENT_DIR = Path("src/content/awards")


@dataclass
class OrenuAward:
    award_id: str
    person_display_name: str
    title: str
    organization: str
    organization_url: str | None
    scope: str
    status: str
    subcategory: str | None
    period: str
    year_awarded: int | None
    description: str
    external_url: str | None
    hero_image_url: str | None


@dataclass
class MdxAward:
    path: Path
    frontmatter: dict[str, Any]
    body: str


def fetch_public_awards_for_person(conn, display_name: str) -> list[OrenuAward]:
    sql = """
        SELECT
          a.award_id::text,
          e.display_name,
          a.title,
          a.organization,
          a.organization_url,
          a.scope::text,
          a.status::text,
          a.subcategory,
          a.period,
          a.year_awarded,
          a.description,
          a.external_url,
          a.hero_image_url
        FROM public.dim_award a
        JOIN public.dim_entity e ON e.id = a.person_entity_id
        WHERE a.household_id = %s
          AND a.public_visibility = true
          AND lower(e.display_name) = lower(%s)
        ORDER BY a.year_awarded DESC NULLS LAST, a.title
    """
    with conn.cursor() as cur:
        cur.execute(sql, (HOUSEHOLD_ID, display_name))
        rows = cur.fetchall()
    return [
        OrenuAward(
            award_id=r[0],
            person_display_name=r[1],
            title=r[2],
            organization=r[3],
            organization_url=r[4],
            scope=r[5],
            status=r[6],
            subcategory=r[7],
            period=r[8],
            year_awarded=r[9],
            description=r[10],
            external_url=r[11],
            hero_image_url=r[12],
        )
        for r in rows
    ]


def read_mdx_files(content_dir: Path) -> list[MdxAward]:
    out: list[MdxAward] = []
    for path in sorted(content_dir.glob("*.mdx")):
        text = path.read_text(encoding="utf-8")
        fm, body = parse_frontmatter(text)
        out.append(MdxAward(path=path, frontmatter=fm, body=body))
    return out


def match_pairs(
    orenu: list[OrenuAward], mdx: list[MdxAward]
) -> tuple[
    list[tuple[OrenuAward, MdxAward]],
    list[OrenuAward],
    list[MdxAward],
]:
    """Match Orenu awards to MDX files by title substring (either direction)."""
    matched: list[tuple[OrenuAward, MdxAward]] = []
    used_paths: set[Path] = set()

    for op in orenu:
        for m in mdx:
            if m.path in used_paths:
                continue
            mdx_title = str(m.frontmatter.get("title", ""))
            if title_matches(op.title, mdx_title) or title_matches(mdx_title, op.title):
                matched.append((op, m))
                used_paths.add(m.path)
                break

    matched_ids = {pair[0].award_id for pair in matched}
    unmatched_orenu = [op for op in orenu if op.award_id not in matched_ids]
    unmatched_mdx = [m for m in mdx if m.path not in used_paths]
    return matched, unmatched_orenu, unmatched_mdx


def compute_drift_warnings(orenu: OrenuAward, mdx: MdxAward) -> list[str]:
    """Title + organization drift warnings; no auto-overwrite."""
    warnings: list[str] = []
    fm = mdx.frontmatter

    if not title_matches(orenu.title, fm.get("title", "")) and not title_matches(fm.get("title", ""), orenu.title):
        warnings.append(
            f"    title:  Orenu={orenu.title!r}\n"
            f"            MDX  ={fm.get('title')!r}"
        )

    if orenu.organization and fm.get("organization"):
        mdx_org = str(fm["organization"])
        if orenu.organization not in mdx_org and mdx_org not in orenu.organization:
            warnings.append(
                f"    org:    Orenu={orenu.organization!r}\n"
                f"            MDX  ={mdx_org!r}"
            )

    return warnings


def run(
    content_dir: Path,
    apply: bool,
    person_display_name: str,
    conn=None,
    *,
    orenu_override: list[OrenuAward] | None = None,
) -> int:
    mode_label = "APPLY" if apply else "DRY-RUN"
    print(f"sync_awards.py [{mode_label}]  person={person_display_name!r}")
    print(f"  content_dir = {content_dir}")

    if orenu_override is not None:
        orenu_awards = orenu_override
    else:
        assert conn is not None
        orenu_awards = fetch_public_awards_for_person(conn, person_display_name)

    mdx_awards = read_mdx_files(content_dir)

    print(f"  Orenu public rows: {len(orenu_awards)}")
    print(f"  MDX files:         {len(mdx_awards)}")

    matched, unmatched_orenu, unmatched_mdx = match_pairs(orenu_awards, mdx_awards)
    print(f"  Matched pairs:     {len(matched)}")
    print(f"  Unmatched Orenu:   {len(unmatched_orenu)}")
    print(f"  Unmatched MDX:     {len(unmatched_mdx)}")

    exit_code = 0
    drift_count = 0

    for orenu, mdx in matched:
        drifts = compute_drift_warnings(orenu, mdx)
        if drifts:
            drift_count += len(drifts)
            print(f"\n  DRIFT [{mdx.path.name}]:")
            for d in drifts:
                print(d)

    for op in unmatched_orenu:
        print(f"\n  STUB NEEDED — Orenu award_id={op.award_id}")
        print(f"    title = {op.title!r}")
        print(f"    scope = {op.scope}  status = {op.status}")
        print(f"    No matching MDX file in {content_dir}.")
        print(f"    Action: create an MDX file with the canonical title + frontmatter.")
        exit_code = 1

    for mp in unmatched_mdx:
        print(f"\n  ORPHAN MDX — {mp.path.name}")
        print(f"    title = {mp.frontmatter.get('title')!r}")
        print(f"    No matching public Orenu row for person={person_display_name!r}.")
        print(f"    Action: flip Orenu public_visibility=true or move MDX to _archive/.")
        exit_code = 1

    print(f"\nSummary:")
    print(f"  Drift warnings (title/org mismatch): {drift_count}")
    print(f"  Stubs needed:                        {len(unmatched_orenu)}")
    print(f"  Orphan MDX:                          {len(unmatched_mdx)}")
    print(f"  Note: Phase 3a is presence-aware ONLY — no fields auto-overwritten.")

    if drift_count > 0:
        exit_code = 1

    return exit_code


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 3a Orenu → site award sync")
    parser.add_argument("--apply", action="store_true", help="No-op in Phase 3a")
    parser.add_argument(
        "--content-dir",
        default=str(DEFAULT_CONTENT_DIR),
        help="Path to the awards content collection",
    )
    parser.add_argument(
        "--person",
        default="Vitor Maia Rodovalho",
        help="dim_entity.display_name of the award owner",
    )
    args = parser.parse_args()

    content_dir = Path(args.content_dir)
    if not content_dir.is_dir():
        print(f"ERROR: content dir not found: {content_dir}", file=sys.stderr)
        sys.exit(2)

    db_url = os.environ.get("ORENU_DATABASE_URL")
    if not db_url:
        print("ERROR: ORENU_DATABASE_URL environment variable not set", file=sys.stderr)
        sys.exit(2)

    try:
        conn = psycopg2.connect(db_url, application_name="sync-awards")
    except Exception as e:
        print(f"ERROR: cannot connect to Orenu Postgres: {e}", file=sys.stderr)
        sys.exit(2)

    try:
        exit_code = run(content_dir, args.apply, args.person, conn=conn)
    finally:
        conn.close()

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
