from ocr import extract_text_from_image
from extraction import extract_structured_data

ocr_result = extract_text_from_image("sample_lab_bill.jpg", document_type="tabular")

if ocr_result["success"]:
    print("RAW OCR TEXT:")
    print(ocr_result["text"])
    print("\n" + "="*50)

    structured = extract_structured_data(ocr_result["text"], "lab_bill")

    if structured["success"]:
        print("\nITEMS:")
        for item in structured["items"]:
            print(item)

        print("\nRELIABILITY:")
        print("illegible_ratio:", structured["illegible_ratio"])
        print("blank_field_ratio:", structured["blank_field_ratio"])
        print("needs_review:", structured["needs_review"])
    else:
        print("STRUCTURED EXTRACTION FAILED:", structured["error"])
else:
    print("OCR FAILED:", ocr_result["error"])