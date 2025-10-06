import os
from urllib.parse import urlparse
import aiohttp
import asyncio
import requests
def extract_filename_from_url(url: str) -> str:
    """
    Extract the filename from a full URL.
    """
    path = urlparse(url).path
    return os.path.basename(path)  # e.g. 20250630_abcd.png



async def download_image_from_url(url: str, local_path: str):
    """
    Download an image from a public URL to a local file.
    """
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200:
                raise Exception(f"Failed to download image. Status code: {response.status}")
            with open(local_path, 'wb') as f:
                f.write(await response.read())


def download_image_from_url_sync(url: str, local_path: str):
    """
    Synchronous version of image download for use in Celery tasks.
    Avoids asyncio.run() conflicts in Celery workers.
    """
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    
    with open(local_path, 'wb') as f:
        f.write(response.content)