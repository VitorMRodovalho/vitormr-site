#!/usr/bin/env python3
"""Write a dated verification record for each Orenu → site sync run.

Why this exists (read before changing it)
-----------------------------------------
The sync workflow is zero-churn by design: when every script is a no-op, no
file changes and no PR. In a repo whose only recurring writer is that
workflow, zero-churn guarantees zero commits — and GitHub disables a
scheduled workflow after 60 days of *repository* inactivity. So the
mechanism's success criterion is what kills it. That already happened once.

But the reason to write a record is NOT the 60-day clock. A heartbeat that
only proves "something ran" would fix the symptom and leave the real gap:
`docs/personal-sites-integration-contract.md` §4 defines a MANDATORY
non-contradiction gate against the Orenu evidence base, and nothing in this
repo records when that gate was last exercised. This ledger is the artifact
that gate presupposes. Keeping the repo alive is a side effect.

What a row DOES assert
----------------------
On date D, the sync compared N Orenu rows against N site MDX files and found
K divergences (drift / stubs / orphans / field updates). That covers legs
1, 2 and 4 of §4 — titles/dates/employers, awards & credentials, and the
"no site fact without an Orenu row" rule.

What a row does NOT assert
--------------------------
Leg 3 of §4 — the OPSEC rule about quantitative immigration claims in public
copy and commit messages — is NOT machine-checked here. Nothing in the sync
reads prose. A row is silent about it on purpose; do not read it as cover.

The property that matters most
------------------------------
A row must never claim "zero divergences" when it could not tell. An
unparseable phase yields `?`, and the run is marked INDETERMINADO. Silent
truncation turning into a false claim of completeness is exactly the failure
this file is meant to prevent.
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from dataclasses import dataclass
from pathlib import Path

# The three scripts word their summaries differently for the same concepts
# ("Drift warnings:" vs "Drift warnings (title/org mismatch):"), so each
# pattern tolerates a parenthetical before the colon.
COMPARED_RE = re.compile(r"^\s*Matched pairs:\s+(\d+)\s*$", re.M)
DIVERGENCE_RES = {
    # "Field updates planned" (credentials) / "Citation updates planned"
    # (publications) — same concept, different wording per script.
    "updates": re.compile(r"^\s*(?:Field|Citation) updates planned:\s+(\d+)", re.M),
    "drift": re.compile(r"^\s*Drift warnings(?:\s*\([^)]*\))?:\s+(\d+)", re.M),
    "stubs": re.compile(r"^\s*Stubs needed:\s+(\d+)", re.M),
    "orphans": re.compile(r"^\s*Orphan MDX:\s+(\d+)", re.M),
}

TABLE_HEADER = "| Data (UTC) | Fontes conferidas | Divergências | Resultado | Execução |"
TABLE_SEP = "|---|---|---|---|---|"
LAST_RUN_PREFIX = "**Última verificação:**"
MAX_ROWS = 200  # ~6 meses de execuções diárias


@dataclass
class Phase:
    name: str
    compared: int | None
    divergences: dict[str, int] | None
    exit_code: int

    @property
    def parsed(self) -> bool:
        return self.compared is not None and self.divergences is not None

    @property
    def divergence_total(self) -> int | None:
        if self.divergences is None:
            return None
        return sum(self.divergences.values())


def parse_phase(name: str, output: str, exit_code: int) -> Phase:
    """Parse one script's stdout. Returns unparsed counts as None, never 0.

    The distinction is the whole point: `0` means "checked, found nothing",
    `None` means "could not tell". Collapsing the two would let a crashed run
    read as a clean one.
    """
    compared_m = COMPARED_RE.search(output)
    compared = int(compared_m.group(1)) if compared_m else None

    divergences: dict[str, int] = {}
    for key, pattern in DIVERGENCE_RES.items():
        m = pattern.search(output)
        if m:
            divergences[key] = int(m.group(1))

    # The "updates planned" line only exists in the credentials and
    # publications scripts, so its absence is normal. The other three must all
    # be present, or we did not read a real summary block.
    required = {"drift", "stubs", "orphans"}
    if not required.issubset(divergences):
        return Phase(name, compared, None, exit_code)

    return Phase(name, compared, divergences, exit_code)


def render_row(phases: list[Phase], date: str, run_url: str | None) -> str:
    compared_parts, diverg_parts = [], []
    total_compared, total_diverg = 0, 0
    any_unparsed = False

    for p in phases:
        if p.parsed:
            compared_parts.append(f"{p.name} {p.compared}")
            total_compared += p.compared or 0
            total_diverg += p.divergence_total or 0
            detail = ", ".join(
                f"{k} {v}" for k, v in sorted(p.divergences.items()) if v
            )
            if detail:
                diverg_parts.append(f"{p.name}: {detail}")
        else:
            any_unparsed = True
            compared_parts.append(f"{p.name} ?")
            diverg_parts.append(f"{p.name}: não apurado (exit {p.exit_code})")

    if any_unparsed:
        compared_cell = " · ".join(compared_parts)
        diverg_cell = " · ".join(diverg_parts)
        result = "⛔ **INDETERMINADO** — ver execução"
    else:
        compared_cell = f"**{total_compared}** ({' · '.join(compared_parts)})"
        if total_diverg == 0:
            diverg_cell = "**0**"
            result = "✅ sem divergência"
        else:
            diverg_cell = f"**{total_diverg}** — {' · '.join(diverg_parts)}"
            result = "⚠️ divergência para revisar"

    run_cell = f"[log]({run_url})" if run_url else "—"
    return f"| {date} | {compared_cell} | {diverg_cell} | {result} | {run_cell} |"


def update_ledger(text: str, row: str, date: str) -> str:
    lines = text.splitlines()

    # Refresh the at-a-glance line in place; it is derived, never appended to.
    for i, line in enumerate(lines):
        if line.startswith(LAST_RUN_PREFIX):
            lines[i] = f"{LAST_RUN_PREFIX} {date}"
            break

    try:
        sep_idx = next(
            i for i, line in enumerate(lines) if line.strip() == TABLE_SEP
        )
    except StopIteration:
        raise SystemExit(
            f"ERRO: separador da tabela não encontrado no ledger ({TABLE_SEP!r}). "
            "O arquivo foi editado à mão ou está corrompido — abortando em vez de "
            "escrever no lugar errado."
        )

    body_start = sep_idx + 1
    body_end = body_start
    while body_end < len(lines) and lines[body_end].startswith("|"):
        body_end += 1

    body = lines[body_start:body_end]
    # Uma execução por dia: reescrever a linha do dia em vez de duplicar, para
    # que um re-run manual não invente uma segunda verificação.
    body = [ln for ln in body if not ln.startswith(f"| {date} |")]
    body.insert(0, row)
    del body[MAX_ROWS:]

    return "\n".join(lines[:body_start] + body + lines[body_end:]) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ledger", required=True, type=Path)
    ap.add_argument(
        "--phase",
        action="append",
        required=True,
        metavar="NAME:PATH:EXIT",
        help="Nome da fase, arquivo com o stdout dela e o exit code.",
    )
    ap.add_argument("--run-url", default=None)
    ap.add_argument("--date", default=None, help="AAAA-MM-DD (default: hoje, UTC).")
    args = ap.parse_args()

    date = args.date or dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")

    phases: list[Phase] = []
    for spec in args.phase:
        name, path_s, exit_s = spec.split(":", 2)
        path = Path(path_s)
        # Um arquivo ausente é "não apurado", nunca "nada a apurar".
        output = path.read_text(errors="replace") if path.exists() else ""
        phases.append(parse_phase(name, output, int(exit_s)))

    row = render_row(phases, date, args.run_url)
    ledger = args.ledger

    if not ledger.exists():
        raise SystemExit(f"ERRO: ledger não encontrado: {ledger}")

    ledger.write_text(update_ledger(ledger.read_text(), row, date))
    print(row)
    return 0


if __name__ == "__main__":
    sys.exit(main())
