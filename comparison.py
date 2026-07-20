import os
import json
import time
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

MAX_RETRIES = 3


def compare_prescribed_vs_billed(prescribed_items, billed_items):
    """
    Compares prescribed items (from the prescription) against billed items
    (from the medicine bill or lab bill) using fuzzy, semantic matching.

    prescribed_items / billed_items: lists of dicts like
        {"item_name": "Paracetamol", "dosage": "500mg", "price": 6.49}

    Returns a dict: {"success": bool, "results": list or None, "error": str or None}
    Each result: {"billed_item": str, "price": float or None, "matched_prescribed_item": str or None,
                   "is_prescribed": bool, "reasoning": str}
    """
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
        "not exact string matching.\n\n"
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
        "Respond with ONLY the JSON array, no explanation, no markdown formatting."
    )

    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="openai/gpt-oss-120b",
            )
            raw_output = response.choices[0].message.content.strip()

            if raw_output.startswith("```"):
                raw_output = raw_output.strip("`")
                if raw_output.startswith("json"):
                    raw_output = raw_output[4:].strip()

            results = json.loads(raw_output)

            # Sanity check: the response must actually cover every billed item.
            # This is exactly the failure mode observed earlier today, where
            # a call "succeeded" but silently returned incomplete/empty results.
            if not isinstance(results, list) or len(results) != len(billed_items):
                raise ValueError(
                    f"Expected {len(billed_items)} results, got "
                    f"{len(results) if isinstance(results, list) else 'non-list response'}"
                )

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