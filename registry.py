#!/usr/bin/env python3
"""
LongevityPath Evidence Registry — SQLite Database Manager

CLI tool to manage the evidence map and server-side data.
Replaces the flat markdown tables with a queryable database.

DATA SEPARATION: This database stores ONLY scientific evidence + account/payment
data + anonymous analytics. User health data (answers, scores, goals) stays
client-side in localStorage/IndexedDB. See ARCHITECTURE.md §3.6.

Usage:
    python registry.py init                       Create DB + all tables
    python registry.py import-md FILE             Parse markdown → DB
    python registry.py query CLAIM [--dir +/-/±]  Studies for a claim
    python registry.py summary                    Claim Summary Index
    python registry.py export-summary             Write index to study-registry.md
    python registry.py stale                      Studies verified >6 months ago
    python registry.py add                        Interactive: add a study
    python registry.py anon-ingest FILE           Ingest anonymous analytics snapshot
    python registry.py anon-report                Aggregate anonymous analytics
    python registry.py stats                      Database statistics
"""

import argparse
import json
import os
import re
import sqlite3
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from textwrap import dedent

# DB lives in a writable directory. The mounted workspace may not support SQLite locking.
# Override with LONGEVITYPATH_DB env var if needed.
DB_PATH = Path(os.environ.get("LONGEVITYPATH_DB", Path(__file__).parent / "longevitypath.db"))
REGISTRY_MD = Path(__file__).parent / "study-registry.md"

# ─────────────────────────────────────────────
# Schema
# ─────────────────────────────────────────────

SCHEMA_SQL = dedent("""\
    -- Domain 1: Study Evidence

    CREATE TABLE IF NOT EXISTS studies (
        study_id         TEXT PRIMARY KEY,
        authors          TEXT NOT NULL,
        pub_year         INTEGER NOT NULL,
        doi              TEXT UNIQUE,
        study_type       TEXT NOT NULL,
        sample_size      TEXT,
        quality_score    REAL NOT NULL,
        relevance_mult   REAL NOT NULL,
        final_score      REAL NOT NULL,
        landmark         BOOLEAN DEFAULT 0,
        direction        TEXT NOT NULL,
        population       TEXT DEFAULT 'all',
        key_finding      TEXT,
        verified_date    TEXT,
        supercheck_date  TEXT,
        notes            TEXT,
        created_at       TEXT DEFAULT (datetime('now')),
        updated_at       TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS claims (
        claim_id    TEXT PRIMARY KEY,
        exposure    TEXT NOT NULL,
        outcome     TEXT NOT NULL,
        description TEXT
    );

    CREATE TABLE IF NOT EXISTS study_claims (
        study_id TEXT NOT NULL REFERENCES studies(study_id),
        claim_id TEXT NOT NULL REFERENCES claims(claim_id),
        PRIMARY KEY (study_id, claim_id)
    );

    CREATE TABLE IF NOT EXISTS evidence_usage (
        id        TEXT PRIMARY KEY,
        study_id  TEXT NOT NULL REFERENCES studies(study_id),
        page_file TEXT NOT NULL,
        card_id   TEXT NOT NULL,
        role      TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS removed_studies (
        id           TEXT PRIMARY KEY,
        authors      TEXT,
        pub_year     INTEGER,
        doi          TEXT,
        removed_from TEXT,
        replaced_by  TEXT,
        reason       TEXT,
        removed_date TEXT
    );

    -- Domain 2: Accounts & Payments (NO health data — see ARCHITECTURE.md §3.6)

    CREATE TABLE IF NOT EXISTS accounts (
        account_id   TEXT PRIMARY KEY,
        email        TEXT UNIQUE NOT NULL,
        display_name TEXT,
        plan         TEXT DEFAULT 'free',
        created_at   TEXT DEFAULT (datetime('now')),
        updated_at   TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS payments (
        payment_id   TEXT PRIMARY KEY,
        account_id   TEXT NOT NULL REFERENCES accounts(account_id),
        amount_cents INTEGER NOT NULL,
        currency     TEXT DEFAULT 'EUR',
        status       TEXT NOT NULL,
        provider_ref TEXT,
        created_at   TEXT DEFAULT (datetime('now'))
    );

    -- Domain 3: Anonymous Analytics (opt-in, non-identifiable)
    -- NEVER store anything linkable to a person. See ARCHITECTURE.md §3.6.

    CREATE TABLE IF NOT EXISTS anon_snapshots (
        snapshot_id   TEXT PRIMARY KEY,
        submitted_at  TEXT DEFAULT (datetime('now')),
        test_version  TEXT DEFAULT '1.0',
        age_bracket   TEXT,
        sex_bracket   TEXT,
        country_code  TEXT
    );

    CREATE TABLE IF NOT EXISTS anon_scores (
        id            TEXT PRIMARY KEY,
        snapshot_id   TEXT NOT NULL REFERENCES anon_snapshots(snapshot_id),
        category_key  TEXT NOT NULL,
        score_value   REAL NOT NULL,
        UNIQUE(snapshot_id, category_key)
    );

    CREATE TABLE IF NOT EXISTS anon_deltas (
        id              TEXT PRIMARY KEY,
        snapshot_id     TEXT NOT NULL REFERENCES anon_snapshots(snapshot_id),
        category_key    TEXT NOT NULL,
        previous_score  REAL,
        current_score   REAL NOT NULL,
        days_between    INTEGER,
        UNIQUE(snapshot_id, category_key)
    );

    -- Indexes

    CREATE INDEX IF NOT EXISTS idx_studies_doi ON studies(doi);
    CREATE INDEX IF NOT EXISTS idx_studies_score ON studies(final_score DESC);
    CREATE INDEX IF NOT EXISTS idx_study_claims_claim ON study_claims(claim_id);
    CREATE INDEX IF NOT EXISTS idx_usage_study ON evidence_usage(study_id);
    CREATE INDEX IF NOT EXISTS idx_usage_page ON evidence_usage(page_file, card_id);
    CREATE INDEX IF NOT EXISTS idx_accounts_email ON accounts(email);
    CREATE INDEX IF NOT EXISTS idx_payments_account ON payments(account_id);
    CREATE INDEX IF NOT EXISTS idx_anon_scores_snapshot ON anon_scores(snapshot_id);
    CREATE INDEX IF NOT EXISTS idx_anon_deltas_snapshot ON anon_deltas(snapshot_id);
""")


