from ocr import extract_text_from_image

test_files = [
    ("sample_prescription.jpg", "general"),
    ("sample_printed.jpeg", "general"),
    ("sample_medicine_bill.jpg", "general"),
    ("sample_lab_bill.jpg", "tabular"),
]

for filepath, doc_type in test_files:
    print(f"\n{'='*50}")
    print(f"Testing: {filepath} (mode: {doc_type})")
    print('='*50)
    result = extract_text_from_image(filepath, document_type=doc_type)
    if result["success"]:
        print(result["text"])
    else:
        print(f"FAILED: {result['error']}")