"""Tests for scripts/write_sync_ledger.py.

The load-bearing test is `test_unparseable_phase_never_claims_zero`: the whole
point of the ledger is that it must not turn a failed run into evidence of a
clean one.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
spec = importlib.util.spec_from_file_location(
    "write_sync_ledger", SCRIPTS / "write_sync_ledger.py"
)
wsl = importlib.util.module_from_spec(spec)
sys.modules["write_sync_ledger"] = wsl
spec.loader.exec_module(wsl)


CREDENTIALS_OUTPUT = """\
Orenu → site sync (credentials)
  MDX files:         14
  Matched pairs:     12
  Unmatched Orenu:   0
  Unmatched MDX:     2

Summary:
  Field updates planned: 0
  Drift warnings:        0
  Stubs needed:          0
  Orphan MDX:            2
"""

AWARDS_OUTPUT = """\
  MDX files:         8
  Matched pairs:     8

Summary:
  Drift warnings (title/org mismatch): 0
  Stubs needed:                        0
  Orphan MDX:                          0
  Note: Phase 3a is presence-aware ONLY — no fields auto-overwritten.
"""

COMMUNITY_OUTPUT = """\
  MDX files:         5
  Matched pairs:     5

Summary:
  Drift warnings (role/org mismatch): 0
  Stubs needed:                       0
  Orphan MDX:                         0
  Note: Phase 3b is presence-aware ONLY — no fields auto-overwritten.
"""

# As duas formas que só existem no sarah-rodovalho-site. O script é infra
# compartilhada entre os dois sites e deve permanecer idêntico nos dois repos,
# então as quatro formas reais são testadas aqui também.
PUBLICATIONS_OUTPUT = """\
  Matched pairs:     19

Summary:
  Citation updates planned: 0
  Drift warnings (non-authoritative fields): 0
  Stubs needed:  0
  Orphan MDX:    0
"""

ENGAGEMENTS_OUTPUT = """\
  Matched pairs:     6

Summary:
  Drift warnings (date misalignment > 30 days): 1
  Stubs needed:  0
  Orphan MDX:    0
  Note: Phase 1b is presence-aware ONLY — no fields auto-overwritten.
"""

LEDGER_SEED = """\
# Registro

**Última verificação:** _(ainda não executado)_

| Data (UTC) | Fontes conferidas | Divergências | Resultado | Execução |
|---|---|---|---|---|
"""


def test_parses_every_real_summary_shape_across_both_sites():
    """Each script words its summary differently; all five must parse.

    "Field updates planned" vs "Citation updates planned", and four different
    parentheticals after "Drift warnings". A wording drift here would silently
    downgrade a clean run to INDETERMINADO — loud, but still wrong.
    """
    for name, output, compared in [
        ("credentials", CREDENTIALS_OUTPUT, 12),
        ("awards", AWARDS_OUTPUT, 8),
        ("community", COMMUNITY_OUTPUT, 5),
        ("publications", PUBLICATIONS_OUTPUT, 19),
        ("engagements", ENGAGEMENTS_OUTPUT, 6),
    ]:
        phase = wsl.parse_phase(name, output, 0)
        assert phase.parsed, f"{name} should parse"
        assert phase.compared == compared


def test_citation_updates_are_counted_as_divergence():
    """The publications script says 'Citation updates planned', not 'Field'."""
    out = PUBLICATIONS_OUTPUT.replace(
        "Citation updates planned: 0", "Citation updates planned: 3"
    )
    phase = wsl.parse_phase("publications", out, 0)
    assert phase.parsed
    assert phase.divergences["updates"] == 3
    assert "⚠️" in wsl.render_row([phase], "2026-08-10", None)


def test_clean_run_reports_zero_and_totals():
    phases = [
        wsl.parse_phase("credentials", CREDENTIALS_OUTPUT.replace("Orphan MDX:            2", "Orphan MDX:            0"), 0),
        wsl.parse_phase("awards", AWARDS_OUTPUT, 0),
        wsl.parse_phase("community", COMMUNITY_OUTPUT, 0),
    ]
    row = wsl.render_row(phases, "2026-08-10", "https://example/run/1")
    assert "✅ sem divergência" in row
    assert "**25**" in row  # 12 + 8 + 5
    assert "**0**" in row


def test_divergence_is_surfaced_with_detail():
    phases = [wsl.parse_phase("credentials", CREDENTIALS_OUTPUT, 0)]
    row = wsl.render_row(phases, "2026-08-10", None)
    assert "⚠️ divergência para revisar" in row
    assert "orphans 2" in row


@pytest.mark.parametrize(
    "output",
    [
        "",  # script crashed before printing anything
        "Traceback (most recent call last):\nRuntimeError: no DB\n",
        "  Matched pairs:     12\n",  # counted, but no Summary block
        "Summary:\n  Drift warnings: 0\n",  # partial Summary block
    ],
)
def test_unparseable_phase_never_claims_zero(output):
    """A run we could not read must NOT read as a clean run.

    This is the property the whole file exists for: `0` means checked-and-
    found-nothing, `?` means could-not-tell, and collapsing them would let a
    broken sync masquerade as evidence that the §4 gate was exercised.
    """
    phase = wsl.parse_phase("credentials", output, 2)
    assert not phase.parsed
    assert phase.divergence_total is None

    row = wsl.render_row([phase], "2026-08-10", None)
    assert "INDETERMINADO" in row
    assert "não apurado" in row
    assert "✅" not in row
    assert "**0**" not in row


def test_one_bad_phase_poisons_the_whole_row():
    """Two clean phases must not average away a third that failed."""
    phases = [
        wsl.parse_phase("credentials", CREDENTIALS_OUTPUT, 0),
        wsl.parse_phase("awards", AWARDS_OUTPUT, 0),
        wsl.parse_phase("community", "", 2),
    ]
    row = wsl.render_row(phases, "2026-08-10", None)
    assert "INDETERMINADO" in row
    assert "✅" not in row


def test_newest_row_goes_on_top_and_refreshes_the_glance_line():
    out = wsl.update_ledger(LEDGER_SEED, "| 2026-08-10 | a | b | c | d |", "2026-08-10")
    out = wsl.update_ledger(out, "| 2026-08-11 | e | f | g | h |", "2026-08-11")
    body = [ln for ln in out.splitlines() if ln.startswith("| 2026-")]
    assert body[0].startswith("| 2026-08-11")
    assert body[1].startswith("| 2026-08-10")
    assert "**Última verificação:** 2026-08-11" in out


def test_rerunning_the_same_day_replaces_instead_of_duplicating():
    """A manual re-run must not invent a second verification for one day."""
    out = wsl.update_ledger(LEDGER_SEED, "| 2026-08-10 | first | | | |", "2026-08-10")
    out = wsl.update_ledger(out, "| 2026-08-10 | second | | | |", "2026-08-10")
    rows = [ln for ln in out.splitlines() if ln.startswith("| 2026-08-10")]
    assert len(rows) == 1
    assert "second" in rows[0]


def test_history_is_capped():
    out = LEDGER_SEED
    for day in range(1, wsl.MAX_ROWS + 30):
        date = f"2026-{(day // 28) + 1:02d}-{(day % 28) + 1:02d}"
        out = wsl.update_ledger(out, f"| {date} | x | y | z | w |", date)
    assert len([ln for ln in out.splitlines() if ln.startswith("| 2026-")]) <= wsl.MAX_ROWS


def test_hand_edited_ledger_aborts_rather_than_guessing():
    with pytest.raises(SystemExit):
        wsl.update_ledger("# Registro\n\nsem tabela nenhuma\n", "| r |", "2026-08-10")
