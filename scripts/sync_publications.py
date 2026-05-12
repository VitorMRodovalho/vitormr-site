#!/usr/bin/env python3
"""
sync_publications.py — Phase 1a Orenu → sarahrodovalho.com publication sync.

Per ADR-024-orenu-as-source-of-truth-personal-branding-sites.md (Accepted
2026-05-12; council revisions D1-D7 applied).

Phase 1a scope (intentionally narrow given Orenu's current data depth):

  - PRESENCE GATE — Orenu's dim_publication.public_visibility flag gates
    whether an MDX file should exist in src/content/publications/.
    Mismatches between the 3 public Orenu rows and the 3 MDX files are
    surfaced as warnings for human PR review (not auto-created/archived
    in v0 — defer to first real new-publication or retraction case).

  - CITATION AUTHORITY — citationsAt.{count,observedOn} in each MDX is
    overwritten from Orenu's google_scholar_citations_count +
    citations_last_audited_at when Orenu has fresher data. This is the
    one field Phase 1a treats as Orenu-authoritative.

  - DRIFT REPORT — other factual fields (title, venue, year, doi) where
    Orenu has data that diverges from MDX are logged as warnings but
    NOT auto-overwritten. Orenu currently has less depth than the MDX
    (short titles without subtitles, online-first dates not print-issue
    years, no DOIs); reconciling those is Phase 1b+ scope as Orenu's
    schema deepens.

Run modes:
  python scripts/sync_publications.py                 # dry-run; reports planned changes
  python scripts/sync_publications.py --apply         # writes citation updates to disk

Environment:
  ORENU_DATABASE_URL — read-only Postgres connection string (CI secret).

Exit codes:
  0 — no changes needed (or --apply succeeded with no warnings)
  1 — warnings emitted: drift, stubs needed, orphan MDX (human PR review)
  2 — fatal error (connection failure, content dir missing, etc.)

Idempotency: re-running with no upstream changes produces zero file
writes and zero stdout diffs. The drift-warning path is the script's
only non-idempotent output, and re-running with the same drift state
emits the same warning lines (still no file changes).
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import psycopg2
import yaml

HOUSEHOLD_ID = "00f03063-e88f-46ff-b9d7-c6bdc346e977"
DEFAULT_CONTENT_DIR = Path("src/content/publications")


@dataclass
class OrenuPublication:
    publication_id: str
    title: str
    journal_name: str | None
    doi: str | None
    published_at: str | None
    google_scholar_citations_count: int
    citations_last_audited_at: str | None


@dataclass
class MdxPublication:
    path: Path
    frontmatter: dict[str, Any]
    body: str


# Unicode subscript + superscript digits → ASCII so "CO₂" matches "CO2".
_DIGIT_TRANSLATE = str.maketrans(
    "₀₁₂₃₄₅₆₇₈₉⁰¹²³⁴⁵⁶⁷⁸⁹",
    "01234567890123456789",
)


def _normalize(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", s.lower().translate(_DIGIT_TRANSLATE)).strip()


def title_matches(orenu_title: str, mdx_title: str) -> bool:
    """Loose: Orenu's (often-shorter) title appears as a substring of MDX title."""
    return _normalize(orenu_title) in _normalize(mdx_title)


def fetch_public_publications(conn) -> list[OrenuPublication]:
    sql = """
        SELECT
          publication_id::text,
          title,
          journal_name,
          doi,
          published_at::text,
          google_scholar_citations_count,
          citations_last_audited_at::date::text
        FROM public.dim_publication
        WHERE household_id = %s
          AND public_visibility = true
        ORDER BY published_at DESC NULLS LAST
    """
    with conn.cursor() as cur:
        cur.execute(sql, (HOUSEHOLD_ID,))
        rows = cur.fetchall()
    return [
        OrenuPublication(
            publication_id=r[0],
            title=r[1],
            journal_name=r[2],
            doi=r[3],
            published_at=r[4],
            google_scholar_citations_count=r[5] or 0,
            citations_last_audited_at=r[6],
        )
        for r in rows
    ]


def parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---\n"):
        raise ValueError("MDX file missing opening frontmatter delimiter")
    parts = text.split("---\n", 2)
    if len(parts) < 3:
        raise ValueError("MDX file missing closing frontmatter delimiter")
    fm = yaml.safe_load(parts[1]) or {}
    return fm, parts[2]


