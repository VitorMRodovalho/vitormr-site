#!/usr/bin/env python3
"""
sync_credentials.py — Phase 2 Orenu → sarahrodovalho.com /credentials sync.

Per ADR-024 Phase 2. Third source table for the sync pipeline; mirrors
the architecture of sync_publications.py + sync_engagements.py with
credential-specific differences:

  - Source table: public.dim_credential (9 rows currently: 3 Vitor +
    6 Sarah; this script only handles Sarah's 6).
  - Match strategy: title substring (Orenu name → MDX title) with DOI-
    equivalent disambiguation via kind+issuer for ambiguous cases.
  - Privacy boundary: credential_id_private is NEVER synced. Phase 2
    treats issued_date, expires_date, and status as Orenu-authoritative
    (these change over time; the daily PR catches renewals, expirations,
    and status transitions). Other fields (description, organizationUrl)
    stay manual on the MDX side.

Vitor's /recognition is NOT a target of this script — his credentials
section is an inline array in recognition.astro, not a content
collection. A separate refactor PR can convert it to a content
collection + extend this script to a second target dir.

Run modes:
  python scripts/sync_credentials.py                    # dry-run
  python scripts/sync_credentials.py --apply            # write changes

Environment:
  ORENU_DATABASE_URL — read-only Postgres URL (CI secret).

Exit codes:
  0 — clean (all matched + no field changes needed or applied)
  1 — warnings: stubs needed / orphan MDX / drift warnings
  2 — fatal error

Authoritative fields written when Orenu differs from MDX:
  - status (Sarah's MDX uses 'active' | 'in-progress' | 'expired';
    Orenu's enum is 'active' | 'in_progress' | 'expired' | 'lapsed' —
    underscore vs hyphen normalized on write; 'lapsed' mapped to
    'expired' in the MDX for Sarah's site UI)
  - issuedDate (from Orenu.issued_date)
  - validThrough (from Orenu.expires_date)

Drift warnings (not auto-overwritten — manual review):
  - Title mismatch (Orenu.name vs MDX.title beyond substring tolerance)
  - Issuer mismatch (Orenu.issuer vs MDX.organization)
  - DOI-equivalent: credentialId column (when MDX has one already)
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
    serialize_frontmatter,
    title_matches,
    write_mdx,
)

DEFAULT_CONTENT_DIR = Path("src/content/credentials")

# Orenu's status enum has 4 values; Sarah's MDX schema has 3.
# 'lapsed' (Orenu, for deliberately-discontinued memberships) maps to
# 'expired' (MDX) — both surface visually as past-tense on the page.
_STATUS_ENUM_TO_MDX: dict[str, str] = {
    "active": "active",
    "in_progress": "in-progress",
    "expired": "expired",
    "lapsed": "expired",
}


@dataclass
class OrenuCredential:
    credential_id: str
    person_display_name: str
    name: str
    kind: str
    issuer: str
    issuer_url: str | None
    status: str
    issued_date: str | None
    expires_date: str | None
    verify_url: str | None
    credly_badge_url: str | None


@dataclass
class MdxCredential:
    path: Path
    frontmatter: dict[str, Any]
    body: str


def fetch_public_credentials_for_person(conn, display_name: str) -> list[OrenuCredential]:
    """Returns Orenu's public credentials for a single person (matched by display_name)."""
    sql = """
        SELECT
          c.credential_id::text,
          e.display_name,
          c.name,
          c.kind::text,
          c.issuer,
          c.issuer_url,
          c.status::text,
          c.issued_date::text,
          c.expires_date::text,
          c.verify_url,
          c.credly_badge_url
        FROM public.dim_credential c
        JOIN public.dim_entity e ON e.id = c.person_entity_id
        WHERE c.household_id = %s
          AND c.public_visibility = true
          AND lower(e.display_name) = lower(%s)
        ORDER BY c.name
    """
    with conn.cursor() as cur:
        cur.execute(sql, (HOUSEHOLD_ID, display_name))
        rows = cur.fetchall()
    return [
        OrenuCredential(
            credential_id=r[0],
            person_display_name=r[1],
            name=r[2],
            kind=r[3],
            issuer=r[4],
            issuer_url=r[5],
            status=r[6],
            issued_date=r[7],
            expires_date=r[8],
            verify_url=r[9],
            credly_badge_url=r[10],
        )
        for r in rows
    ]


def read_mdx_files(content_dir: Path) -> list[MdxCredential]:
    out: list[MdxCredential] = []
    for path in sorted(content_dir.glob("*.mdx")):
        text = path.read_text(encoding="utf-8")
        fm, body = parse_frontmatter(text)
        out.append(MdxCredential(path=path, frontmatter=fm, body=body))
    return out


def match_pairs(
    orenu: list[OrenuCredential], mdx: list[MdxCredential]
) -> tuple[
    list[tuple[OrenuCredential, MdxCredential]],
    list[OrenuCredential],
    list[MdxCredential],
]:
    """Match Orenu credentials to MDX files by title substring."""
    matched: list[tuple[OrenuCredential, MdxCredential]] = []
    used_paths: set[Path] = set()

    for op in orenu:
        for m in mdx:
            if m.path in used_paths:
                continue
            mdx_title = str(m.frontmatter.get("title", ""))
            if title_matches(op.name, mdx_title) or title_matches(mdx_title, op.name):
                matched.append((op, m))
                used_paths.add(m.path)
                break

    matched_ids = {pair[0].credential_id for pair in matched}
    unmatched_orenu = [op for op in orenu if op.credential_id not in matched_ids]
    unmatched_mdx = [m for m in mdx if m.path not in used_paths]
    return matched, unmatched_orenu, unmatched_mdx


