import os
import base64
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))


def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')


base64_image = encode_image("sample_printed.jpeg")

response = client.chat.completions.create(
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "Transcribe all the text in this image exactly as written. Do not summarize, explain, or add anything, just output the raw text you see."
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{base64_image}"
                    }
                }
            ]
        }
    ],
    model="meta-llama/llama-4-scout-17b-16e-instruct",
)

print("EXTRACTED TEXT (Groq / Llama 4 Scout):")
print(response.choices[0].message.content)