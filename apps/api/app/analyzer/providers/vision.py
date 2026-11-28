import base64
import io

from .. import prompts
from .llm import request_qwen_text


def read_screenshot(image, settings, limits):
    if not settings.dashscope_api_key.get_secret_value().strip():
        return None
    sample = image.copy()
    sample.thumbnail((1600, 1600))
    # Re-encode pixels without forwarding the original metadata.
    encoded = io.BytesIO()
    sample.save(encoded, format="JPEG", quality=92)
    data_url = "data:image/jpeg;base64," + base64.b64encode(encoded.getvalue()).decode("ascii")
    system, user = prompts.load(prompts.OCR_PROMPT).render()
    input_data = [{"role": "user", "content": [
        {"type": "input_text", "text": user},
        {"type": "input_image", "image_url": data_url},
    ]}]
    text, _ = request_qwen_text(settings, limits, system, input_data, timeout=14.0, max_output_tokens=1800)
    if not text or len(text) > 6000:
        return None
    readable = text.casefold().replace("[không có chữ]", "").replace("[không đọc được]", "")
    return text if any(char.isalnum() for char in readable) else None
