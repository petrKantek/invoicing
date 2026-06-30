"""Draw bounding boxes on PDF with labels for invoice fields."""

from pathlib import Path

import fitz

# Input and output paths
pdf_path = Path("data/phoenix/sign_f2250048380.pdf")
output_path = Path("data/output/phoenix_annotated.pdf")

# Open PDF
doc = fitz.open(pdf_path)

# Define which text patterns map to which field names
field_mapping = {
    "invoice_number": ["č. 2250048380"],
    "issue_date": ["22.11.2025"],
    "due_date": ["DATUM SPLATNOSTI:", "22.12.2025"],
    "supply_date": ["24.11.2025"],
    "supplier_name": ["PHOENIX lékárenský velkoobchod, s.r.o."],
    "supplier_ic": ["IČO: 45359326"],
    "supplier_dic": ["DIČ: CZ45359326"],
    "total_amount": ["ČÁSTKA K ÚHRADĚ:", "152 321,03"],
    "vat_12_base": ["124 606,96"],
    "vat_12_amount": ["14 952,84"],
    "vat_21_base": ["10 546,47"],
    "vat_21_amount": ["2 214,76"],
}

# Track which bboxes we've already drawn to avoid duplicates
drawn_bboxes = set()

# Process each page
for page_num in range(len(doc)):
    page = doc[page_num]
    blocks = page.get_text("blocks")

    # Track which fields we've found to avoid duplicates
    found_fields = set()

    for block in blocks:
        bbox = block[:4]  # x0, y0, x1, y1
        text = block[4].strip()

        # Skip if we've already drawn this exact bbox
        bbox_key = tuple(round(x, 1) for x in bbox)
        if bbox_key in drawn_bboxes:
            continue

        # Check if this block matches any field
        for field_name, patterns in field_mapping.items():
            # Skip if we already found this field
            if field_name in found_fields:
                continue

            # Check if any pattern matches this block's text
            for pattern in patterns:
                if pattern in text:
                    # Draw rectangle
                    rect = fitz.Rect(bbox)

                    # Use different colors for different field types
                    if "vat" in field_name:
                        color = fitz.utils.getColor("blue")
                    elif "date" in field_name:
                        color = fitz.utils.getColor("green")
                    elif "supplier" in field_name:
                        color = fitz.utils.getColor("purple")
                    elif "total" in field_name or "amount" in field_name:
                        color = fitz.utils.getColor("red")
                    else:
                        color = fitz.utils.getColor("orange")

                    # Draw the bounding box
                    annot = page.add_rect_annot(rect)
                    annot.set_colors(stroke=color)
                    annot.set_border(width=2)
                    annot.update()

                    # Add text label above the box
                    label_point = fitz.Point(bbox[0], bbox[1] - 5)
                    page.insert_text(
                        label_point,
                        field_name,
                        fontsize=8,
                        color=color,
                        fontname="helv",
                    )

                    # Mark as drawn and found
                    drawn_bboxes.add(bbox_key)
                    found_fields.add(field_name)
                    break

# Save annotated PDF
output_path.parent.mkdir(parents=True, exist_ok=True)
doc.save(output_path)
doc.close()

print(f"✓ Annotated PDF saved to: {output_path}")
print(f"✓ Total bounding boxes drawn: {len(drawn_bboxes)}")
