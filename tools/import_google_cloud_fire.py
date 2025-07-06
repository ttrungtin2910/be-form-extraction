import os
import uuid
from google.cloud import firestore

# Gán đường dẫn tới file JSON key
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "crafty-isotope-456021-k2-a99ca9ffcde0.json"

# Khởi tạo client
db = firestore.Client(database="imageinformation")

documents = [
    {
        "Status": "Verify",
        "ImageName": "20250323_092227.jpg",
        "ImagePath": "https://storage.googleapis.com/display-form-extract/20250323_092227.jpg",
        "CreatedAt": "2025-06-30T15:00:00"
    },

    {
        "Status": "Completed",
        "ImageName": "20250323_092238.jpg",
        "ImagePath": "https://storage.googleapis.com/display-form-extract/20250323_092238.jpg",
        "CreatedAt": "2025-06-29T15:00:00"
    },

    {
        "Status": "Synced",
        "ImageName": "20250323_092249.jpg",
        "ImagePath": "https://storage.googleapis.com/display-form-extract/20250323_092249.jpg",
        "CreatedAt": "2025-06-28T15:00:00"
    },

    {
        "Status": "Verify",
        "ImageName": "20250323_092301.jpg",
        "ImagePath": "https://storage.googleapis.com/display-form-extract/20250323_092301.jpg",
        "CreatedAt": "2025-06-30T15:00:00"
    },

    {
        "Status": "Completed",
        "ImageName": "20250323_092310.jpg",
        "ImagePath": "https://storage.googleapis.com/display-form-extract/20250323_092310.jpg",
        "CreatedAt": "2025-06-29T15:00:00"
    },

    {
        "Status": "Synced",
        "ImageName": "20250323_092320.jpg",
        "ImagePath": "https://storage.googleapis.com/display-form-extract/20250323_092320.jpg",
        "CreatedAt": "2025-06-28T15:00:00"
    },

]

for doc in documents:
    doc_ref = db.collection("imagedetail").document(doc['ImageName'])
    doc_ref.set(doc)
print("Test")