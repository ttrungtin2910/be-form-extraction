from google.cloud import storage


def upload_image_to_gcs(
    bucket_name: str, source_file_path: str, destination_blob_name: str
):
    """
    Uploads an image to the Google Cloud Storage bucket.
    """
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_filename(source_file_path)
    print(f"File {source_file_path} uploaded to {destination_blob_name}.")


def delete_blobs_with_prefix(bucket_name: str, prefix: str):
    """Delete all blobs beginning with prefix (simulate folder delete)."""
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blobs = bucket.list_blobs(prefix=prefix)
    for blob in blobs:
        blob.delete()
    print(f"Deleted blobs with prefix {prefix} in bucket {bucket_name}.")


def rename_folder(bucket_name: str, old_prefix: str, new_prefix: str):
    """Rename a 'folder' by copying blobs then deleting originals."""
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blobs = bucket.list_blobs(prefix=old_prefix)
    for blob in blobs:
        new_name = blob.name.replace(old_prefix, new_prefix, 1)
        bucket.copy_blob(blob, bucket, new_name)
        blob.delete()
    print(f"Renamed folder {old_prefix} to {new_prefix} in bucket {bucket_name}.")
