#!/usr/bin/env python3
"""
LongevityPath Content Validator v1.0
=====================================
Automated quality gate for all HTML content pages.
Enforces brand CSS, scientific rigor, and content structure.

Usage:
    python validate.py                          # validate all HTML in current dir
    python validate.py nutrition-calculator-faq.html  # validate one file
    python validate.py --fix                    # show fix suggestions
    python validate.py --verbose                # show all checks (pass + fail)

Exit codes:
    0 = all checks pass
    1 = failures found
"""

import sys
import re
import os
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional
from urllib.parse import urlparse

# ============================================================
# CONFIGURATION — Single source of truth for all rules
# ============================================================

# Brand colors (must match brand.css :root)
BRAND = {
    "teal":        "#00905A",
    "teal_light":  "#E8F5F0",
    "orange":      "#E9A04E",
    "orange_light": "#FDF6EC",
    "red":         "#EF4444",
    "red_light":   "#FEE2E2",
    "bg":          "#FAF9F6",
    "card":        "#FFFFFF",
    "text":        "#1F2937",
    "text_muted":  "#6B7280",
    "border":      "#E5E7EB",
}

# Files to skip (not content pages)
SKIP_FILES = {"brand.css", "template.html", "validate.py"}
SKIP_DIRS  = {"OLD", "Coding-LongevityPath", ".skills", "node_modules", ".git"}

# Known non-peer-reviewed domains (blogs, magazines)
BLOG_DOMAINS = [
    "strongerbyscience.com", "mennohenselmans.com", "bayesianbodybuilding.com",
    "examine.com", "t-nation.com", "bodybuilding.com", "medium.com",
    "wordpress.com", "blogspot.com", "substack.com",
]


# ============================================================
# RESULT DATA STRUCTURES
# ============================================================

@dataclass
class Check:
    """A single validation check result."""
    category: str       # "BRAND", "SCIENCE", "STRUCTURE", "REFERENCE"
    name: str           # short check name
    passed: bool
    message: str        # human-readable result
    line: Optional[int] = None
    fix: Optional[str] = None  # suggested fix

@dataclass
class FileReport:
    """All check results for one file."""
    filepath: str
    checks: List[Check] = field(default_factory=list)

    @property
    def passed(self):
        return all(c.passed for c in self.checks)

    @property
    def failures(self):
        return [c for c in self.checks if not c.passed]

    @property
    def score(self):
        if not self.checks:
            return 0
        return int(100 * sum(1 for c in self.checks if c.passed) / len(self.checks))


# ============================================================
# 1. BRAND CSS COMPLIANCE
# ============================================================

