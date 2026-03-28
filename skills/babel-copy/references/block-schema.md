# Block Schema

Use a compact JSON structure. Keep it stable across extraction, translation, and rebuild stages.

## Payload

```json
{
  "input_pdf": "/abs/path/source.pdf",
  "page_count": 3,
  "block_count": 42,
  "pages": [
    {
      "page_number": 3,
      "page_type": "mixed",
      "strategy_hint": "rebuild",
      "width": 595.08,
      "height": 841.68,
      "render_path": "/abs/path/page-renders/page-003.png",
      "asset_ids": ["p3-a1", "p3-sig1"],
      "tables": [
        {
          "id": "p3-table-1",
          "bbox": [84.7, 199.9, 531.3, 598.7],
          "columns": [84.7, 307.0, 531.3],
          "rows": [199.9, 231.1, 330.8, 362.1, 463.3, 497.5, 598.7],
          "cells": [
            {
              "id": "p3-tp3-table-1-r5-c1",
              "row_index": 5,
              "col_index": 1,
              "bbox": [307.0, 497.5, 531.3, 598.7],
              "block_ids": ["p3-b12"],
              "signature_asset_ids": ["p3-sig3"]
            }
          ]
        }
      ]
    }
  ],
  "blocks": [],
  "assets": []
}
```

## Block

```json
{
  "id": "p1-b12",
  "page_number": 1,
  "bbox": [83.2, 431.0, 530.4, 449.2],
  "text": "A la demande du Régulateur BCEAO...",
  "role": "paragraph",
  "align": "left",
  "style": {
    "font_size_hint": 10.0,
    "font_name": "Cambria",
    "flags": 4,
    "color": 1521502,
    "text_fill_color": "#17387E",
    "bold": false,
    "italic": false
  },
  "list": null,
  "table": {
    "table_id": "p3-table-1",
    "cell_id": "p3-tp3-table-1-r5-c1",
    "row_index": 5,
    "col_index": 1
  },
  "keep_original": false,
  "artifact_risk": "low"
}
```

## Asset

```json
{
  "id": "p3-sig3",
  "page_number": 3,
  "kind": "signature_crop",
  "origin": "page_render",
  "bbox": [318.4, 526.7, 474.2, 577.9],
  "path": "/abs/path/assets/page-003-table-p3-table-1-cell-5-1-signature.png",
  "image_size_px": [311, 103],
  "placement": {
    "mode": "page_absolute",
    "table_id": "p3-table-1",
    "cell_id": "p3-tp3-table-1-r5-c1"
  }
}
```

## Roles

- `title`
- `heading`
- `paragraph`
- `list_item`
- `table_cell`
- `form_label`
- `header`
- `footer`
- `signature_label`
- `artifact`

## Notes

- `header` and `footer` text should be translated unless they are purely non-linguistic marks.
- `keep_original: true` is for non-text or non-translatable visual elements, not for repeated boilerplate text.
- `style.font_name`, `style.flags`, `style.color`, and `style.text_fill_color` are block-level summaries for native text only, not full per-span style runs.
- OCR-derived blocks should serialize those native-style summary fields as `null`.

## Keep Original

Set `keep_original: true` for:

- signatures
- handwritten names or dates
- seals and stamps
- non-text decorative or legal marks
- diagram arrows or connectors that are hard to reconstruct

## Translation Notes

Store translation-specific data separately from source extraction. Do not overwrite the source block text in place until you produce `translated_blocks.json`.
