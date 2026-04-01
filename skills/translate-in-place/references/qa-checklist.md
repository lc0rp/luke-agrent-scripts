# QA Checklist

## Always verify

- page count is sensible, including any continuation pages
- headers and footers are translated where they contain translatable text
- logos and non-text images remain in place
- tables still read correctly and retain structure
- flow-chart arrows, connector lines, and directional markers still exist and remain correctly oriented
- bold headers, bold inline emphasis, and other meaningful typographic distinctions are preserved or acceptably approximated
- bullet indentation, wrapped bullet indentation, numbering, and text alignment remain close to the source
- handwritten names, handwritten dates, initials, stamps, seals, and signatures remain visible
- overlay fill color matches the original page background, or has been deliberately normalized to white and noted
- continuation pages are clearly labeled and referenced in notes

## Pages that require visual inspection

- every page with a signature or handwritten annotation
- every page with stamps or seals
- title pages
- any page with a flow chart, decision tree, process diagram, or connector arrows
- any page with bold-heavy hierarchy, nested bullets, or alignment-sensitive layout
- any page with OCR fallback
- any page with continuation overflow
- any page flagged by `compare_rendered_pages.py` as highly divergent or suspiciously blank

## Notes file must record

- translation backend used
- backend fallback errors and why the final backend was chosen
- pages that used OCR
- pages that required magnification
- pages that overflowed to continuation pages
- pages where exact in-place reproduction was not possible
- pages where arrows, connector lines, or diagram glyphs had to be manually preserved or could not be matched exactly
- pages where bold/emphasis, list indentation, or alignment could not be matched exactly
- pages where overlay background was normalized to white instead of sampled
- pages visually inspected in the final pass
- whether comparison showed page-count parity and which pages were machine-flagged
- any wording-quality caveat if a lower-quality fallback translator was used