def check_brand_css(content: str, lines: list) -> List[Check]:
    """Verify brand.css is imported and used correctly."""
    checks = []

    # 1.1 brand.css must be imported
    has_import = 'brand.css' in content
    checks.append(Check(
        "BRAND", "brand.css imported",
        has_import,
        "brand.css is linked" if has_import else "brand.css NOT imported — page uses standalone CSS",
        fix='Add: <link rel="stylesheet" href="brand.css">' if not has_import else None
    ))

    # 1.2 No redefined :root variables (overriding brand.css)
    style_blocks = re.findall(r'<style[^>]*>(.*?)</style>', content, re.DOTALL)
    full_style = "\n".join(style_blocks)

    root_redefs = re.findall(r':root\s*\{', full_style)
    has_root_redef = len(root_redefs) > 0
    checks.append(Check(
        "BRAND", "no :root override",
        not has_root_redef,
        "No :root redefinition in <style>" if not has_root_redef else f":root redefined {len(root_redefs)}x in <style> — may override brand.css variables",
        fix="Remove :root block from <style>. Use brand.css variables directly." if has_root_redef else None
    ))

    # 1.3 No hardcoded brand colors (should use CSS variables)
    hardcoded_colors = []
    for i, line in enumerate(lines, 1):
        # Only check inside <style> blocks or style= attributes
        if 'style' in line.lower() or (i > 0 and any('<style' in lines[j] for j in range(max(0, i-20), i))):
            for color_name, hex_val in BRAND.items():
                # Look for hardcoded hex values (case insensitive)
                if hex_val.lower() in line.lower() and 'var(--' not in line:
                    # Skip if it's a CSS variable definition line
                    if '--color-' in line:
                        continue
                    hardcoded_colors.append((i, color_name, hex_val))

    checks.append(Check(
        "BRAND", "no hardcoded colors",
        len(hardcoded_colors) == 0,
        "All colors use CSS variables" if not hardcoded_colors else f"{len(hardcoded_colors)} hardcoded color(s) found — use var(--color-xxx) instead",
        fix="\n".join(f"  Line {ln}: Replace {hx} with var(--color-{nm})" for ln, nm, hx in hardcoded_colors[:5]) if hardcoded_colors else None
    ))

    # 1.4 Teal not used as text color — only allowed for science/credibility elements
    teal_text_violations = []
    # Selectors where teal IS correct (science/credibility elements, links, labels, icons)
    TEAL_ALLOWED_SELECTORS = [
        'background', 'border', '.expert-avatar', '.study-badge', '.study-link',
        '.badge', '.evidence-tag', '.reference', '.cite', '.quick-answer',
        '.tip-box', '.warning-box', '.info-icon', '.help-link', '.trend-up',
        '.faq-meta', '.note-box', '.formula', '.intro-link', '.back-btn',
        '::before', '::after',  # pseudo-elements (quote marks etc.)
        'a ', 'a:', 'a{',      # links
        '-label', '-link', '-tag', '-badge', '-icon', '-btn',
        'label', 'strong',      # labels and emphasis in science context
    ]

    # Parse CSS blocks to get selector context for each teal color usage
    for block in style_blocks:
        # Find CSS rules: selector { properties }
        rules = re.finditer(r'([^{}]+?)\{([^{}]+)\}', block)
        for rule in rules:
            selector = rule.group(1).strip()
            props = rule.group(2)
            # Check if this rule has color: teal (not background-color)
            if re.search(r'(?<!background-)color:\s*var\(--color-teal\)', props):
                # Check if the SELECTOR is in the allowed list
                allowed = any(ctx in selector.lower() for ctx in TEAL_ALLOWED_SELECTORS)
                if not allowed:
                    # Also check if it's inside an allowed property context
                    prop_allowed = any(ctx in props.lower() for ctx in ['background', 'border'])
                    if not prop_allowed:
                        teal_text_violations.append(f"'{selector}'")

    checks.append(Check(
        "BRAND", "teal not used as text color",
        len(teal_text_violations) == 0,
        "Teal used correctly (science elements only)" if not teal_text_violations else f"Teal used as body text in: {', '.join(teal_text_violations[:5])}",
        fix="Change color: var(--color-teal) to color: var(--color-text) for body text" if teal_text_violations else None
    ))

    # 1.5 Headings use --color-text, not teal
    heading_violations = []
    in_style = False
    for i, line in enumerate(lines, 1):
        if '<style' in line:
            in_style = True
        if '</style>' in line:
            in_style = False
        if in_style:
            # Look for heading selectors with teal color
            if re.search(r'(?:h[1-6]|\.qa-heading|\.faq-header\s+h[1-6]|\.section-title)', line):
                # Check next few lines for color: teal
                for j in range(i, min(i + 5, len(lines))):
                    if re.search(r'color:\s*var\(--color-teal\)', lines[j - 1]):
                        heading_violations.append(j)
                    if '}' in lines[j - 1]:
                        break

    checks.append(Check(
        "BRAND", "headings use text color",
        len(heading_violations) == 0,
        "All headings use --color-text" if not heading_violations else f"Heading(s) use teal on line(s): {', '.join(str(l) for l in heading_violations)}",
        fix="Change heading color to var(--color-text)" if heading_violations else None
    ))

    # 1.6 Table headers: solid teal bg + white text
    table_th_issues = []
    for block in style_blocks:
        th_rules = re.finditer(r'([\w\s\.\-]+th)\s*\{([^}]+)\}', block)
        for match in th_rules:
            selector = match.group(1).strip()
            props = match.group(2)
            bg = re.search(r'background(?:-color)?:\s*([^;]+)', props)
            color = re.search(r'(?<!background-)color:\s*([^;]+)', props)
            if bg and 'teal-light' in bg.group(1):
                table_th_issues.append(f"{selector}: uses teal-light bg instead of solid teal")
            if color and 'white' not in color.group(1) and '#fff' not in color.group(1).lower():
                table_th_issues.append(f"{selector}: text should be white on teal header")

    checks.append(Check(
        "BRAND", "table headers: teal bg + white text",
        len(table_th_issues) == 0,
        "Table headers styled correctly" if not table_th_issues else "; ".join(table_th_issues[:3]),
        fix="Set th { background: var(--color-teal); color: white; }" if table_th_issues else None
    ))

    # 1.7 Inter font loaded (brand.css loads Inter via @import, so importing brand.css counts)
    has_inter = 'Inter' in content or has_import  # brand.css imports Inter
    checks.append(Check(
        "BRAND", "Inter font loaded",
        has_inter,
        "Inter font present" if has_inter else "Inter font not loaded",
        fix='Import brand.css or add Inter font via Google Fonts' if not has_inter else None
    ))

    # 1.8 Lucide icons loaded
    has_lucide = 'lucide' in content.lower()
    checks.append(Check(
        "BRAND", "Lucide icons loaded",
        has_lucide,
        "Lucide icons script present" if has_lucide else "Lucide icons not loaded",
        fix='Add: <script src="https://unpkg.com/lucide@latest"></script>' if not has_lucide else None
    ))

    # 1.9 lucide.createIcons() called
    has_create = 'createIcons()' in content
    checks.append(Check(
        "BRAND", "createIcons() called",
        has_create,
        "lucide.createIcons() present" if has_create else "lucide.createIcons() not called — icons won't render",
        fix='Add before </body>: <script>lucide.createIcons();</script>' if not has_create else None
    ))

    # 1.10 Mobile viewport meta tag
    has_viewport = 'viewport' in content
    checks.append(Check(
        "BRAND", "mobile viewport meta",
        has_viewport,
        "Viewport meta tag present" if has_viewport else "Missing viewport meta tag",
        fix='Add: <meta name="viewport" content="width=device-width, initial-scale=1.0">' if not has_viewport else None
    ))

    return checks


