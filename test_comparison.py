from comparison import compare_prescribed_vs_billed
from deduction import calculate_deductions

prescribed_items = [
    {"item_name": "Paracetamol", "dosage": "500mg"},
    {"item_name": "Amoxicillin", "dosage": "250mg"},
    {"item_name": "Cough Syrup", "dosage": "10ml"},
]

billed_items = [
    {"item_name": "Panadol 500mg", "price": 6.49},
    {"item_name": "Amoxicillin 250mg", "price": 9.99},
    {"item_name": "Vitamin C 1000mg", "price": 3.79},
    {"item_name": "Cough Syrup 4oz", "price": 5.49},
]

comparison_result = compare_prescribed_vs_billed(prescribed_items, billed_items)

if comparison_result["success"]:
    print("COMPARISON RESULTS:")
    for r in comparison_result["results"]:
        print(r)
    print()

    for claim_type in ["pre_paid", "reimbursement"]:
        deduction_result = calculate_deductions(comparison_result["results"], claim_type)
        print(f"--- {claim_type.upper()} ---")
        print(deduction_result)
        print()
else:
    print("COMPARISON FAILED:", comparison_result["error"])