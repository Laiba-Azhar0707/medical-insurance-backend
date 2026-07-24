import fitz  # PyMuPDF
import os


def is_pdf(file_path):
    return file_path.lower().endswith(".pdf")


def convert_pdf_to_images(pdf_path, output_dir, dpi=200):
    """Converts each page of a PDF into a separate PNG image.
    Returns a list of file paths, one per page, in order."""
    image_paths = []
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]

    doc = fitz.open(pdf_path)
    try:
        zoom = dpi / 72
        matrix = fitz.Matrix(zoom, zoom)

        for page_num in range(len(doc)):
            page = doc[page_num]
            pix = page.get_pixmap(matrix=matrix)
            image_path = os.path.join(output_dir, f"{base_name}_pdfpage{page_num + 1}.png")
            pix.save(image_path)
            image_paths.append(image_path)
    finally:
        doc.close()

    return image_paths