# ============================================================
# 2. SCIENTIFIC RIGOR
# ============================================================

def check_scientific_rigor(content: str, lines: list) -> List[Check]:
    """Verify citations, evidence quality, and source integrity."""
    checks = []

    # Extract body content (skip <head>, <style>, <script>)
    body_match = re.search(r'<body[^>]*>(.*)</body>', content, re.DOTALL)
    if not body_match:
        checks.append(Check("SCIENCE", "body found", False, "No <body> tag found"))
        return checks
    body = body_match.group(1)

    # Remove script tags from body
    body_text = re.sub(r'<script[^>]*>.*?</script>', '', body, flags=re.DOTALL)

    # 2.1 Find all in-text citations [N]
    citations_in_text = set(int(n) for n in re.findall(r'\[(\d+)\]', body_text))

    # 2.2 Find all references defined (support both class="reference" and class="study-ref")
    refs_defined = set(int(n) for n in re.findall(r'class="(?:reference|study-ref)"[^>]*>\s*\[(\d+)\]', body_text))
    # Also try plain text references
    refs_defined.update(int(n) for n in re.findall(r'<p[^>]*>\s*\[(\d+)\]', body_text) if int(n) < 100)

    # 2.3 Citations match references
    orphan_citations = citations_in_text - refs_defined
    orphan_refs = refs_defined - citations_in_text

    checks.append(Check(
        "SCIENCE", "all citations have references",
        len(orphan_citations) == 0,
        f"All {len(citations_in_text)} citations match references" if not orphan_citations else f"Citation(s) {sorted(orphan_citations)} used in text but not in references",
        fix=f"Add references for: {sorted(orphan_citations)}" if orphan_citations else None
    ))

    if orphan_refs:
        checks.append(Check(
            "SCIENCE", "all references are cited",
            False,
            f"Reference(s) {sorted(orphan_refs)} defined but never cited in text",
            fix=f"Remove unused references or add citations: {sorted(orphan_refs)}"
        ))

    # 2.4 Sequential numbering (no gaps)
    if refs_defined:
        expected = set(range(1, max(refs_defined) + 1))
        gaps = expected - refs_defined
        checks.append(Check(
            "SCIENCE", "sequential reference numbering",
            len(gaps) == 0,
            "References numbered sequentially" if not gaps else f"Gap(s) in numbering: missing [{', '.join(str(g) for g in sorted(gaps))}]",
            fix=f"Add missing references or renumber: {sorted(gaps)}" if gaps else None
        ))

    # 2.5 Every reference has a DOI or link
    ref_lines = [(i, line) for i, line in enumerate(lines, 1) if 'class="reference"' in line or 'class="study-ref"' in line]
    refs_without_doi = []
    refs_without_link = []

    for line_num, line in ref_lines:
        has_doi = bool(re.search(r'doi[:\s]*10\.\d+', line, re.IGNORECASE)) or 'doi.org/10.' in line
        has_link = '<a ' in line and 'href=' in line
        ref_num_match = re.search(r'\[(\d+)\]', line)
        ref_num = ref_num_match.group(1) if ref_num_match else "?"

        if not has_doi and 'Book' not in line and 'book' not in line:
            refs_without_doi.append(ref_num)
        if not has_link and 'Book' not in line and 'book' not in line:
            refs_without_link.append(ref_num)

    checks.append(Check(
        "SCIENCE", "all references have DOI",
        len(refs_without_doi) == 0,
        f"All references have DOIs" if not refs_without_doi else f"Reference(s) [{', '.join(refs_without_doi)}] missing DOI",
        fix="Add DOI for each study" if refs_without_doi else None
    ))

    checks.append(Check(
        "SCIENCE", "all references have clickable link",
        len(refs_without_link) == 0,
        f"All references have clickable links" if not refs_without_link else f"Reference(s) [{', '.join(refs_without_link)}] have no clickable link",
        fix="Add <a href='https://doi.org/...'> View Study link for each reference" if refs_without_link else None
    ))

    # 2.6 DOI links use doi.org (permanent) not publisher URLs
    doi_links = re.findall(r'href="(https?://[^"]*doi[^"]*)"', content, re.IGNORECASE)
    non_doi_org = [url for url in doi_links if 'doi.org' not in url and 'pubmed' not in url]
    checks.append(Check(
        "SCIENCE", "DOI links use doi.org (permanent)",
        len(non_doi_org) == 0,
        "All DOI links use permanent doi.org URLs" if not non_doi_org else f"{len(non_doi_org)} link(s) use publisher URLs instead of doi.org",
        fix="Replace publisher URLs with https://doi.org/[DOI]" if non_doi_org else None
    ))

    # 2.7 No blog/non-peer-reviewed sources
    blog_refs = []
    for line_num, line in ref_lines:
        for domain in BLOG_DOMAINS:
            if domain in line.lower():
                ref_match = re.search(r'\[(\d+)\]', line)
                blog_refs.append(f"[{ref_match.group(1) if ref_match else '?'}] ({domain})")

    checks.append(Check(
        "SCIENCE", "no blog sources",
        len(blog_refs) == 0,
        "All sources are peer-reviewed" if not blog_refs else f"Non-peer-reviewed source(s): {', '.join(blog_refs)}",
        fix="Replace blog sources with peer-reviewed studies" if blog_refs else None
    ))

    # 2.8 Content sections have citations
    # Find main content sections (cards, qa-items, faq-content)
    sections = re.findall(r'class="(?:answer|faq-content|prose)"[^>]*>(.*?)</div>', body_text, re.DOTALL)
    sections_without_cite = 0
    for section in sections:
        clean = re.sub(r'<[^>]+>', '', section).strip()
        if len(clean) > 200 and not re.search(r'\[\d+\]', section):
            sections_without_cite += 1

    checks.append(Check(
        "SCIENCE", "content sections have citations",
        sections_without_cite == 0,
        "All substantial content sections cite evidence" if sections_without_cite == 0 else f"{sections_without_cite} content section(s) >200 chars with no citation",
        fix="Add [N] citations to unsupported content sections" if sections_without_cite else None
    ))

    return checks


