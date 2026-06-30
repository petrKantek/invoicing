import fitz

doc = fitz.open("data/phoenix/sign_f2250048380.pdf")
print(f"Pages: {len(doc)}")
page = doc[0]
print(f"Page size: {page.rect.width}x{page.rect.height}")
text = page.get_text("dict")
print("Sample text blocks:")
for i, b in enumerate(text["blocks"][:10]):
    if b.get("type") == 0:
        if b.get("lines") and b["lines"] and b["lines"][0].get("spans"):
            print(f"  Block {i}: {b['lines'][0]['spans'][0]['text'][:60]}")