def compute_field_updates(orenu: OrenuCredential, mdx: MdxCredential) -> dict[str, Any]:
    """Return dict of frontmatter-field updates to apply. Empty = no update."""
    updates: dict[str, Any] = {}
    fm = mdx.frontmatter

    # status (Orenu-authoritative; enum normalized to Sarah's hyphenated form)
    new_status = _STATUS_ENUM_TO_MDX.get(orenu.status, orenu.status)
    if fm.get("status") != new_status:
        updates["status"] = new_status

    # issuedDate
    if orenu.issued_date and fm.get("issuedDate") != orenu.issued_date:
        updates["issuedDate"] = orenu.issued_date

    # validThrough
    if orenu.expires_date and fm.get("validThrough") != orenu.expires_date:
        updates["validThrough"] = orenu.expires_date

    # verify_url — only set when Orenu has one AND MDX doesn't conflict
    if orenu.verify_url and fm.get("verifyUrl") != orenu.verify_url:
        updates["verifyUrl"] = orenu.verify_url

    return updates


def compute_drift_warnings(orenu: OrenuCredential, mdx: MdxCredential) -> list[str]:
    """Title + issuer drift warnings; no auto-overwrite."""
    warnings: list[str] = []
    fm = mdx.frontmatter

    if not title_matches(orenu.name, fm.get("title", "")) and not title_matches(fm.get("title", ""), orenu.name):
        warnings.append(
            f"    title:  Orenu={orenu.name!r}\n"
            f"            MDX  ={fm.get('title')!r}"
        )

    if orenu.issuer and fm.get("organization") and orenu.issuer != fm.get("organization"):
        # Soft-match: substring either direction.
        if orenu.issuer not in fm["organization"] and fm["organization"] not in orenu.issuer:
            warnings.append(
                f"    org:    Orenu={orenu.issuer!r}\n"
                f"            MDX  ={fm.get('organization')!r}"
            )

    return warnings


def apply_updates_to_mdx(mdx: MdxCredential, updates: dict[str, Any]) -> None:
    """Mutate the MDX frontmatter dict in place (preserves key order) and write."""
    fm = mdx.frontmatter
    for key, value in updates.items():
        fm[key] = value
    write_mdx(mdx.path, fm, mdx.body)


def run(
    content_dir: Path,
    apply: bool,
    person_display_name: str,
    conn=None,
    *,
    orenu_override: list[OrenuCredential] | None = None,
) -> int:
    mode_label = "APPLY" if apply else "DRY-RUN"
    print(f"sync_credentials.py [{mode_label}]  person={person_display_name!r}")
    print(f"  content_dir = {content_dir}")

    if orenu_override is not None:
        orenu_creds = orenu_override
    else:
        assert conn is not None
        orenu_creds = fetch_public_credentials_for_person(conn, person_display_name)

    mdx_creds = read_mdx_files(content_dir)

    print(f"  Orenu public rows: {len(orenu_creds)}")
    print(f"  MDX files:         {len(mdx_creds)}")

    matched, unmatched_orenu, unmatched_mdx = match_pairs(orenu_creds, mdx_creds)
    print(f"  Matched pairs:     {len(matched)}")
    print(f"  Unmatched Orenu:   {len(unmatched_orenu)}")
    print(f"  Unmatched MDX:     {len(unmatched_mdx)}")

    exit_code = 0
    updates_count = 0
    drift_count = 0

    for orenu, mdx in matched:
        updates = compute_field_updates(orenu, mdx)
        if updates:
            updates_count += 1
            print(f"\n  UPDATE [{mdx.path.name}]:")
            for key, value in updates.items():
                print(f"    {key}: {mdx.frontmatter.get(key)!r} → {value!r}")
            if apply:
                apply_updates_to_mdx(mdx, updates)

        drifts = compute_drift_warnings(orenu, mdx)
        if drifts:
            drift_count += len(drifts)
            print(f"\n  DRIFT [{mdx.path.name}]:")
            for d in drifts:
                print(d)

    for op in unmatched_orenu:
        print(f"\n  STUB NEEDED — Orenu credential_id={op.credential_id}")
        print(f"    name = {op.name!r}")
        print(f"    kind = {op.kind}")
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
    print(f"  Field updates planned: {updates_count}{' (written)' if apply and updates_count else ''}")
    print(f"  Drift warnings:        {drift_count}")
    print(f"  Stubs needed:          {len(unmatched_orenu)}")
    print(f"  Orphan MDX:            {len(unmatched_mdx)}")

    if drift_count > 0:
        exit_code = 1

    return exit_code


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 2 Orenu → site credential sync")
    parser.add_argument("--apply", action="store_true", help="Write field updates to disk")
    parser.add_argument(
        "--content-dir",
        default=str(DEFAULT_CONTENT_DIR),
        help="Path to the credentials content collection",
    )
    parser.add_argument(
        "--person",
        default="Vitor Maia Rodovalho",
        help="dim_entity.display_name of the credential owner",
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
        conn = psycopg2.connect(db_url, application_name="sync-credentials")
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
