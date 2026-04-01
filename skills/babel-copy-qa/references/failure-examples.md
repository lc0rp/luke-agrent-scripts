# Failure Examples

Use these examples to calibrate `gpt-5.4-mini` toward local defect detection instead of page-level optimism.

## F1 page 3

Source comparison images:

- [/Users/luke/dev/translate/output/optimization-loop/cycles/20260331T200040Z/documents/F1/attempts/20260331T200040Z-initial/compare/page-003.png](/Users/luke/dev/translate/output/optimization-loop/cycles/20260331T200040Z/documents/F1/attempts/20260331T200040Z-initial/compare/page-003.png)
- [/Users/luke/dev/translate/output/optimization-loop/cycles/20260331T193104Z/documents/F1/attempts/20260331T193104Z-initial/compare/page-003.png](/Users/luke/dev/translate/output/optimization-loop/cycles/20260331T193104Z/documents/F1/attempts/20260331T193104Z-initial/compare/page-003.png)

Required interpretation:

- This page must fail.
- The bottom software-used bullet block collides with the green check icons.
- At minimum these checks should fail:
  - `text_overlap_absent`
  - `icon_or_bullet_collision_absent`
  - `text_readability`

## F3 page 1

Source comparison images:

- [/Users/luke/dev/translate/output/optimization-loop/cycles/20260331T200040Z/documents/F3/attempts/20260331T200040Z-initial/compare/page-001.png](/Users/luke/dev/translate/output/optimization-loop/cycles/20260331T200040Z/documents/F3/attempts/20260331T200040Z-initial/compare/page-001.png)
- [/Users/luke/dev/translate/output/optimization-loop/cycles/20260331T193104Z/documents/F3/attempts/20260331T193104Z-initial/compare/page-001.png](/Users/luke/dev/translate/output/optimization-loop/cycles/20260331T193104Z/documents/F3/attempts/20260331T193104Z-initial/compare/page-001.png)

Required interpretation:

- This page must fail.
- There is clear overlapping text in the translated page around the `NEW:` block.
- At minimum these checks should fail:
  - `text_overlap_absent`
  - `text_readability`

## Lesson

When a page contains one obviously broken local region, do not let an otherwise clean page layout pass.

Local blockers outrank global page neatness.
