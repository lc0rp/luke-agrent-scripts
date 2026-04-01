# QA Checklist

Use this checklist exactly. The scorer expects these ids, weights, blocking flags, and review rules.

## Page Checks

| id | Weight | Blocking | Pass when | Fail when | Typical `not_applicable` case |
|---|---:|---|---|---|---|
| `layout_structure` | 10 | no | Major sections, columns, and page rhythm remain recognizably aligned with the source. | Sections drift materially or the page hierarchy is visibly distorted. | Rare. |
| `heading_placement` | 5 | no | Headings, titles, and section emphasis remain correctly placed. | Headings are missing, demoted, misplaced, or collide with body content. | Pages with no heading-like content. |
| `text_readability` | 15 | yes | Main translated text is fully legible at normal zoom. | Text is crowded, obscured, too small, clipped, or partially unreadable. | Rare. |
| `text_overlap_absent` | 15 | yes | No text overlaps or collisions are visible anywhere on the page. | Any overlapping text, stacked lines, or text crossing another text region is visible. | Never. |
| `icon_or_bullet_collision_absent` | 10 | yes | Bullets, icons, and adjacent text remain cleanly separated. | Bullet or icon gutters collapse, or text collides with bullets or icons. | Pages without bullets, icons, or bullet-like markers. |
| `table_or_form_cell_overflow_absent` | 10 | yes | Table/form text stays within cells or form rows. | Text spills out of cells, crosses borders, or collapses row structure. | Pages without tables or form-like structures. |
| `duplicate_draw_or_ocr_junk_absent` | 10 | yes | No duplicate text draws, OCR fragments, or stray rendering debris is visible. | Duplicate text, OCR garbage, stray fragments, or ghost text appears. | Never. |
| `lists_tables_forms` | 10 | no | Lists, tables, and forms remain structurally usable. | Rows, bullets, numbering, or cells lose structural usability. | Pages without any of these structures. |
| `headers_footers_branding` | 5 | no | Headers, footers, logos, and branded line work remain intact. | Header/footer content is missing, broken, detached, or visibly wrong. | Pages without these elements. |
| `non_text_artifacts` | 5 | no | Signatures, stamps, seals, arrows, icons, or similar non-text artifacts survive appropriately. | Important non-text artifacts are missing, corrupted, or collide with text. | Pages without these artifacts. |
| `translation_quality` | 5 | no | Visible target-language wording is natural and terminology-consistent. | Wording is visibly awkward, inconsistent, mistranslated, or leaves text untranslated without reason. | Pages with effectively no translatable text. |

## Mandatory Hotspots

Every page must have hotspot coverage for:

- `top_band`
- `middle_band`
- `bottom_band`
- `densest_region`

`structured_region` is also required when any of these checks are applicable:

- `icon_or_bullet_collision_absent`
- `table_or_form_cell_overflow_absent`
- `lists_tables_forms`
- `non_text_artifacts`

## Challenger Review

Every page that would otherwise pass must get a challenger review.

Allowed challenger statuses:

- `clear`
- `flagged`
- `not_run`

Rules:

- `not_run` is invalid on an otherwise passing page
- `flagged` forces `review_status = needs_review`
- a page with `review_status = needs_review` cannot produce overall pass

## Scoring

### Page score

Page score =:

`round(100 * passed_applicable_weight / total_applicable_weight)`

Where:

- `pass` contributes full weight
- `fail` contributes zero
- `not_applicable` is removed from the denominator

### Page verdict

Page verdict = `pass` only when all are true:

- page score is at least `90`
- no check failed
- no blocking check failed
- mandatory hotspots are complete
- challenger status is `clear`
- page review status is `confirmed`

Otherwise page verdict = `fail`.

### Overall score

Overall score = rounded arithmetic mean of all page scores.

### Overall verdict

Overall verdict = `pass` only when all are true:

- every page verdict is `pass`
- no page review status is `needs_review`
- document page counts match
- every side-by-side image referenced by the comparison report exists
- overall score is at least `90`

Otherwise overall verdict = `fail`.

## Quality Bands

- `excellent`: 90-100
- `good`: 80-89
- `acceptable`: 70-79
- `poor`: 0-69

## Review Status

Use these exact review status values:

- `confirmed`
- `needs_review`

Keep `overall.status` as `pass` or `fail`. Use `review_status` to carry the challenger/manual-review escalation without breaking optimizer handoff.

## Issue Severity

Use these exact severity values:

- `blocking`
- `major`
- `minor`

Use at least one issue entry on every failed page.

## Evidence and Remediation Rules

- `evidence` must identify a visible page region or object
- `remediation` must name a concrete rebuild or translation action
- generic evidence is invalid
- duplicated evidence strings across multiple checks on the same page are invalid
