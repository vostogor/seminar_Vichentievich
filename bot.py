import asyncio
import logging
import os

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup
from dotenv import load_dotenv

from backend.ai_generator import generate_training_with_ai
from backend.database import (
    delete_user_profile,
    get_user_profile,
    init_db,
    save_user_profile,
)

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise RuntimeError("BOT_TOKEN не найден. Проверь файл .env")

bot = Bot(token=TOKEN)
dp = Dispatcher()

BACK_TEXT = "Назад"

AGE_OPTIONS = ["14-29", "30-45", "46-60"]
LEVEL_OPTIONS = ["начинающий", "любитель", "продвинутый", "КМС/МС"]
VO2_OPTIONS = ["Да", "Нет"]
WORKOUT_OPTIONS = ["силовая", "скорость", "выносливость", "гипоксия"]


class ProfileForm(StatesGroup):
    age = State()
    level = State()
    vo2_question = State()
    vo2_value = State()
    speed = State()


class WorkoutForm(StatesGroup):
    workout_type = State()


def make_keyboard(rows: list[list[str]], add_back: bool = False) -> ReplyKeyboardMarkup:
    keyboard = [[KeyboardButton(text=text) for text in row] for row in rows]

    if add_back:
        keyboard.append([KeyboardButton(text=BACK_TEXT)])

    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


age_keyboard = make_keyboard([["14-29"], ["30-45"], ["46-60"]])
level_keyboard = make_keyboard(
    [["начинающий", "любитель"], ["продвинутый", "КМС/МС"]],
    add_back=True,
)
yes_no_keyboard = make_keyboard([["Да", "Нет"]], add_back=True)
workout_keyboard = make_keyboard(
    [["силовая", "скорость"], ["выносливость", "гипоксия"]],
    add_back=True,
)
back_keyboard = make_keyboard([], add_back=True)
main_menu_keyboard = make_keyboard([["Заполнить анкету заново"], ["Выбрать тренировку"]])


def parse_pace_to_seconds(text: str) -> int | None:
    value = text.strip().lower().replace("сек", "").replace("с", "").strip()

    if ":" in value:
        parts = value.split(":")

        if len(parts) != 2:
            return None

        minutes, seconds = parts

        if not minutes.isdigit() or not seconds.isdigit():
            return None

        return int(minutes) * 60 + int(seconds)

    if value.isdigit():
        return int(value)

    return None


def format_pace(seconds: int) -> str:
    minutes = seconds // 60
    sec = seconds % 60
    return f"{minutes}:{sec:02d}"


def profile_text(data: dict, pace_seconds: int) -> str:
    vo2max = data.get("vo2max")
    vo2_text = vo2max if vo2max is not None else "не указан"

    return (
        "Анкета сохранена в базе данных.\n\n"
        f"Возрастная категория: {data['age']}\n"
        f"Уровень плавания: {data['level']}\n"
        f"VO2max: {vo2_text}\n"
        f"Средняя скорость на 100 м: {format_pace(pace_seconds)}\n\n"
        "Теперь выбери действие в главном меню:"
    )


async def ask_age(message: Message, state: FSMContext):
    await message.answer(
        "Выбери возрастную категорию:",
        reply_markup=age_keyboard,
    )
    await state.set_state(ProfileForm.age)


async def ask_level(message: Message, state: FSMContext):
    await message.answer(
        "Теперь выбери уровень плавания:",
        reply_markup=level_keyboard,
    )
    await state.set_state(ProfileForm.level)


async def ask_vo2_question(message: Message, state: FSMContext):
    await message.answer(
        "Ты знаешь свой VO2max?",
        reply_markup=yes_no_keyboard,
    )
    await state.set_state(ProfileForm.vo2_question)


async def ask_vo2_value(message: Message, state: FSMContext):
    await message.answer(
        "Укажи VO2max числом, например: 48",
        reply_markup=back_keyboard,
    )
    await state.set_state(ProfileForm.vo2_value)