# ============================================================
# 3. CONTENT STRUCTURE
# ============================================================

def check_content_structure(content: str, lines: list) -> List[Check]:
    """Verify page structure, navigation, and required elements."""
    checks = []

    # 3.1 Has header with navigation (can be <header> tag or div with header class)
    has_header = '<header' in content or 'class="header"' in content or 'class="mobile-header"' in content or 'class="page-header"' in content
    checks.append(Check(
        "STRUCTURE", "header present",
        has_header,
        "Page header present" if has_header else "No header element found",
        fix="Add <header> or div with class='header' containing back navigation" if not has_header else None
    ))

    # 3.2 Has back navigation
    has_back = 'back' in content.lower() and ('<a ' in content)
    checks.append(Check(
        "STRUCTURE", "back navigation",
        has_back,
        "Back navigation link present" if has_back else "No back navigation found",
        fix="Add back link in header" if not has_back else None
    ))

    # 3.3 Has "Last updated" footer
    has_updated = bool(re.search(r'[Ll]ast\s+[Uu]pdated', content))
    checks.append(Check(
        "STRUCTURE", "last updated date",
        has_updated,
        "Last updated date present" if has_updated else "No 'Last updated' date found",
        fix='Add footer: Last updated: [Month Year] · Based on peer-reviewed research' if not has_updated else None
    ))

    # 3.4 Has "peer-reviewed" or "evidence-based" marker
    has_evidence_marker = bool(re.search(r'peer.?reviewed|evidence.?based', content, re.IGNORECASE))
    checks.append(Check(
        "STRUCTURE", "evidence-based marker",
        has_evidence_marker,
        "Evidence-based credibility marker present" if has_evidence_marker else "No peer-reviewed/evidence-based marker in footer",
        fix='Add to footer: "Based on peer-reviewed research"' if not has_evidence_marker else None
    ))

    # 3.5 Has container with max-width
    has_container = 'class="container' in content or 'max-width' in content
    checks.append(Check(
        "STRUCTURE", "container layout",
        has_container,
        "Container with max-width present" if has_container else "No container element found",
    ))

    # 3.6 HTML lang attribute
    has_lang = 'lang="en"' in content or "lang='en'" in content
    checks.append(Check(
        "STRUCTURE", "html lang attribute",
        has_lang,
        'html lang="en" set' if has_lang else "Missing lang attribute on <html>",
        fix='Add lang="en" to <html> tag' if not has_lang else None
    ))

    # 3.7 Charset meta
    has_charset = 'charset' in content.lower()
    checks.append(Check(
        "STRUCTURE", "charset meta",
        has_charset,
        "Charset meta tag present" if has_charset else "Missing charset meta tag",
        fix='Add: <meta charset="UTF-8">' if not has_charset else None
    ))

    # 3.8 Title tag
    title_match = re.search(r'<title>(.+?)</title>', content)
    has_title = title_match is not None and len(title_match.group(1).strip()) > 0
    checks.append(Check(
        "STRUCTURE", "page title",
        has_title,
        f"Title: {title_match.group(1).strip()[:50]}" if has_title else "Missing or empty <title> tag",
        fix="Add descriptive <title> tag" if not has_title else None
    ))

    return checks


