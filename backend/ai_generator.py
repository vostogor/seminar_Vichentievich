import os
from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

if not DEEPSEEK_API_KEY:
    raise RuntimeError("DEEPSEEK_API_KEY не найден. Проверь файл .env")


client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com",
)


def format_pace(seconds):
    minutes = seconds // 60
    sec = seconds % 60
    return f"{minutes}:{sec:02d}"


def generate_training_with_ai(profile, workout_type):
    vo2_text = profile.vo2max if profile.vo2max is not None else "не указан"

    prompt = f"""
Сгенерируй тренировку по плаванию на русском языке.

Данные пользователя:
- возрастная категория: {profile.age}
- уровень плавания: {profile.level}
- VO2max: {vo2_text}
- средняя скорость на 100 м: {format_pace(profile.pace_seconds)}
- тип тренировки: {workout_type}

Требования:
1. Учитывай уровень пловца.
2. Учитывай возрастную категорию.
3. Учитывай текущий темп на 100 м.
4. Сделай тренировку безопасной.
5. Структура ответа:
   - цель тренировки;
   - разминка;
   - основная часть;
   - заминка;
   - рекомендации.
6. Если тренировка гипоксическая, обязательно добавь предупреждение:
   нельзя выполнять задержки дыхания в одиночку.
7. Ответ должен быть понятным, практичным и не слишком длинным.
"""

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {
                "role": "system",
                "content": (
                    "Ты профессиональный тренер по плаванию. "
                    "Генерируй безопасные, понятные и реалистичные тренировки."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        stream=False,
        reasoning_effort="high",
        extra_body={"thinking": {"type": "enabled"}},
    )

    return response.choices[0].message.content