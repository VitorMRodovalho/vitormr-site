#!/usr/bin/env bash
# Smoke test for scripts/pii-scan.sh.
# Exit 0 = all assertions pass; non-zero = a test broke.

set -euo pipefail

SCRIPT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/scripts/pii-scan.sh"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

cd "$TMP"
git init -q

assert_blocks() {
  local label="$1"
  local content="$2"
  local file="${TMP}/test-${RANDOM}.md"
  echo "$content" > "$file"
  if bash "$SCRIPT" --files "$file" >/dev/null 2>&1; then
    echo "FAIL: $label — expected BLOCK but scan passed"
    echo "  content: $content"
    return 1
  fi
  echo "  ✓ $label blocked"
}

assert_passes() {
  local label="$1"
  local content="$2"
  local file="${TMP}/test-${RANDOM}.md"
  echo "$content" > "$file"
  if ! bash "$SCRIPT" --files "$file" >/dev/null 2>&1; then
    echo "FAIL: $label — expected pass but scan blocked"
    echo "  content: $content"
    return 1
  fi
  echo "  ✓ $label allowed"
}

echo "Running PII scan smoke tests..."

# Should BLOCK
assert_blocks "USCIS receipt format" "Case SRC2390041997 in 2023."
assert_blocks "SSN dashed" "SSN: 123-45-6789"
assert_blocks "CPF formatted" "CPF: 123.456.789-01"
assert_blocks "Personal outlook" "Contact: vitor.rodovalho@outlook.com"
assert_blocks "US phone with country code" "Phone: +1 267-874-8329"

# Should PASS (allowed content)
assert_passes "Public name" "Vitor M. Rodovalho is a Senior Cost Manager at Linesight."
assert_passes "Professional email on own domain" "Contact: vitor@vitormr.dev"
assert_passes "Public LinkedIn slug" "linkedin.com/in/vitor-rodovalho-pmp"
assert_passes "Public GitHub" "github.com/VitorMRodovalho"
assert_passes "City only (no street)" "Based in Leesburg, VA."
assert_passes "Public project URL" "https://meridianiq.vitormr.dev"
assert_passes "Generic 9-digit not SSN-shaped" "Order #ABC-200000000"

echo
echo "All smoke tests passed."