async def ask_speed(message: Message, state: FSMContext):
    await message.answer(
        "Теперь укажи текущую среднюю скорость на 100 м.\n\n"
        "Можно написать в формате 1:40 или просто 100, если это 100 секунд.",
        reply_markup=back_keyboard,
    )
    await state.set_state(ProfileForm.speed)


async def show_main_menu(message: Message, state: FSMContext | None = None):
    if state is not None:
        await state.clear()

    await message.answer(
        "Главное меню:",
        reply_markup=main_menu_keyboard,
    )


@dp.message(Command("start"))
async def start(message: Message, state: FSMContext):
    await state.clear()

    await message.answer(
        "Привет. Это учебный студенческий проект Вичентиевич Марии.\n\n"
        "Бот создан для генерации тренировок по плаванию по типу тренировки "
        "и личным параметрам пользователя.\n\n"
        "Сначала соберём данные для персонализации тренировок."
    )

    await ask_age(message, state)


@dp.message(ProfileForm.age)
async def get_age(message: Message, state: FSMContext):
    age = message.text

    if age not in AGE_OPTIONS:
        await message.answer(
            "Пожалуйста, выбери возрастную категорию с клавиатуры.",
            reply_markup=age_keyboard,
        )
        return

    await state.update_data(age=age)
    await ask_level(message, state)


@dp.message(ProfileForm.level)
async def get_level(message: Message, state: FSMContext):
    level = message.text

    if level == BACK_TEXT:
        await ask_age(message, state)
        return

    if level not in LEVEL_OPTIONS:
        await message.answer(
            "Пожалуйста, выбери уровень плавания с клавиатуры.",
            reply_markup=level_keyboard,
        )
        return

    await state.update_data(level=level)
    await ask_vo2_question(message, state)


@dp.message(ProfileForm.vo2_question)
async def get_vo2_question(message: Message, state: FSMContext):
    answer = message.text

    if answer == BACK_TEXT:
        await ask_level(message, state)
        return

    if answer not in VO2_OPTIONS:
        await message.answer(
            "Пожалуйста, выбери Да или Нет.",
            reply_markup=yes_no_keyboard,
        )
        return

    if answer == "Да":
        await state.update_data(vo2_known=True)
        await ask_vo2_value(message, state)
        return

    await state.update_data(vo2_known=False, vo2max=None)
    await ask_speed(message, state)


@dp.message(ProfileForm.vo2_value)
async def get_vo2_value(message: Message, state: FSMContext):
    if message.text == BACK_TEXT:
        await ask_vo2_question(message, state)
        return

    text = message.text.strip().replace(",", ".")

    try:
        vo2max = float(text)
    except ValueError:
        await message.answer(
            "Пожалуйста, укажи VO2max числом. Например: 48",
            reply_markup=back_keyboard,
        )
        return

    if vo2max < 20 or vo2max > 90:
        await message.answer(
            "Проверь значение VO2max. Обычно оно находится примерно в диапазоне 20–90.",
            reply_markup=back_keyboard,
        )
        return

    await state.update_data(vo2max=vo2max)
    await ask_speed(message, state)


@dp.message(ProfileForm.speed)
async def get_speed(message: Message, state: FSMContext):
    if message.text == BACK_TEXT:
        data = await state.get_data()

        if data.get("vo2_known"):
            await ask_vo2_value(message, state)
        else:
            await ask_vo2_question(message, state)

        return

    user_id = message.from_user.id
    pace_seconds = parse_pace_to_seconds(message.text)

    if pace_seconds is None:
        await message.answer(
            "Не понял формат скорости.\n\nНапиши, например: 1:40 или 100.",
            reply_markup=back_keyboard,
        )
        return

    if pace_seconds < 40 or pace_seconds > 300:
        await message.answer(
            "Проверь темп. Укажи реалистичное время на 100 м, например 1:40 или 120.",
            reply_markup=back_keyboard,
        )
        return

    data = await state.get_data()

    save_user_profile(
        telegram_id=user_id,
        age=data["age"],
        level=data["level"],
        vo2max=data.get("vo2max"),
        pace_seconds=pace_seconds,
    )

    await message.answer(
        profile_text(data, pace_seconds),
        reply_markup=main_menu_keyboard,
    )

    await state.clear()


