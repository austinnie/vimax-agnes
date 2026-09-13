import logging
import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)


@retry(
    retry=retry_if_exception_type((
        requests.exceptions.Timeout,
        requests.exceptions.ConnectionError,
        requests.exceptions.HTTPError,
    )),
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=2, min=5, max=60),
    reraise=True,
)
def download_image(url: str, save_path: str) -> None:
    """Download an image from URL and save to disk."""
    logger.info(f"Downloading image from {url} to {save_path}")
    resp = requests.get(url, timeout=60, stream=True)
    resp.raise_for_status()
    with open(save_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)
    logger.info(f"Image saved to {save_path}")


def image_path_to_b64(image_path: str) -> str:
    """Convert a local image file to base64 data URI."""
    import base64, mimetypes
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    mime = mimetypes.guess_type(image_path)[0] or "image/png"
    return f"data:{mime};base64,{b64}"