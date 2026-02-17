#!/bin/bash
# ============================================================
# LongevityPath — Screening Guidelines Update Checker
# ============================================================
# Schedule: Run every 6 months (January & July)
#   Recommended cron: 0 9 15 1,7 * /path/to/check-screening-guidelines.sh
#
# WHY 6 MONTHS?
#   - USPSTF targets 5-year review per topic but publishes rolling
#     updates (4 new A/B recs in first half of 2025 alone)
#   - G-BA updates on an as-needed basis (no fixed cycle)
#   - EU Council: first implementation report due end of 2026,
#     then regular review every 4 years
#   - 6 months catches important changes without false alarms
#
# WHAT THIS SCRIPT DOES:
#   1. Fetches key guideline pages and saves timestamped snapshots
#   2. Compares against the previous snapshot
#   3. Reports any changes detected
#   4. Logs results to check-screening-guidelines.log
#
# PREREQUISITES:
#   - curl, diff, date (standard on macOS/Linux)
#   - Internet access
# ============================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SNAPSHOT_DIR="$SCRIPT_DIR/.guideline-snapshots"
LOG_FILE="$SCRIPT_DIR/check-screening-guidelines.log"
DATE_STAMP=$(date +"%Y-%m-%d")
CHANGES_FOUND=0

mkdir -p "$SNAPSHOT_DIR"

# Guideline sources to monitor
# Format: KEY|URL|DESCRIPTION
SOURCES=(
  "uspstf_ab|https://www.uspreventiveservicestaskforce.org/uspstf/recommendation-topics/uspstf-a-and-b-recommendations|USPSTF Grade A and B Recommendations"
  "uspstf_progress|https://www.uspreventiveservicestaskforce.org/uspstf/recommendation-topics/recommendations-in-progress|USPSTF Recommendations In Progress"
  "uspstf_news|https://www.uspreventiveservicestaskforce.org/uspstf/news|USPSTF News and Updates"
  "gba_screening|https://www.g-ba.de/themen/methodenbewertung/frueherkennung/|G-BA Screening Guidelines (German)"
  "gba_english|https://www.g-ba.de/english/|G-BA English Overview"
  "eu_screening|https://eur-lex.europa.eu/EN/legal-content/summary/promoting-cancer-screening-in-the-european-union.html|EU Council Cancer Screening Summary"
  "eu_consilium|https://www.consilium.europa.eu/en/press/press-releases/2022/12/09/council-updates-its-recommendation-to-screen-for-cancer/|EU Council Screening Press Release"
)

log() {
  echo "[${DATE_STAMP}] $1" | tee -a "$LOG_FILE"
}

fetch_and_compare() {
  local key="$1"
  local url="$2"
  local desc="$3"
  local current_file="$SNAPSHOT_DIR/${key}_current.txt"
  local previous_file="$SNAPSHOT_DIR/${key}_previous.txt"
  local diff_file="$SNAPSHOT_DIR/${key}_diff_${DATE_STAMP}.txt"

  # Fetch page content (text only, strip HTML)
  local content
  content=$(curl -sL --max-time 30 "$url" 2>/dev/null | \
    sed 's/<[^>]*>//g' | \
    sed 's/&nbsp;/ /g; s/&amp;/\&/g; s/&lt;/</g; s/&gt;/>/g' | \
    sed '/^[[:space:]]*$/d' | \
    head -500) || true

  if [ -z "$content" ]; then
    log "  WARNING: Could not fetch $desc ($url)"
    return
  fi

  # Save current snapshot
  echo "$content" > "$current_file"

  # Compare with previous if it exists
  if [ -f "$previous_file" ]; then
    if ! diff -q "$previous_file" "$current_file" > /dev/null 2>&1; then
      CHANGES_FOUND=$((CHANGES_FOUND + 1))
      log "  CHANGE DETECTED: $desc"
      log "  URL: $url"
      diff "$previous_file" "$current_file" > "$diff_file" 2>/dev/null || true
      local added=$(grep -c "^>" "$diff_file" 2>/dev/null || echo "0")
      local removed=$(grep -c "^<" "$diff_file" 2>/dev/null || echo "0")
      log "  Lines added: $added, removed: $removed"
      log "  Diff saved: $diff_file"
    else
      log "  No change: $desc"
    fi
  else
    log "  FIRST RUN: Baseline saved for $desc"
  fi

  # Rotate: current becomes previous
  cp "$current_file" "$previous_file"
}

# ============================================================
# Main
# ============================================================
log "=========================================="
log "Screening Guidelines Update Check"
log "=========================================="

for source in "${SOURCES[@]}"; do
  IFS='|' read -r key url desc <<< "$source"
  fetch_and_compare "$key" "$url" "$desc"
done

log "------------------------------------------"
if [ "$CHANGES_FOUND" -gt 0 ]; then
  log "RESULT: $CHANGES_FOUND source(s) changed since last check."
  log "ACTION REQUIRED: Review diffs in $SNAPSHOT_DIR"
  log ""
  log "Files that need updating if guidelines changed:"
  log "  1. index.html — SCREENING_GUIDELINES object (line ~588)"
  log "     - Update age ranges, frequencies, or add/remove screenings"
  log "  2. medical-evidence.html — FAQ cards for each system"
  log "     - q-system-de, q-system-us, q-system-eu, q-system-other"
  log "     - Per-screening FAQ cards (q-bp, q-lipid, etc.)"
  log "  3. If a new screening type is added:"
  log "     - Add entry to SCREENING_GUIDELINES in index.html"
  log "     - Add new FAQ card in medical-evidence.html"
  log "     - Add helpLink to the new screening entry"
else
  log "RESULT: No changes detected. All guidelines up to date."
fi

log "=========================================="
log ""

# Exit with code 1 if changes found (useful for CI/cron alerting)
exit $CHANGES_FOUND