@dp.message(Command("profile"))
async def show_profile(message: Message):
    user_id = message.from_user.id
    profile = get_user_profile(user_id)

    if profile is None:
        await message.answer("Анкета пока не заполнена. Напиши /start.")
        return

    vo2_text = profile.vo2max if profile.vo2max is not None else "не указан"

    await message.answer(
        "Твоя анкета:\n\n"
        f"Возрастная категория: {profile.age}\n"
        f"Уровень плавания: {profile.level}\n"
        f"VO2max: {vo2_text}\n"
        f"Средняя скорость на 100 м: {format_pace(profile.pace_seconds)}"
    )


@dp.message(Command("menu"))
async def show_menu(message: Message, state: FSMContext):
    await show_main_menu(message, state)


@dp.message(F.text == "Выбрать тренировку")
async def choose_workout_from_button(message: Message, state: FSMContext):
    await workout(message, state)


@dp.message(F.text == "Заполнить анкету заново")
async def restart_profile_from_button(message: Message, state: FSMContext):
    await start(message, state)


@dp.message(Command("workout"))
async def workout(message: Message, state: FSMContext):
    user_id = message.from_user.id
    profile = get_user_profile(user_id)

    if profile is None:
        await message.answer("Сначала нужно заполнить анкету. Напиши /start.")
        return

    await message.answer(
        "Какой вид тренировки нужен сегодня?",
        reply_markup=workout_keyboard,
    )

    await state.set_state(WorkoutForm.workout_type)


@dp.message(WorkoutForm.workout_type)
async def get_workout_type(message: Message, state: FSMContext):
    user_id = message.from_user.id
    workout_type = message.text

    if workout_type == BACK_TEXT:
        await show_main_menu(message, state)
        return

    if workout_type not in WORKOUT_OPTIONS:
        await message.answer(
            "Пожалуйста, выбери тип тренировки с клавиатуры.",
            reply_markup=workout_keyboard,
        )
        return

    profile = get_user_profile(user_id)

    if profile is None:
        await message.answer("Анкета не найдена. Напиши /start.")
        await state.clear()
        return

    await message.answer(
        "Генерирую тренировку с помощью ИИ. Это может занять немного времени.",
        reply_markup=main_menu_keyboard,
    )

    try:
        workout_text = generate_training_with_ai(
            profile=profile,
            workout_type=workout_type,
        )
        await message.answer(workout_text)
        await message.answer(
            "Что сделать дальше?",
            reply_markup=main_menu_keyboard,
        )
    except Exception as error:
        await message.answer(
            "Не удалось сгенерировать тренировку.\n\n"
            f"Ошибка: {error}",
            reply_markup=main_menu_keyboard,
        )

    await state.clear()


@dp.message(Command("reset"))
async def reset_profile(message: Message, state: FSMContext):
    user_id = message.from_user.id

    delete_user_profile(user_id)
    await state.clear()

    await message.answer(
        "Данные удалены. Можешь заполнить анкету заново.",
        reply_markup=main_menu_keyboard,
    )


@dp.message(Command("cancel"))
async def cancel(message: Message, state: FSMContext):
    await state.clear()

    await message.answer(
        "Действие отменено. Возвращаю в главное меню.",
        reply_markup=main_menu_keyboard,
    )


@dp.message(F.text == BACK_TEXT)
async def back_without_state(message: Message, state: FSMContext):
    await show_main_menu(message, state)


async def main():
    logging.basicConfig(level=logging.INFO)
    init_db()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
