#!/usr/bin/env python3
"""
sync_community.py — ADR-024.1 Phase 3b Orenu → site community-service sync.

Per ADR-024.1 Phase 3b. Fifth source table in the ADR-024 sync pipeline;
mirrors the architecture of sync_awards.py with community-service-
specific match strategy:

  - Source table: public.fact_community_service (5 rows currently:
    Vitor only; Sarah expansion deferred).
  - Matching: Orenu `organization` → MDX `organization` via substring
    (organization is more stable than role; role formatting varies).
  - PRESENCE-AWARE only — no field auto-overwrite. Same scope as
    sync_awards.py.
  - Drift warnings on role + organization mismatches.

Run modes:
  python scripts/sync_community.py                    # dry-run
  python scripts/sync_community.py --apply            # no-op in Phase 3b

Environment:
  ORENU_DATABASE_URL — read-only Postgres URL (CI secret).

Exit codes: 0 clean · 1 warnings · 2 fatal error.
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

DEFAULT_CONTENT_DIR = Path("src/content/community")


@dataclass
class OrenuCommunity:
    service_id: str
    person_display_name: str
    role: str
    organization: str
    organization_url: str | None
    affiliation: str
    start_year: int | None
    is_current: bool
    description: str
    archive_links: list[dict[str, str]]


@dataclass
class MdxCommunity:
    path: Path
    frontmatter: dict[str, Any]
    body: str


def fetch_public_community_for_person(conn, display_name: str) -> list[OrenuCommunity]:
    sql = """
        SELECT
          s.service_id::text,
          e.display_name,
          s.role,
          s.organization,
          s.organization_url,
          s.affiliation,
          s.start_year,
          s.is_current,
          s.description,
          s.archive_links
        FROM public.fact_community_service s
        JOIN public.dim_entity e ON e.id = s.person_entity_id
        WHERE s.household_id = %s
          AND s.public_visibility = true
          AND lower(e.display_name) = lower(%s)
        ORDER BY s.is_current DESC, s.start_year DESC NULLS LAST, s.display_order
    """
    with conn.cursor() as cur:
        cur.execute(sql, (HOUSEHOLD_ID, display_name))
        rows = cur.fetchall()
    return [
        OrenuCommunity(
            service_id=r[0],
            person_display_name=r[1],
            role=r[2],
            organization=r[3],
            organization_url=r[4],
            affiliation=r[5],
            start_year=r[6],
            is_current=bool(r[7]),
            description=r[8],
            archive_links=r[9] or [],
        )
        for r in rows
    ]


def read_mdx_files(content_dir: Path) -> list[MdxCommunity]:
    out: list[MdxCommunity] = []
    for path in sorted(content_dir.glob("*.mdx")):
        text = path.read_text(encoding="utf-8")
        fm, body = parse_frontmatter(text)
        out.append(MdxCommunity(path=path, frontmatter=fm, body=body))
    return out


def match_pairs(
    orenu: list[OrenuCommunity], mdx: list[MdxCommunity]
) -> tuple[
    list[tuple[OrenuCommunity, MdxCommunity]],
    list[OrenuCommunity],
    list[MdxCommunity],
]:
    """Match by organization substring (either direction)."""
    matched: list[tuple[OrenuCommunity, MdxCommunity]] = []
    used_paths: set[Path] = set()

    for op in orenu:
        for m in mdx:
            if m.path in used_paths:
                continue
            mdx_org = str(m.frontmatter.get("organization", ""))
            if title_matches(op.organization, mdx_org) or title_matches(mdx_org, op.organization):
                matched.append((op, m))
                used_paths.add(m.path)
                break

    matched_ids = {pair[0].service_id for pair in matched}
    unmatched_orenu = [op for op in orenu if op.service_id not in matched_ids]
    unmatched_mdx = [m for m in mdx if m.path not in used_paths]
    return matched, unmatched_orenu, unmatched_mdx


def compute_drift_warnings(orenu: OrenuCommunity, mdx: MdxCommunity) -> list[str]:
    """Role + organization drift warnings; no auto-overwrite."""
    warnings: list[str] = []
    fm = mdx.frontmatter

    mdx_role = str(fm.get("role", ""))
    if orenu.role and mdx_role and not title_matches(orenu.role, mdx_role) and not title_matches(mdx_role, orenu.role):
        warnings.append(
            f"    role:   Orenu={orenu.role!r}\n"
            f"            MDX  ={mdx_role!r}"
        )

    mdx_org = str(fm.get("organization", ""))
    if orenu.organization and mdx_org and not title_matches(orenu.organization, mdx_org) and not title_matches(mdx_org, orenu.organization):
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
    orenu_override: list[OrenuCommunity] | None = None,
) -> int:
    mode_label = "APPLY" if apply else "DRY-RUN"
    print(f"sync_community.py [{mode_label}]  person={person_display_name!r}")
    print(f"  content_dir = {content_dir}")

    if orenu_override is not None:
        orenu_entries = orenu_override
    else:
        assert conn is not None
        orenu_entries = fetch_public_community_for_person(conn, person_display_name)

    mdx_entries = read_mdx_files(content_dir)

    print(f"  Orenu public rows: {len(orenu_entries)}")
    print(f"  MDX files:         {len(mdx_entries)}")

    matched, unmatched_orenu, unmatched_mdx = match_pairs(orenu_entries, mdx_entries)
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
        print(f"\n  STUB NEEDED — Orenu service_id={op.service_id}")
        print(f"    role  = {op.role!r}")
        print(f"    org   = {op.organization!r}")
        print(f"    No matching MDX file in {content_dir}.")
        exit_code = 1

    for mp in unmatched_mdx:
        print(f"\n  ORPHAN MDX — {mp.path.name}")
        print(f"    organization = {mp.frontmatter.get('organization')!r}")
        print(f"    No matching public Orenu row for person={person_display_name!r}.")
        exit_code = 1

    print(f"\nSummary:")
    print(f"  Drift warnings (role/org mismatch): {drift_count}")
    print(f"  Stubs needed:                       {len(unmatched_orenu)}")
    print(f"  Orphan MDX:                         {len(unmatched_mdx)}")
    print(f"  Note: Phase 3b is presence-aware ONLY — no fields auto-overwritten.")

    if drift_count > 0:
        exit_code = 1

    return exit_code


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 3b Orenu → site community sync")
    parser.add_argument("--apply", action="store_true", help="No-op in Phase 3b")
    parser.add_argument(
        "--content-dir",
        default=str(DEFAULT_CONTENT_DIR),
        help="Path to the community content collection",
    )
    parser.add_argument(
        "--person",
        default="Vitor Maia Rodovalho",
        help="dim_entity.display_name of the community-service holder",
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
        conn = psycopg2.connect(db_url, application_name="sync-community")
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
