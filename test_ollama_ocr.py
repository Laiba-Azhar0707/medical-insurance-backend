import ollama

response = ollama.chat(
    model='deepseek-ocr',
    messages=[
        {
            'role': 'user',
            'content': 'Transcribe all the text in this image exactly as written. Do not summarize, explain, or add anything, just output the raw text you see.',
            'images': ['sample_prescription.jpg']
        }
    ]
)

print("EXTRACTED TEXT (Ollama / llama3.2-vision):")
print(response['message']['content'])