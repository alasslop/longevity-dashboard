# LongevityPath Project Instructions

## MANDATORY: Read Before Any Changes

Before making ANY code or content changes, read these files in order:

1. **`system/ARCHITECTURE.md`** — system architecture, data shapes, scoring logic, design decisions. **Always read this first.** It prevents you from breaking existing patterns or contradicting prior decisions.
2. The relevant skill(s) listed below.

Failure to read system/ARCHITECTURE.md first will lead to inconsistencies.

## Skill Priority: Editable Skills First

When loading skills for this project, always check `.claude/skills/` first. If a skill exists in both `.claude/skills/` (editable) and `.skills/skills/` (read-only plugin), the `.claude/skills/` version is the single source of truth. Ignore the `anthropic-skills:` prefixed version.

## Available Skills

| Skill | When to use | Location |
|-------|-------------|----------|
| **writing-longevity-lifestyle-test** | Any content work: writing, evidence pages, HTML build pipeline (§13), voice, tradeoffs, claims | `.claude/skills/` (editable) |
| **study-usage-guide** | Any citation or research work (7-factor evaluation, scoring, reference format) | `.claude/skills/` (editable) |
| **skill-editing** | Editing any skill file | `.claude/skills/` (editable) |

**Single-source-of-truth rule:** Each topic is owned by exactly one document. Skills reference each other but never duplicate content. See system/ARCHITECTURE.md §Documentation Principles.

## Folder Structure

- **Root** — website content (HTML pages, .docx source files, brand.css)
- **system/** — architecture docs, database, CLI tools, validation scripts
- **Deleted/** — obsolete files awaiting permanent deletion
- **.claude/skills/** — editable AI skill definitions
- **.skills/** — read-only plugin skills

## Delete the Deleted/ Folder

Once confirmed everything works, permanently remove the Deleted/ folder and all its contents.
