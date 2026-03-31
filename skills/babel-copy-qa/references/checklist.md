# QA Checklist

Use this checklist exactly. The scorer expects these ids, weights, and blocking flags.

## Page Checks

| id | Weight | Blocking | Pass when | Fail when | Typical `not_applicable` case |
|---|---:|---|---|---|---|
| `layout_structure` | 15 | no | Major sections, columns, and visual hierarchy match the source page closely enough to feel like the same document. | Sections drift materially, spacing breaks the page rhythm, or hierarchy is visibly distorted. | Rare. |
| `heading_placement` | 10 | no | Titles and section headings remain correctly placed, sized, and emphasized. | Headings are missing, demoted, misplaced, or collide with body content. | Pages with no heading-like content. |
| `text_readability` | 20 | yes | Main translated text is legible, complete, and readable at normal zoom. | Text is too small, truncated, faint, crowded, or partially missing. | Rare. |
| `overflow_or_collision_absent` | 20 | yes | No overlap, clipping, duplicate draws, spillover, or stray OCR junk is visible. | Any visible overlap, clipping, duplicated text, margin spill, or obvious OCR debris exists. | Never. |
| `lists_tables_forms` | 10 | no | Bullets, numbered lists, tables, and form-like rows remain structurally usable. | Rows break, bullets drift, cells collapse, or form structure becomes confusing. | Pages without any of these structures. |
| `headers_footers_branding` | 10 | no | Headers, footers, logos, and branded line work remain intact and visually consistent. | Footer/header content is missing, broken, mistranslated, or visually detached from the page. | Pages without these elements. |
| `non_text_artifacts` | 5 | no | Signatures, stamps, arrows, icons, seals, and similar non-text artifacts survive appropriately. | Any important non-text artifact is missing, corrupted, or collides with text. | Pages without these artifacts. |
| `translation_quality` | 10 | no | The visible target-language wording is natural, correct, and terminology-consistent for the page. | Wording is visibly awkward, incorrect, inconsistent, or partially untranslated in a way that should be fixed. | Only if the page has effectively no translatable text. |

## Scoring

### Page score

Page score =:

`round(100 * passed_applicable_weight / total_applicable_weight)`

Where:

- `pass` contributes full weight
- `fail` contributes zero
- `not_applicable` is removed from the denominator

### Page verdict

Page verdict = `pass` only when both are true:

- page score is at least `85`
- no blocking check failed

Otherwise page verdict = `fail`.

### Overall score

Overall score = rounded arithmetic mean of all page scores.

### Overall verdict

Overall verdict = `pass` only when all are true:

- every page verdict is `pass`
- document page counts match
- every side-by-side image referenced by the comparison report exists
- overall score is at least `85`

Otherwise overall verdict = `fail`.

## Quality Bands

- `excellent`: 90-100
- `good`: 80-89
- `acceptable`: 70-79
- `poor`: 0-69

## Issue Severity

Use these exact severity values:

- `blocking`: would stop sign-off immediately
- `major`: important defect, but not catastrophic on its own
- `minor`: polish issue or small wording/layout defect

Use at least one issue entry on every failed page.

## Evidence and Remediation Rules

- `evidence` should point to the visible problem on the rendered page
- `remediation` should tell the operator what to change in the rebuild or translation pass
- keep each field to 1-2 sentences
- avoid generic advice
