#!/usr/bin/env bash
# PII scan — blocks commits that contain blacklisted patterns.
#
# Per ADR-023 §D8 (in rodovalho-finance/decisions/). Site repo is public;
# this hook is the last line of defense against accidentally committing
# household-sensitive data (USCIS receipts, SSN, CPF, addresses, etc.).
#
# Run modes:
#   - default: scan staged files (git diff --cached)
#   - --all:   scan whole working tree (full audit)
#   - --files <path...>: scan specific files (used by pre-commit hook)
#
# Patterns are matched against staged content only — extracted via
# `git diff --cached -U0`. False positives can be bypassed via
# `git commit --no-verify` (but log it; we want to know).

set -euo pipefail

# shellcheck disable=SC2155
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly RED='\033[0;31m'
readonly YELLOW='\033[1;33m'
readonly GREEN='\033[0;32m'
readonly NC='\033[0m' # no color

# Patterns. Each line: <severity>|<label>|<regex>
# Severity: BLOCK = abort commit; WARN = print warning, allow commit.
read -r -d '' PATTERNS <<'EOF' || true
BLOCK|USCIS receipt number|[A-Z]{3}[0-9]{10}
BLOCK|SSN (US Social Security Number — dashed)|\b[0-9]{3}-[0-9]{2}-[0-9]{4}\b
BLOCK|Brazilian CPF (formatted)|\b[0-9]{3}\.[0-9]{3}\.[0-9]{3}-[0-9]{2}\b
BLOCK|Personal phone (US format with country code)|\+1[[:space:]]?\(?[0-9]{3}\)?[[:space:]-]?[0-9]{3}[[:space:]-]?[0-9]{4}
BLOCK|Brazilian CNPJ|\b[0-9]{2}\.[0-9]{3}\.[0-9]{3}/[0-9]{4}-[0-9]{2}\b
BLOCK|vitor.rodovalho personal outlook|vitor\.rodovalho@outlook\.com
BLOCK|vitor.rodovalho personal gmail|vitor\.rodovalho@gmail\.com
BLOCK|vitorodovalho personal gmail|vitorodovalho@gmail\.com
WARN|Currency above $100k (potentially sensitive)|\$[0-9]{1,3}(,?[0-9]{3}){2,}
WARN|Currency in BRL above R$50k|R\$[[:space:]]*[0-9]{1,3}(\.?[0-9]{3}){2,}

# Note: bare digit sequences (9 digits = SSN no-dashes; 11 digits = CPF no-dashes) NOT included — too noisy (false-positive on timestamps, order IDs, etc.). Formatted versions cover the realistic accident-paste case.
EOF

# Files to scan: from $@ if --files; else from staging
mode="staged"
files=()
if [[ "${1:-}" == "--all" ]]; then
  mode="all"
elif [[ "${1:-}" == "--files" ]]; then
  shift
  mode="files"
  files=("$@")
fi

case "$mode" in
  staged)
    mapfile -t files < <(git diff --cached --name-only --diff-filter=ACMR | grep -vE '\.(png|jpg|jpeg|gif|webp|svg|ico|woff|woff2|ttf|otf|pdf|zip|gz)$' || true)
    ;;
  all)
    mapfile -t files < <(git ls-files | grep -vE '\.(png|jpg|jpeg|gif|webp|svg|ico|woff|woff2|ttf|otf|pdf|zip|gz)$' || true)
    ;;
  files)
    : # already populated
    ;;
esac

# Exempt test fixtures — they intentionally contain PII patterns to verify
# that the scanner blocks them. Self-test runs via tests/pii-scan.test.sh.
exempt=()
for f in "${files[@]}"; do
  case "$f" in
    tests/pii-scan.test.sh) ;;
    *) exempt+=("$f") ;;
  esac
done
files=("${exempt[@]}")

if [[ ${#files[@]} -eq 0 ]]; then
  echo "PII scan: no files to scan, skipping."
  exit 0
fi

found_block=0
found_warn=0
matches=()

while IFS='|' read -r severity label regex; do
  [[ -z "$severity" ]] && continue
  for f in "${files[@]}"; do
    [[ -f "$f" ]] || continue
    # Use grep -E with line numbers; suppress binary files
    if grep -EnHI "$regex" "$f" 2>/dev/null; then
      matches+=("$severity|$label|$f")
      if [[ "$severity" == "BLOCK" ]]; then
        found_block=1
      else
        found_warn=1
      fi
    fi
  done
done <<< "$PATTERNS"

if [[ $found_block -eq 1 ]]; then
  echo
  echo -e "${RED}✗ PII scan FAILED.${NC} BLOCK-level patterns matched in staged content."
  echo "If a match is a false positive, you can override with: git commit --no-verify"
  echo "But please log the override in the PR description so we can refine the regex."
  echo
  exit 1
fi

if [[ $found_warn -eq 1 ]]; then
  echo
  echo -e "${YELLOW}⚠ PII scan: warnings emitted${NC} (high-value currency mentioned)."
  echo "If intentional (e.g., public project budget already on LinkedIn), proceed."
  echo
fi

echo -e "${GREEN}✓ PII scan passed.${NC} No blacklisted patterns in scope."
exit 0
