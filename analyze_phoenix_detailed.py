from pathlib import Path

import fitz

pdf_path = Path("data/phoenix/sign_f2250048380.pdf")
doc = fitz.open(pdf_path)
print(f"Analyzing: {pdf_path.name}")
print(f"Pages: {len(doc)}\n")

for page_num in range(min(2, len(doc))):
    page = doc[page_num]
    print(f"=== PAGE {page_num + 1} ===")
    print(f"Size: {page.rect.width}x{page.rect.height}")

    # Use blocks extraction which handles encoding better
    blocks = page.get_text("blocks")

    print("\nText blocks with positions:")
    for block in blocks:
        bbox = block[:4]  # x0, y0, x1, y1
        text = block[4]  # text content
        
        # Split into lines and print each
        for line in text.strip().split('\n'):
            line = line.strip()
            if line:
                print(f"  [{bbox[0]:.1f}, {bbox[1]:.1f}, {bbox[2]:.1f}, {bbox[3]:.1f}] {line[:80]}")

    print("\n" + "=" * 60 + "\n")

