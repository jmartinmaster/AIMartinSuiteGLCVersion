#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="$ROOT_DIR/docs/ai-delegation/archive/smoke-test-logs"
EDITOR_CMD="${EDITOR:-nano}"

LABEL="${1:-manual}"
LABEL="$(printf '%s' "$LABEL" | tr '[:upper:]' '[:lower:]' | tr ' ' '_' | tr -cd 'a-z0-9_-')"
if [[ -z "$LABEL" ]]; then
  LABEL="manual"
fi

STAMP="$(date +%Y%m%d_%H%M%S)"
NOTE_PATH="$OUT_DIR/manual_test_notes_${STAMP}_${LABEL}.md"

mkdir -p "$OUT_DIR"

cat > "$NOTE_PATH" <<EOF
# Manual Test Notes

- Date: $(date -Iseconds)
- Area: $LABEL
- Branch: $(git -C "$ROOT_DIR" rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)

## Goal

- 

## Steps Run

1. 

## Expected Result

- 

## Actual Result

- 

## Pass/Fail

- [ ] Pass
- [ ] Fail
- [ ] Partial

## Oddities / Follow-up

- 

## Files / Context

- 
EOF

echo "Created: $NOTE_PATH"
exec "$EDITOR_CMD" "$NOTE_PATH"