import io
import os
import logging
import asyncio
import numpy as np
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message, BufferedInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv

from utils import extract_palette, apply_palette, load_image_from_bytes, download_image

load_dotenv()
logging.basicConfig(level=logging.INFO)

bot = Bot(
    token=str(os.getenv("TOKEN")),
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)
dp = Dispatcher(storage=MemoryStorage())


class ImageState(StatesGroup):
    waiting_target = State()

@dp.message(CommandStart())
async def start(message: Message):
    await message.answer(
        "Send an image to use as a color palette.\n"
        "Then send another image to apply that palette."
    )


@dp.message(F.photo | F.document)
async def handle_images(message: Message, state: FSMContext):
    raw_bytes, send_as = await download_image(message=message, bot=bot)

    if raw_bytes is None or send_as is None:
        await message.answer("Please send a valid image file.")
        return

    image = load_image_from_bytes(raw_bytes)

    data = await state.get_data()
    palette: np.ndarray | None = data.get("palette")

    if palette is None:
        palette = await asyncio.to_thread(extract_palette, image)
        await state.update_data(palette=palette)
        await state.set_state(ImageState.waiting_target)
        await message.answer("Palette saved. Now send the target image.")
        return

    result = await asyncio.to_thread(apply_palette, palette, image)

    buffer = io.BytesIO()
    result.save(buffer, format="PNG")
    buffer.seek(0)

    filename = f"{message.chat.id}.png"
    file = BufferedInputFile(buffer.getvalue(), filename=filename)

    if send_as == "photo":
        await message.answer_photo(file)
    else:
        await message.answer_document(file)

    await state.clear()


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass