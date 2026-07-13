import pytesseract
import cv2
import numpy as np

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


def preprocess(image):
    # Upscale
    scale_percent = 150
    width = int(image.shape[1] * scale_percent / 100)
    height = int(image.shape[0] * scale_percent / 100)
    image = cv2.resize(image, (width, height), interpolation=cv2.INTER_CUBIC)

    # Grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Contrast enhancement (CLAHE) - boosts faint strokes without blowing out bright areas
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    contrasted = clahe.apply(gray)

    # Denoise
    denoised = cv2.fastNlMeansDenoising(contrasted, h=30)

    # Deskew
    coords = np.column_stack(np.where(denoised < 255))
    if len(coords) > 0:
        angle = cv2.minAreaRect(coords)[-1]
        angle = -(90 + angle) if angle < -45 else -angle
        (h, w) = denoised.shape[:2]
        M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
        denoised = cv2.warpAffine(denoised, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)

    # Adaptive threshold
    thresh = cv2.adaptiveThreshold(
        denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 15
    )

    # Morphological closing - bridges small gaps in broken pen strokes
    kernel = np.ones((2, 2), np.uint8)
    closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

    return closed


def extract_with_confidence(processed_image, psm):
    config = f"--oem 3 --psm {psm}"
    data = pytesseract.image_to_data(processed_image, config=config, output_type=pytesseract.Output.DICT)

    words = []
    confidences = []
    for i, word in enumerate(data["text"]):
        conf = int(data["conf"][i])
        if word.strip() and conf > 0:
            words.append(word)
            confidences.append(conf)

    text = " ".join(words)
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0
    return text, avg_confidence


def run_ocr(filepath):
    image = cv2.imread(filepath)
    if image is None:
        raise FileNotFoundError(f"Could not read image: {filepath}")

    processed = preprocess(image)

    # Try a couple of PSM modes and keep whichever scores higher confidence
    best_text, best_conf = "", -1
    for psm in [6, 11]:
        text, conf = extract_with_confidence(processed, psm)
        print(f"--- PSM {psm} | avg confidence: {conf:.1f} ---")
        if conf > best_conf:
            best_text, best_conf = text, conf

    print(f"\nBEST RESULT (confidence {best_conf:.1f}):")
    print(best_text)
    return best_text, best_conf


run_ocr("sample_printed.jpeg")