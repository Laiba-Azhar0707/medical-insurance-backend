import os
import base64
import time
from dotenv import load_dotenv
from groq import Groq
from text_cleanup import strip_thinking_blocks

load_dotenv()

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

MAX_RETRIES = 3

SUSPICIOUS_NAME_PATTERNS = [
    "unnamed", "unspecified", "unknown", "universal", "universum",
    "international", "institute", "centre", "center", "academy",
    "school", "corporation", "company", "organization", "n/a",
]


def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def flag_suspicious_identity_fields(ocr_text):
    for line in ocr_text.split("\n"):
        line_lower = line.lower()
        if "name:" in line_lower or "patient" in line_lower:
            for pattern in SUSPICIOUS_NAME_PATTERNS:
                if pattern in line_lower:
                    return True
    return False


def extract_text_from_image(image_path, document_type="general"):
    if not os.path.exists(image_path):
        return {"success": False, "text": None, "error": f"File not found: {image_path}", "identity_flag": False}

    try:
        base64_image = encode_image(image_path)
    except Exception as e:
        return {"success": False, "text": None, "error": f"Could not read image: {str(e)}", "identity_flag": False}

    if document_type == "tabular":
        prompt = (
            "Transcribe this document exactly as written, preserving its table structure. "
            "For every row in any table, output ALL columns for that row on one line, "
            "separated by ' | ', in the same left-to-right order as the image. "
            "Do not drop any column, including reference ranges, units, or test methods, "
            "even if the value looks blank, incomplete, or hard to read, in that case write [ILLEGIBLE]. "
            "Critical rule: only output institution names, addresses, and locations that are "
            "literally visible in the image. Never substitute a different but similar-sounding "
            "name, city, or address. If unsure, write [ILLEGIBLE] rather than guessing. "
            "Do not summarize, explain, or describe the image, only output the transcribed content. "
            "Do not include any reasoning, thinking, or explanation, respond with ONLY the transcription."
        )
    else:
        prompt = (
            "Transcribe all the text in this image exactly as written, word for word. "
            "Do not describe the image, do not summarize, do not explain anything. "
            "Output only the raw transcribed text, nothing else. "
            "Critical rule: only output words that are actually visible in the image. "
            "Never add a sentence, phrase, or word that continues or completes an idea unless it is literally written there. "
            "If a word is illegible, write [ILLEGIBLE] instead of guessing or inventing plausible text. "
            "Do not include any reasoning, thinking, or explanation, respond with ONLY the transcription."
        )

    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                            },
                        ],
                    }
                ],
                model="qwen/qwen3.6-27b",
            )
            extracted_text = strip_thinking_blocks(response.choices[0].message.content)
            identity_flag = flag_suspicious_identity_fields(extracted_text)
            return {"success": True, "text": extracted_text, "error": None, "identity_flag": identity_flag}

        except Exception as e:
            last_error = str(e)
            if attempt < MAX_RETRIES:
                time.sleep(2 * attempt)

    return {"success": False, "text": None, "error": f"Failed after {MAX_RETRIES} attempts: {last_error}", "identity_flag": False}