def serialize_frontmatter(fm: dict[str, Any]) -> str:
    """Serialize a dict back to YAML preserving insertion order + Unicode + block style.

    PyYAML's safe_dump emits keys in insertion order when sort_keys=False; we
    take advantage of that by mutating the dict in place (not re-creating)
    so the YAML key order matches the original MDX file.
    """
    return yaml.safe_dump(
        fm,
        sort_keys=False,
        default_flow_style=False,
        allow_unicode=True,
        width=10_000,  # don't wrap long abstract: lines
    )


def write_mdx(path: Path, frontmatter: dict[str, Any], body: str) -> None:
    yaml_str = serialize_frontmatter(frontmatter)
    path.write_text(f"---\n{yaml_str}---\n{body}", encoding="utf-8")


def read_mdx_files(content_dir: Path) -> list[MdxPublication]:
    out: list[MdxPublication] = []
    for path in sorted(content_dir.glob("*.mdx")):
        text = path.read_text(encoding="utf-8")
        fm, body = parse_frontmatter(text)
        out.append(MdxPublication(path=path, frontmatter=fm, body=body))
    return out


def match_pairs(
    orenu_pubs: list[OrenuPublication],
    mdx_pubs: list[MdxPublication],
) -> tuple[
    list[tuple[OrenuPublication, MdxPublication]],
    list[OrenuPublication],
    list[MdxPublication],
]:
    """Match Orenu rows to MDX files. DOI exact match first; title substring fallback."""
    matched: list[tuple[OrenuPublication, MdxPublication]] = []
    used_mdx_paths: set[Path] = set()

    for op in orenu_pubs:
        chosen: MdxPublication | None = None

        if op.doi:
            for m in mdx_pubs:
                if m.path in used_mdx_paths:
                    continue
                if m.frontmatter.get("doi") == op.doi:
                    chosen = m
                    break

        if chosen is None:
            for m in mdx_pubs:
                if m.path in used_mdx_paths:
                    continue
                mdx_title = m.frontmatter.get("title", "")
                if title_matches(op.title, mdx_title):
                    chosen = m
                    break

        if chosen is not None:
            matched.append((op, chosen))
            used_mdx_paths.add(chosen.path)

    matched_orenu_ids = {pair[0].publication_id for pair in matched}
    unmatched_orenu = [op for op in orenu_pubs if op.publication_id not in matched_orenu_ids]
    unmatched_mdx = [m for m in mdx_pubs if m.path not in used_mdx_paths]
    return matched, unmatched_orenu, unmatched_mdx


def compute_citations_update(
    orenu: OrenuPublication,
    mdx: MdxPublication,
) -> dict[str, Any] | None:
    """Return the new citationsAt dict iff Orenu has data and it should win.

    Tie-breaker rule: Orenu wins only when its citations_last_audited_at is
    >= the MDX's observedOn. If MDX has a more-recent observedOn (someone
    manually refreshed the count on the site without updating Orenu),
    treat the MDX as the fresher source and DO NOT overwrite. Orenu can
    catch up when its audit_citations_count workflow runs.
    """
    if orenu.citations_last_audited_at is None:
        return None
    new_block = {
        "count": orenu.google_scholar_citations_count,
        "observedOn": orenu.citations_last_audited_at,
    }
    current = mdx.frontmatter.get("citationsAt")
    if not isinstance(current, dict):
        return new_block  # bootstrap: MDX has no citationsAt yet
    if current == new_block:
        return None
    current_observed = str(current.get("observedOn", ""))
    if current_observed and current_observed > orenu.citations_last_audited_at:
        # MDX was audited more recently than Orenu; defer to MDX.
        return None
    return new_block


