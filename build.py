#!/usr/bin/env python3
"""
LongevityPath Build Script — Inject questions.json into index.html

Keeps question data in a standalone JSON file for easy editing, while
producing a single self-contained HTML file that works in every browser
(including file:// on mobile).

Usage:
    python build.py                  Inject questions.json → index.html
    python build.py --extract        Extract CATEGORIES from index.html → questions.json
    python build.py --check          Verify index.html matches questions.json (no changes)
"""

import argparse
import json
import re
import sys
from pathlib import Path

DIR = Path(__file__).parent
INDEX = DIR / "index.html"
QUESTIONS = DIR / "questions.json"

# Markers in index.html that delimit the CATEGORIES block
MARKER_START = "// __QUESTIONS_START__"
MARKER_END   = "// __QUESTIONS_END__"

# Regex for marker-based block (after first extract)
RE_MARKER_BLOCK = re.compile(
    r'([ \t]*' + re.escape(MARKER_START) + r').*?(' + re.escape(MARKER_END) + r')',
    re.DOTALL
)

# Regex for raw CATEGORIES block (before first extract)
RE_RAW_BLOCK = re.compile(
    r'([ \t]*const CATEGORIES = \{).*?(\};)',
    re.DOTALL
)


def read_index():
    return INDEX.read_text(encoding="utf-8")


def build_marker_block(data):
    """Build the full marker block string for injection."""
    raw = json.dumps(data, indent=4, ensure_ascii=False)
    # Re-indent to match 8-space position inside <script> block
    lines = raw.split("\n")
    prefix = "            "
    js_block = lines[0]
    for line in lines[1:]:
        js_block += "\n" + prefix + line

    return (
        f"        {MARKER_START}\n"
        f"        const CATEGORIES = {js_block};\n"
        f"        {MARKER_END}"
    )


def js_object_to_json(js_text):
    """Convert JS object literal to valid JSON."""
    t = js_text

    # Remove JS comments
    t = re.sub(r'//.*?$', '', t, flags=re.MULTILINE)

    # Convert single-quoted JS strings to double-quoted JSON strings.
    # Handles apostrophes inside strings (don't, it's) by checking
    # if the char after ' is a word char (apostrophe) or not (closing quote).
    result = []
    i = 0
    while i < len(t):
        ch = t[i]
        if ch == "'":
            j = i - 1
            while j >= 0 and t[j] in ' \t\n\r':
                j -= 1
            prev = t[j] if j >= 0 else ''

            if prev in ':,[{(':
                end = i + 1
                content = []
                while end < len(t):
                    if t[end] == '\\':
                        content.append(t[end:end+2])
                        end += 2
                        continue
                    if t[end] == "'":
                        next_ch = t[end + 1] if end + 1 < len(t) else ''
                        if next_ch.isalpha():
                            content.append(t[end])
                            end += 1
                            continue
                        else:
                            break
                    if t[end] == '"':
                        content.append('\\"')
                        end += 1
                        continue
                    content.append(t[end])
                    end += 1
                result.append('"')
                result.append(''.join(content))
                result.append('"')
                i = end + 1
                continue
            else:
                result.append(ch)
        else:
            result.append(ch)
        i += 1
    t = ''.join(result)

    # Quote unquoted keys
    t = re.sub(r'(?<=[{,\n])\s*(\w+)\s*:', r' "\1":', t)

    # Remove trailing commas
    t = re.sub(r',\s*([}\]])', r'\1', t)

    return t


