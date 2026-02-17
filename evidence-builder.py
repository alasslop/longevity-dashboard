#!/usr/bin/env python3
"""
Evidence Page Builder for LongevityPath
Extracts data from existing evidence pages and builds new pages from templates.
"""

import json
import re
import sys
import os
from pathlib import Path
from html.parser import HTMLParser
from typing import Dict, List, Any, Optional

# ============================================
# Embedded HTML Template
# ============================================
TEMPLATE_HTML = r'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
    <title>{{HEADER_TITLE}} - LongevityPath</title>
    <link rel="stylesheet" href="brand.css">
    <script src="https://unpkg.com/lucide@latest"></script>
</head>
<body>
    <header class="header">
        <a href="index.html" class="back-btn"><i data-lucide="arrow-left" style="width:20px;height:20px;"></i></a>
        <span class="header-title">{{HEADER_TITLE}}</span>
        <span class="user-badge" id="userBadge"><i data-lucide="user" style="width:12px;height:12px;"></i> <span id="userNameBadge">User</span></span>
    </header>

    <div class="container-evidence">
        <div class="breadcrumb">
            <a href="index.html">LongevityPath</a>
            <span>/</span>
            <a href="index.html">{{DIMENSION}}</a>
            <span>/</span>
            Evidence &amp; FAQ
        </div>

        <div class="marketing-cta" id="marketingCta">
            <div class="marketing-cta-title">{{CTA_TITLE}}</div>
            <div class="marketing-cta-text">{{CTA_TEXT}}</div>
            <a href="index.html" class="marketing-cta-button">
                <i data-lucide="play" style="width:16px;height:16px;"></i> Start Free Assessment
            </a>
        </div>

        {{CARDS}}

        <div class="page-footer">
            <p>All recommendations based on peer-reviewed research. Last updated {{LAST_UPDATED}}.</p>
        </div>

        <div class="footer-cta" id="footerCta">
            <div class="footer-cta-text">{{FOOTER_CTA_TEXT}}</div>
            <a href="index.html" class="footer-cta-button">
                <i data-lucide="{{FOOTER_ICON}}" style="width:16px;height:16px;"></i> {{FOOTER_BUTTON_TEXT}}
            </a>
            <div class="footer-cta-meta">{{FOOTER_CTA_META}}</div>
        </div>
    </div>

    <script>
        lucide.createIcons();

        function toggleFaq(id) {
            const card = document.getElementById(id);
            card.classList.toggle('expanded');
        }

        function openFaqById(id) {
            const card = document.getElementById(id);
            if (card && !card.classList.contains('expanded')) {
                card.classList.add('expanded');
            }
        }

        function handleHashNavigation() {
            if (window.location.hash) {
                const targetId = window.location.hash.substring(1);
                openFaqById(targetId);
                setTimeout(() => {
                    const target = document.getElementById(targetId);
                    if (target) {
                        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
                    }
                }, 100);
            }
        }

        handleHashNavigation();
        window.addEventListener('hashchange', handleHashNavigation);

        {{COACHING_HINTS_JS}}

        {{RATINGS_JS}}

        function checkUserStatus() {
            const saved = localStorage.getItem('longevityPathData');
            const marketingCta = document.getElementById('marketingCta');
            const footerCta = document.getElementById('footerCta');
            const userBadge = document.getElementById('userBadge');
            const userNameBadge = document.getElementById('userNameBadge');

            if (saved) {
                const data = JSON.parse(saved);
                userBadge.classList.add('visible');
                userNameBadge.textContent = data.userName || 'User';
                marketingCta.classList.remove('visible');
                footerCta.querySelector('.footer-cta-text').textContent = 'Take control of your longevity. See where you stand.';
                footerCta.querySelector('.footer-cta-button').innerHTML = '<i data-lucide="arrow-left" style="width:16px;height:16px;"></i> Back to Assessment';
                footerCta.querySelector('.footer-cta-meta').textContent = '';
                lucide.createIcons();
            } else {
                marketingCta.classList.add('visible');
                userBadge.classList.remove('visible');
            }
        }

        checkUserStatus();
    </script>
