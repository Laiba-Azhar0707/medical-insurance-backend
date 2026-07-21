import os
import json
import time
from dotenv import load_dotenv
from groq import Groq
from text_cleanup import strip_thinking_blocks

load_dotenv()

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

MAX_RETRIES = 3


def deduplicate_items(items):
    seen = set()
    deduplicated = []
    for item in items:
        key = (
            (item.get("item_name") or "").strip().lower(),
            (item.get("dosage") or "").strip().lower(),
            item.get("price"),
        )
        if key not in seen:
            seen.add(key)
            deduplicated.append(item)
    return deduplicated


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
            "price (number or null if not shown). "
            "Do not list the same test more than once, even if it appears to repeat in the source text."
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
        "Do not include any reasoning, thinking, or explanation. "
        "Respond with ONLY a valid JSON array, no explanation, no markdown formatting, no extra text.\n\n"
        f"TEXT:\n{ocr_text}"
    )

    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="openai/gpt-oss-120b",
            )
            raw_output = strip_thinking_blocks(response.choices[0].message.content)

            if raw_output.startswith("```"):
                raw_output = raw_output.strip("`")
                if raw_output.startswith("json"):
                    raw_output = raw_output[4:].strip()

            items = json.loads(raw_output)

            if not isinstance(items, list):
                raise ValueError(f"Expected a JSON array, got: {type(items).__name__}")

            items = deduplicate_items(items)
            reliability = calculate_reliability(ocr_text, items, document_type)

            return {
                "success": True,
                "items": items,
                "error": None,
                **reliability,
            }

        except (json.JSONDecodeError, ValueError) as e:
            last_error = f"{str(e)}. Raw: {raw_output[:200] if 'raw_output' in dir() else 'N/A'}"
            if attempt < MAX_RETRIES:
                time.sleep(2 * attempt)
        except Exception as e:
            last_error = str(e)
            if attempt < MAX_RETRIES:
                time.sleep(2 * attempt)

    return {"success": False, "items": None, "error": f"Failed after {MAX_RETRIES} attempts: {last_error}",
            "illegible_ratio": 0.0, "blank_field_ratio": 0.0, "needs_review": False}