def get_db(db_path=None):
    """Open a connection with foreign keys enabled."""
    path = db_path or DB_PATH
    conn = sqlite3.connect(str(path))
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def uid():
    """Generate a short UUID."""
    return uuid.uuid4().hex[:12]


# ─────────────────────────────────────────────
# init
# ─────────────────────────────────────────────

def cmd_init(args):
    """Create database and all tables."""
    conn = get_db()
    conn.executescript(SCHEMA_SQL)
    conn.close()
    print(f"✓ Database initialized at {DB_PATH}")


# ─────────────────────────────────────────────
# import-md
# ─────────────────────────────────────────────

SECTION_PATTERN = re.compile(r'^## (.+)$')
TABLE_ROW_PATTERN = re.compile(r'^\|(.+)\|$')

# Map section names to evidence page file prefixes
SECTION_TO_PAGE = {
    "Sleep": "sleep",
    "Mindset": "mindset",
    "Wellbeing": "wellbeing",
    "Nutrition": "nutrition",
    "Protein": "protein",
    "VO2max": "vo2max",
    "Muscle Strength": "muscle",
}


def parse_claim_tags(claims_str):
    """Extract claim tags from a cell like '`sleep-duration→mortality`, `sleep-quality→health`'."""
    return re.findall(r'`([^`]+→[^`]+)`', claims_str)


def parse_used_in(used_in_str, section_page):
    """
    Parse 'sleep#q3(F), sleep#q1,q2' into list of (page_file, card_id, role).
    """
    usages = []
    if not used_in_str or used_in_str.strip() == '—':
        return usages

    # Split by comma, but be careful: "sleep#q1,q2" means q1 and q2 on same page
    # Pattern: page#cardlist(Role) or page#cardlist
    parts = re.split(r',\s*(?=[a-z])', used_in_str.strip())
    for part in parts:
        part = part.strip()
        if not part:
            continue

        # Extract role if present
        role_match = re.search(r'\(([FS])\)', part)
        role = 'featured' if role_match and role_match.group(1) == 'F' else 'supporting'
        part_clean = re.sub(r'\([FS]\)', '', part).strip()

        # Extract page and cards
        page_match = re.match(r'([a-z0-9]+)#(.+)', part_clean)
        if page_match:
            page = page_match.group(1)
            cards_str = page_match.group(2)
            # Cards can be comma-separated: q1,q2,q3
            cards = re.findall(r'q\d+', cards_str)
            page_file = f"{page}-evidence.html"
            for card in cards:
                usages.append((page_file, card, role))
        else:
            # Sometimes it's just card references without page prefix
            cards = re.findall(r'q\d+', part_clean)
            page_file = f"{section_page}-evidence.html" if section_page else "unknown.html"
            for card in cards:
                usages.append((page_file, card, role))

    return usages


def make_study_id(authors, year):
    """Generate a study_id like 'naghshi-2020-a1b2'."""
    # Clean author name: take first author surname
    author = authors.strip().strip('*').split(' ')[0].split('&')[0].strip()
    author = re.sub(r'[^a-zA-Z]', '', author).lower()
    return f"{author}-{year}-{uid()[:4]}"


