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

# Step 2: Dashboard check (already confirmed working, quick sanity check)
dashboard_response = requests.get("http://127.0.0.1:8000/dashboard", headers=headers)
print("DASHBOARD STATUS:", dashboard_response.status_code)

# Step 3: Submit a claim with files
files = {
    "prescription": open("test_files/prescription.txt", "rb"),
    "medicine_bill": open("test_files/medicine_bill.txt", "rb"),
    "lab_bill": open("test_files/lab_bill.txt", "rb"),
    "consultation_receipt": open("test_files/consultation_receipt.txt", "rb"),
}
data = {"claim_type": "reimbursement"}

claim_response = requests.post(
    "http://127.0.0.1:8000/claims",
    headers=headers,
    data=data,
    files=files,
)
print("CLAIM STATUS:", claim_response.status_code)
print("CLAIM BODY:", claim_response.json())