# ============================================================
# 4. REFERENCE FORMAT VALIDATION
# ============================================================

def check_reference_format(content: str, lines: list) -> List[Check]:
    """Validate individual reference formatting."""
    checks = []

    ref_lines = [(i, line) for i, line in enumerate(lines, 1) if ('class="reference"' in line or 'class="study-ref"' in line) and re.search(r'\[\d+\]', line)]

    if not ref_lines:
        checks.append(Check("REFERENCE", "references exist", False, "No references found on page"))
        return checks

    checks.append(Check("REFERENCE", "references exist", True, f"{len(ref_lines)} reference(s) found"))

    # Check each reference
    format_issues = []
    year_issues = []
    journal_issues = []

    for line_num, line in ref_lines:
        ref_match = re.search(r'\[(\d+)\]', line)
        ref_num = ref_match.group(1) if ref_match else "?"

        # Has year in parentheses
        if not re.search(r'\(\d{4}\)', line):
            year_issues.append(ref_num)

        # Has journal in italics (<em> or <i>)
        if not re.search(r'<em>|<i>', line) and 'Book' not in line:
            journal_issues.append(ref_num)

        # Has author format (Last, I.)
        if not re.search(r'[A-Z][a-z]+,\s+[A-Z]\.', line) and 'Book' not in line:
            format_issues.append(ref_num)

    if year_issues:
        checks.append(Check(
            "REFERENCE", "year format (YYYY)",
            False,
            f"Reference(s) [{', '.join(year_issues)}] missing year in parentheses",
            fix="Format: Author. (Year). \"Title.\" Journal..."
        ))

    if journal_issues:
        checks.append(Check(
            "REFERENCE", "journal in italics",
            False,
            f"Reference(s) [{', '.join(journal_issues)}] missing italic journal name",
            fix="Wrap journal name in <em> tags"
        ))

    if not year_issues and not journal_issues and not format_issues:
        checks.append(Check("REFERENCE", "format consistency", True, "All references properly formatted"))

    # Check DOI format validity
    dois = re.findall(r'doi(?::\s*|\.org/)(10\.\d+/[^\s<"]+)', content, re.IGNORECASE)
    invalid_dois = [d for d in dois if not re.match(r'10\.\d{4,}/', d)]
    checks.append(Check(
        "REFERENCE", "valid DOI format",
        len(invalid_dois) == 0,
        f"All {len(dois)} DOIs have valid format" if not invalid_dois else f"{len(invalid_dois)} invalid DOI format(s)",
    ))

    # Check link targets use doi.org
    view_links = re.findall(r'href="([^"]+)"[^>]*>View Study', content)
    non_permanent = [url for url in view_links if 'doi.org' not in url and 'pubmed' not in url]
    checks.append(Check(
        "REFERENCE", "permanent study links",
        len(non_permanent) == 0,
        f"All {len(view_links)} study links use permanent URLs (doi.org or PubMed)" if not non_permanent else f"{len(non_permanent)} study link(s) use non-permanent URLs",
        fix="Use https://doi.org/[DOI] for permanent links" if non_permanent else None
    ))

    # Check for old studies (>15 years) that may be superseded
    import datetime
    current_year = datetime.datetime.now().year
    old_refs = []
    for line_num, line in ref_lines:
        year_match = re.search(r'\((\d{4})\)', line)
        ref_match = re.search(r'\[(\d+)\]', line)
        if year_match and ref_match:
            study_year = int(year_match.group(1))
            ref_num = ref_match.group(1)
            if study_year < current_year - 15:
                old_refs.append(f"[{ref_num}] ({study_year})")

    checks.append(Check(
        "REFERENCE", "no outdated references (>15 yr)",
        len(old_refs) == 0,
        "All references within 15 years" if not old_refs else f"Old reference(s) needing review: {', '.join(old_refs)} — verify landmark status or replace with newer SR/MA",
        fix="Check if a newer SR/MA covers the same claim; replace if so" if old_refs else None
    ))

    return checks