</body>
</html>'''


class HTMLExtractor(HTMLParser):
    """Parse HTML and extract specific content patterns."""

    def __init__(self):
        super().__init__()
        self.reset()
        self.in_element = {}
        self.current_text = []
        self.elements = {}

    def reset(self):
        super().reset()
        self.in_element = {}
        self.current_text = []
        self.elements = {}

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        key = f"{tag}_{attrs_dict.get('class', attrs_dict.get('id', ''))}"
        self.in_element[key] = True

    def handle_endtag(self, tag):
        pass

    def handle_data(self, data):
        if self.in_element:
            self.current_text.append(data)


def read_html_file(filepath: str) -> str:
    """Read HTML file content."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()


def extract_text_between(html: str, start_marker: str, end_marker: str) -> str:
    """Extract text between two markers in HTML."""
    start_idx = html.find(start_marker)
    if start_idx == -1:
        return ""
    start_idx += len(start_marker)
    end_idx = html.find(end_marker, start_idx)
    if end_idx == -1:
        return ""
    return html[start_idx:end_idx].strip()


def extract_tag_content(html: str, tag: str, class_name: str = "", id_name: str = "") -> List[str]:
    """Extract all content from specific HTML tags."""
    pattern = f"<{tag}"
    if class_name:
        pattern += f"[^>]*class=['\"]?[^'\"]*{class_name}[^'\"]*['\"]?"
    if id_name:
        pattern += f"[^>]*id=['\"]?{id_name}['\"]?"
    pattern += "[^>]*>(.*?)</" + tag + ">"

    matches = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)
    return matches


def extract_attribute(html: str, tag: str, attr: str, value: str = "") -> List[str]:
    """Extract attribute values from tags."""
    if value:
        pattern = f"<{tag}[^>]*{attr}=['\"]?{value}['\"]?[^>]*>"
    else:
        pattern = f"<{tag}[^>]*{attr}=['\"]?([^'\"]*)['\"]?"

    matches = re.findall(pattern, html, re.IGNORECASE)
    return matches


def extract_page_config(html: str) -> Dict[str, Any]:
    """Extract page-level configuration."""
    config = {}

    # Extract title
    title_match = re.search(r'<title>([^<]+)</title>', html, re.IGNORECASE)
    if title_match:
        config['headerTitle'] = title_match.group(1).replace(' - LongevityPath', '')

    # Extract header title from header
    header_match = re.search(r'<span class=["\']header-title["\']>([^<]+)</span>', html)
    if header_match:
        config['headerTitle'] = header_match.group(1)

    # Extract dimension from breadcrumb
    breadcrumb_match = re.search(r'<a href="index\.html">([^<]+)</a>\s*<span>/</span>\s*Evidence', html)
    if breadcrumb_match:
        config['dimension'] = breadcrumb_match.group(1)

    # Extract marketing CTA
    marketing_title = re.search(r'<div class=["\']marketing-cta-title["\']>([^<]+)</div>', html)
    if marketing_title:
        config['ctaTitle'] = marketing_title.group(1)

    marketing_text = re.search(r'<div class=["\']marketing-cta-text["\']>([^<]+)</div>', html)
    if marketing_text:
        config['ctaText'] = marketing_text.group(1)

    # Extract footer CTA
    footer_text = re.search(r'<div class=["\']footer-cta-text["\']>([^<]+)</div>', html)
    if footer_text:
        config['footerCtaText'] = footer_text.group(1)

    footer_button = re.search(
        r'<a[^>]*class=["\']footer-cta-button["\'][^>]*>.*?<i[^>]*data-lucide=["\']([^"\']+)["\'].*?</i>\s*([^<]+)</a>',
        html,
        re.DOTALL
    )
    if footer_button:
        config['footerIcon'] = footer_button.group(1)
        config['footerButtonText'] = footer_button.group(2).strip()

    footer_meta = re.search(r'<div class=["\']footer-cta-meta["\']>([^<]+)</div>', html)
    if footer_meta:
        config['footerCtaMeta'] = footer_meta.group(1)

    # Extract last updated
    last_updated = re.search(r'Last updated ([^<\.]+)', html)
    if last_updated:
        config['lastUpdated'] = last_updated.group(1)

    return config


def extract_cards(html: str) -> List[Dict[str, Any]]:
    """Extract all FAQ cards from HTML."""
    cards = []

    # Split on faq-card divs
    card_pattern = r'<div class="faq-card"[^>]*id="([^"]+)"[^>]*>(.*?)(?=<div class="faq-card"|<div class="page-footer"|$)'
    matches = re.finditer(card_pattern, html, re.DOTALL)

    for idx, match in enumerate(matches):
        card_id = match.group(1)
        card_html = match.group(2)

        card = {
            'id': card_id,
            'order': idx,
            'title': '',
            'readTime': '',
            'metaText': '',
            'preview': '',
            'quickAnswer': '',
            'table': None,
            'proseTexts': [],
            'coachingHintId': None,
            'tipBox': None,
            'warningBox': None,
            'studyCitations': [],
            'expertCitations': [],
            'studyRefs': []
        }

        # Extract title
        title_match = re.search(r'<h[12] class="faq-question-title">([^<]+)</h[12]>', card_html)
        if title_match:
            card['title'] = title_match.group(1)

        # Extract read time
        read_time_match = re.search(r'>(\d+)\s*min read</span>', card_html)
        if read_time_match:
            card['readTime'] = read_time_match.group(1)

        # Extract meta text (second span in faq-meta)
        meta_spans = re.findall(r'<span class="faq-meta-divider"[^>]*>&middot;</span>\s*<span[^>]*>([^<]+)</span>', card_html)
        if meta_spans:
            card['metaText'] = meta_spans[0]

        # Extract preview
        preview_match = re.search(r'<div class="faq-preview">([^<]+)</div>', card_html)
        if preview_match:
            card['preview'] = preview_match.group(1)

        # Extract quick answer
        qa_match = re.search(r'<div class="quick-answer-text">([^<].*?)</div>', card_html, re.DOTALL)
        if qa_match:
            card['quickAnswer'] = qa_match.group(1).strip()

        # Extract table
        table_match = re.search(r'<table class="faq-table">(.*?)</table>', card_html, re.DOTALL)
        if table_match:
            card['table'] = '<table class="faq-table">' + table_match.group(1) + '</table>'

        # Extract prose paragraphs
        prose_matches = re.findall(r'<p class="prose">(.*?)</p>', card_html, re.DOTALL)
        card['proseTexts'] = prose_matches

        # Extract coaching hint divs
        coaching_match = re.search(r'<div id="([^"]*CoachingHint)"', card_html)
        if coaching_match:
            card['coachingHintId'] = coaching_match.group(1)

        # Extract tip box
        tip_match = re.search(r'<div class="tip-box">(.*?)</div>\s*(?=<|$)', card_html, re.DOTALL)
        if tip_match:
            card['tipBox'] = '<div class="tip-box">' + tip_match.group(1) + '</div>'

        # Extract warning box
        warning_match = re.search(r'<div class="warning-box">(.*?)</div>\s*(?=<|$)', card_html, re.DOTALL)
        if warning_match:
            card['warningBox'] = '<div class="warning-box">' + warning_match.group(1) + '</div>'

        # Extract study citations
        study_cite_pattern = r'<div class="study-citation">(.*?)</div>'
        study_matches = re.finditer(study_cite_pattern, card_html, re.DOTALL)
        for study_match in study_matches:
            card['studyCitations'].append('<div class="study-citation">' + study_match.group(1) + '</div>')

        # Extract study refs
        study_refs_pattern = r'<div class="study-refs">(.*?)</div>'
        refs_match = re.search(study_refs_pattern, card_html, re.DOTALL)
        if refs_match:
            card['studyRefs'] = [refs_match.group(1)]

        cards.append(card)

    return cards


def extract_coaching_hints_js(html: str) -> str:
    """Extract the loadCoachingHints function as raw JS string."""
    pattern = r'function loadCoachingHints\(\) \{(.*?)\n\s*\}\s*\n\s*loadCoachingHints\(\);'
    match = re.search(pattern, html, re.DOTALL)

    if match:
        function_body = match.group(1)
        return f"""function loadCoachingHints() {{{function_body}
        }}

        loadCoachingHints();"""

    return ""


def extract_ratings_js(html: str) -> str:
    """Extract ratings JS block (returns empty if not present)."""
    pattern = r'(const RATING_KEY = .*?checkUserStatus\(\);)'
    match = re.search(pattern, html, re.DOTALL)

    if match:
        return match.group(1)

    return ""


def has_coaching_hints(html: str) -> bool:
    """Check if page includes coaching hints."""
    return 'loadCoachingHints()' in html


def has_ratings(html: str) -> bool:
    """Check if page includes ratings system."""
    return 'RATING_KEY' in html


def get_rating_key(html: str) -> str:
    """Extract the RATING_KEY value."""
    match = re.search(r"const RATING_KEY = '([^']+)'", html)
    if match:
        return match.group(1)
    return ""


def extract_evidence_page(filepath: str) -> Dict[str, Any]:
    """Extract all data from an evidence HTML page."""
    html = read_html_file(filepath)

    data = {
        'pageConfig': extract_page_config(html),
        'cards': extract_cards(html),
        'includeCoachingHints': has_coaching_hints(html),
        'includeRatings': has_ratings(html),
        'ratingKey': get_rating_key(html),
        'coachingHintsJs': extract_coaching_hints_js(html) if has_coaching_hints(html) else "",
        'ratingsJs': extract_ratings_js(html) if has_ratings(html) else ""
    }

    return data


def build_card_html(card: Dict[str, Any], is_first: bool = False) -> str:
    """Build HTML for a single FAQ card."""
    heading_tag = "h1" if is_first else "h2"

    html = f"""        <div class="faq-card" id="{card['id']}">
            <div class="faq-header" onclick="toggleFaq('{card['id']}')">
                <div class="faq-header-content">
                    <{heading_tag} class="faq-question-title">{card['title']}</{heading_tag}>"""

    if card['readTime'] or card['metaText']:
        html += f"""
                    <div class="faq-meta">"""
        if card['readTime']:
            html += f"""
                        <span>{card['readTime']} min read</span>"""
            if card['metaText']:
                html += f"""
                        <span class="faq-meta-divider">&middot;</span>
                        <span>{card['metaText']}</span>"""
        elif card['metaText']:
            html += f"""
                        <span>{card['metaText']}</span>"""
        html += f"""
                    </div>"""

    if card['preview']:
        html += f"""
                    <div class="faq-preview">{card['preview']}</div>"""

    html += f"""
                </div>
                <i data-lucide="chevron-down" class="faq-toggle" style="width:20px;height:20px;"></i>
            </div>
            <div class="faq-content">
                <div class="quick-answer">
                    <div class="quick-answer-label">Quick Answer</div>
                    <div class="quick-answer-text">
                        {card['quickAnswer']}
                    </div>
                </div>
"""

    if card['table']:
        html += f"""
                {card['table']}
"""

    for prose in card['proseTexts']:
        html += f"""
                <p class="prose">
                    {prose}
                </p>
"""

    for citation in card['studyCitations']:
        html += f"""
                {citation}
"""

    if card['coachingHintId']:
        html += f"""
                <div id="{card['coachingHintId']}"></div>
"""

    if card['tipBox']:
        html += f"""
                {card['tipBox']}
"""

    if card['warningBox']:
        html += f"""
                {card['warningBox']}
"""

    if card['studyRefs']:
        for ref in card['studyRefs']:
            html += f"""
                <div class="study-refs">
                    {ref}
                </div>
"""

    html += f"""
            </div>
        </div>
"""

    return html


def build_page(config: Dict[str, Any], template_path: str = None) -> str:
    """Build complete HTML page from embedded template and config."""
    template = TEMPLATE_HTML

    # Build cards HTML
    cards_html = ""
    for idx, card in enumerate(config['cards']):
        cards_html += build_card_html(card, is_first=(idx == 0))

    # Replace placeholders
    page = template.replace('{{HEADER_TITLE}}', config['pageConfig'].get('headerTitle', ''))
    page = page.replace('{{DIMENSION}}', config['pageConfig'].get('dimension', ''))
    page = page.replace('{{CTA_TITLE}}', config['pageConfig'].get('ctaTitle', ''))
    page = page.replace('{{CTA_TEXT}}', config['pageConfig'].get('ctaText', ''))
    page = page.replace('{{FOOTER_CTA_TEXT}}', config['pageConfig'].get('footerCtaText', ''))
    page = page.replace('{{FOOTER_ICON}}', config['pageConfig'].get('footerIcon', 'play'))
    page = page.replace('{{FOOTER_BUTTON_TEXT}}', config['pageConfig'].get('footerButtonText', ''))
    page = page.replace('{{FOOTER_CTA_META}}', config['pageConfig'].get('footerCtaMeta', ''))
    page = page.replace('{{LAST_UPDATED}}', config['pageConfig'].get('lastUpdated', 'February 2026'))
    page = page.replace('{{CARDS}}', cards_html)

    # Handle coaching hints
    if config['includeCoachingHints'] and config['coachingHintsJs']:
        page = page.replace('{{COACHING_HINTS_JS}}', config['coachingHintsJs'])
    else:
        page = page.replace('{{COACHING_HINTS_JS}}', '')

    # Handle ratings
    if config['includeRatings'] and config['ratingsJs']:
        page = page.replace('{{RATINGS_JS}}', config['ratingsJs'])
    else:
        page = page.replace('{{RATINGS_JS}}', '')

    return page


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python evidence-builder.py [--extract FILE | --check SLUG | --all | SLUG]")
        print("Commands:")
        print("  --extract FILE     Extract data from existing HTML file")
        print("  --check SLUG       Build in-memory and compare to existing")
        print("  --all              Build all evidence pages in evidence-pages/")
        print("  SLUG               Build evidence-SLUG.html from evidence-pages/SLUG.json")
        sys.exit(1)

    cmd = sys.argv[1]
    system_dir = Path(__file__).parent
    evidence_dir = system_dir / 'evidence-pages'
    # Template is embedded in TEMPLATE_HTML constant above

    if cmd == '--extract':
        if len(sys.argv) < 3:
            print("Usage: python evidence-builder.py --extract FILE")
            sys.exit(1)

        input_file = system_dir / sys.argv[2]
        if not input_file.exists():
            print(f"Error: File not found: {input_file}")
            sys.exit(1)

        print(f"Extracting from {input_file.name}...")
        data = extract_evidence_page(str(input_file))

        # Infer slug from page config
        slug = data['pageConfig'].get('headerTitle', 'unknown').lower().replace(' ', '-').replace('faq', '').strip('-')

        # Write JSON
        output_file = evidence_dir / f'{slug}.json'
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

        print(f"Extracted {len(data['cards'])} cards")
        print(f"Config: headerTitle='{data['pageConfig'].get('headerTitle', '')}', dimension='{data['pageConfig'].get('dimension', '')}'")
        print(f"Features: coachingHints={data['includeCoachingHints']}, ratings={data['includeRatings']}")
        print(f"Saved to {output_file}")

    elif cmd == '--check':
        if len(sys.argv) < 3:
            print("Usage: python evidence-builder.py --check SLUG")
            sys.exit(1)

        slug = sys.argv[2]
        json_file = evidence_dir / f'{slug}.json'

        if not json_file.exists():
            print(f"Error: JSON file not found: {json_file}")
            sys.exit(1)

        with open(json_file, 'r', encoding='utf-8') as f:
            config = json.load(f)

        built_page = build_page(config, None)

        html_file = system_dir / config.get('outputFile', f'evidence-{slug}.html')
        if html_file.exists():
            with open(html_file, 'r', encoding='utf-8') as f:
                existing = f.read()

            if built_page == existing:
                print(f"MATCH: {html_file.name} matches built output")
            else:
                print(f"MISMATCH: {html_file.name} differs from built output")
                print("Differences detected - pages are out of sync")
        else:
            print(f"NEW: {html_file.name} would be created")

    elif cmd == '--all':
        if not evidence_dir.exists():
            print(f"Error: Directory not found: {evidence_dir}")
            sys.exit(1)

        json_files = list(evidence_dir.glob('*.json'))
        if not json_files:
            print(f"No JSON files found in {evidence_dir}")
            sys.exit(1)

        print(f"Building {len(json_files)} evidence pages...")
        for json_file in json_files:
            slug = json_file.stem

            with open(json_file, 'r', encoding='utf-8') as f:
                config = json.load(f)

            built_page = build_page(config, None)

            output_file = system_dir / config.get('outputFile', f'evidence-{slug}.html')
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(built_page)

            print(f"Built {output_file.name} ({len(config['cards'])} cards)")

        print(f"Done! Built {len(json_files)} pages")

    else:
        # Default: build from SLUG
        slug = cmd
        json_file = evidence_dir / f'{slug}.json'

        if not json_file.exists():
            print(f"Error: JSON file not found: {json_file}")
            sys.exit(1)

        with open(json_file, 'r', encoding='utf-8') as f:
            config = json.load(f)

        output_file = system_dir / config.get('outputFile', f'evidence-{slug}.html')
        print(f"Building {output_file.name} from {json_file.name}...")
        built_page = build_page(config, None)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(built_page)

        print(f"Built {output_file.name}")
        print(f"Cards: {len(config['cards'])}")
        print(f"Features: coachingHints={config['includeCoachingHints']}, ratings={config['includeRatings']}")


if __name__ == '__main__':
    main()
