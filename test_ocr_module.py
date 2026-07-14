from ocr import extract_text_from_image

test_files = [
    "sample_prescription.jpg",
    "sample_printed.jpeg",
]

for filepath in test_files:
    print(f"\n{'='*50}")
    print(f"Testing: {filepath}")
    print('='*50)
    result = extract_text_from_image(filepath)
    if result["success"]:
        print(result["text"])
    else:
        print(f"FAILED: {result['error']}")