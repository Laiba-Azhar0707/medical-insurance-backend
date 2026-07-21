"""
Formal end-to-end tests covering both real verified scenarios:
1. A legitimately prescribed medicine gets correctly matched and excluded from deductions.
2. A medicine with a dosage mismatch gets correctly flagged, even though the name matches.

Requires the backend server to be running (uvicorn main:app --reload)
and a logged-in test user (user@test.com / password123) to already exist.
"""

import requests

BASE_URL = "http://127.0.0.1:8000"

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


def login():
    response = requests.post(
        f"{BASE_URL}/login",
        json={"email": "user@test.com", "password": "password123"}
    )
    return response.json().get("access_token")


def submit_claim(token, prescription_file, claim_type="reimbursement"):
    headers = {"Authorization": f"Bearer {token}"}
    files = [
        ("prescription", open(prescription_file, "rb")),
        ("medicine_bill", open("sample_medicine_bill.jpg", "rb")),
        ("lab_bill", open("sample_lab_bill.jpg", "rb")),
        ("consultation_receipt", open("sample_consultation_receipt.jpg", "rb")),
    ]
    data = {"claim_type": claim_type}
    response = requests.post(f"{BASE_URL}/claims", headers=headers, data=data, files=files)
    return response.json()


print("Running end-to-end tests...\n")

token = login()
check("Login succeeds and returns a token", token is not None)

if token:
    # Scenario 1: matching prescription (Ibuprofen 200mg genuinely prescribed)
    result1 = submit_claim(token, "sample_real_prescription.jpg")
    deductions1 = result1.get("deduction_summary", {}).get("deductions", [])
    ibuprofen_flagged = any(
        "Ibuprofen" in d.get("item_name", "") for d in deductions1
    )
    check("Legitimately prescribed Ibuprofen 200mg is NOT flagged as a deduction",
          not ibuprofen_flagged)
    check("Claim with a real, matching prescription reaches a final status",
          result1.get("status") in ("Processed", "Needs Manual Review"))

    # Scenario 2: dosage mismatch (Ibuprofen 400mg prescribed, 200mg billed)
    result2 = submit_claim(token, "sample_dosage_test_prescription.jpg")
    deductions2 = result2.get("deduction_summary", {}).get("deductions", [])
    dosage_mismatch_flagged = any(
        "Ibuprofen" in d.get("item_name", "") and "osage" in d.get("reason", "")
        for d in deductions2
    )
    check("Dosage mismatch (200mg billed vs 400mg prescribed) IS correctly flagged",
          dosage_mismatch_flagged)

    # Scenario 3: pre_paid vs reimbursement branching
    result_prepaid = submit_claim(token, "sample_dosage_test_prescription.jpg", claim_type="pre_paid")
    action_type = result_prepaid.get("deduction_summary", {}).get("action_type")
    check("pre_paid claim type produces 'return_notice' action",
          action_type == "return_notice")

    result_reimbursement = submit_claim(token, "sample_dosage_test_prescription.jpg", claim_type="reimbursement")
    action_type2 = result_reimbursement.get("deduction_summary", {}).get("action_type")
    check("reimbursement claim type produces 'auto_deduct' action",
          action_type2 == "auto_deduct")

print(f"\n{'='*50}")
print(f"RESULTS: {passed} passed, {failed} failed")
print('='*50)