def cmd_extract(html):
    """Extract CATEGORIES from index.html and write questions.json."""
    # Find the raw CATEGORIES JS object content
    lines = html.split("\n")
    start_idx = end_idx = None
    for i, line in enumerate(lines):
        if "const CATEGORIES = {" in line and start_idx is None:
            start_idx = i
        if start_idx is not None and i > start_idx and line.strip() == "};":
            end_idx = i
            break

    if start_idx is None or end_idx is None:
        # Try marker-based
        m = RE_MARKER_BLOCK.search(html)
        if not m:
            print("ERROR: Cannot find CATEGORIES block in index.html", file=sys.stderr)
            sys.exit(1)
        inner = m.group(0)
        # Extract between markers
        inner = inner.split(MARKER_START)[1].split(MARKER_END)[0].strip()
        if inner.startswith("const CATEGORIES ="):
            inner = inner[len("const CATEGORIES ="):].strip().rstrip(";").strip()
        full = inner
    else:
        block = "\n".join(lines[start_idx:end_idx + 1])
        full = block.replace("const CATEGORIES =", "", 1).strip().rstrip(";").strip()

    # Convert to JSON
    json_text = js_object_to_json(full)
    try:
        data = json.loads(json_text)
    except json.JSONDecodeError as e:
        print(f"ERROR: Failed to parse CATEGORIES as JSON: {e}", file=sys.stderr)
        debug = DIR / "questions-debug.json"
        debug.write_text(json_text, encoding="utf-8")
        print(f"Debug output written to {debug}", file=sys.stderr)
        sys.exit(1)

    QUESTIONS.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    q_count = sum(
        len(sec.get("questions", []))
        for cat in data.values()
        for sec in cat.get("sections", {}).values()
    )
    print(f"Extracted {len(data)} categories, {q_count} questions → {QUESTIONS.name}")

    # Inject markers into index.html using regex replacement
    marker_block = build_marker_block(data)

    if RE_MARKER_BLOCK.search(html):
        new_html = RE_MARKER_BLOCK.sub(marker_block, html)
    elif RE_RAW_BLOCK.search(html):
        new_html = RE_RAW_BLOCK.sub(marker_block, html)
    else:
        print("ERROR: Cannot find block to replace", file=sys.stderr)
        sys.exit(1)

    INDEX.write_text(new_html, encoding="utf-8")
    print(f"Injected markers into {INDEX.name}")


def cmd_inject():
    """Read questions.json and inject into index.html."""
    if not QUESTIONS.exists():
        print(f"ERROR: {QUESTIONS} not found. Run --extract first.", file=sys.stderr)
        sys.exit(1)

    data = json.loads(QUESTIONS.read_text(encoding="utf-8"))
    html = read_index()
    marker_block = build_marker_block(data)

    if RE_MARKER_BLOCK.search(html):
        new_html = RE_MARKER_BLOCK.sub(marker_block, html)
    elif RE_RAW_BLOCK.search(html):
        new_html = RE_RAW_BLOCK.sub(marker_block, html)
    else:
        print("ERROR: Cannot find CATEGORIES block in index.html", file=sys.stderr)
        sys.exit(1)

    INDEX.write_text(new_html, encoding="utf-8")

    q_count = sum(
        len(sec.get("questions", []))
        for cat in data.values()
        for sec in cat.get("sections", {}).values()
    )
    print(f"Injected {len(data)} categories, {q_count} questions → {INDEX.name}")


def cmd_check():
    """Verify index.html matches questions.json without making changes."""
    if not QUESTIONS.exists():
        print(f"ERROR: {QUESTIONS} not found.", file=sys.stderr)
        sys.exit(1)

    data = json.loads(QUESTIONS.read_text(encoding="utf-8"))
    html = read_index()
    marker_block = build_marker_block(data)

    if RE_MARKER_BLOCK.search(html):
        expected = RE_MARKER_BLOCK.sub(marker_block, html)
    elif RE_RAW_BLOCK.search(html):
        expected = RE_RAW_BLOCK.sub(marker_block, html)
    else:
        print("ERROR: Cannot find CATEGORIES block in index.html", file=sys.stderr)
        sys.exit(1)

    if html == expected:
        print("OK: index.html matches questions.json")
        sys.exit(0)
    else:
        print("MISMATCH: index.html does not match questions.json. Run `python build.py` to sync.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LongevityPath build: manage questions.json ↔ index.html")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--extract", action="store_true", help="Extract CATEGORIES → questions.json")
    group.add_argument("--check", action="store_true", help="Verify index.html matches questions.json")
    args = parser.parse_args()

    if args.extract:
        cmd_extract(read_index())
    elif args.check:
        cmd_check()
    else:
        cmd_inject()
