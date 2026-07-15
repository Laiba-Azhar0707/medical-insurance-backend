from image_quality import check_image_quality

test_images = [
    "sample_prescription.jpg",
    "sample_medicine_bill.jpg",
    "sample_lab_bill.jpg",
    "sample_consultation_receipt.jpg",
]

for img in test_images:
    result = check_image_quality(img)
    print(f"{img}: {result}")