def parse_score(score_str):
    """
    Parse score cell. The registry merged Quality×Relevance into a single 'Score' column.
    Most entries show final score directly (e.g., '12', '10', '8').
    Some may show partial relevance like '4.5'.
    Returns (quality_score, relevance_mult, final_score).
    """
    score_str = score_str.strip()
    try:
        final = float(score_str)
    except ValueError:
        final = 0.0

    # If score is a whole number ≤14, assume full relevance
    if final == int(final) and final <= 14:
        return (final, 1.0, final)
    elif final < 7:
        # Likely partial relevance: e.g., 4.5 = 9 × 0.5
        return (final * 2, 0.5, final)
    else:
        return (final, 1.0, final)


def parse_study_row(cells, section_name, section_page):
    """Parse a markdown table row into a study dict + claims + usages."""
    if len(cells) < 12:
        return None

    # Columns: Study | Age | DOI | Type | Sample | Score | LM | Dir | Pop | Claims | Used In | Notes
    authors_raw = cells[0].strip()
    age_str = cells[1].strip()
    doi = cells[2].strip()
    study_type = cells[3].strip()
    sample = cells[4].strip()
    score_str = cells[5].strip()
    lm = cells[6].strip()
    direction = cells[7].strip()
    population = cells[8].strip() or 'all'
    claims_str = cells[9].strip()
    used_in_str = cells[10].strip()
    notes = cells[11].strip() if len(cells) > 11 else ''

    # Skip header/separator rows
    if authors_raw.startswith('---') or authors_raw == 'Study' or not authors_raw:
        return None

    # Compute pub_year from age
    try:
        age = int(age_str)
        pub_year = 2026 - age
    except ValueError:
        pub_year = 2020  # fallback

    # Clean authors (remove italic markers)
    authors = authors_raw.strip('*').strip()

    # Parse score
    quality_score, relevance_mult, final_score = parse_score(score_str)

    # Landmark
    landmark = lm.upper() == 'Y'

    # Direction normalization
    dir_map = {'+': '+', '−': '−', '-': '−', '±': '±'}
    direction = dir_map.get(direction, direction)

    # DOI cleanup
    if doi and not doi.startswith('10.'):
        doi = None  # invalid

    study_id = make_study_id(authors, pub_year)

    study = {
        'study_id': study_id,
        'authors': authors,
        'pub_year': pub_year,
        'doi': doi if doi else None,
        'study_type': study_type,
        'sample_size': sample if sample else None,
        'quality_score': quality_score,
        'relevance_mult': relevance_mult,
        'final_score': final_score,
        'landmark': landmark,
        'direction': direction,
        'population': population,
        'key_finding': notes if notes else None,
        'verified_date': '2026-02',
        'supercheck_date': None,
        'notes': notes if notes else None,
    }

    claim_tags = parse_claim_tags(claims_str)
    usages = parse_used_in(used_in_str, section_page)

    return study, claim_tags, usages


def parse_removed_row(cells):
    """Parse a removed studies table row."""
    if len(cells) < 6:
        return None

    # Columns: Study | DOI | Removed From | Replaced By | Reason | Date
    authors = cells[0].strip()
    doi = cells[1].strip()
    removed_from = cells[2].strip()
    replaced_by = cells[3].strip()
    reason = cells[4].strip()
    removed_date = cells[5].strip()

    if authors.startswith('---') or authors == 'Study' or not authors:
        return None

    # Try to extract year from authors
    year_match = re.search(r'(\d{4})', authors)
    pub_year = int(year_match.group(1)) if year_match else None

    return {
        'id': uid(),
        'authors': authors,
        'pub_year': pub_year,
        'doi': doi if doi and doi != '—' else None,
        'removed_from': removed_from,
        'replaced_by': replaced_by if replaced_by and replaced_by != '—' else None,
        'reason': reason,
        'removed_date': removed_date,
    }


