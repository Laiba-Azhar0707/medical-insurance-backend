from ocr import extract_text_from_image
from extraction import extract_structured_data

ocr_result = extract_text_from_image("sample_consultation_receipt.jpg", document_type="general")

if ocr_result["success"]:
    print("RAW OCR TEXT:")
    print(ocr_result["text"])
    print("\n" + "="*50 + "\n")

    structured = extract_structured_data(ocr_result["text"], "consultation_receipt")
    if structured["success"]:
        print("STRUCTURED ITEMS:")
        for item in structured["items"]:
            print(item)
    else:
        print("STRUCTURED EXTRACTION FAILED:", structured["error"])
else:
    print("OCR FAILED:", ocr_result["error"])