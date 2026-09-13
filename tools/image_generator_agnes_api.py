"""Agnes AI Image Generator — implements ImageGenerator protocol.

Supports two modes:
  - Text-to-image (t2i): prompt only, no reference images
  - Image-to-image (i2i): 1 reference image via extra_body
"""

import base64
import logging
import mimetypes
import os
import time
from typing import List, Optional
import requests
from interfaces.image_output import ImageOutput

logger = logging.getLogger(__name__)

BASE_URL = "https://apihub.agnes-ai.com/v1"


class ImageGeneratorAgnesAPI:
    """Generate images using Agnes AI (agnes-image-2.1-flash for t2i, agnes-image-2.0-flash for i2i)."""

    def __init__(self, api_key: str, model: str = "agnes-image-2.1-flash"):
        self.api_key = api_key
        self.model = model
        self.i2i_model = "agnes-image-2.0-flash"  # Image-to-image uses 2.0-flash
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    def _post_with_retry(
        self,
        url: str,
        json_payload: dict,
        max_retries: int = 5,
        base_delay: float = 10.0,
        timeout: int = 120,
    ):
        """POST with automatic retry on 429 / 5xx / timeout / network error."""
        last_exc = None
        for attempt in range(max_retries):
            try:
                resp = requests.post(
                    url,
                    headers=self.headers,
                    json=json_payload,
                    timeout=timeout,
                )
                if resp.status_code == 429:
                    delay = min(base_delay * (2 ** attempt), 120)
                    logger.warning(
                        f"[Agnes Image] 429 rate limit, retry {attempt+1}/{max_retries} in {delay:.0f}s"
                    )
                    print(f"  ⚠️  图片限流 429，{delay:.0f}s 后重试 ({attempt+1}/{max_retries})...", flush=True)
                    time.sleep(delay)
                    continue
                if resp.status_code >= 500:
                    delay = min(base_delay * (2 ** attempt), 120)
                    logger.warning(
                        f"[Agnes Image] {resp.status_code} server error, retry {attempt+1}/{max_retries} in {delay:.0f}s"
                    )
                    print(f"  ⚠️  图片服务端 {resp.status_code}，{delay:.0f}s 后重试 ({attempt+1}/{max_retries})...", flush=True)
                    time.sleep(delay)
                    continue

                if 400 <= resp.status_code < 500 and resp.status_code != 429:
                    logger.error(f"[Agnes Image] HTTP {resp.status_code}: {resp.text[:500]}")                    
                resp.raise_for_status()
                return resp
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                last_exc = e
                delay = min(base_delay * (2 ** attempt), 120)
                logger.warning(
                    f"[Agnes Image] Network error ({type(e).__name__}), retry {attempt+1}/{max_retries} in {delay:.0f}s"
                )
                print(f"  ⚠️  图片网络错误，{delay:.0f}s 后重试 ({attempt+1}/{max_retries})...", flush=True)
                time.sleep(delay)
                continue
        raise RuntimeError(f"[Agnes Image] max retries ({max_retries}) exceeded: {last_exc}")
        
    def _path_to_b64(self, path: str) -> str:
        """Convert a local image file path to base64 data URI."""
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
        mime = mimetypes.guess_type(path)[0] or "image/png"
        return f"data:{mime};base64,{b64}"

    def _resolve_image_ref(self, ref: str) -> str:
        """Resolve an image reference: return URL as-is, convert local path to b64."""
        if ref.startswith(("http://", "https://", "data:")):
            return ref
        if os.path.exists(ref):
            return self._path_to_b64(ref)
        # Assume it's a URL
        return ref

    async def generate_single_image(
        self,
        prompt: str,
        reference_image_paths: List[str] = [],
        size: Optional[str] = None,
        **kwargs,
    ) -> ImageOutput:
        """
        Generate an image.

        - No reference images → text-to-image (model: agnes-image-2.1-flash)
        - With reference images → image-to-image (model: agnes-image-2.0-flash, extra_body)
        """
        use_i2i = len(reference_image_paths) > 0
        model = self.i2i_model if use_i2i else self.model
        payload: dict = {
            "model": model,
            "prompt": prompt,
            "size": size or "1024x1024",
            "n": 1,
        }

        if reference_image_paths:
            # Image-to-image mode: convert local paths to b64, pass via extra_body
            resolved = [self._resolve_image_ref(p) for p in reference_image_paths]
            extra_body: dict = {"response_format": "url"}
            if len(resolved) == 1:
                extra_body["image"] = resolved[0]
            else:
                extra_body["image"] = resolved
            payload["extra_body"] = extra_body

        print(f"  🖼️ 正在生成图片...", flush=True)
        logger.info(f"[Agnes Image] Generating ({'i2i' if use_i2i else 't2i'}): {prompt[:80]}...")

        resp = self._post_with_retry(
            f"{BASE_URL}/images/generations",
            payload,
            max_retries=5,
            base_delay=10.0,
            timeout=120,
        )

        result = resp.json()

        if "error" in result:
            err = result["error"]
            raise RuntimeError(f"Agnes image error: {err.get('message', err)}")

        data_list = result.get("data", [])
        if not data_list:
            raise RuntimeError("Agnes image: no data returned")

        url = data_list[0].get("url", "")
        if not url:
            # Check for base64
            b64_data = data_list[0].get("b64_json", "")
            if b64_data:
                logger.info("[Agnes Image] Got base64 response, saving...")
                return ImageOutput(fmt="b64", ext="png", data=b64_data)
            raise RuntimeError("Agnes image: no URL or base64 in response")

        logger.info(f"[Agnes Image] Done: {url[:80]}...")
        print(f"  ✅ 图片生成完成", flush=True)
        return ImageOutput(fmt="url", ext="png", data=url)
