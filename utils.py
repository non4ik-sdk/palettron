import io
import numpy as np
from typing import Tuple, Literal
from PIL import Image
from aiogram import Bot
from aiogram.types import Message

def extract_palette(image: Image.Image, max_colors: int = 256) -> np.ndarray:
    image = image.convert("RGB")
    small = image.resize((256, 256))
    arr = np.array(small).reshape(-1, 3)
    unique_colors = np.unique(arr, axis=0)

    if len(unique_colors) > max_colors:
        idx = np.random.choice(len(unique_colors), max_colors, replace=False)
        unique_colors = unique_colors[idx]

    return unique_colors.astype(np.float32)


def apply_palette(source_palette: np.ndarray, target_img: Image.Image) -> Image.Image:
    target = np.array(target_img.convert("RGB"), dtype=np.float32)
    h, w, _ = target.shape
    flat = target.reshape(-1, 3)

    diff = flat[:, None, :] - source_palette[None, :, :]
    dist = np.sum(diff * diff, axis=2)
    nearest = np.argmin(dist, axis=1)

    mapped = source_palette[nearest]
    result = mapped.reshape(h, w, 3).astype(np.uint8)

    return Image.fromarray(result)


def load_image_from_bytes(data: bytes) -> Image.Image:
    buffer = io.BytesIO(data)
    buffer.seek(0)
    return Image.open(buffer)

async def download_image(
    bot: Bot,
    message: Message,
) -> Tuple[bytes, Literal["photo", "document"]] | Tuple[None, None]:

    file_id: str | None = None
    send_as: Literal["photo", "document"] | None = None

    if message.photo:
        file_id = message.photo[-1].file_id
        send_as = "photo"

    elif message.document:
        mime = message.document.mime_type
        if mime is not None and mime.startswith("image/"):
            file_id = message.document.file_id
            send_as = "document"

    if file_id is None or send_as is None:
        return None, None

    file = await bot.get_file(file_id)
    if file.file_path is None:
        return None, None

    buffer = io.BytesIO()
    await bot.download_file(file.file_path, buffer)
    return buffer.getvalue(), send_as