"""
Basic automated tests codifying today's manually-verified findings.
Run with: python test_suite.py
"""

from ocr import extract_text_from_image, flag_suspicious_identity_fields
from extraction import extract_structured_data
from image_quality import check_image_quality, validate_file_type

passed = 0
failed = 0


def check(description, condition):
    global passed, failed
    if condition:
        print(f"PASS: {description}")
        passed += 1
    else:
        print(f"FAIL: {description}")
        failed += 1


print("Running test suite...\n")

ocr_result = extract_text_from_image("sample_prescription.jpg", document_type="general")
if ocr_result["success"]:
    structured = extract_structured_data(ocr_result["text"], "prescription")
    check("Prescription with no medicines returns empty items list",
          structured["success"] and len(structured["items"]) == 0)

ocr_result = extract_text_from_image("sample_medicine_bill.jpg", document_type="general")
if ocr_result["success"]:
    structured = extract_structured_data(ocr_result["text"], "medicine_bill")
    check("Medicine bill returns 6 items",
          structured["success"] and len(structured["items"]) == 6)

ocr_result = extract_text_from_image("sample_consultation_receipt.jpg", document_type="general")
if ocr_result["success"]:
    structured = extract_structured_data(ocr_result["text"], "consultation_receipt")
    check("Consultation receipt returns exactly 1 item",
          structured["success"] and len(structured["items"]) == 1)

check("Identity flag detects 'Universal Hospital Research Inst.'",
      flag_suspicious_identity_fields("Name: | Universal Hospital Research Inst. |"))

check("Identity flag does NOT flag a normal-looking name",
      not flag_suspicious_identity_fields("Name: | Mohammed Faisal Karim |"))

check("validate_file_type rejects a .txt file",
      not validate_file_type("test.txt")["valid"])

check("validate_file_type accepts a .jpg file",
      validate_file_type("test.jpg")["valid"])

check("check_image_quality handles missing file without crashing",
      not check_image_quality("does_not_exist.jpg")["acceptable"])

print(f"\n{'='*40}")
print(f"RESULTS: {passed} passed, {failed} failed")
print('='*40)