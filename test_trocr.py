from transformers import RobertaTokenizer, ViTImageProcessor, VisionEncoderDecoderModel
from PIL import Image

print("Loading TrOCR model components directly...")

tokenizer = RobertaTokenizer.from_pretrained("microsoft/trocr-base-handwritten")
feature_extractor = ViTImageProcessor.from_pretrained("microsoft/trocr-base-handwritten")
model = VisionEncoderDecoderModel.from_pretrained("microsoft/trocr-base-handwritten")

image = Image.open("sample_prescription.jpg").convert("RGB")

pixel_values = feature_extractor(images=image, return_tensors="pt").pixel_values

generated_ids = model.generate(pixel_values)
generated_text = tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]

print("EXTRACTED TEXT (TrOCR):")
print(generated_text)