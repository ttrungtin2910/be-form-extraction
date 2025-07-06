from google.cloud import storage

def upload_image_to_gcs(bucket_name: str, source_file_path: str, destination_blob_name: str):
    """
    Uploads an image to the Google Cloud Storage bucket.
    """
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_filename(source_file_path)
    print(f"File {source_file_path} uploaded to {destination_blob_name}.")