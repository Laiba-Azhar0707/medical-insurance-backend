import os
import base64
import time
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

MAX_RETRIES = 3


def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def extract_text_from_image(image_path):
    """
    Sends an image to Groq's vision model and returns extracted text.
    Returns a dict: {"success": bool, "text": str or None, "error": str or None}
    """
    if not os.path.exists(image_path):
        return {"success": False, "text": None, "error": f"File not found: {image_path}"}

    try:
        base64_image = encode_image(image_path)
    except Exception as e:
        return {"success": False, "text": None, "error": f"Could not read image: {str(e)}"}

    prompt = (
    "Transcribe all the text in this image exactly as written, word for word. "
    "Do not describe the image, do not summarize, do not explain anything. "
    "Output only the raw transcribed text, nothing else. "
    "Critical rule: only output words that are actually visible in the image. "
    "Never add a sentence, phrase, or word that continues or completes an idea unless it is literally written there. "
    "If a word is illegible, write [ILLEGIBLE] instead of guessing or inventing plausible text."
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
                model="meta-llama/llama-4-scout-17b-16e-instruct",
            )
            extracted_text = response.choices[0].message.content
            return {"success": True, "text": extracted_text, "error": None}

        except Exception as e:
            last_error = str(e)
            if attempt < MAX_RETRIES:
                time.sleep(2 * attempt)  # brief backoff before retrying

    return {"success": False, "text": None, "error": f"Failed after {MAX_RETRIES} attempts: {last_error}"}