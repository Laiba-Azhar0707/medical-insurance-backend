import os
import json
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))


def calculate_reliability(ocr_text, items, document_type):
    lines = [line for line in ocr_text.split("\n") if line.strip()]
    raw_fields = []
    for line in lines:
        raw_fields.extend(line.split("|"))
    fields = [f for f in raw_fields if f.strip()]
    illegible_ratio = (
        sum(1 for f in fields if "[ILLEGIBLE]" in f) / len(fields) if fields else 0.0
    )

    critical_field = {
        "prescription": "dosage",
        "medicine_bill": "price",
        "lab_bill": "dosage",
        "consultation_receipt": "price",
    }.get(document_type, "price")

    if items:
        blank_count = sum(
            1 for item in items
            if item.get(critical_field) in (None, "", "null")
            or item.get("item_name") in (None, "", "null")
        )
        blank_field_ratio = blank_count / len(items)
    else:
        blank_field_ratio = 0.0

    needs_review = illegible_ratio > 0.15 or blank_field_ratio > 0.3

    return {
        "illegible_ratio": round(illegible_ratio, 3),
        "blank_field_ratio": round(blank_field_ratio, 3),
        "needs_review": needs_review,
    }


def extract_structured_data(ocr_text, document_type):
    schema_instructions = {
        "prescription": (
            "Extract every prescribed medicine or test as a JSON array. "
            "Each item must have: item_name (string), item_type ('medicine' or 'test'), "
            "quantity (number or null), dosage (string or null), price (always null for prescriptions)."
        ),
        "medicine_bill": (
            "Extract every purchased item as a JSON array. "
            "Each item must have: item_name (string), item_type (always 'medicine'), "
            "quantity (number or null), dosage (string or null, usually null for bills), "
            "price (number, the price for that line item)."
        ),
        "lab_bill": (
            "Extract every lab test result as a JSON array. "
            "Each item must have: item_name (the test name, string), item_type (always 'test'), "
            "quantity (always null), dosage (put the result value and reference range here as a string, e.g. '13.8 (13.0-17.0 g/dL)'), "
            "price (number or null if not shown)."
        ),
        "consultation_receipt": (
            "Extract the consultation fee as a JSON array with one item. "
            "It must have: item_name (e.g. 'Consultation Fee' or doctor's name if shown), "
            "item_type (always 'consultation'), quantity (always null), dosage (always null), "
            "price (number, the fee charged)."
        ),
    }

    instruction = schema_instructions.get(document_type)
    if not instruction:
        return {"success": False, "items": None, "error": f"Unknown document_type: {document_type}",
                "illegible_ratio": 0.0, "blank_field_ratio": 0.0, "needs_review": False}

    prompt = (
        f"{instruction}\n\n"
        "Only use information literally present in the text below. Never invent, guess, or fill in "
        "a value that isn't actually there, use null instead. "
        "Respond with ONLY a valid JSON array, no explanation, no markdown formatting, no extra text.\n\n"
        f"TEXT:\n{ocr_text}"
    )

    try:
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="meta-llama/llama-4-scout-17b-16e-instruct",
        )
        raw_output = response.choices[0].message.content.strip()

        if raw_output.startswith("```"):
            raw_output = raw_output.strip("`")
            if raw_output.startswith("json"):
                raw_output = raw_output[4:].strip()

        items = json.loads(raw_output)

        reliability = calculate_reliability(ocr_text, items, document_type)

        return {
            "success": True,
            "items": items,
            "error": None,
            **reliability,
        }

    except json.JSONDecodeError as e:
        return {"success": False, "items": None,
                "error": f"Could not parse JSON response: {str(e)}. Raw output: {raw_output[:200]}",
                "illegible_ratio": 0.0, "blank_field_ratio": 0.0, "needs_review": False}
    except Exception as e:
        return {"success": False, "items": None, "error": str(e),
                "illegible_ratio": 0.0, "blank_field_ratio": 0.0, "needs_review": False}