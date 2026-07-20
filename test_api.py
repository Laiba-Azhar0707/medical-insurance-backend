import requests

# Step 1: Login
login_response = requests.post(
    "http://127.0.0.1:8000/login",
    json={"email": "user@test.com", "password": "password123"}
)
print("LOGIN STATUS:", login_response.status_code)
token = login_response.json().get("access_token")

if not token:
    print("No token received, stopping.")
    exit()

headers = {"Authorization": f"Bearer {token}"}

# Step 2: Dashboard check
dashboard_response = requests.get("http://127.0.0.1:8000/dashboard", headers=headers)
print("DASHBOARD STATUS:", dashboard_response.status_code)

# Step 3: Submit a claim (now sends one page per document type, but supports multiple)
files = [
    ("prescription", open("sample_dosage_test_prescription.jpg", "rb")),
    ("medicine_bill", open("sample_medicine_bill.jpg", "rb")),
    ("lab_bill", open("sample_lab_bill.jpg", "rb")),
    ("consultation_receipt", open("sample_consultation_receipt.jpg", "rb")),
]
data = {"claim_type": "reimbursement"}

claim_response = requests.post(
    "http://127.0.0.1:8000/claims",
    headers=headers,
    data=data,
    files=files,
)
print("CLAIM STATUS:", claim_response.status_code)
print("CLAIM BODY:", claim_response.json())