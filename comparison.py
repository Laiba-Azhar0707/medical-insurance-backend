import os
import json
import re
import time
from dotenv import load_dotenv
from groq import Groq
from text_cleanup import strip_thinking_blocks

load_dotenv()

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

MAX_RETRIES = 3


def extract_dosage_number(text):
    if not text:
        return None
    match = re.search(r'(\d+(?:\.\d+)?)\s*(mg|ml|mcg|g)\b', text, re.IGNORECASE)
    if match:
        return float(match.group(1)), match.group(2).lower()
    return None


def verify_dosage_consistency(results, prescribed_items):
    prescribed_lookup = {
        (item.get("item_name") or "").strip().lower(): item.get("item_name")
        for item in prescribed_items
    }

    for result in results:
        if not result.get("is_prescribed"):
            continue

        matched_name = (result.get("matched_prescribed_item") or "").strip().lower()
        if matched_name not in prescribed_lookup:
            continue

        prescribed_name_text = prescribed_lookup[matched_name]
        billed_dosage_text = result.get("billed_item")

        prescribed_dosage = extract_dosage_number(prescribed_name_text)
        billed_dosage = extract_dosage_number(billed_dosage_text)

        if prescribed_dosage and billed_dosage:
            p_value, p_unit = prescribed_dosage
            b_value, b_unit = billed_dosage
            if p_unit == b_unit and p_value != b_value:
                result["is_prescribed"] = False
                result["reasoning"] = (
                    f"Dosage mismatch detected on verification: prescribed {p_value}{p_unit}, "
                    f"billed {b_value}{b_unit}. Overridden from initial AI match."
                )

    return results


def compare_prescribed_vs_billed(prescribed_items, billed_items):
    if not billed_items:
        return {"success": True, "results": [], "error": None}

    if not prescribed_items:
        results = [
            {
                "billed_item": item.get("item_name"),
                "price": item.get("price"),
                "matched_prescribed_item": None,
                "is_prescribed": False,
                "reasoning": "No prescription was provided, so this item cannot be verified as prescribed.",
            }
            for item in billed_items
        ]
        return {"success": True, "results": results, "error": None}

    prompt = (
        "You are comparing a list of PRESCRIBED items against a list of BILLED items "
        "for a medical insurance claim. Medicine names may vary (brand name vs generic name, "
        "e.g. 'Panadol' and 'Paracetamol' are the same medicine), so match on likely intent, "
        "not exact string matching. Pay close attention to dosage strength, the same medicine "
        "at a different dosage (e.g. 200mg vs 400mg) is NOT a match.\n\n"
        f"PRESCRIBED ITEMS:\n{json.dumps(prescribed_items, indent=2)}\n\n"
        f"BILLED ITEMS:\n{json.dumps(billed_items, indent=2)}\n\n"
        "For EVERY billed item, determine if it reasonably matches a prescribed item. "
        "Respond with a JSON array, one object per billed item, each with exactly these fields: "
        "billed_item (string, the item name), "
        "price (number or null, copy the price value exactly as given in the billed item, do not invent it), "
        "matched_prescribed_item (string or null, the prescribed item it matches, if any), "
        "is_prescribed (boolean), "
        "reasoning (a short string explaining the match or mismatch). "
        "Only use information given above. Do not invent medicines that aren't in either list. "
        "You MUST return exactly one result object for every billed item, in the same order. "
        "Do not include any reasoning, thinking, or explanation outside the JSON. "
        "Respond with ONLY the JSON array, no explanation, no markdown formatting."
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

            results = json.loads(raw_output)

            if not isinstance(results, list) or len(results) != len(billed_items):
                raise ValueError(
                    f"Expected {len(billed_items)} results, got "
                    f"{len(results) if isinstance(results, list) else 'non-list response'}"
                )

            results = verify_dosage_consistency(results, prescribed_items)
            return {"success": True, "results": results, "error": None}

        except (json.JSONDecodeError, ValueError) as e:
            last_error = str(e)
            if attempt < MAX_RETRIES:
                time.sleep(2 * attempt)
        except Exception as e:
            last_error = str(e)
            if attempt < MAX_RETRIES:
                time.sleep(2 * attempt)

    return {"success": False, "results": None, "error": f"Failed after {MAX_RETRIES} attempts: {last_error}"}