# ============================================================
# 5. CSS COMPONENT COMPLETENESS (for evidence pages)
# ============================================================

def check_components(content: str, lines: list) -> List[Check]:
    """Check that evidence pages use the full component library."""
    checks = []

    # Only run for evidence/FAQ pages
    is_evidence = any(kw in content.lower() for kw in ['faq', 'evidence', 'guide', 'research'])
    if not is_evidence:
        return checks

    # Required components for evidence pages
    # Check by class OR by text content
    has_study_links = 'study-link' in content or 'View Study' in content
    # study-link checked separately since it can appear as class or text
    checks.append(Check(
        "COMPONENT", "Study link (View Study)",
        has_study_links,
        "Study links present" if has_study_links else "Missing: View Study links",
        fix="Add 'View Study' links to references" if not has_study_links else None
    ))

    return checks


# ============================================================
# 6. PER-QUESTION FAQ STRUCTURE
# ============================================================

def check_faq_structure(content: str, lines: list) -> List[Check]:
    """Verify per-question FAQ architecture: one FAQ card per scored question,
    score bookend cards, and closing action cards."""
    checks = []

    # Only run for evidence/FAQ pages
    is_evidence = any(kw in content.lower() for kw in ['faq', 'evidence', 'guide', 'research'])
    if not is_evidence:
        return checks

    body_match = re.search(r'<body[^>]*>(.*)</body>', content, re.DOTALL)
    if not body_match:
        return checks
    body = body_match.group(1)

    # 6.1 Find all FAQ cards (div.faq-card with id="qN")
    faq_cards = re.findall(r'<div[^>]*class="faq-card"[^>]*id="(q\d+)"', body)
    if not faq_cards:
        # Also try id before class
        faq_cards = re.findall(r'<div[^>]*id="(q\d+)"[^>]*class="faq-card"', body)

    checks.append(Check(
        "FAQ", "FAQ cards present",
        len(faq_cards) >= 4,
        f"{len(faq_cards)} FAQ card(s) found (need ≥4: 2 score bookends + per-question + closing)" if faq_cards else "No FAQ cards found — need per-question FAQ architecture",
        fix="Add faq-card divs with id='q1', 'q2', etc. following per-question FAQ architecture" if len(faq_cards) < 4 else None
    ))

    if not faq_cards:
        return checks

    # 6.2 Score bookend cards (first 2 cards should reference score ranges)
    # Extract content of first two cards
    score_keywords = ['score', 'scoring', 'below', 'above', '%', 'percent', 'range', 'result']
    for i, card_id in enumerate(faq_cards[:2], 1):
        card_match = re.search(
            rf'id="{card_id}"[^>]*>(.*?)(?=<div[^>]*class="faq-card"|$)',
            body, re.DOTALL
        )
        if card_match:
            card_text = re.sub(r'<[^>]+>', '', card_match.group(1)).lower()
            has_score_ref = any(kw in card_text for kw in score_keywords)
            checks.append(Check(
                "FAQ", f"card {card_id}: score bookend",
                has_score_ref,
                f"Card {card_id} contains score-related framing" if has_score_ref else f"Card {card_id} missing score bookend content (should frame below-25% or above-75%)",
                fix=f"Card {card_id} should discuss what a low/high score means" if not has_score_ref else None
            ))

    # 6.3 Per-question cards have quick-answer sections
    cards_with_quick_answer = 0
    for card_id in faq_cards:
        card_match = re.search(
            rf'id="{card_id}"[^>]*>(.*?)(?=<div[^>]*class="faq-card"|$)',
            body, re.DOTALL
        )
        if card_match and 'quick-answer' in card_match.group(1):
            cards_with_quick_answer += 1

    checks.append(Check(
        "FAQ", "cards have quick-answer boxes",
        cards_with_quick_answer >= len(faq_cards) * 0.5,
        f"{cards_with_quick_answer}/{len(faq_cards)} cards have quick-answer sections" if cards_with_quick_answer > 0 else "No cards have quick-answer sections",
        fix="Add <div class='quick-answer'> to each FAQ card" if cards_with_quick_answer < len(faq_cards) * 0.5 else None
    ))

    # 6.4 Per-question cards have references (inline citations or reference sections)
    cards_with_refs = 0
    for card_id in faq_cards:
        card_match = re.search(
            rf'id="{card_id}"[^>]*>(.*?)(?=<div[^>]*class="faq-card"|$)',
            body, re.DOTALL
        )
        if card_match:
            card_content = card_match.group(1)
            has_refs = (
                'class="reference"' in card_content or
                'class="study-ref"' in card_content or
                'references-section' in card_content or
                bool(re.search(r'\[\d+\]', card_content))
            )
            if has_refs:
                cards_with_refs += 1

    checks.append(Check(
        "FAQ", "cards have citations/references",
        cards_with_refs >= len(faq_cards) - 2,  # allow closing cards to skip refs
        f"{cards_with_refs}/{len(faq_cards)} cards have citations or references",
        fix="Add inline [N] citations and reference sections to FAQ cards" if cards_with_refs < len(faq_cards) - 2 else None
    ))

    # 6.5 Closing cards: "how to improve" and/or "personalized help" / coaching
    closing_keywords = ['improve', 'coaching', 'personalized', 'coach', 'help', 'action', 'strategy', 'next step']
    last_cards = faq_cards[-2:] if len(faq_cards) >= 2 else faq_cards[-1:]
    has_closing = False
    for card_id in last_cards:
        card_match = re.search(
            rf'id="{card_id}"[^>]*>(.*?)(?=<div[^>]*class="faq-card"|$)',
            body, re.DOTALL
        )
        if card_match:
            card_text = re.sub(r'<[^>]+>', '', card_match.group(1)).lower()
            if any(kw in card_text for kw in closing_keywords):
                has_closing = True

    checks.append(Check(
        "FAQ", "closing action cards present",
        has_closing,
        "Closing card(s) with improvement/coaching content found" if has_closing else "Missing closing cards (how to improve + personalized help)",
        fix="Add 'How to Improve' and 'Personalized Help' closing FAQ cards" if not has_closing else None
    ))

    # 6.6 FAQ rating widget
    has_rating = 'was this helpful' in content.lower() or 'faq-rating' in content.lower() or 'thumbs' in content.lower()
    checks.append(Check(
        "FAQ", "FAQ rating widget",
        has_rating,
        "FAQ rating widget present" if has_rating else "Missing 'Was this helpful?' rating widget",
        fix="Add FAQ rating widget (thumbs up/down) to each card" if not has_rating else None
    ))

    return checks


