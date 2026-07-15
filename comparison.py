import os
import json
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))


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
        "Respond with ONLY the JSON array, no explanation, no markdown formatting."
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

        results = json.loads(raw_output)
        return {"success": True, "results": results, "error": None}

    except json.JSONDecodeError as e:
        return {"success": False, "results": None, "error": f"Could not parse JSON: {str(e)}. Raw: {raw_output[:200]}"}
    except Exception as e:
        return {"success": False, "results": None, "error": str(e)}