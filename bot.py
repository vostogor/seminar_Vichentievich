import asyncio
import logging
import json
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import os

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher()


from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
)


load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise RuntimeError("BOT_TOKEN не найден. Проверь файл .env")

bot = Bot(token=TOKEN)
dp = Dispatcher()

user_profiles = {}


class ProfileForm(StatesGroup):
    age = State()
    level = State()
    vo2_question = State()
    vo2_value = State()
    speed = State()


age_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="14-29")],
        [KeyboardButton(text="30-45")],
        [KeyboardButton(text="46-60")],
    ],
    resize_keyboard=True,
)

level_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="начинающий"), KeyboardButton(text="любитель")],
        [KeyboardButton(text="продвинутый"), KeyboardButton(text="КМС/МС")],
    ],
    resize_keyboard=True,
)

yes_no_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Да"), KeyboardButton(text="Нет")],
    ],
    resize_keyboard=True,
)


def parse_pace_to_seconds(text: str) -> int | None:
    text = text.strip().lower()
    text = text.replace("сек", "")
    text = text.replace("с", "")
    text = text.strip()

    if ":" in text:
        parts = text.split(":")

        if len(parts) != 2:
            return None

        minutes = parts[0]
        seconds = parts[1]

        if not minutes.isdigit() or not seconds.isdigit():
            return None

        return int(minutes) * 60 + int(seconds)

    if text.isdigit():
        return int(text)

    return None


def format_pace(seconds: int) -> str:
    minutes = seconds // 60
    sec = seconds % 60
    return f"{minutes}:{sec:02d}"


@dp.message(Command("start"))
async def start(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user_profiles[user_id] = {}

    await message.answer(
        "Привет. Сначала соберём данные для персонализации тренировок.\n\n"
        "Выбери возрастную категорию:",
        reply_markup=age_keyboard,
    )

    await state.set_state(ProfileForm.age)


@dp.message(ProfileForm.age)
async def get_age(message: Message, state: FSMContext):
    user_id = message.from_user.id
    age = message.text

    if age not in ["14-29", "30-45", "46-60"]:
        await message.answer(
            "Пожалуйста, выбери возрастную категорию с клавиатуры.",
            reply_markup=age_keyboard,
        )
        return

    user_profiles[user_id]["age"] = age

    await message.answer(
        "Теперь выбери уровень плавания:",
        reply_markup=level_keyboard,
    )

    await state.set_state(ProfileForm.level)


@dp.message(ProfileForm.level)
async def get_level(message: Message, state: FSMContext):
    user_id = message.from_user.id
    level = message.text

    if level not in ["начинающий", "любитель", "продвинутый", "КМС/МС"]:
        await message.answer(
            "Пожалуйста, выбери уровень плавания с клавиатуры.",
            reply_markup=level_keyboard,
        )
        return

    user_profiles[user_id]["level"] = level

    await message.answer(
        "Ты знаешь свой VO2max?",
        reply_markup=yes_no_keyboard,
    )

    await state.set_state(ProfileForm.vo2_question)


@dp.message(ProfileForm.vo2_question)
async def get_vo2_question(message: Message, state: FSMContext):
    user_id = message.from_user.id
    answer = message.text

    if answer not in ["Да", "Нет"]:
        await message.answer(
            "Пожалуйста, выбери Да или Нет.",
            reply_markup=yes_no_keyboard,
        )
        return

    if answer == "Да":
        await message.answer(
            "Укажи VO2max числом, например: 48",
            reply_markup=ReplyKeyboardRemove(),
        )

        await state.set_state(ProfileForm.vo2_value)
        return

    user_profiles[user_id]["vo2max"] = None

    await message.answer(
        "Теперь укажи текущую среднюю скорость на 100 м.\n\n"
        "Можно написать в формате 1:40 или просто 100, если это 100 секунд.",
        reply_markup=ReplyKeyboardRemove(),
    )

    await state.set_state(ProfileForm.speed)


@dp.message(ProfileForm.vo2_value)
async def get_vo2_value(message: Message, state: FSMContext):
    user_id = message.from_user.id
    text = message.text.strip().replace(",", ".")

    try:
        vo2max = float(text)
    except ValueError:
        await message.answer("Пожалуйста, укажи VO2max числом. Например: 48")
        return

    if vo2max < 20 or vo2max > 90:
        await message.answer(
            "Проверь значение VO2max. Обычно оно находится примерно в диапазоне 20–90."
        )
        return

    user_profiles[user_id]["vo2max"] = vo2max

    await message.answer(
        "Теперь укажи текущую среднюю скорость на 100 м.\n\n"
        "Можно написать в формате 1:40 или просто 100, если это 100 секунд."
    )

    await state.set_state(ProfileForm.speed)


@dp.message(ProfileForm.speed)
async def get_speed(message: Message, state: FSMContext):
    user_id = message.from_user.id
    pace_seconds = parse_pace_to_seconds(message.text)

    if pace_seconds is None:
        await message.answer(
            "Не понял формат скорости.\n\n"
            "Напиши, например: 1:40 или 100."
        )
        return

    if pace_seconds < 40 or pace_seconds > 300:
        await message.answer(
            "Проверь темп. Укажи реалистичное время на 100 м, например 1:40 или 120."
        )
        return

    user_profiles[user_id]["pace_seconds"] = pace_seconds

    profile = user_profiles[user_id]

    vo2_text = profile["vo2max"] if profile["vo2max"] is not None else "не указан"

    await message.answer(
        "Анкета сохранена.\n\n"
        f"Возрастная категория: {profile['age']}\n"
        f"Уровень плавания: {profile['level']}\n"
        f"VO2max: {vo2_text}\n"
        f"Средняя скорость на 100 м: {format_pace(profile['pace_seconds'])}",
        reply_markup=ReplyKeyboardRemove(),
    )

    await state.clear()


@dp.message(Command("profile"))
async def show_profile(message: Message):
    user_id = message.from_user.id

    if user_id not in user_profiles:
        await message.answer("Анкета пока не заполнена. Напиши /start.")
        return

    profile = user_profiles[user_id]

    vo2_text = profile["vo2max"] if profile["vo2max"] is not None else "не указан"

    await message.answer(
        "Твоя анкета:\n\n"
        f"Возрастная категория: {profile['age']}\n"
        f"Уровень плавания: {profile['level']}\n"
        f"VO2max: {vo2_text}\n"
        f"Средняя скорость на 100 м: {format_pace(profile['pace_seconds'])}"
    )


@dp.message(Command("reset"))
async def reset_profile(message: Message, state: FSMContext):
    user_id = message.from_user.id

    if user_id in user_profiles:
        del user_profiles[user_id]

    await state.clear()

    await message.answer(
        "Данные удалены. Чтобы заполнить анкету заново, напиши /start.",
        reply_markup=ReplyKeyboardRemove(),
    )


@dp.message(Command("cancel"))
async def cancel(message: Message, state: FSMContext):
    await state.clear()

    await message.answer(
        "Действие отменено.",
        reply_markup=ReplyKeyboardRemove(),
    )


async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())