# ============================================================
# MAIN VALIDATOR
# ============================================================

def validate_file(filepath: str) -> FileReport:
    """Run all validators on a single HTML file."""
    report = FileReport(filepath=filepath)

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')
    except Exception as e:
        report.checks.append(Check("SYSTEM", "file readable", False, f"Error reading file: {e}"))
        return report

    # Run all check categories
    report.checks.extend(check_brand_css(content, lines))
    report.checks.extend(check_scientific_rigor(content, lines))
    report.checks.extend(check_content_structure(content, lines))
    report.checks.extend(check_reference_format(content, lines))
    report.checks.extend(check_components(content, lines))
    report.checks.extend(check_faq_structure(content, lines))

    return report


def find_html_files(target: str) -> List[str]:
    """Find HTML files to validate, respecting skip rules."""
    if os.path.isfile(target):
        return [target]

    files = []
    target_path = Path(target)
    for html_file in sorted(target_path.glob('*.html')):
        if html_file.name not in SKIP_FILES:
            files.append(str(html_file))
    return files


def print_report(report: FileReport, verbose: bool = False, show_fix: bool = False):
    """Print a formatted report for one file."""
    filename = os.path.basename(report.filepath)
    status = "PASS" if report.passed else "FAIL"
    icon = "\u2705" if report.passed else "\u274c"

    print(f"\n{'='*60}")
    print(f"{icon}  {filename}  [{report.score}%]")
    print(f"{'='*60}")

    # Group checks by category
    categories = {}
    for check in report.checks:
        categories.setdefault(check.category, []).append(check)

    for cat, cat_checks in categories.items():
        cat_pass = sum(1 for c in cat_checks if c.passed)
        cat_total = len(cat_checks)
        cat_icon = "\u2705" if cat_pass == cat_total else "\u274c"
        print(f"\n  {cat_icon} {cat} ({cat_pass}/{cat_total})")

        for check in cat_checks:
            if check.passed and not verbose:
                continue
            icon = "\u2705" if check.passed else "\u274c"
            print(f"     {icon} {check.name}: {check.message}")
            if show_fix and check.fix and not check.passed:
                print(f"        \U0001f527 Fix: {check.fix}")


def main():
    args = sys.argv[1:]
    verbose = '--verbose' in args
    show_fix = '--fix' in args
    args = [a for a in args if not a.startswith('--')]

    target = args[0] if args else '.'

    # Find files
    files = find_html_files(target)
    if not files:
        print(f"No HTML files found in: {target}")
        sys.exit(1)

    # Validate
    reports = [validate_file(f) for f in files]

    # Print reports
    for report in reports:
        print_report(report, verbose=verbose, show_fix=show_fix)

    # Summary
    total_checks = sum(len(r.checks) for r in reports)
    total_pass = sum(sum(1 for c in r.checks if c.passed) for r in reports)
    total_fail = total_checks - total_pass
    all_pass = all(r.passed for r in reports)

    print(f"\n{'='*60}")
    print(f"SUMMARY: {len(reports)} file(s), {total_checks} checks, {total_pass} passed, {total_fail} failed")
    if all_pass:
        print("\u2705 ALL PAGES PASS")
    else:
        failing = [os.path.basename(r.filepath) for r in reports if not r.passed]
        print(f"\u274c FAILING: {', '.join(failing)}")
        if not show_fix:
            print("\n\U0001f4a1 Run with --fix to see suggested fixes")
    print(f"{'='*60}\n")

    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
