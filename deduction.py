def calculate_deductions(comparison_results, claim_type):
    """
    Takes comparison results (from compare_prescribed_vs_billed) and the claim type,
    and calculates deduction amounts based on unprescribed items.

    claim_type: "pre_paid" or "reimbursement"

    Returns a dict:
    {
        "total_unprescribed_amount": float,
        "deductions": list of dicts, one per unprescribed item,
        "action_type": "return_notice" or "auto_deduct"
    }

    Each deduction dict: {"item_name": str, "amount": float, "reason": str, "has_price": bool}
    """
    action_type = "return_notice" if claim_type == "pre_paid" else "auto_deduct"

    deductions = []
    total = 0.0

    for result in comparison_results:
        if not result.get("is_prescribed", True):
            amount = result.get("price")
            deductions.append({
                "item_name": result.get("billed_item"),
                "amount": amount if amount is not None else 0.0,
                "reason": result.get("reasoning", "Item not found in prescription"),
                "has_price": amount is not None,
            })
            if amount is not None:
                total += amount

    return {
        "total_unprescribed_amount": round(total, 2),
        "deductions": deductions,
        "action_type": action_type,
    }