def cmd_import_md(args):
    """Parse study-registry.md and populate the database."""
    md_path = Path(args.file)
    if not md_path.exists():
        print(f"✗ File not found: {md_path}")
        sys.exit(1)

    conn = get_db()
    text = md_path.read_text(encoding='utf-8')
    lines = text.splitlines()

    current_section = None
    current_page = None
    in_removed = False
    studies_added = 0
    claims_added = set()
    usages_added = 0
    removed_added = 0

    # First pass: extract claim vocabulary to pre-populate claims table
    in_vocab = False
    for line in lines:
        if '## Claim Tag Vocabulary' in line:
            in_vocab = True
            continue
        if in_vocab and line.startswith('## '):
            break
        if in_vocab and line.startswith('|'):
            match = TABLE_ROW_PATTERN.match(line)
            if match:
                cells = [c.strip() for c in match.group(1).split('|')]
                if len(cells) >= 2:
                    tag = cells[0].strip().strip('`')
                    desc = cells[1].strip()
                    if '→' in tag and tag != 'Tag':
                        parts = tag.split('→', 1)
                        try:
                            conn.execute(
                                "INSERT OR IGNORE INTO claims (claim_id, exposure, outcome, description) VALUES (?, ?, ?, ?)",
                                (tag, parts[0], parts[1], desc)
                            )
                            claims_added.add(tag)
                        except sqlite3.IntegrityError:
                            pass

    # Second pass: parse study tables
    for line in lines:
        # Detect section headers
        sec_match = SECTION_PATTERN.match(line)
        if sec_match:
            section_name = sec_match.group(1).strip()
            if section_name in SECTION_TO_PAGE:
                current_section = section_name
                current_page = SECTION_TO_PAGE[section_name]
                in_removed = False
            elif 'Removed' in section_name:
                in_removed = True
                current_section = None
            else:
                current_section = None
                in_removed = False
            continue

        # Parse table rows
        if not line.startswith('|'):
            continue

        match = TABLE_ROW_PATTERN.match(line)
        if not match:
            continue

        cells = [c.strip() for c in match.group(1).split('|')]

        # Skip separator rows
        if cells and cells[0].startswith('---'):
            continue

        if in_removed:
            removed = parse_removed_row(cells)
            if removed:
                try:
                    conn.execute(
                        "INSERT OR IGNORE INTO removed_studies (id, authors, pub_year, doi, removed_from, replaced_by, reason, removed_date) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (removed['id'], removed['authors'], removed['pub_year'],
                         removed['doi'], removed['removed_from'], removed['replaced_by'],
                         removed['reason'], removed['removed_date'])
                    )
                    removed_added += 1
                except sqlite3.IntegrityError:
                    pass
            continue

        if current_section:
            result = parse_study_row(cells, current_section, current_page)
            if result:
                study, claim_tags, usages = result

                # Insert study
                try:
                    conn.execute(
                        """INSERT OR IGNORE INTO studies
                        (study_id, authors, pub_year, doi, study_type, sample_size,
                         quality_score, relevance_mult, final_score, landmark,
                         direction, population, key_finding, verified_date,
                         supercheck_date, notes)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (study['study_id'], study['authors'], study['pub_year'],
                         study['doi'], study['study_type'], study['sample_size'],
                         study['quality_score'], study['relevance_mult'], study['final_score'],
                         study['landmark'], study['direction'], study['population'],
                         study['key_finding'], study['verified_date'],
                         study['supercheck_date'], study['notes'])
                    )
                    studies_added += 1
                except sqlite3.IntegrityError as e:
                    # DOI conflict — study with same DOI already exists
                    print(f"  ⚠ Skipped duplicate: {study['authors']} {study['pub_year']} ({e})")
                    # Get existing study_id for claim/usage linking
                    if study['doi']:
                        row = conn.execute("SELECT study_id FROM studies WHERE doi = ?", (study['doi'],)).fetchone()
                        if row:
                            study['study_id'] = row['study_id']
                    continue

                # Link claims
                for tag in claim_tags:
                    # Ensure claim exists
                    if tag not in claims_added:
                        parts = tag.split('→', 1)
                        if len(parts) == 2:
                            conn.execute(
                                "INSERT OR IGNORE INTO claims (claim_id, exposure, outcome, description) VALUES (?, ?, ?, ?)",
                                (tag, parts[0], parts[1], '')
                            )
                            claims_added.add(tag)

                    try:
                        conn.execute(
                            "INSERT OR IGNORE INTO study_claims (study_id, claim_id) VALUES (?, ?)",
                            (study['study_id'], tag)
                        )
                    except sqlite3.IntegrityError:
                        pass

                # Link evidence usage
                for page_file, card_id, role in usages:
                    try:
                        conn.execute(
                            "INSERT OR IGNORE INTO evidence_usage (id, study_id, page_file, card_id, role) VALUES (?, ?, ?, ?, ?)",
                            (uid(), study['study_id'], page_file, card_id, role)
                        )
                        usages_added += 1
                    except sqlite3.IntegrityError:
                        pass

    conn.commit()
    conn.close()

    print(f"✓ Import complete:")
    print(f"  {studies_added} studies")
    print(f"  {len(claims_added)} claims")
    print(f"  {usages_added} evidence usages")
    print(f"  {removed_added} removed studies")


# ─────────────────────────────────────────────
# query
# ─────────────────────────────────────────────

def cmd_query(args):
    """Show all studies for a claim."""
    conn = get_db()
    claim = args.claim

    query = """
        SELECT s.authors, s.pub_year, s.study_type, s.final_score, s.landmark,
               s.direction, s.population, s.key_finding, s.doi
        FROM studies s
        JOIN study_claims sc ON s.study_id = sc.study_id
        WHERE sc.claim_id = ?
    """
    params = [claim]

    if args.dir:
        query += " AND s.direction = ?"
        params.append(args.dir)

    query += " ORDER BY s.final_score DESC"
    rows = conn.execute(query, params).fetchall()

    if not rows:
        # Try fuzzy match
        fuzzy = conn.execute(
            "SELECT claim_id FROM claims WHERE claim_id LIKE ?",
            (f"%{claim}%",)
        ).fetchall()
        if fuzzy:
            print(f"No exact match for '{claim}'. Did you mean:")
            for r in fuzzy:
                print(f"  • {r['claim_id']}")
        else:
            print(f"No studies found for claim '{claim}'")
        conn.close()
        return

    print(f"\n{'='*70}")
    print(f"  Claim: {claim}")
    dir_filter = f" (filtered: Dir {args.dir})" if args.dir else ""
    print(f"  {len(rows)} studies found{dir_filter}")
    print(f"{'='*70}\n")

    for r in rows:
        lm = " ★" if r['landmark'] else ""
        pop = f" [{r['population']}]" if r['population'] != 'all' else ""
        print(f"  {r['direction']}  {r['authors']} {r['pub_year']}  "
              f"({r['study_type']}, Score {r['final_score']:.0f}{lm}){pop}")
        if r['key_finding']:
            # Truncate long findings
            finding = r['key_finding'][:100]
            print(f"     → {finding}")
        if r['doi']:
            print(f"     DOI: {r['doi']}")
        print()

    conn.close()


# ─────────────────────────────────────────────
# summary
# ─────────────────────────────────────────────

def build_summary_data(conn):
    """Build claim summary index from database."""
    claims = conn.execute("SELECT claim_id FROM claims ORDER BY claim_id").fetchall()
    summary = []

    for claim_row in claims:
        cid = claim_row['claim_id']
        studies = conn.execute("""
            SELECT s.direction, s.final_score, s.authors, s.pub_year
            FROM studies s
            JOIN study_claims sc ON s.study_id = sc.study_id
            WHERE sc.claim_id = ?
            ORDER BY s.final_score DESC
        """, (cid,)).fetchall()

        if not studies:
            continue

        plus = [s for s in studies if s['direction'] == '+']
        minus = [s for s in studies if s['direction'] == '−']
        mixed = [s for s in studies if s['direction'] == '±']

        best_plus = f"{plus[0]['authors']} {plus[0]['pub_year']} ({plus[0]['final_score']:.0f})" if plus else '—'
        best_minus = f"{minus[0]['authors']} {minus[0]['pub_year']} ({minus[0]['final_score']:.0f})" if minus else '—'

        # Net direction
        if len(plus) > 0 and len(minus) == 0 and len(mixed) == 0:
            net = '+'
        elif len(minus) > 0 and len(plus) == 0:
            net = '−'
        elif len(mixed) > 0 and len(plus) == 0 and len(minus) == 0:
            net = '±'
        else:
            # Mixed — check which side has stronger evidence
            best_p = plus[0]['final_score'] if plus else 0
            best_m = minus[0]['final_score'] if minus else 0
            if best_p > best_m:
                net = '+ (contested)' if minus else '+'
            elif best_m > best_p:
                net = '− (contested)' if plus else '−'
            else:
                net = '±'

        # Confidence
        top_score = max(s['final_score'] for s in studies)
        has_landmark = any(True for s in studies)  # simplified
        if top_score >= 12:
            confidence = 'Strong'
        elif top_score >= 10:
            confidence = 'Moderate'
        else:
            confidence = 'Limited'

        # Evidence gap
        gap = ''
        if len(minus) == 0 and len(mixed) == 0 and len(plus) > 0:
            gap = 'Need contradicting study'
        elif len(minus) > 0 and len(plus) == 0:
            gap = 'Need supporting study'

        summary.append({
            'claim': cid,
            'n_plus': len(plus),
            'n_minus': len(minus),
            'n_mixed': len(mixed),
            'best_plus': best_plus,
            'best_minus': best_minus,
            'net': net,
            'confidence': confidence,
            'gap': gap,
        })

    return summary


def cmd_summary(args):
    """Print the Claim Summary Index."""
    conn = get_db()
    summary = build_summary_data(conn)
    conn.close()

    if not summary:
        print("No claims found. Run 'import-md' first.")
        return

    print(f"\n{'='*90}")
    print("  Claim Summary Index")
    print(f"{'='*90}\n")

    # Header
    print(f"  {'Claim':<35} {'#+':>3} {'#−':>3} {'#±':>3}  {'Net':<16} {'Confidence':<12} {'Gap'}")
    print(f"  {'─'*35} {'─'*3} {'─'*3} {'─'*3}  {'─'*16} {'─'*12} {'─'*25}")

    for s in summary:
        print(f"  {s['claim']:<35} {s['n_plus']:>3} {s['n_minus']:>3} {s['n_mixed']:>3}  "
              f"{s['net']:<16} {s['confidence']:<12} {s['gap']}")

    print(f"\n  Total: {len(summary)} claims, "
          f"{sum(s['n_plus'] for s in summary)} supporting, "
          f"{sum(s['n_minus'] for s in summary)} contradicting, "
          f"{sum(s['n_mixed'] for s in summary)} conditional\n")


# ─────────────────────────────────────────────
# export-summary
# ─────────────────────────────────────────────

def cmd_export_summary(args):
    """Write the Claim Summary Index back to study-registry.md."""
    conn = get_db()
    summary = build_summary_data(conn)
    conn.close()

    if not summary:
        print("No claims found. Run 'import-md' first.")
        return

    md_path = REGISTRY_MD
    if not md_path.exists():
        print(f"✗ {md_path} not found")
        return

    text = md_path.read_text(encoding='utf-8')

    # Build the new summary table
    lines = []
    lines.append("| Claim | #+ | #− | #± | Best+ | Best− | Net | Confidence | Gap? |")
    lines.append("|-------|----|----|-----|-------|-------|-----|------------|------|")

    for s in summary:
        lines.append(
            f"| `{s['claim']}` | {s['n_plus']} | {s['n_minus']} | {s['n_mixed']} | "
            f"{s['best_plus']} | {s['best_minus']} | {s['net']} | {s['confidence']} | {s['gap']} |"
        )

    new_table = '\n'.join(lines)

    # Find and replace the existing summary table
    # Pattern: from the header row to the next --- or ## section
    pattern = re.compile(
        r'(\| Claim \| #\+ \|.*?\n\|[-|\s]+\n)((?:\|.*\n)*)',
        re.MULTILINE
    )
    match = pattern.search(text)
    if match:
        text = text[:match.start()] + new_table + '\n' + text[match.end():]
        md_path.write_text(text, encoding='utf-8')
        print(f"✓ Claim Summary Index updated in {md_path} ({len(summary)} claims)")
    else:
        print("✗ Could not find Claim Summary Index table in study-registry.md")


# ─────────────────────────────────────────────
# stale
# ─────────────────────────────────────────────

def cmd_stale(args):
    """List studies with verified_date > 6 months old."""
    conn = get_db()
    cutoff = (datetime.now() - timedelta(days=180)).strftime('%Y-%m')

    rows = conn.execute("""
        SELECT authors, pub_year, verified_date, final_score, direction
        FROM studies
        WHERE verified_date < ? OR verified_date IS NULL
        ORDER BY verified_date ASC
    """, (cutoff,)).fetchall()

    conn.close()

    if not rows:
        print("✓ No stale studies. All verified within 6 months.")
        return

    print(f"\n⚠ {len(rows)} stale studies (verified before {cutoff}):\n")
    for r in rows:
        vdate = r['verified_date'] or 'never'
        print(f"  {r['authors']} {r['pub_year']}  (Score {r['final_score']:.0f}, Dir {r['direction']})  "
              f"Verified: {vdate}")
    print()


# ─────────────────────────────────────────────
# add (interactive)
# ─────────────────────────────────────────────

def cmd_add(args):
    """Interactively add a new study."""
    print("\n─── Add New Study ───\n")

    authors = input("Authors (e.g., 'Smith 2024'): ").strip()
    pub_year = int(input("Publication year: ").strip())
    doi = input("DOI (or blank): ").strip() or None
    study_type = input("Type (MA/SR/RCT/Cohort/etc.): ").strip()
    sample = input("Sample size: ").strip() or None
    quality = float(input("Quality score (0-14): ").strip())
    relevance = float(input("Relevance multiplier (1.0/0.5/0.0): ").strip())
    final = quality * relevance
    landmark = input("Landmark? (Y/N): ").strip().upper() == 'Y'
    direction = input("Direction (+/−/±): ").strip()
    population = input("Population (all/<65/>65/etc.): ").strip() or 'all'
    finding = input("Key finding: ").strip() or None

    # Claims
    print("\nEnter claim tags (comma-separated, e.g., 'protein→cancer, protein→mortality'):")
    claims_raw = input("> ").strip()
    claim_tags = [c.strip() for c in claims_raw.split(',') if '→' in c]

    # Used in
    print("\nUsed in (e.g., 'nutrition#q3(F), nutrition#q1' or '—'):")
    used_in_raw = input("> ").strip()

    study_id = make_study_id(authors, pub_year)

    conn = get_db()
    try:
        conn.execute(
            """INSERT INTO studies
            (study_id, authors, pub_year, doi, study_type, sample_size,
             quality_score, relevance_mult, final_score, landmark,
             direction, population, key_finding, verified_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (study_id, authors, pub_year, doi, study_type, sample,
             quality, relevance, final, landmark, direction, population,
             finding, datetime.now().strftime('%Y-%m'))
        )

        for tag in claim_tags:
            parts = tag.split('→', 1)
            if len(parts) == 2:
                conn.execute(
                    "INSERT OR IGNORE INTO claims (claim_id, exposure, outcome, description) VALUES (?, ?, ?, ?)",
                    (tag, parts[0], parts[1], '')
                )
                conn.execute(
                    "INSERT OR IGNORE INTO study_claims (study_id, claim_id) VALUES (?, ?)",
                    (study_id, tag)
                )

        # Parse and add usage
        if used_in_raw and used_in_raw != '—':
            usages = parse_used_in(used_in_raw, None)
            for page_file, card_id, role in usages:
                conn.execute(
                    "INSERT INTO evidence_usage (id, study_id, page_file, card_id, role) VALUES (?, ?, ?, ?, ?)",
                    (uid(), study_id, page_file, card_id, role)
                )

        conn.commit()
        print(f"\n✓ Added: {authors} {pub_year} → {study_id}")
        print(f"  Claims: {', '.join(claim_tags)}")
        print(f"  Score: {final:.1f} (Q{quality:.0f} × R{relevance}), Dir {direction}")

    except sqlite3.IntegrityError as e:
        print(f"\n✗ Error: {e}")
    finally:
        conn.close()


# ─────────────────────────────────────────────
# anon-ingest (anonymous analytics)
# ─────────────────────────────────────────────

def cmd_anon_ingest(args):
    """Ingest an anonymous analytics snapshot (from client opt-in).

    Expected JSON format (NO personal data):
    {
        "age_bracket": "30-39",
        "sex_bracket": "M",
        "country_code": "DE",
        "scores": {"nutrition": 7.2, "sleep": 6.1, ...},
        "deltas": {"nutrition": {"previous": 5.8, "current": 7.2, "days": 90}, ...}
    }
    """
    json_path = Path(args.file)
    if not json_path.exists():
        print(f"✗ File not found: {json_path}")
        sys.exit(1)

    data = json.loads(json_path.read_text(encoding='utf-8'))

    # Validate: reject anything that looks personal
    forbidden_keys = {'name', 'email', 'userName', 'user_name', 'phone', 'address', 'ip', 'device_id'}
    found = forbidden_keys.intersection(data.keys())
    if found:
        print(f"✗ REJECTED: payload contains personal data fields: {found}")
        print("  Anonymous snapshots must not contain identifiable information.")
        sys.exit(1)

    conn = get_db()
    snapshot_id = uid()

    conn.execute(
        """INSERT INTO anon_snapshots
        (snapshot_id, age_bracket, sex_bracket, country_code)
        VALUES (?, ?, ?, ?)""",
        (snapshot_id, data.get('age_bracket'), data.get('sex_bracket'),
         data.get('country_code'))
    )

    scores = data.get('scores', {})
    for cat, val in scores.items():
        conn.execute(
            "INSERT INTO anon_scores (id, snapshot_id, category_key, score_value) VALUES (?, ?, ?, ?)",
            (uid(), snapshot_id, cat, float(val))
        )

    deltas = data.get('deltas', {})
    for cat, d in deltas.items():
        conn.execute(
            "INSERT INTO anon_deltas (id, snapshot_id, category_key, previous_score, current_score, days_between) VALUES (?, ?, ?, ?, ?, ?)",
            (uid(), snapshot_id, cat,
             d.get('previous'), float(d['current']), d.get('days'))
        )

    conn.commit()
    conn.close()
    print(f"✓ Anonymous snapshot ingested: {snapshot_id}")
    print(f"  Scores: {len(scores)} categories")
    print(f"  Deltas: {len(deltas)} categories")


# ─────────────────────────────────────────────
# anon-report (aggregate analytics)
# ─────────────────────────────────────────────

def cmd_anon_report(args):
    """Show aggregate anonymous analytics."""
    conn = get_db()

    total = conn.execute("SELECT COUNT(*) as n FROM anon_snapshots").fetchone()['n']
    if total == 0:
        print("No anonymous snapshots yet.")
        conn.close()
        return

    print(f"\n{'='*60}")
    print(f"  Anonymous Analytics Report  ({total} snapshots)")
    print(f"{'='*60}\n")

    # Average scores per category
    rows = conn.execute("""
        SELECT category_key,
               COUNT(*) as n,
               ROUND(AVG(score_value), 1) as avg_score,
               ROUND(MIN(score_value), 1) as min_score,
               ROUND(MAX(score_value), 1) as max_score
        FROM anon_scores
        GROUP BY category_key
        ORDER BY avg_score DESC
    """).fetchall()

    if rows:
        print("  Category Averages:")
        print(f"  {'Category':<15} {'N':>5} {'Avg':>6} {'Min':>6} {'Max':>6}")
        print(f"  {'─'*15} {'─'*5} {'─'*6} {'─'*6} {'─'*6}")
        for r in rows:
            print(f"  {r['category_key']:<15} {r['n']:>5} {r['avg_score']:>6} "
                  f"{r['min_score']:>6} {r['max_score']:>6}")

    # Average improvement per category
    delta_rows = conn.execute("""
        SELECT category_key,
               COUNT(*) as n,
               ROUND(AVG(current_score - previous_score), 2) as avg_change,
               ROUND(AVG(days_between), 0) as avg_days
        FROM anon_deltas
        WHERE previous_score IS NOT NULL
        GROUP BY category_key
        ORDER BY avg_change DESC
    """).fetchall()

    if delta_rows:
        print(f"\n  Score Changes (returning users):")
        print(f"  {'Category':<15} {'N':>5} {'Avg Δ':>7} {'Avg Days':>9}")
        print(f"  {'─'*15} {'─'*5} {'─'*7} {'─'*9}")
        for r in delta_rows:
            sign = '+' if r['avg_change'] >= 0 else ''
            print(f"  {r['category_key']:<15} {r['n']:>5} {sign}{r['avg_change']:>6} "
                  f"{r['avg_days']:>9.0f}")

    print()
    conn.close()


# ─────────────────────────────────────────────
# stats
# ─────────────────────────────────────────────

def cmd_stats(args):
    """Show database statistics."""
    conn = get_db()

    studies = conn.execute("SELECT COUNT(*) as n FROM studies").fetchone()['n']
    claims = conn.execute("SELECT COUNT(*) as n FROM claims").fetchone()['n']
    links = conn.execute("SELECT COUNT(*) as n FROM study_claims").fetchone()['n']
    usages = conn.execute("SELECT COUNT(*) as n FROM evidence_usage").fetchone()['n']
    removed = conn.execute("SELECT COUNT(*) as n FROM removed_studies").fetchone()['n']
    accounts = conn.execute("SELECT COUNT(*) as n FROM accounts").fetchone()['n']
    snapshots = conn.execute("SELECT COUNT(*) as n FROM anon_snapshots").fetchone()['n']

    # Direction breakdown
    dir_plus = conn.execute("SELECT COUNT(*) as n FROM studies WHERE direction = '+'").fetchone()['n']
    dir_minus = conn.execute("SELECT COUNT(*) as n FROM studies WHERE direction = '−'").fetchone()['n']
    dir_mixed = conn.execute("SELECT COUNT(*) as n FROM studies WHERE direction = '±'").fetchone()['n']

    # Landmark count
    landmarks = conn.execute("SELECT COUNT(*) as n FROM studies WHERE landmark = 1").fetchone()['n']

    print(f"\n{'='*50}")
    print("  LongevityPath Database Statistics")
    print(f"{'='*50}\n")
    print(f"  Evidence Map:")
    print(f"    Studies:        {studies}")
    print(f"      Supporting:   {dir_plus}")
    print(f"      Contradicting:{dir_minus}")
    print(f"      Conditional:  {dir_mixed}")
    print(f"      Landmarks:    {landmarks}")
    print(f"    Claims:         {claims}")
    print(f"    Study↔Claim:    {links}")
    print(f"    Evidence usage: {usages}")
    print(f"    Removed:        {removed}")
    print(f"  Accounts:         {accounts}")
    print(f"  Anon. snapshots:  {snapshots}")
    print()

    conn.close()


# ─────────────────────────────────────────────
# CLI entry point
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='LongevityPath Evidence Registry — Database Manager',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    sub = parser.add_subparsers(dest='command', help='Available commands')

    # init
    sub.add_parser('init', help='Create database and all tables')

    # import-md
    p_import = sub.add_parser('import-md', help='Import from study-registry.md')
    p_import.add_argument('file', help='Path to study-registry.md')

    # query
    p_query = sub.add_parser('query', help='Query studies by claim')
    p_query.add_argument('claim', help='Claim tag (e.g., protein→cancer)')
    p_query.add_argument('--dir', help='Filter by direction (+/−/±)')

    # summary
    sub.add_parser('summary', help='Print Claim Summary Index')

    # export-summary
    sub.add_parser('export-summary', help='Write Claim Summary Index to study-registry.md')

    # stale
    sub.add_parser('stale', help='List studies needing re-verification')

    # add
    sub.add_parser('add', help='Interactively add a new study')

    # anon-ingest
    p_anon = sub.add_parser('anon-ingest', help='Ingest anonymous analytics snapshot')
    p_anon.add_argument('file', help='Path to anonymous JSON payload')

    # anon-report
    sub.add_parser('anon-report', help='Aggregate anonymous analytics report')

    # stats
    sub.add_parser('stats', help='Show database statistics')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    commands = {
        'init': cmd_init,
        'import-md': cmd_import_md,
        'query': cmd_query,
        'summary': cmd_summary,
        'export-summary': cmd_export_summary,
        'stale': cmd_stale,
        'add': cmd_add,
        'anon-ingest': cmd_anon_ingest,
        'anon-report': cmd_anon_report,
        'stats': cmd_stats,
    }

    commands[args.command](args)


if __name__ == '__main__':
    main()
