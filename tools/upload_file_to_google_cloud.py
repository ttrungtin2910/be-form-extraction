from google.cloud import storage

def upload_image_to_gcs(bucket_name, source_file_path, destination_blob_name):
    """Uploads an image to the Google Cloud Storage bucket."""
    # Initialize a client
    storage_client = storage.Client()
    
    # Get the bucket
    bucket = storage_client.bucket(bucket_name)
    
    # Create a blob object from the filepath
    blob = bucket.blob(destination_blob_name)
    
    # Upload the file to the blob
    blob.upload_from_filename(source_file_path)
    
    print(f"File {source_file_path} uploaded to {destination_blob_name}.")

# Example usage
upload_image_to_gcs(
    bucket_name="display-form-extract",
    source_file_path="/Users/trantrungtin/Desktop/Screenshot 2025-06-30 at 00.18.23.png",
    destination_blob_name="test.png"
)