def compute_drift_warnings(
    orenu: OrenuPublication,
    mdx: MdxPublication,
) -> list[str]:
    """Non-authoritative-field divergences worth a human eye (no auto-overwrite).

    Phase 1a checks only title + DOI:
    - Title drift = Orenu's short title is NOT a substring of MDX's long title
      (the common pattern of Orenu having "Title" and MDX having "Title:
      Subtitle" is NOT drift; it's expected data-depth asymmetry).
    - DOI drift = both populated AND different (someone updated inconsistently).
    Venue + year are intentionally NOT checked: venue is rarely updated in
    place (more common: rename a journal entirely → a new row), and
    published_at vs print-issue-year are semantically different fields
    that Phase 1a doesn't reconcile (Orenu has no print-issue-year column;
    Phase 1b+ scope).
    """
    warnings: list[str] = []
    fm = mdx.frontmatter

    if not title_matches(orenu.title, fm.get("title", "")):
        warnings.append(
            f"    title:  Orenu={orenu.title!r}\n"
            f"            MDX  ={fm.get('title')!r}"
        )

    if orenu.doi and fm.get("doi") and orenu.doi != fm.get("doi"):
        warnings.append(
            f"    doi:    Orenu={orenu.doi!r}\n"
            f"            MDX  ={fm.get('doi')!r}"
        )

    return warnings


def run(content_dir: Path, apply: bool, conn=None, *, orenu_override: list[OrenuPublication] | None = None) -> int:
    """Returns exit code. Conn=None means use orenu_override (tests inject in-memory data)."""
    mode_label = "APPLY" if apply else "DRY-RUN"
    print(f"sync_publications.py [{mode_label}]")
    print(f"  content_dir = {content_dir}")

    if orenu_override is not None:
        orenu_pubs = orenu_override
    else:
        assert conn is not None
        orenu_pubs = fetch_public_publications(conn)

    mdx_pubs = read_mdx_files(content_dir)

    print(f"  Orenu public rows: {len(orenu_pubs)}")
    print(f"  MDX files:         {len(mdx_pubs)}")

    matched, unmatched_orenu, unmatched_mdx = match_pairs(orenu_pubs, mdx_pubs)
    print(f"  Matched pairs:     {len(matched)}")
    print(f"  Unmatched Orenu:   {len(unmatched_orenu)}")
    print(f"  Unmatched MDX:     {len(unmatched_mdx)}")

    exit_code = 0
    citation_updates = 0
    drift_warnings_total = 0

    for orenu, mdx in matched:
        new_cite = compute_citations_update(orenu, mdx)
        if new_cite is not None:
            citation_updates += 1
            current = mdx.frontmatter.get("citationsAt")
            print(f"\n  UPDATE citations [{mdx.path.name}]:")
            print(f"    current: {current}")
            print(f"    new:     {new_cite}")
            if apply:
                mdx.frontmatter["citationsAt"] = new_cite
                write_mdx(mdx.path, mdx.frontmatter, mdx.body)

        drifts = compute_drift_warnings(orenu, mdx)
        if drifts:
            drift_warnings_total += len(drifts)
            print(f"\n  DRIFT [{mdx.path.name}]:")
            for d in drifts:
                print(d)

    for op in unmatched_orenu:
        print(f"\n  STUB NEEDED — Orenu publication_id={op.publication_id}")
        print(f"    title = {op.title!r}")
        print(f"    No matching MDX file in {content_dir}.")
        print(f"    Action: create an MDX file with the canonical Orenu title + frontmatter before next sync.")
        exit_code = 1

    for mp in unmatched_mdx:
        print(f"\n  ORPHAN MDX — {mp.path.name}")
        print(f"    title = {mp.frontmatter.get('title')!r}")
        print(f"    No matching public Orenu row.")
        print(f"    Action: either flip the Orenu row's public_visibility = true, or move this MDX to an _archive/ path.")
        exit_code = 1

    print(f"\nSummary:")
    print(f"  Citation updates planned: {citation_updates}{' (written)' if apply and citation_updates else ''}")
    print(f"  Drift warnings (non-authoritative fields): {drift_warnings_total}")
    print(f"  Stubs needed:  {len(unmatched_orenu)}")
    print(f"  Orphan MDX:    {len(unmatched_mdx)}")

    if drift_warnings_total > 0:
        exit_code = 1

    return exit_code


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 1a Orenu → site publication sync")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write citation updates to disk (default: dry-run)",
    )
    parser.add_argument(
        "--content-dir",
        default=str(DEFAULT_CONTENT_DIR),
        help="Path to the publications content collection",
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
        conn = psycopg2.connect(db_url, application_name="sync-publications")
    except Exception as e:
        print(f"ERROR: cannot connect to Orenu Postgres: {e}", file=sys.stderr)
        sys.exit(2)

    try:
        exit_code = run(content_dir, args.apply, conn=conn)
    finally:
        conn.close()

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
